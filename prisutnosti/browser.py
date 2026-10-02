"""Browser lifetime shared by all interactive commands."""

import logging
from contextlib import contextmanager
from collections.abc import Iterator

from playwright.sync_api import Page, sync_playwright

logger = logging.getLogger(__name__)


@contextmanager
def browser_page() -> Iterator[Page]:
    logger.info("Starting Microsoft Edge")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=False)
        try:
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            page.set_default_timeout(30_000)
            logger.info("Browser context ready")
            yield page
        finally:
            logger.info("Closing Microsoft Edge")
            browser.close()
