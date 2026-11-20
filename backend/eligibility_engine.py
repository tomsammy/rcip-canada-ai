"""Honest, deterministic RCIP eligibility & gap roadmap engine grounded in Canada.ca rules."""

import re
from typing import Any, Dict, List, Optional

from backend.config import PILOT_CLOSE_DATE, PILOT_RECOMMENDATION_CUTOFF
from backend.rcip_data import (
    ADDITIONAL_FAMILY_MEMBER_CAD,
    ECA_ORGANIZATIONS,
    HEALTHCARE_NURSE_EXCEPTION_OFFER_NOCS,
    LANGUAGE_TEST_CHARTS,
    PARTICIPATING_COMMUNITIES,
    ROADMAP_STAGES,
    SETTLEMENT_FUNDS_TABLE,
    TEER_EXPERIENCE_MATRIX,
    TEER_MIN_CLB,
)

PILLAR_WEIGHTS: Dict[str, int] = {
    "work_experience": 20,
    "language": 20,
    "education": 15,
    "settlement_funds": 15,
    "job_offer": 15,
    "community_recommendation": 15,
}

URL_ELIGIBILITY = "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/eligibility.html"
URL_WORK = "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/eligibility/work-experience.html"
URL_LANGUAGE = "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/eligibility/language-test.html"
URL_EDUCATION = "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/eligibility/education-assessment.html"
URL_FUNDS = "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/eligibility/proof-funds.html"
URL_JOB_OFFER = "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/job-offer.html"
URL_PR_APPLY = "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration/permanent-residence/apply.html"
URL_PERMANENT_PROGRAM = "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/rural-franco-pilots/rural-immigration-program.html"


def _normalize_noc(code: Any) -> str:
    if code is None:
        return ""
    digits = re.sub(r"\D", "", str(code))
    return digits[:5] if len(digits) >= 5 else digits


def _to_float(val: Any) -> Optional[float]:
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _to_int(val: Any) -> Optional[int]:
    if val is None or val == "":
        return None
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


def compute_clb_from_test(
    test_type: str,
    reading: float,
    writing: float,
    listening: float,
    speaking: float,
) -> Dict[str, Any]:
    """Convert raw language test scores to official IRCC CLB/NCLC levels (4–10).

    The overall CLB/NCLC for RCIP is governed by the lowest score across all four abilities.
    """
    key = (test_type or "").strip().lower()
    chart = LANGUAGE_TEST_CHARTS.get(key)
    if not chart:
        return {
            "valid_test": False,
            "error": f"Unsupported test type '{test_type}'. Accepted: {', '.join(LANGUAGE_TEST_CHARTS.keys())}.",
            "per_skill_clb": {},
            "overall_clb": 0,
            "weakest_skills": [],
        }

    raw_scores = {
        "reading": float(reading),
        "writing": float(writing),
        "listening": float(listening),
        "speaking": float(speaking),
    }

    levels = chart["levels"]
    sorted_clbs = sorted(levels.keys(), reverse=True)
    per_skill: Dict[str, int] = {}

    for skill, score in raw_scores.items():
        matched_clb = 0
        for clb in sorted_clbs:
            if score >= levels[clb][skill]:
                matched_clb = clb
                break
        per_skill[skill] = matched_clb

    overall_clb = min(per_skill.values())
    weakest = [skill for skill, lvl in per_skill.items() if lvl == overall_clb]

    return {
        "valid_test": True,
        "test_type": key,
        "label": chart["label"],
        "language": chart["language"],
        "note": chart["note"],
        "raw_scores": raw_scores,
        "per_skill_clb": per_skill,
        "overall_clb": overall_clb,
        "weakest_skills": weakest,
    }


def required_settlement_funds(family_size: int) -> int:
    """Return exact minimum CAD settlement funds required by Canada.ca for the given family size."""
    if family_size < 1:
        raise ValueError("family_size must be at least 1")
    if family_size in SETTLEMENT_FUNDS_TABLE:
        return SETTLEMENT_FUNDS_TABLE[family_size]
    extra = family_size - 7
    return SETTLEMENT_FUNDS_TABLE[7] + extra * ADDITIONAL_FAMILY_MEMBER_CAD


