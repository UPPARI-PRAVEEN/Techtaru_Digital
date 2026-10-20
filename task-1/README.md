# Task 1 — Papertrail PDF Chat

Papertrail is a React and FastAPI application for asking questions about text-based PDFs. It extracts PDF text, indexes overlapping chunks locally in ChromaDB, retrieves relevant excerpts, and uses Groq to generate answers grounded in those excerpts. Responses include source pages.

## Requirements

- Python 3.10+
- Node.js 18+ and npm
- A Groq API key for model-generated answers

## Configuration

From the repository root, create the task-local environment file and set the key:

```powershell
Copy-Item task-1\.env.example task-1\.env
```

`GROQ_MODEL`, `FRONTEND_ORIGIN`, `MAX_UPLOAD_MB`, `TOP_K`, `MAX_COSINE_DISTANCE`, and `LOG_LEVEL` are also configurable; their defaults are listed in `.env.example`. The backend loads `task-1/.env` first and retains support for a root `.env` for existing installations. Keep credentials server-side and do not commit `.env`.

## Run locally

Start the backend in one terminal:

```powershell
cd task-1\backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Start the frontend in another terminal from the repository root:

```powershell
cd task-1\frontend
npm ci
npm run dev
```

Open the Vite URL printed by the frontend (normally `http://localhost:5173`). The development proxy forwards `/api` to `http://127.0.0.1:8000`.

## API

- `GET /api/health` — health check.
- `POST /api/documents/upload` — multipart upload with a `file` PDF field. Returns `document_id`, filename, page count, and chunk count.
- `POST /api/chat` — JSON request with `document_id` (UUID) and `question` (1–2,000 characters). Returns an answer and source-page excerpts.
- `DELETE /api/documents/{document_id}` — deletes that document's local index.

OpenAPI documentation is available at `http://127.0.0.1:8000/docs` while the backend is running.

## Tests and production build

```powershell
cd task-1\backend
pytest
```

```powershell
cd task-1\frontend
npm ci
npm run build
```

## Implementation notes

The backend stores vector collections in `task-1/backend/.chroma/`. It does not upload the original PDF to Groq—only retrieved excerpts are used for answer generation. PDFs without selectable text are rejected; OCR is not included. Groq rate limits are reported as HTTP 429, and unavailable or invalid service credentials produce explicit API errors.
