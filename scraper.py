"""
Google Maps Playwright scraper.
Searches by niche + pincode and extracts: Name, Rating, Reviews, Phone, Website.
"""
import time
import sys
import asyncio
import re
import os
import subprocess
import pandas as pd
from playwright.sync_api import sync_playwright

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


def _block_unneeded_resources(route):
    """Blocks heavy assets to maintain ultra-low RAM usage (<120MB) and 4x faster page loads."""
    if route.request.resource_type in ['image', 'media', 'font']:
        try:
            route.abort()
        except Exception:
            pass
    else:
        try:
            route.continue_()
        except Exception:
            pass


def scrape_google_maps(niche: str, pincode: str, max_scrolls: int = 5, on_item_scraped=None, should_stop=None, context=None, profile_id: int = 1) -> pd.DataFrame:
    """
    Scrapes Google Maps for ALL businesses in a given niche and pincode.
    - Continuous auto-scrolling with fast stagnation detection.
    - Instant deduplication: businesses already in DB skip detail navigation (0ms vs 2000ms).
    - Resource blocking (images/fonts/media) for ultra-low RAM and network overhead.
    - Reusable Playwright context for zero browser restart overhead.
    """
    ensure_playwright_installed()

    query = f"{niche} in {pincode}"
    url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"

    results = []

    def _execute(ctx):
        page = ctx.new_page()
        page.route('**/*', _block_unneeded_resources)

        try:
            page.goto(url, timeout=25000, wait_until="domcontentloaded")

            # Handle consent popups if any
            try:
                for sel in [
                    'button:has-text("Accept all")',
                    'button:has-text("I agree")',
                    'form[action*="consent"] button',
                    'button[aria-label*="Accept all"]'
                ]:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=500):
                        btn.click()
                        time.sleep(0.5)
                        break
            except Exception:
                pass

            feed_selector = 'div[role="feed"]'
            try:
                page.wait_for_selector(feed_selector, timeout=8000)
            except Exception:
                feed_selector = None

            if not feed_selector:
                print(f"[SCRAPER] No feed found for '{query}'")
                page.close()
                return pd.DataFrame()

            try:
                page.locator(feed_selector).hover(timeout=1500)
            except Exception:
                pass

            # ── 1. Fast auto-scroll ──────────────────────────────────────────
            last_count = 0
            stagnant_count = 0
            max_scroll_attempts = max(10, max_scrolls * 3)

            for s in range(max_scroll_attempts):
                if should_stop and should_stop():
                    break

                page.mouse.wheel(0, 15000)
                time.sleep(0.25)

                try:
                    end_marker = page.locator(
                        'span:has-text("You\'ve reached the end of the list"), '
                        'div:has-text("You\'ve reached the end of the list")'
                    )
                    if end_marker.count() > 0 and end_marker.first.is_visible(timeout=50):
                        break
                except Exception:
                    pass

                current_count = page.locator('a[href*="https://www.google.com/maps/place/"]').count()
                if current_count == last_count:
                    stagnant_count += 1
                    if stagnant_count >= 2:
                        break
                else:
                    stagnant_count = 0
                    last_count = current_count

                if current_count >= 120:
                    break

            link_locators = page.locator('a[href*="https://www.google.com/maps/place/"]').all()
            places_to_extract = []
            seen_names = set()

            for link_el in link_locators:
                try:
                    name = link_el.get_attribute('aria-label')
                    href = link_el.get_attribute('href')
                    if name and href and name not in seen_names:
                        seen_names.add(name)
                        places_to_extract.append((name, href))
                except Exception:
                    continue

            print(f"[SCRAPER] Found {len(places_to_extract)} places for '{query}'")
            page.close()
            import gc
            gc.collect()

            if not places_to_extract:
                return pd.DataFrame()

            # ── 2. Instant Deduplication check against DB ─────────────────────
            from database import get_existing_businesses_by_urls
            all_urls = [h for _, h in places_to_extract]
            existing_by_url = get_existing_businesses_by_urls(profile_id, all_urls)

            new_places = []
            for name, href in places_to_extract:
                if href in existing_by_url:
                    # Already in DB! Emit immediately without costly page load
                    ex = existing_by_url[href]
                    item = {
                        "Name": ex.get("name", name),
                        "Rating": ex.get("rating", "N/A"),
                        "Reviews": ex.get("reviews", "N/A"),
                        "Phone": ex.get("phone", "N/A"),
                        "Phone 1": ex.get("phone", "N/A"),
                        "Phone 2": ex.get("phone_2", ""),
                        "Phone 3": ex.get("phone_3", ""),
                        "Website Available?": ex.get("website_available", "No"),
                        "Website Link": ex.get("website_link", "N/A"),
                        "Google Maps URL": href
                    }
                    results.append(item)
                    if on_item_scraped:
                        on_item_scraped(item)
                else:
                    new_places.append((name, href))

            if existing_by_url:
                print(f"[SCRAPER] Reused {len(existing_by_url)} places already in DB (saved {len(existing_by_url)*1.8:.1f}s). Extracting {len(new_places)} new places...")

            if not new_places:
                return pd.DataFrame(results)

            # ── 3. Extract only genuinely NEW places ─────────────────────────
            detail_page = ctx.new_page()
            detail_page.route('**/*', _block_unneeded_resources)

            for idx, (name, href) in enumerate(new_places):
                if should_stop and should_stop():
                    break

                phone_1, phone_2, phone_3 = "N/A", "", ""
                website, website_link = "No", "N/A"
                rating, reviews = "N/A", "N/A"

                try:
                    detail_page.goto(href, wait_until='domcontentloaded', timeout=10000)
                    try:
                        detail_page.locator('[data-item-id^="phone:tel:"], a[data-item-id="authority"]').first.wait_for(timeout=400)
                    except Exception:
                        pass

                    # Extract Phone numbers (deduplicated by 10 digits to prevent duplicate formats)
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
                    except Exception:
                        pass

                    # Extract Rating & Reviews
                    try:
                        panel_text = detail_page.locator('div[role="main"]').inner_text(timeout=300)
                        for line in panel_text.split('\n'):
                            line = line.strip()
                            if '(' in line and ')' in line:
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
                    '--blink-settings=imagesEnabled=false',
                    '--js-flags=--max-old-space-size=96'
                ]
            )
            ctx = browser.new_context(
                viewport={'width': 800, 'height': 600},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            try:
                return _execute(ctx)
            finally:
                browser.close()
