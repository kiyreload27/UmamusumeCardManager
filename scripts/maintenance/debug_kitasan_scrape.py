import os
import sys
from playwright.sync_api import sync_playwright

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def debug_kitasan_scrape():
    url = "https://gametora.com/umamusume/supports/30028-kitasan-black"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto(url)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        
        # 1. Get Skill Rarity Map
        rarity_map = page.evaluate("""
            () => {
                const map = {};
                const sections = Array.from(document.querySelectorAll('div, span, h3')).filter(el => 
                    el.innerText.trim().startsWith('Skills from events')
                );
                if (sections.length === 0) return { error: "Section not found" };
                
                const root = sections[0].closest('div');
                const containers = Array.from(root.querySelectorAll('div')).filter(d => 
                    d.innerText.includes('Details') && d.children.length > 1
                );
                
                containers.forEach(c => {
                    const textNodes = Array.from(c.querySelectorAll('div, span')).filter(n => n.children.length === 0);
                    const name = textNodes[0] ? textNodes[0].innerText.trim() : "";
                    
                    if (name && name.length > 1 && !name.includes('Details')) {
                        const style = window.getComputedStyle(c);
                        const isGold = style.backgroundImage.includes('linear-gradient') || 
                                       style.backgroundColor.includes('rgb(255, 193, 7)') ||
                                       c.className.includes('kkspcu');
                        map[name] = isGold;
                    }
                });
                return map;
            }
        """)
        print(f"Skill Rarity Map: {rarity_map}")
        
        # 2. Click Golden Perk Button
        page.evaluate("() => { const h = Array.from(document.querySelectorAll('h2, h1')).find(el => el.innerText.includes('Training Events')); if (h) h.scrollIntoView(); }")
        page.wait_for_timeout(500)
        
        btn_found = page.evaluate("""
            () => {
                const labels = Array.from(document.querySelectorAll('div, span, h2, h3')).filter(el => 
                    el.innerText.trim() === 'Chain Events'
                );
                const buttons = [];
                labels.forEach(label => {
                    let container = label.parentElement;
                    while (container && container.querySelectorAll('button').length === 0) {
                        container = container.nextElementSibling || container.parentElement;
                        if (container && container.tagName === 'BODY') break;
                    }
                    if (container) {
                        const btns = Array.from(container.querySelectorAll('button'));
                        btns.forEach(btn => {
                            const text = btn.innerText.trim();
                            if (text.includes('>') || text.includes('❯')) buttons.push(btn);
                        });
                    }
                });
                
                let goldenBtn = buttons.find(b => b.innerText.includes('❯❯❯'));
                if (!goldenBtn) {
                     // Fallback to max arrows
                     let maxArrows = 0;
                     buttons.forEach(b => {
                         const count = (b.innerText.match(/>|❯/g) || []).length;
                         if (count > maxArrows) { maxArrows = count; goldenBtn = b; }
                     });
                }
                
                if (goldenBtn) {
                    goldenBtn.click();
                    return goldenBtn.innerText;
                }
                return null;
            }
        """)
        print(f"Clicked button: {btn_found}")
        page.wait_for_timeout(1000)
        
        # 3. Get Skills from Tooltip
        tooltip_skills = page.evaluate("""
            () => {
                const popovers = Array.from(document.querySelectorAll('div')).filter(d => 
                    window.getComputedStyle(d).zIndex > 50 &&
                    d.innerText.length < 2500
                );
                if (popovers.length === 0) return { error: "No popovers found" };
                
                const pop = popovers[popovers.length - 1];
                const skillLinks = Array.from(pop.querySelectorAll('span, a')).filter(el => 
                    el.innerText.length > 2 && 
                    !el.innerText.includes('Energy') && 
                    !el.innerText.includes('bond')
                );
                return skillLinks.map(s => s.innerText.trim());
            }
        """)
        print(f"Tooltip Skills: {tooltip_skills}")
        
        browser.close()

if __name__ == "__main__":
    debug_kitasan_scrape()
