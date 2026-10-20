# Techtaru Digital

This repository contains two independent document-processing applications:

- **Task 1 — Papertrail:** upload a text-based PDF, ask questions about it, and receive answers grounded in retrieved PDF excerpts with page citations.
- **Task 2 — Data Extraction Bot:** submit unstructured text and receive validated, structured fields for resumes, invoices, or custom documents.

Each task has its own backend dependencies, React frontend, environment example, and task-specific README. Start each task from its own folder as described below.

## Project Structure

```text
.
├── task-1/
│   ├── backend/
│   │   ├── app/
│   │   │   └── main.py
│   │   ├── tests/
│   │   │   └── test_retrieval.py
│   │   └── requirements.txt
│   ├── frontend/
│   │   ├── src/
│   │   ├── package.json
│   │   └── vite.config.js
│   ├── .env.example
│   └── README.md
├── task-2/
│   ├── frontend/
│   │   ├── src/
│   │   ├── package.json
│   │   └── vite.config.js
│   ├── app.py
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
├── .gitignore
└── README.md
```

The package lockfiles, HTML entry points, stylesheets, and other application files remain alongside their respective frontend manifests. Virtual environments, installed packages, and generated build/index data are local runtime files and are not listed above.

## Task 1 Details — Papertrail PDF Chat

### Objective and features

Papertrail lets a user upload a text-based PDF, ask questions about its contents, and inspect answer citations and supporting excerpts. The React interface supports drag-and-drop upload, suggested questions, and removal of an indexed document.

### Technologies

- Python 3.10 or later, FastAPI, Pydantic, and Uvicorn
- `pypdf` for page text extraction
- ChromaDB for local vector storage and cosine-distance retrieval
- Groq's Python client for answer generation
- React 18 and Vite 6

See [task-1/backend/requirements.txt](./task-1/backend/requirements.txt) and [task-1/frontend/package.json](./task-1/frontend/package.json) for the dependency constraints.

### Implementation details

PDF text is extracted page by page, normalized, and split into overlapping chunks. ChromaDB embeds and stores the chunks with page metadata in `task-1/backend/.chroma/`. For each question, the API retrieves the nearest chunks, filters them by `MAX_COSINE_DISTANCE`, and asks Groq to answer only when relevant candidates remain. The response includes cited page numbers and source excerpts; if there are no relevant candidates or the model cannot substantiate an answer, the API abstains.

Only retrieved text excerpts—not the original PDF—are sent to Groq. Scanned PDFs without selectable text are not OCR-processed and are rejected with an explanatory error.

### API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Health check |
| `POST` | `/api/documents/upload` | Upload a PDF as multipart form field `file`; returns its ID, filename, page count, and chunk count |
| `POST` | `/api/chat` | JSON body: `{"document_id":"<uuid>","question":"..."}`; returns an answer and cited sources |
| `DELETE` | `/api/documents/{document_id}` | Remove the document's local vector collection |

### Setup and run

Prerequisites: Python 3.10+ and Node.js 18+. A Groq API key is needed for model-generated answers.

In PowerShell, configure the backend:

```powershell
Copy-Item task-1\.env.example task-1\.env
# Edit task-1\.env and set GROQ_API_KEY.
cd task-1\backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

In a second terminal from the repository root, run the frontend:

```powershell
cd task-1\frontend
npm ci
npm run dev
```

Open the Vite URL shown in the frontend terminal (normally `http://localhost:5173`). The Vite development server proxies `/api` to the backend on `http://127.0.0.1:8000`.

Additional notes and commands: [task-1/README.md](./task-1/README.md).

## Task 2 Details — Data Extraction Bot

### Objective and features

The Data Extraction Bot accepts pasted document text and returns typed JSON fields. It supports automatic document-type detection and explicit `resume`, `invoice`, or `custom` selection. When credentials are unavailable or structured model output cannot be used, it returns a local heuristic extraction.

### Technologies

- Python 3.10 or later, FastAPI, Pydantic, and Uvicorn
- OpenAI Python SDK configured for Groq's OpenAI-compatible endpoint
- React 18 and Vite 5

See [task-2/requirements.txt](./task-2/requirements.txt) and [task-2/frontend/package.json](./task-2/frontend/package.json) for the dependency constraints.

### Implementation details

The API validates input text length (10–20,000 characters) and document type, detects a type when `auto` is selected, and returns fields including contact details, company, invoice details, skills, experience, summary, confidence, and extraction source. The React UI includes sample resume and invoice text and displays the response JSON.

The service can return heuristic results without an API key. With `GROQ_API_KEY`, it uses the configured Groq model and structured output; it also accepts `OPENAI_API_KEY` for the OpenAI client defaults. The documented local server port is 8001.

### API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/` | Service status message |
| `GET` | `/api/health` | Health check |
| `POST` | `/api/extract` | Extract data from JSON `{"text":"...","document_type":"auto"}` |

