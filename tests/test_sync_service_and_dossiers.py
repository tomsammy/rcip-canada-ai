"""Seam-level TDD tests for catalog schema, sync_service with fake HTTP adapters, and dossier rendering."""

import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.canada_crawler import SEED_CANADA_PAGES  # noqa: E402
from backend.catalog_schema import validate_countries_catalog  # noqa: E402
from backend.countries_data import COUNTRIES_CATALOG  # noqa: E402
from backend.dossier_renderer import (  # noqa: E402
    render_country_pathway_dossier,
    render_rcip_dossier,
)
from backend.matcher_engine import match_global_pathways  # noqa: E402
from backend.rag_service import CanadaRAGService  # noqa: E402
from backend.store import list_global_official_pages, store_session  # noqa: E402
from backend.sync_service import sync_official_sources  # noqa: E402


class CatalogSchemaAndDossierTests(unittest.TestCase):
    def test_live_catalog_has_zero_schema_or_localization_errors(self):
        self.assertEqual(validate_countries_catalog(COUNTRIES_CATALOG), [])

    def test_validator_catches_invalid_url_unknown_field_and_duplicate_pathway(self):
        broken = copy.deepcopy(COUNTRIES_CATALOG[:1])
        broken[0]["official_portal"] = "http://insecure.example.com"
        broken[0]["pathways"][0]["fields"] = ["invalid_field_xyz"]
        broken[0]["pathways"].append(copy.deepcopy(broken[0]["pathways"][0]))

        errs = validate_countries_catalog(broken)
        joined = "\n".join(errs)
        self.assertIn("https://", joined)
        self.assertIn("invalid_field_xyz", joined)
        self.assertIn("Duplicate pathway id", joined)

    def test_matcher_supports_spanish_and_portuguese_languages(self):
        sp_res = match_global_pathways(
            {
                "education_level": "bachelors",
                "years_experience": 3,
                "field": "tech",
                "spanish_level": "fluent",
                "monthly_remote_income_usd": 3500,
                "relocation_budget_usd": 7000,
            }
        )
        self.assertEqual(sp_res["status"], "MATCHED")
        by_id = {m["pathway_id"]: m for m in sp_res["all_matches"]}
        self.assertEqual(by_id["es-digital-nomad"]["fit_tier"], "STRONG_MATCH")

        pt_res = match_global_pathways(
            {
                "education_level": "bachelors",
                "years_experience": 2,
                "field": "tech",
                "portuguese_level": "fluent",
                "monthly_remote_income_usd": 2000,
                "relocation_budget_usd": 5000,
            }
        )
        pt_by_id = {m["pathway_id"]: m for m in pt_res["all_matches"]}
        self.assertEqual(pt_by_id["br-digital-nomad"]["fit_tier"], "STRONG_MATCH")

    def test_dossier_renderers_escape_xss_and_include_counts(self):
        uk = next(c for c in COUNTRIES_CATALOG if c["id"] == "uk")
        sw = uk["pathways"][0]
        step_id = sw["stages"][0]["id"]

        html_doc = render_country_pathway_dossier(
            country=uk,
            pathway=sw,
            applicant_name="<script>alert(1)</script>Kofi",
            checked_steps={step_id: True},
            notes={step_id: "<img src=x onerror=alert(2)>Uploaded"},
        )
        self.assertIn("ai4japa.store", html_doc)
        self.assertNotIn("<script>alert(1)</script>", html_doc)
        self.assertNotIn("<img src=x onerror=alert(2)>", html_doc)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;Kofi", html_doc)
        self.assertIn(f"1 / {len(sw['stages'])} completed", html_doc)

        rcip_doc = render_rcip_dossier(
            profile={"name": "<b>Ada</b>"},
            progress_map={"s1_noc_teer": {"completed": True}},
            shortlists={},
        )
        self.assertIn("ai4japa.store", rcip_doc)
        self.assertNotIn("<b>Ada</b>", rcip_doc)
        self.assertIn("&lt;b&gt;Ada&lt;/b&gt;", rcip_doc)


class SyncServiceSeamTests(unittest.TestCase):
    def test_sync_service_injectable_fetcher_lifecycle_and_honest_errors(self):
        version = {"v": 1}

        def fake_fetcher(url, timeout, headers):
            if "skilled-worker-visa" in url:
                return 403, "Forbidden", {}
            if "health-care-worker-visa" in url:
                raise TimeoutError("Simulated portal timeout")
            suffix = "Updated 2026 threshold notice." if version["v"] == 2 else ""
            html = f"""<!doctype html><html><head><title>UK Work Visas</title></head><body>
            <main>
              <h1>UK Work Immigration Portal</h1>
              <time datetime="2026-11-19">2026-11-19</time>
              <p>Apply on GOV.UK for Skilled Worker and Global Talent routes with official sponsor verification.</p>
              <p>{suffix}</p>
            </main></body></html>"""
            return 200, html, {"last-modified": "2026-11-19"}

        rag = CanadaRAGService()
        rag.index_pages(SEED_CANADA_PAGES)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_db = str(Path(tmpdir) / "sync_seam.db")

            # Cycle 1: inserts live portals, records 403 and TimeoutError without fabricating
            res1 = sync_official_sources("uk", tmp_db, rag, fetcher=fake_fetcher)
            self.assertEqual(res1["status"], "success")
            self.assertEqual(res1["live_fetched"], 2)
            self.assertEqual(res1["inserted"], 2)
            self.assertEqual(res1["failed"], 2)
            self.assertTrue(any(err.get("country_id") == "uk" and err.get("url") for err in res1["errors"]))

            # Cycle 2: identical HTML -> unchanged
            res2 = sync_official_sources("uk", tmp_db, rag, fetcher=fake_fetcher)
            self.assertEqual(res2["unchanged"], 2)
            self.assertEqual(res2["inserted"], 0)
            self.assertEqual(res2["updated"], 0)

            # Cycle 3: changed content -> updated and indexed as LIVE in RAG
            version["v"] = 2
            res3 = sync_official_sources("uk", tmp_db, rag, fetcher=fake_fetcher)
            self.assertEqual(res3["updated"], 2)

            with store_session(tmp_db) as conn:
                rows = list_global_official_pages(conn, country_id="uk")
                self.assertEqual(len(rows), 2)
                self.assertTrue(all("Updated 2026 threshold notice" in r["content_text"] for r in rows))

            chat = rag.answer_query("Updated 2026 threshold notice GOV.UK", country_id="uk")
            self.assertTrue(any(c.get("source_mode") == "live" for c in chat["citations"]))


if __name__ == "__main__":
    unittest.main()
