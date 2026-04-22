import os
import re

gui_dir = r"f:\UmaApp\UmamusumeCardManager-main - Cursor Edits\gui"

for root, _, files in os.walk(gui_dir):
    for f in files:
        if not f.endswith(".py"): continue
        path = os.path.join(root, f)
        with open(path, "r", encoding="utf-8") as file:
            content = file.read()
        
        orig_content = content
        
        # 1. QFrame {{ -> .QFrame {{
        content = re.sub(r'\"QFrame\s*\{\{', '".QFrame {{', content)
        content = re.sub(r'f\"QFrame\s*\{\{', 'f".QFrame {{', content)
        
        # 2. Fix bare background-color sets
        # Example: root.setStyleSheet(f"background-color: {BG_DARK};")
        # Replace with: f".QWidget, .QFrame, .QMainWindow, .QDialog {{ background-color: {BG_DARK}; }}"
        def repl(m):
            return 'setStyleSheet(f".QWidget, .QFrame, .QMainWindow, .QDialog {{ background-color: ' + m.group(1) + '; }}")'
            
        content = re.sub(r'setStyleSheet\(f"background-color:\s*(\{BG_[^}]+\});"\)', repl, content)
        
        if content != orig_content:
            with open(path, "w", encoding="utf-8") as file:
                file.write(content)
            print(f"Fixed {f}")
