"""Tests for the GitHub-sync router endpoints (SPEC 附录 F.7 TASK-B03).

Note: UserProfile.load() re-imports PROFILE_PATH from backend.app.config
fresh on every call, while routers/profile.py's own read/write code uses
its own module-level import of the same name. Both must be monkeypatched
together to the same tmp path, or UserProfile.load() silently falls back
to the real project data/user_profile.json.
"""
import json
import time

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")
    monkeypatch.setenv("GITHUB_TOKEN", "test-github-token")

    profile_path = tmp_path / "user_profile.json"
    monkeypatch.setattr("backend.app.config.PROFILE_PATH", profile_path)
    monkeypatch.setattr("backend.app.routers.profile.PROFILE_PATH", profile_path)

    import backend.app.routers.profile as profile_router
    profile_router._github_sync_tasks.clear()

    from backend.app.main import app
    test_client = TestClient(app, raise_server_exceptions=False)
    test_client._profile_path = profile_path  # stashed for tests that need to seed/read it directly
    return test_client


def _seed_profile(path, skills):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "name": "Jane Doe",
        "target_roles": [],
        "skills": skills,
        "experience": [],
        "projects": [],
        "education": [],
        "preferences": {"locations": []},
    }), encoding="utf-8")


class TestStartGitHubSync:
    def test_missing_token_returns_400(self, client, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        resp = client.post("/api/profile/github-sync", json={})
        assert resp.status_code == 400

    def test_starts_background_task(self, client, monkeypatch):
        async def fake_sync_profile(username=None, exclude_forks=True):
            return []

        monkeypatch.setattr("backend.app.routers.profile.sync_profile", fake_sync_profile)

        resp = client.post("/api/profile/github-sync", json={})
        assert resp.status_code == 200
        assert "task_id" in resp.json()


class TestGetGitHubSyncTask:
    def test_nonexistent_task_returns_404(self, client):
        resp = client.get("/api/profile/github-sync/tasks/does-not-exist")
        assert resp.status_code == 404

    def test_completed_task_carries_diff(self, client, monkeypatch):
        _seed_profile(client._profile_path, [])

        async def fake_sync_profile(username=None, exclude_forks=True):
            from backend.app.agents.profile_sync import InferredSkill
            return [InferredSkill(name="Python", years=2.0, source_repos=["octocat/repo1"],
                                   first_seen="2024-01-01", last_active="2024-06-01")]

        monkeypatch.setattr("backend.app.routers.profile.sync_profile", fake_sync_profile)

        start = client.post("/api/profile/github-sync", json={})
        task_id = start.json()["task_id"]

        status = _poll_until_done(client, task_id)

        assert status["status"] == "done"
        assert len(status["diff"]) == 1
        assert status["diff"][0]["name"] == "Python"
        assert status["diff"][0]["change_type"] == "new"

    def test_sync_failure_surfaces_as_error_status(self, client, monkeypatch):
        async def fake_sync_profile(username=None, exclude_forks=True):
            raise RuntimeError("boom")

        monkeypatch.setattr("backend.app.routers.profile.sync_profile", fake_sync_profile)

        start = client.post("/api/profile/github-sync", json={})
        task_id = start.json()["task_id"]

        status = _poll_until_done(client, task_id)

        assert status["status"] == "error"


def _poll_until_done(client, task_id, attempts=50, interval=0.05):
    status = {}
    for _ in range(attempts):
        status = client.get(f"/api/profile/github-sync/tasks/{task_id}").json()
        if status["status"] in ("done", "error"):
            break
        time.sleep(interval)
    return status


class TestApplyGitHubSync:
    def test_nonexistent_task_returns_404(self, client):
        resp = client.post("/api/profile/github-sync/apply", json={"task_id": "nope", "accepted_skill_names": []})
        assert resp.status_code == 404

    def test_task_not_ready_returns_400(self, client):
        import backend.app.routers.profile as profile_router
        profile_router._github_sync_tasks["t1"] = {"status": "running"}

        resp = client.post("/api/profile/github-sync/apply", json={"task_id": "t1", "accepted_skill_names": []})
        assert resp.status_code == 400

    def test_only_accepted_entries_are_merged_and_saved(self, client):
        _seed_profile(client._profile_path, [{"name": "Go", "level": "intermediate", "years": 2.0}])

        import backend.app.routers.profile as profile_router
        profile_router._github_sync_tasks["t1"] = {
            "status": "done",
            "diff": [
                {
                    "name": "Python", "change_type": "new", "proposed_years": 3.0,
                    "current_years": None, "source_repos": ["r1"],
                    "first_seen": "2024-01-01", "last_active": "2024-06-01",
                },
                {
                    "name": "Rust", "change_type": "new", "proposed_years": 1.5,
                    "current_years": None, "source_repos": ["r2"],
                    "first_seen": "2024-01-01", "last_active": "2024-06-01",
                },
            ],
        }

        resp = client.post("/api/profile/github-sync/apply", json={
            "task_id": "t1", "accepted_skill_names": ["Python"],  # Rust NOT accepted
        })

        assert resp.status_code == 200
        skills = {s["name"]: s for s in resp.json()["profile"]["skills"]}
        assert "Python" in skills
        assert "Rust" not in skills
        assert "Go" in skills  # untouched existing skill preserved

        # Persisted to disk, not just returned in the response
        saved = json.loads(client._profile_path.read_text())
        saved_names = {s["name"] for s in saved["skills"]}
        assert saved_names == {"Go", "Python"}

    def test_no_profile_returns_400(self, client):
        import backend.app.routers.profile as profile_router
        profile_router._github_sync_tasks["t1"] = {"status": "done", "diff": []}
        # client._profile_path points at a file that was never seeded — doesn't exist

        resp = client.post("/api/profile/github-sync/apply", json={"task_id": "t1", "accepted_skill_names": []})
        assert resp.status_code == 400
