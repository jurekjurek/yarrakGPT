# backend/app/services/chunking.py

import math
import re
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any

from PyPDF2 import PdfReader


# --- Basic PDF reading ---

def read_pdf_text_by_page(pdf_path: str | Path) -> List[str]:
    """
    Read a PDF file and return a list of page texts.
    """
    path = Path(pdf_path)
    reader = PdfReader(str(path))
    pages: List[str] = []
    for p in reader.pages:
        try:
            pages.append(p.extract_text() or "")
        except Exception:
            pages.append("")
    return pages


# --- Tokenization / normalization ---

def simple_normalize(text: str) -> List[str]:
    """
    Lowercase and keep only word characters (including German Umlauts) and digits.
    Returns a list of tokens.
    """
    text = text.lower()
    text = re.sub(r"[^\w\sÄÖÜäöüß]", " ", text, flags=re.UNICODE)
    tokens = re.findall(r"[a-zA-ZÄÖÜäöüß0-9]+", text)
    return tokens


def chunk_text(text: str, max_tokens: int = 220, overlap: int = 40) -> List[str]:
    """
    Chunk text based on tokens into overlapping windows.
    Returns token-joined strings (already normalized).
    """
    tokens = simple_normalize(text)
    if not tokens:
        return []
    chunks: List[str] = []
    i = 0
    while i < len(tokens):
        chunk_tokens = tokens[i : i + max_tokens]
        chunks.append(" ".join(chunk_tokens))
        if i + max_tokens >= len(tokens):
            break
        i += max_tokens - overlap
    return chunks


# --- Scoring functions (BM25 + TF-IDF cosine) ---

def bm25_scores(
    query_tokens: List[str],
    docs_tokens: List[List[str]],
    k1: float = 1.5,
    b: float = 0.75,
) -> List[float]:
    N = len(docs_tokens)
    df: Counter[str] = Counter()
    doc_len = [len(dt) for dt in docs_tokens]
    avgdl = sum(doc_len) / N if N else 0.0

    for dt in docs_tokens:
        df.update(set(dt))

    idf = {
        term: math.log((N - df_t + 0.5) / (df_t + 0.5) + 1.0)
        for term, df_t in df.items()
    }

    scores: List[float] = []
    q_counts = Counter(query_tokens)

    for dt in docs_tokens:
        dl = len(dt) or 1
        f = Counter(dt)
        s = 0.0
        for term in q_counts:
            if term not in f:
                continue
            tf = f[term]
            denom = tf + k1 * (1 - b + b * dl / (avgdl or 1))
            s += idf.get(term, 0.0) * ((tf * (k1 + 1)) / denom)
        scores.append(s)
    return scores


def tfidf_cosine(query_tokens: List[str], docs_tokens: List[List[str]]) -> List[float]:
    N = len(docs_tokens)
    df: Counter[str] = Counter()
    for dt in docs_tokens:
        df.update(set(dt))

    idf = {t: math.log((N + 1) / (df_t + 1)) + 1.0 for t, df_t in df.items()}
    vocab = {t: i for i, t in enumerate(df.keys())}

    def vec(tokens: List[str]) -> Dict[int, float]:
        tf = Counter(tokens)
        v: Dict[int, float] = {}
        L = len(tokens) or 1
        for t, c in tf.items():
            if t in vocab:
                v[vocab[t]] = (c / L) * idf.get(t, 1.0)
        return v

    def dot(a: Dict[int, float], b: Dict[int, float]) -> float:
        # iterate over smaller dict
        if len(a) > len(b):
            a, b = b, a
        return sum(a[i] * b.get(i, 0.0) for i in a.keys())

    def norm(a: Dict[int, float]) -> float:
        return math.sqrt(sum(x * x for x in a.values())) or 1.0

    qv = vec(query_tokens)
    qn = norm(qv)
    sims: List[float] = []
    for dt in docs_tokens:
        dv = vec(dt)
        dn = norm(dv)
        sims.append(dot(qv, dv) / (qn * dn))
    return sims


# --- Query rewrite & hybrid search ---

def rewrite_query(user_q: str) -> Dict[str, Any]:
    return {"original": user_q, "normalized": " ".join(simple_normalize(user_q))}


def hybrid_search(
    qobj: Dict[str, Any],
    corpus: Dict[str, Any],
    top_k: int = 5,
    alpha: float = 0.6,
) -> List[Dict[str, Any]]:
    qtoks = qobj["normalized"].split()
    docs_tokens: List[List[str]] = corpus.get("doc_tokens", [])
    if not docs_tokens:
        return []

    s_bm25 = bm25_scores(qtoks, docs_tokens)
    s_cos = tfidf_cosine(qtoks, docs_tokens)

    mixed = [
        (alpha * s_cos[i] + (1 - alpha) * s_bm25[i], i)
        for i in range(len(docs_tokens))
    ]
    mixed.sort(reverse=True)

    out: List[Dict[str, Any]] = []
    for score, idx in mixed[:top_k]:
        rec = dict(corpus["records"][idx])
        rec["score"] = float(score)
        out.append(rec)
    return out


# --- Prompt building ---

def build_prompt(user_q: str, hits: List[Dict[str, Any]]) -> str:
    blocks = []
    for i, h in enumerate(hits, 1):
        filename = h.get("filename", "unknown")
        page = h.get("page", "?")
        score = h.get("score", 0.0)
        text = h.get("text", "")
        blocks.append(
            f"[Chunk {i} | {filename} S.{page} | score={score:.3f}]\n{text}"
        )
    context = "\n\n".join(blocks)
    system = (
        "Du bist ein hilfreicher Assistent. Antworte präzise basierend auf dem Kontext. "
        "Wenn Informationen fehlen, sage das offen."
    )
    return f"{system}\n\nKONTEXT:\n{context}\n\nFRAGE: {user_q}\n\nANTWORT:"
