"""Quick test of the fixed level navigation"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright

URL = "https://gametora.com/umamusume/supports/30022-mejiro-mcqueen"

def test_levels():
    print("Testing fixed level navigation...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.goto(URL, timeout=60000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        
        for target in [1, 25, 40, 50]:
            actual = page.evaluate("""
                async (targetLevel) => {
                    const getLevel = () => {
                        const el = Array.from(document.querySelectorAll('div')).find(d => 
                            d.textContent.trim().startsWith('Level ') && d.children.length === 0
                        );
                        if (!el) {
                            const text = document.body.innerText;
                            const match = text.match(/Level\\s*(\\d+)/i);
                            return match ? parseInt(match[1]) : 30;
                        }
                        return parseInt(el.textContent.replace('Level ', '').trim());
                    };
                    
                    const clickButton = (text) => {
                        const btns = Array.from(document.querySelectorAll('div'));
                        const btn = btns.find(d => d.textContent.trim() === text && d.children.length === 0);
                        if (btn) {
                            btn.click();
                            return true;
                        }
                        return false;
                    };
                    
                    let currentLevel = getLevel();
                    
                    while (currentLevel !== targetLevel) {
                        let btnText;
                        if (currentLevel > targetLevel) {
                            const diff = currentLevel - targetLevel;
                            btnText = diff >= 5 ? '-5' : '-1';
                        } else {
                            const diff = targetLevel - currentLevel;
                            btnText = diff >= 5 ? '+5' : '+1';
                        }
                        
                        if (!clickButton(btnText)) break;
                        
                        const startLevel = currentLevel;
                        let start = Date.now();
                        while (Date.now() - start < 1000) {
                            await new Promise(r => setTimeout(r, 50));
                            const newLevel = getLevel();
                            if (newLevel !== startLevel) {
                                currentLevel = newLevel;
                                break;
                            }
                        }
                        
                        if (currentLevel === startLevel) break;
                    }
                    
                    await new Promise(r => setTimeout(r, 200));
                    return getLevel();
                }
            """, target)
            
            status = "✓" if actual == target else "✗"
            print(f"Target: {target} -> Actual: {actual} {status}")
        
        browser.close()
    
    print("Done!")

if __name__ == "__main__":
    test_levels()
