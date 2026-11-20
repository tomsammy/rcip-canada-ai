"""Printable HTML Dossier renderers for global Country Hubs and Canada RCIP."""

import html as html_lib
from typing import Any, Dict

from backend.eligibility_engine import build_tailored_roadmap, evaluate_rcip_eligibility
from backend.rcip_data import PARTICIPATING_COMMUNITIES

_BASE_PRINT_CSS = """
  body {{ font-family: Arial, sans-serif; color: #0f172a; max-width: {max_width}px; margin: 32px auto; padding: 0 20px; line-height: 1.55; }}
  h1 {{ color: {accent}; border-bottom: 2px solid {accent}; padding-bottom: 8px; }}
  h2 {{ color: #1f2937; margin-top: 28px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
  th, td {{ border: 1px solid #d1d5db; padding: 8px 10px; text-align: left; font-size: 14px; }}
  th {{ background: #f3f4f6; }}
  .box {{ background: #f8fafc; border: 1px solid #cbd5e1; padding: 14px 16px; border-radius: 8px; margin-bottom: 18px; }}
  li {{ margin-bottom: 10px; }}
  @media print {{ .no-print {{ display: none; }} }}
"""


def render_country_pathway_dossier(
    country: Dict[str, Any],
    pathway: Dict[str, Any],
    applicant_name: str,
    checked_steps: Dict[str, bool],
    notes: Dict[str, str],
) -> str:
    """Render an escaped printable HTML Dossier for any Destination Hub pathway."""
    esc = html_lib.escape
    name_safe = esc(applicant_name or "Applicant")
    steps_html = ""
    done_count = 0

    for idx, step in enumerate(pathway.get("stages", []), 1):
        sid = step["id"]
        is_done = bool((checked_steps or {}).get(sid))
        if is_done:
            done_count += 1
        note = esc(str((notes or {}).get(sid, "") or ""))
        note_html = (
            f"<div style='margin-top:4px; color:#047857; font-size:13px;'><strong>Note:</strong> {note}</div>"
            if note
            else ""
        )
        steps_html += (
            f"<li><strong>[{'DONE' if is_done else 'TODO'}] Step {idx}: {esc(step['title'])}</strong><br>"
            f"<span>{esc(step['description'])}</span> "
            f"(<a href='{esc(step['url'])}'>Official Guide</a>){note_html}</li>"
        )

    notes_html = "".join(f"<li>{esc(n)}</li>" for n in (country.get("applicant_notes") or []))
    css = _BASE_PRINT_CSS.format(max_width=880, accent="#047857")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>JapaAI.ng — {esc(country['name'])}: {esc(pathway['name'])}</title>
<style>{css}</style>
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
    <p><strong>Checklist Progress:</strong> {done_count} / {len(pathway.get('stages', []))} completed</p>
  </div>
  <h2>Official Step-by-Step Roadmap</h2>
  <ol>{steps_html}</ol>
  <h2>Official Applicant Notes &amp; Key Requirements</h2>
  <ul>{notes_html}</ul>
  <p style="margin-top:28px; font-size:12px; color:#64748b;">
    Curated directly from official government portals indexed by JapaAI.ng with no added assumptions. Informational planning guide only; not legal immigration advice.
  </p>
</body>
</html>"""


def render_rcip_dossier(
    profile: Dict[str, Any],
    progress_map: Dict[str, Any],
    shortlists: Dict[str, Any],
) -> str:
    """Render an escaped printable HTML Dossier for Canada RCIP eligibility and checklist progress."""
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

    css = _BASE_PRINT_CSS.format(max_width=900, accent="#991b1b")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>RCIP Canada AI — Personalized Roadmap Report</title>
<style>{css}</style>
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
