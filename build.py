import subprocess
import sys
import os

def main():
    print("🚀 Starting Build Process...\n")
    
    # Get python interpreter
    python_exe = sys.executable
    
    # 1. Prepare Release Database
    print("--------------------------------")
    print("Step 1/2: Preparing Database")
    print("--------------------------------")
    script_path = os.path.join("scripts", "prepare_release_db.py")
    ret = subprocess.call([python_exe, script_path])
    if ret != 0:
        print("❌ Error: Database preparation failed.")
        sys.exit(1)
        
    print("\n")
    
    # 2. Run PyInstaller
    print("--------------------------------")
    print("Step 2/2: Building Executable")
    print("--------------------------------")
    # We use 'pyinstaller' as a command. If it's not in path, we might need to assume it's a module
    # Try running as module first for safety: python -m PyInstaller
    ret = subprocess.call([python_exe, "-m", "PyInstaller", "UmamusumeCardManager.spec", "--noconfirm"])
    if ret != 0:
        print("❌ Error: PyInstaller build failed.")
        sys.exit(1)
        
    print("\n✅ Build Complete! Executable is in in 'dist' folder.")

if __name__ == "__main__":
    main()
