"""Deep module encapsulating official-portal Live Snapshot sync, persistence, RAG indexing, and read-models."""

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.canada_crawler import (
    HttpFetcher,
    crawl_official_canada_pages,
    crawl_official_global_sources,
)
from backend.countries_data import COUNTRIES_CATALOG
from backend.rcip_data import ECA_ORGANIZATIONS, LANGUAGE_TEST_CHARTS
from backend.store import (
    list_canada_pages as store_list_canada_pages,
    list_global_official_pages as store_list_global_official_pages,
    store_session,
    upsert_canada_page as store_upsert_canada_page,
    upsert_global_official_page as store_upsert_global_official_page,
)


def _is_live_canada_snapshot(page: Dict[str, Any]) -> bool:
    fetched_at = str(page.get("fetched_at") or "")
    return bool(fetched_at and not fetched_at.startswith("2026-11-09T00:00:00"))


def sync_canada_sources(
    db_path: str,
    rag_engine: Any,
    fetcher: Optional[HttpFetcher] = None,
) -> Dict[str, Any]:
    """Fetch official Canada.ca RCIP pages, persist changes in SQLite, and refresh the RAG index."""
    crawl_result = crawl_official_canada_pages(fetcher=fetcher)
    counts = {"inserted": 0, "updated": 0, "unchanged": 0}

    with store_session(db_path) as conn:
        for page in crawl_result["pages"]:
            outcome = store_upsert_canada_page(conn, page)
            counts[outcome] = counts.get(outcome, 0) + 1
        all_pages = store_list_canada_pages(conn)
        global_pages = store_list_global_official_pages(conn)

    rag_engine.index_pages(all_pages, global_live_pages=global_pages)
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


def sync_official_sources(
    scope: str,
    db_path: str,
    rag_engine: Any,
    fetcher: Optional[HttpFetcher] = None,
) -> Dict[str, Any]:
    """Concurrently sync verbatim Live Snapshots across all 12 or 1 Destination Hub(s) within bounded latency."""
    normalized_scope = (scope or "all").strip().lower()
    is_all = normalized_scope in ("", "all")
    crawl_canada_too = normalized_scope in ("", "all", "canada")

    if crawl_canada_too:
        pool = ThreadPoolExecutor(max_workers=2)
        try:
            f_global = pool.submit(
                crawl_official_global_sources,
                None if is_all else "canada",
                4 if is_all else 5,
                16 if is_all else 6,
                1 if is_all else 3,
                9.0,
                fetcher,
            )
            f_ca = pool.submit(crawl_official_canada_pages, 4, 10, fetcher)
            crawl_global = f_global.result()
            ca_crawl = f_ca.result()
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
    else:
        crawl_global = crawl_official_global_sources(
            country_id=normalized_scope,
            timeout=5,
            max_workers=6,
            max_pathways_per_country=3,
            overall_timeout=9.0,
            fetcher=fetcher,
        )
        ca_crawl = {"pages": [], "errors": []}

    ca_errors: List[Dict[str, str]] = ca_crawl.get("errors", [])
    counts = {"inserted": 0, "updated": 0, "unchanged": 0}

    with store_session(db_path) as conn:
        for page in crawl_global["pages"]:
            outcome = store_upsert_global_official_page(conn, page)
            counts[outcome] = counts.get(outcome, 0) + 1

        for ca_page in ca_crawl.get("pages", []):
            outcome = store_upsert_canada_page(conn, ca_page)
            counts[outcome] = counts.get(outcome, 0) + 1

        all_canada = store_list_canada_pages(conn)
        all_global = store_list_global_official_pages(conn)

    rag_engine.index_pages(all_canada, global_live_pages=all_global)
    return {
        "status": "success",
        "scope": normalized_scope or "all",
        "synced_at": crawl_global["synced_at"],
        "countries_indexed": len(COUNTRIES_CATALOG),
        "live_fetched": crawl_global["total_fetched"],
        "inserted": counts["inserted"],
        "updated": counts["updated"],
        "unchanged": counts["unchanged"],
        "failed": len(crawl_global["errors"]) + len(ca_errors),
        "errors": (crawl_global["errors"] + ca_errors)[:10],
        "total_indexed": len(all_canada) + len(all_global),
        "live_global_pages": len(all_global),
    }


