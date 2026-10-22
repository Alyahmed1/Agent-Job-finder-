"""One refresh = LinkedIn alert emails + the free remote-job sites, each scored and saved once."""
from datetime import datetime, timedelta, timezone

import db
from collect import feeds
from collect.gmail import fetch_alert_emails
from collect.parse import parse_alert_html
import learn
from score import score_job

SOURCES = {
    "Remotive": feeds.fetch_remotive,
    "Remote OK": feeds.fetch_remoteok,
    "We Work Remotely": feeds.fetch_wwr,
    "Jobicy": feeds.fetch_jobicy,
    "Himalayas": feeds.fetch_himalayas,
    "Working Nomads": feeds.fetch_workingnomads,
}

SEARCHABLE = ("Jobicy", "Himalayas")  # these take your keywords from profile.yaml


def current_model(conn):
    return learn.build_model(conn.execute("SELECT title, company, status FROM jobs").fetchall())


def rescore(conn, profile):
    """Apply the rules plus what your clicks taught us to every saved job. Fast: no web, no model."""
    model = current_model(conn)
    rows = conn.execute("SELECT * FROM jobs").fetchall()
    for r in rows:
        db.update_score(conn, r["id"], score_job(profile, dict(r), model))
    return len(rows)


def refresh_linkedin(conn, profile, days=2):
    model = current_model(conn)
    seen = db.known_ids(conn)
    new_jobs = {}
    for email in fetch_alert_emails(days=days):
        for job in parse_alert_html(email["html"], source=email["subject"]):
            if job["id"] not in seen:
                new_jobs.setdefault(job["id"], job)
    for job in new_jobs.values():
        db.save_job(conn, {**job, **score_job(profile, job, model)})
    return len(new_jobs)


def _due(conn, name, hours):
    last = db.get_meta(conn, f"fetched:{name}")
    if not last:
        return True
    return datetime.now(timezone.utc) - datetime.fromisoformat(last) >= timedelta(hours=hours)


def refresh_feeds(conn, profile, force=False):
    """Returns {source: number of new jobs, or a short note when skipped/failed}."""
    cfg = profile["feeds"]
    model = current_model(conn)
    seen_ids, seen_keys = db.known_ids(conn), db.known_keys(conn)
    report = {}
    for name, fetch in SOURCES.items():
        if not force and not _due(conn, name, cfg["cooldown_hours"].get(name, 3)):
            report[name] = "skipped (checked recently)"
            continue
        try:
            jobs = fetch(cfg["search_terms"]) if name in SEARCHABLE else fetch()
        except Exception as exc:  # one broken site must not stop the others
            report[name] = f"failed ({type(exc).__name__})"
            continue
        added = 0
        for job in jobs:
            key = db.job_key(job["title"], job["company"])
            if job["id"] in seen_ids or key in seen_keys:
                continue
            if not feeds.region_ok(job["location"], cfg["regions_ok"]):
                continue
            result = score_job(profile, job, model)
            if result["score"] < cfg["min_score"]:
                continue
            db.save_job(conn, {**job, **result})
            seen_ids.add(job["id"])
            seen_keys.add(key)
            added += 1
        db.set_meta(conn, f"fetched:{name}", datetime.now(timezone.utc).isoformat())
        report[name] = added
    return report


def refresh(conn, profile, days=2, force=False):
    """LinkedIn first, then the remote sites. Never raises: problems come back in the report."""
    try:
        report = {"LinkedIn": refresh_linkedin(conn, profile, days)}
    except Exception as exc:
        report = {"LinkedIn": f"failed ({type(exc).__name__})"}
    report.update(refresh_feeds(conn, profile, force=force))
    if not all(isinstance(v, str) and v.startswith("failed") for v in report.values()):
        db.set_meta(conn, "last_refresh", datetime.now(timezone.utc).isoformat())  # all failed (no network) -> stay stale, so the next open retries
    return report


def is_stale(iso, hours, now=None):
    """True when the last refresh is older than `hours` (or there has never been one)."""
    if not iso:
        return True
    now = now or datetime.now(timezone.utc)
    return now - datetime.fromisoformat(iso) > timedelta(hours=hours)


def total_new(report):
    return sum(v for v in report.values() if isinstance(v, int))
