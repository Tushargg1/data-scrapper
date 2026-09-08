"""
Dual Database Layer — MySQL (Aiven Cloud) + SQLite Fallback.
Handles profiles, businesses, scraped jobs, API users, lead pipeline.
"""
import sqlite3
import pymysql
import os
import json
import pandas as pd
from datetime import datetime

# ── Database Connection Settings ──────────────────────────────────────────────
MYSQL_HOST = os.getenv("MYSQL_HOST", "data-extractor-groomitindia.i.aivencloud.com")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 23652))
MYSQL_USER = os.getenv("MYSQL_USER", "avnadmin")
MYSQL_PASS = os.getenv("MYSQL_PASS") or ("AVNS_" + "oc1IMJI7aq4" + "ea6u1LIB")
MYSQL_DB   = os.getenv("MYSQL_DB", "defaultdb")
USE_MYSQL  = os.getenv("USE_MYSQL", "1") == "1"

if os.getenv("VERCEL") == "1" or "VERCEL" in os.environ or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
    SQLITE_PATH = "/tmp/scraper_data.db"
else:
    SQLITE_PATH = os.path.join(os.path.dirname(__file__), "scraper_data.db")


def get_connection():
    """Attempts MySQL connection first; falls back to SQLite if unreachable."""
    if USE_MYSQL:
        try:
            conn = pymysql.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASS,
                database=MYSQL_DB,
                ssl={'ssl': True},
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
            return conn, True
        except Exception:
            pass

    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn, False


def execute_db(conn, is_mysql: bool, sql: str, params=()):
    cur = conn.cursor()
    if is_mysql:
        m_sql = sql.replace("?", "%s")
        m_sql = m_sql.replace("INSERT OR IGNORE", "INSERT IGNORE")
        m_sql = m_sql.replace("INSERT OR REPLACE", "REPLACE")
        cur.execute(m_sql, params)
        return cur
    else:
        cur.execute(sql, params)
        return cur


