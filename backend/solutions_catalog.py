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
        "name": "Canada RCIP Employer Matcher AI",
        "tagline": "Match your CV to 34 verified RCIP designated employers across all 14 communities and apply directly.",
        "category": "employer-job",
        "category_label": "EMPLOYER & JOB AI",
        "country_ids": ["canada"],
        "country_label": "Canada · 14 Towns",
        "flag": "🇨🇦",
        "badge": "POPULAR",
        "highlight_badge": "Best Match",
        "emblem_title": "RCIP Jobs",
        "emblem_color": "#e11d48",
        "accent": "crimson",
        "featured": True,
        "icon_key": "briefcase",
        "highlights": ["PDF/DOCX CV Parser", "NOC 2021 Match", "Direct Apply Links"],
        "official_source_label": "Canada.ca RCIP + 14 EDO Lists",
        "scope_footer": "Canada · Free",
        "cta_label": "Launch",
        "launch_action": {
            "type": "rcip_subtab",
            "tab_id": "tab-rcip",
            "subtab_id": "rcip-sub-employers",
        },
    },
    {
        "id": "global-20country-matcher",
        "name": "20-Country Global Pathway Finder",
        "tagline": "Compare PR, Skilled Worker, EU Blue Card, Self-Petition & Digital Nomad fit across 67 official routes.",
        "category": "pathway-matcher",
        "category_label": "PATHWAY MATCHER",
        "country_ids": ["all"],
        "country_label": "Global · 20 Countries",
        "flag": "🌍",
        "badge": "CORE AI",
        "highlight_badge": "67 Routes",
        "emblem_title": "Global Match",
        "emblem_color": "#047857",
        "accent": "emerald",
        "featured": True,
        "icon_key": "compass",
        "highlights": ["67 Official Pathways", "Zero Score Floors", "3 Fit Tiers"],
        "official_source_label": "20 National Immigration Portals",
        "scope_footer": "20 Countries · Free",
        "cta_label": "Launch",
        "launch_action": {
            "type": "tab",
            "tab_id": "tab-matcher",
        },
    },
    {
        "id": "canada-rcip-eligibility-calc",
        "name": "Canada RCIP CLB & Funds Calculator",
        "tagline": "Run IRCC 6-pillar check: 1,560-hr / Local Grad exemption, TEER cross-match, CLB conversion & CAD funds.",
        "category": "eligibility-calc",
        "category_label": "CALCULATORS",
        "country_ids": ["canada"],
        "country_label": "Canada · IRCC Rules",
        "flag": "🇨🇦",
        "badge": "POPULAR",
        "highlight_badge": "2027 Ready",
        "emblem_title": "CLB & TEER",
        "emblem_color": "#dc2626",
        "accent": "crimson",
        "featured": True,
        "icon_key": "calculator",
        "highlights": ["IELTS / CELPIP / PTE", "Jan 1, 2027 Track", "6-Stage Roadmap"],
        "official_source_label": "IRCC Rural Community Program",
        "scope_footer": "Canada · Free",
        "cta_label": "Launch",
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
        "category_label": "AI COPILOT",
        "country_ids": ["all"],
        "country_label": "All 20 Portals",
        "flag": "🛰️",
        "badge": "LIVE RAG",
        "highlight_badge": "Cited Answers",
        "emblem_title": "Gov Copilot",
        "emblem_color": "#2563eb",
        "accent": "blue",
        "featured": True,
        "icon_key": "sparkles",
        "highlights": ["Clickable [LIVE] Links", "20-Country Scope", "Real-Time Sync"],
        "official_source_label": "Live Official Portal Index",
        "scope_footer": "All Portals · Free",
        "cta_label": "Launch",
        "launch_action": {
            "type": "tab",
            "tab_id": "tab-copilot",
        },
    },
    {
        "id": "usa-niw-o1a-explorer",
        "name": "USA Self-Petition App (EB-2 NIW)",
        "tagline": "Step-by-step official roadmap for National Interest Waiver self-petitions, O-1A & Diversity Visa.",
        "category": "popular-pathway",
        "category_label": "POPULAR PATHWAY",
        "country_ids": ["usa"],
        "country_label": "United States",
        "flag": "🇺🇸",
        "badge": "",
        "highlight_badge": "No Sponsor",
        "emblem_title": "US NIW / O-1",
        "emblem_color": "#1d4ed8",
        "accent": "blue",
        "featured": False,
        "icon_key": "shield",
        "highlights": ["EB-2 NIW Self-Petition", "Dhanasar 3-Prong", "USCIS Live Feed"],
        "official_source_label": "USCIS & U.S. State Dept",
        "scope_footer": "USA · Free",
        "cta_label": "Launch",
        "launch_action": {
            "type": "country_hub",
            "country_id": "usa",
            "pathway_id": "us-eb2-niw",
        },
    },
    {
        "id": "germany-blue-card-chancenkarte",
        "name": "Germany EU Blue Card & Chancenkarte",
        "tagline": "2026 EU Blue Card salary thresholds, shortage STEM tracks, Opportunity Card & Make-it-in-Germany steps.",
        "category": "popular-pathway",
        "category_label": "POPULAR PATHWAY",
        "country_ids": ["germany"],
        "country_label": "Germany",
        "flag": "🇩🇪",
        "badge": "",
        "highlight_badge": "Fast PR",
        "emblem_title": "DE Blue Card",
        "emblem_color": "#047857",
        "accent": "emerald",
        "featured": False,
        "icon_key": "badge",
        "highlights": ["21–27 Mo PR Path", "Anabin Degree Check", "2026 Thresholds"],
        "official_source_label": "Make-it-in-Germany.com",
        "scope_footer": "Germany · Free",
        "cta_label": "Launch",
        "launch_action": {
            "type": "country_hub",
            "country_id": "germany",
            "pathway_id": "de-blue-card",
        },
    },
    {
        "id": "uk-health-skilled-planner",
        "name": "UK Skilled Worker & Health Care App",
        "tagline": "Official GOV.UK routes for NHS/care sponsorship, SOC codes, reduced fees & 5-year ILR settlement.",
        "category": "popular-pathway",
        "category_label": "POPULAR PATHWAY",
        "country_ids": ["uk"],
        "country_label": "United Kingdom",
        "flag": "🇬🇧",
        "badge": "",
        "highlight_badge": "GOV.UK",
        "emblem_title": "UK Visas",
        "emblem_color": "#4338ca",
        "accent": "blue",
        "featured": False,
        "icon_key": "heart",
        "highlights": ["Health & Care Fee", "CoS Checklist", "Global Talent"],
        "official_source_label": "GOV.UK Visas & Immigration",
        "scope_footer": "UK · Free",
        "cta_label": "Launch",
        "launch_action": {
            "type": "country_hub",
            "country_id": "uk",
            "pathway_id": "uk-health-care",
        },
    },
    {
        "id": "netherlands-kennismigrant-hub",
        "name": "Netherlands Skilled Migrant (IND)",
        "tagline": "IND 2026 recognized-sponsor salary criteria, 5-year residency path & live IND regulatory notices.",
        "category": "popular-pathway",
        "category_label": "POPULAR PATHWAY",
        "country_ids": ["netherlands"],
        "country_label": "Netherlands",
        "flag": "🇳🇱",
        "badge": "",
        "highlight_badge": "IND 2026",
        "emblem_title": "IND.nl Hub",
        "emblem_color": "#ea580c",
        "accent": "amber",
        "featured": False,
        "icon_key": "building",
        "highlights": ["Recognized Sponsors", "Orientation Year", "2026 Salaries"],
        "official_source_label": "IND.nl (Netherlands)",
        "scope_footer": "Netherlands · Free",
        "cta_label": "Launch",
        "launch_action": {
            "type": "country_hub",
            "country_id": "netherlands",
            "pathway_id": "nl-kennismigrant",
        },
    },
    {
        "id": "nomad-pr-spain-brazil",
        "name": "Digital Nomad PR (Spain & Brazil)",
        "tagline": "Official remote-work residency steps for Spain Digital Nomad Visa & Brazil VITEM XIV pathways.",
        "category": "popular-pathway",
        "category_label": "REMOTE & NOMAD",
        "country_ids": ["spain", "brazil"],
        "country_label": "Spain & Brazil",
        "flag": "🇪🇸",
        "badge": "",
        "highlight_badge": "Remote Pay",
        "emblem_title": "Nomad PR",
        "emblem_color": "#d97706",
        "accent": "amber",
        "featured": False,
        "icon_key": "laptop",
        "highlights": ["Income Thresholds", "Residency Steps", "Exportable PDF"],
        "official_source_label": "Inclusion.gob.es & Gov.br",
        "scope_footer": "ES & BR · Free",
        "cta_label": "Launch",
        "launch_action": {
            "type": "country_hub",
            "country_id": "spain",
            "pathway_id": "es-digital-nomad",
        },
    },
    {
        "id": "nordic-baltic-europe-hubs",
        "name": "Nordic, Baltic & EU Destination Hubs",
        "tagline": "Explore Sweden, Estonia, Lithuania, Bulgaria & France official portals with real-time live verification.",
        "category": "gov-copilot",
        "category_label": "COUNTRY HUBS",
        "country_ids": ["sweden", "estonia", "lithuania", "bulgaria", "france"],
        "country_label": "5 EU Countries",
        "flag": "🇪🇺",
        "badge": "",
        "highlight_badge": "Live Sync",
        "emblem_title": "EU Hubs",
        "emblem_color": "#0f766e",
        "accent": "emerald",
        "featured": False,
        "icon_key": "globe",
        "highlights": ["Live Portal Feeds", "Checklists + Notes", "Official Links"],
        "official_source_label": "Migrationsverket, PPA & MIGRIS",
        "scope_footer": "5 Countries · Free",
        "cta_label": "Launch",
        "launch_action": {
            "type": "countries_region",
            "tab_id": "tab-countries",
            "region": "Europe",
        },
    },
    {
        "id": "australia-skilled-pr-planner",
        "name": "Australia Skilled 189 / 190 & 482 PR App",
        "tagline": "SkillSelect points pathways (189/190), Subclass 482 → 186 Employer PR & Regional 491 → 191 tracks.",
        "category": "popular-pathway",
        "category_label": "POINTS PR",
        "country_ids": ["australia"],
        "country_label": "Australia",
        "flag": "🇦🇺",
        "badge": "POPULAR",
        "highlight_badge": "Direct PR",
        "emblem_title": "AU 189 / 190",
        "emblem_color": "#0284c7",
        "accent": "blue",
        "featured": True,
        "icon_key": "badge",
        "highlights": ["65+ EOI Points", "Subclass 482 → 186", "Home Affairs Live"],
        "official_source_label": "Immi.HomeAffairs.gov.au",
        "scope_footer": "Australia · Free",
        "cta_label": "Launch",
        "launch_action": {
            "type": "country_hub",
            "country_id": "australia",
            "pathway_id": "au-skilled-189-190",
        },
    },
    {
        "id": "portugal-italy-nomad-residency",
        "name": "Portugal D8 / D3 & Italy Nomad Residence",
        "tagline": "Official Southern EU routes: Portugal D8 & Job Seeker visas via AIMA plus Italy Blue Card & Digital Nomad.",
        "category": "popular-pathway",
        "category_label": "SOUTHERN EU",
        "country_ids": ["portugal", "italy"],
        "country_label": "Portugal & Italy",
        "flag": "🇵🇹",
        "badge": "NEW",
        "highlight_badge": "5-Yr PR",
        "emblem_title": "PT & IT Hub",
        "emblem_color": "#16a34a",
        "accent": "emerald",
        "featured": True,
        "icon_key": "laptop",
        "highlights": ["AIMA & VistosOnline", "Carta Blu UE", "Nomad Income Check"],
        "official_source_label": "Vistos.mne.gov.pt & Esteri.it",
        "scope_footer": "PT & IT · Free",
        "cta_label": "Launch",
        "launch_action": {
            "type": "country_hub",
            "country_id": "portugal",
            "pathway_id": "pt-d8-nomad",
        },
    },
    {
        "id": "austria-rwr-card-planner",
        "name": "Austria Red-White-Red & Job Seeker AI",
        "tagline": "70/100 Very Highly Qualified Job Seeker Visa, Shortage List (55/90 pts), & 24-month RWR → Plus PR.",
        "category": "eligibility-calc",
        "category_label": "POINTS PERMIT",
        "country_ids": ["austria"],
        "country_label": "Austria",
        "flag": "🇦🇹",
        "badge": "",
        "highlight_badge": "70+ Pts",
        "emblem_title": "RWR Card",
        "emblem_color": "#dc2626",
        "accent": "crimson",
        "featured": False,
        "icon_key": "compass",
        "highlights": ["6-Mo Job Seeker", "Shortage Occupations", "Migration.gv.at"],
        "official_source_label": "Migration.gv.at (Austria)",
        "scope_footer": "Austria · Free",
        "cta_label": "Launch",
        "launch_action": {
            "type": "country_hub",
            "country_id": "austria",
            "pathway_id": "at-rwr-qualified",
        },
    },
    {
        "id": "central-eu-caribbean-hubs",
        "name": "Hungary, Slovakia, Slovenia & Cuba Hubs",
        "tagline": "Official portals for Enter Hungary, Slovakia EU Blue Card, Slovenia Single Permits & Cuba MINREX D-2.",
        "category": "gov-copilot",
        "category_label": "NEW HUBS",
        "country_ids": ["hungary", "slovakia", "slovenia", "cuba"],
        "country_label": "4 New Hubs",
        "flag": "🇭🇺",
        "badge": "NEW",
        "highlight_badge": "4 Countries",
        "emblem_title": "HU SK SI CU",
        "emblem_color": "#7c3aed",
        "accent": "blue",
        "featured": True,
        "icon_key": "globe",
        "highlights": ["Enter Hungary & OIF", "IOM MIC & GOV.SI", "MINREX Consular"],
        "official_source_label": "OIF, MZV.sk, GOV.SI & MINREX",
        "scope_footer": "4 Countries · Free",
        "cta_label": "Launch",
        "launch_action": {
            "type": "country_hub",
            "country_id": "hungary",
            "pathway_id": "hu-hungarian-card",
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

        if not sol.get("emblem_title") or not sol.get("icon_key"):
            errors.append(f"{sid}: missing emblem_title or icon_key for card UI")

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
