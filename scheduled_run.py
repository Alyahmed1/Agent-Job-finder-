"""Entry point for the 7:00 AM task. Runs with no window (pythonw) and writes logs/last_run.txt."""
import contextlib
import os
import socket
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
(ROOT / "logs").mkdir(exist_ok=True)


def wait_for_network(timeout=180, pause=5):
    """After waking from sleep Wi-Fi takes a few seconds to reconnect; wait for it instead of failing every source."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            socket.create_connection(("1.1.1.1", 443), timeout=3).close()
            return True
        except OSError:
            if time.monotonic() >= deadline:
                return False
            time.sleep(pause)


with open(ROOT / "logs" / "last_run.txt", "w", encoding="utf-8") as log, \
        contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
    print(f"Run started {datetime.now():%Y-%m-%d %H:%M:%S}")
    try:
        print("Network ready" if wait_for_network() else "No network after 3 minutes, trying anyway")
        import run_daily

        sys.argv = ["run_daily.py", "--days", "3"]  # 3 days, so a missed morning never loses emails
        run_daily.main()
        print(f"\nRun finished OK {datetime.now():%H:%M:%S}")
    except Exception:
        traceback.print_exc()
        print(f"\nRun FAILED {datetime.now():%H:%M:%S}")
