"""
SQLite database layer — Multi-Profile Edition.
Handles profiles, businesses, scraped jobs, lead management.
"""
import sqlite3
import os
import json
import pandas as pd
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "scraper_data.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create / migrate all tables. Safe to call multiple times."""
    conn = get_connection()
    cur = conn.cursor()

    # ── Profiles table ────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            slug        TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            icon        TEXT DEFAULT '📁',
            niches      TEXT DEFAULT '[]',   -- JSON list of niche strings
            api_key     TEXT NOT NULL UNIQUE,
            created_at  TEXT NOT NULL
        )
    """)

    # ── Scraped jobs ──────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scraped_jobs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id   INTEGER NOT NULL DEFAULT 1,
            state        TEXT NOT NULL,
            pincode      TEXT NOT NULL,
            niche        TEXT NOT NULL,
            scraped_at   TEXT NOT NULL,
            results_count INTEGER DEFAULT 0,
            UNIQUE(profile_id, pincode, niche)
        )
    """)

    # ── Businesses ────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS businesses (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id       INTEGER NOT NULL DEFAULT 1,
            state            TEXT NOT NULL,
            pincode          TEXT NOT NULL,
            niche            TEXT NOT NULL,
            name             TEXT,
            rating           TEXT,
            reviews          TEXT,
            phone            TEXT,
            website_available TEXT,
            website_link     TEXT,
            maps_url         TEXT,
            lead_status      TEXT DEFAULT '🆕 New Lead',
            notes            TEXT DEFAULT '',
            scraped_at       TEXT NOT NULL,
            updated_at       TEXT,
            UNIQUE(profile_id, maps_url)
        )
    """)

    # ── Migrations: safely add columns to old schemas ─────────────────────────
    def _add_col(table, col, col_def):
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
        except Exception:
            pass  # column already exists

    _add_col("businesses",   "profile_id",  "INTEGER NOT NULL DEFAULT 1")
    _add_col("businesses",   "lead_status", "TEXT DEFAULT '🆕 New Lead'")
    _add_col("businesses",   "notes",       "TEXT DEFAULT ''")
    _add_col("businesses",   "updated_at",  "TEXT")
    _add_col("scraped_jobs", "profile_id",  "INTEGER NOT NULL DEFAULT 1")

    conn.commit()
    conn.close()


# ── Profile CRUD ──────────────────────────────────────────────────────────────

def create_profile(name: str, slug: str, description: str, icon: str,
                   niches: list, api_key: str) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO profiles (name, slug, description, icon, niches, api_key, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, slug, description, icon, json.dumps(niches), api_key, datetime.now().isoformat()))
    pid = cur.lastrowid
    conn.commit()
    conn.close()
    return pid


def get_all_profiles() -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM profiles ORDER BY created_at")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    for r in rows:
        r["niches"] = json.loads(r.get("niches") or "[]")
    return rows


def get_profile_by_slug(slug: str) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM profiles WHERE slug=?", (slug,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    r = dict(row)
    r["niches"] = json.loads(r.get("niches") or "[]")
    return r


def get_profile_by_api_key(api_key: str) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM profiles WHERE api_key=?", (api_key,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    r = dict(row)
    r["niches"] = json.loads(r.get("niches") or "[]")
    return r


def update_profile(slug: str, name: str = None, description: str = None,
                   icon: str = None, niches: list = None):
    conn = get_connection()
    cur = conn.cursor()
    if name is not None:
        cur.execute("UPDATE profiles SET name=? WHERE slug=?", (name, slug))
    if description is not None:
        cur.execute("UPDATE profiles SET description=? WHERE slug=?", (description, slug))
    if icon is not None:
        cur.execute("UPDATE profiles SET icon=? WHERE slug=?", (icon, slug))
    if niches is not None:
        cur.execute("UPDATE profiles SET niches=? WHERE slug=?", (json.dumps(niches), slug))
    conn.commit()
    conn.close()


def delete_profile(slug: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM profiles WHERE slug=?", (slug,))
    row = cur.fetchone()
    if row:
        pid = row["id"]
        cur.execute("DELETE FROM businesses WHERE profile_id=?", (pid,))
        cur.execute("DELETE FROM scraped_jobs WHERE profile_id=?", (pid,))
        cur.execute("DELETE FROM profiles WHERE id=?", (pid,))
    conn.commit()
    conn.close()


def slug_exists(slug: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM profiles WHERE slug=?", (slug,))
    row = cur.fetchone()
    conn.close()
    return row is not None


# ── Job Tracking ──────────────────────────────────────────────────────────────

def is_already_scraped(pincode: str, niche: str, profile_id: int = 1) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM scraped_jobs WHERE profile_id=? AND pincode=? AND niche=?",
        (profile_id, pincode, niche)
    )
    row = cur.fetchone()
    conn.close()
    return row is not None


def mark_as_scraped(state: str, pincode: str, niche: str,
                    results_count: int, profile_id: int = 1):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO scraped_jobs
            (profile_id, state, pincode, niche, scraped_at, results_count)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (profile_id, state, pincode, niche, datetime.now().isoformat(), results_count))
    conn.commit()
    conn.close()


# ── Business Data ─────────────────────────────────────────────────────────────

def save_businesses(state: str, pincode: str, niche: str,
                    df: pd.DataFrame, profile_id: int = 1) -> int:
    if df.empty:
        return 0
    conn = get_connection()
    cur = conn.cursor()
    inserted = 0
    now = datetime.now().isoformat()
    for _, row in df.iterrows():
        maps_url = row.get("Google Maps URL", "")
        if not maps_url:
            continue
        try:
            cur.execute("""
                INSERT OR IGNORE INTO businesses
                    (profile_id, state, pincode, niche, name, rating, reviews,
                     phone, website_available, website_link, maps_url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile_id, state, pincode, niche,
                row.get("Name", ""), row.get("Rating", ""), row.get("Reviews", ""),
                row.get("Phone", ""), row.get("Website Available?", ""),
                row.get("Website Link", ""), maps_url, now
            ))
            if cur.rowcount > 0:
                inserted += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return inserted


