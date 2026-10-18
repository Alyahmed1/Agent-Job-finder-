"""Learn from your clicks. Jobs you hide push similar jobs down; jobs you save or apply to push them up.

Everything is computed from the saved statuses each time (nothing hidden is stored), and every effect
shows up on the card as a chip such as: You often hide ".net" -8
"""
import re
from collections import Counter

MAX_PENALTY, MAX_BOOST = -15, 10
# How many clicks it takes before the agent acts (raised a little so one bad week does not change your list).
MIN_TOKEN_HIDES = 4      # was 3: hide 4 jobs with the same word
MIN_TOKEN_LIKES = 3      # was 2: save or apply to 3 jobs with the same word
MIN_COMPANY_HIDES = 3    # was 2: hide 3 jobs from the same company

# Words that appear in almost every job title say nothing about taste.
STOP = {
    "engineer", "developer", "software", "senior", "junior", "lead", "staff", "specialist", "manager", "remote",
    "full", "time", "part", "and", "the", "for", "with", "of", "in", "at", "to", "a", "an", "on", "us", "ii", "iii",
    "i", "iv", "new", "team", "hybrid", "site", "contract", "intern", "internship", "graduate", "entry", "level",
}

HIDDEN, LIKED = ("rejected",), ("saved", "applied")


def tokens(title):
    return set(re.findall(r"[a-z0-9][a-z0-9+#.\-]+", (title or "").lower())) - STOP


def _company(name):
    return re.sub(r"\W+", " ", (name or "").lower()).strip()


def build_model(rows):
    """rows: anything with title, company, status. Returns the lists of effects to apply."""
    hidden_t, liked_t, hidden_c, liked_c = Counter(), Counter(), Counter(), Counter()
    names = {}
    for r in rows:
        status = r["status"]
        if status not in HIDDEN + LIKED:
            continue
        toks, comp = tokens(r["title"]), _company(r["company"])
        names.setdefault(comp, (r["company"] or "").strip())
        (hidden_t if status in HIDDEN else liked_t).update(toks)
        (hidden_c if status in HIDDEN else liked_c)[comp] += 1

    token_effects, company_effects = {}, {}
    for t in set(hidden_t) | set(liked_t):
        h, l = hidden_t[t], liked_t[t]
        if h >= MIN_TOKEN_HIDES and h > 2 * l:
            token_effects[t] = (f'You often hide "{t}"', -8)
        elif l >= MIN_TOKEN_LIKES and l > 2 * h:
            token_effects[t] = (f'You like "{t}"', 5)
    for c in set(hidden_c) | set(liked_c):
        if not c:
            continue
        h, l = hidden_c[c], liked_c[c]
        if h >= MIN_COMPANY_HIDES and l == 0:
            company_effects[c] = (f"You hid {h} jobs from {names[c]}", -10)
        elif l >= 1 and h == 0:
            company_effects[c] = (f"You liked {names[c]}", 5)
    return {"tokens": token_effects, "companies": company_effects}


def adjust(model, job):
    """[(label, points)] for one job, capped so your clicks can never overrule everything else."""
    if not model:
        return []
    found = [model["tokens"][t] for t in tokens(job["title"]) if t in model["tokens"]]
    found += [model["companies"][c] for c in [_company(job["company"])] if c in model["companies"]]
    out, total = [], 0
    for label, points in sorted(found, key=lambda x: -abs(x[1])):
        if MAX_PENALTY <= total + points <= MAX_BOOST:
            out.append((label, points))
            total += points
    return out
