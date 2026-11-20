"""Evidence-based resume parser (PDF, DOCX, TXT) for RCIP NOC/TEER suggestions."""

import io
import re
from typing import Any, Dict, List

from backend.rcip_data import COMMON_NOC_CATALOG, ESDC_NOC_FINDER_URL

KNOWN_SKILLS = [
    "Python", "FastAPI", "Django", "Flask", "JavaScript", "TypeScript", "React", "Node.js",
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "Docker", "Kubernetes", "AWS", "Azure", "GCP",
    "Power BI", "Tableau", "Excel", "ETL", "Machine Learning", "PyTorch", "TensorFlow",
    "Linux", "Cisco", "CCNA", "Active Directory", "Firewall", "Cybersecurity",
    "Registered Nurse", "Nursing", "LPN", "Patient Care", "Medication Administration",
    "Early Childhood Education", "Childcare", "Welding", "MIG", "TIG", "CNC", "Machining",
    "Millwright", "Electrical", "Plumbing", "Carpentry", "Truck Driving", "AZ", "Class 1",
    "Heavy Equipment", "Accounting", "CPA", "Auditing", "Pharmacy", "Architecture",
]

CANADIAN_PROVINCE_HINTS = (
    "ontario", "nova scotia", "manitoba", "saskatchewan", "alberta", "british columbia",
    "canada", "pictou", "north bay", "sudbury", "timmins", "sault ste. marie",
    "thunder bay", "steinbach", "brandon", "moose jaw", "claresholm", "kootenay",
    "okanagan", "peace liard", "toronto", "vancouver", "calgary", "winnipeg", "halifax",
)


def extract_text_from_bytes(filename: str, content_bytes: bytes) -> str:
    """Extract UTF-8 text from .pdf, .docx, or plain text bytes."""
    lower = (filename or "").lower()
    if lower.endswith(".pdf"):
        import pdfplumber

        pages: List[str] = []
        with pdfplumber.open(io.BytesIO(content_bytes)) as pdf:
            for page in pdf.pages:
                txt = page.extract_text() or ""
                if txt.strip():
                    pages.append(txt)
        return "\n".join(pages)

    if lower.endswith(".docx"):
        import docx

        document = docx.Document(io.BytesIO(content_bytes))
        parts = [p.text for p in document.paragraphs if p.text.strip()]
        for table in document.tables:
            for row in table.rows:
                row_txt = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_txt:
                    parts.append(row_txt)
        return "\n".join(parts)

    return content_bytes.decode("utf-8", errors="replace")


def parse_resume_text(text: str) -> Dict[str, Any]:
    """Parse resume text without inventing skills/credentials, returning top 3 NOC suggestions."""
    cleaned = (text or "").strip()
    if not cleaned:
        return {
            "name": "",
            "email": "",
            "detected_skills": [],
            "education_level": "",
            "canadian_context_detected": False,
            "years_experience_mentioned": None,
            "suggested_nocs": [],
            "experience_summary": "",
            "extracted_notes": ["No text was found in the uploaded file or pasted resume."],
        }

    text_lower = cleaned.lower()

    # Name heuristic (first short non-email line)
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    name = ""
    if lines:
        first = lines[0]
        if len(first) <= 60 and "@" not in first and not re.search(r"\d{4}", first):
            name = first

    # Email
    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", cleaned)
    email = email_match.group(0) if email_match else ""

    # Skills strictly observed in resume text
    detected_skills: List[str] = []
    for skill in KNOWN_SKILLS:
        pattern = r"(?<!\w)" + re.escape(skill.lower()) + r"(?!\w)"
        if re.search(pattern, text_lower):
            detected_skills.append(skill)

    # Education level hint
    education_level = ""
    if re.search(r"\b(ph\.?d|doctorate)\b", text_lower):
        education_level = "Doctorate / Ph.D."
    elif re.search(r"\b(master'?s|m\.?sc|m\.?eng|mba|m\.?a\.?)\b", text_lower):
        education_level = "Master's Degree"
    elif re.search(r"\b(bachelor'?s|b\.?sc|b\.?eng|b\.?a\.?|b\.?tech)\b", text_lower):
        education_level = "Bachelor's Degree"
    elif re.search(r"\b(diploma|certificate|apprenticeship|associate degree)\b", text_lower):
        education_level = "Post-secondary Diploma / Certificate / Trade"
    elif re.search(r"\b(high school|secondary school|ssce|waec)\b", text_lower):
        education_level = "Secondary School Diploma"

    canadian_context = any(re.search(r"\b" + re.escape(tok) + r"\b", text_lower) for tok in CANADIAN_PROVINCE_HINTS)

    # Years experience mention
    years_match = re.findall(r"(\d{1,2})\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|work)", text_lower)
    years_exp = max((int(y) for y in years_match), default=None)

    # Top 3 NOC 2021 matches from COMMON_NOC_CATALOG
    scored_nocs = []
    for entry in COMMON_NOC_CATALOG:
        hits = []
        for kw in entry["keywords"]:
            pat = r"(?<!\w)" + re.escape(kw.lower()) + r"(?!\w)"
            if re.search(pat, text_lower):
                hits.append(kw)
        if hits:
            scored_nocs.append((len(hits), entry, hits))

    scored_nocs.sort(key=lambda item: (-item[0], item[1]["teer"]))
    suggested_nocs = [
        {
            "noc": item[1]["noc"],
            "title": item[1]["title"],
            "teer": item[1]["teer"],
            "sector": item[1]["sector"],
            "matched_keywords": item[2],
        }
        for item in scored_nocs[:3]
    ]

    summary = " ".join(cleaned.split())[:420]
    notes = [
        f"Verify that your actual job duties match the NOC lead statement and main duties on ESDC's NOC Finder ({ESDC_NOC_FINDER_URL}).",
        "RCIP requires at least 1,560 paid hours in the past 3 years (or an eligible local community graduate exemption).",
    ]
    if not suggested_nocs:
        notes.append("No automatic NOC match exceeded threshold — search your job title directly on ESDC's NOC Finder.")

    return {
        "name": name,
        "email": email,
        "detected_skills": detected_skills,
        "education_level": education_level,
        "canadian_context_detected": canadian_context,
        "years_experience_mentioned": years_exp,
        "suggested_nocs": suggested_nocs,
        "experience_summary": summary,
        "extracted_notes": notes,
    }


def parse_resume_file(filename: str, content_bytes: bytes) -> Dict[str, Any]:
    """Extract text from an uploaded resume file and return evidence-grounded NOC/TEER hints."""
    text = extract_text_from_bytes(filename, content_bytes)
    result = parse_resume_text(text)
    result["filename"] = filename
    return result
