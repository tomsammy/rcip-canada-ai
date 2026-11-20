"""Unit tests for the Canada.ca HTML parser and grounded RAG service."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.canada_crawler import SEED_CANADA_PAGES, parse_canada_page_html  # noqa: E402
from backend.rag_service import CanadaRAGService  # noqa: E402

SAMPLE_CANADA_HTML = """<!DOCTYPE html>
<html lang="en">
<head><title>Get a job offer - Canada.ca</title></head>
<body>
<main>
  <h1>Get a job offer and a community recommendation</h1>
  <section class="alert alert-warning">
    <p>As of January 1, 2027, the Rural Community Immigration Pilot will close.</p>
  </section>
  <p>Each community designates employers and posts priority sectors.</p>
  <ul>
    <li><a href="https://pictoucountypartnership.com/rcip/">Pictou County website</a></li>
    <li><a href="/en/immigration-refugees-citizenship/services/immigrate-canada.html">Immigrate</a></li>
  </ul>
  <div class="pagedetails">
    <dl id="wb-dtmd"><dt>Date modified:</dt><dd><time property="dateModified">2026-11-09</time></dd></dl>
  </div>
</main>
</body>
</html>"""


class TestCrawlerAndRAG(unittest.TestCase):
    def test_parse_canada_page_html_extracts_fields(self):
        parsed = parse_canada_page_html(
            SAMPLE_CANADA_HTML,
            url="https://www.canada.ca/en/test/job-offer.html",
            track="pilot",
            slug="pilot-job-offer",
        )
        self.assertEqual(parsed["title"], "Get a job offer and a community recommendation")
        self.assertIn("January 1, 2027", parsed["alert_text"])
        self.assertEqual(parsed["site_last_modified"], "2026-11-09")
        self.assertIn("designates employers", parsed["content_text"])
        self.assertEqual(len(parsed["external_links"]), 1)
        self.assertEqual(parsed["external_links"][0]["url"], "https://pictoucountypartnership.com/rcip/")

    def test_rag_retrieves_and_cites_official_pages(self):
        rag = CanadaRAGService()
        rag.index_pages(SEED_CANADA_PAGES)

        funds_ans = rag.answer_query(
            "How much settlement funds do I need for a family of 3?",
            profile={"family_size": 3, "in_canada_valid_work_permit": False},
        )
        self.assertIn("$16,080", funds_ans["answer"])
        self.assertTrue(any("proof-funds.html" in c["url"] for c in funds_ans["citations"]))

        transition_ans = rag.answer_query("What happens on January 1, 2027?")
        self.assertIn("2027", transition_ans["answer"])
        self.assertTrue(any("canada.ca" in c["url"] for c in transition_ans["citations"]))

        grad_ans = rag.answer_query("Am I exempt from work experience as a local graduate?")
        self.assertIn("18 months", grad_ans["answer"])
        self.assertTrue(any("work-experience.html" in c["url"] for c in grad_ans["citations"]))


if __name__ == "__main__":
    unittest.main()
