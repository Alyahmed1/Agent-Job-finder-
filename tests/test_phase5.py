from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import cover
import db
import learn
import pipeline
from score import load_profile, score_job

APP = str(Path(__file__).resolve().parent.parent / "app.py")
EXAMPLE = load_profile(Path(__file__).resolve().parent.parent / "profile.example.yaml")   # the shipped example: personal fields blank on purpose
# A filled-in profile for these tests, so they never depend on anyone's real details.
PROFILE = {
    **EXAMPLE,
    "name": "Test User",
    "summary": "A test summary.",
    "cover_note": {
        **EXAMPLE["cover_note"],
        "always_mention": {"name": "Demo Project", "sentence": "In a personal project, I built Demo Project."},
        "facts": ["WORK (Test Co): built a thing.", "PERSONAL PROJECT (not for an employer): built Demo Project."],
    },
}
MUST = PROFILE["cover_note"]["always_mention"]["name"]   # the project every cover note must name


def rows(*items):
    return [{"title": t, "company": c, "status": s} for t, c, s in items]


# ---------- learning from clicks ----------
def test_hiding_the_same_kind_of_job_four_times_lowers_similar_jobs():
    model = learn.build_model(rows(*[(f"Backend Engineer Magento {i}", f"Co{i}", "rejected") for i in range(4)]))
    assert model["tokens"]["magento"] == ('You often hide "magento"', -8)
    assert learn.adjust(model, {"title": "Magento Developer", "company": "Other"}) == [('You often hide "magento"', -8)]
    assert learn.adjust(model, {"title": "Machine Learning Engineer", "company": "Other"}) == []


def test_a_company_you_hid_twice_and_never_liked_goes_down_and_a_liked_one_goes_up():
    model = learn.build_model(rows(("A", "Acme Ltd", "rejected"), ("B", "Acme Ltd", "rejected"), ("D", "Acme Ltd", "rejected"),
                                   ("C", "Good Co", "saved")))
    assert learn.adjust(model, {"title": "x", "company": "acme ltd"})[0] == ("You hid 3 jobs from Acme Ltd", -10)
    assert learn.adjust(model, {"title": "x", "company": "Good Co"})[0] == ("You liked Good Co", 5)


def test_a_few_clicks_are_not_enough_to_change_anything():
    few = rows(*[(f"Magento Dev {i}", "Acme", "rejected") for i in range(2)])   # 2 hides of one company, 2 of one word
    model = learn.build_model(few)
    assert learn.adjust(model, {"title": "Magento Dev", "company": "Acme"}) == []


def test_learning_is_capped_so_clicks_never_overrule_everything():
    model = {"tokens": {"a": ("a", -8), "b": ("b", -8), "c": ("c", -8)}, "companies": {"x": ("x", -10)}}
    total = sum(p for _, p in learn.adjust(model, {"title": "a b c", "company": "x"}))
    assert learn.MAX_PENALTY <= total < 0


def test_the_card_shows_why_and_scoring_without_a_model_is_unchanged():
    model = learn.build_model(rows(*[(f"Magento Dev {i}", f"C{i}", "rejected") for i in range(4)]))
    job = {"title": "Magento Developer", "location": "Cairo, Egypt", "company": "Z"}
    plain, learned = score_job(PROFILE, job), score_job(PROFILE, job, model)
    assert learned["score"] == plain["score"] - 8 and 'You often hide "magento" -8' in learned["reason"]


