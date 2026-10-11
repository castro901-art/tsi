"""Isolated Chromium checks against the real local API; no live provider calls.
Run with requirements-e2e.txt and `python -m playwright install chromium`.
"""
import os
import hashlib
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

import pytest
from api import config, store
from api.schemas import Findings
from api.worker import process

playwright = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def studio(tmp_path, monkeypatch, request):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    base = f"http://127.0.0.1:{port}"
    data = tmp_path / "data"
    monkeypatch.setattr(config, "DATA", data)
    env = {**os.environ, "TSI_DATA_DIR": str(data), "TSI_COOKIE_SECURE": "false",
           "TSI_REGISTRATION_ENABLED": getattr(request, "param", {}).get("registration_enabled", "true"), "TSI_APP_ORIGIN": base,
           "GEMINI_API_KEY": "test-placeholder-never-sent", "TSI_GEMINI_MODEL": "test-model",
           "TSI_PROVIDER_TERMS_ACCEPTED": "true"}
    log = (tmp_path / "api.log").open("w")
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "api.main:app",
                               "--host", "127.0.0.1", "--port", str(port)], cwd=ROOT,
                              env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        for _ in range(100):
            try:
                with urllib.request.urlopen(base + "/health", timeout=1):
                    break
            except Exception:
                if server.poll() is not None:
                    pytest.fail((tmp_path / "api.log").read_text())
                time.sleep(.1)
        else:
            pytest.fail("Local test API did not start")
        with playwright.sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context()
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            yield page, base, tmp_path, errors
            context.close()
            browser.close()
        assert not errors, errors
    finally:
        server.terminate()
        server.wait(timeout=10)
        log.close()


def register(page, base):
    page.goto(base + "/studio/register")
    page.locator("#auth-name").fill("analyst")
    page.locator("#auth-password").fill("test-password-1234")
    page.locator("#auth-submit").click()
    playwright.expect(page.locator("#workspace")).to_be_visible()
    playwright.expect(page.locator("#start")).to_be_enabled()


def upload_form(page, video):
    page.locator('input[name="title"]').fill("TEST FIXTURE — not football analysis")
    page.locator("#file").set_input_files(str(video))
    page.locator('input[name="authorised"]').check()
    page.locator('input[name="provider_processing_consent"]').check()


def source_video(tmp_path):
    video = tmp_path / "fixture.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=green:s=64x64:d=2",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video)], check=True)
    return video


def assert_layout(page, width):
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), f"Horizontal overflow at {width}"
    for button in page.locator("button:visible").all():
        box = button.bounding_box()
        assert box["height"] >= 44
    columns = page.locator(".workspace-grid").evaluate("el => getComputedStyle(el).gridTemplateColumns.split(' ').length")
    assert columns == (1 if width <= 800 else 2)


