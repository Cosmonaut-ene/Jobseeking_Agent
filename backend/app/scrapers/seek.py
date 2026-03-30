"""Seek.com.au 全自动爬虫."""
import logging
import random
import re
import time

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from backend.app.scrapers import ScrapedJob

logger = logging.getLogger(__name__)


def _delay(min_s: float = 2.0, max_s: float = 6.0) -> None:
    time.sleep(random.uniform(min_s, max_s))


def _safe_text(page: Page, selector: str, default: str = "") -> str:
    try:
        el = page.query_selector(selector)
        return el.inner_text().strip() if el else default
    except Exception:
        return default


class SeekScraper:
    BASE = "https://www.seek.com.au"

    def scrape(
        self,
        target_roles: list[str],
        locations: list[str],
        max_per_query: int = 15,
        existing_urls: set[str] | None = None,
    ) -> list[ScrapedJob]:
        existing_urls = existing_urls or set()
        results: list[ScrapedJob] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 900},
            )
            page = ctx.new_page()

            for role in target_roles:
                location = locations[0] if locations else "All Australia"
                job_urls = self._search(page, role, location, max_per_query, existing_urls)
                for url in job_urls:
                    try:
                        job = self._fetch_job(page, url)
                        if job:
                            results.append(job)
                            existing_urls.add(url)
                    except Exception as e:
                        logger.warning("[Seek] Failed to fetch %s after retries: %s", url, e)
                    _delay(2.5, 6.0)

            browser.close()

        return results

    @staticmethod
    def _to_slug(text: str) -> str:
        """Convert text to SEEK URL slug (lowercase, spaces/special chars → hyphens)."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)      # remove punctuation except hyphens
        text = re.sub(r"[\s_]+", "-", text)        # spaces → hyphens
        text = re.sub(r"-+", "-", text).strip("-") # collapse multiple hyphens
        return text

    def _build_search_url(self, role: str, location: str) -> str:
        """Build SEEK path-based search URL.

        Example: developer + Sydney NSW
          → https://www.seek.com.au/developer-jobs/in-All-Sydney-NSW/full-time?daterange=7&sortmode=ListedDate
        """
        role_slug = self._to_slug(role)
        loc_slug = self._to_slug(location)
        return (
            f"{self.BASE}/{role_slug}-jobs/in-All-{loc_slug}/full-time"
            f"?daterange=7&sortmode=ListedDate"
        )

    def _search(self, page: Page, role: str, location: str, max_jobs: int, existing_urls: set[str]) -> list[str]:
        search_url = self._build_search_url(role, location)
        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=30_000)
            _delay(1.5, 3.0)
        except Exception as e:
            logger.warning("[Seek] Search page load failed for %r: %s", role, e)
            return []

        urls: list[str] = []
        links = page.query_selector_all("a[data-automation='jobTitle']")
        for link in links:
            if len(urls) >= max_jobs:
                break
            href = link.get_attribute("href") or ""
            if not href.startswith("/job/"):
                continue
            full_url = self.BASE + href.split("?")[0]
            if full_url not in existing_urls:
                urls.append(full_url)

        return urls

    @retry(
        retry=retry_if_exception_type(PlaywrightTimeoutError),
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=3, max=10),
        reraise=True,
    )
    def _fetch_job(self, page: Page, url: str) -> ScrapedJob | None:
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        _delay(1.0, 2.5)

        title    = _safe_text(page, "[data-automation='job-detail-title']")
        company  = _safe_text(page, "[data-automation='advertiser-name']")
        location = _safe_text(page, "[data-automation='job-detail-location']")
        salary   = _safe_text(page, "[data-automation='job-detail-salary']")
        jd_el    = page.query_selector("[data-automation='jobAdDetails']")

        if not jd_el:
            return None

        raw_jd = jd_el.inner_text().strip()
        if not raw_jd or len(raw_jd) < 100:
            return None

        return ScrapedJob(url=url, raw_jd=raw_jd, title=title, company=company, location=location, salary=salary)
