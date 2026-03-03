"""
LinkedIn 全自动爬虫 — Cookie + Playwright。

首次使用：
  1. 用户在浏览器登录 LinkedIn，导出 cookies 为 JSON 格式
  2. 保存到 data/cookies/linkedin.json
  3. 系统自动加载 cookies 保持登录状态

格式示例 (Netscape/EditThisCookie 格式):
[{"name": "li_at", "value": "...", "domain": ".linkedin.com", ...}, ...]
"""
import json
import logging
import random
import time
from pathlib import Path
from urllib.parse import quote_plus

from playwright.sync_api import BrowserContext, Page, sync_playwright

from backend.app.scrapers import ScrapedJob
from backend.app.config import COOKIES_DIR

logger = logging.getLogger(__name__)
COOKIES_FILE = COOKIES_DIR / "linkedin.json"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]


def _delay(min_s: float = 3.0, max_s: float = 8.0) -> None:
    time.sleep(random.uniform(min_s, max_s))


def _safe_text(page: Page, selector: str, default: str = "") -> str:
    try:
        el = page.query_selector(selector)
        return el.inner_text().strip() if el else default
    except Exception:
        return default


def _load_cookies(cookies_file: Path) -> list[dict]:
    """Load cookies from JSON file."""
    if not cookies_file.exists():
        logger.warning("[LinkedIn] Cookies file not found: %s", cookies_file)
        return []
    try:
        data = json.loads(cookies_file.read_text(encoding="utf-8"))
        # Ensure required fields
        cookies = []
        for c in data:
            cookie = {
                "name": c["name"],
                "value": c["value"],
                "domain": c.get("domain", ".linkedin.com"),
                "path": c.get("path", "/"),
            }
            if "secure" in c:
                cookie["secure"] = c["secure"]
            if "httpOnly" in c:
                cookie["httpOnly"] = c["httpOnly"]
            cookies.append(cookie)
        return cookies
    except Exception as e:
        logger.error("[LinkedIn] Failed to load cookies: %s", e)
        return []


