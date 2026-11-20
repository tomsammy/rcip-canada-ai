"""Unit and API tests for JapaAI.ng 12-country catalog, global matcher, and endpoints."""

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.countries_data import COUNTRIES_CATALOG  # noqa: E402
from backend.main import app  # noqa: E402
from backend.matcher_engine import match_global_pathways  # noqa: E402

EXPECTED_COUNTRY_IDS = {
    "canada",
    "uk",
    "usa",
    "germany",
    "netherlands",
    "sweden",
    "estonia",
    "bulgaria",
    "lithuania",
    "spain",
    "france",
    "brazil",
}


class GlobalCatalogAndMatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_twelve_country_catalog_integrity(self):
        self.assertEqual(len(COUNTRIES_CATALOG), 12)
        ids = {c["id"] for c in COUNTRIES_CATALOG}
        self.assertEqual(ids, EXPECTED_COUNTRY_IDS)

        seen_pathway_ids = set()
        for country in COUNTRIES_CATALOG:
            self.assertTrue(
                country["official_portal"].startswith("https://"),
                f"{country['id']} portal must use https://",
            )
            self.assertTrue(country.get("nigerian_notes"), f"{country['id']} missing Nigerian notes")
            pathways = country["pathways"]
            if country["id"] == "canada":
                self.assertEqual(len(pathways), 6)
            else:
                self.assertGreaterEqual(len(pathways), 3, f"{country['id']} needs >= 3 pathways")

            for p in pathways:
                self.assertNotIn(p["id"], seen_pathway_ids)
                seen_pathway_ids.add(p["id"])
                self.assertTrue(p["official_url"].startswith("https://"), f"{p['id']} URL invalid")
                self.assertGreaterEqual(len(p["stages"]), 2, f"{p['id']} needs >= 2 stages")
                for st in p["stages"]:
                    self.assertTrue(st["url"].startswith("https://"), f"{st['id']} stage URL invalid")

    def test_incomplete_profile_has_zero_fake_matches(self):
        empty_res = match_global_pathways({})
        self.assertEqual(empty_res["status"], "INCOMPLETE")
        self.assertEqual(empty_res["total_pathways"], 0)
        self.assertEqual(empty_res["all_matches"], [])

        blank_res = match_global_pathways({"education_level": "", "years_experience": 0, "field": ""})
        self.assertEqual(blank_res["status"], "INCOMPLETE")
        self.assertEqual(blank_res["total_pathways"], 0)

    def test_remote_tech_earner_matches_spain_and_brazil_nomad(self):
        profile = {
            "education_level": "bachelors",
            "years_experience": 4,
            "field": "tech",
            "english_level": "fluent",
            "relocation_budget_usd": 8000,
            "monthly_remote_income_usd": 3500,
        }
        res = match_global_pathways(profile)
        self.assertEqual(res["status"], "MATCHED")
        self.assertGreaterEqual(len(res["top_matches"]), 2)

        by_id = {m["pathway_id"]: m for m in res["all_matches"]}
        self.assertIn("es-digital-nomad", by_id)
        self.assertIn("br-digital-nomad", by_id)
        self.assertEqual(by_id["es-digital-nomad"]["fit_tier"], "STRONG_MATCH")
        self.assertEqual(by_id["br-digital-nomad"]["fit_tier"], "STRONG_MATCH")
        # Strict healthcare gate must not pass a tech-only profile as strong match
        self.assertNotEqual(by_id["uk-health-care"]["fit_tier"], "STRONG_MATCH")

    def test_healthcare_and_french_profiles(self):
        hc_profile = {
            "education_level": "bachelors",
            "years_experience": 3,
            "field": "healthcare",
            "english_level": "fluent",
            "relocation_budget_usd": 10000,
            "has_foreign_job_offer": True,
        }
        hc_res = match_global_pathways(hc_profile)
        hc_by_id = {m["pathway_id"]: m for m in hc_res["all_matches"]}
        self.assertEqual(hc_by_id["uk-health-care"]["fit_tier"], "STRONG_MATCH")
        # No French should block Canada Francophone pilot
        self.assertNotEqual(hc_by_id["ca-fcip"]["fit_tier"], "STRONG_MATCH")

        fr_profile = {
            "education_level": "bachelors",
            "years_experience": 3,
            "field": "tech",
            "english_level": "fluent",
            "french_level": "intermediate",
            "relocation_budget_usd": 12000,
            "has_foreign_job_offer": True,
        }
        fr_res = match_global_pathways(fr_profile)
        fr_by_id = {m["pathway_id"]: m for m in fr_res["all_matches"]}
        self.assertEqual(fr_by_id["ca-fcip"]["fit_tier"], "STRONG_MATCH")
        self.assertGreaterEqual(fr_by_id["fr-talent-blue-card"]["score"], 70)

    def test_global_api_endpoints_and_export_escaping(self):
        countries_resp = self.client.get("/api/countries")
        self.assertEqual(countries_resp.status_code, 200)
        cdata = countries_resp.json()
        self.assertEqual(cdata["status"], "success")
        self.assertEqual(cdata["total"], 12)
        self.assertEqual(len(cdata["countries"]), 12)

        filtered = self.client.get("/api/countries?search=Brazil")
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(filtered.json()["total"], 1)

        usa_resp = self.client.get("/api/countries/usa")
        self.assertEqual(usa_resp.status_code, 200)
        self.assertEqual(usa_resp.json()["country"]["id"], "usa")

        missing_resp = self.client.get("/api/countries/unknown")
        self.assertEqual(missing_resp.status_code, 404)

        empty_match = self.client.post("/api/global/match", json={})
        self.assertEqual(empty_match.status_code, 200)
        self.assertEqual(empty_match.json()["status"], "INCOMPLETE")

        good_match = self.client.post(
            "/api/global/match",
            json={
                "education_level": "bachelors",
                "years_experience": 4,
                "field": "tech",
                "english_level": "fluent",
                "relocation_budget_usd": 8000,
                "monthly_remote_income_usd": 3500,
            },
        )
        self.assertEqual(good_match.status_code, 200)
        mdata = good_match.json()
        self.assertEqual(mdata["status"], "MATCHED")
        self.assertGreaterEqual(mdata["total_pathways"], 40)

        chat_resp = self.client.post(
            "/api/chat",
            json={
                "query": "Can Nigerians apply for the USA Diversity Visa lottery?",
                "country_id": "usa",
            },
        )
        self.assertEqual(chat_resp.status_code, 200)
        chat_json = chat_resp.json()
        answer_text = chat_json.get("answer", "")
        self.assertTrue(
            "diversity" in answer_text.lower() or "nigeria" in answer_text.lower(),
            f"Unexpected USA chat answer: {answer_text[:200]}",
        )

        export_resp = self.client.post(
            "/api/global/roadmap/export/html",
            json={
                "country_id": "uk",
                "pathway_id": "uk-skilled-worker",
                "applicant_name": "<script>alert(1)</script>Ada",
                "checked_steps": {"uk-sw-1": True},
                "notes": {"uk-sw-1": "<img src=x onerror=alert(2)>Target COS"},
            },
        )
        self.assertEqual(export_resp.status_code, 200)
        html_body = export_resp.text
        self.assertNotIn("<script>alert(1)</script>", html_body)
        self.assertNotIn("<img src=x onerror=alert(2)>", html_body)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;Ada", html_body)
        self.assertIn("Skilled Worker", html_body)


if __name__ == "__main__":
    unittest.main()
