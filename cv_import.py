"""Read your CV (.docx or .pdf) into cv_data.yaml: skills, work experience and projects, copied word for word.
Plain code only, no AI, so nothing can be invented. Usage: python cv_import.py [path-to-cv]"""
import argparse
from pathlib import Path

import yaml

DEFAULT_CV = Path.home() / "Desktop" / "cv" / "Aly_Ahmed_CV.docx"
OUT = Path(__file__).parent / "cv_data.yaml"
SECTIONS = {"PROFILE", "TECHNICAL SKILLS", "WORK EXPERIENCE", "PROJECTS", "EDUCATION", "CERTIFICATIONS",
            "ADDITIONAL INFORMATION"}


def read_lines(path):
    path = Path(path)
    if path.suffix.lower() == ".docx":
        import docx

        return [("• " if "List" in p.style.name else "") + p.text.strip() for p in docx.Document(path).paragraphs
                if p.text.strip()]
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        text = "\n".join(page.extract_text() for page in PdfReader(path).pages)
        return [ln.strip() for ln in text.splitlines() if ln.strip()]
    raise ValueError("Give me a .docx or .pdf file.")


def split_sections(lines):
    out, current = {}, None
    for ln in lines:
        if ln.upper() in SECTIONS and ln == ln.upper():
            current = out.setdefault(ln, [])
        elif current is not None:
            current.append(ln)
    return out


def split_items(text):
    """Split on commas that are not inside brackets: 'fine-tuning (LoRA, QLoRA), RAG' -> two items."""
    items, depth, buf = [], 0, ""
    for ch in text:
        depth += (ch == "(") - (ch == ")")
        if ch == "," and depth == 0:
            items.append(buf.strip())
            buf = ""
        else:
            buf += ch
    return [i for i in items + [buf.strip()] if i]


def parse_skills(lines):
    groups, label = {}, None
    for ln in lines:
        head, sep, rest = ln.partition(":")
        if sep and len(head) < 30:
            label, groups[head.strip()] = head.strip(), rest.strip()
        elif label:  # a wrapped line belongs to the group above it
            groups[label] += " " + ln
    return {k: split_items(v) for k, v in groups.items()}


def parse_blocks(lines):
    """Blocks start at 'Title | something'; the next line is meta (dates, or the tech stack); '•' lines are bullets."""
    blocks, block, meta_next = [], None, False
    for ln in lines:
        if ln.startswith("•"):
            block["bullets"].append(ln.lstrip("• ").strip())
        elif " | " in ln and not meta_next:
            block, meta_next = {"title": ln.split(" | ")[0].strip(), "role": ln.partition(" | ")[2].strip(),
                                "meta": "", "bullets": []}, True
            blocks.append(block)
        elif block and meta_next:
            block["meta"], meta_next = ln, False
        elif block and block["bullets"]:
            block["bullets"][-1] += " " + ln  # wrapped bullet line (PDF)
    return blocks


def parse_cv(lines):
    sec = split_sections(lines)
    experience = parse_blocks(sec.get("WORK EXPERIENCE", []))
    projects = parse_blocks(sec.get("PROJECTS", []))
    for p in projects:
        p["name"] = p["title"].split(" — ")[0].strip()
        p["stack"] = [t.strip() for t in p["meta"].split("·") if t.strip()]
    return {
        "skills": parse_skills(sec.get("TECHNICAL SKILLS", [])),
        "experience": [{"company": b["title"], "role": b["role"], "dates": b["meta"], "bullets": b["bullets"]} for b in experience],
        "projects": [{"name": p["name"], "stack": p["stack"], "bullets": p["bullets"]} for p in projects],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cv", nargs="?", default=DEFAULT_CV)
    data = parse_cv(read_lines(ap.parse_args().cv))
    OUT.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")
    print(f"Wrote {OUT.name}: {sum(len(v) for v in data['skills'].values())} skills, "
          f"{len(data['experience'])} jobs, {len(data['projects'])} projects. Please read it and fix anything wrong.")


if __name__ == "__main__":
    main()
