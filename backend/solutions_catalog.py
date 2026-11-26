"""Curated AI Solutions Store Catalog for ai4japa.store."""

import re
from typing import Any, Dict, List, Optional

from backend.countries_data import COUNTRIES_CATALOG

SOLUTION_CATEGORIES: List[Dict[str, str]] = [
    {"id": "all", "label": "All AI Solutions"},
    {"id": "employer-job", "label": "Employer & Job AI"},
    {"id": "pathway-matcher", "label": "Pathway Matchers"},
    {"id": "eligibility-calc", "label": "Eligibility & Calculators"},
    {"id": "popular-pathway", "label": "Popular Pathway Apps"},
    {"id": "gov-copilot", "label": "Gov RAG & Hubs"},
]

_VALID_CATEGORY_IDS = {c["id"] for c in SOLUTION_CATEGORIES if c["id"] != "all"}
_COUNTRIES_BY_ID = {c["id"]: c for c in COUNTRIES_CATALOG}
_FORBIDDEN_LOCALIZED = ("Nigeria", "Nigerian", "Lagos", "Abuja")


AI_SOLUTIONS_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "canada-rcip-employer-ai",
        "name": "Canada RCIP Designated Employer & CV AI",
        "tagline": "Match your CV to 34 verified RCIP employers across all 14 communities and apply directly.",
        "category": "employer-job",
        "country_ids": ["canada"],
        "country_label": "Canada (14 Communities)",
        "flag": "🇨🇦",
        "badge": "Flagship Solution",
        "accent": "crimson",
        "featured": True,
        "icon_key": "briefcase",
        "cover_image": "/static/images/dest-canada.webp?v=7",
        "highlights": ["PDF/DOCX CV Parser", "NOC 2021 Skill Match", "Direct Apply + Job Bank"],
        "official_source_label": "Canada.ca RCIP + 14 EDO Directories",
        "cta_label": "Launch Employer Matcher",
        "launch_action": {
            "type": "rcip_subtab",
            "tab_id": "tab-rcip",
            "subtab_id": "rcip-sub-employers",
        },
    },
    {
        "id": "global-12country-matcher",
        "name": "12-Country Global Pathway Finder AI",
        "tagline": "Compare PR, Skilled Worker, EU Blue Card, Self-Petition & Digital Nomad fit across 43 official routes.",
        "category": "pathway-matcher",
        "country_ids": ["all"],
        "country_label": "Global (12 Countries)",
        "flag": "🌍",
        "badge": "Core AI",
        "accent": "emerald",
        "featured": True,
        "icon_key": "compass",
        "cover_image": "/static/images/hero-global-mobility.webp?v=7",
        "highlights": ["43 Official Pathways", "Zero Fake Score Floors", "3 Realistic Fit Tiers"],
        "official_source_label": "12 National Immigration Ministries",
        "cta_label": "Launch Pathway Matcher",
        "launch_action": {
            "type": "tab",
            "tab_id": "tab-matcher",
        },
    },
    {
        "id": "canada-rcip-eligibility-calc",
        "name": "Canada RCIP Eligibility, CLB & Funds Toolkit",
        "tagline": "Run IRCC 6-pillar verification: 1,560-hr / Local Grad rule, TEER cross-match, CLB conversion & CAD funds.",
        "category": "eligibility-calc",
        "country_ids": ["canada"],
        "country_label": "Canada (Pilot & 2027)",
        "flag": "🇨🇦",
        "badge": "Popular Pathway",
        "accent": "crimson",
        "featured": True,
        "icon_key": "calculator",
        "cover_image": "/static/images/dest-canada.webp?v=7",
        "highlights": ["IELTS / CELPIP / PTE / TEF", "Jan 1, 2027 Track Split", "6-Stage Checklist"],
        "official_source_label": "IRCC Rural Community Immigration",
        "cta_label": "Launch RCIP Toolkit",
        "launch_action": {
            "type": "rcip_subtab",
            "tab_id": "tab-rcip",
            "subtab_id": "rcip-sub-wizard",
        },
    },
    {
        "id": "official-gov-rag-copilot",
        "name": "Real-Time Official Gov RAG Copilot",
        "tagline": "Ask questions on thresholds, forms & draws — grounded strictly in live scraped government portals.",
        "category": "gov-copilot",
        "country_ids": ["all"],
        "country_label": "All 12 Portals",
        "flag": "🛰️",
        "badge": "Live Citations",
        "accent": "blue",
        "featured": True,
        "icon_key": "sparkles",
        "cover_image": "/static/images/hero-global-mobility.webp?v=7",
        "highlights": ["Clickable [LIVE] Citations", "Multi-Country Scope", "Real-Time Portal Sync"],
        "official_source_label": "Live SQLite Official Portal Index",
        "cta_label": "Open Gov Copilot",
        "launch_action": {
            "type": "tab",
            "tab_id": "tab-copilot",
        },
    },
    {
        "id": "usa-niw-o1a-explorer",
        "name": "USA Self-Petition Green Card App (EB-2 NIW)",
        "tagline": "Step-by-step official roadmap for National Interest Waiver self-petitions, O-1A & Diversity Visa.",
        "category": "popular-pathway",
        "country_ids": ["usa"],
        "country_label": "United States",
        "flag": "🇺🇸",
        "badge": "Popular Pathway",
        "accent": "blue",
        "featured": False,
        "icon_key": "shield",
        "cover_image": "/static/images/dest-usa.webp?v=7",
        "highlights": ["No Job Offer Needed (NIW)", "Dhanasar 3-Prong Guide", "USCIS Live Snapshots"],
        "official_source_label": "USCIS & U.S. State Dept",
        "cta_label": "Launch USA NIW App",
        "launch_action": {
            "type": "country_hub",
            "country_id": "usa",
            "pathway_id": "us-eb2-niw",
        },
    },
    {
        "id": "germany-blue-card-chancenkarte",
        "name": "Germany EU Blue Card & Opportunity Card App",
        "tagline": "2026 EU Blue Card salary thresholds, shortage STEM tracks, Chancenkarte points & Make-it-in-Germany steps.",
        "category": "popular-pathway",
        "country_ids": ["germany"],
        "country_label": "Germany",
        "flag": "🇩🇪",
        "badge": "EU Fast-Track PR",
        "accent": "emerald",
        "featured": False,
        "icon_key": "badge",
        "cover_image": "/static/images/dest-central-europe.webp?v=7",
        "highlights": ["21–27 Mo PR Fast-Track", "Anabin Degree Check", "Live 2026 Thresholds"],
        "official_source_label": "Make-it-in-Germany.com",
        "cta_label": "Launch Germany App",
        "launch_action": {
            "type": "country_hub",
            "country_id": "germany",
            "pathway_id": "de-blue-card",
        },
    },
    {
        "id": "uk-health-skilled-planner",
        "name": "UK Skilled Worker & Health Care AI Planner",
        "tagline": "Official GOV.UK routes for NHS/care sponsorship, SOC codes, reduced fees & 5-year ILR settlement.",
        "category": "popular-pathway",
        "country_ids": ["uk"],
        "country_label": "United Kingdom",
        "flag": "🇬🇧",
        "badge": "GOV.UK Direct",
        "accent": "blue",
        "featured": False,
        "icon_key": "heart",
        "cover_image": "/static/images/dest-uk.webp?v=7",
        "highlights": ["Health & Care Reduced Fee", "CoS Sponsor Checklist", "Global Talent Route"],
        "official_source_label": "GOV.UK Visas & Immigration",
        "cta_label": "Launch UK Planner",
        "launch_action": {
            "type": "country_hub",
            "country_id": "uk",
            "pathway_id": "uk-health-care",
        },
    },
    {
        "id": "netherlands-kennismigrant-hub",
        "name": "Netherlands Highly Skilled Migrant (IND) App",
        "tagline": "IND 2026 recognized-sponsor salary criteria, 5-year residency path & live IND regulatory notices.",
        "category": "popular-pathway",
        "country_ids": ["netherlands"],
        "country_label": "Netherlands",
        "flag": "🇳🇱",
        "badge": "EU Sponsor Route",
        "accent": "emerald",
        "featured": False,
        "icon_key": "building",
        "cover_image": "/static/images/dest-central-europe.webp?v=7",
        "highlights": ["IND Recognized Sponsors", "Orientation Year (Zoekjaar)", "2026 Live Thresholds"],
        "official_source_label": "IND.nl (Netherlands)",
        "cta_label": "Launch Netherlands App",
        "launch_action": {
            "type": "country_hub",
            "country_id": "netherlands",
            "pathway_id": "nl-kennismigrant",
        },
    },
    {
        "id": "nomad-pr-spain-brazil",
        "name": "Remote Earner & Digital Nomad PR Tracker",
        "tagline": "Official remote-work residency steps for Spain Digital Nomad Visa & Brazil VITEM XIV pathways.",
        "category": "popular-pathway",
        "country_ids": ["spain", "brazil"],
        "country_label": "Spain & Brazil",
        "flag": "🇪🇸",
        "badge": "Remote Income",
        "accent": "amber",
        "featured": False,
        "icon_key": "laptop",
        "cover_image": "/static/images/dest-southern-europe.webp?v=7",
        "highlights": ["Income Threshold Guides", "Direct Residency Steps", "Exportable PDF Dossier"],
        "official_source_label": "Inclusion.gob.es & Gov.br",
        "cta_label": "Launch Nomad Tracker",
        "launch_action": {
            "type": "country_hub",
            "country_id": "spain",
            "pathway_id": "es-digital-nomad",
        },
    },
    {
        "id": "nordic-baltic-europe-hubs",
        "name": "Nordic, Baltic & EU Destination Hubs Suite",
        "tagline": "Explore Sweden, Estonia, Lithuania, Bulgaria & France official portals with real-time live verification.",
        "category": "gov-copilot",
        "country_ids": ["sweden", "estonia", "lithuania", "bulgaria", "france"],
        "country_label": "5 EU Destinations",
        "flag": "🇪🇺",
        "badge": "EU Growth Hubs",
        "accent": "emerald",
        "featured": False,
        "icon_key": "globe",
        "cover_image": "/static/images/dest-nordic-baltic.webp?v=7",
        "highlights": ["Live Portal Snapshots", "Step Checklists + Notes", "Printable Roadmaps"],
        "official_source_label": "Migrationsverket, PPA, MIGRIS & MVR",
        "cta_label": "Open European Hubs",
        "launch_action": {
            "type": "countries_region",
            "tab_id": "tab-countries",
            "region": "Europe",
        },
    },
]


