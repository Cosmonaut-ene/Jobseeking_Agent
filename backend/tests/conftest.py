"""Shared pytest fixtures for backend tests."""
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_load_dotenv():
    """Prevent config.py from re-reading .env during module reload in tests.

    Some config tests pop env vars and reload backend.app.config to check
    defaults. Without this fixture, load_dotenv() re-reads .env and
    re-populates the env vars, defeating the test's setup.
    """
    # Patch the source so that importlib.reload(config) won't re-read .env.
    # Patching backend.app.config.load_dotenv is insufficient because reload()
    # re-executes "from dotenv import load_dotenv", re-binding the real function.
    # Patch dotenv.__init__.load_dotenv — the actual symbol that
    # "from dotenv import load_dotenv" binds to in config.py on reload.
    with patch("dotenv.load_dotenv"):
        yield
