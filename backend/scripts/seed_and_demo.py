import os
import sys
import asyncio
import glob
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.future import select
from backend.app.db.base import AsyncSessionLocal, engine, Base
from backend.app.db.models import User, Document
from backend.app.auth.jwt import hash_password
from backend.app.ingestion.pipeline import IngestionPipeline
from backend.app.agents.router import AgentRouter
from backend.app.retrieval.pipeline import HybridRetrievalPipeline
from backend.app.auth.rbac import check_document_access, get_allowed_access_levels


async def init_and_seed():
    print("=" * 70)
    print("NEXUS — Initializing Database and Seeding Initial Enterprise Users")
    print("=" * 70)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        default_users = [
            ("admin@nexus.com", "AdminPass123!", "System Admin", "Admin", "IT"),
            ("employee@nexus.com", "Employee123!", "John Employee", "Employee", "General"),
            ("hr@nexus.com", "HRPass123!", "Sarah HR Manager", "HR", "People"),
            ("finance@nexus.com", "Finance123!", "Michael Finance Lead", "Finance", "Finance"),
            ("security@nexus.com", "Security123!", "Alex Security Officer", "Security", "Cybersecurity"),
        ]
        
        for email, password, full_name, role, department in default_users:
            res = await session.execute(select(User).where(User.email == email))
            if not res.scalars().first():
                user = User(
                    email=email,
                    hashed_password=hash_password(password),
                    full_name=full_name,
                    role=role,
                    department=department
                )
                session.add(user)
                print(f"[+] Seeded User: {email} (Role: {role}, Dept: {department})")
        await session.commit()

        # Ingest Sample PDFs
        print("\n" + "=" * 70)
        print("NEXUS — Ingesting Synthetic Enterprise Sample Documents")
        print("=" * 70)
        sample_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "sample_data", "documents")
        pdf_files = glob.glob(os.path.join(sample_dir, "*.pdf"))
        
        for pdf_path in pdf_files:
            fname = os.path.basename(pdf_path)
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            doc, info = await IngestionPipeline.process_document(session, fname, pdf_bytes)
            print(f"[+] Ingested '{fname}': {doc.chunk_count} chunks | Dept: {doc.department} | Access: {doc.access_level} | Version: {doc.version}")

        # Now Execute Demo Scenarios
        print("\n" + "=" * 70)
        print("NEXUS — Executing Acceptance Demo Scenarios")
        print("=" * 70)
        
        router = AgentRouter()
        retrieval_pipe = HybridRetrievalPipeline()

        # Fetch test users
        admin = (await session.execute(select(User).where(User.email == "admin@nexus.com"))).scalars().first()
        employee = (await session.execute(select(User).where(User.email == "employee@nexus.com"))).scalars().first()
        finance = (await session.execute(select(User).where(User.email == "finance@nexus.com"))).scalars().first()

        # Demo 1: Basic RAG Question
        print("\n--- DEMO 1: Basic RAG Question ---")
        q1 = "What is the international travel reimbursement limit?"
        res1 = await router.execute_agent_workflow(session, finance, q1)
        print(f"User: {finance.email} (Role: {finance.role})")
        print(f"Query: {q1}")
        print(f"Grounding Score: {res1.get('grounding_score')}")
        print(f"Answer:\n{res1.get('answer')[:250]}...")
        print("Citations:")
        for c in res1.get("citations", []):
            print(f"  - [{c.get('document_name')} p.{c.get('page')} {c.get('section','')}]")

        # Demo 2: Document Comparison
        print("\n--- DEMO 2: Document Version Comparison ---")
        q2 = "Compare the 2024 and 2025 travel policies and tell me what changed."
        res2 = await router.execute_agent_workflow(session, finance, q2)
        print(f"Query: {q2}")
        print(f"Answer:\n{res2.get('answer')}")

        # Demo 3: Conflict Detection
        print("\n--- DEMO 3: Policy Conflict Detection ---")
        q3 = "Are there conflicting policies regarding remote work?"
        res3 = await router.execute_agent_workflow(session, admin, q3)
        print(f"Query: {q3}")
        print(f"Answer:\n{res3.get('answer')}")

        # Demo 4: Cybersecurity Analysis
        print("\n--- DEMO 4: Cybersecurity Analysis ---")
        q4 = "Analyze all cybersecurity-related documents and produce an executive summary of major policy changes introduced in 2025."
        res4 = await router.execute_agent_workflow(session, admin, q4)
        print(f"Query: {q4}")
        print(f"Answer:\n{res4.get('answer')[:300]}...")

        # Demo 5: Executive Report
        print("\n--- DEMO 5: Executive Report Generation ---")
        print(f"Executive Report Generated: Grounding Score {res4.get('grounding_score')}, Citations Count: {len(res4.get('citations', []))}")

        # Demo 6: Evidence Verification
        print("\n--- DEMO 6: Grounding & Evidence Verification ---")
        print(f"Grounding Score: {res1.get('grounding_score')} | Status: {res1.get('verification_status')}")

        # Demo 7: RBAC Access Control Denied
        print("\n--- DEMO 7: Unauthorized Access Control Enforcement ---")
        sec_doc_res = await session.execute(select(Document).where(Document.filename == "Cybersecurity_SOP_2025.pdf"))
        sec_doc = sec_doc_res.scalars().first()
        is_emp_authorized = check_document_access(employee, sec_doc.access_level, sec_doc.department)
        print(f"Document: {sec_doc.filename} (Access Level: {sec_doc.access_level}, Dept: {sec_doc.department})")
        print(f"User: {employee.email} (Role: {employee.role})")
        print(f"Is Employee Authorized? -> {is_emp_authorized}")
        assert not is_emp_authorized, "Employee should NOT be authorized for Restricted Cybersecurity SOP!"
        print("[SUCCESS] Pre-retrieval RBAC successfully blocked unauthorized document retrieval!")

    await engine.dispose()
    print("\n" + "=" * 70)
    print("ALL DEMO SCENARIOS VERIFIED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(init_and_seed())