def test_rescore_applies_what_your_clicks_taught(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    for i in range(4):
        db.save_job(conn, {"id": f"r{i}", "title": f"Magento Developer {i}", "company": f"C{i}", "location": "Cairo", "url": "u",
                           "source": "s", "score": 50, "reason": "", "missing": ""})
        db.set_status(conn, f"r{i}", "rejected")
    db.save_job(conn, {"id": "n", "title": "Magento Developer", "company": "Zed", "location": "Cairo", "url": "u",
                       "source": "s", "score": 50, "reason": "", "missing": ""})
    pipeline.rescore(conn, PROFILE)
    row = conn.execute("SELECT * FROM jobs WHERE id = 'n'").fetchone()
    assert 'You often hide "magento" -8' in row["reason"]


# ---------- cover note ----------
JOB = {"title": "Machine Learning Engineer", "company": "Acme", "location": "Cairo, Egypt"}


def test_prompt_uses_only_profile_facts_and_the_job():
    prompt = cover.build_prompt(PROFILE, JOB)
    assert "Machine Learning Engineer" in prompt and "Acme" in prompt and "Use ONLY the facts" in prompt
    assert PROFILE["name"] in prompt and PROFILE["cover_note"]["facts"][0] in prompt


def test_generate_returns_text_or_a_friendly_error(monkeypatch):
    class Resp:
        def raise_for_status(self): pass
        def json(self): return {"response": "  Hi, I am Aly.  "}

    monkeypatch.setattr(cover.requests, "post", lambda *a, **k: Resp())
    text, error = cover.generate(PROFILE, JOB)
    assert error == "" and text.startswith("Hi, I am Aly.") and MUST in text   # the required project is always added

    def down(*a, **k):
        raise cover.requests.ConnectionError("no ollama")

    monkeypatch.setattr(cover.requests, "post", down)
    text, error = cover.generate(PROFILE, JOB)
    assert text == "" and "Ollama" in error


def test_a_note_is_saved_only_when_asked_and_old_databases_get_the_column(tmp_path):
    import sqlite3
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.execute("CREATE TABLE jobs (id TEXT PRIMARY KEY, title TEXT, company TEXT, location TEXT, url TEXT, source TEXT,"
                " score INTEGER, reason TEXT, missing TEXT, status TEXT DEFAULT 'new', first_seen TEXT)")
    old.execute("INSERT INTO jobs (id, title) VALUES ('1', 't')")
    old.commit()
    old.close()
    conn = db.connect(path)                      # opens an older database without a note column
    assert conn.execute("SELECT note FROM jobs").fetchone()["note"] is None
    db.save_note(conn, "1", "Hi, I am Aly.")
    assert conn.execute("SELECT note FROM jobs").fetchone()["note"] == "Hi, I am Aly."


def test_note_panel_opens_writes_a_draft_but_saves_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    conn = db.connect()
    db.save_job(conn, {"id": "n1", "title": "Machine Learning Engineer", "company": "Acme", "location": "Cairo, Egypt",
                       "url": "https://example.com/1", "source": "s", "score": 80, "reason": "Egypt +10", "missing": ""})
    job = db.list_jobs(conn, "new")[0]
    notes_before = [r["note"] for r in conn.execute("SELECT note FROM jobs")]
    monkeypatch.setattr(cover, "generate", lambda profile, j: ("Hi, a draft for you. Aly Ahmed", ""))

    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["page"] = "Egypt"
    at.session_state["auto_checked"] = True   # never start a live refresh inside a test
    at.session_state["note_open"] = job["id"]
    at.session_state["note_generate"] = job["id"]
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    box = next(t for t in at.text_area if t.key == f"note_text_{job['id']}")
    assert box.value == "Hi, a draft for you. Aly Ahmed"
    assert [r["note"] for r in db.connect().execute("SELECT note FROM jobs")] == notes_before   # nothing was saved


def test_note_panel_shows_a_copy_ready_box_only_when_there_is_text(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    conn = db.connect()
    db.save_job(conn, {"id": "c1", "title": "Machine Learning Engineer", "company": "Acme", "location": "Cairo, Egypt",
                       "url": "https://example.com/1", "source": "s", "score": 80, "reason": "Egypt +10", "missing": ""})
    job = db.list_jobs(conn, "new")[0]

    def open_panel(saved_note):
        if saved_note:
            db.save_note(db.connect(), job["id"], saved_note)
        at = AppTest.from_file(APP, default_timeout=60)
        at.session_state["page"] = "Egypt"
        at.session_state["auto_checked"] = True
        at.session_state["note_open"] = job["id"]
        at.run()
        assert not at.exception, [e.value for e in at.exception]
        return at

    assert not open_panel("").code                                            # empty note: nothing to copy
    assert [c.value for c in open_panel("Hi, I am Aly.").code] == ["Hi, I am Aly."]


def test_cover_note_always_names_the_required_project(monkeypatch):
    calls = []

    class Resp:
        def __init__(self, text): self.text = text
        def raise_for_status(self): pass
        def json(self): return {"response": self.text}

    # the model forgets the required project both times: it is added before the closing line
    monkeypatch.setattr(cover.requests, "post", lambda *a, **k: calls.append(1) or Resp("Hi,\n\nI am applying.\n\nBest regards,\nAly Ahmed"))
    text, error = cover.generate(PROFILE, JOB)
    assert error == "" and MUST in text and text.index(MUST) < text.index("Best regards")
    assert len(calls) == 2                                       # it retried once first

    # the model remembers it: used as written, no retry, nothing added
    calls.clear()
    monkeypatch.setattr(cover.requests, "post", lambda *a, **k: calls.append(1) or Resp(f"Hi, I built {MUST}.\n\nBest regards,\nAly"))
    text, _ = cover.generate(PROFILE, JOB)
    assert text.count(MUST) == 1 and len(calls) == 1


def test_the_prompt_demands_the_required_project():
    assert f"MUST name {MUST}" in cover.build_prompt(PROFILE, JOB)


# ---------- safety net: refresh on open when the list is old ----------
def test_is_stale():
    from datetime import datetime, timedelta, timezone
    now = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)
    assert pipeline.is_stale(None, 8, now)                                          # never updated
    assert not pipeline.is_stale((now - timedelta(hours=5)).isoformat(), 8, now)    # 7:00 run worked, opened at noon
    assert pipeline.is_stale((now - timedelta(hours=9)).isoformat(), 8, now)         # older than 8 hours
    assert pipeline.is_stale((now - timedelta(hours=25)).isoformat(), 8, now)        # the 7:00 run failed


def test_opening_a_stale_dashboard_refreshes_once_and_a_fresh_one_does_not(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    calls = []
    monkeypatch.setattr(pipeline, "refresh", lambda conn, profile, **k: calls.append(1) or {"LinkedIn": 0})

    def open_app(last_refresh):
        monkeypatch.setattr(db, "get_meta", lambda conn, key: last_refresh if key == "last_refresh" else None)
        at = AppTest.from_file(APP, default_timeout=60)
        at.run()
        assert not at.exception, [e.value for e in at.exception]
        return at

    from datetime import datetime, timedelta, timezone
    fresh = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    old = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    open_app(fresh)
    assert calls == []                      # fresh list: nothing to do
    at = open_app(old)
    assert calls == [1]                     # old list: updated once
    at.run()
    assert calls == [1]                     # a second run in the same visit does not loop


def test_the_shipped_example_is_blank_but_still_works():
    cfg = EXAMPLE["cover_note"]
    assert cfg["facts"] == [] and cfg["always_mention"] == {"name": "", "sentence": ""}
    assert EXAMPLE["name"] == "Your Name" and EXAMPLE["gmail"] == "you@gmail.com"
    # no required project: the prompt has no "MUST name" rule, and nothing is inserted into a note
    assert "MUST name" not in cover.build_prompt({**EXAMPLE, "summary": ""}, JOB)
    assert cover.ensure_mentioned("Hi,\n\nBest regards,\nX", cfg) == "Hi,\n\nBest regards,\nX"
    # and without facts the cover-note button explains what to do instead of inventing a note
    text, error = cover.generate(EXAMPLE, JOB)
    assert text == "" and "profile.yaml" in error and "facts" in error
