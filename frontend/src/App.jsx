import { useEffect, useRef, useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  BookOpen,
  Check,
  FileText,
  LoaderCircle,
  MessageSquareText,
  Paperclip,
  Plus,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  X,
} from "lucide-react";

const starterPrompts = [
  "What is this document about?",
  "Summarize the key points",
  "What are the main conclusions?",
];

async function readError(response) {
  try {
    const body = await response.json();
    return body.detail || "Something went wrong. Please try again.";
  } catch {
    return "Something went wrong. Please try again.";
  }
}

function App() {
  const inputRef = useRef(null);
  const endRef = useRef(null);
  const [document, setDocument] = useState(null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [uploading, setUploading] = useState(false);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, asking]);

  async function uploadPdf(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Choose a PDF file to get started.");
      return;
    }
    setError("");
    setUploading(true);
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await fetch("/api/documents/upload", { method: "POST", body });
      if (!response.ok) throw new Error(await readError(response));
      setDocument(await response.json());
      setMessages([]);
    } catch (uploadError) {
      setError(uploadError.message || "Unable to upload this PDF.");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function sendQuestion(value = question) {
    const text = value.trim();
    if (!text || !document || asking) return;
    setError("");
    setQuestion("");
    setMessages((current) => [...current, { role: "user", content: text }]);
    setAsking(true);
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_id: document.document_id, question: text }),
      });
      if (!response.ok) throw new Error(await readError(response));
      const result = await response.json();
      setMessages((current) => [
        ...current,
        { role: "assistant", content: result.answer, sources: result.sources },
      ]);
    } catch (chatError) {
      setError(chatError.message || "Unable to get an answer.");
    } finally {
      setAsking(false);
    }
  }

  function resetDocument() {
    if (document) {
      fetch(`/api/documents/${document.document_id}`, { method: "DELETE" }).catch(() => {});
    }
    setDocument(null);
    setMessages([]);
    setError("");
  }

  function onDrop(event) {
    event.preventDefault();
    setDragging(false);
    uploadPdf(event.dataTransfer.files?.[0]);
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="#" aria-label="Papertrail home">
          <span className="brand-mark"><BookOpen size={19} strokeWidth={2.2} /></span>
          <span>papertrail<span className="brand-period">.</span></span>
        </a>
        <div className="topbar-note"><ShieldCheck size={15} /> Private by design</div>
      </header>

      <section className={`workspace ${document ? "has-document" : ""}`}>
        {!document ? (
          <div
            className={`welcome ${dragging ? "is-dragging" : ""}`}
            onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <div className="eyebrow"><Sparkles size={14} /> YOUR DOCUMENT, MADE CLEAR</div>
            <h1>Good questions<br /><span>start with good context.</span></h1>
            <p className="intro">Add a PDF and explore what matters. Every answer is grounded in your document, with page references to back it up.</p>
            <button
              className="upload-card"
              onClick={() => inputRef.current?.click()}
              disabled={uploading}
            >
              <span className="upload-icon">
                {uploading ? <LoaderCircle className="spin" size={23} /> : <UploadCloud size={23} />}
              </span>
              <span className="upload-copy">
                <strong>{uploading ? "Reading your PDF…" : "Drop your PDF here"}</strong>
                <span>{uploading ? "Extracting text and building a searchable index" : "or click to browse · up to 15 MB"}</span>
              </span>
              {!uploading && <span className="browse-button">Choose file</span>}
            </button>
            <input ref={inputRef} className="file-input" type="file" accept="application/pdf,.pdf" onChange={(event) => uploadPdf(event.target.files?.[0])} />
            <div className="trust-row"><ShieldCheck size={15} /> Your documents are indexed locally and never used to train AI.</div>
            {error && <div className="error-banner" role="alert">{error}</div>}
            <div className="steps">
              <div><span>01</span><p>Upload a PDF</p></div>
              <div><span>02</span><p>Ask anything</p></div>
              <div><span>03</span><p>Get cited answers</p></div>
            </div>
          </div>
        ) : (
          <div className="chat-layout">
            <aside className="document-rail">
              <div className="rail-heading">YOUR WORKSPACE</div>
              <div className="document-card">
                <span className="pdf-icon"><FileText size={18} /></span>
                <span className="doc-info">
                  <strong title={document.filename}>{document.filename}</strong>
                  <small>{document.page_count} {document.page_count === 1 ? "page" : "pages"} · {document.chunk_count} sections</small>
                </span>
                <button className="icon-button" onClick={resetDocument} aria-label="Remove PDF"><X size={16} /></button>
              </div>
              <button className="add-document" onClick={() => inputRef.current?.click()}><Plus size={15} /> Add another PDF</button>
              <input ref={inputRef} className="file-input" type="file" accept="application/pdf,.pdf" onChange={(event) => uploadPdf(event.target.files?.[0])} />
              <div className="rail-footnote"><ShieldCheck size={14} /> Answers stay grounded in this PDF.</div>
            </aside>

            <section className="conversation">
              <div className="conversation-header">
                <div><span className="live-dot" /> DOCUMENT CHAT</div>
                <span className="model-label">Groq · {import.meta.env.VITE_MODEL_LABEL || "GPT-OSS 120B"}</span>
              </div>
              <div className="conversation-scroll">
                {messages.length === 0 ? (
                  <div className="empty-chat">
                    <div className="chat-glyph"><MessageSquareText size={22} /></div>
                    <h2>What would you like to know?</h2>
                    <p>Ask a question about <strong>{document.filename}</strong>. Answers include source pages.</p>
                    <div className="prompt-list">
                      {starterPrompts.map((prompt) => (
                        <button key={prompt} onClick={() => sendQuestion(prompt)} disabled={asking}>
                          {prompt}<ArrowUp size={14} />
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="message-list">
                    {messages.map((message, index) => (
                      <article className={`message ${message.role}`} key={`${message.role}-${index}`}>
                        <div className="message-avatar">{message.role === "assistant" ? <Sparkles size={15} /> : "Y"}</div>
                        <div className="message-body">
                          <div className="message-label">{message.role === "assistant" ? "PAPERTRAIL" : "YOU"}</div>
                          <p>{message.content}</p>
                          {message.sources?.length > 0 && (
                            <div className="sources">
                              {message.sources.map((source) => (
                                <div className="source-chip" key={source.page}>
                                  <span><FileText size={12} /> Page {source.page}</span>
                                  <small>{source.excerpt}</small>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </article>
                    ))}
                    {asking && <div className="typing"><LoaderCircle className="spin" size={16} /> Searching your PDF…</div>}
                    <div ref={endRef} />
                  </div>
                )}
                {error && <div className="error-banner chat-error" role="alert">{error}</div>}
              </div>
              <form className="composer" onSubmit={(event) => { event.preventDefault(); sendQuestion(); }}>
                <div className="composer-box">
                  <Paperclip size={17} />
                  <input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask a question about your PDF…" maxLength={2000} aria-label="Ask a question" />
                  <button className="send-button" type="submit" disabled={!question.trim() || asking} aria-label="Send question">
                    {asking ? <LoaderCircle className="spin" size={17} /> : <ArrowUp size={18} />}
                  </button>
                </div>
                <div className="composer-hint"><Check size={12} /> Responses are based only on your document <span><ArrowDown size={12} /> Enter to send</span></div>
              </form>
            </section>
          </div>
        )}
      </section>

      <footer className="footer"><span>papertrail<span className="brand-period">.</span></span><span>Read less. Understand more.</span></footer>
    </main>
  );
}

export default App;
