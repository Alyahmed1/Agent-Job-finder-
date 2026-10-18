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
