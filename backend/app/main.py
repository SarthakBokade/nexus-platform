import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.future import select

from backend.app.config import settings
from backend.app.db.base import engine, Base, AsyncSessionLocal
from backend.app.db.models import User
from backend.app.auth.jwt import hash_password
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.documents import router as doc_router
from backend.app.api.v1.search import router as search_router
from backend.app.api.v1.chat import router as chat_router
from backend.app.api.v1.comparison import router as compare_router
from backend.app.api.v1.evaluation import router as eval_router
from backend.app.api.v1.metrics import router as metrics_router
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.conversations import router as conversations_router


async def seed_initial_users():
    """Seeds default enterprise users with diverse RBAC roles for immediate testing."""
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
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database Tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_initial_users()
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}"}
    )

# Include API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(doc_router, prefix=settings.API_V1_STR)
app.include_router(search_router, prefix=settings.API_V1_STR)
app.include_router(chat_router, prefix=settings.API_V1_STR)
app.include_router(compare_router, prefix=settings.API_V1_STR)
app.include_router(eval_router, prefix=settings.API_V1_STR)
app.include_router(metrics_router, prefix=settings.API_V1_STR)
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(conversations_router, prefix=settings.API_V1_STR)

# Serve Frontend Static Directory
# Use relative path — works both locally and on Render
import pathlib
_repo_root = pathlib.Path(__file__).parent.parent.parent  # backend/app/main.py → repo root
frontend_dir = str(_repo_root / "frontend")
if not os.path.exists(frontend_dir):
    frontend_dir = os.path.join(os.getcwd(), "frontend")

if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
async def serve_index():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": f"NEXUS Backend Running ({settings.VERSION})", "status": "online"}

