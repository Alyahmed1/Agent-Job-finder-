"""Turn a LinkedIn alert email (HTML) into a list of jobs."""
import re

from bs4 import BeautifulSoup

JOB_ID = re.compile(r"jobs/view/(\d+)")
NOISE = re.compile(
    r"^(easy apply|actively recruiting|be an early applicant|\d+ (school alumni|connections?|applicants?).*|"
    r"promoted|view job|apply now|new|\d+[hdw] ago|\d+ (hours?|days?|weeks?) ago)$",
    re.I,
)


def _pieces(node):
    return [p for p in (x.strip() for x in node.get_text("|", strip=True).split("|")) if p and not NOISE.match(p)]


def _split_company_location(line):
    """'Coca-Cola HBC · New Cairo (Hybrid)' -> ('Coca-Cola HBC', 'New Cairo (Hybrid)')."""
    if "·" in line:
        company, location = line.split("·", 1)
        return company.strip(), location.strip()
    return line.strip(), ""


def _job_from_anchor(anchor):
    """Walk up from a job link to the smallest ancestor that has the job's text."""
    node = anchor
    for _ in range(6):
        ids = {m.group(1) for a in node.find_all("a", href=JOB_ID) for m in [JOB_ID.search(a["href"])] if m}
        if len(ids) > 1:
            return None  # climbed too far: this container holds several jobs
        pieces = _pieces(node)
        if len(pieces) >= 2 and not pieces[0].lower().startswith("jobs similar"):
            company, location = _split_company_location(pieces[1])
            return {"title": pieces[0], "company": company, "location": location}
        if node.parent is None:
            return None
        node = node.parent
    return None


def parse_alert_html(html, source=""):
    soup = BeautifulSoup(html, "html.parser")
    jobs = {}
    for a in soup.find_all("a", href=JOB_ID):
        job_id = JOB_ID.search(a["href"]).group(1)
        if job_id in jobs:
            continue
        details = _job_from_anchor(a)
        if details:
            jobs[job_id] = {
                "id": job_id,
                "url": f"https://www.linkedin.com/jobs/view/{job_id}/",
                "source": source,
                **details,
            }
    return list(jobs.values())
