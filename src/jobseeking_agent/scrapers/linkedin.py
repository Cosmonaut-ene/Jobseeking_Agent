"""
LinkedIn 半自动抓取。

用法：
  1. 用户在 LinkedIn 手动搜索，把感兴趣的职位 URL 保存到
     data/linkedin_urls.txt（每行一个）
  2. 运行 cli linkedin-scout
  3. 脚本用 Playwright 访问各公开职位页面提取 JD

注意：
  - 不需要登录，LinkedIn 职位详情页对未登录用户是公开的
  - 抓取速度放慢（4-9s 间隔），降低被 block 风险
"""

import random
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from jobseeking_agent.scrapers.seek import ScrapedJob  # reuse dataclass

URLS_FILE = Path("data/linkedin_urls.txt")


def _delay(min_s: float = 4.0, max_s: float = 9.0) -> None:
    time.sleep(random.uniform(min_s, max_s))


def _safe_text(page: Page, selector: str, default: str = "") -> str:
    try:
        el = page.query_selector(selector)
        return el.inner_text().strip() if el else default
    except Exception:
        return default


class LinkedInScraper:
    def scrape_from_file(
        self,
        url_file: Path = URLS_FILE,
        existing_urls: set[str] | None = None,
    ) -> list[ScrapedJob]:
        existing_urls = existing_urls or set()

        if not url_file.exists():
            print(f"[LinkedIn] URL file not found: {url_file}")
            return []

        urls = [
            line.strip()
            for line in url_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        new_urls = [u for u in urls if u not in existing_urls]

        if not new_urls:
            print("[LinkedIn] All URLs already processed.")
            return []

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

            for url in new_urls:
                try:
                    job = self._fetch_job(page, url)
                    if job:
                        results.append(job)
                except Exception as e:
                    print(f"[LinkedIn] Failed to fetch {url}: {e}")
                _delay(4.0, 9.0)

            browser.close()

        return results

    def _fetch_job(self, page: Page, url: str) -> ScrapedJob | None:
        # Normalise URL — strip tracking params
        clean_url = url.split("?")[0].rstrip("/")

        page.goto(clean_url, wait_until="domcontentloaded", timeout=30_000)
        _delay(1.5, 3.0)

        # LinkedIn public job page selectors (logged-out view)
        title   = _safe_text(page, "h1.top-card-layout__title")
        company = _safe_text(page, "a.topcard__org-name-link") or \
                  _safe_text(page, "span.topcard__org-name-link")
        location = _safe_text(page, "span.topcard__flavor--bullet")

        # JD lives inside .show-more-less-html__markup
        jd_el = page.query_selector(".show-more-less-html__markup")
        if not jd_el:
            # fallback: decorated description div
            jd_el = page.query_selector(".description__text")

        if not jd_el:
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