@pytest.mark.parametrize("width", [360, 390, 768, 1440])
def test_responsive_real_upload_and_evidence(studio, width):
    page, base, tmp_path, errors = studio
    page.set_viewport_size({"width": width, "height": 900})
    register(page, base)
    assert_layout(page, width)
    video = source_video(tmp_path)
    upload_form(page, video)
    writes = []
    page.on("request", lambda r: writes.append(r) if r.method in ("POST", "PUT") and "/v1/analyses" in r.url else None)
    page.locator("#start").click()
    playwright.expect(page.locator("#status")).to_contain_text("Queued")
    playwright.expect(page.locator("#results")).to_be_hidden()
    assert len(writes) == 2
    assert writes[0].headers.get("x-tsi-csrf")
    assert writes[1].headers.get("content-type") == "video/mp4"
    assert writes[1].headers.get("x-tsi-csrf")
    job_id = page.locator("#job-id").inner_text().split(": ")[-1]
    assert store.get(job_id)["status"] == "queued"
    assert store.get(job_id)["sha256"] == hashlib.sha256(video.read_bytes()).hexdigest()
    assert store.claim() == job_id
    page.locator("#retry").click()
    playwright.expect(page.locator("#status")).to_contain_text("Processing")
    playwright.expect(page.locator("#events-panel")).to_be_hidden()

    class TestProvider:
        model = "TEST DOUBLE — no live provider"
        def analyse(self, path):
            return Findings.model_validate({"events": [{"event_type": "other", "start_seconds": .5,
                "end_seconds": 1, "observation": "TEST ONLY <script>window.injected=true</script>", "confidence": .4}],
                "interpretations": [{"section": "attacking", "text": "TEST ONLY interpretation", "event_indices": [0]}],
                "limitations": ["Synthetic test fixture, not representative football footage."]})

    process(job_id, TestProvider())
    page.locator("#retry").click()
    playwright.expect(page.locator("#results")).to_be_visible()
    playwright.expect(page.locator("#events")).to_contain_text("TEST ONLY <script>")
    assert page.evaluate("window.injected") is None
    assert page.locator("#interpretations button").count() == 1
    playwright.expect(page.locator("#limitations")).to_contain_text("not human-verified")
    page.locator("#events button").first.click()
    page.wait_for_function("document.getElementById('video').currentTime >= 0.49")
    with page.expect_download() as download:
        page.locator("#report").click()
    report = Path(download.value.path()).read_text()
    assert "TEST ONLY" in report and "not human-verified" in report
    assert_layout(page, width)
    output = Path(os.getenv("TSI_TEST_ARTIFACTS", str(tmp_path / "screenshots")))
    output.mkdir(exist_ok=True)
    page.screenshot(path=str(output / f"studio-{width}.png"), full_page=True)
    page.reload()
    playwright.expect(page.locator("#analyses button")).to_have_count(1)
    page.locator("#analyses button").click()
    playwright.expect(page.locator("#results")).to_be_visible()
    page.locator("#logout").click()
    playwright.expect(page.locator("#workspace")).to_be_hidden()
    assert page.locator("#events").inner_text() == ""
    page.locator("#auth-name").fill("analyst")
    page.locator("#auth-password").fill("test-password-1234")
    page.locator('#auth-form button[type="submit"]').first.click()
    playwright.expect(page.locator("#analyses button")).to_have_count(1)


def test_validation_and_server_upload_failure(studio):
    page, base, tmp_path, errors = studio
    register(page, base)
    bad = tmp_path / "invalid.mp4"
    bad.write_bytes(b"not video")
    upload_form(page, bad)
    page.locator("#start").click()
    playwright.expect(page.locator("#status")).to_contain_text("Failed")
    playwright.expect(page.locator("#job-error")).to_contain_text("Server error:")
    playwright.expect(page.locator("#results")).to_be_hidden()
    playwright.expect(page.locator("#notice")).to_contain_text("Video validation failed")
    assert not page.locator("#report").get_attribute("href")


@pytest.mark.parametrize("code", ["provider_quota_exhausted", "provider_access_denied", "provider_timeout", "interrupted"])
def test_worker_errors_are_not_results(studio, code):
    page, base, tmp_path, errors = studio
    register(page, base)
    user = page.request.get(base + "/v1/auth/me").json()["user"]
    job = store.create({"title": "TEST failed", "authorised": True, "provider_processing_consent": True}, user["id"])
    store.transition(job, "awaiting_upload", "failed", error=code)
    page.locator("#refresh").click()
    page.locator("#analyses button").click()
    playwright.expect(page.locator("#job-error")).to_contain_text(code)
    playwright.expect(page.locator("#results")).to_be_hidden()
    playwright.expect(page.locator("#video")).to_be_hidden()