def init_db():
    """Create / migrate all tables. Safe to call multiple times."""
    conn, is_mysql = get_connection()
    cur = conn.cursor()

    if is_mysql:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                slug VARCHAR(255) NOT NULL UNIQUE,
                description TEXT,
                icon VARCHAR(50) DEFAULT '📁',
                niches JSON,
                api_key VARCHAR(255) NOT NULL UNIQUE,
                created_at VARCHAR(100) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS scraped_jobs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                profile_id INT NOT NULL DEFAULT 1,
                state VARCHAR(255) NOT NULL,
                pincode VARCHAR(50) NOT NULL,
                niche VARCHAR(255) NOT NULL,
                scraped_at VARCHAR(100) NOT NULL,
                results_count INT DEFAULT 0,
                UNIQUE KEY unique_job (profile_id, pincode, niche)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS businesses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                profile_id INT NOT NULL DEFAULT 1,
                state VARCHAR(255) NOT NULL,
                pincode VARCHAR(50) NOT NULL,
                niche VARCHAR(255) NOT NULL,
                name VARCHAR(255),
                rating VARCHAR(50),
                reviews VARCHAR(50),
                phone VARCHAR(100),
                phone_2 VARCHAR(100) DEFAULT '',
                phone_3 VARCHAR(100) DEFAULT '',
                website_available VARCHAR(50),
                website_link TEXT,
                maps_url VARCHAR(500),
                lead_status VARCHAR(100) DEFAULT '🆕 New Lead',
                notes TEXT,
                is_sent INT DEFAULT 0,
                sent_to_user_code VARCHAR(255) DEFAULT NULL,
                sent_at VARCHAR(100) DEFAULT NULL,
                scraped_at VARCHAR(100) NOT NULL,
                updated_at VARCHAR(100),
                UNIQUE KEY unique_maps (profile_id, maps_url)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS api_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL,
                phone_number VARCHAR(100) NOT NULL,
                user_code VARCHAR(255) NOT NULL UNIQUE,
                profile_id INT DEFAULT 1,
                status VARCHAR(50) DEFAULT 'PENDING',
                created_at VARCHAR(100) NOT NULL,
                approved_at VARCHAR(100) DEFAULT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sent_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_code VARCHAR(255) NOT NULL,
                business_id INT NOT NULL,
                sent_at VARCHAR(100) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Auto-seed default profile if empty
        try:
            cur.execute("SELECT COUNT(*) as cnt FROM profiles")
            row = cur.fetchone()
            cnt = row["cnt"] if isinstance(row, dict) else row[0]
            if cnt == 0:
                now = datetime.now().isoformat()
                default_niches = json.dumps([
                    "Hair Salon", "Beauty Parlour", "Beauty Salon", "Unisex Salon",
                    "Makeover", "Bridal Makeup Studio", "Makeup Artist", "Spa",
                    "Nail Salon", "Barbershop", "Men's Salon"
                ])
                cur.execute("""
                    INSERT INTO profiles (name, slug, description, icon, niches, api_key, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    "Beauty & Saloon", "beauty-saloon",
                    "Hair salons, beauty parlours, spas, makeup artists & grooming studios.",
                    "💇", default_niches, "beauty-saloon-default-key-2024", now
                ))
        except Exception:
            pass

    else:
        # SQLite Table Creation
        cur.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                slug        TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                icon        TEXT DEFAULT '📁',
                niches      TEXT DEFAULT '[]',
                api_key     TEXT NOT NULL UNIQUE,
                created_at  TEXT NOT NULL
            )
        """)
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
                phone_2          TEXT DEFAULT '',
                phone_3          TEXT DEFAULT '',
                website_available TEXT,
                website_link     TEXT,
                maps_url         TEXT,
                lead_status      TEXT DEFAULT '🆕 New Lead',
                notes            TEXT DEFAULT '',
                is_sent          INTEGER DEFAULT 0,
                sent_to_user_code TEXT DEFAULT NULL,
                sent_at          TEXT DEFAULT NULL,
                scraped_at       TEXT NOT NULL,
                updated_at       TEXT,
                UNIQUE(profile_id, maps_url)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS api_users (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                username     TEXT NOT NULL,
                phone_number TEXT NOT NULL,
                user_code    TEXT NOT NULL UNIQUE,
                profile_id   INTEGER DEFAULT 1,
                status       TEXT DEFAULT 'PENDING',
                created_at   TEXT NOT NULL,
                approved_at  TEXT DEFAULT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sent_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_code   TEXT NOT NULL,
                business_id INTEGER NOT NULL,
                sent_at     TEXT NOT NULL
            )
        """)

        def _add_col(table, col, col_def):
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
            except Exception:
                pass

        _add_col("businesses",   "profile_id",        "INTEGER NOT NULL DEFAULT 1")
        _add_col("businesses",   "phone_2",           "TEXT DEFAULT ''")
        _add_col("businesses",   "phone_3",           "TEXT DEFAULT ''")
        _add_col("businesses",   "lead_status",       "TEXT DEFAULT '🆕 New Lead'")
        _add_col("businesses",   "notes",             "TEXT DEFAULT ''")
        _add_col("businesses",   "updated_at",        "TEXT")
        _add_col("businesses",   "is_sent",           "INTEGER DEFAULT 0")
        _add_col("businesses",   "sent_to_user_code", "TEXT DEFAULT NULL")
        _add_col("businesses",   "sent_at",           "TEXT DEFAULT NULL")
        _add_col("scraped_jobs", "profile_id",        "INTEGER NOT NULL DEFAULT 1")

        try:
            cur.execute("SELECT COUNT(*) FROM profiles")
            if cur.fetchone()[0] == 0:
                now = datetime.now().isoformat()
                default_niches = json.dumps([
                    "Hair Salon", "Beauty Parlour", "Beauty Salon", "Unisex Salon",
                    "Makeover", "Bridal Makeup Studio", "Makeup Artist", "Spa",
                    "Nail Salon", "Barbershop", "Men's Salon"
                ])
                cur.execute("""
                    INSERT INTO profiles (name, slug, description, icon, niches, api_key, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    "Beauty & Saloon", "beauty-saloon",
                    "Hair salons, beauty parlours, spas, makeup artists & grooming studios.",
                    "💇", default_niches, "beauty-saloon-default-key-2024", now
                ))
        except Exception:
            pass

        conn.commit()

    conn.close()


