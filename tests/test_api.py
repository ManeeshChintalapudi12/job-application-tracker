"""Backend tests — run from the project root:  pytest -q"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app

SAMPLE = {
    "company": "Paystand",
    "role": "Junior Fullstack Engineer",
    "date_applied": "2026-11-19",
    "status": "Applied",
    "notes": "Tailored resume v2",
}


@pytest.fixture()
def client(tmp_path):
    app = create_app(db_path=tmp_path / "test.db")
    return TestClient(app)


def test_create_and_list(client):
    res = client.post("/applications", json=SAMPLE)
    assert res.status_code == 201
    created = res.json()
    assert created["id"] >= 1
    assert created["company"] == "Paystand"

    listed = client.get("/applications").json()
    assert len(listed) == 1
    assert listed[0]["role"] == "Junior Fullstack Engineer"


def test_update_status_then_delete(client):
    created = client.post("/applications", json=SAMPLE).json()

    updated = client.put(
        f"/applications/{created['id']}", json={"status": "Interview"}
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "Interview"

    assert client.delete(f"/applications/{created['id']}").status_code == 204
    assert client.get(f"/applications/{created['id']}").status_code == 404
    assert client.get("/applications").json() == []


def test_validation_and_not_found(client):
    # Missing required field -> 422
    bad = client.post("/applications", json={"company": "NoRole Co"})
    assert bad.status_code == 422

    # Invalid status -> 422
    bad_status = client.post("/applications", json={**SAMPLE, "status": "Ghosted"})
    assert bad_status.status_code == 422

    # Unknown id -> 404
    assert client.get("/applications/9999").status_code == 404


def test_stats_counts_by_status(client):
    client.post("/applications", json=SAMPLE)
    client.post("/applications", json={**SAMPLE, "company": "Kira", "status": "Interview"})
    stats = client.get("/stats").json()
    assert stats["total"] == 2
    assert stats["by_status"] == {"Applied": 1, "Interview": 1}
