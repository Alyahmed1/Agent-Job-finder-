"""Free remote-job sources: Remotive, Remote OK, We Work Remotely, Jobicy, Himalayas, Working Nomads.

The parse_* functions are pure (raw response in, jobs out) so they can be tested offline.
Every job keeps its own page URL and a source name; the page shows "via <source>" as these sites require.
"""
import json
import re
import time
import xml.etree.ElementTree as ET
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "WillyJobFinder/1.0 (personal job search, not redistributed)"}
TIMEOUT = 30

REMOTIVE_URL = "https://remotive.com/api/remote-jobs?limit=200"
REMOTEOK_URL = "https://remoteok.com/api"
JOBICY_URL = "https://jobicy.com/api/v2/remote-jobs?count=50&tag="
WORKINGNOMADS_URL = "https://www.workingnomads.com/api/exposed_jobs/"
HIMALAYAS_URL = "https://himalayas.app/jobs/api/search?worldwide=true&q="  # worldwide-eligible jobs only
WWR_FEEDS = [
    "remote-programming-jobs",
    "remote-back-end-programming-jobs",
    "remote-full-stack-programming-jobs",
    "remote-devops-sysadmin-jobs",
]

SOURCE_NAMES = ("Remotive", "Remote OK", "We Work Remotely", "Jobicy", "Himalayas", "Working Nomads")


def _text(html):
    """A feed's HTML description as plain text, cut to a sensible length."""
    return re.sub(r"\s+", " ", BeautifulSoup(html or "", "html.parser").get_text(" ")).strip()[:6000]


def _job(job_id, url, title, company, location, source, description=""):
    job = {
        "id": job_id,
        "url": url,
        "title": (title or "").strip(),
        "company": (company or "").strip(),
        "location": location,
        "source": source,
    }
    if description:  # only some feeds send the full text; the rest is fetched on demand (jobdesc.py)
        job["description"] = _text(description)
    return job


def parse_remotive(data):
    jobs = []
    for j in data.get("jobs", []):
        where = (j.get("candidate_required_location") or "Worldwide").strip()
        jobs.append(_job(f"remotive-{j['id']}", j["url"], j["title"], j.get("company_name"), f"{where} (Remote)", "Remotive"))
    return jobs


def parse_remoteok(data):
    """The first element is a legal notice, not a job."""
    jobs = []
    for j in data:
        if not isinstance(j, dict) or "position" not in j:
            continue
        where = (j.get("location") or "").strip() or "Worldwide"
        jobs.append(_job(f"remoteok-{j['id']}", j["url"], j["position"], j.get("company"), f"{where} (Remote)", "Remote OK"))
    return jobs


def parse_wwr(xml_text):
    """Titles look like 'Company: Job title'; the region says where applicants may live."""
    jobs = []
    for item in ET.fromstring(xml_text).iter("item"):
        raw_title = (item.findtext("title") or "").strip()
        company, _, title = raw_title.partition(": ")
        if not title:
            company, title = "", raw_title
        link = (item.findtext("link") or item.findtext("guid") or "").strip()
        slug = link.rstrip("/").rsplit("/", 1)[-1]
        if not slug:
            continue
        where = (item.findtext("region") or "").strip() or "Worldwide"
        jobs.append(_job(f"wwr-{slug}", link, title, company, f"{where} (Remote)", "We Work Remotely",
                         item.findtext("description")))
    return jobs


def parse_jobicy(data):
    """jobGeo says where applicants may live: 'Anywhere', 'USA', 'EMEA', ..."""
    jobs = []
    for j in data.get("jobs", []):
        where = (j.get("jobGeo") or "").strip() or "Worldwide"
        jobs.append(_job(f"jobicy-{j['id']}", j["url"], j["jobTitle"], j.get("companyName"), f"{where} (Remote)", "Jobicy"))
    return jobs


def parse_himalayas(data):
    """locationRestrictions is a list of countries; an empty list means open to everyone."""
    jobs = []
    for j in data.get("jobs", []):
        link = j.get("applicationLink") or j.get("guid") or ""
        slug = re.sub(r"\W+", "-", link.split("himalayas.app/")[-1]).strip("-")[:120]
        if not slug:
            continue
        where = ", ".join(j.get("locationRestrictions") or []) or "Worldwide"
        jobs.append(_job(f"himalayas-{slug}", link, j.get("title"), j.get("companyName"), f"{where} (Remote)", "Himalayas",
                         j.get("description")))
    return jobs


def parse_workingnomads(data):
    """Every job here is remote; 'location' says who may apply ('Global', 'USA only', 'CET +/- 3 hours'...)."""
    jobs = []
    for j in data:
        match = re.search(r"/(\d+)/?$", j.get("url") or "")
        if not match:
            continue
        where = (j.get("location") or "").strip() or "Worldwide"
        jobs.append(_job(f"workingnomads-{match.group(1)}", j["url"], j.get("title"), j.get("company_name"),
                         f"{where} (Remote)", "Working Nomads"))
    return jobs


def region_ok(location, allowed):
    """True when someone in Egypt can plausibly take the job: worldwide-style, or an allowed region."""
    where = re.sub(r"\(remote\)", "", location or "", flags=re.I).strip().lower()
    if where in ("", "remote", "remoto"):
        return True
    return any(word in where for word in allowed)


def _get(url):
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp


def fetch_remotive():
    return parse_remotive(_get(REMOTIVE_URL).json())


def fetch_remoteok():
    return parse_remoteok(json.loads(_get(REMOTEOK_URL).text))


def fetch_wwr():
    jobs, seen = [], set()
    for feed in WWR_FEEDS:
        for job in parse_wwr(_get(f"https://weworkremotely.com/categories/{feed}.rss").content):
            if job["id"] not in seen:
                seen.add(job["id"])
                jobs.append(job)
    return jobs


def _search(url, terms, parse):
    """One request per keyword (their 'latest jobs' lists are mostly sales/support, so we search for your roles)."""
    jobs, seen = [], set()
    for term in terms:
        for job in parse(_get(url + quote(term)).json()):
            if job["id"] not in seen:
                seen.add(job["id"])
                jobs.append(job)
        time.sleep(1)  # be polite between requests
    return jobs


def fetch_jobicy(terms):
    return _search(JOBICY_URL, terms, parse_jobicy)


def fetch_himalayas(terms):
    return _search(HIMALAYAS_URL, terms, parse_himalayas)


def fetch_workingnomads():
    return parse_workingnomads(_get(WORKINGNOMADS_URL).json())
