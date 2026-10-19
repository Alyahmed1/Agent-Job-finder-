"""Get a job's full text from its public page, once, when you ask for it. Nothing is sent anywhere."""
import json
import re

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (personal job search)"}
MAX_CHARS = 6000


def _clean(text):
    return re.sub(r"\s+", " ", text or "").strip()[:MAX_CHARS]


def _json_ld_description(soup):
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except ValueError:
            continue
        for item in data if isinstance(data, list) else [data]:
            if isinstance(item, dict) and item.get("@type") == "JobPosting" and item.get("description"):
                return BeautifulSoup(item["description"], "html.parser").get_text(" ")
    return ""


def parse_description(html):
    """LinkedIn's public page, then the standard JobPosting data most job sites include, then <article>/<main>."""
    soup = BeautifulSoup(html, "html.parser")
    box = soup.select_one(".show-more-less-html__markup, .description__text")
    text = box.get_text(" ") if box else _json_ld_description(soup)
    if not text:
        box = soup.find("article") or soup.find("main")
        text = box.get_text(" ") if box else ""
    return _clean(text)


def fetch_description(url, timeout=20):
    """Returns (text, error). Exactly one of them is empty. LinkedIn pages are never opened, so your account can't be blocked."""
    if "linkedin.com" in url:
        return "", "LinkedIn jobs aren't opened by the tool. Paste the description yourself, or only the title will be used."
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException:
        return "", "Couldn't open the job page. Only the job title will be used."
    text = parse_description(resp.text)
    return (text, "") if len(text) > 80 else ("", "This page has no readable description. Only the job title will be used.")
