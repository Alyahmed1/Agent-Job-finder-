"""Draft a short cover note with the free local model (Ollama). It only ever writes text; nothing is sent."""
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
    return ensure_mentioned(text, cfg), ""
