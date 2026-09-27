import pytest
from backend.app.db.models import User
from backend.app.auth.rbac import check_document_access, get_allowed_access_levels


def test_rbac_access_matrix():
    admin = User(role="Admin", department="IT")
    employee = User(role="Employee", department="General")
    hr = User(role="HR", department="People")
    finance = User(role="Finance", department="Finance")
    security = User(role="Security", department="Cybersecurity")

    # Admin accesses everything
    assert check_document_access(admin, "Confidential", "Finance") is True
    assert check_document_access(admin, "Restricted", "HR") is True

    # Employee accesses only Public & Internal
    assert check_document_access(employee, "Public", "General") is True
    assert check_document_access(employee, "Internal", "General") is True
    assert check_document_access(employee, "Restricted", "HR") is False
    assert check_document_access(employee, "Confidential", "Security") is False

    # HR accesses Public, Internal, Restricted
    assert check_document_access(hr, "Restricted", "HR") is True
    assert check_document_access(hr, "Confidential", "Security") is False

    # Security accesses Confidential
    assert check_document_access(security, "Confidential", "Security") is True


def test_allowed_access_levels():
    assert "Confidential" in get_allowed_access_levels("Admin")
    assert "Confidential" not in get_allowed_access_levels("Employee")
    assert "Internal" in get_allowed_access_levels("Employee")
