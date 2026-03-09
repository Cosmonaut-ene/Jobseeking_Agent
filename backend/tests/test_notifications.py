"""Tests for notifications module."""
import pytest
from unittest.mock import patch, MagicMock
from backend.app.models.job import Job


class TestNotifications:
    def test_send_returns_false_without_webhook(self, monkeypatch):
        """_send should return False if no webhook URL configured."""
        from backend.app import notifications
        monkeypatch.setattr(notifications, "NOTIFICATION_WEBHOOK_URL", "")
        result = notifications._send("Test message")
        assert result is False

    def test_send_with_webhook_success(self, monkeypatch):
        """_send should call httpx.post and return True on success."""
        from backend.app import notifications
        monkeypatch.setattr(notifications, "NOTIFICATION_WEBHOOK_URL", "https://example.com/webhook")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("backend.app.notifications.httpx.post", return_value=mock_response) as mock_post:
            result = notifications._send("Test message")
            assert result is True
            mock_post.assert_called_once()

    def test_send_with_webhook_failure(self, monkeypatch):
        """_send should return False on HTTP error."""
        from backend.app import notifications
        monkeypatch.setattr(notifications, "NOTIFICATION_WEBHOOK_URL", "https://example.com/webhook")

        with patch("backend.app.notifications.httpx.post", side_effect=Exception("Connection refused")):
            result = notifications._send("Test message")
            assert result is False

    def test_push_high_score_job_format(self, monkeypatch):
        """push_high_score_job should format message correctly."""
        from backend.app import notifications

        sent_messages = []

        def mock_send(text: str) -> bool:
            sent_messages.append(text)
            return True

        monkeypatch.setattr(notifications, "_send", mock_send)

        job = Job(
            source="seek",
            raw_jd="Python Developer",
            title="Senior Python Developer",
            company="Acme Corp",
            location="Sydney, NSW",
            salary_range="$120k - $150k",
            match_score=0.87,
            gap_analysis={
                "strong_matches": ["Python", "FastAPI", "PostgreSQL"],
                "missing_skills": ["Kubernetes"],
            },
            source_url="https://seek.com.au/job/123",
        )

        result = notifications.push_high_score_job(job)
        assert result is True
        assert len(sent_messages) == 1
        msg = sent_messages[0]
        assert "Senior Python Developer" in msg
        assert "Acme Corp" in msg
        assert "87%" in msg
        assert "Sydney" in msg

    def test_push_daily_summary_format(self, monkeypatch):
        """push_daily_summary should format summary correctly."""
        from backend.app import notifications

        sent_messages = []

        def mock_send(text: str) -> bool:
            sent_messages.append(text)
            return True

        monkeypatch.setattr(notifications, "_send", mock_send)

        high_job = Job(source="seek", raw_jd="...", title="SWE", company="Google", match_score=0.85)
        mid_job = Job(source="indeed", raw_jd="...", title="Dev", company="Atlassian", match_score=0.75)

        stats = {"seek": 15, "linkedin": 20}
        result = notifications.push_daily_summary(stats, [high_job], [mid_job])

        assert result is True
        assert len(sent_messages) == 1
        msg = sent_messages[0]
        assert "Seek: 15" in msg
        assert "LinkedIn: 20" in msg
        assert "Google" in msg
        assert "Atlassian" in msg

    def test_push_high_score_job_calls_send(self, monkeypatch):
        """push_high_score_job should call _send exactly once."""
        from backend.app import notifications

        call_count = [0]

        def mock_send(text: str) -> bool:
            call_count[0] += 1
            return True

        monkeypatch.setattr(notifications, "_send", mock_send)

        job = Job(
            source="seek",
            raw_jd="Test JD",
            title="Dev",
            company="Corp",
            match_score=0.90,
        )
        notifications.push_high_score_job(job)
        assert call_count[0] == 1

    def test_push_high_score_job_includes_source_url(self, monkeypatch):
        """push_high_score_job should include source URL if available."""
        from backend.app import notifications

        sent_messages = []

        def mock_send(text: str) -> bool:
            sent_messages.append(text)
            return True

        monkeypatch.setattr(notifications, "_send", mock_send)

        job = Job(
            source="seek",
            raw_jd="Test JD",
            title="Dev",
            company="Corp",
            match_score=0.90,
            source_url="https://seek.com.au/job/999",
        )
        notifications.push_high_score_job(job)
        assert "https://seek.com.au/job/999" in sent_messages[0]

    def test_push_high_score_job_no_url_omits_link(self, monkeypatch):
        """push_high_score_job should not include link section if no URL."""
        from backend.app import notifications

        sent_messages = []

        def mock_send(text: str) -> bool:
            sent_messages.append(text)
            return True

        monkeypatch.setattr(notifications, "_send", mock_send)

        job = Job(
            source="seek",
            raw_jd="Test JD",
            title="Dev",
            company="Corp",
            match_score=0.90,
            source_url="",
        )
        notifications.push_high_score_job(job)
        # No href link should appear
        assert "href" not in sent_messages[0]

    def test_push_daily_summary_with_empty_jobs(self, monkeypatch):
        """push_daily_summary with no jobs should still send summary."""
        from backend.app import notifications

        sent_messages = []

        def mock_send(text: str) -> bool:
            sent_messages.append(text)
            return True

        monkeypatch.setattr(notifications, "_send", mock_send)

        result = notifications.push_daily_summary({"seek": 0, "indeed": 0, "linkedin": 0}, [], [])
        assert result is True
        assert len(sent_messages) == 1

    def test_push_daily_summary_shows_score_percentages(self, monkeypatch):
        """push_daily_summary should show score percentages for jobs."""
        from backend.app import notifications

        sent_messages = []

        def mock_send(text: str) -> bool:
            sent_messages.append(text)
            return True

        monkeypatch.setattr(notifications, "_send", mock_send)

        high_job = Job(source="seek", raw_jd="...", title="SWE", company="Google", match_score=0.85)
        notifications.push_daily_summary({}, [high_job], [])
        msg = sent_messages[0]
        assert "85%" in msg

    def test_send_with_chat_id_includes_it_in_payload(self, monkeypatch):
        """_send should include chat_id in payload when configured."""
        from backend.app import notifications
        monkeypatch.setattr(notifications, "NOTIFICATION_WEBHOOK_URL", "https://example.com/webhook")
        monkeypatch.setattr(notifications, "NOTIFICATION_CHAT_ID", "12345")

        captured_payload = {}

        def mock_post(url, json, timeout):
            captured_payload.update(json)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        with patch("backend.app.notifications.httpx.post", side_effect=mock_post):
            notifications._send("Hello")

        assert captured_payload.get("chat_id") == "12345"

    def test_send_without_chat_id_no_chat_id_field(self, monkeypatch):
        """_send should not include chat_id in payload when not configured."""
        from backend.app import notifications
        monkeypatch.setattr(notifications, "NOTIFICATION_WEBHOOK_URL", "https://example.com/webhook")
        monkeypatch.setattr(notifications, "NOTIFICATION_CHAT_ID", "")

        captured_payload = {}

        def mock_post(url, json, timeout):
            captured_payload.update(json)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        with patch("backend.app.notifications.httpx.post", side_effect=mock_post):
            notifications._send("Hello")

        assert "chat_id" not in captured_payload