`document_type` accepts `auto`, `resume`, `invoice`, or `custom`. The response includes `document_type`, `name`, `email`, `phone`, `company`, `total_amount`, `invoice_number`, `due_date`, `skills`, `experience_years`, `summary`, `confidence`, and `source`.

### Setup and run

Prerequisites: Python 3.10+ and Node.js 18+. A Groq API key is optional; without a key, local heuristic extraction is used.

In PowerShell, configure the backend:

```powershell
Copy-Item task-2\.env.example task-2\.env
# Optionally edit task-2\.env and set GROQ_API_KEY.
cd task-2
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --reload --port 8001
```

In a second terminal from the repository root, run the frontend:

```powershell
cd task-2\frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. The Vite development server proxies `/api` to the Task 2 backend on port 8001.

Additional notes and commands: [task-2/README.md](./task-2/README.md).

## Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer and npm
- PowerShell on Windows for the commands above; equivalent Python, virtual-environment, and npm commands work on other operating systems
- Groq API credentials for model-generated answers in Task 1; optional Groq or OpenAI credentials for model-based extraction in Task 2

Use a separate Python virtual environment per task. Their Python dependencies and frontend toolchains are intentionally kept separate.

## Installation and Execution

Run each task independently by starting its backend and frontend in separate terminals:

| Task | Backend working directory and command | Frontend working directory and command |
| --- | --- | --- |
| Task 1 | `task-1\backend` — `uvicorn app.main:app --reload` (port 8000) | `task-1\frontend` — `npm run dev` (port 5173) |
| Task 2 | `task-2` — `uvicorn app:app --reload --port 8001` | `task-2\frontend` — `npm run dev` (port 5173) |

Install backend dependencies with `pip install -r requirements.txt` from the listed backend directory, and frontend dependencies with `npm ci` from the listed frontend directory. Configure each task's `.env` from its own `.env.example`; do not put API keys in frontend variables.

## Testing

Task 1 includes backend tests for chunking and retrieval/chat behavior:

```powershell
cd task-1\backend
pytest
```

Build each frontend to validate its production bundle:

```powershell
cd task-1\frontend
npm ci
npm run build
```

```powershell
cd task-2\frontend
npm ci
npm run build
```

No Task 2 automated test files are currently included.

## Environment Variables

### Task 1 (`task-1/.env`)

Start from `task-1/.env.example`. The values below are placeholders or defaults; replace the key locally and never commit secrets.

| Variable | Default | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | unset | Groq credential for answer generation |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Groq chat model |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | Browser origin allowed by API CORS |
| `MAX_UPLOAD_MB` | `15` | Maximum PDF upload size in MiB |
| `TOP_K` | `4` | Maximum number of retrieval candidates |
| `MAX_COSINE_DISTANCE` | `0.95` | Maximum cosine distance for a candidate |
| `LOG_LEVEL` | `INFO` | Python logging level |

For compatibility, Task 1 also reads a root `.env` if a task-local `.env` is absent or does not define a value.

### Task 2 (`task-2/.env`)

Start from `task-2/.env.example`. Credentials are optional for the fallback extractor.

| Variable | Default | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | unset | Groq credential |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Model name; `OPENAI_MODEL` is used as a fallback |
| `OPENAI_API_KEY` | unset | Optional OpenAI credential when no Groq credential is set |
| `OPENAI_BASE_URL` | `https://api.groq.com/openai/v1` | OpenAI-compatible endpoint used with `GROQ_API_KEY` |

The server port is selected by the Uvicorn command (`8001` in the documented command). Do not put real credentials in the frontend or commit local `.env` files.

## Troubleshooting

- **PowerShell blocks virtual-environment activation:** use `py -m venv .venv` and invoke `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and `.\.venv\Scripts\python.exe -m uvicorn ...` without activating.
- **A port is already in use:** stop the other server or select another backend port. If changing Task 1's backend port, also update the Task 1 Vite proxy in `task-1/frontend/vite.config.js`.
- **The browser cannot reach the API:** keep the backend and frontend running in separate terminals and check that the correct task's Vite proxy target is active (8000 for Task 1, 8001 for Task 2).
- **Task 1 reports a missing/rejected Groq key:** set a valid `GROQ_API_KEY` in `task-1/.env`; do not expose it to the browser.
- **Task 1 rejects a PDF with no selectable text:** scanned PDFs require OCR before upload; OCR is not included.
- **Task 1 returns no relevant answer:** check that the PDF contains the requested information. Retrieval distance filtering and model evidence checks can intentionally produce an abstention.
- **Task 2 returns fallback results:** check that a valid `GROQ_API_KEY` is available if model-based extraction is desired. The fallback extractor works without it but uses local heuristics.
- **Frontend dependencies or builds fail:** run `npm ci` from that task's frontend folder and then retry `npm run build`.
