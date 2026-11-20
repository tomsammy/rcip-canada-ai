"""Single deterministic guardrail script verifying JapaAI.ng backend, schema parity, PWA, and JS checks."""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.catalog_schema import (  # noqa: E402
    ALLOWED_EDUCATION_LEVELS,
    validate_countries_catalog,
)
from backend.countries_data import COUNTRIES_CATALOG  # noqa: E402

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _run(cmd, label: str) -> None:
    print(f"[check] {label}...")
    proc = subprocess.run(cmd, cwd=str(ROOT))
    if proc.returncode != 0:
        raise SystemExit(f"FAILED: {label} (exit {proc.returncode})")


def _check_catalog_and_ui_parity() -> None:
    print("[check] Catalog invariants & UI enum parity...")
    errs = validate_countries_catalog(COUNTRIES_CATALOG)
    if errs:
        raise SystemExit("Catalog invariant errors:\n- " + "\n- ".join(errs))

    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    # Verify every profession field referenced by any pathway exists in #gm-field
    field_block_m = re.search(r'<select id="gm-field"[^>]*>(.*?)</select>', index_html, re.S)
    if not field_block_m:
        raise SystemExit("Missing <select id='gm-field'> in frontend/index.html")
    ui_fields = {v for v in re.findall(r'<option value="([^"]*)"', field_block_m.group(1)) if v}
    catalog_fields = {f for c in COUNTRIES_CATALOG for p in c["pathways"] for f in p["fields"]}
    missing_fields = sorted(catalog_fields - ui_fields)
    if missing_fields:
        raise SystemExit(f"UI #gm-field missing catalog fields: {missing_fields}")

    # Verify every education level exists in #gm-edu
    edu_block_m = re.search(r'<select id="gm-edu"[^>]*>(.*?)</select>', index_html, re.S)
    if not edu_block_m:
        raise SystemExit("Missing <select id='gm-edu'> in frontend/index.html")
    ui_edus = {v for v in re.findall(r'<option value="([^"]*)"', edu_block_m.group(1)) if v}
    missing_edus = sorted(ALLOWED_EDUCATION_LEVELS - ui_edus)
    if missing_edus:
        raise SystemExit(f"UI #gm-edu missing education levels: {missing_edus}")


def _check_forbidden_strings() -> None:
    print("[check] Forbidden legacy/localized text guard...")
    forbidden = [
        "Vercel Production",
        "Sync Canada.ca",
        "Canada RCIP Engine",
        "Built for Nigerians",
        "Nigerian Applicant",
        "WAEC",
        "OND / HND",
    ]
    targets = [
        ROOT / "frontend" / "index.html",
        ROOT / "frontend" / "app.js",
        ROOT / "frontend" / "js" / "utils.js",
        ROOT / "frontend" / "js" / "pwa.js",
        ROOT / "frontend" / "manifest.webmanifest",
    ]
    for path in targets:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                raise SystemExit(f"Forbidden string '{token}' found in {path.relative_to(ROOT)}")


def _check_pwa_assets() -> None:
    print("[check] PWA manifest & PNG icons...")
    manifest_path = ROOT / "frontend" / "manifest.webmanifest"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for icon in manifest.get("icons", []):
        src = str(icon.get("src") or "")
        if not src.startswith("/static/"):
            raise SystemExit(f"Unexpected icon path in manifest: {src}")
        rel = src[len("/static/"):]
        disk_path = ROOT / "frontend" / rel
        if not disk_path.exists():
            raise SystemExit(f"Missing manifest icon file: {disk_path}")
        if not disk_path.read_bytes().startswith(PNG_MAGIC):
            raise SystemExit(f"Invalid PNG header: {disk_path}")

    apple_icon = ROOT / "frontend" / "icons" / "icon-180.png"
    if not apple_icon.exists() or not apple_icon.read_bytes().startswith(PNG_MAGIC):
        raise SystemExit(f"Missing or corrupt Apple touch icon: {apple_icon}")
    if not (ROOT / "frontend" / "sw.js").exists():
        raise SystemExit("Missing frontend/sw.js")


def main() -> None:
    _run([sys.executable, "-m", "compileall", "-q", "backend", "app.py", "run_server.py", "scripts", "tests"], "Python bytecode compileall")
    _check_catalog_and_ui_parity()
    _check_forbidden_strings()
    _check_pwa_assets()
    _run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], "Python unit & API tests")
    for js_file in [
        "frontend/js/utils.js",
        "frontend/js/pwa.js",
        "frontend/app.js",
        "frontend/sw.js",
    ]:
        _run(["node", "--check", js_file], f"Node syntax check ({js_file})")
    _run(["node", "--test", "tests/test_frontend_utils.test.mjs"], "Node frontend utility unit tests")
    print("[check] ALL GUARDRAILS PASSED")


if __name__ == "__main__":
    main()
