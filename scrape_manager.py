"""
Background Scrape Job Manager.
Runs Playwright Google Maps scraping asynchronously in a background thread,
saves businesses instantly to Aiven MySQL, records job history, and provides live status.
"""
import threading
import time
from database import save_single_business, mark_as_scraped, get_profile_by_slug, get_all_profiles
from scraper import scrape_google_maps

scrape_lock = threading.Lock()
stop_scrape_event = threading.Event()

current_scrape_job = {
    "status": "idle",  # idle | running | completed | stopped | error
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


def _run_worker(profile_id: int, state: str, pincodes: list, niches: list, max_scrolls: int):
    global current_scrape_job
    stop_scrape_event.clear()
    total_jobs = len(pincodes) * len(niches)

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

    with scrape_lock:
        current_scrape_job.update({
            "status": "running",
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
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                    '--blink-settings=imagesEnabled=false',
                    '--js-flags=--max-old-space-size=96'
                ]
            )
            context = browser.new_context(
                viewport={'width': 800, 'height': 600},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )

            try:
                for pc in pincodes:
                    if stop_scrape_event.is_set():
                        break
                    for niche in niches:
                        if stop_scrape_event.is_set():
                            break

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
                        except Exception as ex:
                            print(f"[SCRAPER] Error on {niche} in {pc}: {ex}")
                            with scrape_lock:
                                current_scrape_job["error"] = f"{pc} ({niche}): {str(ex)[:150]}"

                        with scrape_lock:
                            current_scrape_job["done_jobs"] += 1

            finally:
                browser.close()

        with scrape_lock:
            current_scrape_job["status"] = "stopped" if stop_scrape_event.is_set() else "completed"
            current_scrape_job["ended_at"] = time.time()

    except Exception as e:
        with scrape_lock:
            current_scrape_job["status"] = "error"
            current_scrape_job["error"] = str(e)
            current_scrape_job["ended_at"] = time.time()


def start_scraping(profile_id: int, state: str, pincodes: list, niches: list, max_scrolls: int = 3) -> dict:
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
        args=(profile_id, state, pincodes, niches, max_scrolls),
        daemon=True
    )
    active_thread.start()
    return {"success": True, "message": f"Scrape job started for {len(pincodes)} pincodes and {len(niches)} niches."}


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
