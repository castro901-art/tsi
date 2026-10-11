"""Dashboard regressions on the isolated real API, with no platform/provider calls."""
from test_studio import studio, register, upload_form, source_video, playwright


def test_link_mode_configuration_and_switch_back(studio):
    page, base, tmp_path, errors = studio
    register(page, base)
    page.locator('[data-source-mode="link"]').click()
    playwright.expect(page.locator('#source-link')).to_be_visible()
    playwright.expect(page.locator('#link-note')).to_contain_text('operator-configured')
    page.locator('input[name="title"]').fill('TEST link import')
    page.locator('#source-link').fill('https://youtu.be/abcdefghijk')
    page.locator('input[name="authorised"]').check()
    page.locator('input[name="provider_processing_consent"]').check()
    page.locator('#start').click()
    playwright.expect(page.locator('#notice')).to_contain_text('not configured')
    playwright.expect(page.locator('#inputs')).to_be_enabled()
    assert page.request.get(base + '/v1/analyses').json() == []
    page.locator('[data-source-mode="file"]').click()
    playwright.expect(page.locator('#file')).to_be_visible()
    upload_form(page, source_video(tmp_path))
    page.locator('#start').click()
    playwright.expect(page.locator('#status')).to_contain_text('Queued')


def test_match_titles_search_and_safe_rendering(studio):
    page, base, tmp_path, errors = studio
    register(page, base)
    upload_form(page, source_video(tmp_path))
    title = 'TEST ONLY <script>unsafe()</script>'
    page.locator('input[name="title"]').fill(title)
    page.locator('#start').click()
    playwright.expect(page.locator('#analyses .match-title')).to_have_text(title)
    page.locator('#match-search').fill('no-such-match')
    playwright.expect(page.locator('#search-empty')).to_be_visible()
    page.locator('#match-search').fill('TEST ONLY')
    playwright.expect(page.locator('#analyses button')).to_be_visible()
    page.locator('#logout').click()
    playwright.expect(page.locator('#workspace')).to_be_hidden()
    assert page.locator('#match-search').input_value() == ''
