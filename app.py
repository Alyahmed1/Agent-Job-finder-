"""The daily jobs page. Run with: .venv\\Scripts\\streamlit run app.py"""
from datetime import date, datetime

import streamlit as st

import cover
import db
import jobdesc
import pipeline
import settings
import tailor
import ui
from classify import home_cities, home_name, tags
from score import load_profile
from stats import tab_stats

SHOW_LIMIT = 25
PROFILE = load_profile()
HOME = home_name(PROFILE)  # your home country (locations.priority in profile.yaml), Egypt by default
CITIES = home_cities(PROFILE)
# (name, icon, tag for new jobs or status), in sidebar order
DISCOVER = [
    (HOME, ":material/location_on:", "egypt"),
    ("Remote", ":material/public:", "remote"),
    ("Relocation", ":material/flight_takeoff:", "relocation"),
]
YOUR_LIST = [
    ("Saved", ":material/bookmark:", "saved"),
    ("Applied", ":material/task_alt:", "applied"),
    ("Not interested", ":material/block:", "rejected"),
]
SUBTITLES = {
    HOME: f"On-site and hybrid jobs in {HOME}, ranked first",
    "Remote": f"Work from anywhere, including remote jobs open to {HOME}",
    "Relocation": "Canada, UAE, Saudi Arabia, Europe",
    "Saved": "Jobs you want to come back to",
    "Applied": "Jobs you've applied to",
    "Not interested": "Jobs you hid. Press Restore if you change your mind",
}
EMPTY = {
    HOME: f"No new {HOME} jobs right now. Press Refresh to check your emails.",
    "Remote": "No remote jobs yet. Press Refresh to check LinkedIn and the remote job sites.",
    "Relocation": "No relocation jobs yet. Your Canada, Saudi and Europe alerts send their first lists soon.",
    "Saved": "Nothing saved yet. Press Save on a job you like.",
    "Applied": "No applications tracked yet. Press Mark applied after you apply.",
    "Not interested": "You haven't hidden any jobs. Jobs you mark Not interested show up here.",
}
TOASTS = {"saved": "Saved", "applied": "Marked as applied", "rejected": "Hidden. It won't come back", "new": "Moved back to new jobs"}


def updated_label(iso):
    """'Updated Mon 07:01' in local time, or a hint when it has never run."""
    if not iso:
        return "not updated yet, press Refresh"
    return f"Updated {datetime.fromisoformat(iso).astimezone():%a %H:%M}"


def go(page):
    st.session_state.page = page


def pick_theme():
    choice = st.session_state.get("theme_pick")
    if choice:
        st.session_state.theme = choice
        settings.save_theme(choice)
    else:  # clicking the selected option again clears it; keep the current theme selected
        st.session_state.theme_pick = st.session_state.theme


def mark(job_id, status):
    conn = db.connect()
    db.set_status(conn, job_id, status)
    pipeline.rescore(conn, load_profile())  # your click teaches the ranking right away
    conn.close()
    st.toast(TOASTS[status])
    if status == "applied":
        st.session_state.celebrate = True


def set_replied(job_id, replied):
    conn = db.connect()
    db.set_replied(conn, job_id, replied)
    conn.close()


def report_toasts(report):
    found = pipeline.total_new(report)
    st.toast(f"{found} new jobs found" if found else "No new jobs yet")
    for name, note in report.items():
        if isinstance(note, str) and note.startswith("failed"):
            st.toast("Gmail login expired: double-click login_gmail.bat" if "GmailLoginNeeded" in note else f"Problem with {name}: {note}")


def refresh(profile):
    conn = db.connect()
    report = pipeline.refresh(conn, profile)
    conn.close()
    return report


def nav_button(name, icon, count):
    active = st.session_state.page == name
    st.button(f"{icon} {name}  ·  {count}", key=f"nav-{name}", on_click=go, args=(name,),
              type="primary" if active else "secondary", use_container_width=True)


def open_note(job_id):
    st.session_state.note_open = None if st.session_state.get("note_open") == job_id else job_id


def ask_for_draft(job_id):
    st.session_state.note_generate = job_id


def save_note(job_id, key):
    conn = db.connect()
    db.save_note(conn, job_id, st.session_state[key].strip())
    conn.close()
    st.toast("Note saved")


