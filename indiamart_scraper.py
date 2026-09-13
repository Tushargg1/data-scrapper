import time
import asyncio
import re
import pandas as pd
from playwright.sync_api import sync_playwright

def scrape_indiamart(niche: str, pincode: str, max_scrolls: int = 5, on_item_scraped=None, should_stop=None, context=None, profile_id: int = 1) -> pd.DataFrame:
    """
    IndiaMART Scraper
    Searches IndiaMART for the niche and pincode.
    """
    if context is None:
        raise ValueError("Playwright context required for IndiaMART scraper")
    
    page = context.new_page()
    items = []
    
    try:
        query = f"{niche} {pincode}".replace(" ", "+")
        url = f"https://dir.indiamart.com/search.mp?ss={query}"
        
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)
        
        scrolls = 0
        while scrolls < max_scrolls:
            if should_stop and should_stop():
                break
            page.evaluate("window.scrollBy(0, 1000);")
            time.sleep(1.5)
            scrolls += 1
            
        cards = page.locator(".lst_cl, .card, .m-w, .ls_coell").all()
        for i, card in enumerate(cards):
            if should_stop and should_stop():
                break
            try:
                name = card.inner_text().split("\\n")[0].strip()
                if len(name) < 3:
                    continue
                    
                phone = "N/A"
                raw_text = card.inner_text()
                phone_match = re.search(r'(?:\\+91|0)?[-\s]?\\d{4,5}[-\s]?\\d{5,6}', raw_text)
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
                    "Google Maps URL": f"https://indiamart.com/dedup/{pincode}/{niche.replace(' ','')}/{i}",
                    "phone_source": "IndiaMART"
                }
                items.append(item)
                if on_item_scraped:
                    on_item_scraped(item)
            except Exception:
                pass
                
    except Exception as e:
        print(f"[IndiaMART] Error: {e}")
    finally:
        page.close()
        
    return pd.DataFrame(items)
