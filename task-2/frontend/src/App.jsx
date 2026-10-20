
import { useState } from 'react';
import './styles.css';

const starterSamples = [
  {
    label: 'Resume sample',
    description: 'Python engineer · 6 years',
    icon: 'file-text',
    type: 'resume',
    text: 'John Doe is a senior Python engineer with 6 years of experience in FastAPI, SQL, and backend architecture. Email: john.doe@example.com. Phone: +1 (555) 123-4567. Worked at Acme Corp and DataForge.',
  },
  {
    label: 'Invoice sample',
    description: 'Northwind Labs · $2,480.75',
    icon: 'receipt',
    type: 'invoice',
    text: 'Invoice #INV-2048. Vendor: Northwind Labs. Total Amount: $2,480.75. Due Date: 2026-10-30. Contact: billing@northwind.com.',
  },
];

function App() {
  const [form, setForm] = useState({
    text: '',
    document_type: 'auto',
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(event) {
    event.preventDefault();

    const text = form.text.trim();

    if (!text) {
      setError('Please enter some document text first.');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await fetch('/api/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          document_type: form.document_type,
        }),
      });

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(
          payload.detail || 'Unable to extract structured data.'
        );
      }

      setResult(payload);
    } catch (err) {
      setError(
        err.message || 'Something went wrong. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  }

  function loadSample(sample) {
    setForm({
      text: sample.text,
      document_type: sample.type,
    });
    setError('');
    setResult(null);
  }

  function resetWorkspace() {
    setForm({ text: '', document_type: 'auto' });
    setResult(null);
    setError('');
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#workspace">
          <span className="brand-mark">✳</span>
          <span>Extract<span className="brand-accent">AI</span></span>
        </a>

        <div className="topbar-divider" />

        <p className="topbar-description">
          Intelligent document processing
        </p>

        <div className="topbar-right">
          <span className="tech-pill">
            <span className="status-dot" />
            Groq + Pydantic
          </span>
          <button
            type="button"
            className="icon-button"
            onClick={resetWorkspace}
            title="Reset workspace"
            aria-label="Reset workspace"
          >
            ↺
          </button>
        </div>
      </header>

      <aside className="sidebar">
        <div className="sidebar-links">
          <a className="sidebar-link active" href="#workspace"
            aria-label="Workspace" title="Workspace">
            <span>⌂</span>
          </a>
          <a className="sidebar-link" href="#input-panel"
            aria-label="Documents" title="Documents">
            <span>▤</span>
          </a>
          <a className="sidebar-link" href="#output-panel"
            aria-label="Results" title="Results">
            <span>⌘</span>
          </a>
        </div>
        <div className="sidebar-bottom">
          <span className="sidebar-sparkle">✳</span>
          <span>AI powered</span>
        </div>
      </aside>

      <main className="main-content" id="workspace">
        <section className="hero-section">
          <div className="hero-copy">
            <div className="eyebrow">
              <span className="eyebrow-line" />
              DOCUMENT INTELLIGENCE
            </div>

            <h1>
              Extract what
              <br />
              <span>matters most.</span>
            </h1>

            <p>
              Transform unstructured text into clean, structured
              data. Paste a document, choose a format, and let AI
              do the heavy lifting.
            </p>
          </div>

          <div className="feature-list">
            <div className="feature-item">
              <span className="feature-icon">ϟ</span>
              <strong>Fast</strong>
              <span>Groq inference</span>
            </div>
            <div className="feature-item">
              <span className="feature-icon">◇</span>
              <strong>Validated</strong>
              <span>Pydantic schemas</span>
            </div>
            <div className="feature-item">
              <span className="feature-icon">✳</span>
              <strong>Flexible</strong>
              <span>Multiple formats</span>
            </div>
          </div>
        </section>

        <section className="workspace-grid">
          <form
            className="workspace-card input-card"
            id="input-panel"
            onSubmit={handleSubmit}
          >
            <div className="card-heading">
              <div className="heading-icon">↗</div>
              <div>
                <h2>Document input</h2>
                <p>Provide the content you want to process.</p>
              </div>
              <span className="step-label">STEP 01</span>
            </div>

            <div className="form-field">
              <label htmlFor="document-type">Document type</label>
              <select
                id="document-type"
                value={form.document_type}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    document_type: event.target.value,
                  }))
                }
              >
                <option value="auto">✳ Auto detect</option>
                <option value="resume">Resume</option>
                <option value="invoice">Invoice</option>
                <option value="custom">Custom document</option>
              </select>
            </div>

            <div className="form-field text-field">
              <div className="label-row">
                <label htmlFor="raw-text">Document content</label>
                <span>{form.text.length} characters</span>
              </div>
              <textarea
                id="raw-text"
                maxLength={20000}
                value={form.text}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    text: event.target.value,
                  }))
                }
                placeholder="Paste your resume, invoice, or any unstructured text here..."
              />
              <div className="editor-footer">
                <span className="editor-dot" />
                Plain text input
                <span className="editor-limit">20,000 max</span>
              </div>
            </div>

            <div className="sample-section">
              <div className="sample-heading">
                <span>Try an example</span>
                <span className="sample-caption">QUICK START</span>
              </div>

              <div className="sample-grid">
                {starterSamples.map((sample) => (
                  <button
                    type="button"
                    key={sample.type}
                    className={`sample-card ${
                      form.text === sample.text ? 'selected' : ''
                    }`}
                    onClick={() => loadSample(sample)}
                  >
                    <span className="sample-icon">
                      {sample.type === 'resume' ? '▤' : '▧'}
                    </span>
                    <span className="sample-copy">
                      <strong>{sample.label}</strong>
                      <small>{sample.description}</small>
                    </span>
                    <span className="sample-arrow">↗</span>
                  </button>
                ))}
              </div>
            </div>

            {error && (
              <div className="error-box" role="alert">
                <strong>Something needs your attention</strong>
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              className="extract-button"
              disabled={loading || !form.text.trim()}
            >
              <span>{loading ? '◌' : '✳'}</span>
              {loading ? 'Extracting your data...' : 'Extract structured data'}
              {!loading && <span className="button-arrow">→</span>}
            </button>

            <p className="privacy-note">
              Process your text into structured output in one step.
            </p>
          </form>

          <section
            className="workspace-card output-card"
            id="output-panel"
          >
            <div className="card-heading output-heading">
              <div className="heading-icon output-icon">{'{}'}</div>
              <div>
                <h2>Structured output</h2>
                <p>Your extracted data, ready to inspect.</p>
              </div>
              <span className={`result-status ${loading ? 'processing' : result ? 'complete' : ''}`}>
                <span className="status-dot" />
                {loading
                  ? 'Processing'
                  : result
                  ? 'Complete'
                  : 'Awaiting input'}
              </span>
            </div>

            {loading ? (
              <div className="output-empty">
                <div className="loader-ring" />
                <h3>Structuring your data</h3>
                <p>Analyzing the document and validating the output.</p>
              </div>
            ) : !result ? (
              <div className="output-empty">
                <div className="empty-illustration">
                  <span className="empty-file">{'{}'}</span>
                  <span className="empty-star">✳</span>
                </div>
                <h3>Your results will appear here</h3>
                <p>
                  Submit a document to see structured fields,
                  metadata, and the complete JSON response.
                </p>
                <div className="expected-fields">
                  <span>Document type</span>
                  <span>Extracted fields</span>
                  <span>JSON output</span>
                </div>
              </div>
            ) : (
              <div className="output-content">
                <div className="result-metrics">
                  <div className="metric-card">
                    <span>DOCUMENT TYPE</span>
                    <strong>{result.document_type || '—'}</strong>
                  </div>
                  <div className="metric-card">
                    <span>SOURCE</span>
                    <strong>{result.source || '—'}</strong>
                  </div>
                  <div className="metric-card">
                    <span>CONFIDENCE</span>
                    <strong>
                      {result.confidence == null
                        ? '—'
                        : Number(result.confidence).toFixed(2)}
                    </strong>
                  </div>
                </div>

                <div className="json-heading">
                  <div>
                    <span className="json-live-dot" />
                    <strong>Response JSON</strong>
                  </div>
                  <button
                    type="button"
                    className="copy-button"
                    onClick={() => {
                      navigator.clipboard?.writeText(
                        JSON.stringify(result, null, 2)
                      );
                    }}
                  >
                    Copy JSON ↗
                  </button>
                </div>

                <pre className="json-viewer">
                  {JSON.stringify(result, null, 2)}
                </pre>

                <button
                  type="button"
                  className="secondary-button"
                  onClick={resetWorkspace}
                >
                  Start a new extraction ↗
                </button>
              </div>
            )}

            <div className="output-footer">
              <span className="footer-shield">◇</span>
              <div>
                <strong>Structured. Validated. Ready.</strong>
                <p>Groq-powered extraction with Pydantic validation.</p>
              </div>
            </div>
          </section>
        </section>

        <footer className="page-footer">
          <span>EXTRACTAI <span>·</span> DOCUMENT WORKSPACE</span>
          <span>Built with Groq + Pydantic</span>
        </footer>
      </main>
    </div>
  );
}

export default App;
