import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_shorten_url_success():
    payload = {"url": "https://example.com"}
    response = client.post("/shorten", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "short_code" in data
    assert "short_url" in data

def test_redirect_works():
    # First, create a short link
    payload = {"url": "https://google.com"}
    create_res = client.post("/shorten", json=payload)
    code = create_res.json()["short_code"]
    
    # Then, test the redirect (don't follow it)
    redirect_res = client.get(f"/{code}", follow_redirects=False)
    assert redirect_res.status_code == 307
    assert redirect_res.headers["location"].rstrip("/") == "https://google.com"

def test_stats_tracking():
    payload = {"url": "https://python.org"}
    create_res = client.post("/shorten", json=payload)
    code = create_res.json()["short_code"]
    
    # Simulate 3 visits
    client.get(f"/{code}")
    client.get(f"/{code}")
    client.get(f"/{code}")
    
    stats_res = client.get(f"/{code}/stats")
    assert stats_res.status_code == 200
    data = stats_res.json()
    assert data["visit_count"] == 3
    assert data["original_url"].rstrip("/") == "https://python.org"

def test_not_found():
    response = client.get("/non-existent-code")
    assert response.status_code == 404

def test_invalid_url():
    payload = {"url": "not-a-url"}
    response = client.post("/shorten", json=payload)
    assert response.status_code == 422
