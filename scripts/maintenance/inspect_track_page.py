"""
Diagnostic script to inspect GameTora track page DOM structure.
Run this to see exactly how courses appear on the page.
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright

URL = "https://gametora.com/umamusume/racetracks/sapporo"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    print(f"Loading {URL}...")
    page.goto(URL, timeout=60000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(5000)
    
    # Scroll fully
    for _ in range(10):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(1000)
    
    # Dump full page text
    full_text = page.evaluate("() => document.body.innerText")
    print("\n" + "=" * 80)
    print("FULL PAGE TEXT (first 5000 chars):")
    print("=" * 80)
    print(full_text[:5000])
    
    # Look for all links
    links = page.evaluate("""
        () => {
            return Array.from(document.querySelectorAll('a')).map(a => ({
                href: a.href,
                text: a.textContent.trim().substring(0, 100),
            })).filter(l => l.text.length > 0);
        }
    """)
    print("\n" + "=" * 80)
    print(f"ALL LINKS ({len(links)}):")
    print("=" * 80)
    for l in links:
        print(f"  [{l['text']}] -> {l['href']}")

    # Look for anything with "m" and digits (potential course distances)
    dist_elements = page.evaluate("""
        () => {
            const results = [];
            const allEls = document.querySelectorAll('*');
            for (const el of allEls) {
                if (el.children.length > 0) continue;
                const text = el.textContent.trim();
                if (text.match(/\\d+\\s*m/) && text.length < 120) {
                    results.push({
                        tag: el.tagName,
                        class: el.className?.substring(0, 60) || '',
                        text: text,
                        parent: el.parentElement?.tagName + '.' + (el.parentElement?.className?.substring(0, 30) || '')
                    });
                }
            }
            return results;
        }
    """)
    print("\n" + "=" * 80)
    print(f"ELEMENTS WITH DISTANCE-LIKE TEXT ({len(dist_elements)}):")
    print("=" * 80)
    for e in dist_elements:
        print(f"  <{e['tag']} class='{e['class']}'> {e['text']}  [parent: {e['parent']}]")

    # Look for buttons, tabs, or clickable elements
    buttons = page.evaluate("""
        () => {
            return Array.from(document.querySelectorAll('button, [role=tab], [role=button]')).map(b => ({
                tag: b.tagName,
                text: b.textContent.trim().substring(0, 100),
                class: b.className?.substring(0, 60) || ''
            })).filter(b => b.text.length > 0);
        }
    """)
    print("\n" + "=" * 80)
    print(f"BUTTONS/TABS ({len(buttons)}):")
    print("=" * 80)
    for b in buttons:
        print(f"  <{b['tag']}> {b['text']}  [class: {b['class']}]")
    
    # Look for table-like structures
    tables = page.evaluate("""
        () => {
            const tables = document.querySelectorAll('table');
            if (tables.length > 0) {
                return Array.from(tables).map(t => ({
                    rows: t.rows.length,
                    text: t.textContent.trim().substring(0, 300)
                }));
            }
            // Also look for div-based tables
            const divTables = Array.from(document.querySelectorAll('div')).filter(d => {
                const text = d.innerText;
                return text.includes('Phases') && text.includes('Corners') && d.children.length > 3;
            });
            return divTables.map(d => ({
                tag: 'div-table',
                children: d.children.length,
                text: d.innerText.substring(0, 500)
            }));
        }
    """)
    print("\n" + "=" * 80)
    print(f"TABLE-LIKE STRUCTURES ({len(tables)}):")
    print("=" * 80)
    for t in tables:
        print(json.dumps(t, indent=2))

    # Look specifically for Turf/Dirt text
    surface_els = page.evaluate("""
        () => {
            const results = [];
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            while (walker.nextNode()) {
                const text = walker.currentNode.nodeValue.trim();
                if (text.match(/Turf|Dirt/i) && text.length < 100) {
                    const parent = walker.currentNode.parentElement;
                    results.push({
                        text: text,
                        tag: parent?.tagName,
                        class: parent?.className?.substring(0, 60) || '',
                        grandparent: parent?.parentElement?.tagName + '.' + (parent?.parentElement?.className?.substring(0, 30) || '')
                    });
                }
            }
            return results;
        }
    """)
    print("\n" + "=" * 80)
    print(f"TURF/DIRT TEXT NODES ({len(surface_els)}):")
    print("=" * 80)
    for e in surface_els:
        print(f"  '{e['text']}' in <{e['tag']} class='{e['class']}'> [parent: {e['grandparent']}]")
    
    browser.close()
    print("\nDone!")