def determine_program_track(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Route applicant between Pilot (recommendation <= 2026-12-31) and Permanent Program (>= 2027-01-01)."""
    has_rec = bool(profile.get("has_community_recommendation"))
    rec_date = str(profile.get("recommendation_date") or "").strip()

    if has_rec and rec_date and re.match(r"^\d{4}-\d{2}-\d{2}$", rec_date):
        if rec_date <= PILOT_RECOMMENDATION_CUTOFF:
            return {
                "track": "pilot",
                "label": "Rural Community Immigration Pilot (RCIP Pilot)",
                "summary": (
                    f"Your recommendation is dated {rec_date} (on or before Dec 31, 2026). "
                    "Submit your permanent residence application under the pilot rules before the certificate expires."
                ),
                "pilot_closes": PILOT_CLOSE_DATE,
                "url": URL_PR_APPLY,
            }
        return {
            "track": "permanent",
            "label": "Rural Community Immigration Program (Permanent — Opens Jan 1, 2027)",
            "summary": (
                f"Your recommendation date ({rec_date}) is on or after January 1, 2027. "
                "Apply through the permanent Rural Community Immigration Program."
            ),
            "pilot_closes": PILOT_CLOSE_DATE,
            "url": URL_PERMANENT_PROGRAM,
        }

    return {
        "track": "permanent",
        "label": "Rural Community Immigration Program (Permanent Transition — Opens Jan 1, 2027)",
        "summary": (
            "The RCIP Pilot closes on January 1, 2027. Without a community recommendation dated Dec 31, 2026 or earlier, "
            "plan your job offer and community recommendation for the permanent Rural Community Immigration Program."
        ),
        "pilot_closes": PILOT_CLOSE_DATE,
        "url": URL_PERMANENT_PROGRAM,
    }


def evaluate_work_experience(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate 1,560-hour paid experience, TEER/NOC rules, healthcare exception, or local graduate exemption."""
    weight = PILLAR_WEIGHTS["work_experience"]
    is_grad = bool(profile.get("is_local_graduate"))
    hours = _to_float(profile.get("paid_work_hours_last_3_years"))
    exp_teer = _to_int(profile.get("experience_teer"))
    exp_noc = _normalize_noc(profile.get("experience_noc_code"))
    offer_teer = _to_int(profile.get("target_job_teer"))
    offer_noc = _normalize_noc(profile.get("target_job_noc_code"))
    unpaid_or_self = bool(profile.get("work_was_self_employed_or_unpaid"))

    # 1. Check Local International Graduate Exemption first
    grad_reasons_failed: List[str] = []
    if is_grad:
        prog_type = str(profile.get("grad_program_type") or "").strip().lower()
        public_inst = bool(profile.get("grad_public_institution_in_community"))
        full_time = bool(profile.get("grad_full_time"))
        months_since = _to_float(profile.get("months_since_graduation"))
        lived_months = _to_float(profile.get("grad_lived_in_community_months"))
        lived_entire = bool(profile.get("grad_lived_entire_duration"))

        if not public_inst:
            grad_reasons_failed.append("Credential must be from a publicly funded Canadian post-secondary institution in the recommending community.")
        if not full_time:
            grad_reasons_failed.append("You must have studied full-time for the entire program.")
        if months_since is None or months_since > 18:
            grad_reasons_failed.append("Credential must have been received no more than 18 months before applying for PR.")
        if prog_type == "masters_phd":
            if not lived_entire:
                grad_reasons_failed.append("Master's/doctoral programs (2 years or less) require living in the community for the entire duration of studies.")
        elif prog_type == "2yr_plus":
            if lived_months is None or lived_months < 16:
                grad_reasons_failed.append("Programs of 2 years or longer require living in the community for at least 16 of the last 24 months while studying.")
        else:
            grad_reasons_failed.append("Select graduate program length ('2yr_plus' or 'masters_phd').")

        # Official disqualifiers
        if bool(profile.get("grad_over_half_language_study")):
            grad_reasons_failed.append("Exemption disqualified: English/French study made up more than half of the program.")
        if bool(profile.get("grad_over_half_distance_learning")):
            grad_reasons_failed.append("Exemption disqualified: distance learning made up more than half of the program.")
        if bool(profile.get("grad_return_home_scholarship")):
            grad_reasons_failed.append("Exemption disqualified: scholarship/fellowship requires returning to your home country.")

        if not grad_reasons_failed:
            return {
                "pillar": "work_experience",
                "title": "Work Experience",
                "status": "EXEMPT",
                "score": weight,
                "max_score": weight,
                "summary": "Exempt from the 1-year (1,560-hour) work experience rule as an eligible local international graduate.",
                "details": [
                    "Graduated full-time from a public post-secondary institution in the recommending community within the past 18 months.",
                    "Residency requirement and all three IRCC exclusion checks passed.",
                ],
                "gaps": [],
                "url": URL_WORK,
            }

    # 2. Check if user hasn't entered any work experience information at all
    if not is_grad and hours is None and exp_teer is None and not exp_noc and not unpaid_or_self:
        return {
            "pillar": "work_experience",
            "title": "Work Experience",
            "status": "INCOMPLETE",
            "score": 0,
            "max_score": weight,
            "summary": "Enter your paid work hours (last 3 years) and experience TEER/NOC, or mark Local Graduate Exemption.",
            "details": [],
            "gaps": [
                "Need at least 1 year (1,560 hours) of paid, non-self-employed related work experience in the past 3 years (or qualify for the local graduate exemption)."
            ],
            "url": URL_WORK,
        }

    gaps: List[str] = []
    details: List[str] = []
    if grad_reasons_failed:
        details.append("Local graduate exemption not met — checking standard 1,560-hour work experience fallback:")
        gaps.extend(grad_reasons_failed)

    if unpaid_or_self:
        gaps.append("Self-employment, volunteer work, and unpaid internships do NOT count toward the 1,560-hour requirement.")

    if hours is None or hours < 1560:
        have = int(hours or 0)
        gaps.append(f"Need at least 1,560 paid hours in the past 3 years (currently recorded: {have} hrs; missing {max(0, 1560 - have)} hrs).")
    else:
        details.append(f"Recorded {int(hours)} paid work hours in the past 3 years (>= 1,560 required).")

    # TEER / NOC matching
    healthcare_exception = (
        exp_noc == "31301"
        and offer_noc in HEALTHCARE_NURSE_EXCEPTION_OFFER_NOCS
    )
    if healthcare_exception:
        details.append(
            f"Healthcare worker exception applies: NOC 31301 (Registered Nurse) work experience qualifies for NOC {offer_noc} ({HEALTHCARE_NURSE_EXCEPTION_OFFER_NOCS[offer_noc]})."
        )
    elif offer_teer is None:
        if exp_teer is not None:
            details.append(f"Experience TEER {exp_teer} recorded — select a target job offer TEER to validate cross-TEER compatibility.")
        else:
            gaps.append("Specify both your past experience TEER/NOC and target job TEER/NOC.")
    elif offer_teer == 5:
        if not offer_noc or not exp_noc:
            gaps.append("Target TEER 5 occupations require your past work experience to be in the exact same 5-digit NOC code — enter both 5-digit NOC codes.")
        elif exp_noc != offer_noc:
            gaps.append(f"TEER 5 mismatch: job offer NOC {offer_noc} requires work experience in the exact same 5-digit NOC (yours: {exp_noc}).")
        else:
            details.append(f"TEER 5 exact 5-digit NOC match confirmed ({offer_noc}).")
    else:
        allowed_teers = TEER_EXPERIENCE_MATRIX.get(offer_teer, [])
        if exp_teer is None:
            gaps.append(f"Enter your work experience TEER (job offer TEER {offer_teer} requires experience in TEER {', '.join(map(str, allowed_teers))}).")
        elif exp_teer not in allowed_teers:
            gaps.append(
                f"TEER mismatch: a TEER {offer_teer} job offer requires experience in TEER {', '.join(map(str, allowed_teers))} (yours: TEER {exp_teer})."
            )
        else:
            details.append(f"Experience TEER {exp_teer} is compatible with target job offer TEER {offer_teer}.")

    # Determine status
    if not gaps and offer_teer is not None and (hours or 0) >= 1560 and not unpaid_or_self:
        return {
            "pillar": "work_experience",
            "title": "Work Experience",
            "status": "PASS",
            "score": weight,
            "max_score": weight,
            "summary": "Work experience hours and TEER/NOC rules satisfied.",
            "details": details,
            "gaps": [],
            "url": URL_WORK,
        }

    if unpaid_or_self or (offer_teer == 5 and exp_noc and offer_noc and exp_noc != offer_noc):
        status = "BLOCKED" if (hours or 0) >= 1560 else "ACTION_REQUIRED"
    elif hours is not None or exp_teer is not None or grad_reasons_failed:
        status = "ACTION_REQUIRED"
    else:
        status = "INCOMPLETE"

    return {
        "pillar": "work_experience",
        "title": "Work Experience",
        "status": status,
        "score": 0,
        "max_score": weight,
        "summary": gaps[0] if gaps else "Provide target job TEER to complete work experience check.",
        "details": details,
        "gaps": gaps,
        "url": URL_WORK,
    }


def evaluate_language(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate official language test scores (CLB/NCLC) and 2-year validity against job TEER."""
    weight = PILLAR_WEIGHTS["language"]
    offer_teer = _to_int(profile.get("target_job_teer"))
    required_clb = TEER_MIN_CLB.get(offer_teer) if offer_teer is not None else None
    test_type = str(profile.get("language_test_type") or "").strip().lower()
    test_age_months = _to_float(profile.get("language_test_age_months"))

    raw_r = _to_float(profile.get("lang_reading"))
    raw_w = _to_float(profile.get("lang_writing"))
    raw_l = _to_float(profile.get("lang_listening"))
    raw_s = _to_float(profile.get("lang_speaking"))
    direct_clb = _to_int(profile.get("clb_overall"))

    has_raw = all(v is not None for v in (raw_r, raw_w, raw_l, raw_s)) and bool(test_type)
    if not has_raw and direct_clb is None and not test_type:
        return {
            "pillar": "language",
            "title": "Language Proficiency (CLB / NCLC)",
            "status": "INCOMPLETE",
            "score": 0,
            "max_score": weight,
            "summary": "Enter your approved language test scores (CELPIP-General, IELTS General, PTE Core, TEF Canada, or TCF Canada).",
            "details": [
                f"Target TEER {offer_teer} requires CLB/NCLC {required_clb}." if required_clb else "Minimum CLB/NCLC: 6 for TEER 0/1, 5 for TEER 2/3, 4 for TEER 4/5."
            ],
            "gaps": ["Approved language test results (< 2 years old at PR submission) are required."],
            "url": URL_LANGUAGE,
        }

    gaps: List[str] = []
    details: List[str] = []
    overall_clb = 0
    per_skill: Dict[str, int] = {}

    if has_raw:
        conv = compute_clb_from_test(test_type, raw_r, raw_w, raw_l, raw_s)
        if not conv.get("valid_test"):
            gaps.append(conv.get("error", "Invalid language test type."))
        else:
            per_skill = conv["per_skill_clb"]
            overall_clb = conv["overall_clb"]
            details.append(
                f"{conv['label']}: R=CLB {per_skill['reading']}, W=CLB {per_skill['writing']}, L=CLB {per_skill['listening']}, S=CLB {per_skill['speaking']} -> Overall CLB {overall_clb}."
            )
    elif direct_clb is not None:
        overall_clb = direct_clb
        details.append(f"Reported lowest-skill CLB/NCLC: {overall_clb}.")
    else:
        gaps.append("Provide all 4 ability scores (Reading, Writing, Listening, Speaking) to compute your exact CLB/NCLC.")

    if test_age_months is not None and test_age_months >= 24:
        gaps.append(f"Language test results are {int(test_age_months)} months old — IRCC requires results to be less than 2 years (24 months) old when applying.")

    if required_clb is None:
        gaps.append("Select your target job offer TEER (0–5) to verify whether CLB 6, 5, or 4 is required.")
    elif has_raw or direct_clb is not None:
        if per_skill:
            failing = [f"{skill} (CLB {lvl} < {required_clb})" for skill, lvl in per_skill.items() if lvl < required_clb]
            if failing:
                gaps.append(f"Target TEER {offer_teer} requires at least CLB/NCLC {required_clb} in every ability. Below target: {', '.join(failing)}.")
            else:
                details.append(f"Meets or exceeds CLB/NCLC {required_clb} requirement for TEER {offer_teer}.")
        elif overall_clb < required_clb:
            gaps.append(f"CLB {overall_clb} is below the minimum CLB {required_clb} required for TEER {offer_teer}.")
        else:
            details.append(f"Meets CLB/NCLC {required_clb} requirement for TEER {offer_teer}.")

    if not gaps and required_clb is not None and overall_clb >= required_clb:
        return {
            "pillar": "language",
            "title": "Language Proficiency (CLB / NCLC)",
            "status": "PASS",
            "score": weight,
            "max_score": weight,
            "summary": f"Overall CLB/NCLC {overall_clb} meets the TEER {offer_teer} threshold (CLB {required_clb}).",
            "details": details,
            "gaps": [],
            "per_skill_clb": per_skill,
            "overall_clb": overall_clb,
            "url": URL_LANGUAGE,
        }

    return {
        "pillar": "language",
        "title": "Language Proficiency (CLB / NCLC)",
        "status": "ACTION_REQUIRED" if (has_raw or direct_clb is not None) else "INCOMPLETE",
        "score": 0,
        "max_score": weight,
        "summary": gaps[0] if gaps else "Complete language test scores.",
        "details": details,
        "gaps": gaps,
        "per_skill_clb": per_skill,
        "overall_clb": overall_clb,
        "url": URL_LANGUAGE,
    }


def evaluate_education(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate Canadian credential or foreign ECA (<5 years) plus regulated profession rules."""
    weight = PILLAR_WEIGHTS["education"]
    origin = str(profile.get("education_origin") or "").strip().lower()
    has_eca = bool(profile.get("has_eca"))
    eca_org = str(profile.get("eca_organization") or "").strip()
    eca_age_years = _to_float(profile.get("eca_age_years"))
    offer_noc = _normalize_noc(profile.get("target_job_noc_code"))

    if not origin:
        return {
            "pillar": "education",
            "title": "Education / ECA",
            "status": "INCOMPLETE",
            "score": 0,
            "max_score": weight,
            "summary": "Select whether your highest credential was completed in Canada or outside Canada.",
            "details": [],
            "gaps": ["Provide Canadian secondary/post-secondary proof or a valid foreign ECA report (< 5 years old)."],
            "url": URL_EDUCATION,
        }

    details: List[str] = []
    gaps: List[str] = []

    if origin == "canada":
        details.append("Canadian secondary or post-secondary credential from a designated learning institution.")
    elif origin == "foreign":
        if not has_eca:
            gaps.append("Foreign credentials require an Educational Credential Assessment (ECA) from WES, CES, ICAS, IQAS, ICES, or a designated professional body.")
        else:
            if eca_age_years is not None and eca_age_years >= 5:
                gaps.append(f"Your ECA is {eca_age_years:g} years old — it must be less than 5 years old on the date you apply.")
            else:
                details.append(f"Valid foreign ECA report recorded{f' ({eca_org})' if eca_org else ''}.")

        # Special regulated NOC checks
        specialty = ECA_ORGANIZATIONS["regulated_specialties"].get(offer_noc)
        if specialty:
            expected_body = specialty["body"]
            details.append(f"Regulated occupation notice — {specialty['occupation']}: {specialty['rule']}")
            if eca_org and expected_body.split(" (")[0].lower() not in eca_org.lower() and "cacb" not in eca_org.lower() and "mcc" not in eca_org.lower() and "pebc" not in eca_org.lower():
                details.append(f"Verify if licensure requires an ECA specifically from {expected_body}.")
    else:
        gaps.append("Education origin must be 'canada' or 'foreign'.")

    if not gaps:
        return {
            "pillar": "education",
            "title": "Education / ECA",
            "status": "PASS",
            "score": weight,
            "max_score": weight,
            "summary": "Education proof requirement satisfied.",
            "details": details,
            "gaps": [],
            "url": URL_EDUCATION,
        }

    return {
        "pillar": "education",
        "title": "Education / ECA",
        "status": "ACTION_REQUIRED",
        "score": 0,
        "max_score": weight,
        "summary": gaps[0],
        "details": details,
        "gaps": gaps,
        "url": URL_EDUCATION,
    }


def evaluate_settlement_funds(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate CAD settlement funds or valid Canadian work permit exemption."""
    weight = PILLAR_WEIGHTS["settlement_funds"]
    in_canada_wp = bool(profile.get("in_canada_valid_work_permit"))
    family_size = _to_int(profile.get("family_size"))
    available_funds = _to_float(profile.get("available_funds_cad"))

    if in_canada_wp:
        return {
            "pillar": "settlement_funds",
            "title": "Settlement Funds",
            "status": "EXEMPT",
            "score": weight,
            "max_score": weight,
            "required_cad": 0,
            "summary": "Exempt from proof of settlement funds because you are already working in Canada with a valid work permit.",
            "details": ["Keep a copy of your valid Canadian work permit ready for PR Portal upload."],
            "gaps": [],
            "url": URL_FUNDS,
        }

    if family_size is None and available_funds is None:
        return {
            "pillar": "settlement_funds",
            "title": "Settlement Funds",
            "status": "INCOMPLETE",
            "score": 0,
            "max_score": weight,
            "required_cad": None,
            "summary": "Enter your family size and available unencumbered CAD funds (or confirm valid Canadian work permit).",
            "details": [
                "Family size includes yourself, your spouse/common-law partner, and all dependent children — even if Canadian citizens, PRs, or non-accompanying."
            ],
            "gaps": ["Proof of unencumbered settlement funds is required unless working in Canada on a valid work permit."],
            "url": URL_FUNDS,
        }

    effective_size = max(1, family_size or 1)
    required_cad = required_settlement_funds(effective_size)
    details = [
        f"Family size {effective_size} requires CAD ${required_cad:,} (Canada.ca table updated July 29, 2025).",
        "Must include spouse/partner and all dependent children even if Canadian citizens, PRs, or not accompanying you.",
    ]

    if available_funds is None:
        return {
            "pillar": "settlement_funds",
            "title": "Settlement Funds",
            "status": "ACTION_REQUIRED",
            "score": 0,
            "max_score": weight,
            "required_cad": required_cad,
            "summary": f"Need CAD ${required_cad:,} for family size {effective_size} — enter available unencumbered funds.",
            "details": details,
            "gaps": [f"Provide bank statements/drafts proving at least CAD ${required_cad:,} unencumbered by debts."],
            "url": URL_FUNDS,
        }

    if available_funds >= required_cad:
        return {
            "pillar": "settlement_funds",
            "title": "Settlement Funds",
            "status": "PASS",
            "score": weight,
            "max_score": weight,
            "required_cad": required_cad,
            "available_cad": int(available_funds),
            "summary": f"Available CAD ${int(available_funds):,} meets the CAD ${required_cad:,} requirement for family size {effective_size}.",
            "details": details,
            "gaps": [],
            "url": URL_FUNDS,
        }

    shortfall = int(required_cad - available_funds)
    return {
        "pillar": "settlement_funds",
        "title": "Settlement Funds",
        "status": "ACTION_REQUIRED",
        "score": 0,
        "max_score": weight,
        "required_cad": required_cad,
        "available_cad": int(available_funds),
        "shortfall_cad": shortfall,
        "summary": f"Settlement funds shortfall: CAD ${shortfall:,} below the CAD ${required_cad:,} minimum.",
        "details": details,
        "gaps": [f"Increase unencumbered liquid settlement funds by CAD ${shortfall:,} to reach CAD ${required_cad:,}."],
        "url": URL_FUNDS,
    }


def evaluate_job_offer(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate genuine, full-time, non-seasonal, indeterminate designated employer job offer."""
    weight = PILLAR_WEIGHTS["job_offer"]
    has_offer = bool(profile.get("has_job_offer"))

    if not has_offer:
        return {
            "pillar": "job_offer",
            "title": "Designated Employer Job Offer",
            "status": "INCOMPLETE" if not profile.get("target_community_id") and not profile.get("education_origin") and profile.get("paid_work_hours_last_3_years") is None else "ACTION_REQUIRED",
            "score": 0,
            "max_score": weight,
            "summary": "No designated employer job offer yet — target the 14 participating RCIP communities.",
            "details": ["Job offers must be full-time (>=30 paid hrs/wk), non-seasonal, indeterminate, from a designated employer with >=75% of work inside community boundaries."],
            "gaps": ["Secure a qualifying job offer from a designated employer in one of the 14 RCIP communities (IMM 0247)."],
            "url": URL_JOB_OFFER,
        }

    checks = [
        ("offer_from_designated_employer", "Employer must be officially designated by the participating community's EDO."),
        ("offer_full_time_30h", "Job offer must be full-time (at least 30 paid hours per week)."),
        ("offer_non_seasonal", "Job offer must be non-seasonal (year-round)."),
        ("offer_indeterminate", "Job offer must be indeterminate (no set end date)."),
        ("offer_inside_community", "At least 75% of the work must take place inside the participating community boundaries."),
    ]
    failed = [msg for key, msg in checks if not bool(profile.get(key))]

    if not failed:
        return {
            "pillar": "job_offer",
            "title": "Designated Employer Job Offer",
            "status": "PASS",
            "score": weight,
            "max_score": weight,
            "summary": "Qualifying designated employer job offer criteria confirmed.",
            "details": ["All 5 IRCC job offer conditions satisfied (designated, >=30 hrs/wk, non-seasonal, indeterminate, >=75% in community)."],
            "gaps": [],
            "url": URL_JOB_OFFER,
        }

    return {
        "pillar": "job_offer",
        "title": "Designated Employer Job Offer",
        "status": "BLOCKED",
        "score": 0,
        "max_score": weight,
        "summary": f"Job offer has {len(failed)} disqualifying issue(s) under Canada.ca rules.",
        "details": [],
        "gaps": failed,
        "url": URL_JOB_OFFER,
    }


def evaluate_recommendation(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate community recommendation certificate and Pilot vs Jan 1, 2027 Permanent track."""
    weight = PILLAR_WEIGHTS["community_recommendation"]
    has_rec = bool(profile.get("has_community_recommendation"))
    track_info = determine_program_track(profile)
    community_id = str(profile.get("target_community_id") or "").strip()
    community_obj = next((c for c in PARTICIPATING_COMMUNITIES if c["id"] == community_id), None)

    if not has_rec:
        if not profile.get("has_job_offer") and not community_id and not profile.get("education_origin") and profile.get("paid_work_hours_last_3_years") is None:
            status = "INCOMPLETE"
        else:
            status = "ACTION_REQUIRED"
        return {
            "pillar": "community_recommendation",
            "title": "Community Recommendation",
            "status": status,
            "score": 0,
            "max_score": weight,
            "track_info": track_info,
            "summary": "Pending community recommendation from the local economic development organization.",
            "details": [track_info["summary"]],
            "gaps": ["After securing a designated job offer, your employer submits your community recommendation application to the EDO."],
            "url": track_info["url"],
        }

    rec_date = str(profile.get("recommendation_date") or "").strip()
    details = [track_info["summary"]]
    if community_obj:
        details.append(f"Recommending community: {community_obj['name']}, {community_obj['province']} ({community_obj['edo_name']}).")

    gaps: List[str] = []
    if not rec_date:
        gaps.append("Enter the issuance date on your Community Recommendation Certificate to confirm Pilot vs Jan 1, 2027 Permanent Program routing.")

    return {
        "pillar": "community_recommendation",
        "title": "Community Recommendation",
        "status": "PASS" if not gaps else "ACTION_REQUIRED",
        "score": weight if not gaps else 0,
        "max_score": weight,
        "track_info": track_info,
        "summary": track_info["label"] if not gaps else gaps[0],
        "details": details,
        "gaps": gaps,
        "url": track_info["url"],
    }


def evaluate_rcip_eligibility(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Run complete honest multi-pillar RCIP eligibility evaluation and prioritized action roadmap."""
    safe_profile = dict(profile or {})
    track_info = determine_program_track(safe_profile)

    pillars = [
        evaluate_work_experience(safe_profile),
        evaluate_language(safe_profile),
        evaluate_education(safe_profile),
        evaluate_settlement_funds(safe_profile),
        evaluate_job_offer(safe_profile),
        evaluate_recommendation(safe_profile),
    ]

    total_score = sum(p["score"] for p in pillars)
    statuses = {p["pillar"]: p["status"] for p in pillars}

    if all(p["status"] == "INCOMPLETE" for p in pillars):
        overall_status = "INCOMPLETE"
        verdict = "Profile Incomplete — Enter your background to calculate honest RCIP readiness."
    elif any(p["status"] == "BLOCKED" for p in pillars):
        overall_status = "BLOCKED"
        verdict = "Blocked — One or more conditions violate official Canada.ca rules and must be resolved."
    elif total_score == 100:
        overall_status = "READY_TO_APPLY_PR"
        verdict = f"Ready for PR Application ({track_info['label']}) — All 6 core pillars satisfied."
    elif (
        statuses["work_experience"] in ("PASS", "EXEMPT")
        and statuses["language"] == "PASS"
        and statuses["education"] == "PASS"
        and statuses["settlement_funds"] in ("PASS", "EXEMPT")
    ):
        overall_status = "ELIGIBLE_NEEDS_JOB_AND_RECOMMENDATION"
        verdict = "Core Applicant Criteria Met — Focus on securing a Designated Employer Job Offer & Community Recommendation."
    else:
        overall_status = "CLOSING_GAPS"
        verdict = f"In Progress ({total_score}/100) — Resolve the prioritized gaps below before applying."

    # Prioritize action plan: BLOCKED first, then core credentials, then job offer & recommendation
    priority_rank = {"BLOCKED": 0, "ACTION_REQUIRED": 1, "INCOMPLETE": 2}
    action_plan: List[Dict[str, str]] = []
    for p in sorted(pillars, key=lambda x: priority_rank.get(x["status"], 9)):
        if p["status"] in ("PASS", "EXEMPT"):
            continue
        priority_label = "BLOCKING" if p["status"] == "BLOCKED" else ("REQUIRED" if p["status"] == "ACTION_REQUIRED" else "START")
        for gap in p["gaps"]:
            action_plan.append(
                {
                    "priority": priority_label,
                    "pillar": p["title"],
                    "action": gap,
                    "url": p["url"],
                }
            )

    in_canada = bool(safe_profile.get("currently_in_canada")) or bool(safe_profile.get("in_canada_valid_work_permit"))
    applicant_context = {
        "location_branch": "inside_canada" if in_canada else "outside_canada",
        "funds_exempt": statuses["settlement_funds"] == "EXEMPT",
        "local_grad_exempt": statuses["work_experience"] == "EXEMPT",
        "program_track": track_info["track"],
        "has_spouse": ( _to_int(safe_profile.get("family_size")) or 1 ) >= 2 or bool(safe_profile.get("has_spouse")),
    }

    return {
        "readiness_score": total_score,
        "overall_status": overall_status,
        "verdict": verdict,
        "program_track": track_info,
        "applicant_context": applicant_context,
        "pillars": pillars,
        "action_plan": action_plan,
    }


def build_tailored_roadmap(
    profile: Dict[str, Any],
    progress_map: Dict[str, Dict[str, Any]],
    evaluation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the 6-stage Canada.ca RCIP roadmap tailored to applicant branches & checklist state."""
    eval_result = evaluation or evaluate_rcip_eligibility(profile)
    ctx = eval_result["applicant_context"]

    def _item_applies(applies_to: str) -> bool:
        if applies_to == "all":
            return True
        if applies_to == "outside_canada":
            return ctx["location_branch"] == "outside_canada"
        if applies_to == "inside_canada":
            return ctx["location_branch"] == "inside_canada"
        if applies_to == "funds_exempt":
            return ctx["funds_exempt"]
        if applies_to == "requires_funds":
            return not ctx["funds_exempt"]
        if applies_to == "local_graduate":
            return ctx["local_grad_exempt"]
        if applies_to == "standard_experience":
            return not ctx["local_grad_exempt"]
        if applies_to == "pilot_track":
            return ctx["program_track"] == "pilot"
        if applies_to == "permanent_track":
            return ctx["program_track"] == "permanent"
        if applies_to == "has_spouse":
            return ctx["has_spouse"]
        return True

    stages_out: List[Dict[str, Any]] = []
    total_items = 0
    completed_items = 0

    for stage in ROADMAP_STAGES:
        items_out: List[Dict[str, Any]] = []
        stage_done = 0
        for item in stage["items"]:
            applicable = _item_applies(item["applies_to"])
            saved = progress_map.get(item["id"], {})
            is_done = bool(saved.get("completed", False))
            if applicable:
                total_items += 1
                if is_done:
                    completed_items += 1
                    stage_done += 1
            items_out.append(
                {
                    **item,
                    "applicable": applicable,
                    "completed": is_done,
                    "notes": saved.get("notes", ""),
                    "target_date": saved.get("target_date", ""),
                    "updated_at": saved.get("updated_at", ""),
                }
            )

        active_count = sum(1 for x in items_out if x["applicable"])
        stages_out.append(
            {
                "stage_id": stage["stage_id"],
                "order": stage["order"],
                "title": stage["title"],
                "summary": stage["summary"],
                "official_url": stage["pilot_url"] if ctx["program_track"] == "pilot" else stage["permanent_url"],
                "pilot_url": stage["pilot_url"],
                "permanent_url": stage["permanent_url"],
                "completed_count": stage_done,
                "active_count": active_count,
                "items": items_out,
            }
        )

    return {
        "program_track": eval_result["program_track"],
        "applicant_context": ctx,
        "completed_items": completed_items,
        "total_items": total_items,
        "completion_percent": round((completed_items / total_items) * 100) if total_items else 0,
        "stages": stages_out,
    }
