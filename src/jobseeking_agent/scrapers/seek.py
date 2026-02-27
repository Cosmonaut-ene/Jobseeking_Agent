"""
Seek.com.au 全自动爬虫。

流程：
  对每个 target_role × location 组合：
    1. 搜索 Seek，获取职位列表（最多 max_per_query 条）
    2. 逐个访问职位详情页，提取完整 JD
    3. 随机延迟，模拟人类浏览
  返回 list[ScrapedJob]，由 ScoutAgent 统一打分入库。
"""

import random
import time
from dataclasses import dataclass, field
from urllib.parse import quote_plus

from playwright.sync_api import Page, sync_playwright


@dataclass
class ScrapedJob:
    url: str
    raw_jd: str
    title: str = ""
    company: str = ""
    location: str = ""
    salary: str = ""


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
        """
        existing_urls: already-processed URLs to skip (dedup).
        Returns scraped jobs (not yet in DB).
        """
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
                # Use only the first preferred location to avoid redundant calls
                location = locations[0] if locations else "All Australia"
                job_urls = self._search(page, role, location, max_per_query, existing_urls)

                for url in job_urls:
                    try:
                        job = self._fetch_job(page, url)
                        if job:
                            results.append(job)
                            existing_urls.add(url)
                    except Exception as e:
                        print(f"[Seek] Failed to fetch {url}: {e}")
                    _delay(2.5, 6.0)

            browser.close()

        return results

    def _search(
        self,
        page: Page,
        role: str,
        location: str,
        max_jobs: int,
        existing_urls: set[str],
    ) -> list[str]:
        search_url = (
            f"{self.BASE}/jobs?keywords={quote_plus(role)}"
            f"&where={quote_plus(location)}"
            f"&dateRange=7d&sortMode=ListedDate"
        )
        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=30_000)
            _delay(1.5, 3.0)
        except Exception as e:
            print(f"[Seek] Search page load failed for '{role}': {e}")
            return []

        urls: list[str] = []
        # Job cards link to /job/{id}
        links = page.query_selector_all("a[data-automation='jobTitle']")
        for link in links:
            if len(urls) >= max_jobs:
                break
            href = link.get_attribute("href") or ""
            if not href.startswith("/job/"):
                continue
            full_url = self.BASE + href.split("?")[0]  # strip query params
            if full_url not in existing_urls:
                urls.append(full_url)

        return urls

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

        return ScrapedJob(
            url=url,
            raw_jd=raw_jd,
            title=title,
            company=company,
            location=location,
            salary=salary,
        )
