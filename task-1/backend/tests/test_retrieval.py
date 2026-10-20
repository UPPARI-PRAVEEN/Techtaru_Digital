from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import main
from app.main import select_relevant_chunks, split_into_chunks

client = TestClient(main.app)


def test_split_into_chunks_preserves_text_with_overlap():
    text = " ".join(f"word{i}" for i in range(45))
    chunks = split_into_chunks(text, size=60, overlap=12)

    assert len(chunks) > 1
    assert all(len(chunk) <= 60 for chunk in chunks)
    assert chunks[0].split()[-1] in chunks[1].split()[:3]


def test_split_into_chunks_handles_empty_text():
    assert split_into_chunks(" \n\t ") == []


def test_split_into_chunks_rejects_invalid_overlap():
    with pytest.raises(ValueError, match="overlap"):
        split_into_chunks("text", size=10, overlap=10)


def test_select_relevant_chunks_keeps_resume_matches_with_higher_cosine_distance():
    matches = select_relevant_chunks(
        documents=["resume experience", "unrelated match"],
        distances=[0.656, 1.05],
        metadatas=[{"page": 2}, {"page": 3}],
    )

    assert matches == [{"text": "resume experience", "page": 2, "distance": 0.656}]


def test_chat_does_not_call_llm_when_no_chunks_are_relevant(monkeypatch):
    class EmptyMatchCollection:
        def count(self):
            return 1

        def query(self, **kwargs):
            assert kwargs["n_results"] == 1
            return {
                "documents": [["unrelated text"]],
                "distances": [[1.05]],
                "metadatas": [[{"page": 1}]],
            }

    monkeypatch.setattr(main, "get_collection", lambda _: EmptyMatchCollection())
    response = client.post(
        "/api/chat",
        json={"document_id": "00000000-0000-0000-0000-000000000001", "question": "question"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "I couldn't find a relevant answer in this PDF.",
        "sources": [],
    }


def test_chat_sends_resume_match_to_llm_and_returns_source(monkeypatch):
    class ResumeCollection:
        def count(self):
            return 1

        def query(self, **kwargs):
            assert kwargs["n_results"] == 1
            return {
                "documents": [["The candidate has over five years of experience in data analytics."]],
                "distances": [[0.839]],
                "metadatas": [[{"page": 2}]],
            }

    class FakeGroq:
        def __init__(self, *, api_key: str):
            assert api_key == "test-key"
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self.create_completion)
            )

        async def create_completion(self, **kwargs):
            assert "over five years of experience" in kwargs["messages"][1]["content"]
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="The candidate has over five years of experience [Page 2].")
                    )
                ]
            )

        async def close(self):
            pass

    monkeypatch.setattr(main, "get_collection", lambda _: ResumeCollection())
    monkeypatch.setattr(main, "AsyncGroq", FakeGroq)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    response = client.post(
        "/api/chat",
        json={
            "document_id": "00000000-0000-0000-0000-000000000001",
            "question": "Can you summarize the resume?",
        },
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "The candidate has over five years of experience [Page 2]."
    assert response.json()["sources"][0]["page"] == 2


def test_chat_omits_sources_when_llm_cannot_support_an_answer(monkeypatch):
    class SearchCandidateCollection:
        def count(self):
            return 1

        def query(self, **kwargs):
            assert kwargs["n_results"] == 1
            return {
                "documents": [["A loosely related excerpt."]],
                "distances": [[0.8]],
                "metadatas": [[{"page": 1}]],
            }

    class RefusingGroq:
        def __init__(self, *, api_key: str):
            assert api_key == "test-key"
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self.create_completion)
            )

        async def create_completion(self, **kwargs):
            assert "verify that they actually support" in kwargs["messages"][0]["content"]
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="I couldn't find a relevant answer in this PDF."
                        )
                    )
                ]
            )

        async def close(self):
            pass

    monkeypatch.setattr(main, "get_collection", lambda _: SearchCandidateCollection())
    monkeypatch.setattr(main, "AsyncGroq", RefusingGroq)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    response = client.post(
        "/api/chat",
        json={
            "document_id": "00000000-0000-0000-0000-000000000001",
            "question": "What is the office address?",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "I couldn't find a relevant answer in this PDF.",
        "sources": [],
    }


def test_chat_rejects_blank_questions():
    response = client.post(
        "/api/chat",
        json={"document_id": "00000000-0000-0000-0000-000000000001", "question": "   "},
    )

    assert response.status_code == 422
