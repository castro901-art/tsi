"""Real local auth/session regression checks. No live account or provider requests."""
import os
from pathlib import Path
import pytest
from test_studio import studio, register, assert_layout, playwright


def screenshot(page, name):
    output = Path(os.getenv("TSI_TEST_ARTIFACTS", "/home/user/tsi-auth-redesign/screenshots"))
    output.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(output / f"{name}.png"), full_page=True)


@pytest.mark.parametrize("width", [360, 390, 768, 1440])
def test_auth_layout_registration_signin_signout_and_restore(studio, width):
    page, base, tmp_path, errors = studio
    page.set_viewport_size({"width": width, "height": 900})
    external = []
    page.on("request", lambda req: external.append(req.url) if req.url.startswith("http") and not req.url.startswith(base + "/") else None)
    page.goto(base + "/studio")
    playwright.expect(page.locator("#auth-submit")).to_be_enabled()
    page.wait_for_function("document.querySelector('.auth-emblem').complete && document.querySelector('.auth-emblem').naturalWidth === 512")
    assert page.locator("#auth-title").inner_text() == "Sign in"
    assert page.locator("#auth-description").inner_text() == "Continue to your match analyses."
    assert page.locator("#auth-password").get_attribute("type") == "password"
    assert page.locator("#hero").is_hidden()
    assert page.locator("body > header").is_hidden()
    assert page.locator("#register").is_visible()
    assert page.locator("#workspace").is_hidden()
    assert page.locator("#auth").evaluate("el => getComputedStyle(el).gridTemplateColumns.split(' ').length") == (1 if width <= 800 else 2)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert page.locator("#auth-form input").first.bounding_box()["height"] == 44
    assert page.locator("#auth").evaluate("el => getComputedStyle(el).borderTopWidth") == "0px"
    assert page.locator("#auth-name").evaluate("el => el.labels[0].textContent") == "Username"
    page.locator("#auth-name").focus()
    assert page.locator("#auth-name").evaluate("el => getComputedStyle(el).outlineStyle") == "solid"
    page.keyboard.press("Tab")
    assert page.locator("#auth-password").evaluate("el => el === document.activeElement")
    screenshot(page, f"signin-{width}")
    page.locator("#register").click()
    playwright.expect(page).to_have_url(base + "/studio/register")
    playwright.expect(page.locator("#auth-submit")).to_be_enabled()
    assert page.locator("#auth-title").inner_text() == "Create your account"
    assert page.locator("#password-requirements").is_visible()
    assert page.locator("#username-requirements").is_visible()
    assert page.locator("#auth-password").get_attribute("autocomplete") == "new-password"
    assert page.locator("#register").is_hidden()
    assert page.locator("#back-to-sign-in").is_visible()
    assert page.locator('input[name="confirm_password"]').count() == 0
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    screenshot(page, f"registration-{width}")
    page.locator("#auth-name").fill("analyst")
    page.locator("#auth-password").fill("test-password-1234")
    page.locator("#auth-submit").click()
    playwright.expect(page.locator("#workspace")).to_be_visible()
    playwright.expect(page.locator("#start")).to_be_enabled()
    assert page.locator("#auth-password").input_value() == ""
    assert page.locator("#auth").is_hidden()
    assert_layout(page, width)
    screenshot(page, f"signed-in-{width}")
    page.reload()
    playwright.expect(page.locator("#workspace")).to_be_visible()
    page.locator("#logout").click()
    playwright.expect(page.locator("#auth")).to_be_visible()
    playwright.expect(page.locator("#workspace")).to_be_hidden()
    assert page.request.get(base + "/v1/auth/me").status == 401
    page.locator("#auth-name").fill("analyst")
    page.locator("#auth-password").fill("test-password-1234")
    page.locator("#auth-submit").click()
    playwright.expect(page.locator("#workspace")).to_be_visible()
    assert not external


def test_invalid_credentials_and_private_server_errors_are_sanitized(studio):
    page, base, tmp_path, errors = studio
    register(page, base)
    page.locator("#logout").click()
    playwright.expect(page.locator("#auth")).to_be_visible()
    page.locator("#auth-name").fill("analyst")
    page.locator("#auth-password").fill("wrong-password-1234")
    page.locator("#auth-submit").click()
    playwright.expect(page.locator("#auth-error")).to_contain_text("username or password is incorrect")
    assert page.locator("#auth-password").input_value() == ""
    assert page.request.get(base + "/v1/auth/me").status == 401
    page.route("**/v1/auth/login", lambda route: route.fulfill(status=500, json={"detail": "SECRET database path and stack trace"}))
    page.locator("#auth-password").fill("test-password-1234")
    page.locator("#auth-submit").click()
    playwright.expect(page.locator("#auth-error")).to_contain_text("temporarily unavailable")
    assert "SECRET" not in page.locator("body").inner_text()
    assert page.locator("#workspace").is_hidden()


