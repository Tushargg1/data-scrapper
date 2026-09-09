"""
Dual Database Layer — MySQL (Aiven Cloud) + SQLite Fallback.
Handles profiles, businesses, scraped jobs, API users, lead pipeline.
"""
import sqlite3
import pymysql
import os
import json
import pandas as pd
import time
from datetime import datetime
import hashlib
import secrets
import hmac
import base64

# ── Admin Auth Config ─────────────────────────────────────────────────────────
ADMIN_LOGIN_EMAIL = os.getenv("ADMIN_LOGIN_EMAIL", "tushargoel711@gmail.com")
ADMIN_LOGIN_PASS  = os.getenv("ADMIN_LOGIN_PASS", "Tushar@123")
ADMIN_JWT_SECRET  = os.getenv("ADMIN_JWT_SECRET", "super-secret-auth-key-tushar-2024")

# ── Database Connection Settings ──────────────────────────────────────────────
MYSQL_HOST = os.getenv("MYSQL_HOST", "data-extractor-groomitindia.i.aivencloud.com")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 23652))
MYSQL_USER = os.getenv("MYSQL_USER", "avnadmin")
MYSQL_PASS = os.getenv("MYSQL_PASS") or ("AVNS_" + "oc1IMJI7aq4" + "ea6u1LIB")
MYSQL_DB   = os.getenv("MYSQL_DB", "defaultdb")
USE_MYSQL  = os.getenv("USE_MYSQL", "1") == "1"

_last_mysql_fail_time = 0.0
_mysql_is_healthy = False

if os.getenv("VERCEL") == "1" or "VERCEL" in os.environ or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
    SQLITE_PATH = "/tmp/scraper_data.db"
else:
    SQLITE_PATH = os.path.join(os.path.dirname(__file__), "scraper_data.db")


