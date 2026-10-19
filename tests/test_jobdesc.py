import json

import jobdesc
from db import connect, save_description, save_job


def test_reads_linkedin_description_box():
    html = '<div class="show-more-less-html__markup"><p>Build <b>RAG</b> systems.</p><ul><li>Python</li></ul></div>'
    assert jobdesc.parse_description(html) == "Build RAG systems. Python"


def test_reads_standard_job_posting_data():
    ld = json.dumps({"@type": "JobPosting", "description": "<p>We use <b>FastAPI</b> and Docker.</p>"})
    assert jobdesc.parse_description(f'<script type="application/ld+json">{ld}</script>') == "We use FastAPI and Docker."


def test_falls_back_to_article_and_returns_empty_when_nothing_found():
    assert jobdesc.parse_description("<article>Python  and\n SQL</article>") == "Python and SQL"
    assert jobdesc.parse_description("<div>menu</div>") == ""


def test_long_text_is_cut():
    assert len(jobdesc.parse_description("<article>" + "word " * 5000 + "</article>")) <= jobdesc.MAX_CHARS


def test_short_page_gives_error_not_text(monkeypatch):
    class Resp:
        text = "<article>Too short</article>"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(jobdesc.requests, "get", lambda *a, **k: Resp())
    text, err = jobdesc.fetch_description("https://x.test/job")
    assert text == "" and "title" in err


def test_description_is_stored_once(tmp_path):
    conn = connect(tmp_path / "t.db")
    save_job(conn, {"id": "1", "title": "t", "company": "c", "location": "l", "url": "u", "source": "s",
                    "score": 1, "reason": "r", "missing": ""})
    save_description(conn, "1", "Full text")
    assert conn.execute("SELECT description FROM jobs WHERE id='1'").fetchone()[0] == "Full text"


def test_linkedin_pages_are_never_requested(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("must not call LinkedIn")

    monkeypatch.setattr(jobdesc.requests, "get", boom)
    text, err = jobdesc.fetch_description("https://www.linkedin.com/jobs/view/123/")
    assert text == "" and "LinkedIn" in err
