"""
scratch/verify_all_pages.py - Automated verification for all CoinPulse Web Application pages & endpoints.
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient
from webapp.main import app

client = TestClient(app)

PAGES = [
    "/index.html",
    "/exchanges.html",
    "/exchange.html?id=binance",
    "/categories.html",
    "/coin.html?id=bitcoin",
    "/watchlist.html",
    "/portfolio.html"
]

API_ENDPOINTS = [
    "/api/health",
    "/api/markets?page=1&per_page=10",
    "/api/trending",
    "/api/global",
    "/api/exchanges?page=1&per_page=10",
    "/api/categories"
]

STATIC_FILES = [
    "/css/style.css",
    "/js/api.js",
    "/js/format.js",
    "/js/theme.js",
    "/js/search.js",
    "/js/auth.js",
    "/js/currency.js",
    "/js/alerts.js",
    "/js/market.js",
    "/js/categories.js",
    "/js/exchanges.js",
    "/js/coin.js",
    "/js/watchlist.js",
    "/js/portfolio.js"
]

def run_verification():
    print("==================================================")
    print("   CoinPulse Full Application Automated Verification")
    print("==================================================")
    
    passed = 0
    failed = 0

    # 1. Test Static JS and CSS Files
    print("\n--- 1. Testing Static Resources ---")
    for asset in STATIC_FILES:
        res = client.get(asset)
        if res.status_code == 200 and len(res.content) > 0:
            print(f"  [OK] {asset} ({len(res.content)} bytes)")
            passed += 1
        else:
            print(f"  [FAILED] {asset} - Status {res.status_code}")
            failed += 1

    # 2. Test HTML Page Views
    print("\n--- 2. Testing Web Pages ---")
    for page in PAGES:
        res = client.get(page)
        if res.status_code == 200 and len(res.content) > 0:
            print(f"  [OK] {page} ({len(res.content)} bytes)")
            passed += 1
        else:
            print(f"  [FAILED] {page} - Status {res.status_code}")
            failed += 1

    # 3. Test API Endpoints
    print("\n--- 3. Testing Backend API Endpoints ---")
    for api in API_ENDPOINTS:
        res = client.get(api)
        if res.status_code == 200:
            print(f"  [OK] {api} - Response JSON Keys: {list(res.json().keys())}")
            passed += 1
        else:
            print(f"  [FAILED] {api} - Status {res.status_code}")
            failed += 1

    # 4. Test Auth & Sync Endpoints
    print("\n--- 4. Testing Auth & Sync Endpoints ---")
    reg_email = f"verify_{id(app)}@coinpulse.io"
    reg_res = client.post("/api/auth/register", json={
        "name": "Verifier User",
        "email": reg_email,
        "password": "VerificationPassword123"
    })
    if reg_res.status_code == 200 and "token" in reg_res.json():
        print(f"  [OK] POST /api/auth/register - Account Created")
        passed += 1
        token = reg_res.json()["token"]

        login_res = client.post("/api/auth/login", json={
            "email": reg_email,
            "password": "VerificationPassword123"
        })
        if login_res.status_code == 200 and "token" in login_res.json():
            print(f"  [OK] POST /api/auth/login - Authentication Successful")
            passed += 1

        sync_save = client.post("/api/user/sync", json={
            "token": token,
            "watchlist": ["bitcoin", "ethereum", "solana"],
            "portfolio": [{"id": "bitcoin", "amount": 2.5}]
        })
        if sync_save.status_code == 200:
            print(f"  [OK] POST /api/user/sync - Watchlist & Portfolio Saved")
            passed += 1

        sync_get = client.get(f"/api/user/sync?token={token}")
        if sync_get.status_code == 200 and len(sync_get.json().get("watchlist", [])) == 3:
            print(f"  [OK] GET /api/user/sync - Watchlist & Portfolio Retrieved")
            passed += 1
    else:
        print(f"  [FAILED] Auth flow verification failed")
        failed += 1

    print("\n==================================================")
    print(f"  VERIFICATION RESULTS: {passed} PASSED, {failed} FAILED")
    print("==================================================")
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(run_verification())
