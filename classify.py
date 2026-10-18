"""Decide which list a job belongs to: Egypt, Remote, or Relocation."""

EGYPT_CITIES = (
    "egypt", "cairo", "giza", "alexandria", "new capital", "6th of october", "nozha",
    "qesm", "maadi", "heliopolis", "smart village", "nasr city", "zayed city", "obour", "tagamoa",
    "mohandessin", "dokki", "sheraton", "el rehab", "madinaty", "ain shams",
)


def tags(location):
    """A job can be in two lists, e.g. 'Egypt (Remote)' is both Egypt and Remote."""
    where = (location or "").lower()
    found = set()
    if "remote" in where:
        found.add("remote")
    if any(city in where for city in EGYPT_CITIES):
        found.add("egypt")
    if not found:
        found.add("relocation")  # on-site/hybrid abroad (Canada, UAE, Saudi, Europe...)
    return found
