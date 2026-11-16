"""
Industrial AMR Digital Twin - 1-Click Launch Script
Starts Flask background simulation server and opens the 3D Digital Twin Cockpit in the default browser.
"""

import sys
import time
import webbrowser
import subprocess
import os

def main():
    print("=" * 68)
    print(" 🚀 STARTING AI-POWERED INDUSTRIAL AMR DIGITAL TWIN & SIMULATOR")
    print("=" * 68)
    
    server_path = os.path.join(os.path.dirname(__file__), "server.py")
    url = "http://127.0.0.1:5000"

    print(f"[*] Starting Backend Simulation & Fleet Engine on {url}...")
    
    # Launch server as child process
    server_proc = subprocess.Popen([sys.executable, server_path])
    
    # Wait 1.5 seconds for Flask server to initialize
    time.sleep(1.5)
    
    print(f"[*] Opening 3D Digital Twin Fleet Dashboard in browser...")
    webbrowser.open(url)
    
    print("\n" + "=" * 68)
    print(" ✅ SYSTEM RUNNING SUCCESSFULLY")
    print(f" 🌐 Dashboard URL: {url}")
    print(" 🤖 3 AMRs active: AMR-01 Alpha, AMR-02 Beta, AMR-03 Gamma")
    print(" 🧠 Google Gemini AI Commander: Active (Configure API Key in UI)")
    print(" ⌨️  Controls: WASD to teleoperate, mouse to rotate/zoom 3D camera")
    print(" Press Ctrl+C in this terminal to safely shutdown the server.")
    print("=" * 68 + "\n")

    try:
        server_proc.wait()
    except KeyboardInterrupt:
        print("\n[*] Shutting down AMR simulation server...")
        server_proc.terminate()
        server_proc.wait()
        print("[*] Server stopped cleanly. Goodbye!")

if __name__ == "__main__":
    main()
