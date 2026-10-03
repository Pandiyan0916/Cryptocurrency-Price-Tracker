"""
tests/test_webapp_auth.py - Unit tests for Auth and User Sync FastAPI endpoints.
"""

from fastapi.testclient import TestClient
from webapp.main import app

client = TestClient(app)

def test_register_and_login_flow():
    email = f"test_user_{id(app)}@example.com"
    password = "secretpassword123"

    # Register
    reg_resp = client.post("/api/auth/register", json={
        "name": "Test User",
        "email": email,
        "password": password
    })
    assert reg_resp.status_code == 200
    data = reg_resp.json()
    assert data["status"] == "ok"
    assert "token" in data
    assert data["user"]["email"] == email

    token = data["token"]

    # Login
    login_resp = client.post("/api/auth/login", json={
        "email": email,
        "password": password
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["status"] == "ok"
    assert "token" in login_data

    # User Sync (Save Data)
    sync_save = client.post("/api/user/sync", json={
        "token": token,
        "watchlist": ["bitcoin", "ethereum"],
        "portfolio": [{"id": "bitcoin", "amount": 1.5}]
    })
    assert sync_save.status_code == 200

    # User Sync (Fetch Data)
    sync_get = client.get(f"/api/user/sync?token={token}")
    assert sync_get.status_code == 200
    get_data = sync_get.json()
    assert get_data["watchlist"] == ["bitcoin", "ethereum"]
    assert get_data["portfolio"][0]["id"] == "bitcoin"