def update_lead_status(business_id: int, status: str, notes: str = None):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    if notes is not None:
        cur.execute(
            "UPDATE businesses SET lead_status=?, notes=?, updated_at=? WHERE id=?",
            (status, notes, now, business_id)
        )
    else:
        cur.execute(
            "UPDATE businesses SET lead_status=?, updated_at=? WHERE id=?",
            (status, now, business_id)
        )
    conn.commit()
    conn.close()


def get_business_by_id(business_id: int) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM businesses WHERE id=?", (business_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


# ── Flexible Query ────────────────────────────────────────────────────────────

def get_businesses(
    profile_id: int = None,
    state: str = None,
    pincode: str = None,
    niche: str = None,
    has_phone: bool = None,
    has_website: bool = None,
    lead_status: str = None,
    page: int = 1,
    limit: int = 100
) -> pd.DataFrame:
    conn = get_connection()
    query = "SELECT * FROM businesses WHERE 1=1"
    params = []
    if profile_id is not None:
        query += " AND profile_id=?"
        params.append(profile_id)
    if state:
        query += " AND LOWER(state)=LOWER(?)"
        params.append(state)
    if pincode:
        query += " AND pincode=?"
        params.append(pincode)
    if niche:
        query += " AND LOWER(niche) LIKE LOWER(?)"
        params.append(f"%{niche}%")
    if has_phone is True:
        query += " AND phone NOT IN ('N/A', '')"
    elif has_phone is False:
        query += " AND (phone='N/A' OR phone='')"
    if has_website is True:
        query += " AND website_available='Yes'"
    elif has_website is False:
        query += " AND website_available!='Yes'"
    if lead_status:
        query += " AND lead_status=?"
        params.append(lead_status)
    query += " ORDER BY state, pincode, niche, name"
    offset = (page - 1) * limit
    query += f" LIMIT {limit} OFFSET {offset}"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_all_businesses_df(profile_id: int = None) -> pd.DataFrame:
    conn = get_connection()
    if profile_id:
        df = pd.read_sql_query(
            "SELECT * FROM businesses WHERE profile_id=? ORDER BY state,pincode,niche,name",
            conn, params=(profile_id,)
        )
    else:
        df = pd.read_sql_query(
            "SELECT * FROM businesses ORDER BY state,pincode,niche,name", conn
        )
    conn.close()
    return df