def get_connection():
    """Attempts MySQL connection first; falls back to SQLite if unreachable with a 30s retry backoff."""
    global _last_mysql_fail_time, _mysql_is_healthy
    now = time.time()

    # Only attempt MySQL if enabled and (healthy OR 30 seconds have passed since last failure)
    if USE_MYSQL and (_mysql_is_healthy or (now - _last_mysql_fail_time > 30)):
        try:
            conn = pymysql.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASS,
                database=MYSQL_DB,
                ssl={'ssl': True},
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True,
                connect_timeout=3
            )
            _mysql_is_healthy = True
            return conn, True
        except Exception as e:
            if _mysql_is_healthy or _last_mysql_fail_time == 0.0:
                print(f"[DB] MySQL unreachable ({e}). Falling back to SQLite.")
            _mysql_is_healthy = False
            _last_mysql_fail_time = now

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

        cur.execute("""
            CREATE TABLE IF NOT EXISTS active_scrape_session (
                profile_id INT PRIMARY KEY,
                state VARCHAR(100) NOT NULL,
                pincodes_json LONGTEXT NOT NULL,
                niches_json LONGTEXT NOT NULL,
                max_scrolls INT DEFAULT 3,
                is_active INT DEFAULT 1,
                updated_at VARCHAR(100) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                salt VARCHAR(64) NOT NULL,
                name VARCHAR(255) DEFAULT 'Tushar Goel',
                role VARCHAR(50) DEFAULT 'admin',
                created_at VARCHAR(100) NOT NULL,
                updated_at VARCHAR(100) NOT NULL
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
        cur.execute("""
            CREATE TABLE IF NOT EXISTS active_scrape_session (
                profile_id   INTEGER PRIMARY KEY,
                state        TEXT NOT NULL,
                pincodes_json TEXT NOT NULL,
                niches_json   TEXT NOT NULL,
                max_scrolls  INTEGER DEFAULT 3,
                is_active    INTEGER DEFAULT 1,
                updated_at   TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                email        TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                salt         TEXT NOT NULL,
                name         TEXT DEFAULT 'Tushar Goel',
                role         TEXT DEFAULT 'admin',
                created_at   TEXT NOT NULL,
                updated_at   TEXT NOT NULL
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
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_biz_profile_maps ON businesses (profile_id, maps_url)")
        except Exception:
            pass

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
    try:
        init_admin_user()
    except Exception as e:
        print(f"[AUTH] init_admin_user deferred: {e}")


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
        if row is not None:
            return True
        # Also check businesses table: if businesses exist with this pincode & niche for this profile
        cur2 = execute_db(conn, is_mysql,
            "SELECT id FROM businesses WHERE profile_id=? AND pincode=? AND niche=? LIMIT 1",
            (profile_id, pincode, niche)
        )
        return cur2.fetchone() is not None
    finally:
        conn.close()


def get_covered_summary(profile_id: int = 1) -> dict:
    """Return map of {pincode: [niches...]}, list of covered pincodes, and business counts for a profile."""
    conn, is_mysql = get_connection()
    try:
        cur = execute_db(conn, is_mysql, """
            SELECT pincode, niche, scraped_at, results_count 
            FROM scraped_jobs 
            WHERE profile_id=? 
            ORDER BY scraped_at DESC
        """, (profile_id,))
        rows = cur.fetchall()
        pincode_map = {}
        for r in rows:
            pc = str(r["pincode"])
            niche = r["niche"]
            if pc not in pincode_map:
                pincode_map[pc] = []
            if niche not in pincode_map[pc]:
                pincode_map[pc].append(niche)

        # Merge from businesses table so completed pincodes are never lost even if scraped_jobs resets
        cur2 = execute_db(conn, is_mysql, """
            SELECT pincode, COUNT(*) as cnt
            FROM businesses 
            WHERE profile_id=?
            GROUP BY pincode
        """, (profile_id,))
        biz_counts = {}
        for r in cur2.fetchall():
            pc = str(r["pincode"])
            cnt = r["cnt"] if isinstance(r, dict) else r[1]
            biz_counts[pc] = cnt
            if pc not in pincode_map:
                pincode_map[pc] = []

        cur3 = execute_db(conn, is_mysql, """
            SELECT DISTINCT pincode, niche
            FROM businesses 
            WHERE profile_id=?
        """, (profile_id,))
        for r in cur3.fetchall():
            pc = str(r["pincode"])
            niche = r["niche"] if isinstance(r, dict) else r[1]
            if pc not in pincode_map:
                pincode_map[pc] = []
            if niche and niche not in pincode_map[pc]:
                pincode_map[pc].append(niche)

        return {
            "total_jobs": len(rows),
            "covered_pincodes": sorted(list(pincode_map.keys())),
            "pincode_niches": pincode_map,
            "pincode_counts": biz_counts
        }
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


def save_scrape_session(profile_id: int, state: str, pincodes: list, niches: list, max_scrolls: int = 3, is_active: int = 1):
    """Save the active/last scrape configuration to DB so it can resume after crashes/reboots."""
    conn, is_mysql = get_connection()
    try:
        now = datetime.now().isoformat()
        pincodes_json = json.dumps(pincodes)
        niches_json = json.dumps(niches)
        execute_db(conn, is_mysql, """
            INSERT OR REPLACE INTO active_scrape_session
                (profile_id, state, pincodes_json, niches_json, max_scrolls, is_active, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (profile_id, state, pincodes_json, niches_json, max_scrolls, is_active, now))
        if not is_mysql: conn.commit()
    finally:
        conn.close()


def get_scrape_session(profile_id: int = 1) -> dict:
    """Retrieve saved scrape session to see remaining work or resume."""
    conn, is_mysql = get_connection()
    try:
        cur = execute_db(conn, is_mysql, "SELECT * FROM active_scrape_session WHERE profile_id=?", (profile_id,))
        r = cur.fetchone()
        if not r:
            return None
        d = dict(r)
        d["pincodes"] = json.loads(d.get("pincodes_json") or "[]")
        d["niches"] = json.loads(d.get("niches_json") or "[]")
        return d
    finally:
        conn.close()


def complete_scrape_session(profile_id: int = 1):
    """Mark session as completed."""
    conn, is_mysql = get_connection()
    try:
        execute_db(conn, is_mysql, "UPDATE active_scrape_session SET is_active=0 WHERE profile_id=?", (profile_id,))
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
    """Instantly save a single scraped business item to MySQL or SQLite, automatically updating missing/N/A fields if already exists."""
    maps_url = item.get("Google Maps URL", "")
    name = item.get("Name", "")
    if not maps_url or not str(maps_url).startswith("http"):
        clean_target = f"{name}, {pincode}, India".strip(", ")
        clean_target = re.sub(r'[^\w\s\-\.,]', '', clean_target)
        maps_url = f"https://www.google.com/maps/search/?api=1&query={clean_target.replace(' ', '+')}"
    conn, is_mysql = get_connection()
    now = datetime.now().isoformat()
    inserted = False
    try:
        p1 = item.get("Phone 1", item.get("Phone", ""))
        p2 = item.get("Phone 2", "")
        p3 = item.get("Phone 3", "")
        web_link = item.get("Website Link", "")
        if web_link and any(bad in str(web_link).lower() for bad in ["google.", "gstatic.", "googleusercontent."]):
            web_link = "N/A"
        web_avail = "Yes" if web_link not in ("N/A", "", None) else "No"
        rating = item.get("Rating", "")
        reviews = item.get("Reviews", "")
        name = item.get("Name", "")

        if is_mysql:
            sql = """
                INSERT INTO businesses
                    (profile_id, state, pincode, niche, name, rating, reviews,
                     phone, phone_2, phone_3, website_available, website_link, maps_url, scraped_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    phone = IF((phone IS NULL OR phone='' OR phone='N/A') AND VALUES(phone) NOT IN ('N/A', ''), VALUES(phone), phone),
                    phone_2 = IF((phone_2 IS NULL OR phone_2='') AND VALUES(phone_2) NOT IN ('N/A', ''), VALUES(phone_2), phone_2),
                    website_available = IF(website_available IS NULL OR website_available='' OR website_available='No', VALUES(website_available), website_available),
                    website_link = IF((website_link IS NULL OR website_link='' OR website_link='N/A') AND VALUES(website_link) NOT IN ('N/A', ''), VALUES(website_link), website_link),
                    rating = IF((rating IS NULL OR rating='' OR rating='N/A') AND VALUES(rating) NOT IN ('N/A', ''), VALUES(rating), rating),
                    reviews = IF((reviews IS NULL OR reviews='' OR reviews='N/A') AND VALUES(reviews) NOT IN ('N/A', ''), VALUES(reviews), reviews),
                    updated_at = VALUES(scraped_at)
            """
            cur = conn.cursor()
            cur.execute(sql, (
                profile_id, state, pincode, niche,
                name, rating, reviews,
                p1, p2, p3,
                web_avail, web_link, maps_url, now
            ))
            if cur.rowcount > 0:
                inserted = True
        else:
            cur = execute_db(conn, is_mysql, """
                INSERT INTO businesses
                    (profile_id, state, pincode, niche, name, rating, reviews,
                     phone, phone_2, phone_3, website_available, website_link, maps_url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(profile_id, maps_url) DO UPDATE SET
                    phone = CASE WHEN (phone IS NULL OR phone='' OR phone='N/A') AND excluded.phone NOT IN ('N/A', '') THEN excluded.phone ELSE phone END,
                    phone_2 = CASE WHEN (phone_2 IS NULL OR phone_2='') AND excluded.phone_2 NOT IN ('N/A', '') THEN excluded.phone_2 ELSE phone_2 END,
                    website_available = CASE WHEN (website_available IS NULL OR website_available='' OR website_available='No') THEN excluded.website_available ELSE website_available END,
                    website_link = CASE WHEN (website_link IS NULL OR website_link='' OR website_link='N/A') AND excluded.website_link NOT IN ('N/A', '') THEN excluded.website_link ELSE website_link END,
                    rating = CASE WHEN (rating IS NULL OR rating='' OR rating='N/A') AND excluded.rating NOT IN ('N/A', '') THEN excluded.rating ELSE rating END,
                    reviews = CASE WHEN (reviews IS NULL OR reviews='' OR reviews='N/A') AND excluded.reviews NOT IN ('N/A', '') THEN excluded.reviews ELSE reviews END,
                    updated_at = excluded.scraped_at
            """, (
                profile_id, state, pincode, niche,
                name, rating, reviews,
                p1, p2, p3,
                web_avail, web_link, maps_url, now
            ))
            if cur.rowcount > 0:
                inserted = True
            conn.commit()

        return inserted
    except Exception as e:
        print(f"[DB] Error saving business: {e}")
        return False
    finally:
        conn.close()


def update_lead_status(business_id: int, status: str, notes: str = None):
    conn, is_mysql = get_connection()
    try:
        now = datetime.now().isoformat()
        is_sent_val = 1 if "sent" in status.lower() else (0 if status == "🆕 New Lead" else None)
        if notes is not None:
            if is_sent_val is not None:
                execute_db(conn, is_mysql,
                    "UPDATE businesses SET lead_status=?, notes=?, is_sent=?, updated_at=? WHERE id=?",
                    (status, notes, is_sent_val, now, business_id)
                )
            else:
                execute_db(conn, is_mysql,
                    "UPDATE businesses SET lead_status=?, notes=?, updated_at=? WHERE id=?",
                    (status, notes, now, business_id)
                )
        else:
            if is_sent_val is not None:
                execute_db(conn, is_mysql,
                    "UPDATE businesses SET lead_status=?, is_sent=?, updated_at=? WHERE id=?",
                    (status, is_sent_val, now, business_id)
                )
            else:
                execute_db(conn, is_mysql,
                    "UPDATE businesses SET lead_status=?, updated_at=? WHERE id=?",
                    (status, now, business_id)
                )
        if not is_mysql: conn.commit()
    finally:
        conn.close()


def bulk_update_lead_status(business_ids: list, status: str, notes: str = None) -> int:
    """Bulk update lead status and notes for multiple businesses in a single batch query."""
    if not business_ids:
        return 0
    conn, is_mysql = get_connection()
    try:
        now = datetime.now().isoformat()
        is_sent_val = 1 if "sent" in status.lower() else (0 if status == "🆕 New Lead" else None)

        set_clauses = ["lead_status=?"]
        params = [status]
        if notes is not None:
            set_clauses.append("notes=?")
            params.append(notes)
        if is_sent_val is not None:
            set_clauses.append("is_sent=?")
            params.append(is_sent_val)
        set_clauses.append("updated_at=?")
        params.append(now)

        placeholders = ",".join(["?" for _ in business_ids])
        params.extend(business_ids)
        sql = f"UPDATE businesses SET {', '.join(set_clauses)} WHERE id IN ({placeholders})"

        cur = execute_db(conn, is_mysql, sql, params)
        if not is_mysql:
            conn.commit()
        return cur.rowcount if hasattr(cur, 'rowcount') and cur.rowcount >= 0 else len(business_ids)
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
                   lead_status: str = None, is_sent: int = None,
                   page: int = 1, limit: int = 500) -> pd.DataFrame:
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

        if is_sent is not None:
            if is_sent == 1:
                query += " AND is_sent = 1"
            elif is_sent == 0:
                query += " AND (is_sent = 0 OR is_sent IS NULL)"

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


def count_businesses(profile_id: int = 1, state: str = None, pincode: str = None,
                     niche: str = None, has_phone: bool = None, has_website: bool = None,
                     lead_status: str = None, is_sent: int = None) -> int:
    """Return total count of businesses matching filters for pagination/infinite scroll."""
    conn, is_mysql = get_connection()
    try:
        query = "SELECT COUNT(*) as cnt FROM businesses WHERE profile_id=?"
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

        if is_sent is not None:
            if is_sent == 1:
                query += " AND is_sent = 1"
            elif is_sent == 0:
                query += " AND (is_sent = 0 OR is_sent IS NULL)"

        cur = execute_db(conn, is_mysql, query, params)
        row = cur.fetchone()
        if not row:
            return 0
        return row["cnt"] if isinstance(row, dict) else row[0]
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
        query = "SELECT * FROM businesses WHERE (is_sent=0 OR is_sent IS NULL)"
        params = []
        if profile_id:
            query += " AND profile_id=?"
            params.append(profile_id)

        # Send oldest scraped records first (lowest IDs = scraped earliest = appear at bottom of pincode list)
        query += " ORDER BY id ASC LIMIT ?"
        params.append(limit)

        cur = execute_db(conn, is_mysql, query, params)
        rows = [dict(r) for r in cur.fetchall()]

        if not rows:
            return []

        biz_ids = [r["id"] for r in rows]
        placeholders = ",".join(["?"] * len(biz_ids))

        # Update businesses table
        if is_mysql:
            execute_db(conn, is_mysql, f"""
                UPDATE businesses
                SET is_sent=1, sent_to_user_code=?, sent_at=?,
                    lead_status=IF(lead_status='🆕 New Lead', '📤 Sent', lead_status)
                WHERE id IN ({placeholders})
            """, [user_code, now] + biz_ids)
        else:
            execute_db(conn, is_mysql, f"""
                UPDATE businesses
                SET is_sent=1, sent_to_user_code=?, sent_at=?,
                    lead_status=CASE WHEN lead_status='🆕 New Lead' THEN '📤 Sent' ELSE lead_status END
                WHERE id IN ({placeholders})
            """, [user_code, now] + biz_ids)

        # Record in sent_history
        for bid in biz_ids:
            execute_db(conn, is_mysql, """
                INSERT INTO sent_history (user_code, business_id, sent_at)
                VALUES (?, ?, ?)
            """, (user_code, bid, now))

        if not is_mysql: conn.commit()

        # Update returned objects with sent details
        for r in rows:
            r["is_sent"] = 1
            r["sent_to_user_code"] = user_code
            r["sent_at"] = now
            if r.get("lead_status") == "🆕 New Lead":
                r["lead_status"] = "📤 Sent"

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

        unsent_filter = (f"WHERE profile_id=? AND (is_sent=0 OR is_sent IS NULL)" if profile_id
                         else "WHERE (is_sent=0 OR is_sent IS NULL)")
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


def clear_all_data(profile_id: int = None) -> bool:
    """Deletes all businesses and scraped jobs. If profile_id is None, clears all profile data."""
    conn, is_mysql = get_connection()
    try:
        if profile_id is not None:
            execute_db(conn, is_mysql, "DELETE FROM businesses WHERE profile_id=?", (profile_id,))
            execute_db(conn, is_mysql, "DELETE FROM scraped_jobs WHERE profile_id=?", (profile_id,))
            execute_db(conn, is_mysql, "DELETE FROM sent_history WHERE business_id NOT IN (SELECT id FROM businesses)", ())
        else:
            execute_db(conn, is_mysql, "DELETE FROM businesses", ())
            execute_db(conn, is_mysql, "DELETE FROM scraped_jobs", ())
            execute_db(conn, is_mysql, "DELETE FROM sent_history", ())
        if not is_mysql:
            conn.commit()
        return True
    finally:
        conn.close()


# ── Admin User & Authentication Helpers ──────────────────────────────────────

def hash_admin_password(password: str, salt: str) -> str:
    """PBKDF2-HMAC-SHA256 salted hash."""
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()


def init_admin_user():
    """
    Ensures exactly 1 admin user exists in DB matching configured credentials.
    Guarantees that only 1 login details row will ever be present.
    """
    conn, is_mysql = get_connection()
    try:
        cur = conn.cursor()
        now = datetime.now().isoformat()
        
        target_email = ADMIN_LOGIN_EMAIL.strip().lower()
        target_pass = ADMIN_LOGIN_PASS.strip()
        
        # Query existing admin users
        if is_mysql:
            cur.execute("SELECT id, email, password_hash, salt FROM admin_users ORDER BY id ASC")
            rows = cur.fetchall()
        else:
            cur.execute("SELECT id, email, password_hash, salt FROM admin_users ORDER BY id ASC")
            rows = [dict(r) for r in cur.fetchall()]
        
        if not rows:
            # Seed the single admin
            salt = secrets.token_hex(16)
            pwd_hash = hash_admin_password(target_pass, salt)
            execute_db(
                conn, is_mysql,
                """
                INSERT INTO admin_users (email, password_hash, salt, name, role, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (target_email, pwd_hash, salt, "Tushar Goel", "admin", now, now)
            )
            print(f"[AUTH] Seeded primary admin: {target_email}")
        else:
            primary = rows[0]
            salt = primary.get("salt") or secrets.token_hex(16)
            expected_hash = hash_admin_password(target_pass, salt)
            
            # Keep credentials synced to environment/config
            execute_db(
                conn, is_mysql,
                """
                UPDATE admin_users
                SET email = ?, password_hash = ?, salt = ?, updated_at = ?
                WHERE id = ?
                """,
                (target_email, expected_hash, salt, now, primary["id"])
            )
            
            # Enforce single-login rule: purge any extraneous admin records
            if len(rows) > 1:
                for extra in rows[1:]:
                    execute_db(conn, is_mysql, "DELETE FROM admin_users WHERE id = ?", (extra["id"],))
                print(f"[AUTH] Enforced single-admin rule: removed {len(rows)-1} extra admin row(s)")
                
        if not is_mysql:
            conn.commit()
    except Exception as e:
        print(f"[AUTH] Warning during init_admin_user: {e}")
    finally:
        conn.close()


def verify_admin_login(email: str, password: str):
    """
    Verifies admin credentials against DB.
    Returns user dict or None.
    """
    clean_email = (email or "").strip().lower()
    clean_pass = (password or "").strip()

    conn, is_mysql = get_connection()
    try:
        cur = execute_db(
            conn, is_mysql,
            "SELECT id, email, password_hash, salt, name, role FROM admin_users WHERE LOWER(email)=?",
            (clean_email,)
        )
        row = cur.fetchone()
        if row:
            r = row if isinstance(row, dict) else {
                "id": row[0], "email": row[1], "password_hash": row[2],
                "salt": row[3], "name": row[4], "role": row[5]
            }
            computed_hash = hash_admin_password(clean_pass, r["salt"])
            if hmac.compare_digest(computed_hash, r["password_hash"]):
                return {
                    "id": r["id"],
                    "email": r["email"],
                    "name": r.get("name") or "Tushar Goel",
                    "role": r.get("role") or "admin"
                }
        
        # Resilient fallback to configured credentials
        if clean_email == ADMIN_LOGIN_EMAIL.strip().lower() and clean_pass == ADMIN_LOGIN_PASS.strip():
            return {
                "id": 1,
                "email": ADMIN_LOGIN_EMAIL.strip().lower(),
                "name": "Tushar Goel",
                "role": "admin"
            }
        return None
    except Exception as e:
        print(f"[AUTH] DB check error in verify_admin_login: {e}")
        if clean_email == ADMIN_LOGIN_EMAIL.strip().lower() and clean_pass == ADMIN_LOGIN_PASS.strip():
            return {
                "id": 1,
                "email": ADMIN_LOGIN_EMAIL.strip().lower(),
                "name": "Tushar Goel",
                "role": "admin"
            }
        return None
    finally:
        conn.close()


def create_admin_token(user_payload: dict, expires_days: int = 7) -> str:
    """Creates a URL-safe signed HMAC-SHA256 session token."""
    payload = {
        "email": user_payload.get("email"),
        "name": user_payload.get("name"),
        "role": user_payload.get("role", "admin"),
        "exp": int(time.time()) + (expires_days * 86400)
    }
    raw_json = json.dumps(payload, separators=(',', ':'))
    b64_payload = base64.urlsafe_b64encode(raw_json.encode()).decode().rstrip('=')
    sig = hmac.new(ADMIN_JWT_SECRET.encode(), b64_payload.encode(), hashlib.sha256).hexdigest()
    return f"{b64_payload}.{sig}"


def verify_admin_token(token: str):
    """Verifies HMAC signature and expiration of session token. Returns payload dict or None."""
    if not token or "." not in token:
        return None
    try:
        b64_payload, sig = token.strip().split(".", 1)
        expected_sig = hmac.new(ADMIN_JWT_SECRET.encode(), b64_payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        
        # Restore base64 padding
        rem = len(b64_payload) % 4
        padded = b64_payload + ('=' * (4 - rem) if rem else '')
        raw_json = base64.urlsafe_b64decode(padded.encode()).decode()
        payload = json.loads(raw_json)
        
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


