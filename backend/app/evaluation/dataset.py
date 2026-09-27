import json
import os
from typing import List, Dict, Any

EVAL_DATASET_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "sample_data", "eval_dataset.json")

DEFAULT_EVAL_DATASET = [
    {
        "id": "eval-01",
        "question": "What is the international travel reimbursement limit?",
        "expected_doc_filename": "Travel_Policy_2025.pdf",
        "expected_page_number": 1,
        "expected_answer_keywords": ["$350", "350 USD", "per night", "hotel"],
        "category": "Travel Policy"
    },
    {
        "id": "eval-02",
        "question": "Compare the 2024 and 2025 travel policies.",
        "expected_doc_filename": "Travel_Policy_2025.pdf",
        "expected_page_number": 1,
        "expected_answer_keywords": ["5,000", "5000", "1,200", "1200", "Manager + Finance"],
        "category": "Comparison"
    },
    {
        "id": "eval-03",
        "question": "Are there conflicting policies regarding remote work?",
        "expected_doc_filename": "Cybersecurity_SOP_2025.pdf",
        "expected_page_number": 1,
        "expected_answer_keywords": ["conflict", "3 days", "2 days", "remote"],
        "category": "Conflict Detection"
    },
    {
        "id": "eval-04",
        "question": "What MFA requirement is enforced for remote access?",
        "expected_doc_filename": "Cybersecurity_SOP_2025.pdf",
        "expected_page_number": 1,
        "expected_answer_keywords": ["Multi-Factor Authentication", "MFA", "hardware key"],
        "category": "Security SOP"
    },
    {
        "id": "eval-05",
        "question": "How many days of paid vacation do employees accrue annually?",
        "expected_doc_filename": "Employee_Handbook_2025.pdf",
        "expected_page_number": 1,
        "expected_answer_keywords": ["20 days", "annual vacation"],
        "category": "HR Handbook"
    }
]


def load_eval_dataset() -> List[Dict[str, Any]]:
    if os.path.exists(EVAL_DATASET_FILE):
        try:
            with open(EVAL_DATASET_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
            
    # Save default if not present
    os.makedirs(os.path.dirname(EVAL_DATASET_FILE), exist_ok=True)
    with open(EVAL_DATASET_FILE, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_EVAL_DATASET, f, indent=2)
    return DEFAULT_EVAL_DATASET
