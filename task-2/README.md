# Task 2 — Data Extraction Bot

The Data Extraction Bot turns unstructured text into a typed JSON response. It supports resumes, invoices, and custom text, with automatic document-type detection. It has an independent FastAPI backend and React interface.

## Requirements

- Python 3.10+
- Node.js 18+ and npm
- A Groq API key for model-based extraction (optional; heuristic extraction works without a key)

## Configuration

From the repository root, create the task-local environment file:

```powershell
Copy-Item task-2\.env.example task-2\.env
```

Set `GROQ_API_KEY` in `task-2/.env` to enable Groq-based structured extraction. The service also supports `OPENAI_API_KEY`; supported model and endpoint settings are described in the root README. Keep secrets out of source control.

## Run locally

Start the backend in one terminal:

```powershell
cd task-2
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --reload --port 8001
```

Start the frontend in another terminal from the repository root:

```powershell
cd task-2\frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` requests to the backend on port 8001.
The port is selected by the Uvicorn command; changing an environment file does not change it.

## API

- `GET /` — service status.
- `GET /api/health` — health check.
- `POST /api/extract` — submit text and a document type:

```json
{
  "text": "John Doe, Python engineer with 4 years of experience. Email: john@example.com.",
  "document_type": "resume"
}
```

The `text` field must contain 10–20,000 characters. `document_type` accepts `auto`, `resume`, `invoice`, or `custom`. The response includes document type, name, email, phone, company, invoice fields, skills, experience, summary, confidence, and the extraction `source` (`llm` or `fallback`).

OpenAPI documentation is available at `http://127.0.0.1:8001/docs` while the backend is running.

## Build and tests

```powershell
cd task-2\frontend
npm ci
npm run build
```

No automated Task 2 test files are currently included.

## Implementation notes

The API uses Pydantic to validate requests and parse structured model responses. It detects invoice- or resume-like text when `auto` is selected. When there is no configured API key, or structured model output cannot be used, it falls back to local regular-expression and keyword heuristics. Heuristic results are best-effort and can be less complete than model-based extraction.
