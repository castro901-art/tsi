import json
import subprocess
import time
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from api import config, store
from api.main import app
from api.schemas import Findings, MatchInput
from api.worker import process
from api.provider import ProviderError

TOKEN = "test-token-only-not-a-real-secret-123456"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
META = {"title": "Test highlights", "authorised": True, "provider_processing_consent": True}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path)
    monkeypatch.setenv("TSI_ACCESS_TOKEN", TOKEN)
    monkeypatch.setenv("GEMINI_API_KEY", "test-placeholder")
    monkeypatch.setenv("TSI_GEMINI_MODEL", "test-model")
    monkeypatch.setenv("TSI_PROVIDER_TERMS_ACCEPTED", "true")
    with TestClient(app) as value:
        yield value


def create(client):
    response = client.post("/v1/analyses", json=META, headers=HEADERS)
    assert response.status_code == 201
    return response.json()["id"]


def test_token_required(client):
    assert client.get("/v1/analyses").status_code == 401
    assert client.get("/v1/analyses", headers=HEADERS).status_code == 200


def test_configuration_guard(client, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY")
    response = client.post("/v1/analyses", json=META, headers=HEADERS)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "provider_not_configured"


def test_consent_and_urls(client):
    assert client.post("/v1/analyses", json={"title": "x", "authorised": False, "provider_processing_consent": True}, headers=HEADERS).status_code == 422
    assert client.post("/v1/analyses", json={**META, "url": "https://example.org/video"}, headers=HEADERS).status_code == 422


def test_invalid_file(client):
    job_id = create(client)
    response = client.put(f"/v1/analyses/{job_id}/video", content=b"not a video", headers={**HEADERS, "Content-Type": "video/mp4"})
    assert response.status_code == 422
    assert store.get(job_id)["status"] == "failed"
    assert not (config.DATA / f"{job_id}.mp4").exists()


def test_upload_limit(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_BYTES", 3)
    job_id = create(client)
    assert client.put(f"/v1/analyses/{job_id}/video", content=b"large", headers={**HEADERS, "Content-Type": "video/mp4"}).status_code == 413


def test_queue_and_result(client, tmp_path):
    # A generated test video checks ingestion; the provider below is a test double.
    video = tmp_path / "fixture.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=green:s=64x64:d=1", "-c:v", "mpeg4", str(video)], check=True)
    job_id = create(client)
    upload = client.put(f"/v1/analyses/{job_id}/video", content=video.read_bytes(), headers={**HEADERS, "Content-Type": "video/mp4"})
    assert upload.status_code == 202, upload.text
    assert store.claim() == job_id
    assert store.claim() is None

    class TestProvider:
        model = "test-double"
        def analyse(self, path):
            return Findings.model_validate({"events": [{"event_type": "other", "start_seconds": 0, "end_seconds": 0.5, "observation": "Test-only candidate", "confidence": 0.4}], "interpretations": [{"section": "attacking", "text": "Test-only interpretation", "event_indices": [0]}], "limitations": []})

    process(job_id, TestProvider())
    item = client.get(f"/v1/analyses/{job_id}", headers=HEADERS).json()
    assert item["status"] == "completed"
    assert item["result"]["events"][0]["verification_status"] == "unverified"
    assert item["result"]["events"][0]["player_id"] is None
    assert item["result"]["interpretations"][0]["evidence_ids"] == [item["result"]["events"][0]["id"]]
    assert "not human-verified" in client.get(f"/v1/analyses/{job_id}/report", headers=HEADERS).text
    assert client.put(f"/v1/analyses/{job_id}/video", content=b"x", headers={**HEADERS, "Content-Type": "video/mp4"}).status_code == 409
    store.init()
    assert store.get(job_id)["result"] == item["result"]


def test_schema_rejects_invalid_evidence():
    event = {"event_type": "shot", "start_seconds": 1, "end_seconds": 2, "observation": "candidate", "confidence": 0.5}
    with pytest.raises(ValidationError):
        Findings.model_validate({"events": [{**event, "start_seconds": float("nan")}], "interpretations": [], "limitations": []})
    with pytest.raises(ValueError):
        Findings.model_validate({"events": [event], "interpretations": [], "limitations": []}).validate_evidence(1)
    with pytest.raises(ValueError):
        Findings.model_validate({"events": [event], "interpretations": [{"section": "defensive", "text": "claim", "event_indices": [1]}], "limitations": []}).validate_evidence(3)


def test_quota_failure_does_not_fallback(client):
    job_id = create(client)
    store.transition(job_id, "awaiting_upload", "queued", duration=2, sha256="test")
    assert store.claim() == job_id
    class Exhausted:
        model = "test-double"
        def analyse(self, path):
            raise ProviderError("provider_quota_exhausted")
    process(job_id, Exhausted())
    assert store.get(job_id)["error"] == "provider_quota_exhausted"


def test_storage_limit(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_JOBS", 1)
    create(client)
    assert client.post("/v1/analyses", json=META, headers=HEADERS).status_code == 429


def test_retention(client):
    job_id = create(client)
    path = config.DATA / f"{job_id}.mp4"
    path.write_bytes(b"test")
    with store.connection() as db:
        db.execute("UPDATE analyses SET created=? WHERE id=?", (time.time() - config.RETENTION_SECONDS - 1, job_id))
    store.maintenance()
    assert store.get(job_id) is None
    assert not path.exists()


def test_provider_terms_guard(client, monkeypatch):
    monkeypatch.setenv("TSI_PROVIDER_TERMS_ACCEPTED", "false")
    response = client.post("/v1/analyses", json=META, headers=HEADERS)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "provider_terms_not_accepted"


def test_provider_sdk_adapter(client, monkeypatch, tmp_path):
    from types import SimpleNamespace
    from api.provider import GeminiProvider
    import api.provider as module
    calls = []
    remote = SimpleNamespace(name="files/test", state=SimpleNamespace(name="ACTIVE"))
    class Files:
        def upload(self, **kwargs):
            calls.append("upload")
            return remote
        def delete(self, **kwargs):
            calls.append("delete")
    class Models:
        def generate_content(self, **kwargs):
            calls.append("analyse")
            return SimpleNamespace(text=json.dumps({"events": [], "interpretations": [], "limitations": ["No football sequence in test response."]}))
    class Client:
        files = Files()
        models = Models()
        def __init__(self, **kwargs):
            pass
        def close(self):
            calls.append("close")
    monkeypatch.setattr(module.genai, "Client", Client)
    result = GeminiProvider().analyse(tmp_path / "test.mp4")
    assert result.events == []
    assert calls == ["upload", "analyse", "delete", "close"]
