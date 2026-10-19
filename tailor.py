"""Tailor my CV: compare a job to your CV and say what to lead with and what you are missing.
Steps 3-4: plain code finds skills, the local model (Ollama) only writes one summary line, and
that line is checked so it can never name a tool your CV does not have."""
import re
import sys
from pathlib import Path

import requests
import yaml

from cover import OLLAMA_URL

CV_DATA = Path(__file__).parent / "cv_data.yaml"


def _t(name, *patterns):
    return name, re.compile("|".join(patterns), re.I)


def _w(word):
    return rf"(?<![\w+#.]){word}(?![\w+#])"


TERMS = dict([
    _t("Python", _w("python")), _t("Java", _w("java")), _t("JavaScript", _w("javascript"), _w("js")),
    _t("TypeScript", _w("typescript")), _t("C++", _w(r"c\+\+")), _t("C#", _w("c#")), _t(".NET", _w(r"\.net")),
    _t("Go", _w("golang")), _t("Rust", _w("(?-i:Rust)")), _t("SQL", _w("sql")), _t("PostgreSQL", _w("postgres(?:ql)?")),
    _t("MySQL", _w("mysql")), _t("MongoDB", _w("mongo(?:db)?")), _t("Redis", _w("redis")),
    _t("Elasticsearch", _w("elasticsearch")), _t("Kafka", _w("kafka")), _t("Spark", _w("pyspark"), _w("apache spark"), _w("(?-i:Spark)")),
    _t("Airflow", _w("airflow")), _t("dbt", _w("dbt")), _t("Snowflake", _w("snowflake")),
    _t("BigQuery", _w("bigquery")), _t("Databricks", _w("databricks")),
    _t("AWS", _w("aws"), _w("amazon web services")), _t("Azure", _w("azure")),
    _t("Google Cloud", _w("gcp"), _w("google cloud")), _t("Kubernetes", _w("kubernetes"), _w("k8s")),
    _t("Docker", _w("docker")), _t("Terraform", _w("terraform")), _t("CI/CD", _w(r"ci/cd"), _w("cicd")),
    _t("GitHub Actions", _w("github actions")), _t("Jenkins", _w("jenkins")), _t("Linux", _w("linux")),
    _t("FastAPI", _w("fastapi")), _t("Flask", _w("flask")), _t("Django", _w("django")),
    _t("Spring", _w("spring boot"), _w("spring framework")), _t("Node.js", _w(r"node(?:\.js|js)?")), _t("React", _w(r"react(?:\.js|js)"), _w("(?-i:React)")),
    _t("Next.js", _w(r"next\.?js")), _t("Vue", _w(r"vue(?:\.js)?")), _t("Angular", _w("angular")),
    _t("Flutter", _w("flutter")), _t("GraphQL", _w("graphql")), _t("REST APIs", _w("restful"), _w("rest apis?")),
    _t("PyTorch", _w("pytorch")), _t("TensorFlow", _w("tensorflow")),
    _t("scikit-learn", _w("scikit[- ]?learn"), _w("sklearn")), _t("Pandas", _w("pandas")), _t("NumPy", _w("numpy")),
    _t("Hugging Face", _w("hugging ?face"), _w("transformers")), _t("LangChain", _w("langchain")),
    _t("LlamaIndex", _w("llama ?index")), _t("OpenAI API", _w("openai")), _t("Claude API", _w("anthropic"), _w("claude")),
    _t("LLMs", _w("llms?"), _w("large language models?")), _t("RAG", _w("rag"), _w("retrieval[- ]augmented")),
    _t("Fine-tuning", _w(r"fine[- ]?tun\w*"), _w("lora")), _t("NLP", _w("nlp"), _w("natural language processing")),
    _t("Computer vision", _w("computer vision")), _t("MLOps", _w("mlops")), _t("MLflow", _w("mlflow")),
    _t("Vector databases", _w("vector (?:databases?|stores?|search)"), _w("chromadb"), _w("qdrant"), _w("faiss"),
       _w("pinecone")), _t("Prompt engineering", _w("prompt engineering")),
    _t("MCP", _w("mcp"), _w("model context protocol")), _t("AI agents", _w(r"agent(?:s|ic)?"), _w("multi-agent")),
    _t("XGBoost/LightGBM", _w("xgboost"), _w("lightgbm")), _t("Streamlit", _w("streamlit")),
    _t("Supabase", _w("supabase")), _t("Firebase", _w("firebase")), _t("SQLAlchemy", _w("sqlalchemy")),
    _t("Git", _w("git"), _w("github")), _t("Figma", _w("figma")),
])


