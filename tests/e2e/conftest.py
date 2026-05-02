"""Playwright E2E fixtures.

Tests in this folder run from the host (not inside the Docker web container)
and target http://localhost:8000 by default. The Django app must be running
locally (e.g. `make dev` or `docker compose up`).

Usage:
    pytest tests/e2e -v

Set E2E_APP_URL to point at a different host (e.g. ngrok tunnel for LS webhook tests).
"""

from __future__ import annotations

import os

import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="session")
def app_url() -> str:
    return os.environ.get("E2E_APP_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as p:
        yield p


@pytest.fixture()
def browser(playwright_instance):
    browser = playwright_instance.chromium.launch(
        headless=os.environ.get("E2E_HEADED", "0") != "1",
    )
    yield browser
    browser.close()


@pytest.fixture()
def page(browser):
    context = browser.new_context(
        record_video_dir="tests/e2e/artifacts/videos",
        viewport={"width": 1280, "height": 800},
    )
    p = context.new_page()
    yield p
    context.close()
