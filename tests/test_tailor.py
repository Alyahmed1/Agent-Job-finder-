import tailor

CV = {
    "skills": {"Languages": ["Python 3.11+", "SQL"], "Backend": ["FastAPI", "Flask"], "Frontend": ["React"]},
    "experience": [{"company": "Acme", "role": "Backend Intern", "dates": "2025",
                    "bullets": ["Built FastAPI services with PostgreSQL and Docker."]}],
    "projects": [{"name": "Legato", "stack": ["ChromaDB", "Flutter"], "bullets": ["Built a RAG system for legal text."]}],
}
JOB = "We need a Python and FastAPI engineer with Kubernetes, AWS and RAG experience. We spark curiosity and react quickly."
PROFILE = {"summary": "ML engineer.", "cover_note": {"model": "m"}}


def test_have_and_missing_are_found_without_false_hits():
    a = tailor.analyze(CV, JOB, "Backend Engineer")
    assert a["have"] == ["FastAPI", "Python", "RAG"]
    assert a["missing"] == ["AWS", "Kubernetes"]  # "spark" and "react" as plain verbs are not tools


def test_skill_used_in_a_bullet_counts_even_if_not_in_the_skills_list():
    assert "Docker" in tailor.analyze(CV, "Docker needed. " * 20)["have"]


def test_best_items_are_ranked_by_overlap():
    best = tailor.analyze(CV, JOB)["best"]
    assert [b["name"] for b in best] == ["Acme (Backend Intern)", "Legato"]
    assert best[0]["matched"] == ["FastAPI", "Python"] or "FastAPI" in best[0]["matched"]


def test_short_text_is_flagged_limited():
    assert tailor.analyze(CV, "", "Python Engineer")["limited"] is True
    assert tailor.analyze(CV, JOB * 4)["limited"] is False


class Reply:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass

    def json(self):
        return {"response": self.text}


def test_model_line_that_names_a_missing_tool_is_never_used(monkeypatch):
    monkeypatch.setattr(tailor.requests, "post", lambda *a, **k: Reply("Engineer who ships Python services on Kubernetes."))
    text, note = tailor.summary_line(PROFILE, CV, tailor.analyze(CV, JOB), "Backend Engineer")
    assert "Kubernetes" not in text and "AWS" not in text
    assert text.startswith("Engineer with hands-on experience in FastAPI, Python, RAG")
    assert "built by code" in note


def test_clean_model_line_is_used(monkeypatch):
    monkeypatch.setattr(tailor.requests, "post", lambda *a, **k: Reply("Backend engineer who builds Python and FastAPI services."))
    text, note = tailor.summary_line(PROFILE, CV, tailor.analyze(CV, JOB), "Backend Engineer")
    assert text == "Backend engineer who builds Python and FastAPI services." and note == ""


def test_model_down_falls_back_to_code(monkeypatch):
    def down(*a, **k):
        raise tailor.requests.ConnectionError()

    monkeypatch.setattr(tailor.requests, "post", down)
    text, note = tailor.summary_line(PROFILE, CV, tailor.analyze(CV, JOB), "Backend Engineer")
    assert text and "isn't running" in note


def test_no_overlap_gives_no_line():
    text, note = tailor.summary_line(PROFILE, CV, tailor.analyze(CV, "Cobol and Fortran only. " * 10), "Dev")
    assert text == "" and note
