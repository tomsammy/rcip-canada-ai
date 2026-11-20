"""SQLite WAL store for RCIP profiles, roadmap progress, Canada.ca pages, and community shortlists."""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.config import DB_PATH

_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY,
    data_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS roadmap_progress (
    item_id TEXT PRIMARY KEY,
    stage_id TEXT NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT '',
    target_date TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS canada_pages (
    url TEXT PRIMARY KEY,
    track TEXT NOT NULL,
    slug TEXT NOT NULL,
    title TEXT NOT NULL,
    site_last_modified TEXT NOT NULL DEFAULT '',
    alert_text TEXT NOT NULL DEFAULT '',
    content_text TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS community_shortlist (
    community_id TEXT PRIMARY KEY,
    shortlisted INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT '',
    employers_contacted INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Open a thread-local SQLite connection in WAL mode and ensure schema exists."""
    target = str(db_path or DB_PATH)
    parent = os.path.dirname(os.path.abspath(target))
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(target, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


@contextmanager
def store_session(db_path: Optional[str] = None):
    """Yield a fresh SQLite connection and close it cleanly on exit."""
    conn = connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


def get_profile(conn: sqlite3.Connection, profile_id: str = "default") -> Dict[str, Any]:
    """Retrieve stored candidate profile JSON, or an empty dict if none saved yet."""
    row = conn.execute(
        "SELECT data_json, updated_at FROM profiles WHERE id = ?",
        (profile_id,),
    ).fetchone()
    if not row:
        return {}
    try:
        data = json.loads(row["data_json"])
        if isinstance(data, dict):
            data["_updated_at"] = row["updated_at"]
            return data
    except ValueError:
        pass
    return {}


def save_profile(
    conn: sqlite3.Connection,
    profile_data: Dict[str, Any],
    profile_id: str = "default",
) -> Dict[str, Any]:
    """Persist candidate profile JSON and return saved copy."""
    clean = {k: v for k, v in profile_data.items() if k != "_updated_at"}
    now = _utc_now()
    conn.execute(
        """
        INSERT INTO profiles (id, data_json, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            data_json = excluded.data_json,
            updated_at = excluded.updated_at
        """,
        (profile_id, json.dumps(clean, ensure_ascii=False), now),
    )
    conn.commit()
    result = dict(clean)
    result["_updated_at"] = now
    return result


def list_progress(conn: sqlite3.Connection) -> Dict[str, Dict[str, Any]]:
    """Return all roadmap checklist progress rows keyed by item_id."""
    rows = conn.execute(
        "SELECT item_id, stage_id, completed, notes, target_date, updated_at FROM roadmap_progress"
    ).fetchall()
    return {
        row["item_id"]: {
            "item_id": row["item_id"],
            "stage_id": row["stage_id"],
            "completed": bool(row["completed"]),
            "notes": row["notes"],
            "target_date": row["target_date"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    }


def upsert_progress(
    conn: sqlite3.Connection,
    item_id: str,
    stage_id: str,
    completed: bool,
    notes: str = "",
    target_date: str = "",
) -> Dict[str, Any]:
    """Insert or update a roadmap checklist item's progress."""
    now = _utc_now()
    conn.execute(
        """
        INSERT INTO roadmap_progress (item_id, stage_id, completed, notes, target_date, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(item_id) DO UPDATE SET
            stage_id = excluded.stage_id,
            completed = excluded.completed,
            notes = excluded.notes,
            target_date = excluded.target_date,
            updated_at = excluded.updated_at
        """,
        (item_id, stage_id, 1 if completed else 0, notes or "", target_date or "", now),
    )
    conn.commit()
    return {
        "item_id": item_id,
        "stage_id": stage_id,
        "completed": bool(completed),
        "notes": notes or "",
        "target_date": target_date or "",
        "updated_at": now,
    }


def upsert_canada_page(conn: sqlite3.Connection, page: Dict[str, Any]) -> str:
    """Upsert a crawled/seeded Canada.ca page and return 'inserted', 'updated', or 'unchanged'."""
    url = page["url"]
    existing = conn.execute(
        "SELECT content_hash FROM canada_pages WHERE url = ?",
        (url,),
    ).fetchone()
    now = page.get("fetched_at") or _utc_now()
    if existing is None:
        conn.execute(
            """
            INSERT INTO canada_pages (
                url, track, slug, title, site_last_modified,
                alert_text, content_text, content_hash, fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                url,
                page.get("track", "pilot"),
                page.get("slug", ""),
                page.get("title", ""),
                page.get("site_last_modified", ""),
                page.get("alert_text", ""),
                page.get("content_text", ""),
                page.get("content_hash", ""),
                now,
            ),
        )
        conn.commit()
        return "inserted"

    if existing["content_hash"] == page.get("content_hash", ""):
        conn.execute(
            "UPDATE canada_pages SET fetched_at = ? WHERE url = ?",
            (now, url),
        )
        conn.commit()
        return "unchanged"

    conn.execute(
        """
        UPDATE canada_pages
        SET track = ?, slug = ?, title = ?, site_last_modified = ?,
            alert_text = ?, content_text = ?, content_hash = ?, fetched_at = ?
        WHERE url = ?
        """,
        (
            page.get("track", "pilot"),
            page.get("slug", ""),
            page.get("title", ""),
            page.get("site_last_modified", ""),
            page.get("alert_text", ""),
            page.get("content_text", ""),
            page.get("content_hash", ""),
            now,
            url,
        ),
    )
    conn.commit()
    return "updated"


def list_canada_pages(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Return all cached/crawled Canada.ca pages ordered by track and slug."""
    rows = conn.execute(
        """
        SELECT url, track, slug, title, site_last_modified, alert_text,
               content_text, content_hash, fetched_at
        FROM canada_pages
        ORDER BY track ASC, slug ASC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def list_shortlists(conn: sqlite3.Connection) -> Dict[str, Dict[str, Any]]:
    """Return community shortlist records keyed by community_id."""
    rows = conn.execute(
        "SELECT community_id, shortlisted, notes, employers_contacted, updated_at FROM community_shortlist"
    ).fetchall()
    return {
        row["community_id"]: {
            "community_id": row["community_id"],
            "shortlisted": bool(row["shortlisted"]),
            "notes": row["notes"],
            "employers_contacted": int(row["employers_contacted"]),
            "updated_at": row["updated_at"],
        }
        for row in rows
    }


def upsert_shortlist(
    conn: sqlite3.Connection,
    community_id: str,
    shortlisted: bool,
    notes: str = "",
    employers_contacted: int = 0,
) -> Dict[str, Any]:
    """Insert or update a community shortlist record."""
    now = _utc_now()
    count = max(0, int(employers_contacted))
    conn.execute(
        """
        INSERT INTO community_shortlist (community_id, shortlisted, notes, employers_contacted, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(community_id) DO UPDATE SET
            shortlisted = excluded.shortlisted,
            notes = excluded.notes,
            employers_contacted = excluded.employers_contacted,
            updated_at = excluded.updated_at
        """,
        (community_id, 1 if shortlisted else 0, notes or "", count, now),
    )
    conn.commit()
    return {
        "community_id": community_id,
        "shortlisted": bool(shortlisted),
        "notes": notes or "",
        "employers_contacted": count,
        "updated_at": now,
    }
