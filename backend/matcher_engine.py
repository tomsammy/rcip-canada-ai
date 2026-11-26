"""Honest cross-country immigration & PR pathway matcher across 20 countries."""

from typing import Any, Dict, List

from backend.countries_data import COUNTRIES_CATALOG

_EDU_RANK = {
    "": 0,
    "none": 0,
    "secondary": 1,
    "high_school": 1,
    "diploma": 2,
    "associate": 2,
    "bachelors": 3,
    "bachelor": 3,
    "masters": 4,
    "master": 4,
    "phd": 5,
    "doctorate": 5,
}

_LANG_RANK = {
    "": 0,
    "none": 0,
    "basic": 1,
    "intermediate": 2,
    "fluent": 3,
}

_STRICT_SECTOR_PATHWAYS = {
    "uk-health-care": {"healthcare"},
    "ee-ict-trp": {"tech"},
}


def _to_float(val: Any) -> float:
    if val is None or val == "":
        return 0.0
    try:
        return max(0.0, float(val))
    except (TypeError, ValueError):
        return 0.0


def _has_profile_input(profile: Dict[str, Any]) -> bool:
    if not profile:
        return False
    checks = [
        bool((profile.get("education_level") or "").strip()),
        bool((profile.get("field") or "").strip()),
        _to_float(profile.get("years_experience")) > 0,
        bool((profile.get("english_level") or "").strip()),
        bool((profile.get("french_level") or "").strip()),
        bool((profile.get("german_level") or "").strip()),
        bool((profile.get("spanish_level") or "").strip()),
        bool((profile.get("portuguese_level") or "").strip()),
        _to_float(profile.get("relocation_budget_usd")) > 0,
        _to_float(profile.get("monthly_remote_income_usd")) > 0,
        bool(profile.get("has_foreign_job_offer")),
    ]
    return any(checks)


