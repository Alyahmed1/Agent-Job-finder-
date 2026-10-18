"""The four numbers at the top of each page, based on what was found for that page."""
from classify import tags

LISTS = ("egypt", "remote", "relocation")


def in_tab(rows, tag):
    return [r for r in rows if tag in tags(r["location"])]


def tab_stats(page, tag, rows, saved, applied):
    """tag is set for the Egypt / Remote / Relocation tabs; rows are that page's unfiltered jobs."""
    if tag:
        return [
            ("New jobs", len(rows)),
            ("Great fits (80+)", sum(1 for r in rows if r["score"] >= 80)),
            ("Saved", len(in_tab(saved, tag))),
            ("Applied", len(in_tab(applied, tag))),
        ]
    # Saved / Applied / Not interested: the total, then where those jobs are
    return [(f"{page}", len(rows))] + [(t.capitalize(), len(in_tab(rows, t))) for t in LISTS]
