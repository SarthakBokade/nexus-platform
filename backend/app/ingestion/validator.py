import re
import hashlib
from typing import Tuple, List
from fastapi import UploadFile, HTTPException, status
from backend.app.config import settings

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"system\s*:\s*you\s+are\s+now",
    r"system\s*override",
    r"disregard\s+(all\s+)?(prior|previous|the\s+above)\s+(directives|rules|instructions)",
    r"forget\s+(your\s+)?(all\s+)?instructions",
    r"reveal\s+all\s+(company|system|user|confidential)\s+(documents|data|salaries|files)",
    r"jailbreak",
    r"bypass\s+(security|all)\s+(filter|checks)",
    r"override\s+system\s+prompt",
    r"dump\s+(the\s+)?internal\s+user\s+database",
    r"print\s+(the\s+)?secret\s+api\s+keys"
]


def compute_file_hash(file_bytes: bytes) -> str:
    """Computes SHA-256 hash of document binary data for deduplication."""
    return hashlib.sha256(file_bytes).hexdigest()


def validate_file(file_obj, file_bytes: bytes, max_size_mb: int = None) -> Tuple[bool, str]:
    """
    Validates file extension, size limits, and basic integrity.
    Supports FastAPI UploadFile or string filename.
    """
    filename = getattr(file_obj, "filename", None) or str(file_obj)
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    
    if ext not in settings.ALLOWED_EXTENSIONS:
        return False, f"Unsupported file type '.{ext}'. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        
    limit_mb = max_size_mb if max_size_mb is not None else settings.UPLOAD_MAX_SIZE_MB
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > limit_mb:
        return False, f"File size ({size_mb:.2f} MB) exceeds maximum allowed limit of {limit_mb} MB."
        
    if len(file_bytes) == 0:
        return False, "Uploaded file is empty (0 bytes)."
        
    return True, "File validation successful."


def scan_for_prompt_injection(text: str) -> List[str]:
    """
    Scans document text for malicious prompt injection attempts.
    Returns list of matched patterns.
    """
    matches = []
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            matches.append(pattern)
    return matches
