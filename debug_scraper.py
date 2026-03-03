from playwright.sync_api import sync_playwright
import json

def test_image_grab():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://gametora.com/umamusume/characters/100101-special-week")
        page.wait_for_load_state("networkidle")
        
        img_url = page.evaluate("""
            () => {
                const imgs = Array.from(document.querySelectorAll('img'));
                return imgs.map(img => img.src);
            }
        """)
        
        matches = []
        for url in img_url:
            if "character" in url.lower() or "chara" in url.lower():
                matches.append(url)
                
        with open("urls.json", "w") as f:
            json.dump(matches, f, indent=2)
            
        browser.close()

if __name__ == "__main__":
    test_image_grab()
