"""
Background Scrape Job Manager.
Runs Playwright Google Maps scraping asynchronously in a background thread,
saves businesses instantly to Aiven MySQL, records job history, and provides live status.
"""
import threading
import time
from database import (
    save_single_business, mark_as_scraped, is_already_scraped,
    get_profile_by_slug, get_all_profiles,
    save_scrape_session, complete_scrape_session, get_scrape_session,
    _release_thread_mysql
)
from scraper import scrape_google_maps, get_random_user_agent


scrape_lock = threading.Lock()
stop_scrape_event = threading.Event()

current_scrape_job = {
    "status": "idle",  # idle | running | completed | stopped | error
    "source": "google_maps",
    "source_name": "Google Maps",
    "profile_id": 1,
    "profile_name": "",
    "state": "",
    "total_jobs": 0,
    "done_jobs": 0,
    "scraped": 0,
    "saved": 0,
    "phones": 0,
    "webs": 0,
    "current_pincode": "",
    "current_niche": "",
    "started_at": None,
    "ended_at": None,
    "recent_items": [],
    "error": None
}

active_thread = None


def _launch_browser_and_context(playwright_inst):
    """Launch clean Chromium instance with consent cookies pre-set and rotated user agent."""
    browser = playwright_inst.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-software-rasterizer',
            # Memory reduction
            '--blink-settings=imagesEnabled=false',
            '--js-flags=--max-old-space-size=96',
            # Kill background activity that wastes RAM on cloud servers
            '--disable-extensions',
            '--disable-component-update',
            '--disable-background-networking',
            '--disable-background-timer-throttling',
            '--disable-client-side-phishing-detection',
            '--disable-default-apps',
            '--disable-sync',
            '--disable-translate',
            '--disable-hang-monitor',
            '--disable-prompt-on-repost',
            '--disable-breakpad',
            '--mute-audio',
            '--no-first-run',
            '--no-default-browser-check',
            '--metrics-recording-only',
        ]
    )
    context = browser.new_context(
        viewport={'width': 800, 'height': 600},
        user_agent=get_random_user_agent()
    )
    try:
        context.add_cookies([
            {'name': 'SOCS', 'value': 'CAESHAgBEhJnd3NfMjAyNDA2MTAtMF9SQzIaAmVuIAEaBgiA_L20Bg', 'domain': '.google.com', 'path': '/'},
            {'name': 'CONSENT', 'value': 'PENDING+987', 'domain': '.google.com', 'path': '/'}
        ])
    except Exception:
        pass
    return browser, context


