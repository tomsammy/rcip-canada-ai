"""Grounded Canada.ca RAG service for RCIP guidance with verified citations."""

import math
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.eligibility_engine import (
    determine_program_track,
    required_settlement_funds,
)
from backend.rcip_data import PARTICIPATING_COMMUNITIES, TEER_MIN_CLB

_STOPWORDS = {
    "the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "is", "are",
    "was", "were", "be", "can", "do", "does", "i", "my", "me", "we", "you", "your",
    "what", "how", "when", "where", "which", "who", "if", "under", "with", "that",
    "this", "from", "by", "as", "at", "it", "need", "about", "get",
}

_DOMAIN_BOOST_GROUPS = (
    ({"2027", "january", "december", "pilot", "permanent", "transition", "close", "closes", "expire"}, ("pilot-overview", "permanent-overview")),
    ({"funds", "money", "lico", "bank", "family", "settlement", "cad", "10507", "13080", "16080"}, ("pilot-proof-funds",)),
    ({"language", "clb", "nclc", "ielts", "celpip", "pte", "tef", "tcf"}, ("pilot-language-test",)),
    ({"work", "experience", "1560", "hours", "teer", "noc", "graduate", "student", "18", "16", "31301", "nurse"}, ("pilot-work-experience",)),
    ({"education", "eca", "wes", "iqas", "icas", "ces", "ices", "cacb", "mcc", "pebc", "architect", "doctor", "pharmacist"}, ("pilot-education-assessment",)),
    ({"community", "communities", "employer", "designated", "offer", "recommendation", "edo"}, ("pilot-job-offer", "permanent-job-offer")),
    ({"portal", "apply", "imm", "0246", "0247", "0248", "0008", "5669", "5406", "5562", "police", "fee", "fees"}, ("pilot-permanent-residence-apply", "pilot-permanent-residence")),
    ({"permit", "spouse", "open", "employer-specific", "2-year"}, ("pilot-work-permit", "permanent-work-permit")),
    ({"biometrics", "medical", "aor", "ecopr", "card", "settle", "cbsa", "180"}, ("pilot-after-apply", "pilot-settle")),
)


def _tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


def _split_chunks(text: str, max_chars: int = 700) -> List[str]:
    paragraphs = [p.strip() for p in re.split(r"\n{1,}", text or "") if p.strip()]
    if not paragraphs:
        return []

    chunks: List[str] = []
    current = ""
    for para in paragraphs:
        if len(para) > max_chars:
            # Break long paragraph on sentence boundaries
            sentences = re.split(r"(?<=[.!?])\s+", para)
            for sent in sentences:
                if len(current) + len(sent) + 1 <= max_chars:
                    current = f"{current} {sent}".strip()
                else:
                    if current:
                        chunks.append(current)
                    current = sent
        elif len(current) + len(para) + 1 <= max_chars:
            current = f"{current} {para}".strip()
        else:
            if current:
                chunks.append(current)
            current = para
    if current:
        chunks.append(current)
    return chunks


