"""
Google Maps Playwright scraper.
Searches by niche + pincode and extracts: Name, Rating, Reviews, Phone, Website.
"""
import time
import sys
import asyncio
import re
import pandas as pd
from playwright.sync_api import sync_playwright

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def scrape_google_maps(niche: str, pincode: str, max_scrolls: int = 3) -> pd.DataFrame:
    """
    Scrapes Google Maps for a given niche and pincode.
    Returns a Pandas DataFrame with detailed business info.
    """
    query = f"{niche} in {pincode}"
    url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
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
            page.goto(url, timeout=30000)
            feed_selector = 'div[role="feed"]'

            try:
                page.wait_for_selector(feed_selector, timeout=12000)
            except Exception:
                # No results page (e.g. pincode has no matches)
                browser.close()
                return pd.DataFrame()

            # Scroll to load more results
            for _ in range(max_scrolls):
                page.locator(feed_selector).hover()
                page.mouse.wheel(0, 15000)
                time.sleep(1.8)

            # Collect place links + names from the feed
            links = page.locator('a[href*="https://www.google.com/maps/place/"]').all()
            places = []
            seen = set()
            for link in links:
                try:
                    name = link.get_attribute('aria-label')
                    href = link.get_attribute('href')
                    if name and href and name not in seen:
                        places.append((name, href))
                        seen.add(name)
                except Exception:
                    pass

            # Visit each place detail page
            for name, href in places:
                rating, reviews, phone, website, website_link = "N/A", "N/A", "N/A", "No", "N/A"
                try:
                    page.goto(href, timeout=15000)
                    page.wait_for_selector('h1', timeout=8000)

                    # Rating & Reviews
                    try:
                        panel_text = page.locator('div[role="main"]').inner_text(timeout=4000)
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

                    # Phone — via aria-label on buttons
                    try:
                        btns = page.locator('button').all()
                        for btn in btns:
                            lbl = btn.get_attribute('aria-label') or ''
                            if 'phone' in lbl.lower() or re.search(r'\+?\d[\d\s\-]{7,}', lbl):
                                # Extract digits
                                num = re.search(r'[\+\d][\d\s\-\(\)]{7,}', lbl)
                                if num:
                                    phone = num.group(0).strip()
                                    break
                    except Exception:
                        pass

                    # Fallback phone via HTML regex
                    if phone == "N/A":
                        try:
                            html = page.content()
                            # Find tel: links
                            match = re.search(r'tel:([\+\d\-\s\(\)]{7,})"', html)
                            if match:
                                phone = match.group(1).strip()
                        except Exception:
                            pass

                    # Website
                    try:
                        web_el = page.locator('a[data-item-id="authority"]')
                        if web_el.count() > 0:
                            website = "Yes"
                            website_link = web_el.first.get_attribute('href') or "N/A"
                        else:
                            # Fallback: look for aria-label containing "website"
                            all_links = page.locator('a').all()
                            for lnk in all_links:
                                lbl = lnk.get_attribute('aria-label') or ''
                                if 'website' in lbl.lower():
                                    website = "Yes"
                                    website_link = lnk.get_attribute('href') or "N/A"
                                    break
                    except Exception:
                        pass

                except Exception:
                    pass

                results.append({
                    "Name": name,
                    "Rating": rating,
                    "Reviews": reviews,
                    "Phone": phone,
                    "Website Available?": website,
                    "Website Link": website_link,
                    "Google Maps URL": href
                })

        except Exception as e:
            browser.close()
            raise e
        finally:
            try:
                browser.close()
            except Exception:
                pass

    return pd.DataFrame(results)