def _run_worker(profile_id: int, state: str, pincodes: list, niches: list, max_scrolls: int, rescan_covered: bool = False, source: str = "google_maps"):
    global current_scrape_job
    stop_scrape_event.clear()
    total_jobs = len(pincodes) * len(niches)

    # Save active scrape session to DB so it can be resumed after reboot/crash
    try:
        save_scrape_session(profile_id, state, pincodes, niches, max_scrolls, is_active=1)
    except Exception as e:
        print(f"[SCRAPER] Warning saving session: {e}")

    # Get profile name
    p_name = f"Profile #{profile_id}"
    try:
        profiles = get_all_profiles()
        for p in profiles:
            if p["id"] == profile_id:
                p_name = p["name"]
                break
    except Exception:
        pass

    source_title = "Google Maps" if source == "google_maps" else source.replace("_", " ").title()

    with scrape_lock:
        current_scrape_job.update({
            "status": "running",
            "source": source,
            "source_name": source_title,
            "profile_id": profile_id,
            "profile_name": p_name,
            "state": state,
            "total_jobs": total_jobs,
            "done_jobs": 0,
            "scraped": 0,
            "saved": 0,
            "phones": 0,
            "webs": 0,
            "current_pincode": pincodes[0] if pincodes else "",
            "current_niche": niches[0] if niches else "",
            "started_at": time.time(),
            "ended_at": None,
            "recent_items": [],
            "error": None
        })

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser, context = _launch_browser_and_context(p)

            try:
                for pc in pincodes:
                    if stop_scrape_event.is_set():
                        break
                    for niche in niches:
                        if stop_scrape_event.is_set():
                            break

                        # If already scraped and user chose not to re-scrape, skip and continue
                        if not rescan_covered and is_already_scraped(pc, niche, profile_id):
                            with scrape_lock:
                                current_scrape_job["done_jobs"] += 1
                            continue

                        with scrape_lock:
                            current_scrape_job["current_pincode"] = pc
                            current_scrape_job["current_niche"] = niche

                        def on_item_scraped(item):
                            with scrape_lock:
                                current_scrape_job["scraped"] += 1
                                if item.get("Phone") not in ["N/A", ""]:
                                    current_scrape_job["phones"] += 1
                                if item.get("Website Available?") == "Yes":
                                    current_scrape_job["webs"] += 1

                                current_scrape_job["recent_items"].insert(0, {
                                    "name": item.get("Name", "N/A"),
                                    "phone": item.get("Phone 1", item.get("Phone", "N/A")),
                                    "phone_2": item.get("Phone 2", ""),
                                    "website": item.get("Website Link", ""),
                                    "rating": item.get("Rating", "N/A"),
                                    "reviews": item.get("Reviews", "N/A"),
                                    "pincode": pc,
                                    "niche": niche
                                })
                                if len(current_scrape_job["recent_items"]) > 25:
                                    current_scrape_job["recent_items"].pop()

                            is_new = save_single_business(state, pc, niche, item, profile_id)
                            if is_new:
                                with scrape_lock:
                                    current_scrape_job["saved"] += 1

                        # Self-healing retry loop: up to 2 attempts per query
                        max_query_attempts = 2
                        query_success = False

                        for attempt in range(max_query_attempts):
                            if stop_scrape_event.is_set():
                                break
                            try:
                                df = scrape_google_maps(
                                    niche=niche,
                                    pincode=pc,
                                    max_scrolls=max_scrolls,
                                    on_item_scraped=on_item_scraped,
                                    should_stop=lambda: stop_scrape_event.is_set(),
                                    context=context,
                                    profile_id=profile_id
                                )
                                count = len(df) if df is not None and not df.empty else 0
                                mark_as_scraped(state, pc, niche, count, profile_id)
                                query_success = True
                                break
                            except Exception as ex:
                                is_rate_limit = any(term in str(ex).lower() for term in ["sorry", "unusual traffic", "rate limit", "429", "captcha"])
                                pause_time = 45 if is_rate_limit else 2
                                if is_rate_limit:
                                    print(f"[SCRAPER] ⚠️ Rate limit / CAPTCHA detected on {niche} in {pc}. Rotating User-Agent & cooling down for {pause_time}s...")
                                else:
                                    print(f"[SCRAPER] Error on {niche} in {pc} (attempt {attempt+1}/{max_query_attempts}): {ex}")
                                # Re-heal browser context with fresh rotated User-Agent
                                try:
                                    context.close()
                                    browser.close()
                                except Exception:
                                    pass
                                time.sleep(pause_time)
                                try:
                                    browser, context = _launch_browser_and_context(p)
                                except Exception as err:
                                    print(f"[SCRAPER] Could not relaunch browser: {err}")

                        if not query_success:
                            with scrape_lock:
                                current_scrape_job["error"] = f"Skipped {pc} ({niche}) after retries."

                        with scrape_lock:
                            current_scrape_job["done_jobs"] += 1

            finally:
                try:
                    context.close()
                    browser.close()
                except Exception:
                    pass

        with scrape_lock:
            current_scrape_job["status"] = "stopped" if stop_scrape_event.is_set() else "completed"
            current_scrape_job["ended_at"] = time.time()

        # Mark session finished if completed without stop
        if not stop_scrape_event.is_set():
            try:
                complete_scrape_session(profile_id)
            except Exception:
                pass

    except Exception as e:
        with scrape_lock:
            current_scrape_job["status"] = "error"
            current_scrape_job["error"] = str(e)
            current_scrape_job["ended_at"] = time.time()

    finally:
        # Always release the thread-local MySQL connection when the worker exits
        try:
            _release_thread_mysql()
        except Exception:
            pass



