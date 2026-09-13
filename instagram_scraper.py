import time
import asyncio
import re
import pandas as pd
from playwright.sync_api import sync_playwright

def scrape_instagram(niche: str, pincode: str, max_scrolls: int = 5, on_item_scraped=None, should_stop=None, context=None, profile_id: int = 1) -> pd.DataFrame:
    """
    Instagram Scraper
    Searches Instagram profiles via Google (site:instagram.com) since native IG search requires login.
    Extracts bio snippets, website availability, and contact numbers if listed in bio.
    """
    if context is None:
        raise ValueError("Playwright context required for Instagram scraper")
    
    page = context.new_page()
    items = []
    
    try:
        # Search via Google using site: operator
        query = f"site:instagram.com {niche} {pincode}".replace(" ", "+")
        url = f"https://www.google.com/search?q={query}"
        
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)
        
        scrolls = 0
        while scrolls < max_scrolls:
            if should_stop and should_stop():
                break
            page.evaluate("window.scrollBy(0, 1000);")
            time.sleep(1)
            scrolls += 1
            
        # Parse Google SERP results for Instagram
        results = page.locator("div.g").all()
        for i, res in enumerate(results):
            if should_stop and should_stop():
                break
            try:
                title_el = res.locator("h3").first
                if not title_el.is_visible():
                    continue
                name = title_el.inner_text().strip()
                name = name.replace(" - Instagram", "").strip()
                name = name.split("(@")[0].strip() # Clean IG handles
                
                snippet_el = res.locator(".VwiC3b").first
                snippet = snippet_el.inner_text().strip() if snippet_el.is_visible() else ""
                
                # Check for contact numbers in bio snippet
                phone = "N/A"
                phone_match = re.search(r'(?:\\+91|0)?[-\s]?\\d{4,5}[-\s]?\\d{5,6}', snippet)
                if phone_match:
                    phone = phone_match.group(0).strip()
                    
                # Check for links/contact references in snippet
                has_contact_link = "linktr.ee" in snippet.lower() or "wa.me" in snippet.lower() or "website" in snippet.lower()
                website_avail = "Yes" if has_contact_link else "No"
                
                # Get the actual IG profile link
                link_el = res.locator("a").first
                ig_link = link_el.get_attribute("href") if link_el.is_visible() else "N/A"
                
                item = {
                    "Name": name[:100],
                    "Rating": "N/A",
                    "Reviews": "N/A",
                    "Phone": phone,
                    "Phone 2": "",
                    "Phone 3": "",
                    "Website Available?": website_avail,
                    "Website Link": ig_link,
                    "Google Maps URL": ig_link if ig_link != "N/A" else f"https://instagram.com/dedup/{pincode}/{niche.replace(' ','')}/{i}",
                    "phone_source": "Instagram Bio"
                }
                items.append(item)
                if on_item_scraped:
                    on_item_scraped(item)
            except Exception:
                pass
                
    except Exception as e:
        print(f"[Instagram] Error: {e}")
    finally:
        page.close()
        
    return pd.DataFrame(items)
