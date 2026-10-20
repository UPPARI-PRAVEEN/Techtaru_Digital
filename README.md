# Papertrail — Chat with your PDF

A React and FastAPI RAG application for asking questions about text-based PDF documents. It extracts and chunks PDF text, embeds chunks into ChromaDB, retrieves them with cosine-distance search, and asks Groq to answer using only the retrieved excerpts. Answers include the source page and excerpt.

## Requirements

- Python 3.10+
- Node.js 18+
- A Groq API key

## Configure

From the project root, copy `.env.example` to `.env` and set `GROQ_API_KEY` to a **newly rotated** key. Do not commit `.env`. The model defaults to `openai/gpt-oss-120b`.

```powershell
Copy-Item .env.example .env
```

Optional settings:

| Variable | Default | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | — | Secret used by the FastAPI server; never expose it in React. |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Groq chat model identifier. |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | Allowed browser origin for the API. |
| `MAX_UPLOAD_MB` | `15` | Maximum PDF upload size. |
| `TOP_K` | `4` | Maximum number of matching chunks to retrieve. |
| `MAX_COSINE_DISTANCE` | `0.95` | Maximum Chroma cosine distance for a chunk to be considered as an answer candidate. |

## Run locally

Open two terminals from the project root.

### FastAPI

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

On systems where `py` is unavailable, create the virtual environment with `python -m venv .venv`.

### React

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL printed in the terminal (normally `http://localhost:5173`). Vite proxies `/api` requests to FastAPI on port 8000. The first ChromaDB embedding may download its default `all-MiniLM-L6-v2` model.

## Tests and build

```powershell
cd backend
pytest
```

```powershell
cd frontend
npm run build
```

## How retrieval works

PDF text is split into overlapping character windows so a sentence near a chunk boundary is less likely to lose its context. ChromaDB embeds each chunk and stores the vectors with page metadata. At question time it embeds the question, searches the collection created for that PDF, and returns the nearest chunks using the collection's cosine metric. For normalized vectors, cosine similarity is the dot product; Chroma's cosine distance is `1 - similarity`, so smaller distances indicate closer semantic matches. Chunks farther than `MAX_COSINE_DISTANCE` are discarded. The cutoff is deliberately permissive because short or paraphrased questions can have relatively high distances even when a PDF contains the answer. Retrieved excerpts are candidates, not guaranteed evidence: the LLM must verify that they support its answer and abstain if they do not. If no candidates survive the cutoff, the API returns an explicit no-match response without asking the LLM.

## Notes

- Scanned PDFs without selectable text require OCR and are rejected with a helpful error.
- PDF vectors are stored locally in `backend/.chroma/`; deleting a document in the interface removes its collection.
- The API does not send the PDF itself to Groq—only retrieved text excerpts are sent for answering.
- Groq rate limits are returned as HTTP 429 with a retry hint; invalid credentials and service outages produce explicit errors.
