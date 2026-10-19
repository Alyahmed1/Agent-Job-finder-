import json

import db
import pipeline
from collect import feeds
from score import load_profile

REMOTIVE = {"jobs": [
    {"id": 1, "url": "https://remotive.com/remote-jobs/x-1", "title": "Machine Learning Engineer", "company_name": "Acme",
     "candidate_required_location": "Worldwide"},
    {"id": 2, "url": "https://remotive.com/remote-jobs/x-2", "title": "Backend Developer", "company_name": "UsaCo",
     "candidate_required_location": "USA"},
]}
REMOTEOK = [
    {"last_updated": 1, "legal": "terms"},
    {"id": "10", "url": "https://remoteOK.com/remote-jobs/10", "position": "Data Engineer", "company": "Globex", "location": ""},
]
WWR = b"""<?xml version="1.0"?><rss><channel><item>
  <title>Initech: Full Stack Engineer</title><region>Anywhere in the World</region>
  <link>https://weworkremotely.com/remote-jobs/initech-full-stack-engineer</link></item></channel></rss>"""


def test_parsers_give_one_shape_with_prefixed_ids_and_sources():
    r = feeds.parse_remotive(REMOTIVE)
    assert r[0] == {"id": "remotive-1", "url": "https://remotive.com/remote-jobs/x-1", "title": "Machine Learning Engineer",
                    "company": "Acme", "location": "Worldwide (Remote)", "source": "Remotive"}
    o = feeds.parse_remoteok(REMOTEOK)
    assert [j["id"] for j in o] == ["remoteok-10"] and o[0]["location"] == "Worldwide (Remote)"
    w = feeds.parse_wwr(WWR)
    assert w[0]["company"] == "Initech" and w[0]["title"] == "Full Stack Engineer"
    assert w[0]["id"] == "wwr-initech-full-stack-engineer" and w[0]["source"] == "We Work Remotely"


def test_region_filter_drops_country_locked_jobs():
    ok = load_profile()["feeds"]["regions_ok"]
    assert feeds.region_ok("Worldwide (Remote)", ok)
    assert feeds.region_ok("Remote", ok) and feeds.region_ok("", ok)
    assert feeds.region_ok("EMEA, Africa (Remote)", ok)
    assert not feeds.region_ok("USA (Remote)", ok)
    assert not feeds.region_ok("Remote - US", ok)


def _fake_sources(monkeypatch, jobs_by_source):
    monkeypatch.setattr(pipeline, "SOURCES", {name: (lambda *_, j=jobs: j) for name, jobs in jobs_by_source.items()})


def test_refresh_feeds_keeps_matching_worldwide_jobs_only_once(tmp_path, monkeypatch):
    profile, conn = load_profile(), db.connect(tmp_path / "t.db")
    _fake_sources(monkeypatch, {
        "Remotive": feeds.parse_remotive(REMOTIVE),   # ML (worldwide) kept, Backend (USA) dropped
        "Remote OK": feeds.parse_remoteok(REMOTEOK),
        "We Work Remotely": feeds.parse_wwr(WWR),
    })
    report = pipeline.refresh_feeds(conn, profile, force=True)
    assert report == {"Remotive": 1, "Remote OK": 1, "We Work Remotely": 1}
    titles = {r["title"] for r in conn.execute("SELECT title FROM jobs")}
    assert titles == {"Machine Learning Engineer", "Data Engineer", "Full Stack Engineer"}
    # running again adds nothing: same ids and same title+company are skipped
    assert pipeline.refresh_feeds(conn, profile, force=True) == {"Remotive": 0, "Remote OK": 0, "We Work Remotely": 0}


def test_same_job_on_two_sites_is_saved_once(tmp_path, monkeypatch):
    profile, conn = load_profile(), db.connect(tmp_path / "t.db")
    twin = dict(feeds.parse_remoteok(REMOTEOK)[0], id="wwr-twin", source="We Work Remotely")
    _fake_sources(monkeypatch, {"Remote OK": feeds.parse_remoteok(REMOTEOK), "We Work Remotely": [twin]})
    pipeline.refresh_feeds(conn, profile, force=True)
    assert conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1


def test_cooldown_skips_a_source_fetched_recently(tmp_path, monkeypatch):
    profile, conn = load_profile(), db.connect(tmp_path / "t.db")
    calls = []
    monkeypatch.setattr(pipeline, "SOURCES", {"Remotive": lambda: calls.append(1) or []})
    pipeline.refresh_feeds(conn, profile)           # first time: fetches
    report = pipeline.refresh_feeds(conn, profile)  # right after: skipped
    assert len(calls) == 1 and report["Remotive"].startswith("skipped")


def test_one_broken_source_does_not_stop_the_others(tmp_path, monkeypatch):
    profile, conn = load_profile(), db.connect(tmp_path / "t.db")

    def boom():
        raise ConnectionError("down")

    monkeypatch.setattr(pipeline, "SOURCES", {"Remotive": boom, "Remote OK": lambda: feeds.parse_remoteok(REMOTEOK)})
    report = pipeline.refresh_feeds(conn, profile, force=True)
    assert report["Remotive"].startswith("failed") and report["Remote OK"] == 1
    assert pipeline.total_new(report) == 1


