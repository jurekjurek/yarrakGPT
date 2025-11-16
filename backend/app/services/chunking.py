# here is where the chunking logic shall be implemented
# TODO: implement the existing chunking logic here. 
# backend/app/services/chunking.py
from typing import List

def extract_text_from_pdf(file_path: str) -> str:
    """
    Placeholder for your real PDF-to-text logic.
    For now, we just read the file as bytes or return dummy text.
    Replace with your existing code.
    """
    # TODO: plug your actual implementation here.
    # Example structure:
    # import fitz  # PyMuPDF
    # doc = fitz.open(file_path)
    # text = ""
    # for page in doc:
    #     text += page.get_text()
    # return text
    with open(file_path, "rb") as f:
        data = f.read()
    return f"Dummy extracted text of length {len(data)} from {file_path}"

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Simple character-based chunking as a placeholder.
    Replace with your own smarter chunking.
    """
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == text_len:
            break
        start = end - overlap  # move back a bit for overlap
    return chunks
