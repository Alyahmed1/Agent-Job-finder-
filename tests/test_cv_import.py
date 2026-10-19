from cv_import import parse_cv, split_items

LINES = [
    "ALY AHMED",
    "TECHNICAL SKILLS",
    "Languages: Python 3.11+, SQL",
    "LLMs: Claude API, fine-tuning (LoRA, QLoRA), RAG pipelines, multi-agent",
    "systems, MCP",
    "WORK EXPERIENCE",
    "Acme | Backend Intern",
    "June 2025 – July 2025 | Cairo",
    "• Built an API with FastAPI that served",
    "300 users.",
    "Beta Co | Data Intern",
    "May 2024 | Remote",
    "• Cleaned data.",
    "PROJECTS",
    "Legato — Legal AI | github.com/x",
    "Graduation Project · FastAPI · ChromaDB",
    "• Built RAG.",
    "EDUCATION",
]


def test_skills_split_outside_brackets_and_join_wrapped_lines():
    skills = parse_cv(LINES)["skills"]
    assert skills["Languages"] == ["Python 3.11+", "SQL"]
    assert skills["LLMs"] == ["Claude API", "fine-tuning (LoRA, QLoRA)", "RAG pipelines", "multi-agent systems", "MCP"]
    assert split_items("a (b, c), d") == ["a (b, c)", "d"]


def test_jobs_and_projects_keep_their_own_bullets_with_wrapped_lines_joined():
    cv = parse_cv(LINES)
    assert [(j["company"], j["role"]) for j in cv["experience"]] == [("Acme", "Backend Intern"), ("Beta Co", "Data Intern")]
    assert cv["experience"][0]["bullets"] == ["Built an API with FastAPI that served 300 users."]
    assert cv["experience"][1]["bullets"] == ["Cleaned data."]
    assert cv["projects"] == [{"name": "Legato", "stack": ["Graduation Project", "FastAPI", "ChromaDB"],
                               "bullets": ["Built RAG."]}]
