import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app


@pytest.mark.asyncio
async def test_frontend_index_served():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/")
        assert res.status_code == 200
        assert "NEXUS" in res.text
        assert "Enterprise Agentic Document Intelligence Platform" in res.text


@pytest.mark.asyncio
async def test_admin_full_pipeline_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Login as Admin
        login_res = await ac.post("/api/v1/auth/login", data={
            "username": "admin@nexus.com",
            "password": "AdminPass123!"
        })
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. List Documents (Admin sees all)
        docs_res = await ac.get("/api/v1/documents", headers=headers)
        assert docs_res.status_code == 200
        docs = docs_res.json()
        assert len(docs) >= 5

        # 3. Search endpoint
        search_res = await ac.post("/api/v1/search/query", json={
            "query": "international travel reimbursement limit",
            "mode": "hybrid_rerank",
            "top_k": 3
        }, headers=headers)
        assert search_res.status_code == 200
        search_data = search_res.json()
        assert len(search_data["results"]) > 0

        # 4. Chat / Agent Completions endpoint
        chat_res = await ac.post("/api/v1/chat/completions", json={
            "message": "What is the international travel reimbursement limit?"
        }, headers=headers)
        assert chat_res.status_code == 200
        chat_data = chat_res.json()
        assert "answer" in chat_data
        assert "citations" in chat_data
        assert "agent_trace" in chat_data

        # 5. Document Version Comparison
        comp_res = await ac.post("/api/v1/chat/completions", json={
            "message": "Compare the 2024 and 2025 travel policies and tell me what changed."
        }, headers=headers)
        assert comp_res.status_code == 200
        comp_data = comp_res.json()
        assert "Structured Comparison" in comp_data["answer"]

        # 6. Conflict Detection
        conf_res = await ac.post("/api/v1/chat/completions", json={
            "message": "Are there conflicting policies regarding remote work?"
        }, headers=headers)
        assert conf_res.status_code == 200
        conf_data = conf_res.json()
        assert "Potential Policy Conflict Detected" in conf_data["answer"]

        # 7. Evaluation Runs endpoint
        bench_res = await ac.post("/api/v1/evaluation/benchmark", json={"strategy": "hybrid_rerank"}, headers=headers)
        assert bench_res.status_code == 200
        bench_data = bench_res.json()
        assert "recall_at_5" in bench_data

        eval_res = await ac.get("/api/v1/evaluation/runs", headers=headers)
        assert eval_res.status_code == 200
        eval_runs = eval_res.json()
        assert len(eval_runs) >= 1

        # 8. Metrics Dashboard endpoint
        metrics_res = await ac.get("/api/v1/metrics/dashboard", headers=headers)
        assert metrics_res.status_code == 200
        metrics_data = metrics_res.json()
        assert "total_queries" in metrics_data
        assert "system_status" in metrics_data


@pytest.mark.asyncio
async def test_employee_rbac_restriction():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Login as regular Employee
        login_res = await ac.post("/api/v1/auth/login", data={
            "username": "employee@nexus.com",
            "password": "Employee123!"
        })
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # List Documents: Employee should only see Public & Internal
        docs_res = await ac.get("/api/v1/documents", headers=headers)
        assert docs_res.status_code == 200
        docs = docs_res.json()
        for doc in docs:
            assert doc["access_level"] in ["Public", "Internal"]
            assert doc["access_level"] != "Restricted"
            assert doc["access_level"] != "Confidential"