def terms_in(text):
    return {name for name, rx in TERMS.items() if rx.search(text or "")}


def load_cv(path=CV_DATA):
    if not Path(path).exists():
        raise FileNotFoundError("Run `python cv_import.py` first so I can read your CV.")
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _items(cv):
    """Every job and project on the CV as (kind, name, text)."""
    out = [("job", f"{e['company']} ({e.get('role', '')})", " ".join([e.get("role", "")] + e["bullets"]))
           for e in cv["experience"]]
    out += [("project", p["name"], " ".join(p["stack"] + p["bullets"])) for p in cv["projects"]]
    return out


def cv_terms(cv):
    skills = " ".join(s for group in cv["skills"].values() for s in group)
    return terms_in(skills + " " + " ".join(text for _, _, text in _items(cv)))


def analyze(cv, job_text, title=""):
    """Plain code, no AI. Returns what you have, what you are missing, and what to lead with."""
    limited = len((job_text or "").split()) < 60  # a real posting is 150+ words; less is a title or a cut-off snippet
    wanted = terms_in(f"{title} {job_text or ''}")
    mine = cv_terms(cv)
    best = []
    for kind, name, text in _items(cv):
        matched = sorted(wanted & terms_in(text))
        if matched:
            best.append({"kind": kind, "name": name, "matched": matched})
    best.sort(key=lambda b: (-len(b["matched"]), b["kind"] != "job"))
    return {"have": sorted(wanted & mine), "missing": sorted(wanted - mine), "best": best[:3], "limited": limited}


PROMPT = """Write the first lines of a CV profile section, in 1 or 2 sentences. No "I". Start with a noun like "Machine Learning engineer who ...".
Use ONLY the facts below. Do not name any tool, language or skill that is not in the lists.
Plain and specific. No flattery, no buzzwords, no "extensive".

Job title to aim at: {title}
About the person: {summary}
Skills that fit this job: {have}
Work or projects that fit this job: {best}

Write the lines now:"""


def fallback_line(analysis):
    """Built by code when the model is down or breaks a rule. Uses only your own matched facts."""
    if not analysis["have"]:
        return ""
    skills = ", ".join(analysis["have"][:5])
    line = f"Engineer with hands-on experience in {skills}"
    if analysis["best"]:
        line += f", including {analysis['best'][0]['name']}"
    return line + "."


def summary_line(profile, cv, analysis, title, timeout=120, attempts=2):
    """Returns (text, note). The model is checked: if it names a tool your CV lacks it is retried, then replaced."""
    if not analysis["have"]:
        return "", "Nothing in this job matches your CV tools, so there is no tailored line to write."
    allowed = cv_terms(cv)
    prompt = PROMPT.format(
        title=title, summary=" ".join((profile.get("summary") or "").split()), have=", ".join(analysis["have"]),
        best="; ".join(f"{b['name']} ({', '.join(b['matched'])})" for b in analysis["best"]) or "none")
    for _ in range(attempts):
        try:
            resp = requests.post(OLLAMA_URL, json={"model": profile["cover_note"]["model"], "prompt": prompt,
                                                   "stream": False, "options": {"temperature": 0.3}}, timeout=timeout)
            resp.raise_for_status()
        except requests.RequestException:
            return fallback_line(analysis), "The local model isn't running, so this line was built by code."
        text = resp.json().get("response", "").strip().strip('"')
        if text and not terms_in(text) - allowed:
            return text, ""
    return fallback_line(analysis), "The model kept naming tools you don't have, so this line was built by code."


def tailor(profile, cv, job_text, title):
    analysis = analyze(cv, job_text, title)
    analysis["line"], analysis["line_note"] = summary_line(profile, cv, analysis, title)
    return analysis


if __name__ == "__main__":  # try it: python tailor.py <job id> ["pasted description"]
    import db
    import jobdesc
    from score import load_profile

    conn = db.connect()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (sys.argv[1],)).fetchone()
    text = sys.argv[2] if len(sys.argv) > 2 else row["description"] or ""
    if not text:
        text, err = jobdesc.fetch_description(row["url"])
        print(err) if err else db.save_description(conn, row["id"], text)
    result = tailor(load_profile(), load_cv(), text, row["title"])
    print(row["title"], "-", row["company"], "\n")
    for key in ("have", "missing", "best", "line", "line_note", "limited"):
        print(f"{key}: {result[key]}")
