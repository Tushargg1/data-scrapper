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


def scrape_google_maps(niche: str, pincode: str, max_scrolls: int = 3, on_item_scraped=None) -> pd.DataFrame:
    """
    Scrapes Google Maps for a given niche and pincode.
    Returns a Pandas DataFrame with detailed business info.
    Executes on_item_scraped(item_dict) immediately for every business found.
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
                '--single-process',
                '--no-zygote'
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

        try:
            page.goto(url, timeout=35000, wait_until="domcontentloaded")

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
                    if btn.is_visible(timeout=1500):
                        btn.click()
                        time.sleep(1.5)
                        break
            except Exception:
                pass

            feed_selector = 'div[role="feed"]'
            try:
                page.wait_for_selector(feed_selector, timeout=12000)
            except Exception:
                feed_selector = None

            if not feed_selector:
                # Check if search returned 0 results or single place
                print(f"[SCRAPER] No results feed found for '{query}'")
                browser.close()
                return pd.DataFrame()

            # Scroll to load more results
            for _ in range(max_scrolls):
                try:
                    page.locator('div[role="feed"]').hover()
                    page.mouse.wheel(0, 15000)
                    time.sleep(0.8)
                except Exception:
                    break

            # Collect place links from the feed
            link_locators = page.locator('a[href*="https://www.google.com/maps/place/"]').all()
            seen_names = set()

            for link_el in link_locators:
                try:
                    name = link_el.get_attribute('aria-label')
                    href = link_el.get_attribute('href')
                    if not name or not href or name in seen_names:
                        continue
                    seen_names.add(name)

                    rating, reviews, phone, website, website_link = "N/A", "N/A", "N/A", "No", "N/A"

                    # ⚡ FAST-PATH: Click the link directly on the loaded page (NO page.goto!)
                    try:
                        link_el.scroll_into_view_if_needed(timeout=2000)
                        link_el.click(timeout=3000)
                        page.wait_for_selector('h1', timeout=4000)

                        # Extract Rating & Reviews
                        try:
                            panel_text = page.locator('div[role="main"]').inner_text(timeout=2000)
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

                        # Extract Phones — collect up to 3 unique numbers per business
                        phones = []
                        try:
                            p_els = page.locator('[data-item-id^="phone:tel:"]').all()
                            for p_el in p_els:
                                pid = p_el.get_attribute('data-item-id') or ''
                                num = pid.replace('phone:tel:', '').strip()
                                if num and num not in phones:
                                    phones.append(num)

                            btns = page.locator('button[aria-label*="Phone"], button[aria-label*="phone"]').all()
                            for btn in btns:
                                lbl = btn.get_attribute('aria-label') or ''
                                matches = re.findall(r'[\+\d][\d\s\-\(\)]{7,}', lbl)
                                for m in matches:
                                    m_clean = m.strip()
                                    if len(m_clean) >= 8 and m_clean not in phones:
                                        phones.append(m_clean)

                            try:
                                html = page.locator('div[role="main"]').inner_html(timeout=2000)
                                matches = re.findall(r'tel:([\+\d\-\s\(\)]{7,})"', html)
                                for m in matches:
                                    m_clean = m.strip()
                                    if len(m_clean) >= 8 and m_clean not in phones:
                                        phones.append(m_clean)
                            except Exception:
                                pass
                        except Exception:
                            pass

                        phone_1 = phones[0] if len(phones) > 0 else "N/A"
                        phone_2 = phones[1] if len(phones) > 1 else ""
                        phone_3 = phones[2] if len(phones) > 2 else ""

                        # Extract Website
                        try:
                            web_el = page.locator('a[data-item-id="authority"]')
                            if web_el.count() > 0:
                                website = "Yes"
                                website_link = web_el.first.get_attribute('href') or "N/A"
                            else:
                                web_btns = page.locator('a[aria-label*="website"], a[aria-label*="Website"]').all()
                                if web_btns:
                                    website = "Yes"
                                    website_link = web_btns[0].get_attribute('href') or "N/A"
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

                except Exception:
                    continue

        except Exception as e:
            browser.close()
            raise e
        finally:
            try:
                browser.close()
            except Exception:
                pass

    return pd.DataFrame(results)
