import subprocess
import time
import sys
import psutil

# Start the application
print("Starting main application...")
process = subprocess.Popen([sys.executable, "main.py"])

# Give it time to launch
time.sleep(5)

# Verify it's still running
if process.poll() is None:
    print("Application is running successfully.")
    
    # We could theoretically use PyAutoGUI here to click tabs, 
    # but CustomTkinter doesn't expose standard handles easily to OS automation
    # The main thing we needed to test was that it doesn't crash on load with the CTkImage warning
    time.sleep(5)
    
    # Kill the process nicely
    print("Terminating application...")
    parent = psutil.Process(process.pid)
    for child in parent.children(recursive=True):
        child.terminate()
    parent.terminate()
else:
    print(f"Application crashed with code: {process.returncode}")