def get_stats(profile_id: int = None) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    pid_filter = "WHERE profile_id=?" if profile_id else ""
    pid_args = (profile_id,) if profile_id else ()

    def q(sql, args=()):
        cur.execute(sql, args)
        return cur.fetchone()[0]

    total_businesses   = q(f"SELECT COUNT(*) FROM businesses {pid_filter}", pid_args)
    total_jobs         = q(f"SELECT COUNT(*) FROM scraped_jobs {pid_filter}", pid_args)
    total_pincodes     = q(f"SELECT COUNT(DISTINCT pincode) FROM scraped_jobs {pid_filter}", pid_args)
    total_states       = q(f"SELECT COUNT(DISTINCT state) FROM scraped_jobs {pid_filter}", pid_args)
    with_phone_filter  = (f"WHERE profile_id=? AND phone NOT IN ('N/A','')" if profile_id
                          else "WHERE phone NOT IN ('N/A','')")
    with_phone         = q(f"SELECT COUNT(*) FROM businesses {with_phone_filter}", pid_args)
    with_web_filter    = (f"WHERE profile_id=? AND website_available='Yes'" if profile_id
                          else "WHERE website_available='Yes'")
    with_website       = q(f"SELECT COUNT(*) FROM businesses {with_web_filter}", pid_args)

    status_sql = (
        f"SELECT lead_status, COUNT(*) as cnt FROM businesses {pid_filter} GROUP BY lead_status"
    )
    cur.execute(status_sql, pid_args)
    lead_breakdown = {row["lead_status"]: row["cnt"] for row in cur.fetchall()}

    conn.close()
    return {
        "total_businesses": total_businesses,
        "total_jobs_done": total_jobs,
        "total_pincodes_done": total_pincodes,
        "total_states_scraped": total_states,
        "businesses_with_phone": with_phone,
        "businesses_with_website": with_website,
        "lead_status_breakdown": lead_breakdown,
    }


def get_scraped_jobs_df(profile_id: int = None) -> pd.DataFrame:
    conn = get_connection()
    if profile_id:
        df = pd.read_sql_query(
            "SELECT * FROM scraped_jobs WHERE profile_id=? ORDER BY scraped_at DESC",
            conn, params=(profile_id,)
        )
    else:
        df = pd.read_sql_query("SELECT * FROM scraped_jobs ORDER BY scraped_at DESC", conn)
    conn.close()
    return df


def get_distinct_states(profile_id: int = None) -> list:
    conn = get_connection()
    cur = conn.cursor()
    if profile_id:
        cur.execute("SELECT DISTINCT state FROM businesses WHERE profile_id=? ORDER BY state", (profile_id,))
    else:
        cur.execute("SELECT DISTINCT state FROM businesses ORDER BY state")
    rows = cur.fetchall()
    conn.close()
    return [r["state"] for r in rows]


def get_distinct_niches(profile_id: int = None) -> list:
    conn = get_connection()
    cur = conn.cursor()
    if profile_id:
        cur.execute("SELECT DISTINCT niche FROM businesses WHERE profile_id=? ORDER BY niche", (profile_id,))
    else:
        cur.execute("SELECT DISTINCT niche FROM businesses ORDER BY niche")
    rows = cur.fetchall()
    conn.close()
    return [r["niche"] for r in rows]
