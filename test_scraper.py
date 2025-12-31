
import sqlite3
import os
from playwright.sync_api import sync_playwright
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_scrape_events(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print(f"Testing URL: {url}")
        page.goto(url)
        page.wait_for_timeout(2000)
        
        # 1. First, build a map of skills from the 'Skills from events' summary section
        skill_rarity_map = page.evaluate("""
            () => {
                const map = {};
                const sections = Array.from(document.querySelectorAll('div')).filter(d => d.innerText.includes('Skills from events'));
                if (sections.length === 0) return { error: 'No Skills from events section' };
                
                const containers = sections[0].parentElement.querySelectorAll('div[class*="sc-"]');
                containers.forEach(c => {
                    const nameNode = c.querySelector('div[font-weight="bold"], span[font-weight="bold"], b');
                    const name = nameNode ? nameNode.innerText.trim() : c.innerText.split('\\n')[0].trim();
                    if (name && name.length > 2) {
                        const isGold = c.className.includes('kkspcu') || 
                                     window.getComputedStyle(c).backgroundColor.includes('rgb(255, 193, 7)') ||
                                     c.innerText.includes('✨');
                        map[name] = isGold;
                    }
                });
                return map;
            }
        """)
        print(f"Skill Rarity Map: {skill_rarity_map}")
        
        # 2. Scrape ONLY the LAST chain event (Golden Perk) with OR options
        golden_perk_data = page.evaluate("""
            async () => {
                const getChainEventButtons = () => {
                    const buttons = [];
                    const headers = Array.from(document.querySelectorAll('div, h2, h3, span')).filter(el => 
                        el.innerText.includes('Chain Events')
                    );
                    
                    headers.forEach(header => {
                        const container = header.parentElement;
                        if (container) {
                            const btns = Array.from(container.querySelectorAll('button'));
                            btns.forEach(btn => {
                                const text = btn.innerText.trim();
                                const isVisible = btn.offsetWidth > 0;
                                if (isVisible && text && text.includes('>') && !text.includes('Events')) {
                                    buttons.push(btn);
                                }
                            });
                        }
                    });
                    return buttons;
                    };

                const buttons = getChainEventButtons();
                if (buttons.length === 0) return { error: 'No chain event buttons found' };
                
                let goldenPerkButton = null;
                let maxArrows = 0;
                for (const btn of buttons) {
                    const text = btn.innerText.trim();
                    const arrowCount = (text.match(/>/g) || []).length;
                    if (arrowCount > maxArrows) {
                        maxArrows = arrowCount;
                        goldenPerkButton = btn;
                    }
                }
                
                if (!goldenPerkButton) return { error: 'No golden perk button identified' };
                
                const eventName = goldenPerkButton.innerText.trim();
                goldenPerkButton.click();
                await new Promise(r => setTimeout(r, 1000));
                
                const popovers = Array.from(document.querySelectorAll('div')).filter(d => 
                    d.innerText.includes(eventName) && 
                    window.getComputedStyle(d).zIndex > 50
                );
                
                if (popovers.length === 0) return { error: 'Popover not found', eventName: eventName };
                
                const pop = popovers[popovers.length - 1];
                const skillLinks = Array.from(pop.querySelectorAll('span, a')).filter(el => 
                    el.innerText.length > 2 && 
                    (window.getComputedStyle(el).color === 'rgb(102, 107, 255)' || 
                     el.className.includes('linkcolor'))
                );
                
                return { 
                    name: eventName, 
                    skills: skillLinks.map(l => l.innerText.trim())
                };
            }
        """)
        print(f"Golden Perk Data: {golden_perk_data}")
        browser.close()

if __name__ == "__main__":
    # Test with Gentildonna (verified URL from subagent)
    test_scrape_events("https://gametora.com/umamusume/supports/30186-gentildonna")
