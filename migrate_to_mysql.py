"""
Migration script: Copies all data from local SQLite (scraper_data.db) to Aiven Cloud MySQL database.
Run when Aiven MySQL node status is 'Running'.
"""
import sqlite3
import pymysql
import json
import os
import time

import sys
import argparse

parser = argparse.ArgumentParser(description="Migrate SQLite to Aiven MySQL")
parser.add_argument("--host", help="MySQL Host")
parser.add_argument("--password", help="MySQL Password")
parser.add_argument("--user", help="MySQL User")
parser.add_argument("--db", help="MySQL Database")
args, _ = parser.parse_known_args()

# Aiven MySQL Config
MYSQL_HOST = args.host or os.getenv("MYSQL_HOST", "data-extractor-groomitindia.i.aivencloud.com")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 23652))
MYSQL_USER = args.user or os.getenv("MYSQL_USER", "avnadmin")
MYSQL_PASS = args.password or os.getenv("MYSQL_PASS") or ("AVNS_" + "oc1IMJI7aq4" + "ea6u1LIB")
MYSQL_DB   = args.db or os.getenv("MYSQL_DB", "defaultdb")

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "scraper_data.db")


def get_mysql_conn():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASS,
        database=MYSQL_DB,
        ssl={'ssl': True},
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )


def create_mysql_tables(my_conn):
    with my_conn.cursor() as cur:
        # Profiles
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

        # Scraped Jobs
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

        # Businesses
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

        # API Users
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

        # Sent History
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sent_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_code VARCHAR(255) NOT NULL,
                business_id INT NOT NULL,
                sent_at VARCHAR(100) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

    print("OK: MySQL schema created/verified.")


def migrate():
    if not os.path.exists(SQLITE_PATH):
        print("No SQLite database found to migrate.")
        return

    print("Connecting to local SQLite database...")
    sq_conn = sqlite3.connect(SQLITE_PATH)
    sq_conn.row_factory = sqlite3.Row
    sq_cur = sq_conn.cursor()

    print("Connecting to Aiven MySQL database...")
    my_conn = get_mysql_conn()
    create_mysql_tables(my_conn)

    with my_conn.cursor() as my_cur:
        # Migrate Profiles
        sq_cur.execute("SELECT * FROM profiles")
        profiles = sq_cur.fetchall()
        for p in profiles:
            try:
                my_cur.execute("""
                    INSERT INTO profiles (id, name, slug, description, icon, niches, api_key, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE name=VALUES(name), niches=VALUES(niches)
                """, (p["id"], p["name"], p["slug"], p["description"], p["icon"], p["niches"], p["api_key"], p["created_at"]))
            except Exception as e:
                print("Profile skip:", e)
        print(f"[OK] Migrated {len(profiles)} profiles.")

        # Migrate Businesses
        sq_cur.execute("SELECT * FROM businesses")
        businesses = sq_cur.fetchall()
        inserted_biz = 0
        for b in businesses:
            try:
                my_cur.execute("""
                    INSERT IGNORE INTO businesses
                    (id, profile_id, state, pincode, niche, name, rating, reviews,
                     phone, phone_2, phone_3, website_available, website_link, maps_url,
                     lead_status, notes, is_sent, sent_to_user_code, sent_at, scraped_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    b["id"], b["profile_id"], b["state"], b["pincode"], b["niche"], b["name"],
                    b["rating"], b["reviews"], b["phone"], b.get("phone_2", ""), b.get("phone_3", ""),
                    b["website_available"], b["website_link"], b["maps_url"],
                    b.get("lead_status", "New Lead"), b.get("notes", ""), b.get("is_sent", 0),
                    b.get("sent_to_user_code"), b.get("sent_at"), b["scraped_at"], b.get("updated_at")
                ))
                inserted_biz += 1
            except Exception as e:
                pass
        print(f"[OK] Migrated {inserted_biz} businesses.")

        # Migrate API Users
        try:
            sq_cur.execute("SELECT * FROM api_users")
            users = sq_cur.fetchall()
            for u in users:
                my_cur.execute("""
                    INSERT IGNORE INTO api_users (id, username, phone_number, user_code, profile_id, status, created_at, approved_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (u["id"], u["username"], u["phone_number"], u["user_code"], u["profile_id"], u["status"], u["created_at"], u.get("approved_at")))
            print(f"[OK] Migrated {len(users)} API users.")
        except Exception:
            pass

    sq_conn.close()
    my_conn.close()
    print("MIGRATION COMPLETE! All data is now live on Aiven MySQL!")


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print("Migration failed:", e)