def start_scraping(profile_id: int, state: str, pincodes: list, niches: list, max_scrolls: int = 3, rescan_covered: bool = False, source: str = "google_maps") -> dict:
    global active_thread

    with scrape_lock:
        if current_scrape_job["status"] == "running":
            return {"success": False, "message": "A scrape job is already running."}

    if not pincodes:
        return {"success": False, "message": "At least one pincode is required."}
    if not niches:
        return {"success": False, "message": "At least one niche is required."}

    active_thread = threading.Thread(
        target=_run_worker,
        args=(profile_id, state, pincodes, niches, max_scrolls, rescan_covered, source),
        daemon=True
    )
    active_thread.start()
    mode_text = "re-scraping all including covered" if rescan_covered else "skipping covered & continuing"
    source_label = "Google Maps" if source == "google_maps" else source.replace("_", " ").title()
    return {"success": True, "message": f"[{source_label}] Scrape job started for {len(pincodes)} pincodes and {len(niches)} niches ({mode_text})."}


def stop_scraping() -> dict:
    with scrape_lock:
        if current_scrape_job["status"] != "running":
            return {"success": False, "message": "No scrape job is currently running."}
        stop_scrape_event.set()
        return {"success": True, "message": "Stopping scrape job..."}


def get_scrape_status() -> dict:
    with scrape_lock:
        data = dict(current_scrape_job)
        data["recent_items"] = list(current_scrape_job["recent_items"])

        # Calculate progress
        total = data.get("total_jobs", 0)
        done = data.get("done_jobs", 0)
        data["progress_percent"] = round((done / total * 100), 1) if total > 0 else 0

        # Calculate elapsed time
        if data.get("started_at"):
            end = data.get("ended_at") or time.time()
            data["elapsed_seconds"] = int(end - data["started_at"])
        else:
            data["elapsed_seconds"] = 0

        return data


def resume_scraping(profile_id: int) -> dict:
    """Resume a previous or interrupted scrape job from where it left off."""
    session = get_scrape_session(profile_id)
    if not session:
        return {"success": False, "message": "No saved scrape session found for this profile."}

    pincodes = session.get("pincodes", [])
    niches = session.get("niches", [])
    state = session.get("state", "")
    max_scrolls = session.get("max_scrolls", 3)

    if not pincodes or not niches:
        return {"success": False, "message": "Saved session has no pincodes or niches."}

    # Start with rescan_covered=False so it automatically skips covered ones and continues
    return start_scraping(
        profile_id=profile_id,
        state=state,
        pincodes=pincodes,
        niches=niches,
        max_scrolls=max_scrolls,
        rescan_covered=False
    )


def get_last_session_info(profile_id: int) -> dict:
    """Return info about saved session, including total and remaining jobs."""
    session = get_scrape_session(profile_id)
    if not session:
        return {"has_session": False}

    pincodes = session.get("pincodes", [])
    niches = session.get("niches", [])
    total_combos = len(pincodes) * len(niches)
    
    # Count how many are already finished
    done_count = 0
    for pc in pincodes:
        for n in niches:
            if is_already_scraped(pc, n, profile_id):
                done_count += 1

    remaining = total_combos - done_count
    return {
        "has_session": True,
        "is_active": session.get("is_active", 0) == 1,
        "state": session.get("state", ""),
        "total_pincodes": len(pincodes),
        "total_niches": len(niches),
        "total_jobs": total_combos,
        "done_jobs": done_count,
        "remaining_jobs": remaining,
        "updated_at": session.get("updated_at", "")
    }