def test_create_configuration_error_and_capability_retry(studio):
    page, base, tmp_path, errors = studio
    page.route("**/v1/capabilities", lambda route: route.abort())
    page.goto(base + "/studio/register")
    page.locator("#auth-name").fill("analyst")
    page.locator("#auth-password").fill("test-password-1234")
    page.locator("#auth-submit").click()
    playwright.expect(page.locator("#limits")).to_contain_text("Uploads are disabled")
    playwright.expect(page.locator("#start")).to_be_disabled()
    page.unroute("**/v1/capabilities")
    page.locator("#refresh").click()
    playwright.expect(page.locator("#start")).to_be_enabled()
    page.route("**/v1/analyses", lambda route: route.fulfill(status=503, json={"detail": {"code": "provider_not_configured", "message": "Provider not configured"}}) if route.request.method == "POST" else route.continue_())
    upload_form(page, source_video(tmp_path))
    page.locator("#start").click()
    playwright.expect(page.locator("#notice")).to_contain_text("provider_not_configured")
    playwright.expect(page.locator("#review")).to_be_hidden()


def test_awaiting_upload_resume_and_network_recovery(studio):
    page, base, tmp_path, errors = studio
    register(page, base)
    user = page.request.get(base + "/v1/auth/me").json()["user"]
    job = store.create({"title": "TEST resume", "authorised": True, "provider_processing_consent": True}, user["id"])
    page.locator("#refresh").click()
    page.locator("#analyses button").click()
    playwright.expect(page.locator("#resume")).to_be_visible()
    upload_form(page, source_video(tmp_path))
    page.locator("#resume-upload").click()
    playwright.expect(page.locator("#status")).to_contain_text("Queued")
    page.route(f"**/v1/analyses/{job}", lambda route: route.abort())
    page.locator("#retry").click()
    playwright.expect(page.locator("#status")).to_contain_text("state unavailable")
    playwright.expect(page.locator("#results")).to_be_hidden()
    page.unroute(f"**/v1/analyses/{job}")
    page.locator("#retry").click()
    playwright.expect(page.locator("#status")).to_contain_text("Queued")


def test_session_expiry_clears_private_ui(studio):
    page, base, tmp_path, errors = studio
    register(page, base)
    user = page.request.get(base + "/v1/auth/me").json()["user"]
    job = store.create({"title": "TEST expiry", "authorised": True, "provider_processing_consent": True}, user["id"])
    page.locator("#refresh").click()
    page.locator("#analyses button").click()
    playwright.expect(page.locator("#resume")).to_be_visible()
    with store.connection() as db:
        db.execute("UPDATE sessions SET expires=0")
    page.locator("#retry").click()
    playwright.expect(page.locator("#workspace")).to_be_hidden()
    playwright.expect(page.locator("#auth")).to_be_visible()
    assert page.locator("#analyses").inner_text() == ""
    playwright.expect(page.locator("#notice")).to_contain_text("session expired")


@pytest.mark.parametrize("status", ["unknown_state", "completed"])
def test_unknown_state_and_missing_results_do_not_fabricate(studio, status):
    page, base, tmp_path, errors = studio
    register(page, base)
    user = page.request.get(base + "/v1/auth/me").json()["user"]
    job = store.create({"title": "TEST missing result", "authorised": True, "provider_processing_consent": True}, user["id"])
    store.transition(job, "awaiting_upload", status)
    page.locator("#refresh").click()
    page.locator("#analyses button").click()
    playwright.expect(page.locator("#results")).to_be_hidden()
    assert not page.locator("#report").get_attribute("href")
    if status == "completed":
        playwright.expect(page.locator("#job-error")).to_contain_text("No sample results were substituted")
    else:
        playwright.expect(page.locator("#status")).to_contain_text("Unknown server state")


def test_studio_routes_only_expose_public_assets():
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    for path in ("/studio", "/studio/"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert 'name="viewport"' in response.text
    assert client.get("/studio/assets/studio.js").status_code == 200
    assert client.get("/studio/assets/studio.css").status_code == 200
    assert client.get("/studio/assets/private-data/tsi.sqlite3").status_code == 404
    assert client.get("/studio/assets/%2E%2E/api/auth.py").status_code == 404
