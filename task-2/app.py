from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator

from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent / ".env")

app = FastAPI(title="Data Extraction Bot", version="1.0.0")

GROQ_MODEL = os.getenv("GROQ_MODEL", os.getenv("OPENAI_MODEL", "openai/gpt-oss-120b"))
GROQ_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")


class ExtractionRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=20000)
    document_type: Literal["auto", "resume", "invoice", "custom"] = "auto"

    @field_validator("text")
    @classmethod
    def clean_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Text must not be blank.")
        return cleaned


class ExtractedData(BaseModel):
    document_type: str = Field(default="unknown")
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    total_amount: str | None = None
    invoice_number: str | None = None
    due_date: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience_years: str | None = None
    summary: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source: Literal["llm", "fallback"] = "fallback"


def _detect_document_type(raw_text: str, requested: str) -> str:
    if requested != "auto":
        return requested

    lowered = raw_text.lower()
    if re.search(r"\b(invoice|bill|amount due|payment terms|vendor|customer)\b", lowered):
        return "invoice"
    if re.search(r"\b(experience|skills|education|resume|employment|project)\b", lowered):
        return "resume"
    return "custom"


def _extract_email(text: str) -> str | None:
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else None


def _extract_phone(text: str) -> str | None:
    match = re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", text)
    return match.group(0).strip() if match else None


def _extract_amount(text: str) -> str | None:
    match = re.search(
        r"(?:total|amount due|balance due|grand total)[:\s$]*([$€£]?\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+\.\d{2})",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None
    return match.group(0).strip()


def _extract_number(text: str, label: str) -> str | None:
    pattern = rf"{label}\s*[:#-]?\s*([A-Za-z0-9-]+)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


def _extract_skills(text: str) -> list[str]:
    common_skills = [
        "Python",
        "FastAPI",
        "JavaScript",
        "TypeScript",
        "React",
        "SQL",
        "PostgreSQL",
        "Docker",
        "AWS",
        "Git",
        "Machine Learning",
        "Data Analysis",
        "APIs",
        "Leadership",
        "Communication",
    ]
    found = []
    lowered = text.lower()
    for skill in common_skills:
        if skill.lower() in lowered:
            found.append(skill)
    return found[:10]


def _extract_name(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:8]:
        words = line.split()
        if len(words) >= 2 and not any(token.lower() in {"resume", "invoice", "bill", "total", "page"} for token in words[:3]):
            return line
    return None


def _heuristic_extract(raw_text: str, document_type: str) -> ExtractedData:
    email = _extract_email(raw_text)
    phone = _extract_phone(raw_text)
    name = _extract_name(raw_text)
    amount = None
    invoice_number = None
    due_date = None
    company = None
    experience_years = None
    summary = "Structured information extracted from text."

    if document_type == "invoice":
        company_match = re.search(r"(?:from|vendor|company)[:\s]+([A-Za-z0-9&.,\- ]+)", raw_text, re.IGNORECASE)
        company = company_match.group(1).strip() if company_match else None
        invoice_number = _extract_number(raw_text, "invoice") or _extract_number(raw_text, "bill")
        due_date_match = re.search(r"(?:due date|due)[:\s]+(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|[A-Za-z]+ \d{1,2}, \d{4})", raw_text, re.IGNORECASE)
        if due_date_match:
            due_date = due_date_match.group(1).strip()
        amount = _extract_amount(raw_text)
        summary = "Invoice details extracted from unstructured text."
    elif document_type == "resume":
        experience_match = re.search(r"(\d+\+?\s*(?:years?|yrs?))\s*(?:of\s+)?experience", raw_text, re.IGNORECASE)
        if experience_match:
            experience_years = experience_match.group(1).strip()
        company_match = re.search(r"(?:at|with)\s+([A-Z][A-Za-z0-9&.,\- ]{2,})\s*(?:\n|$)", raw_text)
        if company_match:
            company = company_match.group(1).strip()
        summary = "Professional profile extracted from resume content."
    else:
        amount = _extract_amount(raw_text)
        invoice_number = _extract_number(raw_text, "invoice")

    return ExtractedData(
        document_type=document_type,
        name=name,
        email=email,
        phone=phone,
        company=company,
        total_amount=amount,
        invoice_number=invoice_number,
        due_date=due_date,
        skills=_extract_skills(raw_text),
        experience_years=experience_years,
        summary=summary,
        confidence=0.7,
        source="fallback",
    )


def _run_structured_extract(raw_text: str, document_type: str) -> ExtractedData:
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _heuristic_extract(raw_text, document_type)

    client_kwargs = {"api_key": api_key}
    if os.getenv("GROQ_API_KEY"):
        client_kwargs["base_url"] = GROQ_BASE_URL

    client = OpenAI(**client_kwargs)
    system_prompt = (
        "Extract only factual information from the provided text. If a field is missing, return null or an empty list. "
        "Return clean JSON that is consistent with the selected document type."
    )
    if document_type == "resume":
        system_prompt += " Focus on name, email, phone, company, skills, experience_years, and summary."
    elif document_type == "invoice":
        system_prompt += " Focus on company, invoice_number, total_amount, due_date, email, phone, and summary."

    try:
        response = client.beta.chat.completions.parse(
            model=GROQ_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw_text},
            ],
            response_format=ExtractedData,
        )
        parsed = response.choices[0].message.parsed
        if parsed is None:
            return _heuristic_extract(raw_text, document_type)
        parsed.document_type = document_type
        parsed.source = "llm"
        parsed.confidence = max(float(parsed.confidence or 0.0), 0.9)
        return parsed
    except Exception:
        return _heuristic_extract(raw_text, document_type)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/extract", response_model=ExtractedData)
def extract_data(payload: ExtractionRequest) -> ExtractedData:
    detected_type = _detect_document_type(payload.text, payload.document_type)
    return _run_structured_extract(payload.text, detected_type)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Data Extraction Bot is running."}
