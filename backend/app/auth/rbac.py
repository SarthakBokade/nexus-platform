from enum import Enum
from typing import List, Dict, Set
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.app.auth.jwt import decode_access_token
from backend.app.db.base import get_db
from backend.app.db.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class UserRole(str, Enum):
    ADMIN = "Admin"
    EMPLOYEE = "Employee"
    HR = "HR"
    FINANCE = "Finance"
    SECURITY = "Security"


class AccessLevel(str, Enum):
    PUBLIC = "Public"
    INTERNAL = "Internal"
    RESTRICTED = "Restricted"
    CONFIDENTIAL = "Confidential"


# Explicit Role -> Accessible Access Levels Mapping
ROLE_ACCESS_MAPPING: Dict[str, Set[str]] = {
    UserRole.ADMIN.value: {
        AccessLevel.PUBLIC.value,
        AccessLevel.INTERNAL.value,
        AccessLevel.RESTRICTED.value,
        AccessLevel.CONFIDENTIAL.value,
    },
    UserRole.EMPLOYEE.value: {
        AccessLevel.PUBLIC.value,
        AccessLevel.INTERNAL.value,
    },
    UserRole.HR.value: {
        AccessLevel.PUBLIC.value,
        AccessLevel.INTERNAL.value,
        AccessLevel.RESTRICTED.value,
    },
    UserRole.FINANCE.value: {
        AccessLevel.PUBLIC.value,
        AccessLevel.INTERNAL.value,
        AccessLevel.RESTRICTED.value,
    },
    UserRole.SECURITY.value: {
        AccessLevel.PUBLIC.value,
        AccessLevel.INTERNAL.value,
        AccessLevel.RESTRICTED.value,
        AccessLevel.CONFIDENTIAL.value,
    },
}


# Role -> Department Privileges Mapping
ROLE_DEPARTMENT_MAPPING: Dict[str, Set[str]] = {
    UserRole.ADMIN.value: {"All"},
    UserRole.EMPLOYEE.value: {"General"},
    UserRole.HR.value: {"General", "HR", "People"},
    UserRole.FINANCE.value: {"General", "Finance", "Accounting"},
    UserRole.SECURITY.value: {"General", "Security", "IT", "Cybersecurity"},
}


def get_allowed_access_levels(role: str) -> List[str]:
    """
    Returns list of access levels user role is authorized to retrieve.
    """
    return list(ROLE_ACCESS_MAPPING.get(role, {AccessLevel.PUBLIC.value, AccessLevel.INTERNAL.value}))


def check_document_access(user: User, doc_access_level: str, doc_department: str) -> bool:
    """
    Evaluates whether user can access a specific document.
    Enforced BEFORE sending document text to vector DB or LLM.
    """
    if user.role == UserRole.ADMIN.value:
        return True
        
    allowed_levels = ROLE_ACCESS_MAPPING.get(user.role, {AccessLevel.PUBLIC.value})
    if doc_access_level not in allowed_levels:
        return False
        
    if doc_access_level == AccessLevel.CONFIDENTIAL.value and user.role != UserRole.ADMIN.value and user.role != UserRole.SECURITY.value:
        return False
        
    return True


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
        
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
        
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account")
        
    return user


def require_roles(allowed_roles: List[str]):
    """
    Role-based endpoint protection dependency.
    """
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles and current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{current_user.role}' is not authorized to perform this operation."
            )
        return current_user
    return role_checker
