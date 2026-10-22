"""Draft a short cover note with the free local model (Ollama). It only ever writes text; nothing is sent."""
import re

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"

PROMPT = """You are {name}, applying for a job. Write your own short cover note, in the FIRST PERSON ("I", "my").

Rules:
- 4 to 5 sentences. Start with "Hi," and end with "Best regards," then "{name}".
- Sentence 1: say you are applying for the {title} role at {company}.
- Next 2 to 3 sentences: pick the facts below that fit this job best and describe them as things YOU did.
- Last sentence: say you would be glad to talk.
- Use ONLY the facts below. Never invent experience, numbers, tools or companies.
{must_rule}- A project may belong only to the place the fact says. PERSONAL PROJECTs are not work for any company; say "in a personal project".
- Do not explain how the facts relate to the job's duties or values. Just state what you did.
- Do not say "extensive". You are early in your career.
- Plain and specific. No flattery, no buzzwords. Never write "you" about {name}.

My summary: {summary}
My facts:
{facts}

The job: {title} at {company} ({location})

Write the cover note now:"""


def required_project(cfg):
    """The project every note must name, or "" when the profile leaves it empty."""
    return ((cfg.get("always_mention") or {}).get("name") or "").strip()


def build_prompt(profile, job):
    cfg = profile["cover_note"]
    must = required_project(cfg)
    return PROMPT.format(
        name=profile["name"],
        must_rule=f"- You MUST name {must} in one sentence, as a personal project, and say what it is.\n" if must else "",
        summary=" ".join((profile.get("summary") or "").split()),
        facts="\n".join(f"- {f}" for f in cfg.get("facts") or []),
        title=job["title"],
        company=job["company"] or "your company",
        location=job["location"] or "not stated",
    )


def ensure_mentioned(text, cfg):
    """A small model sometimes forgets a rule, so the required project is guaranteed here."""
    name, sentence = required_project(cfg), ((cfg.get("always_mention") or {}).get("sentence") or "").strip()
    if not name or not sentence or name.lower() in text.lower():
        return text
    cut = text.rfind("Best regards")
    if cut == -1:
        return text.rstrip() + "\n\n" + sentence
    return text[:cut].rstrip() + " " + sentence + "\n\n" + text[cut:]


CLOSING = "I would be glad to talk."
_CLOSING_WORDS = re.compile(r"\b(glad|happy|look forward|talk|discuss|chat)\b", re.I)
_SKIP = set("""with that this their which have also well into from about would could these those where while than then them they
    your more most such other some when what will been being were just only over very much many each both between through
    built build developed created designed worked work internship intern project projects personal role company team position
    experience skills skill using used apply applying applied hope believe strong great excellent""".split())


def _stems(text):
    """First 5 letters of every meaningful word, so 'automate' matches 'automates'."""
    return {w[:5] for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in _SKIP}


def _supported(sentence, known, share=0.6):
    """A small model invents job-fit claims. Keep a sentence only if most of its words come from your own facts."""
    words = _stems(sentence)
    return not words or sum(w in known for w in words) / len(words) >= share


def _names(facts):
    """(employers, personal project names) read from the facts, e.g. 'Schneider Electric' and 'Legato'."""
    work = " ".join(f for f in facts if f.startswith("WORK"))
    mine = " ".join(f for f in facts if f.startswith("PERSONAL PROJECT"))
    employers = re.findall(r"(?:WORK \(|at )([A-Z][\w&]*(?: [A-Z][\w&]*)*)", work)
    projects = re.findall(r"built\s+(?:an?\s+)?([A-Z][\w]*(?:\s+[A-Z][\w]*)?)", mine)
    return employers, projects


def _mixes_up(sentence, employers, projects):
    """A personal project must never be credited to an employer or an internship."""
    low = sentence.lower()
    has_project = any(p.lower() in low for p in projects)
    return has_project and (any(e.lower() in low for e in employers) or "intern" in low)


def finalize(text, profile, job):
    """Opener written by code, only fact-based sentences, the required project, a closing line, then the sign-off."""
    cfg, name = profile["cover_note"], profile["name"]
    facts = cfg.get("facts") or []
    employers, projects = _names(facts)
    body = re.sub(r"(?is)\bbest regards\b.*$", "", text)
    body = re.sub(r"(?i)^\s*(hi|hello|dear)\b[^\n,]*,\s*", "", body).strip()
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", " ".join(body.split())) if s]
    known = _stems(" ".join([profile.get("summary") or "", *facts]))
    opener = f"I am applying for the {job['title']} role at {job['company'] or 'your company'}."
    middle = [s for s in sentences if not re.search(r"\bapplying\b", s, re.I) and not _mixes_up(s, employers, projects)
              and (_supported(s, known) or _CLOSING_WORDS.search(s))]
    closing = next((s for s in middle if _CLOSING_WORDS.search(s)), CLOSING)
    middle = [s for s in middle if s is not closing]
    must, sentence = required_project(cfg), ((cfg.get("always_mention") or {}).get("sentence") or "").strip()
    if must and sentence and must.lower() not in " ".join(middle).lower():
        middle.append(sentence)
    return f"Hi,\n\n{' '.join([opener, *middle])}\n\n{closing}\n\nBest regards,\n{name}"


def generate(profile, job, timeout=180, attempts=2):
    """Returns (text, error). Exactly one of them is empty."""
    cfg = profile["cover_note"]
    if not cfg.get("facts"):
        return "", "Add a few true facts about yourself in profile.yaml (cover_note: facts), then try again."
    text = ""
    for _ in range(attempts):  # one retry if the model leaves the required project out
        try:
            resp = requests.post(
                OLLAMA_URL,
                json={"model": cfg["model"], "prompt": build_prompt(profile, job), "stream": False,
                      "options": {"temperature": 0.4}},
                timeout=timeout,
            )
            resp.raise_for_status()
            text = resp.json().get("response", "").strip()
        except requests.RequestException:
            return "", "The local model isn't running. Start Ollama, then try again."
        if text and required_project(cfg).lower() in text.lower():
            break
    if not text:
        return "", "The model returned nothing. Try again."
    return finalize(text, profile, job), ""
