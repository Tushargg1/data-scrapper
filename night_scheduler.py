"""
Night Phone Extraction Scheduler
Automatically executes the phone enrichment engine during night hours
(12:00 AM Midnight to 8:00 AM Morning IST - Indian Standard Time)
to discover phone numbers for businesses that have none, and tags them
with 'Extracted through other medium'.
"""
import time
import threading
from datetime import datetime, timezone, timedelta
from database import get_all_profiles, get_businesses_without_phone
from phone_enricher import (
    start_enrichment_thread, stop_enrichment,
    is_enrichment_running, get_enrich_status
)

# Indian Standard Time (IST = UTC + 5:30)
IST_TIMEZONE = timezone(timedelta(hours=5, minutes=30))

_scheduler_thread = None
_scheduler_lock = threading.Lock()
_scheduler_enabled = True
_last_auto_run_time = None
_auto_started_by_night = False

# Keepalive tracking
_keepalive_thread = None
_keepalive_lock = threading.Lock()
_last_keepalive_time = None
_KEEPALIVE_INTERVAL_SECONDS = 300  # Ping every 5 minutes


def get_ist_now() -> datetime:
    """Current time in Indian Standard Time (IST)."""
    return datetime.now(IST_TIMEZONE)


def is_in_night_window(dt: datetime = None) -> bool:
    """
    Returns True if current time is between 12:00 AM (00:00) and 8:00 AM (08:00) IST.
    """
    if dt is None:
        dt = get_ist_now()
    # 0 = 00:00 (12 midnight), 7 = 07:59:59 (up to 8:00 AM)
    return 0 <= dt.hour < 8


def get_night_scheduler_status() -> dict:
    now_ist = get_ist_now()
    in_window = is_in_night_window(now_ist)
    return {
        "enabled": _scheduler_enabled,
        "active_window": "12:00 AM to 8:00 AM IST (Midnight to Morning)",
        "current_ist_time": now_ist.strftime("%Y-%m-%d %I:%M:%S %p IST"),
        "is_in_night_window": in_window,
        "enrichment_running": is_enrichment_running(),
        "enrichment_status": get_enrich_status(),
        "last_auto_run": _last_auto_run_time,
        "auto_started_by_night": _auto_started_by_night,
        "last_db_keepalive": _last_keepalive_time,
    }


def set_night_scheduler_enabled(enabled: bool) -> dict:
    global _scheduler_enabled
    _scheduler_enabled = enabled
    return get_night_scheduler_status()


def _db_keepalive_worker():
    """
    Background thread that pings the Aiven MySQL database every 5 minutes
    with a lightweight SELECT 1 query to prevent it from powering off due
    to inactivity (Aiven free-tier auto-pauses after ~15 min idle).
    """
    global _last_keepalive_time
    print("[DB-KEEPALIVE] Database keepalive thread started. Pinging every 5 minutes.")

    while True:
        try:
            from database import get_connection
            conn, is_mysql = get_connection()
            if is_mysql:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.fetchone()
                conn.close()
                now_str = get_ist_now().strftime("%Y-%m-%d %I:%M:%S %p IST")
                _last_keepalive_time = now_str
                print(f"[DB-KEEPALIVE] Pinged Aiven MySQL at {now_str} — connection healthy.")
            else:
                conn.close()
                print("[DB-KEEPALIVE] MySQL not reachable, currently on SQLite. Will retry in 5 min.")
        except Exception as e:
            print(f"[DB-KEEPALIVE] Ping error: {e}")

        time.sleep(_KEEPALIVE_INTERVAL_SECONDS)


def _night_scheduler_worker():
    global _last_auto_run_time, _auto_started_by_night
    print("[NIGHT-SCHEDULER] Night Phone Extraction Scheduler active (12:00 AM to 8:00 AM IST).")

    while True:
        try:
            if _scheduler_enabled:
                now_ist = get_ist_now()
                in_window = is_in_night_window(now_ist)

                if in_window:
                    # Inside 12:00 AM - 8:00 AM IST
                    from scrape_manager import is_scrape_running
                    if is_scrape_running():
                        if _auto_started_by_night and is_enrichment_running():
                            print("[NIGHT-SCHEDULER] Scrape job is active. Pausing night extraction to avoid dual-browser memory spike.")
                            stop_enrichment()
                            _auto_started_by_night = False
                    elif not is_enrichment_running():
                        profiles = get_all_profiles()
                        for p in profiles:
                            pid = p["id"]
                            missing = get_businesses_without_phone(pid)
                            if missing:
                                print(
                                    f"[NIGHT-SCHEDULER] [{now_ist.strftime('%I:%M %p IST')}] "
                                    f"Found {len(missing)} businesses without phone in '{p['name']}'. "
                                    f"Starting phone extraction engine..."
                                )
                                start_enrichment_thread(pid)
                                _last_auto_run_time = now_ist.strftime("%Y-%m-%d %I:%M:%S %p IST")
                                _auto_started_by_night = True
                                break
                else:
                    # Outside night window (8:00 AM to 11:59 PM IST)
                    # If an auto-started night run is still going past 8:00 AM, stop it gracefully
                    if _auto_started_by_night and is_enrichment_running():
                        print(f"[NIGHT-SCHEDULER] 8:00 AM IST reached. Pausing night extraction.")
                        stop_enrichment()
                        _auto_started_by_night = False

        except Exception as ex:
            print(f"[NIGHT-SCHEDULER] Error in scheduler loop: {ex}")

        # Check every 60 seconds
        time.sleep(60)


def start_night_scheduler():
    """Start the background daemon threads if not already running."""
    global _scheduler_thread, _keepalive_thread
    with _scheduler_lock:
        if _scheduler_thread is None or not _scheduler_thread.is_alive():
            _scheduler_thread = threading.Thread(target=_night_scheduler_worker, daemon=True)
            _scheduler_thread.start()

    with _keepalive_lock:
        if _keepalive_thread is None or not _keepalive_thread.is_alive():
            _keepalive_thread = threading.Thread(target=_db_keepalive_worker, daemon=True)
            _keepalive_thread.start()
