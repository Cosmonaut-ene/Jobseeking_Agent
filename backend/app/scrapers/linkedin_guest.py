"""LinkedIn guest-API scraper — no login, no account required.

Flow:
  1. Call LinkedIn's guest search API (seeMoreJobPostings) to get job card
     HTML fragments — the same endpoint used by the non-logged-in search page.
  2. For each job URL, call the guest jobPosting API to retrieve the full JD.
  Both endpoints are served to unauthenticated users / search-engine crawlers,
  so no LinkedIn account is ever put at risk.
"""
import asyncio
import logging
import random
import re
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from backend.app.scrapers import ScrapedJob

logger = logging.getLogger(__name__)


def _is_retryable(exc: Exception) -> bool:
    """429/5xx 和网络错误触发重试，404 等客户端错误不重试。"""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {429, 500, 502, 503, 504}
    return isinstance(exc, httpx.RequestError)


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    reraise=True,
)
async def _get_with_retry(client: httpx.AsyncClient, url: str) -> httpx.Response:
    """带指数退避重试的 GET 请求，最多 3 次。"""
    resp = await client.get(url)
    resp.raise_for_status()
    return resp

GUEST_SEARCH_API = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    "?keywords={keywords}&location={location}&f_TPR=r86400&start={start}"
)
GUEST_API = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _extract_job_id(url: str) -> str | None:
    # URL format: /jobs/view/some-title-{job_id}?params  (ID is trailing digits in path)
    path = url.split("?")[0].rstrip("/")
    m = re.search(r"/jobs/view/[^/]*?-?(\d{7,})$", path)
    return m.group(1) if m else None


async def _fetch_job_detail(
    client: httpx.AsyncClient, job_id: str, job_url: str, fallback_title: str
) -> ScrapedJob | None:
    """Call LinkedIn's public guest API and parse the returned HTML fragment."""
    api_url = GUEST_API.format(job_id=job_id)
    try:
        resp = await _get_with_retry(client, api_url)
    except Exception as exc:
        logger.warning("[LinkedIn] Guest API failed for job_id=%s after retries: %s", job_id, exc)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    def _text(selector: str) -> str:
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else ""

    title = (
        _text("h2.top-card-layout__title")
        or _text("h1.top-card-layout__title")
        or _text("h1")
        or fallback_title
    )
    company = _text("a.topcard__org-name-link") or _text("span.topcard__org-name-link")
    location = _text("span.topcard__flavor--bullet") or _text(".top-card-layout__bullet")

    jd_el = (
        soup.select_one(".show-more-less-html__markup")
        or soup.select_one(".description__text")
        or soup.select_one("#job-details")
    )
    if not jd_el:
        logger.warning("[LinkedIn] No JD element found for job_id=%s", job_id)
        return None

    raw_jd = jd_el.get_text(separator="\n", strip=True)
    if len(raw_jd) < 100:
        return None

    return ScrapedJob(url=job_url, raw_jd=raw_jd, title=title, company=company, location=location)


async def scrape_linkedin_guest(
    keywords: list[str],
    location: str,
    max_results: int = 25,
    existing_urls: set[str] | None = None,
) -> list[ScrapedJob]:
    """
    Fetch LinkedIn job listings without any account or cookies.
    Returns empty list on complete failure.
    """
    existing_urls = existing_urls or set()

    # Step 1: collect job URLs from guest search API (25 results per page)
    search_items: list[tuple[str, str]] = []  # (url, title)
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
        for keyword in keywords:
            start = 0
            while len(search_items) < max_results:
                search_url = GUEST_SEARCH_API.format(
                    keywords=quote_plus(keyword),
                    location=quote_plus(location),
                    start=start,
                )
                try:
                    resp = await client.get(search_url)
                    resp.raise_for_status()
                    page_items = _parse_search_cards(resp.text)
                    if not page_items:
                        break
                    for item_url, item_title in page_items:
                        if item_url and item_url not in existing_urls:
                            search_items.append((item_url, item_title))
                            existing_urls.add(item_url)
                            if len(search_items) >= max_results:
                                break
                    start += 25
                    await asyncio.sleep(random.uniform(1.0, 2.0))
                except Exception as exc:
                    logger.warning("[LinkedIn] Guest search failed keyword=%r: %s", keyword, exc)
                    break

    logger.info("[LinkedIn] Found %d URLs via guest search", len(search_items))

    # Step 2: fetch full JD for each URL via guest jobPosting API
    results: list[ScrapedJob] = []
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
        for job_url, job_title in search_items:
            job_id = _extract_job_id(job_url)
            if not job_id:
                logger.debug("[LinkedIn] Cannot extract job_id from %s", job_url)
                continue
            job = await _fetch_job_detail(client, job_id, job_url, job_title)
            if job:
                results.append(job)
            await asyncio.sleep(random.uniform(1.5, 3.5))

    logger.info("[LinkedIn] Fetched %d full job descriptions", len(results))
    return results


def _parse_search_cards(html: str) -> list[tuple[str, str]]:
    """Parse job card HTML fragments from guest search API into (url, title) pairs."""
    soup = BeautifulSoup(html, "html.parser")
    items: list[tuple[str, str]] = []
    for card in soup.select("li"):
        # Job URL: the full-link anchor
        link_el = card.select_one("a.base-card__full-link") or card.select_one("a[href*='/jobs/view/']")
        if not link_el:
            continue
        href = link_el.get("href", "")
        if "/jobs/view/" not in href:
            continue
        url = href.split("?")[0].rstrip("/")
        if not url.startswith("http"):
            url = "https://www.linkedin.com" + url
        # Normalise regional subdomains (au., uk., ca., …) → www
        url = re.sub(r"https://[a-z]{2}\.linkedin\.com/", "https://www.linkedin.com/", url)

        # Title: prefer data attributes, fall back to link text
        title_el = card.select_one("h3.base-search-card__title") or card.select_one(".job-search-card__title")
        title = title_el.get_text(strip=True) if title_el else link_el.get_text(strip=True)

        items.append((url, title))
    return items
