"""Indeed.com 爬虫 (基础版)."""
import logging
import random
import time
from urllib.parse import quote_plus

from playwright.sync_api import Page, sync_playwright

from backend.app.scrapers import ScrapedJob

logger = logging.getLogger(__name__)


def _delay(min_s: float = 2.0, max_s: float = 5.0) -> None:
    time.sleep(random.uniform(min_s, max_s))


def _safe_text(page: Page, selector: str, default: str = "") -> str:
    try:
        el = page.query_selector(selector)
        return el.inner_text().strip() if el else default
    except Exception:
        return default


class IndeedScraper:
    BASE = "https://au.indeed.com"

    def scrape(
        self,
        target_roles: list[str],
        locations: list[str],
        max_per_query: int = 10,
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
                location = locations[0] if locations else "Australia"
                job_urls = self._search(page, role, location, max_per_query, existing_urls)
                for url in job_urls:
                    try:
                        job = self._fetch_job(page, url)
                        if job:
                            results.append(job)
                            existing_urls.add(url)
                    except Exception as e:
                        logger.error("[Indeed] Failed to fetch %s: %s", url, e)
                    _delay(2.0, 5.0)

            browser.close()

        return results

    def _search(self, page: Page, role: str, location: str, max_jobs: int, existing_urls: set[str]) -> list[str]:
        search_url = (
            f"{self.BASE}/jobs?q={quote_plus(role)}"
            f"&l={quote_plus(location)}"
            f"&sort=date&fromage=7"
        )
        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=30_000)
            _delay(1.5, 3.0)
        except Exception as e:
            logger.error("[Indeed] Search failed for '%s': %s", role, e)
            return []

        urls: list[str] = []
        links = page.query_selector_all("a.jcs-JobTitle")
        for link in links:
            if len(urls) >= max_jobs:
                break
            href = link.get_attribute("href") or ""
            if not href:
                continue
            if href.startswith("/"):
                href = self.BASE + href
            href = href.split("?")[0]
            if href not in existing_urls and href not in urls:
                urls.append(href)

        return urls

    def _fetch_job(self, page: Page, url: str) -> ScrapedJob | None:
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        _delay(1.0, 2.5)

        title = _safe_text(page, "h1.jobsearch-JobInfoHeader-title")
        company = _safe_text(page, "[data-company-name='true']") or _safe_text(page, ".jobsearch-InlineCompanyRating-companyHeader")
        location = _safe_text(page, "[data-testid='job-location']") or _safe_text(page, ".jobsearch-JobInfoHeader-subtitle span")

        jd_el = page.query_selector("#jobDescriptionText") or page.query_selector(".jobsearch-jobDescriptionText")
        if not jd_el:
            return None

        raw_jd = jd_el.inner_text().strip()
        if not raw_jd or len(raw_jd) < 100:
            return None

        return ScrapedJob(url=url, raw_jd=raw_jd, title=title, company=company, location=location)
