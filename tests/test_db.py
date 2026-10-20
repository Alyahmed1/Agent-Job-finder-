import db

JOB = {"id": "1", "title": "t", "company": "c", "location": "l", "url": "u",
       "source": "s", "score": 50, "reason": "r", "missing": ""}


def test_job_is_saved_once_and_known(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    db.save_job(conn, JOB)
    db.save_job(conn, {**JOB, "score": 99})  # same id: ignored, never shown twice
    assert db.known_ids(conn) == {"1"}
    assert db.top_jobs(conn)[0]["score"] == 50


def test_marking_applied_saves_the_date_and_other_statuses_clear_it(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    db.save_job(conn, {"id": "a", "title": "t", "company": "c", "location": "Cairo", "url": "u", "source": "s",
                       "score": 50, "reason": "", "missing": ""})
    db.set_status(conn, "a", "applied")
    row = conn.execute("SELECT * FROM jobs WHERE id = 'a'").fetchone()
    assert row["applied_at"] and row["reply"] is None
    db.set_reply(conn, "a", "interview")
    assert conn.execute("SELECT reply FROM jobs WHERE id = 'a'").fetchone()["reply"] == "interview"
    db.set_reply(conn, "a", None)                         # back to waiting
    assert conn.execute("SELECT reply FROM jobs WHERE id = 'a'").fetchone()["reply"] is None
    db.set_reply(conn, "a", "rejected")
    db.set_status(conn, "a", "new")                       # Undo: the date and the reply go away
    row = conn.execute("SELECT * FROM jobs WHERE id = 'a'").fetchone()
    assert row["applied_at"] is None and row["reply"] is None


def test_a_reply_must_be_interview_rejected_or_none(tmp_path):
    import pytest
    conn = db.connect(tmp_path / "t.db")
    with pytest.raises(ValueError):
        db.set_reply(conn, "a", "maybe")


def test_old_databases_get_the_follow_up_columns(tmp_path):
    import sqlite3
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.execute("CREATE TABLE jobs (id TEXT PRIMARY KEY, title TEXT, status TEXT DEFAULT 'applied')")
    old.execute("INSERT INTO jobs (id, title) VALUES ('1', 't')")
    old.commit()
    old.close()
    row = db.connect(path).execute("SELECT applied_at, reply FROM jobs").fetchone()
    assert row["applied_at"] is None and row["reply"] is None


def test_followed_up_is_saved_and_cleared_with_the_status(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    db.save_job(conn, {"id": "a", "title": "t", "company": "c", "location": "Cairo", "url": "u", "source": "s",
                       "score": 50, "reason": "", "missing": ""})
    db.set_status(conn, "a", "applied")
    db.set_followed_up(conn, "a")
    assert conn.execute("SELECT followed_up_at FROM jobs WHERE id = 'a'").fetchone()["followed_up_at"]
    db.set_status(conn, "a", "new")
    assert conn.execute("SELECT followed_up_at FROM jobs WHERE id = 'a'").fetchone()["followed_up_at"] is None
