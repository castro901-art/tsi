"""Link tests use doubles only: no real platform requests or paid services."""
import socket
import pytest
from api import config, store, links
from api.main import app
from fastapi.testclient import TestClient

META = {"title": "TEST — authorised platform import", "authorised": True, "provider_processing_consent": True}

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path)
    monkeypatch.setenv("TSI_REGISTRATION_ENABLED", "true")
    monkeypatch.setenv("TSI_APP_ORIGIN", "https://testserver")
    monkeypatch.setenv("GEMINI_API_KEY", "test-placeholder")
    monkeypatch.setenv("TSI_GEMINI_MODEL", "test-model")
    monkeypatch.setenv("TSI_PROVIDER_TERMS_ACCEPTED", "true")
    monkeypatch.delenv("TSI_LINK_RESOLVER_URL", raising=False)
    monkeypatch.delenv("TSI_LINK_MEDIA_HOSTS", raising=False)
    with TestClient(app, base_url="https://testserver") as client:
        auth = client.post("/v1/auth/register", json={"username":"analyst", "password":"test-password-1234"})
        client.headers["X-TSI-CSRF"] = auth.json()["csrf_token"]
        yield client

@pytest.mark.parametrize("url,platform", [
    ("https://youtu.be/abcdefghijk?t=5", "youtube"),
    ("https://www.youtube.com/watch?v=abcdefghijk", "youtube"),
    ("https://youtube.com/shorts/abcdefghijk", "youtube"),
    ("https://x.com/team/status/123456/video/1", "x"),
    ("https://twitter.com/team/status/123456", "x"),
])
def test_canonical_sources(url, platform):
    assert links.canonical_source(url)[0] == platform

@pytest.mark.parametrize("url", ["http://youtu.be/abcdefghijk", "https://youtube.com.evil.org/watch?v=abcdefghijk", "https://user:pass@youtube.com/watch?v=abcdefghijk", "https://127.0.0.1/video.mp4", "https://x.com/team", "https://youtube.com/watch?v=bad", "file:///etc/passwd"])
def test_reject_bad_sources(url):
    with pytest.raises(links.LinkError):
        links.canonical_source(url)

def test_unconfigured_and_csrf(client):
    assert client.get("/v1/capabilities").json()["url_ingestion"] is False
    response = client.post("/v1/analyses/from-link", json={"url":"https://youtu.be/abcdefghijk", "metadata":META})
    assert response.status_code == 503
    assert client.get("/v1/analyses").json() == []
    client.headers.pop("X-TSI-CSRF")
    assert client.post("/v1/analyses/from-link", json={"url":"https://youtu.be/abcdefghijk", "metadata":META}).status_code == 403

@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "fc00::1"])
def test_private_destinations_blocked(monkeypatch, ip):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip,443))])
    with pytest.raises(links.LinkError):
        links.connection("https://media.example/video.mp4", {"media.example"})

def test_reject_redirect_host_and_credentials():
    for url in ["https://evil.example/video", "https://user:pass@media.example/video", "https://media.example:444/video", "https://media.example/video#fragment"]:
        with pytest.raises(links.LinkError):
            links.connection(url, {"media.example"})

@pytest.mark.parametrize("platform,url", [("youtube","https://youtu.be/abcdefghijk"),("x","https://x.com/team/status/123")])
def test_queue_link_and_provenance(client, monkeypatch, platform, url):
    monkeypatch.setenv("TSI_LINK_RESOLVER_URL", "https://resolver.example/resolve")
    monkeypatch.setenv("TSI_LINK_MEDIA_HOSTS", "media.example")
    monkeypatch.setattr(links, "resolve", lambda source: "https://media.example/video.mp4")
    def download(url, target):
        target.write_bytes(b"test-only video bytes")
        return "a" * 64
    monkeypatch.setattr(links, "download", download)
    monkeypatch.setattr(links, "probe", lambda target: 2.0)
    response = client.post("/v1/analyses/from-link", json={"url":url, "metadata":META})
    assert response.status_code == 202
    item = store.get(response.json()["id"])
    assert item["status"] == "queued" and item["duration"] == 2
    assert item["metadata"]["source_platform"] == platform
    assert client.get("/v1/analyses").json()[0]["metadata"]["title"] == META["title"]
    assert store.claim() == item["id"]

def test_failed_import_cleans_file(client, monkeypatch):
    monkeypatch.setenv("TSI_LINK_RESOLVER_URL", "https://resolver.example/resolve")
    monkeypatch.setenv("TSI_LINK_MEDIA_HOSTS", "media.example")
    monkeypatch.setattr(links, "resolve", lambda source: "https://media.example/video.mp4")
    def broken(url, target):
        target.write_bytes(b"partial")
        raise links.LinkError("Platform access unavailable.")
    monkeypatch.setattr(links, "download", broken)
    response = client.post("/v1/analyses/from-link", json={"url":"https://youtu.be/abcdefghijk", "metadata":META})
    assert response.status_code == 422
    item = store.get(response.json()["detail"]["job_id"])
    assert item["status"] == "failed"
    assert not (config.DATA / f"{item['id']}.mp4").exists()
    assert store.claim() is None
