"""Smoke test: every sidebar page renders without an error. Only navigates, never changes a job."""
from pathlib import Path

import pytest

import db
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")
PAGES = ["Egypt", "Remote", "Relocation", "Saved", "Applied", "Not interested"]


@pytest.mark.parametrize("page", PAGES)
def test_each_page_renders(page, tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")   # an empty database, never yours
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["page"] = page
    at.session_state["auto_checked"] = True   # never start a live refresh inside a test
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert [b.label for b in at.sidebar.button if page in b.label], f"{page} missing from the sidebar"


def test_tailor_panel_opens_and_shows_a_comparison(tmp_path, monkeypatch):
    import tailor

    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    conn = db.connect()
    db.save_job(conn, {"id": "r1", "title": "Python Engineer", "company": "Acme", "location": "Worldwide (Remote)",
                       "url": "https://x.test/j", "source": "Jobicy", "score": 80, "reason": "r", "missing": "",
                       "description": "We need Python, FastAPI and Kubernetes. " * 12})
    conn.close()
    monkeypatch.setattr(tailor, "load_cv", lambda: {"skills": {"L": ["Python", "FastAPI"]}, "experience": [],
                                                    "projects": []})
    monkeypatch.setattr(tailor, "summary_line", lambda *a, **k: ("Python engineer.", ""))
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["page"] = "Remote"
    at.session_state["auto_checked"] = True
    at.run()
    next(b for b in at.button if b.label == "Tailor my CV").click().run()
    assert not at.exception, [e.value for e in at.exception]
    text = " ".join(m.value for m in at.markdown)
    assert "Kubernetes" in text and "FastAPI, Python" in text
    next(b for b in at.button if b.label == "Close").click().run()
    assert not at.exception and "Kubernetes" not in " ".join(m.value for m in at.markdown)