def test_validation_and_duplicate_submissions(studio):
    page, base, tmp_path, errors = studio
    page.goto(base + "/studio/register")
    playwright.expect(page.locator("#auth-submit")).to_be_enabled()
    writes = []
    page.on("request", lambda req: writes.append(req) if req.method == "POST" and "/v1/auth/" in req.url else None)
    page.locator("#auth-name").fill("Invalid Name")
    page.locator("#auth-password").fill("short")
    page.locator("#auth-submit").click()
    playwright.expect(page.locator("#auth-error")).to_contain_text("3–40")
    page.locator("#auth-name").fill("analyst")
    page.locator("#auth-submit").click()
    playwright.expect(page.locator("#auth-error")).to_contain_text("12–128")
    assert not writes
    page.locator("#auth-password").fill("test-password-1234")
    page.evaluate("""() => { const original = window.fetch; window.fetch = (url, options) =>
      url === '/v1/auth/register' && options?.method === 'POST'
      ? new Promise(resolve => { window.releaseRegister = () => resolve(original(url, options)); })
      : original(url, options); }""")
    page.locator("#auth-submit").click()
    assert page.locator("#auth-form").get_attribute("aria-busy") == "true"
    assert page.locator("#auth-submit").inner_text() == "Creating account…"
    assert page.locator("#auth-name").is_disabled()
    page.dispatch_event("#auth-form", "submit")
    page.evaluate("window.releaseRegister()")
    playwright.expect(page.locator("#workspace")).to_be_visible()
    assert len(writes) == 1
    assert set(writes[0].post_data_json) == {"username", "password"}


@pytest.mark.parametrize("enabled", ["true", "false"])
def test_server_presentation_respects_registration_setting(monkeypatch, enabled):
    from fastapi.testclient import TestClient
    from api.main import app
    monkeypatch.setenv("TSI_REGISTRATION_ENABLED", enabled)
    with TestClient(app) as client:
        response = client.get("/studio")
        assert response.status_code == 200
        assert f'data-registration-enabled="{enabled}"' in response.text
        assert response.headers["cache-control"] == "no-store"
        result = client.get("/studio/register", follow_redirects=False)
        if enabled == "true":
            assert result.status_code == 200
            assert 'data-auth-mode="register"' in result.text
        else:
            assert result.status_code == 303
            assert result.headers["location"] == "/studio"
        assert result.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("width", [360, 1440])
@pytest.mark.parametrize("studio", [{"registration_enabled": "false"}], indirect=True)
def test_registration_disabled_in_real_browser_but_signin_still_works(studio, width):
    from uuid import uuid4
    import time
    from api import store
    from api.auth import hasher
    page, base, tmp_path, errors = studio
    with store.connection() as db:
        db.execute("INSERT INTO users(id,username,password_hash,created) VALUES(?,?,?,?)",
                   (str(uuid4()), "existing_analyst", hasher.hash("test-password-1234"), time.time()))
    page.set_viewport_size({"width": width, "height": 900})
    page.goto(base + "/studio")
    playwright.expect(page.locator("#auth-submit")).to_be_enabled()
    assert page.locator("#register").is_hidden()
    assert page.locator("#back-to-sign-in").is_hidden()
    screenshot(page, f"signin-registration-disabled-{width}")
    page.goto(base + "/studio/register")
    playwright.expect(page).to_have_url(base + "/studio")
    assert page.locator("#auth-title").inner_text() == "Sign in"
    assert page.request.post(base + "/v1/auth/register", data={"username": "new_user", "password": "test-password-1234"}).status == 403
    page.locator("#auth-name").fill("existing_analyst")
    page.locator("#auth-password").fill("test-password-1234")
    page.locator("#auth-submit").click()
    playwright.expect(page.locator("#workspace")).to_be_visible()
    assert_layout(page, width)
    page.locator("#logout").click()
    playwright.expect(page.locator("#auth")).to_be_visible()
    assert page.locator("#register").is_hidden()


def test_duplicate_signin_and_signout_are_blocked(studio):
    page, base, tmp_path, errors = studio
    register(page, base)
    page.locator("#logout").click()
    playwright.expect(page.locator("#auth")).to_be_visible()
    page.locator("#auth-name").fill("analyst")
    page.locator("#auth-password").fill("test-password-1234")
    writes = []
    page.on("request", lambda req: writes.append(req.url) if req.method == "POST" and "/v1/auth/" in req.url else None)
    page.evaluate("""() => {const original = window.fetch; window.fetch = (url, options) =>
      ['/v1/auth/login','/v1/auth/logout'].includes(url) && options?.method === 'POST'
      ? new Promise(resolve => { window.releaseAuth = () => resolve(original(url, options)); }) : original(url, options); }""")
    page.locator("#auth-submit").click()
    assert page.locator("#auth-submit").inner_text() == "Signing in…"
    assert page.locator("#auth-submit").is_disabled()
    page.dispatch_event("#auth-form", "submit")
    page.evaluate("window.releaseAuth()")
    playwright.expect(page.locator("#workspace")).to_be_visible()
    assert len(writes) == 1
    page.locator("#logout").click()
    assert page.locator("#logout").inner_text() == "Signing out…"
    assert page.locator("#logout").is_disabled()
    page.dispatch_event("#logout", "click")
    page.evaluate("window.releaseAuth()")
    playwright.expect(page.locator("#auth")).to_be_visible()
    assert len(writes) == 2