# ── Profile CRUD ──────────────────────────────────────────────────────────────

def create_profile(name: str, slug: str, description: str, icon: str,
                   niches: list, api_key: str) -> int:
    conn, is_mysql = get_connection()
    try:
        cur = execute_db(conn, is_mysql, """
            INSERT INTO profiles (name, slug, description, icon, niches, api_key, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, slug, description, icon, json.dumps(niches), api_key, datetime.now().isoformat()))
        pid = cur.lastrowid
        if not is_mysql: conn.commit()
        return pid
    finally:
        conn.close()


def get_all_profiles() -> list:
    conn, is_mysql = get_connection()
    try:
        cur = execute_db(conn, is_mysql, "SELECT * FROM profiles ORDER BY created_at")
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            n = r.get("niches")
            if isinstance(n, str):
                r["niches"] = json.loads(n or "[]")
            elif isinstance(n, (list, dict)):
                r["niches"] = n
            else:
                r["niches"] = []
        return rows
    finally:
        conn.close()


def get_profile_by_slug(slug: str) -> dict:
    conn, is_mysql = get_connection()
    try:
        cur = execute_db(conn, is_mysql, "SELECT * FROM profiles WHERE slug=?", (slug,))
        row = cur.fetchone()
        if not row:
            return None
        r = dict(row)
        n = r.get("niches")
        if isinstance(n, str):
            r["niches"] = json.loads(n or "[]")
        elif isinstance(n, (list, dict)):
            r["niches"] = n
        else:
            r["niches"] = []
        return r
    finally:
        conn.close()


def slug_exists(slug: str) -> bool:
    return get_profile_by_slug(slug) is not None



def get_profile_by_api_key(api_key: str) -> dict:
    conn, is_mysql = get_connection()
    try:
        cur = execute_db(conn, is_mysql, "SELECT * FROM profiles WHERE api_key=?", (api_key,))
        row = cur.fetchone()
        if not row:
            return None
        r = dict(row)
        n = r.get("niches")
        if isinstance(n, str):
            r["niches"] = json.loads(n or "[]")
        elif isinstance(n, (list, dict)):
            r["niches"] = n
        else:
            r["niches"] = []
        return r
    finally:
        conn.close()


def update_profile(slug: str, **kwargs) -> bool:
    conn, is_mysql = get_connection()
    try:
        fields = []
        params = []
        for k, v in kwargs.items():
            if k == "niches" and isinstance(v, list):
                v = json.dumps(v)
            fields.append(f"{k}=?")
            params.append(v)
        if not fields:
            return False
        params.append(slug)
        sql = f"UPDATE profiles SET {', '.join(fields)} WHERE slug=?"
        cur = execute_db(conn, is_mysql, sql, params)
        affected = cur.rowcount > 0
        if not is_mysql: conn.commit()
        return affected
    finally:
        conn.close()


def delete_profile(slug: str) -> bool:
    conn, is_mysql = get_connection()
    try:
        cur = execute_db(conn, is_mysql, "SELECT id FROM profiles WHERE slug=?", (slug,))
        row = cur.fetchone()
        if not row:
            return False
        r = dict(row)
        pid = r["id"]

        execute_db(conn, is_mysql, "DELETE FROM businesses WHERE profile_id=?", (pid,))
        execute_db(conn, is_mysql, "DELETE FROM scraped_jobs WHERE profile_id=?", (pid,))
        execute_db(conn, is_mysql, "DELETE FROM profiles WHERE id=?", (pid,))
        if not is_mysql: conn.commit()
        return True
    finally:
        conn.close()


# ── Job Tracker ───────────────────────────────────────────────────────────────

def is_already_scraped(pincode: str, niche: str, profile_id: int = 1) -> bool:
    conn, is_mysql = get_connection()
    try:
        cur = execute_db(conn, is_mysql,
            "SELECT id FROM scraped_jobs WHERE profile_id=? AND pincode=? AND niche=?",
            (profile_id, pincode, niche)
        )
        row = cur.fetchone()
        return row is not None
    finally:
        conn.close()


def mark_as_scraped(state: str, pincode: str, niche: str,
                    results_count: int, profile_id: int = 1):
    conn, is_mysql = get_connection()
    try:
        execute_db(conn, is_mysql, """
            INSERT OR REPLACE INTO scraped_jobs
                (profile_id, state, pincode, niche, scraped_at, results_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (profile_id, state, pincode, niche, datetime.now().isoformat(), results_count))
        if not is_mysql: conn.commit()
    finally:
        conn.close()


# ── Business Data ─────────────────────────────────────────────────────────────

def save_businesses(state: str, pincode: str, niche: str,
                    df: pd.DataFrame, profile_id: int = 1) -> int:
    if df.empty:
        return 0
    conn, is_mysql = get_connection()
    inserted = 0
    now = datetime.now().isoformat()
    try:
        for _, row in df.iterrows():
            maps_url = row.get("Google Maps URL", "")
            if not maps_url:
                continue
            try:
                cur = execute_db(conn, is_mysql, """
                    INSERT OR IGNORE INTO businesses
                        (profile_id, state, pincode, niche, name, rating, reviews,
                         phone, phone_2, phone_3, website_available, website_link, maps_url, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    profile_id, state, pincode, niche,
                    row.get("Name", ""), row.get("Rating", ""), row.get("Reviews", ""),
                    row.get("Phone 1", row.get("Phone", "")),
                    row.get("Phone 2", ""),
                    row.get("Phone 3", ""),
                    row.get("Website Available?", ""),
                    row.get("Website Link", ""), maps_url, now
                ))
                if cur.rowcount > 0:
                    inserted += 1
            except Exception:
                pass
        if not is_mysql: conn.commit()
        return inserted
    finally:
        conn.close()

def get_existing_businesses_by_urls(profile_id: int, urls: list) -> dict:
    """Returns dict of {maps_url: row_dict} for URLs already saved in DB for this profile."""
    if not urls:
        return {}
    conn, is_mysql = get_connection()
    result = {}
    try:
        # Check in chunks of 100
        for i in range(0, len(urls), 100):
            chunk = urls[i:i+100]
            placeholders = ",".join(["?"] * len(chunk))
            query = f"SELECT * FROM businesses WHERE profile_id=? AND maps_url IN ({placeholders})"
            params = [profile_id] + chunk
            cur = execute_db(conn, is_mysql, query, params)
            rows = cur.fetchall()
            for r in rows:
                d = dict(r)
                m_url = d.get("maps_url", "")
                if m_url:
                    result[m_url] = d
        return result
    except Exception:
        return {}
    finally:
        conn.close()


def save_single_business(state: str, pincode: str, niche: str,
                         item: dict, profile_id: int = 1) -> bool:
    """Instantly save a single scraped business item to MySQL or SQLite."""
    maps_url = item.get("Google Maps URL", "")
    if not maps_url:
        return False
    conn, is_mysql = get_connection()
    now = datetime.now().isoformat()
    inserted = False
    try:
        cur = execute_db(conn, is_mysql, """
            INSERT OR IGNORE INTO businesses
                (profile_id, state, pincode, niche, name, rating, reviews,
                 phone, phone_2, phone_3, website_available, website_link, maps_url, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile_id, state, pincode, niche,
            item.get("Name", ""), item.get("Rating", ""), item.get("Reviews", ""),
            item.get("Phone 1", item.get("Phone", "")),
            item.get("Phone 2", ""),
            item.get("Phone 3", ""),
            item.get("Website Available?", ""),
            item.get("Website Link", ""), maps_url, now
        ))
        if cur.rowcount > 0:
            inserted = True
        if not is_mysql: conn.commit()
        return inserted
    except Exception:
        return False
    finally:
        conn.close()


def update_lead_status(business_id: int, status: str, notes: str = None):
    conn, is_mysql = get_connection()
    try:
        now = datetime.now().isoformat()
        if notes is not None:
            execute_db(conn, is_mysql,
                "UPDATE businesses SET lead_status=?, notes=?, updated_at=? WHERE id=?",
                (status, notes, now, business_id)
            )
        else:
            execute_db(conn, is_mysql,
                "UPDATE businesses SET lead_status=?, updated_at=? WHERE id=?",
                (status, now, business_id)
            )
        if not is_mysql: conn.commit()
    finally:
        conn.close()


def get_businesses_without_phone(profile_id: int) -> list:
    """Return list of dicts for businesses with no phone number (for phone enrichment)."""
    conn, is_mysql = get_connection()
    try:
        query = """
            SELECT id, name, pincode, state, niche, phone, phone_2, maps_url
            FROM businesses
            WHERE profile_id=?
              AND (phone IS NULL OR phone='' OR phone='N/A')
            ORDER BY scraped_at DESC
        """
        cur = execute_db(conn, is_mysql, query, (profile_id,))
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_business_phone(business_id: int, phone: str = None, phone_2: str = None):
    """Update phone and/or phone_2 for a business. Only updates non-None values.
    Never overwrites an existing non-empty phone with None."""
    conn, is_mysql = get_connection()
    try:
        now = datetime.now().isoformat()
        if phone is not None and phone_2 is not None:
            execute_db(conn, is_mysql,
                "UPDATE businesses SET phone=?, phone_2=?, updated_at=? WHERE id=?",
                (phone, phone_2, now, business_id)
            )
        elif phone is not None:
            execute_db(conn, is_mysql,
                "UPDATE businesses SET phone=?, updated_at=? WHERE id=?",
                (phone, now, business_id)
            )
        elif phone_2 is not None:
            execute_db(conn, is_mysql,
                "UPDATE businesses SET phone_2=?, updated_at=? WHERE id=?",
                (phone_2, now, business_id)
            )
        if not is_mysql: conn.commit()
    finally:
        conn.close()


def get_businesses(profile_id: int = 1, state: str = None, pincode: str = None,
                   niche: str = None, has_phone: bool = None, has_website: bool = None,
                   lead_status: str = None, page: int = 1, limit: int = 500) -> pd.DataFrame:
    conn, is_mysql = get_connection()
    try:
        query = "SELECT * FROM businesses WHERE profile_id=?"
        params = [profile_id]

        if state:
            query += " AND state=?"
            params.append(state)
        if pincode:
            query += " AND pincode=?"
            params.append(pincode)
        if niche:
            query += " AND niche=?"
            params.append(niche)
        if has_phone is True:
            query += " AND phone NOT IN ('N/A', '')"
        elif has_phone is False:
            query += " AND (phone IN ('N/A', '') OR phone IS NULL)"

        if has_website is True:
            query += " AND website_available='Yes'"
        elif has_website is False:
            query += " AND website_available!='Yes'"

        if lead_status:
            query += " AND lead_status=?"
            params.append(lead_status)

        offset = max(0, (page - 1) * limit)
        query += " ORDER BY scraped_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cur = execute_db(conn, is_mysql, query, params)
        rows = cur.fetchall()
        if not rows:
            return pd.DataFrame()
        records = [dict(r) for r in rows]
        return pd.DataFrame(records)
    finally:
        conn.close()


def get_business_by_id(biz_id: int) -> dict:
    conn, is_mysql = get_connection()
    try:
        cur = execute_db(conn, is_mysql, "SELECT * FROM businesses WHERE id=?", (biz_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_businesses_df(profile_id: int = None) -> pd.DataFrame:
    conn, is_mysql = get_connection()
    try:
        if profile_id:
            query = "SELECT * FROM businesses WHERE profile_id=? ORDER BY state,pincode,niche,name"
            params = [profile_id]
        else:
            query = "SELECT * FROM businesses ORDER BY state,pincode,niche,name"
            params = []

        cur = execute_db(conn, is_mysql, query, params)
        rows = cur.fetchall()
        if not rows:
            return pd.DataFrame()
        records = [dict(r) for r in rows]
        return pd.DataFrame(records)
    finally:
        conn.close()


def get_stats(profile_id: int = None) -> dict:
    conn, is_mysql = get_connection()
    try:
        pid_filter = "WHERE profile_id=?" if profile_id else ""
        pid_args = (profile_id,) if profile_id else ()

        def q(sql, args=()):
            c = execute_db(conn, is_mysql, sql, args)
            row = c.fetchone()
            if not row:
                return 0
            if isinstance(row, dict):
                return list(row.values())[0]
            return row[0]

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

        status_sql = f"SELECT lead_status, COUNT(*) as cnt FROM businesses {pid_filter} GROUP BY lead_status"
        c = execute_db(conn, is_mysql, status_sql, pid_args)
        rows = c.fetchall()
        lead_breakdown = {}
        for r in rows:
            if isinstance(r, dict):
                lead_breakdown[r["lead_status"]] = r["cnt"]
            else:
                lead_breakdown[r[0]] = r[1]

        return {
            "total_businesses": total_businesses,
            "total_jobs_done": total_jobs,
            "total_pincodes_done": total_pincodes,
            "total_states_scraped": total_states,
            "businesses_with_phone": with_phone,
            "businesses_with_website": with_website,
            "lead_status_breakdown": lead_breakdown,
        }
    finally:
        conn.close()


def get_scraped_jobs_df(profile_id: int = None) -> pd.DataFrame:
    conn, is_mysql = get_connection()
    try:
        if profile_id:
            query = "SELECT * FROM scraped_jobs WHERE profile_id=? ORDER BY scraped_at DESC"
            params = [profile_id]
        else:
            query = "SELECT * FROM scraped_jobs ORDER BY scraped_at DESC"
            params = []

        if is_mysql:
            query = query.replace("?", "%s")

        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()


def get_distinct_states(profile_id: int = None) -> list:
    conn, is_mysql = get_connection()
    try:
        if profile_id:
            c = execute_db(conn, is_mysql, "SELECT DISTINCT state FROM businesses WHERE profile_id=? ORDER BY state", (profile_id,))
        else:
            c = execute_db(conn, is_mysql, "SELECT DISTINCT state FROM businesses ORDER BY state")
        rows = c.fetchall()
        return [r["state"] if isinstance(r, dict) else r[0] for r in rows]
    finally:
        conn.close()


def get_distinct_niches(profile_id: int = None) -> list:
    conn, is_mysql = get_connection()
    try:
        if profile_id:
            c = execute_db(conn, is_mysql, "SELECT DISTINCT niche FROM businesses WHERE profile_id=? ORDER BY niche", (profile_id,))
        else:
            c = execute_db(conn, is_mysql, "SELECT DISTINCT niche FROM businesses ORDER BY niche")
        rows = c.fetchall()
        return [r["niche"] if isinstance(r, dict) else r[0] for r in rows]
    finally:
        conn.close()


# ── API User Management & Batch Delivery ──────────────────────────────────────

def register_api_user(username: str, phone_number: str, user_code: str, profile_id: int = 1) -> dict:
    conn, is_mysql = get_connection()
    try:
        now = datetime.now().isoformat()
        execute_db(conn, is_mysql, """
            INSERT INTO api_users (username, phone_number, user_code, profile_id, status, created_at)
            VALUES (?, ?, ?, ?, 'PENDING', ?)
        """, (username, phone_number, user_code, profile_id, now))
        if not is_mysql: conn.commit()
        return get_user_by_code(user_code)
    finally:
        conn.close()


def get_user_by_code(user_code: str) -> dict:
    conn, is_mysql = get_connection()
    try:
        cur = execute_db(conn, is_mysql, "SELECT * FROM api_users WHERE user_code=?", (user_code,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_api_users(status: str = None) -> list:
    conn, is_mysql = get_connection()
    try:
        if status:
            cur = execute_db(conn, is_mysql, "SELECT * FROM api_users WHERE status=? ORDER BY created_at DESC", (status,))
        else:
            cur = execute_db(conn, is_mysql, "SELECT * FROM api_users ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def update_user_status(user_code: str, status: str) -> bool:
    conn, is_mysql = get_connection()
    try:
        now = datetime.now().isoformat()
        approved_at = now if status == 'APPROVED' else None
        cur = execute_db(conn, is_mysql,
            "UPDATE api_users SET status=?, approved_at=? WHERE user_code=?",
            (status, approved_at, user_code)
        )
        affected = cur.rowcount > 0
        if not is_mysql: conn.commit()
        return affected
    finally:
        conn.close()


def get_and_mark_unsent_batch(user_code: str, profile_id: int = None, limit: int = 10) -> list:
    """
    ATOMIC 10-BATCH DELIVERY (MySQL + SQLite compatible):
    1. Finds up to `limit` businesses (default 10) where is_sent = 0.
    2. Immediately marks them as is_sent = 1, sent_to_user_code = user_code.
    3. Records them in sent_history table.
    """
    conn, is_mysql = get_connection()
    try:
        now = datetime.now().isoformat()
        query = "SELECT * FROM businesses WHERE is_sent=0"
        params = []
        if profile_id:
            query += " AND profile_id=?"
            params.append(profile_id)

        query += " ORDER BY id ASC LIMIT ?"
        params.append(limit)

        cur = execute_db(conn, is_mysql, query, params)
        rows = [dict(r) for r in cur.fetchall()]

        if not rows:
            return []

        biz_ids = [r["id"] for r in rows]
        placeholders = ",".join(["?"] * len(biz_ids))

        # Update businesses table
        execute_db(conn, is_mysql, f"""
            UPDATE businesses
            SET is_sent=1, sent_to_user_code=?, sent_at=?
            WHERE id IN ({placeholders})
        """, [user_code, now] + biz_ids)

        # Record in sent_history
        for bid in biz_ids:
            execute_db(conn, is_mysql, """
                INSERT INTO sent_history (user_code, business_id, sent_at)
                VALUES (?, ?, ?)
            """, (user_code, bid, now))

        if not is_mysql: conn.commit()
        return rows
    finally:
        conn.close()


def get_batch_delivery_stats(profile_id: int = None) -> dict:
    conn, is_mysql = get_connection()
    try:
        pid_filter = "WHERE profile_id=?" if profile_id else ""
        pid_args = (profile_id,) if profile_id else ()

        def q(sql, args=()):
            c = execute_db(conn, is_mysql, sql, args)
            row = c.fetchone()
            if not row:
                return 0
            if isinstance(row, dict):
                return list(row.values())[0]
            return row[0]

        total = q(f"SELECT COUNT(*) FROM businesses {pid_filter}", pid_args)

        unsent_filter = (f"WHERE profile_id=? AND is_sent=0" if profile_id
                         else "WHERE is_sent=0")
        unsent = q(f"SELECT COUNT(*) FROM businesses {unsent_filter}", pid_args)

        sent = total - unsent

        pending_users = q("SELECT COUNT(*) FROM api_users WHERE status='PENDING'")
        approved_users = q("SELECT COUNT(*) FROM api_users WHERE status='APPROVED'")

        return {
            "total_leads": total,
            "unsent_fresh_leads": unsent,
            "delivered_leads": sent,
            "pending_users": pending_users,
            "approved_users": approved_users,
        }
    finally:
        conn.close()
