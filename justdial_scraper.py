import time
import asyncio
import re
import pandas as pd
from playwright.sync_api import sync_playwright

def scrape_justdial(niche: str, pincode: str, max_scrolls: int = 5, on_item_scraped=None, should_stop=None, context=None, profile_id: int = 1) -> pd.DataFrame:
    """
    JustDial Scraper
    Searches JustDial via Google for the niche and pincode since direct search is blocked.
    """
    if context is None:
        raise ValueError("Playwright context required for JustDial scraper")
    
    page = context.new_page()
    items = []
    
    try:
        # Search via Google using site: operator
        query = f"site:justdial.com {niche} {pincode}".replace(" ", "+")
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
            
        # Parse Google SERP results for JustDial
        results = page.locator("div.g").all()
        for i, res in enumerate(results):
            if should_stop and should_stop():
                break
            try:
                title_el = res.locator("h3").first
                if not title_el.is_visible():
                    continue
                name = title_el.inner_text().strip()
                name = name.split("-")[0].strip() # Clean JustDial titles
                
                snippet_el = res.locator(".VwiC3b").first
                snippet = snippet_el.inner_text().strip() if snippet_el.is_visible() else ""
                
                phone = "N/A"
                phone_match = re.search(r'(?:\\+91|0)?[-\s]?\\d{4,5}[-\s]?\\d{5,6}', snippet)
                if phone_match:
                    phone = phone_match.group(0).strip()
                    
                item = {
                    "Name": name[:100],
                    "Rating": "N/A",
                    "Reviews": "N/A",
                    "Phone": phone,
                    "Phone 2": "",
                    "Phone 3": "",
                    "Website Available?": "No",
                    "Website Link": "N/A",
                    "Google Maps URL": f"https://justdial.com/dedup/{pincode}/{niche.replace(' ','')}/{i}",
                    "phone_source": "JustDial"
                }
                items.append(item)
                if on_item_scraped:
                    on_item_scraped(item)
            except Exception:
                pass
                
    except Exception as e:
        print(f"[JustDial] Error: {e}")
    finally:
        page.close()
        
    return pd.DataFrame(items)
