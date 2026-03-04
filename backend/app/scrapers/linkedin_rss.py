"""LinkedIn RSS job scraper — no login required."""
import logging
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

import httpx

from backend.app.scrapers import ScrapedJob

logger = logging.getLogger(__name__)

RSS_URL = "https://www.linkedin.com/jobs/search?keywords={keywords}&location={location}&f_TPR=r86400&format=rss"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


async def scrape_linkedin_rss(
    keywords: list[str],
    location: str,
    max_results: int = 25,
    existing_urls: set[str] | None = None,
) -> list[ScrapedJob]:
    """
    Fetch LinkedIn job RSS feed and return ScrapedJob list.
    Returns empty list on any network/parse error.
    """
    existing_urls = existing_urls or set()
    results: list[ScrapedJob] = []

    for keyword in keywords:
        if len(results) >= max_results:
            break
        url = RSS_URL.format(
            keywords=quote_plus(keyword),
            location=quote_plus(location),
        )
        try:
            async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                items = _parse_rss(resp.text)
                for item in items:
                    if len(results) >= max_results:
                        break
                    if item.url and item.url not in existing_urls:
                        results.append(item)
                        existing_urls.add(item.url)
        except Exception as exc:
            logger.warning("[LinkedIn RSS] Failed to fetch keyword=%r location=%r: %s", keyword, location, exc)

    logger.info("[LinkedIn RSS] Fetched %d jobs for keywords=%s location=%s", len(results), keywords, location)
    return results


def _parse_rss(xml_text: str) -> list[ScrapedJob]:
    """Parse RSS XML and return list of ScrapedJob."""
    jobs: list[ScrapedJob] = []
    try:
        root = ET.fromstring(xml_text)
        # Handle potential namespaces
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        channel = root.find(f"{ns}channel")
        if channel is None:
            channel = root  # some feeds have items directly under root

        for item in channel.findall(f"{ns}item"):
            title = (item.findtext(f"{ns}title") or "").strip()
            link = (item.findtext(f"{ns}link") or "").strip()
            description = (item.findtext(f"{ns}description") or "").strip()

            if not link:
                continue

            # Build raw_jd from title + description
            raw_jd = f"{title}\n\n{description}" if description else title

            jobs.append(ScrapedJob(
                url=link,
                raw_jd=raw_jd,
                title=title,
                location="",  # Not reliably in RSS
            ))
    except ET.ParseError as exc:
        logger.warning("[LinkedIn RSS] XML parse error: %s", exc)
    return jobs
