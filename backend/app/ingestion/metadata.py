import re
from typing import Dict, Any, Optional
from datetime import datetime


def extract_metadata_from_filename_and_text(
    filename: str,
    first_page_text: str,
    user_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Combines explicit user payload metadata with auto-detected metadata from filename and document cover page.
    """
    user_metadata = user_metadata or {}
    
    # 1. Document Type Detection
    doc_type = user_metadata.get("document_type")
    if not doc_type:
        fn_lower = filename.lower()
        if "policy" in fn_lower or "guideline" in fn_lower:
            doc_type = "Policy"
        elif "sop" in fn_lower or "procedure" in fn_lower or "manual" in fn_lower:
            doc_type = "SOP"
        elif "financial" in fn_lower or "budget" in fn_lower or "reimbursement" in fn_lower:
            doc_type = "Financial"
        elif "hr" in fn_lower or "handbook" in fn_lower or "employee" in fn_lower:
            doc_type = "HR"
        elif "contract" in fn_lower or "agreement" in fn_lower:
            doc_type = "Contract"
        elif "security" in fn_lower or "cyber" in fn_lower or "tech" in fn_lower:
            doc_type = "Technical"
        else:
            doc_type = "Policy"

    # 2. Department Detection
    department = user_metadata.get("department")
    if not department:
        combined_text = (filename + " " + first_page_text[:1000]).lower()
        if "travel" in combined_text or "expense" in combined_text or "finance" in combined_text or "budget" in combined_text:
            department = "Finance"
        elif "cyber" in combined_text or "security" in combined_text or "it " in combined_text:
            department = "Security"
        elif "hr" in combined_text or "employee" in combined_text or "remote" in combined_text or "leave" in combined_text:
            department = "HR"
        else:
            department = "General"

    # 3. Version Detection
    version = user_metadata.get("version")
    if not version:
        version_match = re.search(r"v?(\d+\.\d+|\d{4})", filename, re.IGNORECASE)
        if version_match:
            version = f"v{version_match.group(1)}" if not version_match.group(1).startswith("v") else version_match.group(1)
        else:
            version = "v1.0"

    # 4. Effective Date Detection
    effective_date = user_metadata.get("effective_date")
    if not effective_date:
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})|((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})", first_page_text, re.IGNORECASE)
        if date_match:
            effective_date = date_match.group(0)
        else:
            effective_date = datetime.utcnow().strftime("%Y-%m-%d")

    # 5. Access Level
    access_level = user_metadata.get("access_level")
    if not access_level:
        text_lower = first_page_text[:500].lower()
        if "confidential" in text_lower or "top secret" in text_lower:
            access_level = "Confidential"
        elif "restricted" in text_lower or "internal only" in text_lower:
            access_level = "Restricted"
        elif "public" in text_lower:
            access_level = "Public"
        else:
            access_level = "Internal"

    return {
        "document_type": doc_type,
        "department": department,
        "version": version,
        "effective_date": effective_date,
        "access_level": access_level,
        "author": user_metadata.get("author", "Enterprise Compliance Office")
    }
