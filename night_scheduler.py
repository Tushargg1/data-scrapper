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
    }


def set_night_scheduler_enabled(enabled: bool) -> dict:
    global _scheduler_enabled
    _scheduler_enabled = enabled
    return get_night_scheduler_status()


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
                    if not is_enrichment_running():
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
    """Start the background daemon thread if not already running."""
    global _scheduler_thread
    with _scheduler_lock:
        if _scheduler_thread is None or not _scheduler_thread.is_alive():
            _scheduler_thread = threading.Thread(target=_night_scheduler_worker, daemon=True)
            _scheduler_thread.start()