class LinkedInAutoScraper:
    """Cookie-based LinkedIn auto-scraper."""

    BASE = "https://www.linkedin.com"

    def __init__(self, cookies_path: Path | None = None) -> None:
        self.cookies_path = cookies_path or COOKIES_FILE
        self.cookies = _load_cookies(self.cookies_path)

    @property
    def has_cookies(self) -> bool:
        return len(self.cookies) > 0

    def scrape_search(
        self,
        keywords: list[str],
        location: str,
        max_results: int = 25,
        existing_urls: set[str] | None = None,
    ) -> list[ScrapedJob]:
        """Auto-search LinkedIn jobs and scrape results."""
        existing_urls = existing_urls or set()
        results: list[ScrapedJob] = []

        if not self.cookies:
            logger.warning("[LinkedIn] No cookies loaded — scraping without auth (limited results).")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            ctx = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1280, "height": 900},
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )

            # Inject cookies for authenticated session
            if self.cookies:
                try:
                    ctx.add_cookies(self.cookies)
                    logger.info("[LinkedIn] Loaded %d cookies", len(self.cookies))
                except Exception as e:
                    logger.error("[LinkedIn] Failed to set cookies: %s", e)

            page = ctx.new_page()
            # Hide automation markers
            page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            for keyword in keywords:
                if len(results) >= max_results:
                    break
                job_urls = self._search(page, keyword, location, max_results, existing_urls)
                for url in job_urls:
                    if len(results) >= max_results:
                        break
                    try:
                        job = self._fetch_job(page, url)
                        if job:
                            results.append(job)
                            existing_urls.add(url)
                    except Exception as e:
                        logger.error("[LinkedIn] Failed to fetch %s: %s", url, e)
                    _delay(3.0, 8.0)

            browser.close()

        logger.info("[LinkedIn] Scraped %d jobs", len(results))
        return results

    def scrape_urls(
        self,
        urls: list[str],
        existing_urls: set[str] | None = None,
    ) -> list[ScrapedJob]:
        """Scrape specific LinkedIn job URLs (fallback for manual URL input)."""
        existing_urls = existing_urls or set()
        new_urls = [u for u in urls if u.strip() and u not in existing_urls]

        if not new_urls:
            return []

        results: list[ScrapedJob] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1280, "height": 900},
            )
            if self.cookies:
                try:
                    ctx.add_cookies(self.cookies)
                except Exception:
                    pass

            page = ctx.new_page()
            page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            for url in new_urls:
                try:
                    job = self._fetch_job(page, url)
                    if job:
                        results.append(job)
                except Exception as e:
                    logger.error("[LinkedIn] Failed to fetch %s: %s", url, e)
                _delay(4.0, 9.0)

            browser.close()

        return results

    def _search(
        self, page: Page, keyword: str, location: str, max_jobs: int, existing_urls: set[str]
    ) -> list[str]:
        """Search LinkedIn jobs and return job URLs."""
        search_url = (
            f"{self.BASE}/jobs/search/"
            f"?keywords={quote_plus(keyword)}"
            f"&location={quote_plus(location)}"
            f"&f_TPR=r604800"  # posted in last 7 days
            f"&sortBy=DD"      # sort by date
        )
        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=30_000)
            _delay(2.0, 4.0)
        except Exception as e:
            logger.error("[LinkedIn] Search failed for '%s': %s", keyword, e)
            return []

        # Try to expand "Show more" to load more results
        for _ in range(2):
            try:
                btn = page.query_selector("button.infinite-scroller__show-more-button")
                if btn:
                    btn.click()
                    _delay(1.0, 2.0)
            except Exception:
                break

        urls: list[str] = []
        # Job cards use various selectors depending on auth state
        selectors = [
            "a.job-card-list__title",
            "a.job-card-container__link",
            "a[data-tracking-control-name='public_jobs_jserp-result_search-card']",
            ".jobs-search__results-list li a",
            "a[href*='/jobs/view/']",
        ]
        for sel in selectors:
            links = page.query_selector_all(sel)
            for link in links:
                if len(urls) >= max_jobs:
                    break
                href = link.get_attribute("href") or ""
                if "/jobs/view/" not in href:
                    continue
                clean = href.split("?")[0].rstrip("/")
                if not clean.startswith("http"):
                    clean = self.BASE + clean
                if clean not in existing_urls and clean not in urls:
                    urls.append(clean)
            if urls:
                break

        logger.info("[LinkedIn] Found %d URLs for '%s'", len(urls), keyword)
        return urls

    def _fetch_job(self, page: Page, url: str) -> ScrapedJob | None:
        clean_url = url.split("?")[0].rstrip("/")
        page.goto(clean_url, wait_until="domcontentloaded", timeout=30_000)
        _delay(1.5, 3.0)

        # Try authenticated view first, then fall back to public view
        title = (
            _safe_text(page, ".job-details-jobs-unified-top-card__job-title")
            or _safe_text(page, "h1.top-card-layout__title")
            or _safe_text(page, "h1")
        )
        company = (
            _safe_text(page, ".job-details-jobs-unified-top-card__company-name")
            or _safe_text(page, "a.topcard__org-name-link")
            or _safe_text(page, "span.topcard__org-name-link")
        )
        location = (
            _safe_text(page, ".job-details-jobs-unified-top-card__bullet")
            or _safe_text(page, "span.topcard__flavor--bullet")
        )

        # JD selectors for both auth and public views
        jd_el = (
            page.query_selector(".jobs-description__content")
            or page.query_selector(".show-more-less-html__markup")
            or page.query_selector(".description__text")
            or page.query_selector("#job-details")
        )

        if not jd_el:
            logger.warning("[LinkedIn] No JD found for %s", clean_url)
            return None

        raw_jd = jd_el.inner_text().strip()
        if not raw_jd or len(raw_jd) < 100:
            return None

        return ScrapedJob(
            url=clean_url,
            raw_jd=raw_jd,
            title=title,
            company=company,
            location=location,
        )
