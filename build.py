"""
Build script for UmamusumeCardManager.
Steps:
  1. Inject BUILD_DATE into version.py
  2. Prepare the release database (strips user data, seeds version)
  3. Run PyInstaller to produce the single-file exe
  4. Print the SHA256 of the output exe
  5. Restore version.py BUILD_DATE to "dev"
"""

import subprocess
import sys
import os
import hashlib
from datetime import datetime, timezone

# Force UTF-8 output so emoji don't crash on Windows cp1252 consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


_VERSION_FILE = os.path.join(os.path.dirname(__file__), "version.py")
_BUILD_DATE_PLACEHOLDER = 'BUILD_DATE: str = "dev"'


def _inject_build_date(date_str: str):
    """Replace the BUILD_DATE placeholder in version.py with today's date."""
    with open(_VERSION_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    new_line = f'BUILD_DATE: str = "{date_str}"'
    if _BUILD_DATE_PLACEHOLDER not in content:
        print(f"⚠  Could not find BUILD_DATE placeholder in version.py. Skipping injection.")
        return False

    new_content = content.replace(_BUILD_DATE_PLACEHOLDER, new_line)
    with open(_VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"✅ Injected BUILD_DATE = {date_str}")
    return True


def _restore_build_date():
    """Restore BUILD_DATE to 'dev' after build."""
    with open(_VERSION_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    import re
    restored = re.sub(r'BUILD_DATE: str = "[^"]*"', _BUILD_DATE_PLACEHOLDER, content)
    with open(_VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(restored)
    print("✅ Restored BUILD_DATE to 'dev'")


def _sha256_of(path: str) -> str:
    """Compute and return the SHA256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    python_exe = sys.executable
    build_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print("🚀 Starting Build Process...\n")

    # ── Step 0: Inject BUILD_DATE ──────────────────────────────────────
    print("--------------------------------")
    print("Step 0/3: Injecting BUILD_DATE")
    print("--------------------------------")
    injected = _inject_build_date(build_date)

    try:
        # ── Step 1: Prepare Release Database ──────────────────────────
        print("\n--------------------------------")
        print("Step 1/3: Preparing Database")
        print("--------------------------------")
        script_path = os.path.join("scripts", "prepare_release_db.py")
        ret = subprocess.call([python_exe, script_path])
        if ret != 0:
            print("❌ Error: Database preparation failed.")
            sys.exit(1)

        # ── Step 2: Run PyInstaller ────────────────────────────────────
        print("\n--------------------------------")
        print("Step 2/3: Building Executable")
        print("--------------------------------")
        ret = subprocess.call([
            python_exe, "-m", "PyInstaller",
            "UmamusumeCardManager.spec", "--noconfirm"
        ])
        if ret != 0:
            print("❌ Error: PyInstaller build failed.")
            sys.exit(1)

        # ── Step 3: Report SHA256 ──────────────────────────────────────
        print("\n--------------------------------")
        print("Step 3/3: Verifying Output")
        print("--------------------------------")
        exe_name = "UmamusumeCardManager.exe" if sys.platform == "win32" else "UmamusumeCardManager"
        exe_path = os.path.join("dist", exe_name)
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            sha = _sha256_of(exe_path)
            print(f"\n✅ Build Complete!")
            print(f"   Output:  {exe_path}")
            print(f"   Size:    {size_mb:.1f} MB")
            print(f"   SHA256:  {sha}")
            print(f"\n   Build date embedded: {build_date}")
            print("\n   Paste this into your GitHub release notes:")
            print(f"   ```\n   SHA256: {sha}\n   ```")
        else:
            print(f"✅ Build Complete!  (binary not found at expected path: {exe_path})")

    finally:
        # Always restore BUILD_DATE even if the build fails
        if injected:
            print("\n--------------------------------")
            print("Restoring version.py")
            print("--------------------------------")
            _restore_build_date()


if __name__ == "__main__":
    main()
