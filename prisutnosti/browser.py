"""Browser lifetime shared by all interactive commands."""
from contextlib import contextmanager
from collections.abc import Iterator

from playwright.sync_api import Page, sync_playwright


@contextmanager
def browser_page() -> Iterator[Page]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=False)
        try:
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            page.set_default_timeout(30_000)
            yield page
        finally:
            browser.close()
