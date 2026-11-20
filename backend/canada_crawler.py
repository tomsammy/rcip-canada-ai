"""Live Canada.ca RCIP web crawler and offline verified seed snapshots."""

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from backend.config import OFFICIAL_CANADA_PAGES

USER_AGENT = "RCIP-Canada-AI/1.0 (+https://www.canada.ca)"


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_canada_page_html(
    html: str,
    url: str,
    track: str = "pilot",
    slug: str = "",
    title_fallback: str = "",
) -> Dict[str, Any]:
    """Parse an official Canada.ca HTML document into clean text, alert banner, modified date, and external links."""
    soup = BeautifulSoup(html or "", "html.parser")
    main = soup.find("main") or soup.body or soup

    # Remove script/style/nav/footer noise before text extraction
    for tag in main.find_all(["script", "style", "noscript"]):
        tag.decompose()

    h1 = main.find("h1")
    title = (
        h1.get_text(" ", strip=True)
        if h1
        else (soup.title.get_text(" ", strip=True) if soup.title else title_fallback)
    )
    title = re.sub(r"\s*-\s*Canada\.ca\s*$", "", title or title_fallback).strip()

    # Extract official alert/transition banners
    alerts: List[str] = []
    for sec in main.find_all(["section", "div"]):
        classes = " ".join(sec.get("class") or [])
        if "alert" in classes.split() or "alert-" in classes:
            txt = " ".join(sec.get_text(" ", strip=True).split())
            if txt and txt not in alerts:
                alerts.append(txt)
    alert_text = " | ".join(alerts)

    # Extract site last modified date
    site_last_modified = ""
    time_tag = main.find("time", attrs={"property": "dateModified"}) or soup.find("time")
    if time_tag:
        site_last_modified = time_tag.get_text(" ", strip=True)
    if not site_last_modified:
        raw_text = main.get_text(" ", strip=True)
        m = re.search(r"Date modified:\s*(\d{4}-\d{2}-\d{2})", raw_text)
        if m:
            site_last_modified = m.group(1)

    # Collect external community/portal links
    external_links: List[Dict[str, str]] = []
    seen_ext = set()
    for a in main.find_all("a", href=True):
        full = urljoin(url, a["href"])
        if full.startswith("http") and "canada.ca" not in full and full not in seen_ext:
            seen_ext.add(full)
            external_links.append({"text": a.get_text(" ", strip=True), "url": full})

    # Remove page details footer & feedback noise if present
    for cls in ("pagedetails", "gc-pg-hlpfl"):
        for node in main.find_all(class_=re.compile(cls)):
            node.decompose()

    lines = [line.strip() for line in main.get_text("\n").splitlines() if line.strip()]
    content_text = "\n".join(lines)

    return {
        "url": url,
        "track": track,
        "slug": slug,
        "title": title or title_fallback,
        "site_last_modified": site_last_modified,
        "alert_text": alert_text,
        "content_text": content_text,
        "content_hash": _hash_text(content_text),
        "external_links": external_links,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def crawl_official_canada_pages(timeout: int = 20) -> Dict[str, Any]:
    """Fetch all official RCIP Pilot and Permanent Program pages from Canada.ca."""
    pages: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    with httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        for meta in OFFICIAL_CANADA_PAGES:
            try:
                resp = client.get(meta["url"])
                if resp.status_code != 200:
                    errors.append(
                        {
                            "url": meta["url"],
                            "error": f"HTTP {resp.status_code}",
                        }
                    )
                    continue
                parsed = parse_canada_page_html(
                    resp.text,
                    url=meta["url"],
                    track=meta["track"],
                    slug=meta["slug"],
                    title_fallback=meta["title"],
                )
                pages.append(parsed)
            except Exception as exc:
                errors.append({"url": meta["url"], "error": str(exc)})

    return {
        "pages": pages,
        "errors": errors,
        "total_attempted": len(OFFICIAL_CANADA_PAGES),
        "total_fetched": len(pages),
    }


def _seed_entry(slug: str, track: str, title: str, url: str, alert_text: str, content_text: str) -> Dict[str, Any]:
    return {
        "url": url,
        "track": track,
        "slug": slug,
        "title": title,
        "site_last_modified": "2026-11-09",
        "alert_text": alert_text,
        "content_text": content_text,
        "content_hash": _hash_text(content_text),
        "fetched_at": "2026-11-09T00:00:00+00:00",
    }


_PILOT_ALERT = (
    "As of January 1, 2027, the Rural Community Immigration Pilot will close. "
    "If your community recommendation is dated December 31, 2026, or earlier, you must apply for permanent residence before it expires. "
    "If you don't have a recommendation under the pilot, explore the new permanent Rural Community Immigration Program."
)

# Verified offline baseline snapshots grounded directly in our Canada.ca inspection (2026-11-09)
SEED_CANADA_PAGES: List[Dict[str, Any]] = [
    _seed_entry(
        "pilot-overview",
        "pilot",
        "Rural Community Immigration Pilot",
        "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration.html",
        _PILOT_ALERT,
        (
            "The Rural Community Immigration Pilot offers permanent residence to skilled workers who want to work and settle in participating communities. "
            "Participating communities approve certain employers to hire skilled migrants for jobs that they cannot fill with local workers. "
            "As of January 1, 2027, the pilot closes. Recommendations dated December 31, 2026 or earlier must be used to apply before expiry. "
            "IRCC continues processing applications already received and eligible applicants can still apply for a 2-year optional work permit."
        ),
    ),
    _seed_entry(
        "permanent-overview",
        "permanent",
        "Rural Community Immigration Program",
        "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration-program.html",
        "Program opens January 1, 2027.",
        (
            "The Rural Community Immigration Program opens on January 1, 2027 as a permanent economic immigration program offering permanent residence (PR) "
            "to skilled workers who want to work and settle in participating rural communities. Participating communities designate employers to make qualifying job offers "
            "and issue community recommendations."
        ),
    ),
    _seed_entry(
        "pilot-eligibility",
        "pilot",
        "Who can apply (RCIP)",
        "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/eligibility.html",
        _PILOT_ALERT,
        (
            "To apply for permanent residence under RCIP, you must: "
            "1) obtain a valid recommendation certificate from a participating community; "
            "2) have a valid job offer from a designated employer in the community; "
            "3) have at least 1 year (1,560 hours) of related paid work experience in the past 3 years (or qualify for the local international graduate exemption); "
            "4) prove your language abilities by taking an approved test; "
            "5) have a Canadian educational credential or foreign Educational Credential Assessment (ECA); "
            "6) prove you have enough settlement funds to support yourself and your family (unless already working in Canada with a valid work permit)."
        ),
    ),
    _seed_entry(
        "pilot-work-experience",
        "pilot",
        "Work experience & Local Graduate Exemption",
        "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/eligibility/work-experience.html",
        _PILOT_ALERT,
        (
            "You need at least 1 year (1,560 hours) of continuous or equivalent paid work experience in the past 3 years (up to 30 hours/week counted; volunteer work, unpaid internships, and self-employment do not count). "
            "TEER compatibility: Offer TEER 0 or 1 requires experience in TEER 0, 1, 2, or 3; Offer TEER 2 requires TEER 1, 2, 3, or 4; Offer TEER 3 or 4 requires TEER 2, 3, or 4; Offer TEER 5 requires the exact same 5-digit NOC code. "
            "Healthcare exception: work experience in NOC 31301 (Registered Nurses, TEER 1) also qualifies for job offers in NOC 33102 (TEER 3) or NOC 44101 (TEER 4). "
            "Local international graduate exemption: exempt from 1,560 hours if you graduated full-time from a publicly funded post-secondary institution in the recommending community no more than 18 months before applying for PR, "
            "with a 2+ year credential (lived in community 16 of last 24 months) or Master's/PhD <=2 years (lived in community for entire studies), provided <=50% language study, <=50% distance learning, and no return-home scholarship."
        ),
    ),
    _seed_entry(
        "pilot-language-test",
        "pilot",
        "Language assessment (CLB / NCLC)",
        "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/eligibility/language-test.html",
        _PILOT_ALERT,
        (
            "Approved tests: English — CELPIP-General, IELTS General Training, PTE Core; French — TEF Canada, TCF Canada. Results must be less than 2 years old when you apply. "
            "Minimum CLB/NCLC across all 4 abilities depends on job offer TEER: TEER 0 or 1 requires CLB 6; TEER 2 or 3 requires CLB 5; TEER 4 or 5 requires CLB 4. "
            "IELTS General minimums: CLB 6 = R 5.0, W 5.5, L 5.5, S 5.5; CLB 5 = R 4.0, W 5.0, L 5.0, S 5.0; CLB 4 = R 3.5, W 4.0, L 4.5, S 4.0. "
            "PTE Core minimums: CLB 6 = R 51, W 60, L 50, S 59; CLB 5 = R 42, W 51, L 39, S 51; CLB 4 = R 33, W 41, L 28, S 42."
        ),
    ),
    _seed_entry(
        "pilot-education-assessment",
        "pilot",
        "Education assessment (ECA)",
        "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/eligibility/education-assessment.html",
        _PILOT_ALERT,
        (
            "Option 1: Canadian secondary school diploma or recognized Canadian post-secondary certificate, diploma, or degree. "
            "Option 2: Foreign credential with an Educational Credential Assessment (ECA) report less than 5 years old from WES, CES (U of T), ICAS, IQAS, or ICES. "
            "Regulated occupations: Architects (NOC 21200) needing a licence must use CACB (unless valid ECA issued before Oct 31, 2024); Physicians (NOC 31100, 31101, 31102) must use Medical Council of Canada (MCC); Pharmacists (NOC 31120) needing a licence must use PEBC."
        ),
    ),
    _seed_entry(
        "pilot-proof-funds",
        "pilot",
        "Settlement funds",
        "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/eligibility/proof-funds.html",
        _PILOT_ALERT,
        (
            "You do NOT need to show proof of settlement funds if you are already working in Canada with a valid work permit. "
            "Otherwise, you must prove unencumbered funds (bank statements, drafts, cheques, money orders) both when applying and when your PR visa is issued. "
            "Minimum CAD funds by family size (updated July 29, 2025): 1 = $10,507; 2 = $13,080; 3 = $16,080; 4 = $19,524; 5 = $22,143; 6 = $24,975; 7 = $27,806; add $2,831 for each additional family member. "
            "Family size includes yourself, your spouse/common-law partner, and all dependent children, even if Canadian citizens, permanent residents, or not accompanying you."
        ),
    ),
    _seed_entry(
        "pilot-job-offer",
        "pilot",
        "Get a job offer and a community recommendation",
        "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/job-offer.html",
        _PILOT_ALERT,
        (
            "14 participating communities: Pictou County (NS), North Bay (ON), Sudbury (ON), Timmins (ON), Sault Ste. Marie (ON), Thunder Bay (ON), "
            "Steinbach (MB), Altona/Rhineland (MB), Brandon (MB), Moose Jaw (SK), Claresholm (AB), West Kootenay (BC), North Okanagan Shuswap (BC), Peace Liard (BC). "
            "Each community designates local employers and posts priority sectors on its economic development website. Job offers must be full-time (>=30 paid hrs/wk), non-seasonal, indeterminate, with at least 75% of work inside community boundaries. "
            "Once you have a valid job offer, the designated employer submits your community recommendation application directly to the community."
        ),
    ),
    _seed_entry(
        "pilot-permanent-residence-apply",
        "pilot",
        "Apply for permanent residence via PR Portal",
        "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/permanent-residence/apply.html",
        _PILOT_ALERT,
        (
            "Apply online using the IRCC Permanent Residence (PR) Portal. Required forms include IMM 0246 (Document Checklist), IMM 0247 (Offer of Employment), "
            "IMM 0248 (Schedule 1 - RCIP), IMM 0008 (Generic Application Form), IMM 5669 (Schedule A Background/Declaration), IMM 5406 (Additional Family Information), "
            "IMM 5562 (Your Travels), plus IMM 5409 (Common-law Union), IMM 5604 (Minors), IMM 5476 (Representative), IMM 5475 (Release Personal Info) if applicable. "
            "Include police certificates, certified translations, PR photos, language test, ECA/education proof, work experience letters, and settlement funds proof."
        ),
    ),
    _seed_entry(
        "pilot-work-permit",
        "pilot",
        "Optional 2-year employer-specific work permit",
        "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/work-permit.html",
        _PILOT_ALERT,
        (
            "After applying for permanent residence under RCIP, you may apply for an optional 2-year employer-specific work permit so you can work for your designated employer while PR is processed. "
            "Your employer must give you an Offer of Employment number before you start. Your spouse or common-law partner can apply for an open work permit restricted to the same community. "
            "Instructions branch depending on whether you are applying from outside Canada or inside Canada."
        ),
    ),
    _seed_entry(
        "pilot-after-apply",
        "pilot",
        "After you apply (Biometrics, Medical, AOR)",
        "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/after-apply.html",
        _PILOT_ALERT,
        (
            "Ages 14 to 79 must give biometrics (fingerprints and photo) within 30 days of the instruction letter — even if biometrics were given previously for another application. "
            "You and your family members must complete immigration medical exams. Once you receive an Acknowledgement of Receipt (AOR) letter, track your status online and use the IRCC Webform to report contact or family updates."
        ),
    ),
    _seed_entry(
        "pilot-settle",
        "pilot",
        "Settling in Canada (Outside & Inside Canada)",
        "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/settle.html",
        _PILOT_ALERT,
        (
            "Outside Canada: use free pre-arrival settlement services and prepare for Canada Border Services Agency (CBSA) arrival. "
            "Inside Canada / after arrival: watch for your electronic Confirmation of Permanent Residence (e-COPR) email, upload your photo in the portal for your first PR card, "
            "and confirm your Canadian mailing address within 180 days using the online address notification tool."
        ),
    ),
]
