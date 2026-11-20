"""FastAPI gateway for RCIP Canada AI."""

import html as html_lib
import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.canada_crawler import SEED_CANADA_PAGES, crawl_official_canada_pages
from backend.config import BASE_DIR, DB_PATH, IS_VERCEL
from backend.countries_data import COUNTRIES_CATALOG
from backend.eligibility_engine import (
    build_tailored_roadmap,
    compute_clb_from_test,
    evaluate_rcip_eligibility,
    required_settlement_funds,
)
from backend.matcher_engine import match_global_pathways
from backend.rag_service import CanadaRAGService
from backend.rcip_data import (
    COMMON_NOC_CATALOG,
    ECA_ORGANIZATIONS,
    ESDC_NOC_FINDER_URL,
    LANGUAGE_TEST_CHARTS,
    OFFICIAL_IMM_FORMS,
    PARTICIPATING_COMMUNITIES,
    SETTLEMENT_FUNDS_TABLE,
)
from backend.resume_parser import parse_resume_file, parse_resume_text
from backend.store import (
    get_profile as store_get_profile,
    list_canada_pages as store_list_canada_pages,
    list_progress as store_list_progress,
    list_shortlists as store_list_shortlists,
    save_profile as store_save_profile,
    store_session,
    upsert_canada_page as store_upsert_canada_page,
    upsert_progress as store_upsert_progress,
    upsert_shortlist as store_upsert_shortlist,
)

