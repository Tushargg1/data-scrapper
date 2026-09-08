"""
Phone Enrichment Engine
Searches Google Search, JustDial, and Sulekha to find phone numbers
for businesses that have no number on Google Maps.
"""
import re
import gc
import time
import threading
from datetime import datetime

# -- Indian phone number patterns -----------------------------------------------
_PHONE_RE = re.compile(
    r"""(?:
        (?:\+91[\s\-]?)?
        (?:0)?
        [6-9]\d{9}
    |
        (?:\+91[\s\-]?)?
        0?1[1-9]\d{8}
    |
        \+91[\s\-]\d{2,5}[\s\-]\d{3,8}
    )""",
    re.VERBOSE
)

def _extract_indian_phones(text: str) -> list:
    raw = _PHONE_RE.findall(text)
    cleaned = []
    seen = set()
    for p in raw:
        digits = re.sub(r'\D', '', p)
        if len(digits) == 12 and digits.startswith('91'):
            digits = digits[2:]
        elif len(digits) == 11 and digits.startswith('0'):
            digits = digits[1:]
        if len(digits) == 10 and digits not in seen:
            seen.add(digits)
            cleaned.append('+91' + digits)
    return cleaned


def _clean_for_search(text: str) -> str:
    return re.sub(r'[^\w\s]', ' ', text).strip()


# -- Global enrichment state ---------------------------------------------------
_enrich_lock = threading.Lock()
_enrich_state = {
    "status": "idle",
    "profile_id": None,
    "total": 0,
    "done": 0,
    "found": 0,
    "current_name": "",
    "current_source": "",
    "started_at": None,
    "ended_at": None,
    "recent_found": [],
    "error": None,
}
_stop_enrich_event = threading.Event()
_enrich_thread = None


def get_enrich_status() -> dict:
    with _enrich_lock:
        s = dict(_enrich_state)
    s["progress_percent"] = round(100 * s["done"] / s["total"], 1) if s["total"] > 0 else 0
    if s["started_at"]:
        s["elapsed_seconds"] = round(time.time() - s["started_at"])
    else:
        s["elapsed_seconds"] = 0
    return s


def stop_enrichment():
    _stop_enrich_event.set()


def is_enrichment_running() -> bool:
    global _enrich_thread
    return _enrich_thread is not None and _enrich_thread.is_alive()


# -- Core search functions -----------------------------------------------------

async def _search_google_phone(page, name, pincode, state):
    try:
        query = _clean_for_search(name) + " " + pincode + " phone number"
        url = "https://www.google.com/search?q=" + query.replace(' ', '+') + "&hl=en"
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1000)
        text = await page.inner_text("body")
        phones = _extract_indian_phones(text)
        if phones:
            return phones[0]
        for selector in ["[data-dtype='d3ph']", ".LrzXr", "a[href^='tel:']"]:
            try:
                el = await page.query_selector(selector)
                if el:
                    t = await el.inner_text()
                    phones = _extract_indian_phones(t)
                    if phones:
                        return phones[0]
            except Exception:
                pass
    except Exception as e:
        print(f"[ENRICH] Google error for {name}: {e}")
    return None


async def _search_justdial_phone(page, name, pincode, state):
    try:
        clean_name = _clean_for_search(name)
        query = "site:justdial.com " + clean_name + " " + pincode
        url = "https://www.google.com/search?q=" + query.replace(' ', '+') + "&hl=en"
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(800)
        jd_links = await page.query_selector_all("a[href*='justdial.com']")
        if not jd_links:
            return None
        href = await jd_links[0].get_attribute("href")
        if not href or "justdial.com" not in href:
            return None
        await page.goto(href, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1200)
        text = await page.inner_text("body")
        phones = _extract_indian_phones(text)
        if phones:
            return phones[0]
    except Exception as e:
        print(f"[ENRICH] JustDial error for {name}: {e}")
    return None


async def _search_sulekha_phone(page, name, pincode, state):
    try:
        clean_name = _clean_for_search(name)
        query = "site:sulekha.com " + clean_name + " " + state + " phone"
        url = "https://www.google.com/search?q=" + query.replace(' ', '+') + "&hl=en"
        await page.goto(url, wait_until="domcontentloaded", timeout=12000)
        await page.wait_for_timeout(700)
        sul_links = await page.query_selector_all("a[href*='sulekha.com']")
        if not sul_links:
            return None
        href = await sul_links[0].get_attribute("href")
        if not href:
            return None
        await page.goto(href, wait_until="domcontentloaded", timeout=12000)
        await page.wait_for_timeout(1000)
        text = await page.inner_text("body")
        phones = _extract_indian_phones(text)
        if phones:
            return phones[0]
    except Exception as e:
        print(f"[ENRICH] Sulekha error for {name}: {e}")
    return None


