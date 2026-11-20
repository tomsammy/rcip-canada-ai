"""Unit tests for the RCIP eligibility, CLB conversion, settlement funds, and track engine."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.eligibility_engine import (  # noqa: E402
    compute_clb_from_test,
    determine_program_track,
    evaluate_education,
    evaluate_rcip_eligibility,
    evaluate_settlement_funds,
    evaluate_work_experience,
    required_settlement_funds,
)


class TestRCIPHonestScoringAndTracks(unittest.TestCase):
    def test_empty_profile_returns_zero_and_incomplete(self):
        result = evaluate_rcip_eligibility({})
        self.assertEqual(result["readiness_score"], 0)
        self.assertEqual(result["overall_status"], "INCOMPLETE")
        self.assertEqual(result["program_track"]["track"], "permanent")

    def test_program_track_routing_pilot_vs_permanent(self):
        pilot = determine_program_track(
            {"has_community_recommendation": True, "recommendation_date": "2026-12-31"}
        )
        self.assertEqual(pilot["track"], "pilot")

        perm_jan = determine_program_track(
            {"has_community_recommendation": True, "recommendation_date": "2027-01-01"}
        )
        self.assertEqual(perm_jan["track"], "permanent")

        no_rec = determine_program_track({"has_community_recommendation": False})
        self.assertEqual(no_rec["track"], "permanent")

    def test_full_ready_profile_scores_100(self):
        profile = {
            "name": "Amina Okafor",
            "currently_in_canada": False,
            "in_canada_valid_work_permit": False,
            "family_size": 2,
            "available_funds_cad": 14000,
            "target_community_id": "sudbury",
            "target_job_noc_code": "21231",
            "target_job_teer": 1,
            "paid_work_hours_last_3_years": 2080,
            "experience_teer": 1,
            "experience_noc_code": "21231",
            "language_test_type": "ielts_general",
            "language_test_age_months": 6,
            "lang_reading": 6.5,
            "lang_writing": 6.0,
            "lang_listening": 7.0,
            "lang_speaking": 6.5,
            "education_origin": "foreign",
            "has_eca": True,
            "eca_organization": "WES",
            "eca_age_years": 1.5,
            "has_job_offer": True,
            "offer_from_designated_employer": True,
            "offer_full_time_30h": True,
            "offer_non_seasonal": True,
            "offer_indeterminate": True,
            "offer_inside_community": True,
            "has_community_recommendation": True,
            "recommendation_date": "2026-11-15",
        }
        result = evaluate_rcip_eligibility(profile)
        self.assertEqual(result["readiness_score"], 100)
        self.assertEqual(result["overall_status"], "READY_TO_APPLY_PR")
        self.assertEqual(result["program_track"]["track"], "pilot")
        self.assertEqual(result["action_plan"], [])


class TestWorkExperienceAndLocalGraduate(unittest.TestCase):
    def test_teer_cross_matrix_rules(self):
        # TEER 1 offer accepts TEER 3 experience
        res_pass = evaluate_work_experience(
            {"paid_work_hours_last_3_years": 1600, "experience_teer": 3, "target_job_teer": 1}
        )
        self.assertEqual(res_pass["status"], "PASS")
        self.assertEqual(res_pass["score"], 20)

        # TEER 2 offer rejects TEER 0 experience (allowed: 1, 2, 3, 4)
        res_fail = evaluate_work_experience(
            {"paid_work_hours_last_3_years": 2000, "experience_teer": 0, "target_job_teer": 2}
        )
        self.assertEqual(res_fail["status"], "ACTION_REQUIRED")
        self.assertEqual(res_fail["score"], 0)

    def test_teer5_requires_exact_same_5digit_noc(self):
        mismatch = evaluate_work_experience(
            {
                "paid_work_hours_last_3_years": 1800,
                "experience_teer": 5,
                "experience_noc_code": "65201",
                "target_job_teer": 5,
                "target_job_noc_code": "95106",
            }
        )
        self.assertEqual(mismatch["status"], "BLOCKED")
        self.assertEqual(mismatch["score"], 0)

        exact = evaluate_work_experience(
            {
                "paid_work_hours_last_3_years": 1800,
                "experience_teer": 5,
                "experience_noc_code": "95106",
                "target_job_teer": 5,
                "target_job_noc_code": "95106",
            }
        )
        self.assertEqual(exact["status"], "PASS")

    def test_healthcare_nurse_exception(self):
        res = evaluate_work_experience(
            {
                "paid_work_hours_last_3_years": 1560,
                "experience_teer": 1,
                "experience_noc_code": "31301",
                "target_job_teer": 3,
                "target_job_noc_code": "33102",
            }
        )
        self.assertEqual(res["status"], "PASS")

    def test_local_graduate_exemption_pass_and_disqualifiers(self):
        # 2+ year credential with 16/24 months residency and <=18 months since graduation
        ok_2yr = evaluate_work_experience(
            {
                "is_local_graduate": True,
                "grad_program_type": "2yr_plus",
                "grad_public_institution_in_community": True,
                "grad_full_time": True,
                "months_since_graduation": 6,
                "grad_lived_in_community_months": 18,
            }
        )
        self.assertEqual(ok_2yr["status"], "EXEMPT")
        self.assertEqual(ok_2yr["score"], 20)

        # Master's <= 2 years living entire duration in community
        ok_masters = evaluate_work_experience(
            {
                "is_local_graduate": True,
                "grad_program_type": "masters_phd",
                "grad_public_institution_in_community": True,
                "grad_full_time": True,
                "months_since_graduation": 12,
                "grad_lived_entire_duration": True,
            }
        )
        self.assertEqual(ok_masters["status"], "EXEMPT")

        # Expired (> 18 months) without fallback work hours
        expired = evaluate_work_experience(
            {
                "is_local_graduate": True,
                "grad_program_type": "2yr_plus",
                "grad_public_institution_in_community": True,
                "grad_full_time": True,
                "months_since_graduation": 20,
                "grad_lived_in_community_months": 20,
            }
        )
        self.assertEqual(expired["status"], "ACTION_REQUIRED")
        self.assertEqual(expired["score"], 0)

        # Disqualified by >50% distance learning, >50% language study, or return-home scholarship
        for disqualifier in (
            "grad_over_half_distance_learning",
            "grad_over_half_language_study",
            "grad_return_home_scholarship",
        ):
            bad = evaluate_work_experience(
                {
                    "is_local_graduate": True,
                    "grad_program_type": "2yr_plus",
                    "grad_public_institution_in_community": True,
                    "grad_full_time": True,
                    "months_since_graduation": 6,
                    "grad_lived_in_community_months": 20,
                    disqualifier: True,
                }
            )
            self.assertEqual(bad["status"], "ACTION_REQUIRED", f"Failed check for {disqualifier}")


class TestLanguageFundsAndEducation(unittest.TestCase):
    def test_language_equivalency_and_lowest_skill_governs(self):
        # IELTS CLB 6 minimum: R 5.0, W 5.5, L 5.5, S 5.5
        ielts = compute_clb_from_test("ielts_general", 7.0, 5.0, 7.5, 6.5)
        self.assertEqual(ielts["per_skill_clb"]["reading"], 9)
        self.assertEqual(ielts["per_skill_clb"]["writing"], 5)
        self.assertEqual(ielts["overall_clb"], 5)
        self.assertEqual(ielts["weakest_skills"], ["writing"])

        # CELPIP-General
        celpip = compute_clb_from_test("celpip_general", 8, 7, 6, 9)
        self.assertEqual(celpip["overall_clb"], 6)

        # PTE Core CLB 5 minimums: R 42, W 51, L 39, S 51
        pte = compute_clb_from_test("pte_core", 45, 55, 40, 52)
        self.assertEqual(pte["overall_clb"], 5)

        # TEF Canada NCLC 6: R 393, W 379, L 393, S 422
        tef = compute_clb_from_test("tef_canada", 400, 385, 410, 425)
        self.assertEqual(tef["overall_clb"], 6)

        # TCF Canada NCLC 5: R 375, W 6, L 369, S 6
        tcf = compute_clb_from_test("tcf_canada", 380, 6, 370, 6)
        self.assertEqual(tcf["overall_clb"], 5)

    def test_settlement_funds_table_and_work_permit_exemption(self):
        self.assertEqual(required_settlement_funds(1), 10507)
        self.assertEqual(required_settlement_funds(2), 13080)
        self.assertEqual(required_settlement_funds(3), 16080)
        self.assertEqual(required_settlement_funds(7), 27806)
        self.assertEqual(required_settlement_funds(8), 27806 + 2831)

        exempt = evaluate_settlement_funds({"in_canada_valid_work_permit": True, "family_size": 4, "available_funds_cad": 0})
        self.assertEqual(exempt["status"], "EXEMPT")
        self.assertEqual(exempt["score"], 15)

        shortfall = evaluate_settlement_funds({"in_canada_valid_work_permit": False, "family_size": 3, "available_funds_cad": 15000})
        self.assertEqual(shortfall["status"], "ACTION_REQUIRED")
        self.assertEqual(shortfall["shortfall_cad"], 1080)

    def test_education_eca_expiry_and_architect_cacb(self):
        expired = evaluate_education({"education_origin": "foreign", "has_eca": True, "eca_age_years": 5.5})
        self.assertEqual(expired["status"], "ACTION_REQUIRED")

        arch = evaluate_education(
            {
                "education_origin": "foreign",
                "has_eca": True,
                "eca_organization": "WES",
                "eca_age_years": 1.0,
                "target_job_noc_code": "21200",
            }
        )
        self.assertEqual(arch["status"], "PASS")
        self.assertTrue(any("CACB" in d for d in arch["details"]))


if __name__ == "__main__":
    unittest.main()