app = FastAPI(
    title="JapaAI.ng — Official Global Immigration & PR Roadmap Platform",
    description="Multi-country official immigration roadmaps across 12 countries, cross-country matcher, deep Canada RCIP engine, and official government RAG copilot.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_engine = CanadaRAGService()


def _resolve_db_path() -> str:
    return getattr(app.state, "db_path", None) or os.environ.get("RCIP_DB_PATH") or DB_PATH


def ensure_seeded_and_indexed(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Seed offline Canada.ca baseline pages if DB is empty and load RAG index."""
    target_db = db_path or _resolve_db_path()
    with store_session(target_db) as conn:
        pages = store_list_canada_pages(conn)
        if not pages:
            for seed_page in SEED_CANADA_PAGES:
                store_upsert_canada_page(conn, seed_page)
            pages = store_list_canada_pages(conn)
    rag_engine.index_pages(pages)
    return pages


@app.on_event("startup")
def on_startup() -> None:
    ensure_seeded_and_indexed()


# --------------------------------------------------------------------------
# Pydantic models
# --------------------------------------------------------------------------

class ProfilePayload(BaseModel):
    name: Optional[str] = ""
    email: Optional[str] = ""
    currently_in_canada: bool = False
    in_canada_valid_work_permit: bool = False
    has_spouse: bool = False
    family_size: Optional[int] = None
    available_funds_cad: Optional[float] = None

    target_community_id: Optional[str] = ""
    target_job_noc_code: Optional[str] = ""
    target_job_teer: Optional[int] = None
    target_job_title: Optional[str] = ""

    # Work experience / local graduate exemption
    is_local_graduate: bool = False
    grad_program_type: Optional[str] = ""  # "2yr_plus" | "masters_phd"
    grad_public_institution_in_community: bool = False
    grad_full_time: bool = False
    months_since_graduation: Optional[float] = None
    grad_lived_in_community_months: Optional[float] = None
    grad_lived_entire_duration: bool = False
    grad_over_half_language_study: bool = False
    grad_over_half_distance_learning: bool = False
    grad_return_home_scholarship: bool = False

    paid_work_hours_last_3_years: Optional[float] = None
    experience_teer: Optional[int] = None
    experience_noc_code: Optional[str] = ""
    work_was_self_employed_or_unpaid: bool = False

    # Language
    language_test_type: Optional[str] = ""
    language_test_age_months: Optional[float] = None
    lang_reading: Optional[float] = None
    lang_writing: Optional[float] = None
    lang_listening: Optional[float] = None
    lang_speaking: Optional[float] = None
    clb_overall: Optional[int] = None

    # Education
    education_origin: Optional[str] = ""  # "canada" | "foreign"
    education_level: Optional[str] = ""
    has_eca: bool = False
    eca_organization: Optional[str] = ""
    eca_age_years: Optional[float] = None

    # Job Offer
    has_job_offer: bool = False
    offer_from_designated_employer: bool = False
    offer_full_time_30h: bool = False
    offer_non_seasonal: bool = False
    offer_indeterminate: bool = False
    offer_inside_community: bool = False

    # Community Recommendation
    has_community_recommendation: bool = False
    recommendation_date: Optional[str] = ""

    # Skills / Resume summary
    detected_skills: List[str] = Field(default_factory=list)
    experience_summary: Optional[str] = ""


class RoadmapProgressPayload(BaseModel):
    item_id: str
    stage_id: str
    completed: bool
    notes: str = ""
    target_date: str = ""


class CLBConvertPayload(BaseModel):
    test_type: str
    reading: float
    writing: float
    listening: float
    speaking: float


class CommunityShortlistPayload(BaseModel):
    community_id: str
    shortlisted: bool
    notes: str = ""
    employers_contacted: int = 0


class ChatPayload(BaseModel):
    query: str
    profile: Optional[Dict[str, Any]] = None
    country_id: Optional[str] = None


class GlobalRoadmapExportPayload(BaseModel):
    country_id: str
    pathway_id: str
    applicant_name: str = "Applicant"
    checked_steps: Dict[str, bool] = Field(default_factory=dict)
    notes: Dict[str, str] = Field(default_factory=dict)


class RoadmapComputePayload(BaseModel):
    profile: Dict[str, Any] = Field(default_factory=dict)
    progress: Dict[str, Any] = Field(default_factory=dict)


class ExportHtmlPayload(BaseModel):
    profile: Dict[str, Any] = Field(default_factory=dict)
    progress: Dict[str, Any] = Field(default_factory=dict)
    shortlists: Dict[str, Any] = Field(default_factory=dict)


MAX_UPLOAD_BYTES = int(4.2 * 1024 * 1024)


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

@app.get("/api/health")
def health_check() -> Dict[str, Any]:
    pages = rag_engine.pages or ensure_seeded_and_indexed()
    return {
        "status": "healthy",
        "service": "JapaAI.ng",
        "countries_count": len(COUNTRIES_CATALOG),
        "indexed_pages": len(pages),
        "environment": "vercel" if IS_VERCEL else "local",
        "storage_mode": "browser_local_plus_tmp" if IS_VERCEL else "sqlite_local",
    }


@app.get("/api/stats")
def get_stats() -> Dict[str, Any]:
    db_path = _resolve_db_path()
    with store_session(db_path) as conn:
        profile = store_get_profile(conn)
        progress_map = store_list_progress(conn)
        shortlists = store_list_shortlists(conn)
        pages = store_list_canada_pages(conn)

    if not pages:
        pages = ensure_seeded_and_indexed(db_path)

    evaluation = evaluate_rcip_eligibility(profile)
    roadmap = build_tailored_roadmap(profile, progress_map, evaluation)
    shortlisted_count = sum(1 for item in shortlists.values() if item.get("shortlisted"))
    last_synced = max((p.get("fetched_at", "") for p in pages), default="")

    return {
        "status": "success",
        "readiness_score": evaluation["readiness_score"],
        "overall_status": evaluation["overall_status"],
        "verdict": evaluation["verdict"],
        "program_track": evaluation["program_track"],
        "applicant_context": evaluation["applicant_context"],
        "completed_tasks": roadmap["completed_items"],
        "total_tasks": roadmap["total_items"],
        "completion_percent": roadmap["completion_percent"],
        "shortlisted_communities": shortlisted_count,
        "synced_pages": len(pages),
        "last_synced_at": last_synced,
    }


@app.get("/api/profile")
def get_profile_endpoint() -> Dict[str, Any]:
    with store_session(_resolve_db_path()) as conn:
        profile = store_get_profile(conn)
    return {"status": "success", "profile": profile}


@app.post("/api/profile")
def save_profile_endpoint(payload: ProfilePayload) -> Dict[str, Any]:
    with store_session(_resolve_db_path()) as conn:
        saved = store_save_profile(conn, payload.model_dump())
    evaluation = evaluate_rcip_eligibility(saved)
    return {"status": "success", "profile": saved, "evaluation": evaluation}


@app.post("/api/resume/upload")
async def upload_resume_endpoint(request: Request) -> Dict[str, Any]:
    """Parse an uploaded PDF/DOCX/TXT file or pasted resume text for NOC/TEER suggestions."""
    content_type = (request.headers.get("content-type") or "").lower()
    parsed: Dict[str, Any]

    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("file")
        pasted = form.get("resume_text")
        if upload is not None and hasattr(upload, "read"):
            raw_bytes = await upload.read()
            if len(raw_bytes) > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="Resume file exceeds 4.2 MB limit.")
            parsed = parse_resume_file(getattr(upload, "filename", "resume.txt"), raw_bytes)
        elif pasted:
            if len(str(pasted).encode("utf-8")) > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="Resume text exceeds 4.2 MB limit.")
            parsed = parse_resume_text(str(pasted))
        else:
            raise HTTPException(status_code=400, detail="Provide a resume file or resume_text.")
    else:
        raw_body = await request.body()
        if len(raw_body) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Resume payload exceeds 4.2 MB limit.")
        try:
            body = await request.json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid request body.") from exc
        resume_text = str((body or {}).get("resume_text") or "")
        if not resume_text.strip():
            raise HTTPException(status_code=400, detail="resume_text cannot be empty.")
        parsed = parse_resume_text(resume_text)

    # Safely update only non-authoritative hints if current profile lacks them
    with store_session(_resolve_db_path()) as conn:
        current = store_get_profile(conn)
        updated = dict(current)
        if parsed.get("name") and not updated.get("name"):
            updated["name"] = parsed["name"]
        if parsed.get("email") and not updated.get("email"):
            updated["email"] = parsed["email"]
        if parsed.get("detected_skills"):
            updated["detected_skills"] = parsed["detected_skills"]
        if parsed.get("experience_summary"):
            updated["experience_summary"] = parsed["experience_summary"]
        if parsed.get("education_level") and not updated.get("education_level"):
            updated["education_level"] = parsed["education_level"]
        if parsed.get("suggested_nocs") and not updated.get("target_job_noc_code"):
            top_noc = parsed["suggested_nocs"][0]
            updated["target_job_noc_code"] = top_noc["noc"]
            updated["target_job_teer"] = top_noc["teer"]
            updated["target_job_title"] = top_noc["title"]
        saved_profile = store_save_profile(conn, updated)

    return {
        "status": "success",
        "parsed": parsed,
        "profile": saved_profile,
    }


@app.post("/api/evaluate")
def evaluate_endpoint(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    db_path = _resolve_db_path()
    if payload:
        profile = payload
    else:
        with store_session(db_path) as conn:
            profile = store_get_profile(conn)
    evaluation = evaluate_rcip_eligibility(profile)
    return {"status": "success", "evaluation": evaluation}


@app.get("/api/roadmap")
def get_roadmap_endpoint() -> Dict[str, Any]:
    db_path = _resolve_db_path()
    with store_session(db_path) as conn:
        profile = store_get_profile(conn)
        progress_map = store_list_progress(conn)

    evaluation = evaluate_rcip_eligibility(profile)
    roadmap = build_tailored_roadmap(profile, progress_map, evaluation)
    return {
        "status": "success",
        "roadmap": roadmap,
        "evaluation": evaluation,
        "official_forms": OFFICIAL_IMM_FORMS,
    }


@app.post("/api/roadmap/compute")
def compute_roadmap_endpoint(payload: RoadmapComputePayload) -> Dict[str, Any]:
    """Stateless roadmap & eligibility computation for multi-visitor browser-persisted sessions."""
    evaluation = evaluate_rcip_eligibility(payload.profile)
    roadmap = build_tailored_roadmap(payload.profile, payload.progress, evaluation)
    return {
        "status": "success",
        "roadmap": roadmap,
        "evaluation": evaluation,
        "official_forms": OFFICIAL_IMM_FORMS,
    }


@app.post("/api/roadmap/progress")
def update_roadmap_progress_endpoint(payload: RoadmapProgressPayload) -> Dict[str, Any]:
    with store_session(_resolve_db_path()) as conn:
        record = store_upsert_progress(
            conn,
            item_id=payload.item_id,
            stage_id=payload.stage_id,
            completed=payload.completed,
            notes=payload.notes,
            target_date=payload.target_date,
        )
    return {"status": "success", "progress": record}


@app.post("/api/tools/clb-convert")
def clb_convert_endpoint(payload: CLBConvertPayload) -> Dict[str, Any]:
    result = compute_clb_from_test(
        payload.test_type,
        payload.reading,
        payload.writing,
        payload.listening,
        payload.speaking,
    )
    if not result.get("valid_test"):
        raise HTTPException(status_code=400, detail=result.get("error", "Unsupported test type"))
    return {"status": "success", "conversion": result}


@app.get("/api/tools/funds")
def settlement_funds_endpoint(
    family_size: int = Query(1, ge=1, le=20),
    in_canada_valid_work_permit: bool = Query(False),
) -> Dict[str, Any]:
    required = 0 if in_canada_valid_work_permit else required_settlement_funds(family_size)
    return {
        "status": "success",
        "family_size": family_size,
        "in_canada_valid_work_permit": in_canada_valid_work_permit,
        "required_cad": required,
        "table": SETTLEMENT_FUNDS_TABLE,
        "note": (
            "Exempt because you are working in Canada on a valid work permit."
            if in_canada_valid_work_permit
            else "Includes yourself, your spouse/partner, and all dependent children (even if citizens/PRs or non-accompanying)."
        ),
    }


@app.get("/api/tools/noc-search")
def noc_search_endpoint(
    q: Optional[str] = Query(None),
    teer: Optional[int] = Query(None, ge=0, le=5),
) -> Dict[str, Any]:
    query = (q or "").strip().lower()
    results = []
    for entry in COMMON_NOC_CATALOG:
        if teer is not None and entry["teer"] != teer:
            continue
        if query:
            haystack = " ".join([entry["noc"], entry["title"], entry["sector"], *entry["keywords"]]).lower()
            if query not in haystack:
                continue
        results.append(entry)

    return {
        "status": "success",
        "count": len(results),
        "esdc_noc_finder_url": ESDC_NOC_FINDER_URL,
        "results": results,
    }


@app.get("/api/communities")
def communities_endpoint(
    province: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    shortlisted_only: bool = Query(False),
) -> Dict[str, Any]:
    with store_session(_resolve_db_path()) as conn:
        shortlists = store_list_shortlists(conn)

    prov_filter = (province or "").strip().lower()
    search_filter = (search or "").strip().lower()
    items = []

    for comm in PARTICIPATING_COMMUNITIES:
        sl = shortlists.get(comm["id"], {})
        is_shortlisted = bool(sl.get("shortlisted", False))
        if shortlisted_only and not is_shortlisted:
            continue
        if prov_filter and prov_filter != "all":
            if prov_filter not in (comm["province"].lower(), comm["province_code"].lower()):
                continue
        if search_filter:
            blob = " ".join(
                [
                    comm["name"],
                    comm["province"],
                    comm["edo_name"],
                    *comm["key_sectors"],
                    *comm["local_institutions"],
                ]
            ).lower()
            if search_filter not in blob:
                continue

        items.append(
            {
                **comm,
                "shortlisted": is_shortlisted,
                "notes": sl.get("notes", ""),
                "employers_contacted": sl.get("employers_contacted", 0),
                "updated_at": sl.get("updated_at", ""),
            }
        )

    return {
        "status": "success",
        "total": len(items),
        "communities": items,
    }


@app.post("/api/communities/shortlist")
def shortlist_community_endpoint(payload: CommunityShortlistPayload) -> Dict[str, Any]:
    valid_ids = {c["id"] for c in PARTICIPATING_COMMUNITIES}
    if payload.community_id not in valid_ids:
        raise HTTPException(status_code=404, detail="Participating community not found.")
    with store_session(_resolve_db_path()) as conn:
        record = store_upsert_shortlist(
            conn,
            community_id=payload.community_id,
            shortlisted=payload.shortlisted,
            notes=payload.notes,
            employers_contacted=payload.employers_contacted,
        )
    return {"status": "success", "shortlist": record}


@app.post("/api/sync-sources")
@app.post("/api/sync-canada")
def sync_canada_endpoint() -> Dict[str, Any]:
    crawl_result = crawl_official_canada_pages()
    counts = {"inserted": 0, "updated": 0, "unchanged": 0}

    db_path = _resolve_db_path()
    with store_session(db_path) as conn:
        for page in crawl_result["pages"]:
            outcome = store_upsert_canada_page(conn, page)
            counts[outcome] = counts.get(outcome, 0) + 1
        all_pages = store_list_canada_pages(conn)

    rag_engine.index_pages(all_pages)
    return {
        "status": "success",
        "inserted": counts["inserted"],
        "updated": counts["updated"],
        "unchanged": counts["unchanged"],
        "failed": len(crawl_result["errors"]),
        "errors": crawl_result["errors"],
        "total_indexed": len(all_pages),
        "countries_indexed": len(COUNTRIES_CATALOG),
    }


@app.get("/api/sources")
def get_sources_endpoint() -> Dict[str, Any]:
    db_path = _resolve_db_path()
    with store_session(db_path) as conn:
        pages = store_list_canada_pages(conn)
    if not pages:
        pages = ensure_seeded_and_indexed(db_path)
    summary_pages = [
        {
            "url": p["url"],
            "track": p["track"],
            "slug": p["slug"],
            "title": p["title"],
            "site_last_modified": p["site_last_modified"],
            "alert_text": p["alert_text"],
            "fetched_at": p["fetched_at"],
        }
        for p in pages
    ]
    return {
        "status": "success",
        "count": len(summary_pages),
        "sources": summary_pages,
        "language_charts": LANGUAGE_TEST_CHARTS,
        "eca_organizations": ECA_ORGANIZATIONS,
    }


@app.post("/api/chat")
def chat_endpoint(payload: ChatPayload) -> Dict[str, Any]:
    if not payload.query or not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    db_path = _resolve_db_path()
    if not rag_engine.pages:
        ensure_seeded_and_indexed(db_path)
    if payload.profile is not None:
        profile = payload.profile
    else:
        with store_session(db_path) as conn:
            profile = store_get_profile(conn)
    result = rag_engine.answer_query(
        payload.query,
        profile=profile,
        country_id=payload.country_id,
    )
    return {"status": "success", **result}


# --------------------------------------------------------------------------
# Multi-Country JapaAI.ng Endpoints
# --------------------------------------------------------------------------

@app.get("/api/countries")
def list_countries_endpoint(
    region: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
) -> Dict[str, Any]:
    reg_filter = (region or "").strip().lower()
    q_filter = (search or "").strip().lower()

    results = []
    for c in COUNTRIES_CATALOG:
        if reg_filter and reg_filter != "all" and c["region"].lower() != reg_filter:
            continue
        if q_filter:
            blob = " ".join(
                [
                    c["name"],
                    c["code"],
                    c["region"],
                    c["authority"],
                    c["summary"],
                    *(p["name"] for p in c["pathways"]),
                ]
            ).lower()
            if q_filter not in blob:
                continue
        results.append(
            {
                "id": c["id"],
                "name": c["name"],
                "code": c["code"],
                "flag": c["flag"],
                "region": c["region"],
                "currency": c["currency"],
                "authority": c["authority"],
                "official_portal": c["official_portal"],
                "summary": c["summary"],
                "pathway_count": len(c["pathways"]),
                "pathway_names": [p["name"] for p in c["pathways"]],
                "has_deep_rcip": any(p.get("has_deep_engine") for p in c["pathways"]),
            }
        )

    return {
        "status": "success",
        "total": len(results),
        "countries": results,
    }


@app.get("/api/countries/{country_id}")
def get_country_hub_endpoint(country_id: str) -> Dict[str, Any]:
    target = next((c for c in COUNTRIES_CATALOG if c["id"] == country_id.strip().lower()), None)
    if not target:
        raise HTTPException(status_code=404, detail="Country not found in catalog.")
    return {"status": "success", "country": target}


@app.post("/api/global/match")
def global_match_endpoint(payload: Dict[str, Any]) -> Dict[str, Any]:
    result = match_global_pathways(payload or {})
    return {"status": "success", **result}


@app.post("/api/global/roadmap/export/html", response_class=HTMLResponse)
def export_global_roadmap_html(payload: GlobalRoadmapExportPayload) -> HTMLResponse:
    country = next((c for c in COUNTRIES_CATALOG if c["id"] == payload.country_id.strip().lower()), None)
    if not country:
        raise HTTPException(status_code=404, detail="Country not found.")
    pathway = next((p for p in country["pathways"] if p["id"] == payload.pathway_id.strip()), None)
    if not pathway:
        raise HTTPException(status_code=404, detail="Pathway not found.")

    esc = html_lib.escape
    name_safe = esc(payload.applicant_name or "Applicant")
    steps_html = ""
    done_count = 0
    for idx, step in enumerate(pathway["stages"], 1):
        is_done = bool(payload.checked_steps.get(step["id"]))
        if is_done:
            done_count += 1
        note = esc(str(payload.notes.get(step["id"], "") or ""))
        note_html = f"<div style='margin-top:4px; color:#047857; font-size:13px;'><strong>Note:</strong> {note}</div>" if note else ""
        steps_html += (
            f"<li><strong>[{'DONE' if is_done else 'TODO'}] Step {idx}: {esc(step['title'])}</strong><br>"
            f"<span>{esc(step['description'])}</span> "
            f"(<a href='{esc(step['url'])}'>Official Guide</a>){note_html}</li>"
        )

    notes_html = "".join(f"<li>{esc(n)}</li>" for n in country["nigerian_notes"])

    doc_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>JapaAI.ng — {esc(country['name'])}: {esc(pathway['name'])}</title>
<style>
  body {{ font-family: Arial, sans-serif; color: #0f172a; max-width: 880px; margin: 32px auto; padding: 0 20px; line-height: 1.55; }}
  h1 {{ color: #047857; border-bottom: 2px solid #047857; padding-bottom: 8px; }}
  .box {{ background: #f8fafc; border: 1px solid #cbd5e1; padding: 14px 16px; border-radius: 8px; margin-bottom: 18px; }}
  li {{ margin-bottom: 10px; }}
  @media print {{ .no-print {{ display: none; }} }}
</style>
</head>
<body>
  <div class="no-print" style="margin-bottom:16px;"><button onclick="window.print()">Print / Save PDF</button></div>
  <h1>JapaAI.ng — {esc(country['name'])} Immigration Roadmap</h1>
  <div class="box">
    <p><strong>Applicant:</strong> {name_safe}</p>
    <p><strong>Pathway:</strong> {esc(pathway['name'])} ({esc(pathway['category'])})</p>
    <p><strong>Official Authority:</strong> {esc(country['authority'])} (<a href="{esc(pathway['official_url'])}">{esc(pathway['official_url'])}</a>)</p>
    <p><strong>PR / Settlement Path:</strong> {esc(pathway['leads_to_pr'])}</p>
    <p><strong>Key Thresholds:</strong> {esc(pathway['threshold_label'])}</p>
    <p><strong>Checklist Progress:</strong> {done_count} / {len(pathway['stages'])} completed</p>
  </div>
  <h2>Official Step-by-Step Roadmap</h2>
  <ol>{steps_html}</ol>
  <h2>Nigerian Applicant Notes &amp; Watch-Outs</h2>
  <ul>{notes_html}</ul>
  <p style="margin-top:28px; font-size:12px; color:#64748b;">
    Grounded in official government portals indexed by JapaAI.ng. Informational guidance only; not legal immigration advice.
  </p>
</body>
</html>"""
    return HTMLResponse(content=doc_html)


def _render_export_html(
    profile: Dict[str, Any],
    progress_map: Dict[str, Any],
    shortlists: Dict[str, Any],
) -> HTMLResponse:
    evaluation = evaluate_rcip_eligibility(profile)
    roadmap = build_tailored_roadmap(profile, progress_map, evaluation)
    esc = html_lib.escape

    candidate_name = esc(str(profile.get("name") or "RCIP Candidate"))
    track_label = esc(evaluation["program_track"]["label"])
    verdict = esc(evaluation["verdict"])

    pillar_rows = "".join(
        f"<tr><td><strong>{esc(p['title'])}</strong></td>"
        f"<td>{esc(p['status'])}</td>"
        f"<td>{p['score']}/{p['max_score']}</td>"
        f"<td>{esc(p['summary'])}</td></tr>"
        for p in evaluation["pillars"]
    )

    action_rows = "".join(
        f"<li><strong>[{esc(a['priority'])}] {esc(a['pillar'])}:</strong> {esc(a['action'])} "
        f"(<a href='{esc(a['url'])}'>Canada.ca source</a>)</li>"
        for a in evaluation["action_plan"]
    ) or "<li>No remaining eligibility blockers detected.</li>"

    shortlisted_rows = "".join(
        f"<li><strong>{esc(c['name'])}, {esc(c['province_code'])}</strong> — "
        f"<a href='{esc(c['official_url'])}'>{esc(c['official_url'])}</a> "
        f"(Employers contacted: {int((shortlists.get(c['id']) or {}).get('employers_contacted', 0))})</li>"
        for c in PARTICIPATING_COMMUNITIES
        if (shortlists.get(c["id"]) or {}).get("shortlisted")
    ) or "<li>No participating communities shortlisted yet.</li>"

    stage_blocks = ""
    for stage in roadmap["stages"]:
        items_html = "".join(
            f"<li>[{'DONE' if item['completed'] else 'TODO'}] "
            f"{'(Optional / Not active for your branch) ' if not item['applicable'] else ''}"
            f"<strong>{esc(item['title'])}</strong> — {esc(item['description'])}</li>"
            for item in stage["items"]
        )
        stage_blocks += (
            f"<h3>{esc(stage['title'])} ({stage['completed_count']}/{stage['active_count']} done)</h3>"
            f"<p>{esc(stage['summary'])}</p><ul>{items_html}</ul>"
        )

    doc_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>RCIP Canada AI — Personalized Roadmap Report</title>
<style>
  body {{ font-family: Arial, sans-serif; color: #111827; max-width: 900px; margin: 32px auto; padding: 0 20px; line-height: 1.5; }}
  h1 {{ color: #991b1b; border-bottom: 2px solid #dc2626; padding-bottom: 8px; }}
  h2 {{ color: #1f2937; margin-top: 28px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
  th, td {{ border: 1px solid #d1d5db; padding: 8px 10px; text-align: left; font-size: 14px; }}
  th {{ background: #f3f4f6; }}
  .box {{ background: #f9fafb; border: 1px solid #e5e7eb; padding: 14px; border-radius: 6px; margin-bottom: 16px; }}
  @media print {{ .no-print {{ display: none; }} }}
</style>
</head>
<body>
  <div class="no-print" style="margin-bottom:16px;">
    <button onclick="window.print()">Print / Save PDF</button>
  </div>
  <h1>RCIP Canada AI — Personalized Roadmap Report</h1>
  <div class="box">
    <p><strong>Applicant:</strong> {candidate_name}</p>
    <p><strong>Readiness Score:</strong> {evaluation['readiness_score']}/100 ({esc(evaluation['overall_status'])})</p>
    <p><strong>Verdict:</strong> {verdict}</p>
    <p><strong>Program Track:</strong> {track_label}</p>
    <p><strong>Roadmap Checklist Progress:</strong> {roadmap['completed_items']}/{roadmap['total_items']} ({roadmap['completion_percent']}%)</p>
  </div>
  <h2>6-Pillar Eligibility Assessment</h2>
  <table>
    <thead><tr><th>Pillar</th><th>Status</th><th>Score</th><th>Assessment</th></tr></thead>
    <tbody>{pillar_rows}</tbody>
  </table>
  <h2>Prioritized Action Plan</h2>
  <ul>{action_rows}</ul>
  <h2>Shortlisted RCIP Communities</h2>
  <ul>{shortlisted_rows}</ul>
  <h2>6-Stage Canada.ca Roadmap</h2>
  {stage_blocks}
  <p style="margin-top:32px; font-size:12px; color:#6b7280;">
    Grounded in official Canada.ca Rural Community Immigration Pilot / Program documentation. Informational planning tool only; not legal immigration advice.
  </p>
</body>
</html>"""
    return HTMLResponse(content=doc_html)


@app.get("/api/roadmap/export/html", response_class=HTMLResponse)
def export_roadmap_html() -> HTMLResponse:
    """Serve a clean printable HTML dossier of the saved applicant's RCIP readiness, gap plan, and checklist."""
    db_path = _resolve_db_path()
    with store_session(db_path) as conn:
        profile = store_get_profile(conn)
        progress_map = store_list_progress(conn)
        shortlists = store_list_shortlists(conn)
    return _render_export_html(profile, progress_map, shortlists)


@app.post("/api/roadmap/export/html", response_class=HTMLResponse)
def export_roadmap_html_stateless(payload: ExportHtmlPayload) -> HTMLResponse:
    """Serve a printable HTML dossier computed directly from client-provided state (for Vercel multi-visitor use)."""
    return _render_export_html(payload.profile, payload.progress, payload.shortlists)


# Serve static frontend & PWA root assets
frontend_dir = os.path.join(str(BASE_DIR), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def serve_index() -> FileResponse:
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/manifest.webmanifest")
    def serve_manifest() -> FileResponse:
        return FileResponse(
            os.path.join(frontend_dir, "manifest.webmanifest"),
            media_type="application/manifest+json",
        )

    @app.get("/sw.js")
    def serve_service_worker() -> FileResponse:
        return FileResponse(
            os.path.join(frontend_dir, "sw.js"),
            media_type="application/javascript",
            headers={
                "Service-Worker-Allowed": "/",
                "Cache-Control": "no-cache",
            },
        )

    @app.get("/apple-touch-icon.png")
    def serve_apple_touch_icon() -> FileResponse:
        return FileResponse(
            os.path.join(frontend_dir, "icons", "icon-180.png"),
            media_type="image/png",
        )