# -- Main enrichment runner ----------------------------------------------------

def run_phone_enrichment(profile_id, business_ids=None):
    import asyncio
    from playwright.async_api import async_playwright
    from database import get_businesses_without_phone, update_business_phone

    global _enrich_thread
    _stop_enrich_event.clear()

    businesses = get_businesses_without_phone(profile_id)
    if business_ids:
        id_set = set(business_ids)
        businesses = [b for b in businesses if b["id"] in id_set]

    with _enrich_lock:
        _enrich_state.update({
            "status": "running",
            "profile_id": profile_id,
            "total": len(businesses),
            "done": 0,
            "found": 0,
            "current_name": "",
            "current_source": "",
            "started_at": time.time(),
            "ended_at": None,
            "recent_found": [],
            "error": None,
        })

    if not businesses:
        with _enrich_lock:
            _enrich_state["status"] = "completed"
            _enrich_state["ended_at"] = time.time()
        return

    async def _run():
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--disable-extensions",
                    "--disable-background-networking",
                    "--blink-settings=imagesEnabled=false",
                    "--js-flags=--max-old-space-size=96",
                ]
            )
            ctx = await browser.new_context(
                viewport={"width": 800, "height": 600},
                user_agent=(
                    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
                ),
                locale="en-IN",
            )
            page = await ctx.new_page()
            await page.route("**/*", lambda route: (
                route.abort()
                if route.request.resource_type in ("image", "media", "font", "stylesheet")
                else route.continue_()
            ))

            try:
                for biz in businesses:
                    if _stop_enrich_event.is_set():
                        break

                    biz_id   = biz["id"]
                    biz_name = biz.get("name", "")
                    pincode  = biz.get("pincode", "")
                    state    = biz.get("state", "")
                    existing_phone = biz.get("phone", "") or ""

                    with _enrich_lock:
                        _enrich_state["current_name"] = biz_name

                    found_phone = None
                    source = None

                    # 1) Google
                    with _enrich_lock:
                        _enrich_state["current_source"] = "Google"
                    found_phone = await _search_google_phone(page, biz_name, pincode, state)
                    if found_phone:
                        source = "Google"

                    # 2) JustDial
                    if not found_phone and not _stop_enrich_event.is_set():
                        with _enrich_lock:
                            _enrich_state["current_source"] = "JustDial"
                        found_phone = await _search_justdial_phone(page, biz_name, pincode, state)
                        if found_phone:
                            source = "JustDial"

                    # 3) Sulekha
                    if not found_phone and not _stop_enrich_event.is_set():
                        with _enrich_lock:
                            _enrich_state["current_source"] = "Sulekha"
                        found_phone = await _search_sulekha_phone(page, biz_name, pincode, state)
                        if found_phone:
                            source = "Sulekha"

                    # Save to DB
                    if found_phone:
                        if not existing_phone or existing_phone in ("N/A", ""):
                            update_business_phone(biz_id, phone=found_phone, phone_2=None)
                        else:
                            update_business_phone(biz_id, phone=None, phone_2=found_phone)

                        with _enrich_lock:
                            _enrich_state["found"] += 1
                            recent = _enrich_state["recent_found"]
                            recent.insert(0, {
                                "name": biz_name,
                                "phone": found_phone,
                                "source": source,
                                "pincode": pincode,
                            })
                            _enrich_state["recent_found"] = recent[:15]

                        print(f"[ENRICH] {biz_name} -> {found_phone} (via {source})")
                    else:
                        print(f"[ENRICH] No number found for: {biz_name}")

                    with _enrich_lock:
                        _enrich_state["done"] += 1

                    gc.collect()

            finally:
                await browser.close()

        with _enrich_lock:
            if _stop_enrich_event.is_set():
                _enrich_state["status"] = "stopped"
            else:
                _enrich_state["status"] = "completed"
            _enrich_state["ended_at"] = time.time()
            _enrich_state["current_name"] = ""
            _enrich_state["current_source"] = ""

    try:
        asyncio.run(_run())
    except Exception as e:
        with _enrich_lock:
            _enrich_state["status"] = "error"
            _enrich_state["error"] = str(e)
            _enrich_state["ended_at"] = time.time()
        print(f"[ENRICH] Fatal error: {e}")


def start_enrichment_thread(profile_id, business_ids=None):
    global _enrich_thread
    if is_enrichment_running():
        return "Enrichment already running."
    _enrich_thread = threading.Thread(
        target=run_phone_enrichment,
        args=(profile_id, business_ids),
        daemon=True,
    )
    _enrich_thread.start()
    return None
