"""
Phone Enrichment Engine
Searches Google Search, JustDial, and Web Directories to find phone numbers
for businesses that have no number on Google Maps.
"""
import re
import gc
import time
import threading
from datetime import datetime

# -- Phone Number Normalization ------------------------------------------------
def _normalize_phone(raw: str) -> str:
    """Normalize extracted digits into clean Indian format: +91XXXXXXXXXX"""
    digits = re.sub(r'\D', '', raw)
    if len(digits) == 12 and digits.startswith('91'):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith('0'):
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in '6789':
        return '+91' + digits
    if len(digits) >= 10:
        return '+91' + digits[-10:]
    return ''


def _clean_for_search(text: str) -> str:
    """Clean query string for search engine."""
    return re.sub(r'[^\w\s]', ' ', text).strip()


# -- Contextual Phone Extraction from HTML --------------------------------------
def extract_phone_from_html(html: str) -> str | None:
    """
    Extracts authentic Indian business phone numbers from page HTML.
    Uses contextual proximity to keywords (appointment, call, phone, etc.)
    and structured attributes to avoid false positives.
    """
    # 1. Direct tel: links
    tel_matches = re.findall(r'href=[\"\']tel:([^\"\']+)[\"\']', html, re.I)
    for m in tel_matches:
        norm = _normalize_phone(m)
        if norm:
            return norm

    # 2. Number in brackets/quotes often found in business descriptions: e.g. [+91 70118 52232]
    bracket_matches = re.findall(r'\[(?:\+91[\s\-]?)?(?:0)?[6-9]\d{4}[\s\-]?\d{5}\]', html)
    for m in bracket_matches:
        norm = _normalize_phone(m)
        if norm:
            return norm

    # 3. Contextual proximity: phone number within 60 chars of contact keywords
    keywords = [
        "phone", "tel", "call", "contact", "mobile",
        "appointment", "book", "karein", "whatsapp", "inquiry"
    ]
    kw_pattern = "|".join(keywords)
    phone_re = r'((?:\+91[\s\-]?)?(?:0)?[6-9]\d{4}[\s\-]?\d{5}|011[\s\-]?\d{7,8})'
    pattern = rf'(?:{kw_pattern})[\s\:\-\w\"\'\,\.\[\]]{{0,60}}{phone_re}'
    
    near_matches = re.findall(pattern, html, re.I)
    for m in near_matches:
        norm = _normalize_phone(m)
        if norm:
            return norm

    # 4. Standard phone pattern in the text body
    clean_text = re.sub(r'<[^>]+>', ' ', html)
    generic = re.findall(r'(?:\+91[\s\-]?)?0?[6-9]\d{4}[\s\-]?\d{5}', clean_text)
    for g in generic:
        norm = _normalize_phone(g)
        if norm:
            return norm

    return None


# -- Global Enrichment State ---------------------------------------------------
_enrich_lock = threading.Lock()
_enrich_state = {
    "status": "idle",          # idle | running | stopped | completed | error
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


# -- Stealth Search Functions ---------------------------------------------------

async def _search_google_phone(page, name: str, pincode: str, state: str) -> str | None:
    """Stealth Google Search for the business name + pincode."""
    try:
        clean_name = _clean_for_search(name)
        q = f"{clean_name} {pincode} {state} phone number"
        url = f"https://www.google.com/search?q={q.replace(' ', '+')}&hl=en"

        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1500)

        # Check DOM structured elements first
        for sel in ["[data-dtype='d3ph']", "[data-local-attribute='d3ph']", ".LrzXr", "a[href^='tel:']"]:
            try:
                el = await page.query_selector(sel)
                if el:
                    txt = await el.inner_text()
                    phone = _normalize_phone(txt)
                    if phone:
                        return phone
            except Exception:
                pass

        # Check full raw HTML for contextual appointment / description numbers
        html = await page.content()
        return extract_phone_from_html(html)

    except Exception as e:
        print(f"[ENRICH] Google search error for {name}: {e}")
    return None


async def _search_justdial_phone(page, name: str, pincode: str, state: str) -> str | None:
    """Search Google with site:justdial.com to extract JustDial listing phone."""
    try:
        clean_name = _clean_for_search(name)
        q = f"site:justdial.com {clean_name} {pincode}"
        url = f"https://www.google.com/search?q={q.replace(' ', '+')}&hl=en"

        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1000)

        html = await page.content()
        return extract_phone_from_html(html)

    except Exception as e:
        print(f"[ENRICH] JustDial search error for {name}: {e}")
    return None


# -- Background Worker ---------------------------------------------------------

def run_phone_enrichment(profile_id: int, business_ids: list = None):
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
                    "--disable-blink-features=AutomationControlled",
                    "--blink-settings=imagesEnabled=false",
                    "--js-flags=--max-old-space-size=96",
                ]
            )
            ctx = await browser.new_context(
                viewport={"width": 800, "height": 600},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="en-IN",
            )
            page = await ctx.new_page()
            # Mask navigator.webdriver
            await page.add_init_script("delete Object.getPrototypeOf(navigator).webdriver;")

            # Block heavy assets to save CPU & RAM
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

                    # 1. Google Stealth Search
                    with _enrich_lock:
                        _enrich_state["current_source"] = "Google"
                    found_phone = await _search_google_phone(page, biz_name, pincode, state)
                    if found_phone:
                        source = "Google"

                    # 2. JustDial Google Search
                    if not found_phone and not _stop_enrich_event.is_set():
                        with _enrich_lock:
                            _enrich_state["current_source"] = "JustDial"
                        found_phone = await _search_justdial_phone(page, biz_name, pincode, state)
                        if found_phone:
                            source = "JustDial"

                    # Save to DB immediately
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

                        print(f"[ENRICH] [OK] {biz_name} -> {found_phone} (via {source})")
                    else:
                        print(f"[ENRICH] [MISS] {biz_name} -> no number found")

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


def start_enrichment_thread(profile_id: int, business_ids: list = None):
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
