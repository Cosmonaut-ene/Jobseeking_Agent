"""Tests for configuration module."""
import os
import pytest
from pathlib import Path


class TestConfig:
    def test_config_imports(self):
        from backend.app.config import (
            BASE_DIR, DATA_DIR, DB_PATH, PROFILE_PATH, COOKIES_DIR,
            RESUMES_DIR, COVER_LETTERS_DIR, HIGH_SCORE_THRESHOLD,
            MID_SCORE_THRESHOLD, SCHEDULER_HOUR, SCHEDULER_MINUTE,
            DEFAULT_MAX_JOBS,
        )
        assert isinstance(BASE_DIR, Path)
        assert isinstance(DATA_DIR, Path)
        assert isinstance(DB_PATH, Path)
        assert 0.0 < HIGH_SCORE_THRESHOLD <= 1.0
        assert 0.0 < MID_SCORE_THRESHOLD <= 1.0
        assert MID_SCORE_THRESHOLD < HIGH_SCORE_THRESHOLD
        assert 0 <= SCHEDULER_HOUR <= 23
        assert 0 <= SCHEDULER_MINUTE <= 59
        assert DEFAULT_MAX_JOBS > 0

    def test_base_dir_is_project_root(self):
        from backend.app.config import BASE_DIR
        # BASE_DIR should be Jobseeking_Agent/
        assert (BASE_DIR / "backend").exists()

    def test_threshold_defaults(self):
        """Test default threshold values."""
        old_val = os.environ.pop("HIGH_SCORE_THRESHOLD", None)
        old_mid = os.environ.pop("MID_SCORE_THRESHOLD", None)
        try:
            # Reimport to get fresh values
            import importlib
            import backend.app.config as cfg
            importlib.reload(cfg)
            assert cfg.HIGH_SCORE_THRESHOLD == 0.80
            assert cfg.MID_SCORE_THRESHOLD == 0.70
        finally:
            if old_val:
                os.environ["HIGH_SCORE_THRESHOLD"] = old_val
            if old_mid:
                os.environ["MID_SCORE_THRESHOLD"] = old_mid

    def test_data_dir_under_base_dir(self):
        from backend.app.config import BASE_DIR, DATA_DIR
        # DATA_DIR should be a subdirectory of BASE_DIR
        assert DATA_DIR.parent == BASE_DIR

    def test_db_path_is_sqlite_file(self):
        from backend.app.config import DB_PATH
        assert DB_PATH.suffix == ".db"

    def test_profile_path_is_json(self):
        from backend.app.config import PROFILE_PATH
        assert PROFILE_PATH.suffix == ".json"

    def test_scheduler_defaults(self):
        """Test default scheduler values without env overrides."""
        old_hour = os.environ.pop("SCHEDULER_HOUR", None)
        old_minute = os.environ.pop("SCHEDULER_MINUTE", None)
        try:
            import importlib
            import backend.app.config as cfg
            importlib.reload(cfg)
            assert cfg.SCHEDULER_HOUR == 9
            assert cfg.SCHEDULER_MINUTE == 0
        finally:
            if old_hour:
                os.environ["SCHEDULER_HOUR"] = old_hour
            if old_minute:
                os.environ["SCHEDULER_MINUTE"] = old_minute

    def test_default_max_jobs_default(self):
        """Test DEFAULT_MAX_JOBS default value."""
        old_val = os.environ.pop("DEFAULT_MAX_JOBS", None)
        try:
            import importlib
            import backend.app.config as cfg
            importlib.reload(cfg)
            assert cfg.DEFAULT_MAX_JOBS == 15
        finally:
            if old_val:
                os.environ["DEFAULT_MAX_JOBS"] = old_val

    def test_gemini_api_key_default_empty(self):
        """GEMINI_API_KEY should default to empty string."""
        old_val = os.environ.pop("GEMINI_API_KEY", None)
        try:
            import importlib
            import backend.app.config as cfg
            importlib.reload(cfg)
            assert cfg.GEMINI_API_KEY == ""
        finally:
            if old_val:
                os.environ["GEMINI_API_KEY"] = old_val

    def test_scheduler_enabled_default_true(self):
        """SCHEDULER_ENABLED should default to True."""
        old_val = os.environ.pop("SCHEDULER_ENABLED", None)
        try:
            import importlib
            import backend.app.config as cfg
            importlib.reload(cfg)
            assert cfg.SCHEDULER_ENABLED is True
        finally:
            if old_val:
                os.environ["SCHEDULER_ENABLED"] = old_val

    def test_notification_webhook_default_empty(self):
        """NOTIFICATION_WEBHOOK_URL should default to empty string."""
        old_val = os.environ.pop("NOTIFICATION_WEBHOOK_URL", None)
        try:
            import importlib
            import backend.app.config as cfg
            importlib.reload(cfg)
            assert cfg.NOTIFICATION_WEBHOOK_URL == ""
        finally:
            if old_val:
                os.environ["NOTIFICATION_WEBHOOK_URL"] = old_val

    def test_resumes_dir_under_data_dir(self):
        from backend.app.config import DATA_DIR, RESUMES_DIR
        assert RESUMES_DIR.parent == DATA_DIR

    def test_cover_letters_dir_under_data_dir(self):
        from backend.app.config import DATA_DIR, COVER_LETTERS_DIR
        assert COVER_LETTERS_DIR.parent == DATA_DIR