def cover_note(row, page):
    """Optional. A draft is written only when you press Write draft, and kept only when you press Save note."""
    label = "Cover note (saved)" if row["note"] else "Cover note"
    st.button(label, key=f"{page}-{row['id']}-note", icon=":material/edit_note:", type="tertiary",
              on_click=open_note, args=(row["id"],))
    if st.session_state.get("note_open") != row["id"]:
        return
    key = f"note_text_{row['id']}"
    st.session_state.setdefault(key, row["note"] or "")
    if st.session_state.get("note_generate") == row["id"]:
        st.session_state.note_generate = None
        with st.spinner("Writing a draft with your local model. This can take up to a minute..."):
            text, error = cover.generate(load_profile(), dict(row))
        if error:
            st.error(error)
        else:
            st.session_state[key] = text
    st.text_area("Your cover note. Edit it freely; it is kept only if you press Save note.", key=key, height=190)
    a, b, c = st.columns([1.2, 1.2, 1])
    a.button("Write draft", key=f"{page}-{row['id']}-draft", icon=":material/auto_awesome:",
             on_click=ask_for_draft, args=(row["id"],), use_container_width=True)
    b.button("Save note", key=f"{page}-{row['id']}-savenote", icon=":material/save:", type="primary",
             on_click=save_note, args=(row["id"], key), use_container_width=True)
    c.button("Close", key=f"{page}-{row['id']}-closenote", on_click=open_note, args=(row["id"],), use_container_width=True)
    st.caption("A draft from your local model, using only facts from your profile. Check every fact before you use it. "
               "Nothing is sent anywhere.")


def open_tailor(job_id):
    st.session_state.tailor_open = None if st.session_state.get("tailor_open") == job_id else job_id


def run_tailor(row, text):
    try:
        cv = tailor.load_cv()
    except FileNotFoundError as err:
        st.error(str(err))
        return
    with st.spinner("Comparing the job to your CV..."):
        st.session_state[f"tailor_res_{row['id']}"] = tailor.tailor(load_profile(), cv, text, row["title"])


def show_tailor(result):
    st.markdown("**You have:** " + (", ".join(result["have"]) or "nothing from this job's tool list"))
    st.markdown("**You're missing:** " + (", ".join(result["missing"]) or "nothing, you cover every tool it names"))
    if result["best"]:
        st.markdown("**Lead with:**")
        for b in result["best"]:
            st.markdown(f"- {b['name']} ({', '.join(b['matched'])})")
    if result["line"]:
        st.markdown("**A profile line for this job** (read it, then copy it into your CV):")
        st.code(result["line"], language=None, wrap_lines=True)
    if result["line_note"]:
        st.caption(result["line_note"])


def cv_tailor(row, page):
    """Advice only. Your CV file is never changed, and the profile line never names a tool your CV lacks."""
    st.button("Tailor my CV", key=f"{page}-{row['id']}-tailor", icon=":material/description:", type="tertiary",
              on_click=open_tailor, args=(row["id"],))
    if st.session_state.get("tailor_open") != row["id"]:
        return
    text, fetched = row["description"] or "", f"tailor_fetched_{row['id']}"
    if not text and not st.session_state.get(fetched):  # one gentle try on the job's own page; LinkedIn is never opened
        st.session_state[fetched] = True
        with st.spinner("Reading the job description..."):
            text, error = jobdesc.fetch_description(row["url"])
        if text:
            conn = db.connect()
            db.save_description(conn, row["id"], text)
            conn.close()
        else:
            st.session_state[f"tailor_why_{row['id']}"] = error
    result = st.session_state.get(f"tailor_res_{row['id']}")
    if text and result is None:
        run_tailor(row, text)
        result = st.session_state.get(f"tailor_res_{row['id']}")
    if result is not None:
        show_tailor(result)
    if result is None or result["limited"]:
        why = st.session_state.get(f"tailor_why_{row['id']}")
        st.info(why or "Only a short snippet of this job was available, so the comparison is light.")
        paste = st.text_area("Paste the full job description for a better result", key=f"tailor_paste_{row['id']}", height=140)
        if st.button("Compare", key=f"{page}-{row['id']}-compare", icon=":material/compare_arrows:", disabled=not paste.strip()):
            conn = db.connect()
            db.save_description(conn, row["id"], paste.strip())
            conn.close()
            run_tailor(row, paste.strip())
            st.rerun()
    st.button("Close", key=f"{page}-{row['id']}-closetailor", on_click=open_tailor, args=(row["id"],))
    st.caption("Advice only: your CV file is never changed. Nothing is sent anywhere.")


def job_card(row, page):
    with st.container(key=f"card-{page}-{row['id']}"):
        st.html(ui.card_html(row, st.session_state.theme))
        if page == "Applied":
            text, due = ui.applied_status(row, load_profile().get("follow_up_days", 7))
            st.html(ui.applied_line_html(text, due, row["replied"], st.session_state.theme))
        cols = st.columns(4)
        cols[0].link_button("Apply", row["url"], icon=":material/open_in_new:", type="primary", use_container_width=True)
        if page in ("Applied", "Not interested"):
            cols[1].button("Undo" if page == "Applied" else "Restore", key=f"{page}-{row['id']}-undo",
                           icon=":material/undo:", on_click=mark, args=(row["id"], "new"), use_container_width=True)
            if page == "Applied":
                cols[2].button("No reply yet" if row["replied"] else "Got a reply", key=f"{page}-{row['id']}-replied",
                               icon=":material/mark_email_read:", on_click=set_replied, args=(row["id"], not row["replied"]),
                               use_container_width=True)
        else:
            cols[1].button("Mark applied", key=f"{page}-{row['id']}-applied", icon=":material/task_alt:",
                           on_click=mark, args=(row["id"], "applied"), use_container_width=True)
            if page != "Saved":
                cols[2].button("Save", key=f"{page}-{row['id']}-saved", icon=":material/bookmark:",
                               on_click=mark, args=(row["id"], "saved"), use_container_width=True)
            cols[3].button("Not interested" if page != "Saved" else "Remove", key=f"{page}-{row['id']}-rejected",
                           icon=":material/close:", on_click=mark, args=(row["id"], "rejected"), use_container_width=True)
        cv_tailor(row, page)
        cover_note(row, page)