class CanadaRAGService:
    """In-memory TF-IDF + phrase + domain-aware search over indexed Canada.ca RCIP pages."""

    def __init__(self) -> None:
        self.pages: List[Dict[str, Any]] = []
        self.chunks: List[Dict[str, Any]] = []
        self.idf: Dict[str, float] = {}

    def index_pages(self, pages: List[Dict[str, Any]]) -> None:
        """Index Canada.ca pages and community reference cards into searchable chunks."""
        self.pages = list(pages or [])
        chunks: List[Dict[str, Any]] = []

        for page in self.pages:
            body = "\n".join(
                part
                for part in (page.get("alert_text", ""), page.get("content_text", ""))
                if part
            )
            page_chunks = _split_chunks(body, max_chars=750) or [page.get("title", "")]
            for idx, chunk_text in enumerate(page_chunks):
                tokens = _tokenize(f"{page.get('title', '')} {chunk_text}")
                chunks.append(
                    {
                        "chunk_id": f"{page.get('slug', 'page')}_{idx}",
                        "slug": page.get("slug", ""),
                        "track": page.get("track", "pilot"),
                        "title": page.get("title", "Canada.ca RCIP"),
                        "url": page.get("url", ""),
                        "site_last_modified": page.get("site_last_modified", ""),
                        "text": chunk_text,
                        "tokens": tokens,
                    }
                )

        # Add compact reference chunks for the 14 participating communities
        for comm in PARTICIPATING_COMMUNITIES:
            text = (
                f"{comm['name']}, {comm['province']} ({comm['province_code']}) is one of the 14 participating RCIP communities. "
                f"Economic development organization: {comm['edo_name']}. Official website: {comm['official_url']}. "
                f"Typical sectors: {', '.join(comm['key_sectors'])}. Local public institutions: {', '.join(comm['local_institutions'])}."
            )
            chunks.append(
                {
                    "chunk_id": f"community_{comm['id']}",
                    "slug": "pilot-job-offer",
                    "track": "community",
                    "title": f"{comm['name']}, {comm['province_code']} — Official EDO Portal",
                    "url": comm["official_url"],
                    "site_last_modified": "2026-11-09",
                    "text": text,
                    "tokens": _tokenize(text),
                }
            )

        self.chunks = chunks
        self._compute_idf()

    def _compute_idf(self) -> None:
        total_docs = max(1, len(self.chunks))
        df: Dict[str, int] = {}
        for chunk in self.chunks:
            for tok in set(chunk["tokens"]):
                df[tok] = df.get(tok, 0) + 1
        self.idf = {
            tok: math.log((total_docs + 1) / (freq + 1)) + 1.0
            for tok, freq in df.items()
        }

    def search(self, query: str, limit: int = 4) -> List[Dict[str, Any]]:
        """Retrieve top grounded chunks ordered by relevance, deduplicating by source URL."""
        if not self.chunks:
            return []

        q_lower = (query or "").lower()
        q_tokens = _tokenize(query)
        if not q_tokens:
            return self.chunks[:limit]

        boosted_slugs = set()
        q_set = set(q_tokens)
        for trigger_words, slugs in _DOMAIN_BOOST_GROUPS:
            if q_set & trigger_words:
                boosted_slugs.update(slugs)

        scored: List[Tuple[float, Dict[str, Any]]] = []
        for chunk in self.chunks:
            c_tokens = chunk["tokens"]
            if not c_tokens:
                continue
            tf_counts: Dict[str, int] = {}
            for tok in c_tokens:
                tf_counts[tok] = tf_counts.get(tok, 0) + 1

            score = 0.0
            for q_tok in q_set:
                if q_tok in tf_counts:
                    tf = 1.0 + math.log(tf_counts[q_tok])
                    score += tf * self.idf.get(q_tok, 1.0)

            # Exact multi-word phrase bonus
            if len(q_lower) >= 5 and q_lower in chunk["text"].lower():
                score += 4.0

            # Domain slug boost
            if chunk["slug"] in boosted_slugs:
                score += 2.2

            # Slight preference for pilot detail pages which contain full tables
            if chunk["track"] == "pilot":
                score += 0.25

            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda pair: pair[0], reverse=True)

        results: List[Dict[str, Any]] = []
        seen_urls = set()
        for _, chunk in scored:
            if chunk["url"] in seen_urls:
                continue
            seen_urls.add(chunk["url"])
            results.append(chunk)
            if len(results) >= limit:
                break

        return results or self.chunks[:limit]

    def _personalized_context_notes(self, query: str, profile: Optional[Dict[str, Any]]) -> List[str]:
        if not profile:
            return []
        q = (query or "").lower()
        notes: List[str] = []

        if any(w in q for w in ("fund", "money", "cad", "bank", "lico", "settlement")):
            if profile.get("in_canada_valid_work_permit"):
                notes.append("Based on your profile (`working in Canada with a valid work permit`), you are **exempt** from showing proof of settlement funds.")
            elif profile.get("family_size"):
                fsize = max(1, int(profile["family_size"]))
                req = required_settlement_funds(fsize)
                notes.append(f"Based on your saved family size ({fsize}), your required settlement funds minimum is **CAD ${req:,}**.")

        if any(w in q for w in ("clb", "language", "ielts", "celpip", "pte", "tef", "tcf")):
            teer = profile.get("target_job_teer")
            if teer is not None and str(teer).isdigit() and int(teer) in TEER_MIN_CLB:
                req_clb = TEER_MIN_CLB[int(teer)]
                notes.append(f"For your saved target job offer (**TEER {teer}**), the minimum requirement is **CLB/NCLC {req_clb}** in all four abilities.")

        if any(w in q for w in ("2027", "pilot", "permanent", "transition", "expire", "deadline")):
            track = determine_program_track(profile)
            notes.append(f"Your current active track: **{track['label']}** — {track['summary']}")

        return notes

    def answer_query(self, query: str, profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Synthesize a grounded answer from official Canada.ca pages with clickable citations."""
        matches = self.search(query, limit=4)
        if not matches:
            return {
                "answer": (
                    "No indexed Canada.ca pages are loaded yet. Click **Sync Canada.ca** to fetch the official RCIP pages, "
                    "then ask about eligibility, settlement funds, CLB/language tests, local graduate exemptions, or the Jan 1, 2027 transition."
                ),
                "citations": [],
                "disclaimer": "Informational guidance grounded in Canada.ca public pages; not legal advice.",
            }

        lines: List[str] = []
        personal_notes = self._personalized_context_notes(query, profile)
        if personal_notes:
            lines.append("**Tailored to Your Saved Profile:**")
            for note in personal_notes:
                lines.append(f"- {note}")
            lines.append("")

        lines.append("**Grounded Official Canada.ca Guidance:**")
        citations: List[Dict[str, str]] = []
        for idx, chunk in enumerate(matches, 1):
            excerpt = chunk["text"][:420].strip()
            if len(chunk["text"]) > 420:
                excerpt += "..."
            lines.append(f"**{idx}. {chunk['title']}**\n{excerpt}\n")
            citations.append(
                {
                    "title": chunk["title"],
                    "url": chunk["url"],
                    "track": chunk["track"],
                    "site_last_modified": chunk.get("site_last_modified", ""),
                    "excerpt": excerpt,
                }
            )

        lines.append(
            "_Note: Official guidance is summarized from Canada.ca public pages and does not constitute legal immigration advice._"
        )

        return {
            "answer": "\n".join(lines),
            "citations": citations,
            "disclaimer": "Informational guidance grounded in official Canada.ca pages; verify forms and dates on Canada.ca before submission.",
        }
