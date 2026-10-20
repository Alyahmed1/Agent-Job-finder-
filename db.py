"""SQLite store: remembers every job so we never show or score it twice."""
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "jobs.db"


def connect(path=None):
    path = path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT, company TEXT, location TEXT, url TEXT, source TEXT,
            score INTEGER, reason TEXT, missing TEXT,
            status TEXT DEFAULT 'new',
            first_seen TEXT
        )"""
    )
    if "note" not in {r["name"] for r in conn.execute("PRAGMA table_info(jobs)")}:
        conn.execute("ALTER TABLE jobs ADD COLUMN note TEXT")  # a cover note you chose to save
    if "description" not in {r["name"] for r in conn.execute("PRAGMA table_info(jobs)")}:
        conn.execute("ALTER TABLE jobs ADD COLUMN description TEXT")  # the job's full text, fetched once on demand
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(jobs)")}
    if "applied_at" not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN applied_at TEXT")  # when you pressed Mark applied (for the follow-up reminder)
    if "reply" not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN reply TEXT")  # NULL = still waiting, else 'interview' or 'rejected'
    conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
    return conn


def known_ids(conn):
    return {r["id"] for r in conn.execute("SELECT id FROM jobs")}


def job_key(title, company):
    """Same job posted on two sites: same normalised title + company."""
    norm = lambda s: re.sub(r"\W+", " ", (s or "").lower()).strip()
    return (norm(title), norm(company))


def known_keys(conn):
    return {job_key(r["title"], r["company"]) for r in conn.execute("SELECT title, company FROM jobs")}


def get_meta(conn, key):
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_meta(conn, key, value):
    conn.execute("INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))
    conn.commit()


def save_job(conn, job):
    conn.execute(
        """INSERT OR IGNORE INTO jobs
           (id, title, company, location, url, source, score, reason, missing, description, first_seen)
           VALUES (:id, :title, :company, :location, :url, :source, :score, :reason, :missing, :description, :first_seen)""",
        {"description": None, **job, "first_seen": datetime.now(timezone.utc).isoformat()},
    )
    conn.commit()


def set_status(conn, job_id, status):
    """status: new | saved | applied | rejected. Marking applied saves today's date; any other status clears it."""
    when = datetime.now(timezone.utc).isoformat() if status == "applied" else None
    conn.execute("UPDATE jobs SET status = ?, applied_at = ?, reply = NULL WHERE id = ?", (status, when, job_id))
    conn.commit()


REPLIES = ("interview", "rejected")


def set_reply(conn, job_id, reply):
    """reply: 'interview', 'rejected', or None to go back to waiting."""
    if reply is not None and reply not in REPLIES:
        raise ValueError(f"reply must be one of {REPLIES} or None")
    conn.execute("UPDATE jobs SET reply = ? WHERE id = ?", (reply, job_id))
    conn.commit()


def save_note(conn, job_id, text):
    conn.execute("UPDATE jobs SET note = ? WHERE id = ?", (text, job_id))
    conn.commit()


def save_description(conn, job_id, text):
    conn.execute("UPDATE jobs SET description = ? WHERE id = ?", (text, job_id))
    conn.commit()


def list_jobs(conn, status="new"):
    return conn.execute(
        "SELECT * FROM jobs WHERE status = ? ORDER BY score DESC, first_seen DESC", (status,)
    ).fetchall()


def update_score(conn, job_id, result):
    conn.execute(
        "UPDATE jobs SET score = :score, reason = :reason, missing = :missing WHERE id = :id",
        {**result, "id": job_id},
    )
    conn.commit()


def top_jobs(conn, limit=10, status="new"):
    return conn.execute(
        "SELECT * FROM jobs WHERE status = ? ORDER BY score DESC, first_seen DESC LIMIT ?",
        (status, limit),
    ).fetchall()