st.set_page_config(page_title="Job Hunter", page_icon=":material/work:", layout="wide",
                   initial_sidebar_state="expanded")
st.session_state.setdefault("page", HOME)
st.session_state.setdefault("theme", settings.load_theme(ui.THEMES, ui.DEFAULT_THEME))
theme = st.session_state.theme
st.markdown(f"<style>{ui.build_css(theme)}</style>", unsafe_allow_html=True)
st.iframe(ui.SPOTLIGHT_JS, height=1)  # our own fixed script, never user input
if st.session_state.pop("celebrate", False):
    st.html(ui.confetti_html(theme))
profile = load_profile()

if not st.session_state.get("auto_checked"):          # once per visit, never in a loop
    st.session_state.auto_checked = True
    conn = db.connect()
    if pipeline.is_stale(db.get_meta(conn, "last_refresh"), profile["auto_refresh_hours"]):
        with st.spinner(f"Your list is more than {profile['auto_refresh_hours']} hours old. Updating it now..."):
            report = pipeline.refresh(conn, profile)
        report_toasts(report)
    conn.close()

conn = db.connect()
new_jobs, saved, applied, rejected = (db.list_jobs(conn, s) for s in ("new", "saved", "applied", "rejected"))
last_refresh = db.get_meta(conn, "last_refresh")
conn.close()
by_tag = {tag: [r for r in new_jobs if tag in tags(r["location"], CITIES)] for _, _, tag in DISCOVER}
by_list = {"Saved": saved, "Applied": applied, "Not interested": rejected}
counts = {name: len(by_tag[tag]) for name, _, tag in DISCOVER} | {name: len(r) for name, r in by_list.items()}

with st.sidebar:
    st.html('<div class="jf-brand"><div class="jf-logo">J</div><span>Job Hunter</span></div>')
    st.html('<div class="jf-nav-label">Discover</div>')
    for name, icon, _ in DISCOVER:
        nav_button(name, icon, counts[name])
    st.html('<div class="jf-nav-label">Your list</div>')
    for name, icon, _ in YOUR_LIST:
        nav_button(name, icon, counts[name])
    st.html('<div class="jf-nav-label">Theme</div>')
    st.segmented_control("Theme", list(ui.THEMES), key="theme_pick", default=theme, label_visibility="collapsed", on_change=pick_theme, width="stretch")

page = st.session_state.page
tag = {n: t for n, _, t in DISCOVER}.get(page)
rows = by_tag[tag] if tag else by_list[page]

with st.container(key="topbar"):
    left, right = st.columns([5, 1.4], vertical_alignment="center")
    left.html(f'<div class="jf-title">{page} <b>jobs</b></div>'
              f'<div class="jf-sub">{date.today():%A, %d %B} &middot; {SUBTITLES[page]} &middot; {updated_label(last_refresh)}</div>')
    if right.button("Refresh", icon=":material/refresh:", type="primary", use_container_width=True):
        skeleton = st.empty()
        skeleton.html(ui.skeleton_html())
        with st.spinner("Reading your LinkedIn alerts and the remote job sites..."):
            report = refresh(profile)
        skeleton.empty()
        report_toasts(report)
        st.rerun()

st.html(ui.stat_html(tab_stats(page, tag, rows, saved, applied, CITIES, HOME)))

f_search, f_score, f_sort = st.columns([3, 2, 2], vertical_alignment="bottom")
query = f_search.text_input("Search", placeholder="Search title or company", key="q",
                            label_visibility="collapsed", icon=":material/search:").strip().lower()
min_score = f_score.slider("Minimum score", 0, 100, 0, step=5, key="min_score")
sort = f_sort.selectbox("Sort by", ["Best match", "Newest"], key="sort", label_visibility="collapsed")

rows = [r for r in rows if r["score"] >= min_score and query in f"{r['title']} {r['company']}".lower()]
if sort == "Newest":
    rows = sorted(rows, key=lambda r: r["first_seen"], reverse=True)

if not rows:
    st.info(EMPTY[page] if not (query or min_score) else "No jobs match these filters. Lower the minimum score or clear the search.")
else:
    if page in (HOME, "Remote", "Relocation"):
        st.caption("Apply opens the job on the site it came from. Come back and press Mark applied so it's tracked.")
    for r in rows[:SHOW_LIMIT]:
        job_card(r, page)
    if len(rows) > SHOW_LIMIT:
        st.caption(f"Showing the top {SHOW_LIMIT} of {len(rows)}. Use search or minimum score to narrow down.")
