from __future__ import annotations

import logging
import os
from io import BytesIO
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import UUID, uuid4

import chromadb
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from groq import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncGroq,
    AuthenticationError,
    RateLimitError,
)
from pydantic import BaseModel, Field, field_validator
from pypdf import PdfReader

TASK_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = TASK_ROOT.parent
load_dotenv(TASK_ROOT / ".env")
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "15")) * 1024 * 1024
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 180
TOP_K = int(os.getenv("TOP_K", "4"))
MAX_COSINE_DISTANCE = float(os.getenv("MAX_COSINE_DISTANCE", "0.95"))
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

chroma = chromadb.PersistentClient(path=str(TASK_ROOT / "backend" / ".chroma"))
collection_lock = RLock()

app = FastAPI(title="PDF Knowledge Chat", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    document_id: UUID
    question: str = Field(min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question must not be blank.")
        return value


class Source(BaseModel):
    page: int
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]


def split_into_chunks(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("Chunk size must be positive and overlap must be smaller than the chunk size.")

    normalized = " ".join(text.split())
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + size, len(normalized))
        if end < len(normalized):
            boundary = normalized.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start = max(end - overlap, start + 1)
    return chunks


def select_relevant_chunks(
    documents: list[str],
    distances: list[float],
    metadatas: list[dict[str, Any]],
    max_distance: float = MAX_COSINE_DISTANCE,
) -> list[dict[str, Any]]:
    matches = []
    for document, distance, metadata in zip(documents, distances, metadatas):
        if distance <= max_distance:
            matches.append(
                {
                    "text": document,
                    "page": int(metadata["page"]),
                    "distance": float(distance),
                }
            )
    return matches


def get_collection(document_id: UUID):
    name = f"doc-{document_id.hex}"
    try:
        return chroma.get_collection(name=name)
    except Exception as exc:
        if exc.__class__.__name__ in {"InvalidCollectionException", "NotFoundError"}:
            raise HTTPException(status_code=404, detail="The requested PDF was not found.") from exc
        logger.exception("Unable to open document collection.")
        raise HTTPException(status_code=503, detail="The document index is temporarily unavailable.") from exc


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/documents/upload")
async def upload_pdf(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename or Path(file.filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=415, detail="Upload a PDF file.")

    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"PDF exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit.",
        )
    if not contents.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="The uploaded file is not a valid PDF.")

    try:
        reader = PdfReader(BytesIO(contents), strict=False)
        pages = [
            (page_number, page.extract_text() or "")
            for page_number, page in enumerate(reader.pages, start=1)
        ]
    except Exception as exc:
        logger.info("PDF parsing failed: %s", exc)
        raise HTTPException(status_code=422, detail="Could not read this PDF. Try a valid, text-based PDF.") from exc

    chunks: list[dict[str, Any]] = []
    for page_number, page_text in pages:
        chunks.extend(
            {"text": chunk, "page": page_number}
            for chunk in split_into_chunks(page_text)
        )
    if not chunks:
        raise HTTPException(
            status_code=422,
            detail="No selectable text was found. Scanned PDFs need OCR before they can be used.",
        )

    document_id = uuid4()
    collection_name = f"doc-{document_id.hex}"
    try:
        with collection_lock:
            collection = chroma.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine", "filename": Path(file.filename).name},
            )
            collection.add(
                ids=[f"chunk-{index}" for index in range(len(chunks))],
                documents=[chunk["text"] for chunk in chunks],
                metadatas=[{"page": chunk["page"]} for chunk in chunks],
            )
    except Exception as exc:
        logger.exception("Failed to create the PDF vector index.")
        raise HTTPException(
            status_code=503,
            detail="Could not build the PDF search index. Please try again.",
        ) from exc

    return {
        "document_id": str(document_id),
        "filename": Path(file.filename).name,
        "page_count": len(pages),
        "chunk_count": len(chunks),
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    collection = get_collection(request.document_id)
    try:
        result = collection.query(
            query_texts=[request.question],
            n_results=min(TOP_K, collection.count()),
            include=["documents", "distances", "metadatas"],
        )
    except Exception as exc:
        logger.exception("Vector search failed.")
        raise HTTPException(status_code=503, detail="PDF search is temporarily unavailable.") from exc

    documents = result["documents"][0] if result["documents"] else []
    distances = result["distances"][0] if result["distances"] else []
    metadatas = result["metadatas"][0] if result["metadatas"] else []
    matches = select_relevant_chunks(documents, distances, metadatas)
    if not matches:
        return ChatResponse(
            answer="I couldn't find a relevant answer in this PDF.",
            sources=[],
        )

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY is not configured. Add it to the project .env file.",
        )

    context = "\n\n".join(
        f"[Page {match['page']}]\n{match['text']}"
        for match in matches
    )
    client = AsyncGroq(api_key=api_key)
    try:
        completion = await client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Answer the user's question using only the supplied PDF excerpts. "
                        "The excerpts are search candidates and may not be relevant: verify that they "
                        "actually support the answer before responding. If they do not contain enough "
                        "evidence, say exactly: \"I couldn't find a relevant answer in this PDF.\" "
                        "Do not use outside knowledge. Cite supporting page numbers as [Page N]."
                    ),
                },
                {
                    "role": "user",
                    "content": f"PDF excerpts:\n{context}\n\nQuestion: {request.question}",
                },
            ],
        )
    except RateLimitError as exc:
        retry_after = exc.response.headers.get("retry-after")
        logger.warning("Groq rate limit reached.")
        raise HTTPException(
            status_code=429,
            detail="The AI service is rate limited. Wait briefly, then try again.",
            headers={"Retry-After": retry_after} if retry_after else None,
        ) from exc
    except AuthenticationError as exc:
        logger.error("Groq rejected the configured API key.")
        raise HTTPException(status_code=503, detail="The configured Groq API key was rejected.") from exc
    except (APITimeoutError, APIConnectionError) as exc:
        logger.warning("Groq is temporarily unreachable: %s", exc)
        raise HTTPException(status_code=503, detail="The AI service is temporarily unavailable.") from exc
    except APIStatusError as exc:
        logger.error("Groq returned HTTP %s.", exc.status_code)
        raise HTTPException(status_code=503, detail="The AI service could not answer this request.") from exc
    finally:
        await client.close()

    answer = completion.choices[0].message.content
    if not answer or not answer.strip():
        raise HTTPException(status_code=502, detail="The AI service returned an empty answer. Please retry.")

    answer = answer.strip()
    if answer.casefold().startswith("i couldn't find a relevant answer in this pdf."):
        return ChatResponse(answer=answer, sources=[])

    sources_by_page: dict[int, str] = {}
    for match in matches:
        sources_by_page.setdefault(match["page"], match["text"])
    return ChatResponse(
        answer=answer,
        sources=[
            Source(page=page, excerpt=text[:240] + ("…" if len(text) > 240 else ""))
            for page, text in sources_by_page.items()
        ],
    )


@app.delete("/api/documents/{document_id}")
def delete_document(document_id: UUID) -> dict[str, str]:
    with collection_lock:
        collection = get_collection(document_id)
        try:
            chroma.delete_collection(name=collection.name)
        except Exception as exc:
            logger.exception("Failed to delete a document collection.")
            raise HTTPException(status_code=503, detail="Could not remove the PDF index.") from exc
    return {"status": "deleted"}
