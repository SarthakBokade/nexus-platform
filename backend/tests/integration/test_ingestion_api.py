import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.db.base import engine, Base


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.mark.asyncio
async def test_health_check_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "uptime_seconds" in data


import uuid

@pytest.mark.asyncio
async def test_auth_login_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        test_email = f"testadmin_{uuid.uuid4().hex[:6]}@nexus.com"
        # Seed user via signup
        signup_res = await ac.post("/api/v1/auth/signup", json={
            "email": test_email,
            "password": "Password123!",
            "full_name": "Test Admin",
            "role": "Admin",
            "department": "IT"
        })
        assert signup_res.status_code == 200
        user_data = signup_res.json()
        assert user_data["email"] == test_email
        assert user_data["role"] == "Admin"

        # Login
        login_res = await ac.post("/api/v1/auth/login", data={
            "username": test_email,
            "password": "Password123!"
        })
        assert login_res.status_code == 200
        token_data = login_res.json()
        assert "access_token" in token_data