JOBICY = {"jobs": [
    {"id": 7, "url": "https://jobicy.com/jobs/7-ai-engineer", "jobTitle": "AI Engineer", "companyName": "Canonical", "jobGeo": "Anywhere"},
    {"id": 8, "url": "https://jobicy.com/jobs/8-x", "jobTitle": "Backend Developer", "companyName": "UkCo", "jobGeo": "UK"},
]}
HIMALAYAS = {"jobs": [
    {"title": "Data Engineer", "companyName": "Globex", "locationRestrictions": [], "guid": "https://himalayas.app/companies/globex/jobs/data-engineer",
     "applicationLink": "https://himalayas.app/companies/globex/jobs/data-engineer"},
    {"title": "Backend Developer", "companyName": "GermanCo", "locationRestrictions": ["Germany"],
     "applicationLink": "https://himalayas.app/companies/germanco/jobs/backend-developer"},
]}


def test_jobicy_and_himalayas_parsers():
    j = feeds.parse_jobicy(JOBICY)
    assert j[0] == {"id": "jobicy-7", "url": "https://jobicy.com/jobs/7-ai-engineer", "title": "AI Engineer",
                    "company": "Canonical", "location": "Anywhere (Remote)", "source": "Jobicy"}
    h = feeds.parse_himalayas(HIMALAYAS)
    assert h[0]["id"] == "himalayas-companies-globex-jobs-data-engineer"
    assert h[0]["location"] == "Worldwide (Remote)" and h[1]["location"] == "Germany (Remote)"
    assert h[0]["source"] == "Himalayas" and h[0]["url"].startswith("https://himalayas.app/")


def test_new_sources_keep_worldwide_and_drop_country_locked(tmp_path, monkeypatch):
    profile, conn = load_profile(), db.connect(tmp_path / "t.db")
    _fake_sources(monkeypatch, {"Jobicy": feeds.parse_jobicy(JOBICY), "Himalayas": feeds.parse_himalayas(HIMALAYAS)})
    report = pipeline.refresh_feeds(conn, profile, force=True)
    assert report == {"Jobicy": 1, "Himalayas": 1}      # UK-only and Germany-only jobs are dropped
    assert {r["title"] for r in conn.execute("SELECT title FROM jobs")} == {"AI Engineer", "Data Engineer"}


def test_every_source_has_a_cooldown_and_a_card_label():
    import ui
    cooldowns = load_profile()["feeds"]["cooldown_hours"]
    assert set(pipeline.SOURCES) == set(feeds.SOURCE_NAMES) == set(cooldowns) == set(ui.FEED_SOURCES)


def test_searchable_sources_get_the_keywords_from_the_profile(tmp_path, monkeypatch):
    profile, conn = load_profile(), db.connect(tmp_path / "t.db")
    got = {}
    monkeypatch.setattr(pipeline, "SOURCES", {
        "Jobicy": lambda terms: got.setdefault("Jobicy", terms) and [],
        "Remotive": lambda: got.setdefault("Remotive", "no keywords") and [],
    })
    pipeline.refresh_feeds(conn, profile, force=True)
    assert got["Jobicy"] == profile["feeds"]["search_terms"] and "machine learning" in got["Jobicy"]
    assert got["Remotive"] == "no keywords"


WORKINGNOMADS = [
    {"url": "https://www.workingnomads.com/job/go/111/", "title": "ML Engineer", "company_name": "Acme", "location": "Global"},
    {"url": "https://www.workingnomads.com/job/go/112/", "title": "Backend Developer", "company_name": "UsCo", "location": "USA, Canada, Ireland or UK only"},
    {"url": "https://www.workingnomads.com/job/go/113/", "title": "Data Engineer", "company_name": "EuCo", "location": "Time zone: CET (+/- 3 hours)"},
    {"title": "No link", "company_name": "x"},
]


def test_working_nomads_parser_and_region_filter(tmp_path, monkeypatch):
    jobs = feeds.parse_workingnomads(WORKINGNOMADS)
    assert [j["id"] for j in jobs] == ["workingnomads-111", "workingnomads-112", "workingnomads-113"]
    assert jobs[0]["location"] == "Global (Remote)" and jobs[0]["source"] == "Working Nomads"
    profile, conn = load_profile(), db.connect(tmp_path / "t.db")
    _fake_sources(monkeypatch, {"Working Nomads": jobs})
    assert pipeline.refresh_feeds(conn, profile, force=True) == {"Working Nomads": 1}  # only the 'Global' job


def test_himalayas_and_wwr_keep_description_as_plain_text():
    from collect.feeds import parse_himalayas, parse_wwr

    him = parse_himalayas({"jobs": [{"title": "ML Engineer", "companyName": "Acme", "guid": "https://himalayas.app/companies/acme/jobs/ml",
                                     "description": "<p>Use <b>PyTorch</b> daily.</p>"}]})
    assert him[0]["description"] == "Use PyTorch daily."
    xml = "<rss><channel><item><title>Acme: ML Eng</title><link>https://weworkremotely.com/remote-jobs/x</link><description>&lt;p&gt;Python&lt;/p&gt;</description></item></channel></rss>"
    assert parse_wwr(xml)[0]["description"] == "Python"
