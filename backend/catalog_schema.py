"""Single-source-of-truth domain enums and integrity validator for JapaAI.ng country & pathway catalogs."""

import re
from typing import Any, Dict, List

ALLOWED_EDUCATION_LEVELS = frozenset({"secondary", "diploma", "bachelors", "masters", "phd"})

ALLOWED_PROFESSION_FIELDS = frozenset(
    {
        "agriculture",
        "arts",
        "business",
        "education",
        "engineering",
        "healthcare",
        "hospitality",
        "manufacturing",
        "research",
        "tech",
        "trades",
    }
)

ALLOWED_LANGUAGES = frozenset({"english", "french", "german", "portuguese", "spanish"})

ALLOWED_REGIONS = frozenset({"North America", "Europe", "South America"})

_DISALLOWED_LOCALIZED_RE = re.compile(r"\b(?:nigeria|nigerian|lagos|abuja)\b", re.I)


def _check_global_text(text: str, location: str, errors: List[str]) -> None:
    match = _DISALLOWED_LOCALIZED_RE.search(text or "")
    if match:
        errors.append(f"{location}: contains nationality/city-specific wording '{match.group(0)}'")


def validate_countries_catalog(catalog: List[Dict[str, Any]]) -> List[str]:
    """Validate structural, domain-enum, URL, and global-neutrality invariants across all country hubs."""
    errors: List[str] = []
    if not isinstance(catalog, list) or not catalog:
        return ["Catalog must be a non-empty list of Destination Hubs."]

    seen_country_ids = set()
    seen_pathway_ids = set()
    seen_stage_ids = set()

    for idx, country in enumerate(catalog):
        cid = str(country.get("id") or f"index-{idx}")
        if cid in seen_country_ids:
            errors.append(f"Duplicate country id '{cid}'")
        seen_country_ids.add(cid)

        region = country.get("region", "")
        if region not in ALLOWED_REGIONS:
            errors.append(f"Country '{cid}' has invalid region '{region}'")

        portal = str(country.get("official_portal") or "")
        if not portal.startswith("https://"):
            errors.append(f"Country '{cid}' official_portal must start with https:// (got '{portal}')")

        _check_global_text(str(country.get("summary") or ""), f"country '{cid}' summary", errors)

        notes = country.get("applicant_notes")
        if not isinstance(notes, list) or not notes:
            errors.append(f"Country '{cid}' missing non-empty applicant_notes")
        else:
            for n_idx, note in enumerate(notes):
                _check_global_text(str(note), f"country '{cid}' applicant_notes[{n_idx}]", errors)

        pathways = country.get("pathways") or []
        if len(pathways) < 3:
            errors.append(f"Country '{cid}' must define at least 3 pathways (got {len(pathways)})")

        for p in pathways:
            pid = str(p.get("id") or "")
            if not pid:
                errors.append(f"Country '{cid}' contains pathway with empty id")
            elif pid in seen_pathway_ids:
                errors.append(f"Duplicate pathway id '{pid}'")
            seen_pathway_ids.add(pid)

            purl = str(p.get("official_url") or "")
            if not purl.startswith("https://"):
                errors.append(f"Pathway '{pid}' official_url must start with https:// (got '{purl}')")

            min_edu = p.get("min_edu", "")
            if min_edu not in ALLOWED_EDUCATION_LEVELS:
                errors.append(f"Pathway '{pid}' has invalid min_edu '{min_edu}'")

            p_fields = set(p.get("fields") or [])
            if not p_fields or not p_fields.issubset(ALLOWED_PROFESSION_FIELDS):
                unknown_f = sorted(p_fields - ALLOWED_PROFESSION_FIELDS)
                errors.append(f"Pathway '{pid}' has invalid fields: {unknown_f or 'empty'}")

            p_langs = set(p.get("languages") or [])
            if not p_langs or not p_langs.issubset(ALLOWED_LANGUAGES):
                unknown_l = sorted(p_langs - ALLOWED_LANGUAGES)
                errors.append(f"Pathway '{pid}' has invalid languages: {unknown_l or 'empty'}")

            _check_global_text(str(p.get("summary") or ""), f"pathway '{pid}' summary", errors)

            stages = p.get("stages") or []
            if len(stages) < 2:
                errors.append(f"Pathway '{pid}' must have at least 2 stages (got {len(stages)})")

            for st in stages:
                sid = str(st.get("id") or "")
                if not sid:
                    errors.append(f"Pathway '{pid}' has stage with empty id")
                elif sid in seen_stage_ids:
                    errors.append(f"Duplicate stage id '{sid}'")
                seen_stage_ids.add(sid)

                surl = str(st.get("url") or "")
                if not surl.startswith("https://"):
                    errors.append(f"Stage '{sid}' url must start with https:// (got '{surl}')")

                _check_global_text(str(st.get("title") or ""), f"stage '{sid}' title", errors)
                _check_global_text(str(st.get("description") or ""), f"stage '{sid}' description", errors)

    return errors
