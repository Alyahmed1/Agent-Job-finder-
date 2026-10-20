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
    assert row["applied_at"] and row["replied"] == 0
    db.set_replied(conn, "a", True)
    assert conn.execute("SELECT replied FROM jobs WHERE id = 'a'").fetchone()["replied"] == 1
    db.set_status(conn, "a", "new")                      # Undo: the date and the reply flag go away
    row = conn.execute("SELECT * FROM jobs WHERE id = 'a'").fetchone()
    assert row["applied_at"] is None and row["replied"] == 0


def test_old_databases_get_the_follow_up_columns(tmp_path):
    import sqlite3
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.execute("CREATE TABLE jobs (id TEXT PRIMARY KEY, title TEXT, status TEXT DEFAULT 'applied')")
    old.execute("INSERT INTO jobs (id, title) VALUES ('1', 't')")
    old.commit()
    old.close()
    row = db.connect(path).execute("SELECT applied_at, replied FROM jobs").fetchone()
    assert row["applied_at"] is None and row["replied"] == 0
