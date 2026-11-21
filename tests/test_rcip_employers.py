"""Unit and API tests for Canada RCIP Designated Employers Directory & CV Matching."""

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.main import app  # noqa: E402
from backend.rcip_employers import (  # noqa: E402
    DESIGNATED_EMPLOYERS_DIRECTORY,
    build_job_bank_url,
    list_designated_employers,
    match_cv_to_rcip_employers,
    validate_designated_employers_directory,
)


class RCIPDesignatedEmployersTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_directory_invariants_and_counts(self):
        self.assertEqual(validate_designated_employers_directory(), [])
        self.assertGreaterEqual(len(DESIGNATED_EMPLOYERS_DIRECTORY), 30)

        listing = list_designated_employers()
        self.assertEqual(listing["communities_count"], 14)
        self.assertEqual(len(listing["official_workflow"]), 3)
        self.assertGreaterEqual(len(listing["compliance_warnings"]), 3)
        for comm in listing["communities"]:
            self.assertTrue(comm["employer_directory_url"].startswith("https://"))
            self.assertTrue(comm["job_bank_url"].startswith("https://www.jobbank.gc.ca/"))

    def test_job_bank_url_builder(self):
        url = build_job_bank_url("Registered Nurse", "Timmins, ON")
        self.assertTrue(url.startswith("https://www.jobbank.gc.ca/jobsearch/jobsearch?"))
        self.assertIn("searchstring=Registered+Nurse", url)
        self.assertIn("locationstring=Timmins%2C+ON", url)

    def test_nurse_cv_matches_hospitals_and_health_authorities(self):
        nurse_cv = """
        Jane Doe
        Registered Nurse (ICU & Emergency) — 5 years hospital patient care experience
        Skills: Registered Nurse, Nursing, Patient Care, Medication Administration, LPN
        """
        res = match_cv_to_rcip_employers(free_text=nurse_cv)
        self.assertEqual(res["status"], "MATCHED")
        self.assertGreater(res["total_matched"], 0)

        top_ids = [e["id"] for e in res["matched_employers"]]
        for expected in (
            "tadh-timmins",
            "prairie-mountain-health-brandon",
            "interior-health-west-kootenay",
            "northern-health-peace-liard",
        ):
            self.assertIn(expected, top_ids)

        tadh = next(e for e in res["matched_employers"] if e["id"] == "tadh-timmins")
        self.assertEqual(tadh["fit_tier"], "STRONG_FIT")
        self.assertGreaterEqual(tadh["match_score"], 65)
        self.assertTrue(any("31301" in reason for reason in tadh["match_reasons"]))
        self.assertTrue(tadh["careers_url"].startswith("https://"))

    def test_software_engineer_cv_matches_tech_employers(self):
        dev_cv = """
        Alex Rivera
        Senior Software Engineer & Full Stack Developer (4 years experience)
        Technical Skills: Python, FastAPI, SQL, TypeScript, React
        """
        res = match_cv_to_rcip_employers(free_text=dev_cv)
        self.assertEqual(res["status"], "MATCHED")
        matched_ids = {e["id"] for e in res["matched_employers"]}
        for expected in (
            "city-greater-sudbury",
            "nss-canada-sudbury",
            "orix-geo-sudbury",
            "mnp-moose-jaw",
            "friesens-altona",
            "valid-mfg-west-kootenay",
        ):
            self.assertIn(expected, matched_ids)

        systems_cv = """
        Taylor Kim
        Systems Analyst, DevOps & Industrial Automation Engineer
        Skills: Cybersecurity, DevOps, PLC, Embedded, Manufacturing
        """
        sys_res = match_cv_to_rcip_employers(free_text=systems_cv)
        self.assertIn("tenaris-ssm", {e["id"] for e in sys_res["matched_employers"]})

    def test_trades_and_transport_cv_matches_industrial_employers(self):
        trades_cv = """
        Sam Taylor
        Red Seal Welder, Construction Millwright & Class 1 Truck Driver — 6 years experience
        Skills: Welding, MIG, TIG, Millwright, Truck Driving, Class 1
        """
        res = match_cv_to_rcip_employers(free_text=trades_cv)
        self.assertEqual(res["status"], "MATCHED")
        matched_ids = {e["id"] for e in res["matched_employers"]}
        for expected in (
            "agnico-eagle-timmins",
            "toromont-cat-timmins",
            "elmers-mfg-altona",
            "big-freight-steinbach",
            "ontario-northland-north-bay",
        ):
            self.assertIn(expected, matched_ids)

    def test_empty_cv_has_zero_fake_matches(self):
        res = match_cv_to_rcip_employers()
        self.assertEqual(res["status"], "NEEDS_INPUT")
        self.assertEqual(res["total_matched"], 0)
        self.assertEqual(res["matched_employers"], [])

    def test_rcip_employers_and_match_api_endpoints(self):
        resp = self.client.get("/api/rcip/employers")
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertGreaterEqual(payload["total_employers"], 34)
        self.assertEqual(payload["communities_count"], 14)

        on_resp = self.client.get("/api/rcip/employers?province=ON&community_id=timmins")
        self.assertEqual(on_resp.status_code, 200)
        on_data = on_resp.json()
        self.assertTrue(len(on_data["employers"]) >= 5)
        self.assertTrue(all(e["community_id"] == "timmins" for e in on_data["employers"]))

        json_match = self.client.post(
            "/api/rcip/match-employers",
            json={
                "resume_text": "Registered Nurse with 4 years Patient Care and Medication Administration experience",
            },
        )
        self.assertEqual(json_match.status_code, 200)
        jm = json_match.json()
        self.assertEqual(jm["status"], "MATCHED")
        self.assertGreater(jm["total_matched"], 0)

        upload_match = self.client.post(
            "/api/rcip/match-employers",
            files={
                "file": (
                    "cv.txt",
                    b"Software Engineer experienced with Python, FastAPI, SQL, and TypeScript.",
                    "text/plain",
                )
            },
        )
        self.assertEqual(upload_match.status_code, 200)
        um = upload_match.json()
        self.assertEqual(um["status"], "MATCHED")
        self.assertGreater(um["total_matched"], 0)
        self.assertEqual(um["parsed"]["filename"], "cv.txt")

        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn("rcip-sub-employers", home.text)
        self.assertIn("/static/app.js?v=8", home.text)


if __name__ == "__main__":
    unittest.main()
