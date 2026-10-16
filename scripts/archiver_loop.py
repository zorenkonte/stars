#!/usr/bin/env python3
"""Container entrypoint: run the archive + Postgres sync on a daily schedule.

On start it seeds /data from the committed stars.json if the volume is empty
(so the ledger keeps its history), optionally runs immediately, then sleeps
until the next ARCHIVE_AT (local time, TZ env) and repeats. A failed run is
logged and retried at the next slot — the ledger file is only rewritten by a
successful archive_stars.py run, so a crash never corrupts it.

Environment:
  ARCHIVE_AT     HH:MM local time, default 08:07
  RUN_ON_START   "true" (default) to run once immediately
  SEED_JSON      seed file copied into STARS_JSON when the latter is missing
  STARS_JSON     ledger path (shared with archive_stars.py / sync_to_postgres.py)
"""

import datetime as dt
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STARS_JSON = os.environ.get("STARS_JSON", "/data/stars.json")
SEED_JSON = os.environ.get("SEED_JSON", "/seed/stars.json")
ARCHIVE_AT = os.environ.get("ARCHIVE_AT", "08:07")
RUN_ON_START = os.environ.get("RUN_ON_START", "true").strip().lower() == "true"


def log(msg):
    print(f"[{dt.datetime.now().isoformat(timespec='seconds')}] {msg}", flush=True)


def seed():
    if os.path.exists(STARS_JSON):
        return
    if os.path.exists(SEED_JSON):
        os.makedirs(os.path.dirname(STARS_JSON), exist_ok=True)
        shutil.copyfile(SEED_JSON, STARS_JSON)
        log(f"Seeded {STARS_JSON} from {SEED_JSON}")
    else:
        log(f"No ledger at {STARS_JSON} and no seed at {SEED_JSON}; starting from an empty archive")


def run_once():
    for script in ("archive_stars.py", "sync_to_postgres.py"):
        log(f"Running {script}")
        res = subprocess.run([sys.executable, os.path.join(HERE, script)])
        if res.returncode != 0:
            log(f"{script} failed with exit code {res.returncode}")
            return False
    log("Run complete")
    return True


def seconds_until_next():
    hh, mm = (int(x) for x in ARCHIVE_AT.split(":"))
    now = dt.datetime.now()
    nxt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if nxt <= now:
        nxt += dt.timedelta(days=1)
    return (nxt - now).total_seconds(), nxt


def main():
    seed()
    if RUN_ON_START:
        run_once()
    while True:
        wait, when = seconds_until_next()
        log(f"Next run at {when.isoformat(timespec='minutes')} ({int(wait // 60)} min)")
        time.sleep(wait)
        run_once()


if __name__ == "__main__":
    main()
