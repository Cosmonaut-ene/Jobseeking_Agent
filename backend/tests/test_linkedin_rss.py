"""Tests for LinkedIn RSS scraper."""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock


SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>LinkedIn Jobs</title>
    <item>
      <title>Software Engineer at TechCorp</title>
      <link>https://www.linkedin.com/jobs/view/123456</link>
      <description>Looking for a Python developer with FastAPI experience.</description>
    </item>
    <item>
      <title>Data Scientist at DataCo</title>
      <link>https://www.linkedin.com/jobs/view/789012</link>
      <description>ML engineer needed for NLP projects.</description>
    </item>
    <item>
      <title>DevOps Engineer at CloudInc</title>
      <link>https://www.linkedin.com/jobs/view/345678</link>
      <description>Kubernetes and Docker experience required.</description>
    </item>
  </channel>
</rss>"""


def _make_mock_response(text: str, status_code: int = 200):
    mock = MagicMock()
    mock.text = text
    mock.status_code = status_code
    mock.raise_for_status = MagicMock()
    return mock


def test_network_success_returns_scraped_jobs():
    """Mock network success returns list[ScrapedJob]."""
    from backend.app.scrapers.linkedin_rss import scrape_linkedin_rss
    from backend.app.scrapers import ScrapedJob

    async def run():
        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = _make_mock_response(SAMPLE_RSS)
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await scrape_linkedin_rss(["python developer"], "Melbourne", max_results=10)
        return result

    result = asyncio.run(run())
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(j, ScrapedJob) for j in result)


def test_network_failure_returns_empty_list():
    """Network failure returns [] without raising exception."""
    from backend.app.scrapers.linkedin_rss import scrape_linkedin_rss

    async def run():
        with patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(side_effect=Exception("Connection refused"))
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await scrape_linkedin_rss(["python"], "Sydney", max_results=10)
        return result

    result = asyncio.run(run())
    assert result == []


def test_scraped_job_url_nonempty():
    """All returned ScrapedJob objects have non-empty url."""
    from backend.app.scrapers.linkedin_rss import scrape_linkedin_rss

    async def run():
        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = _make_mock_response(SAMPLE_RSS)
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await scrape_linkedin_rss(["data scientist"], "Brisbane", max_results=10)
        return result

    result = asyncio.run(run())
    assert all(j.url for j in result), "All ScrapedJob.url must be non-empty"


def test_max_results_limit_respected():
    """max_results parameter limits total returned jobs."""
    from backend.app.scrapers.linkedin_rss import scrape_linkedin_rss

    async def run():
        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = _make_mock_response(SAMPLE_RSS)
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            # SAMPLE_RSS has 3 items, request max_results=2
            result = await scrape_linkedin_rss(["engineer"], "Melbourne", max_results=2)
        return result

    result = asyncio.run(run())
    assert len(result) <= 2
