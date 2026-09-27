import os

sample_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents")
os.makedirs(sample_dir, exist_ok=True)

docs = [
    {
        "filename": "Travel_Policy_2024.pdf",
        "text": """NEXUS ENTERPRISE SOLUTIONS
GLOBAL TRAVEL AND REIMBURSEMENT POLICY (2024 EDITION)
Document ID: POL-FIN-2024-v1
Effective Date: 2024-01-01
Access Level: Internal
Department: Finance

1. EXECUTIVE OVERVIEW
This policy establishes guidelines for all business travel incurred by employees of Nexus Enterprise Solutions during fiscal year 2024.

2. DOMESTIC ACCOMMODATION & MEAL ALLOWANCES
2.1 Hotel Allowance: Domestic hotel accommodation is reimbursed up to a maximum limit of 4000 INR per night for standard business class stays.
2.2 Daily Meal Allowance: Employees are entitled to a daily meal allowance of 1000 INR per day during active business travel.
2.3 Local Transit: Taxis and ride-hailing services are fully reimbursable upon submission of valid original invoices.

3. APPROVAL WORKFLOW
All domestic travel requests must be pre-approved by the employee's direct Line Manager at least 7 days prior to departure.

4. INTERNATIONAL TRAVEL ALLOWANCES
International travel reimbursement for hotel accommodation is capped at 250 USD per night. Daily allowance for international meals is 75 USD per day.
"""
    },
    {
        "filename": "Travel_Policy_2025.pdf",
        "text": """NEXUS ENTERPRISE SOLUTIONS
GLOBAL TRAVEL AND REIMBURSEMENT POLICY (2025 EDITION)
Document ID: POL-FIN-2025-v2
Effective Date: 2025-01-01
Access Level: Internal
Department: Finance
Supersedes: POL-FIN-2024-v1

1. EXECUTIVE OVERVIEW
This policy establishes updated guidelines for all business travel incurred by employees of Nexus Enterprise Solutions during fiscal year 2025.

2. DOMESTIC ACCOMMODATION & MEAL ALLOWANCES
2.1 Hotel Allowance: Domestic hotel accommodation reimbursement limit has been increased to 5000 INR per night for standard business class stays.
2.2 Daily Meal Allowance: Employees are entitled to an updated daily meal allowance of 1200 INR per day during active business travel.
2.3 Local Transit: Taxis and ride-hailing services are fully reimbursable upon submission of valid original invoices.

3. APPROVAL WORKFLOW
All domestic travel requests must be pre-approved by both the employee's direct Line Manager AND the Finance Department prior to booking.

4. INTERNATIONAL TRAVEL ALLOWANCES
International travel reimbursement for hotel accommodation is capped at 350 USD per night. Daily allowance for international meals is 100 USD per day.
"""
    },
    {
        "filename": "Remote_Work_Policy_2025.pdf",
        "text": """NEXUS ENTERPRISE SOLUTIONS
HYBRID AND REMOTE WORK POLICY 2025
Document ID: POL-HR-2025-v1
Effective Date: 2025-01-15
Access Level: Internal
Department: HR

1. PURPOSE & SCOPE
Nexus Enterprise Solutions values flexibility while maintaining high collaboration standards.

2. REMOTE WORK ELIGIBILITY & SCHEDULE
2.1 Remote Working Allowance: Employees in good performance standing may work remotely up to 3 days per week upon manager agreement.
2.2 Core Hours: All team members must remain available online between 10:00 AM and 4:00 PM EST regardless of physical location.
2.3 Workspace Setup: Employees working remotely must ensure a quiet, professional environment with reliable high-speed internet.
"""
    },
    {
        "filename": "Cybersecurity_SOP_2025.pdf",
        "text": """NEXUS ENTERPRISE SOLUTIONS
CYBERSECURITY OPERATIONAL STANDARD & REMOTE ACCESS GUIDELINES
Document ID: SOP-SEC-2025-v1
Effective Date: 2025-02-01
Access Level: Restricted
Department: Security

1. CYBERSECURITY MANDATE
Data protection and network integrity are paramount to enterprise operations.

2. REMOTE ACCESS & NETWORK SECURITY
2.1 Remote Working Restriction: For security audit compliance and endpoint protection, employees may work remotely up to 2 days per week.
2.2 Multi-Factor Authentication: All remote access to enterprise resources requires mandatory hardware key or MFA push authentication.
2.3 Device Security: Workstation screens must automatically lock after 3 minutes of inactivity. Storing company confidential data on personal devices is strictly prohibited.
"""
    },
    {
        "filename": "Employee_Handbook_2025.pdf",
        "text": """NEXUS ENTERPRISE SOLUTIONS
COMPREHENSIVE EMPLOYEE HANDBOOK 2025
Document ID: HB-HR-2025-v1
Effective Date: 2025-01-01
Access Level: Public
Department: General

1. WELCOME TO NEXUS
Nexus Enterprise Solutions delivers cutting-edge enterprise AI solutions to industry leaders worldwide.

2. CODE OF CONDUCT
Employees are expected to act with integrity, transparency, and professional excellence.

3. LEAVE & VACATION POLICY
All full-time employees accrue 20 days of paid annual vacation leave and 10 days of paid sick leave per calendar year.
"""
    }
]


def generate_simple_pdf_bytes(text_content: str) -> bytes:
    """Generates a valid, readable PDF byte string using PyMuPDF."""
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    rect = fitz.Rect(50, 50, 562, 742)
    page.insert_textbox(rect, text_content.strip(), fontsize=10, fontname="helv")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


if __name__ == "__main__":
    for doc in docs:
        pdf_bytes = generate_simple_pdf_bytes(doc["text"])
        target_path = os.path.join(sample_dir, doc["filename"])
        with open(target_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"Generated PDF document: {target_path}")
