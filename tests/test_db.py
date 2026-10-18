import db

JOB = {"id": "1", "title": "t", "company": "c", "location": "l", "url": "u",
       "source": "s", "score": 50, "reason": "r", "missing": ""}


def test_job_is_saved_once_and_known(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    db.save_job(conn, JOB)
    db.save_job(conn, {**JOB, "score": 99})  # same id: ignored, never shown twice
    assert db.known_ids(conn) == {"1"}
    assert db.top_jobs(conn)[0]["score"] == 50