def build_sources_index(
    db_path: str,
    ensure_seeded_fn: Callable[[str], List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Assemble the unified Source Registry combining Live Snapshots and verified baselines across all 12 countries."""
    with store_session(db_path) as conn:
        pages = store_list_canada_pages(conn)
        global_live = store_list_global_official_pages(conn)
    if not pages:
        pages = ensure_seeded_fn(db_path)

    live_urls = {p["url"] for p in global_live}
    summary_pages: List[Dict[str, Any]] = []

    for gp in global_live:
        summary_pages.append(
            {
                "url": gp["url"],
                "country_id": gp["country_id"],
                "track": gp["country_name"],
                "slug": gp["country_id"],
                "title": gp["title"],
                "site_last_modified": gp["site_last_modified"],
                "alert_text": gp["alert_text"],
                "fetched_at": gp["fetched_at"],
                "source_mode": gp.get("source_mode", "live"),
            }
        )

    for p in pages:
        is_live_ca = _is_live_canada_snapshot(p)
        summary_pages.append(
            {
                "url": p["url"],
                "country_id": "canada",
                "track": p["track"],
                "slug": p["slug"],
                "title": p["title"],
                "site_last_modified": p["site_last_modified"],
                "alert_text": p["alert_text"],
                "fetched_at": p["fetched_at"],
                "source_mode": "live" if is_live_ca else "verified_registry",
            }
        )

    for c in COUNTRIES_CATALOG:
        if c["official_portal"] not in live_urls:
            summary_pages.append(
                {
                    "url": c["official_portal"],
                    "country_id": c["id"],
                    "track": c["name"],
                    "slug": c["id"],
                    "title": f"{c['name']} — {c['authority']}",
                    "site_last_modified": "",
                    "alert_text": "",
                    "fetched_at": "",
                    "source_mode": "verified_registry",
                }
            )

    live_timestamps = [
        p["fetched_at"]
        for p in summary_pages
        if p.get("source_mode") == "live" and p.get("fetched_at")
    ]
    return {
        "status": "success",
        "count": len(summary_pages),
        "live_count": len(live_timestamps),
        "last_synced_at": max(live_timestamps, default=""),
        "sources": summary_pages,
        "language_charts": LANGUAGE_TEST_CHARTS,
        "eca_organizations": ECA_ORGANIZATIONS,
    }


def build_country_live_snapshots(
    country_id: str,
    db_path: str,
    rag_engine: Any,
) -> Tuple[List[Dict[str, Any]], str]:
    """Return formatted Live Snapshots and latest verification timestamp for one Destination Hub."""
    with store_session(db_path) as conn:
        live_rows = store_list_global_official_pages(conn, country_id=country_id)

    if not live_rows and getattr(rag_engine, "global_live_pages", None):
        live_rows = [p for p in rag_engine.global_live_pages if p.get("country_id") == country_id]

    live_snapshots = [
        {
            "url": lp["url"],
            "title": lp["title"],
            "site_last_modified": lp.get("site_last_modified", ""),
            "fetched_at": lp.get("fetched_at", ""),
            "alert_text": lp.get("alert_text", ""),
            "excerpt": (
                lp.get("content_text", "")[:450].strip()
                + ("..." if len(lp.get("content_text", "")) > 450 else "")
            ),
        }
        for lp in live_rows
    ]
    timestamps = [s["fetched_at"] for s in live_snapshots if s.get("fetched_at")]
    return live_snapshots, max(timestamps, default="")
