import pytest

import db
import pipeline
from collect import gmail
from score import load_profile


def test_background_run_never_opens_a_browser_when_login_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(gmail, "ROOT", tmp_path)          # no token.json here
    with pytest.raises(gmail.GmailLoginNeeded):
        gmail.get_service(interactive=False)


def test_refresh_reports_a_gmail_problem_and_still_runs_the_other_sources(tmp_path, monkeypatch):
    conn = db.connect(tmp_path / "t.db")

    def expired(*_):
        raise gmail.GmailLoginNeeded("expired")

    monkeypatch.setattr(pipeline, "refresh_linkedin", expired)
    monkeypatch.setattr(pipeline, "SOURCES", {"Remotive": lambda: []})
    report = pipeline.refresh(conn, load_profile())
    assert report["LinkedIn"] == "failed (GmailLoginNeeded)" and report["Remotive"] == 0


def test_last_refresh_time_is_remembered(tmp_path, monkeypatch):
    conn = db.connect(tmp_path / "t.db")
    monkeypatch.setattr(pipeline, "refresh_linkedin", lambda *a, **k: 0)
    monkeypatch.setattr(pipeline, "SOURCES", {})
    assert db.get_meta(conn, "last_refresh") is None
    pipeline.refresh(conn, load_profile())
    assert db.get_meta(conn, "last_refresh")


def test_updated_label(monkeypatch):
    import importlib.util
    from pathlib import Path
    # app.py runs Streamlit code on import, so read just the helper out of it
    src = (Path(__file__).resolve().parent.parent / "app.py").read_text(encoding="utf-8")
    start = src.index("def updated_label")
    ns = {"datetime": __import__("datetime").datetime}
    exec(src[start:src.index("def go(")], ns)
    assert ns["updated_label"](None).startswith("not updated yet")
    assert ns["updated_label"]("2026-10-19T04:01:00+00:00").startswith("Updated ")
