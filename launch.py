"""Quickpipe launcher — double-click or run: python launch.py

Creates a virtual environment and installs dependencies on first run, then
starts the Streamlit app on port 8502 (FlowBench uses 8501, so both can run).
"""
import os
import sys
import subprocess
import time
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

VENV = os.path.join(ROOT, ".venv")
if sys.platform == "win32":
    PYTHON = os.path.join(VENV, "Scripts", "python.exe")
    PIP    = os.path.join(VENV, "Scripts", "pip.exe")
else:
    PYTHON = os.path.join(VENV, "bin", "python")
    PIP    = os.path.join(VENV, "bin", "pip")

URL = "http://127.0.0.1:8502"

if not os.path.exists(PYTHON):
    print("No virtual environment found — running first-time setup...")
    subprocess.check_call([sys.executable, "-m", "venv", VENV])
    print("Installing dependencies (this takes a minute the first time)...")
    subprocess.check_call([PIP, "install", "-r", "requirements.txt"])
    print("Setup complete.\n")

print(f"Starting Quickpipe at {URL}")
print("Close this window or press Ctrl+C to stop.\n")

proc = subprocess.Popen([
    PYTHON, "-m", "streamlit", "run", "quickpipe_app.py",
    "--server.address=127.0.0.1",
    "--server.port=8502",
    "--server.headless=true",
])

time.sleep(5)
webbrowser.open(URL)

try:
    proc.wait()
except KeyboardInterrupt:
    proc.terminate()