def match_global_pathways(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Score and rank pathways across all 20 countries strictly from stated profile facts."""
    safe = dict(profile or {})
    if not _has_profile_input(safe):
        return {
            "status": "INCOMPLETE",
            "message": "Enter your education, field, work experience, language proficiency, and budget to match across all 20 countries.",
            "total_pathways": 0,
            "top_matches": [],
            "viable_with_job_offer": [],
            "explore_and_prepare": [],
            "all_matches": [],
        }

    edu_key = str(safe.get("education_level") or "").strip().lower()
    edu_rank = _EDU_RANK.get(edu_key, 0)
    exp_years = _to_float(safe.get("years_experience"))
    field = str(safe.get("field") or "").strip().lower()
    eng_rank = _LANG_RANK.get(str(safe.get("english_level") or "").strip().lower(), 0)
    fr_rank = _LANG_RANK.get(str(safe.get("french_level") or "").strip().lower(), 0)
    de_rank = _LANG_RANK.get(str(safe.get("german_level") or "").strip().lower(), 0)
    es_rank = _LANG_RANK.get(str(safe.get("spanish_level") or "").strip().lower(), 0)
    pt_rank = _LANG_RANK.get(str(safe.get("portuguese_level") or "").strip().lower(), 0)
    lang_ranks = {
        "english": eng_rank,
        "french": fr_rank,
        "german": de_rank,
        "spanish": es_rank,
        "portuguese": pt_rank,
    }
    budget_usd = _to_float(safe.get("relocation_budget_usd"))
    remote_income = _to_float(safe.get("monthly_remote_income_usd"))
    has_offer = bool(safe.get("has_foreign_job_offer"))
    age = _to_float(safe.get("age"))

    target_region = str(safe.get("target_region") or "all").strip().lower()
    target_country = str(safe.get("target_country") or "all").strip().lower()

    all_matches: List[Dict[str, Any]] = []

    for country in COUNTRIES_CATALOG:
        if target_region not in ("", "all") and country["region"].lower() != target_region:
            continue
        if target_country not in ("", "all") and country["id"].lower() != target_country:
            continue

        for p in country["pathways"]:
            why: List[str] = []
            gaps: List[str] = []
            blocked = False

            # 1. Education (20 pts)
            req_edu_rank = _EDU_RANK.get(p["min_edu"], 1)
            if edu_rank == 0:
                edu_pts = 0
                gaps.append(f"Specify your education level (minimum expected: {p['min_edu'].title()}).")
            elif edu_rank >= req_edu_rank:
                edu_pts = 20
                why.append(f"Education meets {p['min_edu'].title()} requirement.")
            elif edu_rank == req_edu_rank - 1:
                edu_pts = 8
                gaps.append(f"Pathway prefers {p['min_edu'].title()} (higher credential or specialist experience equivalence needed).")
            else:
                edu_pts = 0
                gaps.append(f"Requires {p['min_edu'].title()} qualification.")

            # 2. Experience & Sector Fit (25 pts)
            req_exp = p["min_exp_years"]
            if exp_years >= req_exp:
                exp_pts = 12
                if req_exp > 0:
                    why.append(f"{exp_years:g} yrs experience satisfies >= {req_exp:g} yr rule.")
            elif req_exp > 0 and exp_years >= req_exp * 0.6:
                exp_pts = 6
                gaps.append(f"Need {req_exp:g}+ years experience (currently {exp_years:g} yrs).")
            else:
                exp_pts = 0
                gaps.append(f"Requires at least {req_exp:g} years of relevant experience.")

            strict_allowed = _STRICT_SECTOR_PATHWAYS.get(p["id"])
            if not field:
                field_pts = 5
                gaps.append("Select your profession/field for tighter occupation alignment.")
            elif field in p["fields"]:
                field_pts = 13
                why.append(f"Field ({field.title()}) aligns with priority/eligible tracks.")
            elif strict_allowed and field not in strict_allowed:
                field_pts = 0
                blocked = True
                gaps.append(f"This pathway is restricted to {', '.join(sorted(strict_allowed)).title()} roles.")
            else:
                field_pts = 4
                gaps.append(f"Field '{field.title()}' is outside primary target list ({', '.join(p['fields'][:3])}).")

            # 3. Language Alignment (20 pts)
            langs = p["languages"]
            lang_pts = 0
            if langs == ["french"]:
                if fr_rank >= 2:
                    lang_pts = 20
                    why.append("Intermediate/fluent French unlocks this Francophone pathway.")
                elif fr_rank == 1:
                    lang_pts = 6
                    gaps.append("Requires intermediate French (NCLC 5+ on TEF/TCF Canada).")
                else:
                    lang_pts = 0
                    blocked = True
                    gaps.append("French proficiency (NCLC 5+) is mandatory for this pathway.")
            else:
                best_rank = max((lang_ranks.get(lang, 0) for lang in langs), default=0)
                if best_rank >= 3:
                    lang_pts = 20
                    why.append("Strong language proficiency meets threshold.")
                elif best_rank == 2:
                    lang_pts = 14
                    why.append("Intermediate language level is competitive for most streams.")
                elif best_rank == 1:
                    lang_pts = 6
                    gaps.append("Improve language proficiency to intermediate/CLB 5–7+ for PR eligibility.")
                else:
                    lang_pts = 0
                    gaps.append(f"Add proficiency in {', '.join(l.title() for l in langs)}.")

            # Age advisory for Express Entry (still honest)
            if p["id"] == "ca-express-entry" and age > 40:
                gaps.append("Note: Express Entry CRS age points drop after 30; strong French or PNP/RCIP may score higher.")

            # 4. Accessibility: Job Offer / Remote Income / Self-Petition (20 pts)
            req_remote = p["min_remote_income_usd"]
            needs_offer = p["requires_job_offer"]
            if req_remote > 0:
                if remote_income >= req_remote:
                    access_pts = 20
                    why.append(f"Remote income (${int(remote_income):,}/mo) meets ~${req_remote:,}/mo threshold.")
                elif remote_income >= req_remote * 0.75:
                    access_pts = 10
                    gaps.append(f"Remote income (~${int(remote_income):,}/mo) is slightly below the ~${req_remote:,}/mo minimum.")
                else:
                    access_pts = 0
                    gaps.append(f"Requires ~US${req_remote:,}/month verified foreign remote income (or savings option for Brazil).")
            elif needs_offer:
                if has_offer:
                    access_pts = 20
                    why.append("Stated foreign job offer satisfies sponsor-driven entry.")
                else:
                    access_pts = 6
                    gaps.append("Requires securing a qualifying job offer from an approved/designated employer.")
            else:
                access_pts = 20
                why.append("No job offer required upfront to apply/qualify.")

            # 5. Relocation Budget / Settlement Funds (15 pts)
            req_budget = p["min_budget_usd"]
            if budget_usd >= req_budget:
                budget_pts = 15
                why.append(f"Budget (${int(budget_usd):,}) covers estimated ~${req_budget:,} settlement/fee minimum.")
            elif budget_usd >= req_budget * 0.65:
                budget_pts = 8
                gaps.append(f"Budget (${int(budget_usd):,}) is slightly under estimated ~${req_budget:,} (shortfall ~${int(req_budget - budget_usd):,}).")
            else:
                budget_pts = 2 if budget_usd > 0 else 0
                gaps.append(f"Estimated settlement/tuition/fee minimum is ~US${req_budget:,} (shortfall ~US${int(max(0, req_budget - budget_usd)):,}).")

            total_score = edu_pts + exp_pts + field_pts + lang_pts + access_pts + budget_pts
            if blocked:
                total_score = min(total_score, 35)

            if total_score >= 70 and (not needs_offer or has_offer) and not blocked:
                fit_tier = "STRONG_MATCH"
            elif needs_offer and not has_offer and not blocked and (edu_pts + exp_pts + field_pts + lang_pts + budget_pts) >= 52:
                fit_tier = "VIABLE_WITH_JOB_OFFER"
            else:
                fit_tier = "PREPARE_GAPS"

            all_matches.append(
                {
                    "country_id": country["id"],
                    "country_name": country["name"],
                    "country_code": country["code"],
                    "flag": country["flag"],
                    "region": country["region"],
                    "pathway_id": p["id"],
                    "pathway_name": p["name"],
                    "category": p["category"],
                    "leads_to_pr": p["leads_to_pr"],
                    "requires_job_offer": needs_offer,
                    "threshold_label": p["threshold_label"],
                    "official_url": p["official_url"],
                    "has_deep_engine": p["has_deep_engine"],
                    "score": int(total_score),
                    "fit_tier": fit_tier,
                    "why_it_fits": why,
                    "gaps_to_close": gaps,
                }
            )

    tier_order = {"STRONG_MATCH": 0, "VIABLE_WITH_JOB_OFFER": 1, "PREPARE_GAPS": 2}
    all_matches.sort(key=lambda m: (tier_order.get(m["fit_tier"], 9), -m["score"], m["country_name"]))

    top_matches = [m for m in all_matches if m["fit_tier"] == "STRONG_MATCH"]
    viable_offer = [m for m in all_matches if m["fit_tier"] == "VIABLE_WITH_JOB_OFFER"]
    explore_prepare = [m for m in all_matches if m["fit_tier"] == "PREPARE_GAPS"]

    return {
        "status": "MATCHED",
        "message": (
            f"Evaluated {len(all_matches)} pathways across 20 countries: "
            f"{len(top_matches)} strong match(es), {len(viable_offer)} viable with a sponsored job offer."
        ),
        "total_pathways": len(all_matches),
        "top_matches": top_matches[:16],
        "viable_with_job_offer": viable_offer[:16],
        "explore_and_prepare": explore_prepare[:16],
        "all_matches": all_matches,
    }
