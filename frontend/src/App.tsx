// frontend/src/App.tsx
import { useState, useEffect } from "react";
import { login, uploadDocument, queryData } from "./api";
import type { QueryResponse } from "./api";
import "./App.css";

function App() {
  // Auth state
  const [tenantId, setTenantId] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState<string | null>(null);

  const [loginError, setLoginError] = useState<string | null>(null);
  const [loginLoading, setLoginLoading] = useState(false);

  // Upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [uploadLoading, setUploadLoading] = useState(false);

  // Query state
  const [question, setQuestion] = useState("");
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [queryLoading, setQueryLoading] = useState(false);

  // Simple query history (only in-memory for now)
  const [queryHistory, setQueryHistory] = useState<
    { question: string; answerPreview: string }[]
  >([]);

  // Load auth from localStorage on mount
  useEffect(() => {
    const savedToken = localStorage.getItem("auth_token");
    const savedTenantId = localStorage.getItem("auth_tenant_id");
    const savedEmail = localStorage.getItem("auth_email");

    if (savedToken && savedTenantId && savedEmail) {
      setToken(savedToken);
      setTenantId(savedTenantId);
      setEmail(savedEmail);
    }
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError(null);
    setLoginLoading(true);
    try {
      const res = await login(tenantId, email, password);
      setToken(res.access_token);

      // persist auth info
      localStorage.setItem("auth_token", res.access_token);
      localStorage.setItem("auth_tenant_id", tenantId);
      localStorage.setItem("auth_email", email);
    } catch (err: any) {
      setLoginError(err.message || "Login failed");
    } finally {
      setLoginLoading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
      setUploadStatus(null);
    }
  };

  const handleUpload = async () => {
    if (!token) {
      setUploadStatus("You must be logged in.");
      return;
    }
    if (!selectedFile) {
      setUploadStatus("Please select a file first.");
      return;
    }
    setUploadStatus(null);
    setUploadLoading(true);
    try {
      const res = await uploadDocument(token, selectedFile);
      setUploadStatus(
        `Uploaded "${selectedFile.name}". Document ID: ${res.document_id}, status: ${res.status}`
      );
      setSelectedFile(null);
    } catch (err: any) {
      setUploadStatus(err.message || "Upload failed");
    } finally {
      setUploadLoading(false);
    }
  };

  const handleQuery = async () => {
    if (!token) {
      setQueryError("You must be logged in.");
      return;
    }
    if (!question.trim()) {
      setQueryError("Please enter a question.");
      return;
    }
    setQueryError(null);
    setQueryLoading(true);
    try {
      const res = await queryData(token, question, 5);
      setQueryResult(res);

      // store a small preview in history
      const preview =
        res.answer.length > 120 ? res.answer.slice(0, 120) + "…" : res.answer;
      setQueryHistory((prev) => [
        { question, answerPreview: preview },
        ...prev.slice(0, 4), // keep last 5
      ]);
    } catch (err: any) {
      setQueryError(err.message || "Query failed");
      setQueryResult(null);
    } finally {
      setQueryLoading(false);
    }
  };

  const handleLogout = () => {
    setToken(null);
    setQueryResult(null);
    setUploadStatus(null);
    setSelectedFile(null);
    setQueryHistory([]);

    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_tenant_id");
    localStorage.removeItem("auth_email");
  };

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>Company LLM Dashboard</h1>
          <p className="app-subtitle">
            Upload documents and ask questions about your company data.
          </p>
        </div>
        {token && (
          <div className="user-badge">
            <div>
              <div className="user-email">{email}</div>
              <div className="user-tenant">Tenant: {tenantId}</div>
            </div>
            <button className="btn-secondary" onClick={handleLogout}>
              Logout
            </button>
          </div>
        )}
      </header>

      {!token ? (
        <section className="card">
          <h2>Login</h2>
          <p className="hint">
            For now, use the <strong>tenant_id</strong> you created via Swagger
            plus the user&rsquo;s email &amp; password.
          </p>
          <form onSubmit={handleLogin} className="form">
            <label>
              Tenant ID
              <input
                type="text"
                value={tenantId}
                onChange={(e) => setTenantId(e.target.value)}
                placeholder="UUID of the tenant"
                required
              />
            </label>
            <label>
              Email
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@test.de"
                required
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </label>
            <button className="btn-primary" type="submit" disabled={loginLoading}>
              {loginLoading ? "Logging in..." : "Login"}
            </button>
            {loginError && <p className="error-text">{loginError}</p>}
          </form>
        </section>
      ) : (
        <main className="main-grid">
          <section className="card">
            <h2>1. Upload documents</h2>
            <p className="hint">
              Upload PDFs or other supported files. We&rsquo;ll extract and index
              them in the background.
            </p>
            <div className="upload-row">
              <input type="file" onChange={handleFileChange} />
              <button
                className="btn-primary"
                onClick={handleUpload}
                disabled={uploadLoading || !selectedFile}
              >
                {uploadLoading ? "Uploading..." : "Upload"}
              </button>
            </div>
            {selectedFile && (
              <p className="file-info">
                Selected: <strong>{selectedFile.name}</strong> (
                {(selectedFile.size / 1024).toFixed(1)} KB)
              </p>
            )}
            {uploadStatus && <p className="status-text">{uploadStatus}</p>}
          </section>

          <section className="card">
            <h2>2. Ask your data</h2>
            <p className="hint">
              Ask questions like:{" "}
              <em>&ldquo;Wann ist die Kündigungsfrist für Kunde Müller GmbH?&rdquo;</em>
            </p>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Type your question here..."
              rows={4}
            />
            <button
              className="btn-primary"
              onClick={handleQuery}
              disabled={queryLoading || !question.trim()}
            >
              {queryLoading ? "Asking..." : "Ask"}
            </button>
            {queryError && <p className="error-text">{queryError}</p>}

            {queryResult && (
              <div className="query-result">
                <h3>Answer</h3>
                <pre className="answer-block">{queryResult.answer}</pre>

                <h3>Sources</h3>
                {queryResult.sources.length === 0 ? (
                  <p className="hint">No sources found for this question.</p>
                ) : (
                  <ul className="sources-list">
                    {queryResult.sources.map((s, idx) => (
                      <li key={`${s.document_id}-${s.chunk_index}-${idx}`}>
                        <div className="source-header">
                          <span className="source-pill">
                            Doc: {s.document_id.slice(0, 8)}… Chunk: {s.chunk_index}
                          </span>
                        </div>
                        <div className="source-text">
                          {s.text.length > 300
                            ? s.text.slice(0, 300) + "…"
                            : s.text}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </section>

          <section className="card side-card">
            <h2>Recent questions</h2>
            {queryHistory.length === 0 ? (
              <p className="hint">No questions yet in this session.</p>
            ) : (
              <ul className="history-list">
                {queryHistory.map((q, idx) => (
                  <li key={idx}>
                    <div className="history-question">{q.question}</div>
                    <div className="history-answer-preview">{q.answerPreview}</div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </main>
      )}
    </div>
  );
}

export default App;
