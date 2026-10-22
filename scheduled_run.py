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


FRESH_HOURS = 3  # wake/unlock triggers fire often; skip when the list was just updated


def wait_for_network(timeout=600, pause=5):
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


def recently_updated():
    import db
    import pipeline
    return not pipeline.is_stale(db.get_meta(db.connect(), "last_refresh"), FRESH_HOURS)


exit_code = 0
log_path = ROOT / "logs" / "last_run.txt"
if log_path.exists() and log_path.stat().st_size > 100_000:
    log_path.unlink()  # keep the log small
with open(log_path, "a", encoding="utf-8") as log, \
        contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
    print(f"\nRun started {datetime.now():%Y-%m-%d %H:%M:%S}")
    try:
        print("Network ready" if wait_for_network() else "No network after 10 minutes, trying anyway")
        if recently_updated():
            print(f"Updated less than {FRESH_HOURS} hours ago, nothing to do")
        else:
            import run_daily

            sys.argv = ["run_daily.py", "--days", "3"]  # 3 days, so a missed morning never loses emails
            run_daily.main()
            report = getattr(run_daily.main, "report", {})
            if report and all(isinstance(v, str) and v.startswith("failed") for v in report.values()):
                print(f"\nRun FAILED: every source failed {datetime.now():%H:%M:%S}")
                exit_code = 1  # Task Scheduler retries a failed task
            else:
                print(f"\nRun finished {datetime.now():%H:%M:%S}")
    except Exception:
        traceback.print_exc()
        print(f"\nRun FAILED {datetime.now():%H:%M:%S}")
        exit_code = 1
sys.exit(exit_code)
