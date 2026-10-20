"""Decide which list a job belongs to: home country, Remote, or Relocation.

The home country defaults to Egypt. To use another one, set locations.priority (its name) and
locations.home_cities (words that appear in its job locations) in profile.yaml.
"""

EGYPT_CITIES = (
    "egypt", "cairo", "giza", "alexandria", "new capital", "6th of october", "nozha",
    "qesm", "maadi", "heliopolis", "smart village", "nasr city", "zayed city", "obour", "tagamoa",
    "mohandessin", "dokki", "sheraton", "el rehab", "madinaty", "ain shams",
)


def home_cities(profile=None):
    """The home-country words from profile.yaml (locations.home_cities), else the Egypt list."""
    cities = ((profile or {}).get("locations") or {}).get("home_cities")
    return tuple(c.lower() for c in cities) if cities else EGYPT_CITIES


def home_name(profile=None):
    return ((profile or {}).get("locations") or {}).get("priority") or "Egypt"


def tags(location, cities=None):
    """A job can be in two lists, e.g. 'Egypt (Remote)' is both home and Remote. The home tag stays 'egypt' inside the code."""
    where = (location or "").lower()
    found = set()
    if "remote" in where:
        found.add("remote")
    if any(city in where for city in (cities or EGYPT_CITIES)):
        found.add("egypt")
    if not found:
        found.add("relocation")  # on-site/hybrid abroad (Canada, UAE, Saudi, Europe...)
    return found
