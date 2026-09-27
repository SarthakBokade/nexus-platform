from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.app.db.base import get_db
from backend.app.db.models import User
from backend.app.auth.jwt import hash_password, verify_password, create_access_token
from backend.app.auth.rbac import get_current_user, get_allowed_access_levels

router = APIRouter(prefix="/auth", tags=["Authentication"])


class UserRegisterSchema(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "Employee" # Admin, Employee, HR, Finance, Security
    department: str = "General"


class UserResponseSchema(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    department: str
    allowed_access_levels: list[str]


class TokenResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponseSchema


@router.post("/signup", response_model=UserResponseSchema)
async def register_user(payload: UserRegisterSchema, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="User with this email already exists.")
        
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        department=payload.department
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return UserResponseSchema(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        department=user.department,
        allowed_access_levels=get_allowed_access_levels(user.role)
    )


@router.post("/login", response_model=TokenResponseSchema)
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    access_token = create_access_token(data={"sub": user.id, "role": user.role, "email": user.email})
    
    return TokenResponseSchema(
        access_token=access_token,
        token_type="bearer",
        user=UserResponseSchema(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            department=user.department,
            allowed_access_levels=get_allowed_access_levels(user.role)
        )
    )


@router.get("/me", response_model=UserResponseSchema)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserResponseSchema(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        department=current_user.department,
        allowed_access_levels=get_allowed_access_levels(current_user.role)
    )
