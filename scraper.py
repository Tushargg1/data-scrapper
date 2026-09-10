"""
Google Maps Playwright scraper.
Searches by niche + pincode and extracts: Name, Rating, Reviews, Phone, Website.
"""
import time
import sys
import asyncio
import re
import os
import random
import subprocess
import json
import pandas as pd
from playwright.sync_api import sync_playwright

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
]

def get_random_user_agent() -> str:
    return random.choice(USER_AGENTS)

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# If running on Render or Linux cloud, ensure browsers path is preserved
if os.path.exists("/opt/render/project/src") and not os.getenv("PLAYWRIGHT_BROWSERS_PATH"):
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/render/project/src/pw-browsers"

_browser_ready = False

def ensure_playwright_installed():
    """Verifies that Chromium can be launched, installing it automatically if missing."""
    global _browser_ready
    if _browser_ready:
        return
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
            )
            b.close()
            _browser_ready = True
            print("[PLAYWRIGHT] Verified Chromium is installed and operational.")
    except Exception as err:
        print(f"[PLAYWRIGHT] Browser missing ({err}). Executing auto-install...")
        try:
            cmd = [sys.executable, "-m", "playwright", "install", "chromium"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            print(f"[PLAYWRIGHT] Auto-install finished with code {res.returncode}: {res.stdout[-200:]} {res.stderr[-200:]}")
            _browser_ready = True
        except Exception as install_err:
            print(f"[PLAYWRIGHT] Auto-install failed: {install_err}")


# ── Resource Blocking — maximise speed & minimise Chromium RAM ────────────────
BLOCKED_RESOURCE_TYPES = {'image', 'media', 'font'}
BLOCKED_URL_SUBSTRINGS = (
    # Analytics / telemetry
    'google-analytics', 'play.google.com/log', 'stats.g.doubleclick',
    'googleads', 'doubleclick.net', 'googlesyndication', 'adservice.google',
    # Fonts
    'fonts.googleapis', 'fonts.gstatic',
    # Crash-reporting / background sync
    'crashlytics', 'sentry.io', 'bugsnag', 'newrelic',
    # Social pixels
    'facebook.net', 'twitter.com/i/adsct', 'linkedin.com/px',
    # Misc trackers
    'fls-na.amazon', 'amazon-adsystem', 'adsystem',
)

def _block_unneeded_resources(route):
    """Block images, fonts, stylesheets, media, trackers & analytics for maximum speed & lowest RAM."""
    req = route.request
    url = req.url
    if req.resource_type in BLOCKED_RESOURCE_TYPES or any(b in url for b in BLOCKED_URL_SUBSTRINGS):
        try:
            route.abort()
        except Exception:
            pass
    else:
        try:
            route.continue_()
        except Exception:
            pass



def _parse_tbm_map_text(text: str) -> list:
    """Parse Google Maps internal tbm=map search response in real-time."""
    if text.startswith(")]}'"):
        text = text[4:].strip()
    elif "/*-secure-" in text:
        text = text.split("\n", 1)[1].strip()

    try:
        data = json.loads(text)
    except Exception:
        return []

    discovered = []
    seen = set()

    def scan(obj):
        if isinstance(obj, list):
            if len(obj) > 18 and isinstance(obj[11], str) and isinstance(obj[18], str) and len(obj[11]) > 2:
                name = obj[11]
                addr = obj[18]
                if name not in seen:
                    seen.add(name)
                    s = json.dumps(obj)

                    # Phone extraction & 10-digit normalization
                    phones = re.findall(r'\"tel\:([^\"]+)\"', s)
                    p1 = phones[0].replace("phone:tel:", "").strip() if phones else "N/A"
                    p2 = phones[1].replace("phone:tel:", "").strip() if len(phones) > 1 and phones[1] != p1 else ""
                    if p1 == "N/A":
                        pm = re.findall(r'\"(\+?91[\d\s\-]{8,14}|011[\d\s\-]{7,12}|0[6-9]\d{9})\"', s)
                        if pm: p1 = pm[0].strip()

                    digits1 = re.sub(r'\D', '', p1)
                    if len(digits1) == 10 and digits1[0] in '6789':
                        p1 = '+91' + digits1
                    elif len(digits1) == 11 and digits1.startswith('0'):
                        p1 = '+91' + digits1[1:]

                    if p2:
                        digits2 = re.sub(r'\D', '', p2)
                        if digits2[-10:] == digits1[-10:]:
                            p2 = ""

                    # Website (Google Maps canonical website is at obj[7][0])
                    web = "N/A"
                    if len(obj) > 7 and isinstance(obj[7], list) and len(obj[7]) > 0 and isinstance(obj[7][0], str):
                        cand = obj[7][0].strip()
                        if cand.startswith("http"):
                            cand_lower = cand.lower()
                            if not any(bad in cand_lower for bad in ["google.", "gstatic.", "ggpht.", "schema.org", "googleusercontent."]):
                                web = cand

                    # Rating & Reviews
                    rating = "N/A"
                    reviews = "N/A"
                    if len(obj) > 4 and isinstance(obj[4], list):
                        if len(obj[4]) > 7 and obj[4][7] is not None:
                            rating = str(obj[4][7])
                        if len(obj[4]) > 8 and obj[4][8] is not None:
                            reviews = str(obj[4][8])

                    # Maps URL (Direct Google Maps link with hex ID or universal query)
                    hexes = re.findall(r'0x[0-9a-fA-F]+:0x[0-9a-fA-F]+', s)
                    if hexes:
                        clean_name = re.sub(r'[^\w\s\-\.]', '', name).strip()
                        maps_url = f"https://www.google.com/maps/place/{clean_name.replace(' ', '+')}/data=!4m2!3m1!1s{hexes[0]}"
                    else:
                        clean_target = f"{name}, {addr}".strip(", ")
                        clean_target = re.sub(r'[^\w\s\-\.,]', '', clean_target)
                        maps_url = f"https://www.google.com/maps/search/?api=1&query={clean_target.replace(' ', '+')}"

                    discovered.append({
                        "Name": name,
                        "Rating": rating,
                        "Reviews": reviews,
                        "Phone": p1,
                        "Phone 1": p1,
                        "Phone 2": p2,
                        "Phone 3": "",
                        "Website Available?": "Yes" if web != "N/A" else "No",
                        "Website Link": web,
                        "Address": addr,
                        "Google Maps URL": maps_url
                    })
            for item in obj:
                scan(item)
        elif isinstance(obj, dict):
            for v in obj.values():
                scan(v)

    scan(data)
    return discovered


def scrape_google_maps(niche: str, pincode: str, max_scrolls: int = 5, on_item_scraped=None, should_stop=None, context=None, profile_id: int = 1) -> pd.DataFrame:
    """
    Hyper-speed Google Maps scraper:
    - Intercepts Google's internal structured RPC responses (search?tbm=map) directly in memory.
    - Yields complete places (Name, Phone, Website, Rating, Reviews, Address) in under 2 seconds.
    - Zero separate detail page visits needed for intercepted places.
    - Full fallback to DOM scraping if RPC interception is unavailable.
    """
    ensure_playwright_installed()

    query = f"{niche} in {pincode}"
    url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"

    results = []
    seen_names = set()

    def _execute(ctx):
        page = ctx.new_page()
        page.route('**/*', _block_unneeded_resources)

        # ── 1. Intercept internal Google Maps data payloads ──────────────
        def _on_response(resp):
            if resp.status == 429:
                print(f"[SCRAPER] ⚠️ Google Maps returned HTTP 429 (Too Many Requests). Pausing for 45s...")
                time.sleep(45)
            elif "search?tbm=map" in resp.url and resp.status == 200:
                try:
                    txt = resp.text()
                    batch = _parse_tbm_map_text(txt)
                    for item in batch:
                        key = item["Name"].lower()
                        if key not in seen_names:
                            seen_names.add(key)
                            results.append(item)
                            if on_item_scraped:
                                on_item_scraped(item)
                except Exception:
                    pass

        page.on("response", _on_response)

        try:
            # Pre-set consent cookies to avoid any popup or consent redirect
            try:
                ctx.add_cookies([
                    {'name': 'SOCS', 'value': 'CAESHAgBEhJnd3NfMjAyNDA2MTAtMF9SQzIaAmVuIAEaBgiA_L20Bg', 'domain': '.google.com', 'path': '/'},
                    {'name': 'CONSENT', 'value': 'PENDING+987', 'domain': '.google.com', 'path': '/'}
                ])
            except Exception:
                pass

            page.goto(url, timeout=18000, wait_until="domcontentloaded")

            # Check for Google rate limits, CAPTCHA, or sorry/index redirects
            curr_url = page.url or ""
            if "sorry/index" in curr_url or "google.com/sorry" in curr_url:
                print(f"[SCRAPER] ⚠️ Google Maps CAPTCHA/Rate limit detected ({curr_url}). Auto-pausing 45 seconds to let block clear...")
                time.sleep(45)
                try:
                    page.goto(url, timeout=20000, wait_until="domcontentloaded")
                except Exception:
                    pass

            # Fast wait for results or feed (max 1.5s)
            feed = page.locator('div[role="feed"]')
            for _ in range(15):
                if results or feed.count() > 0:
                    break
                page.wait_for_timeout(100)

            # Fast auto-scroll to trigger pagination RPCs
            scroll_limit = max(1, min(max_scrolls, 3))
            last_count = len(results)
            stagnant = 0

            for _ in range(scroll_limit):
                if should_stop and should_stop():
                    break

                if feed.count() > 0:
                    try:
                        feed.evaluate('el => el.scrollTop = el.scrollHeight')
                    except Exception:
                        page.mouse.wheel(0, 6000)

                page.wait_for_timeout(200)

                if len(results) == last_count:
                    stagnant += 1
                    if stagnant >= 2:
                        break
                else:
                    stagnant = 0
                    last_count = len(results)

            if results:
                try:
                    print(f"[SCRAPER] [HYPER-SPEED] Captured {len(results)} places via RPC for '{query}'")
                except Exception:
                    pass
                try: page.close()
                except Exception: pass
                return pd.DataFrame(results)

            # ── 3. Fallback: DOM extraction if RPC was missed ────────────────
            link_locators = page.locator('a[href*="https://www.google.com/maps/place/"]').all()
            places_to_extract = []

            for link_el in link_locators:
                try:
                    name = link_el.get_attribute('aria-label')
                    href = link_el.get_attribute('href')
                    if name and href and name.lower() not in seen_names:
                        seen_names.add(name.lower())
                        places_to_extract.append((name, href))
                except Exception:
                    continue

            page.close()
            import gc
            gc.collect()

            if not places_to_extract:
                return pd.DataFrame()

            detail_page = ctx.new_page()
            detail_page.route('**/*', _block_unneeded_resources)

            for idx, (name, href) in enumerate(places_to_extract):
                if should_stop and should_stop():
                    break

                phone_1, phone_2, phone_3 = "N/A", "", ""
                website, website_link = "No", "N/A"
                rating, reviews = "N/A", "N/A"

                try:
                    detail_page.goto(href, wait_until='domcontentloaded', timeout=10000)
                    try:
                        detail_page.locator('[data-item-id^="phone:tel:"], a[data-item-id="authority"], div[role="main"]').first.wait_for(timeout=1500)
                    except Exception:
                        pass

                    # Extract Phone numbers (deduplicated by 10 digits)
                    phones = []
                    seen_phone_digits = set()

                    def _add_phone(candidate: str):
                        cand_clean = candidate.strip()
                        raw_digits = re.sub(r'\D', '', cand_clean)
                        sig = raw_digits[-10:] if len(raw_digits) >= 10 else raw_digits
                        if len(sig) >= 7 and sig not in seen_phone_digits:
                            seen_phone_digits.add(sig)
                            if len(raw_digits) == 10 and raw_digits[0] in '6789':
                                phones.append('+91' + raw_digits)
                            else:
                                phones.append(cand_clean)

                    try:
                        p_els = detail_page.locator('[data-item-id^="phone:tel:"]').all()
                        for p_el in p_els:
                            pid = p_el.get_attribute('data-item-id') or ''
                            num = pid.replace('phone:tel:', '').strip()
                            if num:
                                _add_phone(num)

                        btns = detail_page.locator('button[aria-label*="Phone" i], a[href^="tel:"]').all()
                        for btn in btns:
                            lbl = (btn.get_attribute('aria-label') or '') + ' ' + (btn.get_attribute('href') or '')
                            for m in re.findall(r'[\+\d][\d\s\-\(\)]{7,}', lbl):
                                _add_phone(m)

                        if len(phones) < 3:
                            try:
                                panel_html = detail_page.locator('div[role="main"]').inner_text(timeout=200)
                                for m in re.findall(r'(?:(?:\+91[\s\-]?)?[6-9]\d{4}[\s\-]?\d{5}|0\d{2,4}[\s\-]?\d{6,8})', panel_html):
                                    _add_phone(m)
                            except Exception:
                                pass
                    except Exception:
                        pass

                    phone_1 = phones[0] if len(phones) > 0 else "N/A"
                    phone_2 = phones[1] if len(phones) > 1 else ""
                    phone_3 = phones[2] if len(phones) > 2 else ""

                    # Extract Website
                    try:
                        web_el = detail_page.locator('a[data-item-id="authority"]')
                        if web_el.count() > 0:
                            website = "Yes"
                            website_link = web_el.first.get_attribute('href') or "N/A"
                        else:
                            web_btns = detail_page.locator('a[aria-label*="website" i], a[data-item-id*="authority"]').all()
                            if web_btns:
                                website = "Yes"
                                website_link = web_btns[0].get_attribute('href') or "N/A"
                    except Exception:
                        pass

                    # Extract Rating & Reviews
                    try:
                        star = detail_page.locator('span[aria-label*="star" i]').first
                        if star.count() > 0:
                            lbl = star.get_attribute('aria-label') or ''
                            parts = lbl.split()
                            if parts and parts[0].replace('.', '', 1).isdigit():
                                rating = parts[0]

                        rev_btn = detail_page.locator('button[aria-label*="review" i]').first
                        if rev_btn.count() > 0:
                            rlbl = rev_btn.get_attribute('aria-label') or ''
                            rm = re.search(r'([\d,]+)\s*reviews?', rlbl, re.I)
                            if rm:
                                reviews = rm.group(1)

                        if rating == "N/A" or reviews == "N/A":
                            panel_text = detail_page.locator('div[role="main"]').inner_text(timeout=200)
                            for line in panel_text.split('\n'):
                                line = line.strip()
                                if '(' in line and ')' in line and rating == "N/A":
                                    prefix = line.split('(')[0].strip()
                                    if prefix.replace('.', '', 1).isdigit():
                                        rating = prefix
                                        reviews = line.split('(')[1].replace(')', '').strip()
                                        break
                    except Exception:
                        pass

                except Exception:
                    pass

                item = {
                    "Name": name,
                    "Rating": rating,
                    "Reviews": reviews,
                    "Phone": phone_1,
                    "Phone 1": phone_1,
                    "Phone 2": phone_2,
                    "Phone 3": phone_3,
                    "Website Available?": website,
                    "Website Link": website_link,
                    "Google Maps URL": href
                }
                results.append(item)
                if on_item_scraped:
                    on_item_scraped(item)

            detail_page.close()
            gc.collect()

        except Exception as e:
            print(f"[SCRAPER] Error in query '{query}': {e}")
            try: page.close()
            except Exception: pass

        return pd.DataFrame(results)

    if context is not None:
        return _execute(context)
    else:
        with sync_playwright() as p:
            browser = p.chromium.launch(
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
                    # Kill background activity that wastes RAM
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
            ctx = browser.new_context(
                viewport={'width': 800, 'height': 600},
                user_agent=get_random_user_agent()
            )
            try:
                return _execute(ctx)
            finally:
                browser.close()

