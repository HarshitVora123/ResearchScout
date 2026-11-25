"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    """Test registration issues HttpOnly session cookies."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "securepassword123",
            "full_name": "New User",
        },
    )
    assert response.status_code == 201
    assert response.json()["message"] == "Registration successful"
    cookies = response.headers.get_list("set-cookie")
    assert any(
        cookie.startswith("access_token=") and "httponly" in cookie.lower() for cookie in cookies
    )
    assert any(
        cookie.startswith("refresh_token=") and "httponly" in cookie.lower() for cookie in cookies
    )
    session = await client.get("/api/v1/auth/session")
    assert session.status_code == 200
    assert session.json() == {"authenticated": True}


@pytest.mark.asyncio
async def test_refresh_and_logout_revoke_session(client: AsyncClient):
    """Refresh issues usable cookies; logout revokes the refreshed session."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh-session@example.com",
            "password": "securepassword123",
            "full_name": "Refresh Session User",
        },
    )
    assert response.status_code == 201

    refreshed = await client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    assert (await client.get("/api/v1/auth/session")).status_code == 200

    logged_out = await client.post("/api/v1/auth/logout")
    assert logged_out.status_code == 200
    assert (await client.get("/api/v1/auth/session")).status_code == 401


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Test that duplicate email registration returns 409."""
    user_data = {
        "email": "duplicate@example.com",
        "password": "securepassword123",
        "full_name": "First User",
    }
    # Register first time
    response1 = await client.post("/api/v1/auth/register", json=user_data)
    assert response1.status_code == 201

    # Register again with same email
    response2 = await client.post("/api/v1/auth/register", json=user_data)
    assert response2.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Test successful login."""
    # Register first
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "password": "securepassword123",
            "full_name": "Login User",
        },
    )

    # Login
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": "securepassword123",
        },
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Login successful"
    assert any(
        cookie.startswith("access_token=") and "httponly" in cookie.lower()
        for cookie in response.headers.get_list("set-cookie")
    )


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Test login with wrong password returns 401."""
    # Register
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrong@example.com",
            "password": "correctpassword",
            "full_name": "Wrong Pass User",
        },
    )

    # Login with wrong password
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "wrong@example.com",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient, monkeypatch):
    """Test healthy dependency reporting without requiring a local Redis server."""
    from app.core import redis as redis_module

    class HealthyRedis:
        async def ping(self):
            return True

    monkeypatch.setattr(redis_module, "redis_client", HealthyRedis())
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_resume_upload_persists_extracted_projects(client: AsyncClient):
    """Resume discoveries appear in the profile projects dashboard count."""
    registration = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "resume-projects@example.com",
            "password": "securepassword123",
            "full_name": "Resume Projects User",
        },
    )
    assert registration.status_code == 201
    malformed_profile = await client.put(
        "/api/v1/users/profile",
        json={
            "university": "Pune Institute of Computer Technology CGPA: 9.60",
            "gpa": 4.0,
        },
    )
    assert malformed_profile.status_code == 200

    resume_text = """Education
Pune Institute of Computer Technology CGPA: 9.60
BE – Artificial Intelligence & Data Science Aug 2023 – Jun 2027
Projects
Home-Accessible Brain Tumour Screening and Triage Ongoing
– Investigated screening approaches and available datasets.
3D Endoscopic Reconstruction Pipeline
– Developed an end-to-end reconstruction pipeline using Python and OpenCV.
Technical Skills
Python, OpenCV
"""
    response = await client.post(
        "/api/v1/users/profile/resume",
        files={"file": ("resume.txt", resume_text.encode(), "text/plain")},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["parsed_profile"]["gpa"] == pytest.approx(3.84)
    assert len(body["parsed_profile"]["projects"]) == 2
    assert len(body["profile_updates"]["projects_added"]) == 2

    profile = await client.get("/api/v1/users/profile")
    assert profile.status_code == 200
    assert len(profile.json()["projects"]) == 2
    assert profile.json()["university"] == "Pune Institute of Computer Technology"
    assert float(profile.json()["gpa"]) == pytest.approx(3.84)

    repeated_upload = await client.post(
        "/api/v1/users/profile/resume",
        files={"file": ("resume.txt", resume_text.encode(), "text/plain")},
    )
    assert repeated_upload.status_code == 200
    assert "projects_added" not in repeated_upload.json()["profile_updates"]
    profile = await client.get("/api/v1/users/profile")
    assert len(profile.json()["projects"]) == 2


@pytest.mark.asyncio
async def test_discovery_explains_missing_search_credentials(client: AsyncClient, monkeypatch):
    """Do not report a successful discovery job when no search source is set up."""
    from app.agents.discovery import search_agent

    monkeypatch.setattr(search_agent.settings, "google_cse_api_key", "")
    monkeypatch.setattr(search_agent.settings, "google_cse_cx", "")
    monkeypatch.setattr(search_agent.settings, "bing_search_api_key", "")
    monkeypatch.setattr(search_agent.settings, "tavily_api_key", "")
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "no-search-config@example.com",
            "password": "securepassword123",
            "full_name": "No Search Config User",
        },
    )

    response = await client.post("/api/v1/pipeline/discover", json={"topics": ["computer vision"]})

    assert response.status_code == 503
    assert "GOOGLE_CSE_API_KEY" in response.json()["detail"]
    assert "BING_SEARCH_API_KEY" in response.json()["detail"]
    assert "TAVILY_API_KEY" in response.json()["detail"]
