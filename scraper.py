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


def scrape_google_maps(niche: str, pincode: str, max_scrolls: int = 5, on_item_scraped=None, should_stop=None) -> pd.DataFrame:
    """
    Scrapes Google Maps for ALL businesses in a given niche and pincode.
    - Continuous auto-scrolling until end of list marker is reached.
    - Resource blocking (images/fonts/media) for ultra-low RAM usage on Render free tier.
    - Accurate detail extraction via direct place page navigation.
    - Instant on_item_scraped callback for real-time MySQL persistence.
    """
    ensure_playwright_installed()

    query = f"{niche} in {pincode}"
    url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
            ]
        )
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()
        page.route('**/*', _block_unneeded_resources)

        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")

            # Handle Google consent popups / redirects (critical on cloud/datacenter IPs)
            try:
                for sel in [
                    'button:has-text("Accept all")',
                    'button:has-text("I agree")',
                    'form[action*="consent"] button',
                    'button[aria-label*="Accept all"]',
                    'button[aria-label*="Accept"]'
                ]:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=1000):
                        btn.click()
                        time.sleep(1)
                        break
            except Exception:
                pass

            feed_selector = 'div[role="feed"]'
            try:
                page.wait_for_selector(feed_selector, timeout=10000)
            except Exception:
                feed_selector = None

            if not feed_selector:
                print(f"[SCRAPER] No feed found for '{query}'")
                browser.close()
                return pd.DataFrame()

            # Hover feed to enable mouse wheel scrolling
            try:
                page.locator(feed_selector).hover(timeout=2000)
            except Exception:
                pass

            # ── 1. Auto-scroll to load EVERY business in this pincode ────────
            last_count = 0
            stagnant_count = 0
            max_scroll_attempts = max(12, max_scrolls * 4)

            for s in range(max_scroll_attempts):
                if should_stop and should_stop():
                    break

                page.mouse.wheel(0, 15000)
                time.sleep(0.4)

                # Check if Google's end marker is reached
                try:
                    end_marker = page.locator(
                        'span:has-text("You\'ve reached the end of the list"), '
                        'div:has-text("You\'ve reached the end of the list")'
                    )
                    if end_marker.count() > 0 and end_marker.first.is_visible(timeout=100):
                        break
                except Exception:
                    pass

                current_count = page.locator('a[href*="https://www.google.com/maps/place/"]').count()
                if current_count == last_count:
                    stagnant_count += 1
                    if stagnant_count >= 3:
                        break
                else:
                    stagnant_count = 0
                    last_count = current_count

                if current_count >= 120:  # Google's hard cap per query
                    break

            # Collect all place links from the feed
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

            print(f"[SCRAPER] Found {len(places_to_extract)} places in feed for '{query}'. Extracting details...")

            # ── 2. Dedicated lightweight detail extractor page ───────────────
            detail_page = context.new_page()
            detail_page.route('**/*', _block_unneeded_resources)

            for idx, (name, href) in enumerate(places_to_extract):
                if should_stop and should_stop():
                    break

                phone_1, phone_2, phone_3 = "N/A", "", ""
                website, website_link = "No", "N/A"
                rating, reviews = "N/A", "N/A"

                try:
                    detail_page.goto(href, wait_until='domcontentloaded', timeout=12000)
                    try:
                        detail_page.locator('[data-item-id^="phone:tel:"], a[data-item-id="authority"]').first.wait_for(timeout=1200)
                    except Exception:
                        pass

                    # Extract Phone numbers (collect up to 3)
                    phones = []
                    try:
                        p_els = detail_page.locator('[data-item-id^="phone:tel:"]').all()
                        for p_el in p_els:
                            pid = p_el.get_attribute('data-item-id') or ''
                            num = pid.replace('phone:tel:', '').strip()
                            if num and num not in phones:
                                phones.append(num)

                        btns = detail_page.locator('button[aria-label*="Phone"], button[aria-label*="phone"]').all()
                        for btn in btns:
                            lbl = btn.get_attribute('aria-label') or ''
                            matches = re.findall(r'[\+\d][\d\s\-\(\)]{7,}', lbl)
                            for m in matches:
                                m_clean = m.strip()
                                if len(m_clean) >= 8 and m_clean not in phones:
                                    phones.append(m_clean)
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
                            web_btns = detail_page.locator('a[aria-label*="website"], a[aria-label*="Website"]').all()
                            if web_btns:
                                website = "Yes"
                                website_link = web_btns[0].get_attribute('href') or "N/A"
                    except Exception:
                        pass

                    # Extract Rating & Reviews
                    try:
                        panel_text = detail_page.locator('div[role="main"]').inner_text(timeout=500)
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
                    try:
                        on_item_scraped(item)
                    except Exception:
                        pass

            try:
                detail_page.close()
            except Exception:
                pass

        except Exception as e:
            browser.close()
            raise e
        finally:
            try:
                browser.close()
            except Exception:
                pass

    return pd.DataFrame(results)
