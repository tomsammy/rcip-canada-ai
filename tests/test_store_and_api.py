"""API and SQLite persistence tests for RCIP Canada AI."""

import os
import sys
import tempfile
import unittest

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app, ensure_seeded_and_indexed  # noqa: E402


class TestStoreAndAPI(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_rcip.db")
        app.state.db_path = self.db_path
        ensure_seeded_and_indexed(self.db_path)
        self.client = TestClient(app)

    def tearDown(self):
        app.state.db_path = None
        self.tmpdir.cleanup()

    def test_frontend_static_and_health(self):
        idx = self.client.get("/")
        self.assertEqual(idx.status_code, 200)
        self.assertIn("ai4japa.store", idx.text)
        self.assertIn("solutions-store-grid", idx.text)

        css = self.client.get("/static/styles.css")
        self.assertEqual(css.status_code, 200)

        js = self.client.get("/static/app.js")
        self.assertEqual(js.status_code, 200)

        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        self.assertGreater(health.json()["indexed_pages"], 0)

    def test_profile_evaluation_roadmap_and_progress_flow(self):
        # Empty profile -> 0% readiness
        stats_init = self.client.get("/api/stats").json()
        self.assertEqual(stats_init["readiness_score"], 0)

        # Save profile
        profile_payload = {
            "name": "Chidi Nwosu",
            "email": "chidi@example.com",
            "currently_in_canada": False,
            "in_canada_valid_work_permit": False,
            "family_size": 3,
            "available_funds_cad": 17000,
            "target_community_id": "thunder-bay",
            "target_job_noc_code": "21231",
            "target_job_teer": 1,
            "paid_work_hours_last_3_years": 2000,
            "experience_teer": 1,
            "language_test_type": "ielts_general",
            "language_test_age_months": 4,
            "lang_reading": 6.0,
            "lang_writing": 6.0,
            "lang_listening": 6.5,
            "lang_speaking": 6.0,
            "education_origin": "foreign",
            "has_eca": True,
            "eca_organization": "WES",
            "eca_age_years": 1.0,
        }
        save_res = self.client.post("/api/profile", json=profile_payload)
        self.assertEqual(save_res.status_code, 200)
        eval_data = save_res.json()["evaluation"]
        self.assertEqual(eval_data["readiness_score"], 70)
        self.assertEqual(eval_data["overall_status"], "ELIGIBLE_NEEDS_JOB_AND_RECOMMENDATION")

        # Persisted profile check
        got_prof = self.client.get("/api/profile").json()["profile"]
        self.assertEqual(got_prof["name"], "Chidi Nwosu")

        # Roadmap & toggle progress
        road = self.client.get("/api/roadmap").json()["roadmap"]
        self.assertEqual(len(road["stages"]), 6)

        prog_res = self.client.post(
            "/api/roadmap/progress",
            json={
                "item_id": "s1_language_test",
                "stage_id": "stage_1_eligibility",
                "completed": True,
                "notes": "IELTS General completed",
            },
        )
        self.assertEqual(prog_res.status_code, 200)
        self.assertTrue(prog_res.json()["progress"]["completed"])

        stats_after = self.client.get("/api/stats").json()
        self.assertEqual(stats_after["completed_tasks"], 1)

    def test_resume_upload_tools_communities_chat_and_export(self):
        # Resume TXT upload
        resume_bytes = (
            b"Jane Doe\njane.doe@example.com\n"
            b"Bachelor of Science in Computer Science\n"
            b"5 years of experience as a Software Engineer building Python, FastAPI, Docker, PostgreSQL microservices."
        )
        up_res = self.client.post(
            "/api/resume/upload",
            files={"file": ("resume.txt", resume_bytes, "text/plain")},
        )
        self.assertEqual(up_res.status_code, 200)
        parsed = up_res.json()["parsed"]
        self.assertIn("Python", parsed["detected_skills"])
        self.assertTrue(len(parsed["suggested_nocs"]) >= 1)
        self.assertEqual(parsed["suggested_nocs"][0]["noc"], "21231")

        # CLB convert tool
        clb_res = self.client.post(
            "/api/tools/clb-convert",
            json={"test_type": "ielts_general", "reading": 5.0, "writing": 5.5, "listening": 5.5, "speaking": 5.5},
        )
        self.assertEqual(clb_res.status_code, 200)
        self.assertEqual(clb_res.json()["conversion"]["overall_clb"], 6)

        # Funds tool
        funds_res = self.client.get("/api/tools/funds?family_size=4&in_canada_valid_work_permit=false")
        self.assertEqual(funds_res.status_code, 200)
        self.assertEqual(funds_res.json()["required_cad"], 19524)

        # NOC search tool
        noc_res = self.client.get("/api/tools/noc-search?q=nurse")
        self.assertEqual(noc_res.status_code, 200)
        self.assertTrue(any(item["noc"] == "31301" for item in noc_res.json()["results"]))

        # Communities & shortlist
        comm_res = self.client.get("/api/communities")
        self.assertEqual(comm_res.status_code, 200)
        self.assertEqual(comm_res.json()["total"], 14)

        sl_res = self.client.post(
            "/api/communities/shortlist",
            json={"community_id": "pictou-county", "shortlisted": True, "employers_contacted": 2},
        )
        self.assertEqual(sl_res.status_code, 200)

        shortlisted_only = self.client.get("/api/communities?shortlisted_only=true").json()
        self.assertEqual(shortlisted_only["total"], 1)

        # Sources & Chat
        sources_res = self.client.get("/api/sources")
        self.assertEqual(sources_res.status_code, 200)
        self.assertGreater(sources_res.json()["count"], 0)

        chat_res = self.client.post("/api/chat", json={"query": "What is the minimum CLB for TEER 1?"})
        self.assertEqual(chat_res.status_code, 200)
        self.assertIn("CLB 6", chat_res.json()["answer"])
        self.assertGreater(len(chat_res.json()["citations"]), 0)

        # Printable HTML Export
        export_res = self.client.get("/api/roadmap/export/html")
        self.assertEqual(export_res.status_code, 200)
        self.assertIn("ai4japa.store", export_res.text)
        self.assertIn("Pictou County", export_res.text)

    def test_vercel_entrypoint_and_stateless_endpoints(self):
        import app as vercel_entry

        self.assertIn("ai4japa.store", vercel_entry.app.title)

        health = self.client.get("/api/health").json()
        self.assertIn(health["environment"], ("local", "vercel"))
        self.assertIn(health["storage_mode"], ("sqlite_local", "browser_local_plus_tmp"))

        # Stateless roadmap computation
        comp = self.client.post(
            "/api/roadmap/compute",
            json={
                "profile": {
                    "name": "Ada <script>alert(1)</script>",
                    "in_canada_valid_work_permit": True,
                    "family_size": 3,
                    "target_job_teer": 1,
                },
                "progress": {
                    "s1_noc_teer": {"item_id": "s1_noc_teer", "stage_id": "stage_1_eligibility", "completed": True}
                },
            },
        )
        self.assertEqual(comp.status_code, 200)
        comp_data = comp.json()
        self.assertTrue(comp_data["evaluation"]["applicant_context"]["funds_exempt"])
        self.assertEqual(comp_data["roadmap"]["completed_items"], 1)

        # Stateless chat using client-supplied profile context
        chat = self.client.post(
            "/api/chat",
            json={
                "query": "How much settlement funds do I need?",
                "profile": {"family_size": 3, "in_canada_valid_work_permit": False},
            },
        )
        self.assertEqual(chat.status_code, 200)
        self.assertIn("$16,080", chat.json()["answer"])

        # Stateless HTML export escapes untrusted fields
        exp = self.client.post(
            "/api/roadmap/export/html",
            json={
                "profile": {"name": "Ada <script>alert(1)</script>", "family_size": 2},
                "progress": {},
                "shortlists": {"sudbury": {"shortlisted": True, "employers_contacted": 3}},
            },
        )
        self.assertEqual(exp.status_code, 200)
        self.assertNotIn("<script>alert(1)</script>", exp.text)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", exp.text)
        self.assertIn("Sudbury", exp.text)

        # Upload size cap (> 4.2 MB -> 413)
        too_big = b"a" * (4 * 1024 * 1024 + 300 * 1024)
        big_res = self.client.post(
            "/api/resume/upload",
            files={"file": ("big.txt", too_big, "text/plain")},
        )
        self.assertEqual(big_res.status_code, 413)


if __name__ == "__main__":
    unittest.main()
