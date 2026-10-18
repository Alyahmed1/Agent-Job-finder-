"""Score a job against the profile with simple, explainable rules (instant and free).

The reason string lists every rule that fired with its points, e.g.
"Tier 1: AI / ML / GenAI +70 | Egypt +10 | junior-friendly +10", so the page can show why.
"""
import re
from pathlib import Path

import yaml

import learn
from classify import EGYPT_CITIES

SENIOR = re.compile(r"\b(senior|sr\.?|lead|principal|staff|architect)\b", re.I)
MANAGEMENT = re.compile(r"\b(head|manager|director)\b", re.I)
JUNIOR = re.compile(r"\b(junior|jr\.?|graduate|entry|intern|trainee|early career|associate)\b", re.I)
STACK_MISMATCH = re.compile(r"\.net|dotnet|odoo|servicenow|\bsap\b|\bphp\b|laravel|salesforce|dynamics", re.I)


def load_profile(path=None):
    """profile.yaml (private, yours) if it exists, otherwise profile.example.yaml."""
    root = Path(__file__).resolve().parent
    path = path or (root / "profile.yaml" if (root / "profile.yaml").exists() else root / "profile.example.yaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def score_job(profile, job, model=None):
    title = job["title"]
    where = (job["location"] or "").lower()
    adj = profile["adjustments"]

    points, notes = profile["no_match_points"], [("no target role in title", profile["no_match_points"])]
    demote = None
    for tier in profile["priority_tiers"]:
        if not any(re.search(k, title, re.I) for k in tier["keywords"]):
            continue
        if tier.get("needs_role") and not re.search(profile["role_words"], title, re.I):
            continue
        points, notes = tier["points"], [(tier["name"], tier["points"])]
        demote = tier.get("demote")
        break

    def add(label, delta):
        nonlocal points
        points += delta
        notes.append((label, delta))

    if any(city in where for city in EGYPT_CITIES):
        add("Egypt", adj["egypt"])
    if JUNIOR.search(title):
        add("junior-friendly", adj["junior"])
    elif MANAGEMENT.search(title):
        add("management role", adj["management"])
    elif SENIOR.search(title):
        add("senior role", adj["senior"])
    if STACK_MISMATCH.search(title):
        add("stack mismatch", adj["stack_mismatch"])
    if re.search(profile["off_target_words"], title, re.I):
        add("not an engineering role", adj["off_target"])

    # Keep the job in its tier but push it toward the bottom of that tier's range.
    if demote and any(re.search(k, title, re.I) for k in demote["keywords"]) and points > demote["cap"]:
        add(demote["label"], demote["cap"] - points)

    for label, delta in learn.adjust(model, job):  # what your own clicks taught us
        add(label, delta)

    reason = " | ".join(f"{label} {delta:+d}" for label, delta in notes)
    return {"score": max(0, min(100, points)), "reason": reason, "missing": ""}