def validate_solutions_catalog(catalog: Optional[List[Dict[str, Any]]] = None) -> List[str]:
    """Validate structural, country, launch action, and branding invariants for AI_SOLUTIONS_CATALOG."""
    items = AI_SOLUTIONS_CATALOG if catalog is None else catalog
    errors: List[str] = []
    seen_ids = set()

    for idx, sol in enumerate(items):
        sid = str(sol.get("id") or f"idx:{idx}")
        if not sol.get("id") or not re.fullmatch(r"[a-z0-9-]+", sid):
            errors.append(f"Invalid solution id: {sid!r}")
        if sid in seen_ids:
            errors.append(f"Duplicate solution id: {sid!r}")
        seen_ids.add(sid)

        cat = str(sol.get("category") or "")
        if cat not in _VALID_CATEGORY_IDS:
            errors.append(f"{sid}: invalid category {cat!r}")

        cids = sol.get("country_ids") or []
        if not cids:
            errors.append(f"{sid}: country_ids cannot be empty")
        for cid in cids:
            if cid != "all" and cid not in _COUNTRIES_BY_ID:
                errors.append(f"{sid}: unknown country_id {cid!r}")

        action = sol.get("launch_action") or {}
        atype = action.get("type")
        if atype not in {"tab", "rcip_subtab", "country_hub", "copilot", "countries_region"}:
            errors.append(f"{sid}: unsupported launch_action.type {atype!r}")
        if atype == "country_hub":
            target_cid = action.get("country_id")
            if target_cid not in _COUNTRIES_BY_ID:
                errors.append(f"{sid}: unknown country_hub target {target_cid!r}")
            else:
                target_pid = action.get("pathway_id")
                valid_pids = {p["id"] for p in _COUNTRIES_BY_ID[target_cid]["pathways"]}
                if target_pid and target_pid not in valid_pids:
                    errors.append(f"{sid}: unknown pathway_id {target_pid!r} for {target_cid}")

        cover = str(sol.get("cover_image") or "")
        if not cover.startswith("/static/images/") or ".webp" not in cover:
            errors.append(f"{sid}: invalid cover_image path {cover!r}")

        blob = " ".join([
            str(sol.get("name") or ""),
            str(sol.get("tagline") or ""),
            str(sol.get("country_label") or ""),
            *sol.get("highlights", []),
        ])
        for tok in _FORBIDDEN_LOCALIZED:
            if tok in blob:
                errors.append(f"{sid}: forbidden localized term {tok!r}")

    return errors


def list_solutions(
    category: Optional[str] = None,
    country_id: Optional[str] = None,
    q: Optional[str] = None,
) -> Dict[str, Any]:
    """Return filtered AI solutions and category metadata for the ai4japa.store catalog."""
    cat_f = (category or "").strip().lower()
    cid_f = (country_id or "").strip().lower()
    q_f = (q or "").strip().lower()

    results = []
    for sol in AI_SOLUTIONS_CATALOG:
        if cat_f and cat_f != "all" and sol["category"].lower() != cat_f:
            continue
        if cid_f and cid_f != "all":
            cids = [c.lower() for c in sol["country_ids"]]
            if cid_f not in cids and "all" not in cids:
                continue
        if q_f:
            hay = " ".join([
                sol["name"],
                sol["tagline"],
                sol["country_label"],
                sol["category"],
                sol["official_source_label"],
                *sol.get("highlights", []),
            ]).lower()
            if q_f not in hay:
                continue
        results.append(sol)

    return {
        "total": len(results),
        "categories": SOLUTION_CATEGORIES,
        "solutions": results,
    }
