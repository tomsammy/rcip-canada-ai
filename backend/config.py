"""Application configuration and official Canada.ca source registry."""

import os
from pathlib import Path
from typing import Dict, List

IS_VERCEL = bool(os.environ.get("VERCEL"))
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
if not IS_VERCEL:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = os.environ.get(
    "RCIP_DB_PATH",
    "/tmp/rcip.db" if IS_VERCEL else str(DATA_DIR / "rcip.db"),
)
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", 8001))

PILOT_CLOSE_DATE = "2027-01-01"
PILOT_RECOMMENDATION_CUTOFF = "2026-12-31"

OFFICIAL_CANADA_PAGES: List[Dict[str, str]] = [
    # Pilot track (recommendations dated Dec 31, 2026 or earlier)
    {
        "slug": "pilot-overview",
        "track": "pilot",
        "title": "Rural Community Immigration Pilot - Overview",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration.html",
    },
    {
        "slug": "pilot-eligibility",
        "track": "pilot",
        "title": "RCIP Pilot - Who Can Apply (Eligibility)",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/eligibility.html",
    },
    {
        "slug": "pilot-work-experience",
        "track": "pilot",
        "title": "RCIP Pilot - Work Experience & Graduate Exemption",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/eligibility/work-experience.html",
    },
    {
        "slug": "pilot-language-test",
        "track": "pilot",
        "title": "RCIP Pilot - Language Assessment (CLB / NCLC)",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/eligibility/language-test.html",
    },
    {
        "slug": "pilot-education-assessment",
        "track": "pilot",
        "title": "RCIP Pilot - Education Assessment (ECA & Regulated Jobs)",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/eligibility/education-assessment.html",
    },
    {
        "slug": "pilot-proof-funds",
        "track": "pilot",
        "title": "RCIP Pilot - Settlement Funds",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/eligibility/proof-funds.html",
    },
    {
        "slug": "pilot-job-offer",
        "track": "pilot",
        "title": "RCIP Pilot - Job Offer & Community Recommendation",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/job-offer.html",
    },
    {
        "slug": "pilot-permanent-residence",
        "track": "pilot",
        "title": "RCIP Pilot - Apply for Permanent Residence Overview",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/permanent-residence.html",
    },
    {
        "slug": "pilot-permanent-residence-apply",
        "track": "pilot",
        "title": "RCIP Pilot - PR Portal Submission, Forms & Checklist",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/permanent-residence/apply.html",
    },
    {
        "slug": "pilot-work-permit",
        "track": "pilot",
        "title": "RCIP Pilot - Optional Work Permit While PR Processes",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/work-permit.html",
    },
    {
        "slug": "pilot-after-apply",
        "track": "pilot",
        "title": "RCIP Pilot - After You Apply (Biometrics, Medical, AOR)",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/after-apply.html",
    },
    {
        "slug": "pilot-settle",
        "track": "pilot",
        "title": "RCIP Pilot - Settling in Canada",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/settle.html",
    },
    # Permanent Program track (opens January 1, 2027)
    {
        "slug": "permanent-overview",
        "track": "permanent",
        "title": "Rural Community Immigration Program - Permanent Overview",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration-program.html",
    },
    {
        "slug": "permanent-eligibility",
        "track": "permanent",
        "title": "Permanent RCIP - Who Can Apply (Eligibility)",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration-program/eligibility.html",
    },
    {
        "slug": "permanent-job-offer",
        "track": "permanent",
        "title": "Permanent RCIP - Job Offer & Community Recommendation",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration-program/job-offer.html",
    },
    {
        "slug": "permanent-pr",
        "track": "permanent",
        "title": "Permanent RCIP - Apply for Permanent Residence",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration-program/permanent-residence.html",
    },
    {
        "slug": "permanent-work-permit",
        "track": "permanent",
        "title": "Permanent RCIP - Optional Work Permit",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration-program/work-permit.html",
    },
    {
        "slug": "permanent-after-apply",
        "track": "permanent",
        "title": "Permanent RCIP - After You Apply",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration-program/after-apply.html",
    },
    {
        "slug": "permanent-settle",
        "track": "permanent",
        "title": "Permanent RCIP - Settling in Canada",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration-program/settle.html",
    },
]
