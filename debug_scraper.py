from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://gametora.com/umamusume/races')
    page.wait_for_selector("text='Details'")
    time.sleep(2)
    
    # Get locators for all Details buttons
    detail_buttons = page.locator("text='Details'")
    
    btn = detail_buttons.nth(5)
    btn.scroll_into_view_if_needed()
    time.sleep(0.1)
    btn.click()
    time.sleep(0.4)
    
    # Extract data from the modal
    debug_info = page.evaluate("""
        () => {
            const modals = Array.from(document.querySelectorAll('div[role="dialog"]'));
            if (modals.length === 0) return {error: "No div[role=dialog] found"};
            
            const info = modals.map(d => {
                const style = window.getComputedStyle(d);
                return {
                    zIndex: style.zIndex,
                    textLen: d.innerText.length,
                    offsetParent: d.offsetParent !== null,
                    html: d.outerHTML.substring(0, 100)
                };
            });
            
            return {info: info};
        }
    """)
    print(debug_info)
    browser.close()
