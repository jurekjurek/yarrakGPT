// frontend/src/App.tsx
import { useState } from "react";
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

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError(null);
    setLoginLoading(true);
    try {
      const res = await login(tenantId, email, password);
      setToken(res.access_token);
    } catch (err: any) {
      setLoginError(err.message || "Login failed");
    } finally {
      setLoginLoading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
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
      setUploadStatus(`Uploaded. Document ID: ${res.document_id}, status: ${res.status}`);
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
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Company LLM Dashboard</h1>
        {token && (
          <button className="btn-secondary" onClick={handleLogout}>
            Logout
          </button>
        )}
      </header>

      {!token ? (
        <section className="card">
          <h2>Login</h2>
          <p style={{ fontSize: "0.9rem", color: "#555" }}>
            For now, enter the <strong>tenant_id</strong> you created via Swagger,
            plus the user&rsquo;s email and password.
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
        <>
          <section className="card">
            <h2>Upload document</h2>
            <p>Upload a PDF or document to be ingested for your tenant.</p>
            <input type="file" onChange={handleFileChange} />
            <button className="btn-primary" onClick={handleUpload} disabled={uploadLoading}>
              {uploadLoading ? "Uploading..." : "Upload"}
            </button>
            {uploadStatus && <p className="status-text">{uploadStatus}</p>}
          </section>

          <section className="card">
            <h2>Ask your data</h2>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Wann ist die Kündigungsfrist für Kunde X?"
              rows={4}
            />
            <button className="btn-primary" onClick={handleQuery} disabled={queryLoading}>
              {queryLoading ? "Asking..." : "Ask"}
            </button>
            {queryError && <p className="error-text">{queryError}</p>}

            {queryResult && (
              <div className="query-result">
                <h3>Answer</h3>
                <pre className="answer-block">{queryResult.answer}</pre>

                <h3>Sources</h3>
                <ul>
                  {queryResult.sources.map((s, idx) => (
                    <li key={`${s.document_id}-${s.chunk_index}-${idx}`}>
                      <strong>Document:</strong> {s.document_id} |{" "}
                      <strong>Chunk:</strong> {s.chunk_index}
                      <br />
                      <span className="source-text">
                        {s.text.length > 300 ? s.text.slice(0, 300) + "..." : s.text}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}

export default App;

