"""Look and feel for the jobs page: three themes (as color tokens), the CSS, and small HTML helpers."""
import html
import re
from datetime import datetime, timezone

# Each theme is only a set of color tokens; the CSS below uses them through variables.
# "Dark" is the original look. Text/background pairs are checked for >= 4.5:1 contrast.
THEMES = {
    "Light": dict(
        bg="#F4F5FA", surface="#FFFFFF", surface2="#EEF0F6", border="#D5D9E6", text="#14161F", muted="#555D70",
        accent="#2563EB", accent_rgb="37,99,235", btn="#2563EB", on_accent="#FFFFFF", logo2="#1D4ED8",
        great="#15803D", good="#2563EB", possible="#B45309", weak="#6B7280", red="#B91C1C", green="#15803D",
        title_a="#B45309", title_b="#F59E0B", sidebar="#FFFFFF", top1="#FFFFFF", top2="#F0F2F9",
        track="#DDE1EC", skel2="#E6E9F2", shadow="rgba(20,22,31,.14)",
    ),
    "Dark": dict(
        bg="#121214", surface="#1B1B1F", surface2="#242429", border="#2E2E35", text="#ECECF1", muted="#A1A1AE",
        accent="#3B82F6", accent_rgb="59,130,246", btn="#2563EB", on_accent="#FFFFFF", logo2="#1E40AF",
        great="#22C55E", good="#3B82F6", possible="#F59E0B", weak="#64748B", red="#F87171", green="#22C55E",
        title_a="#F59E0B", title_b="#FDE68A", sidebar="#0D0D0F", top1="#202027", top2="#17171B",
        track="#35353D", skel2="#2B2B32", shadow="rgba(0,0,0,.4)",
    ),
}
DEFAULT_THEME = "Dark"

BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@500;600&family=Fira+Sans:wght@400;500;600;700&display=swap');
:root { --ease: cubic-bezier(.2,.7,.2,1); }
html, body, [class*="css"], .stApp { font-family:'Fira Sans', system-ui, sans-serif; }
.stApp { background: var(--bg); color: var(--text); }
header[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 980px; padding-top: 4.2rem; padding-bottom: 4rem; }
footer, #MainMenu { visibility: hidden; }

/* ---------- Streamlit widgets, recolored from the theme (selectors match Streamlit 1.66) ---------- */
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p { color: var(--text) !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: var(--muted) !important; opacity: 1 !important; }
[data-testid="stAlert"] { background: rgba(var(--accent-rgb), .12) !important; border: 1px solid rgba(var(--accent-rgb), .35); }
[data-testid="stAlert"] * { color: var(--text) !important; }
[data-testid="stTextInputRootElement"] { background: var(--surface-2) !important; border-color: var(--border) !important; }
[data-testid="stTextInputRootElement"] input { color: var(--text) !important; -webkit-text-fill-color: var(--text); }
[data-testid="stTextInputRootElement"] input::placeholder { color: var(--muted) !important; -webkit-text-fill-color: var(--muted); opacity: 1 !important; }
[data-testid="stTextInputRootElement"] svg, [data-testid="stSelectbox"] svg { color: var(--muted) !important; fill: var(--muted) !important; opacity: 1 !important; }
[data-testid="stTextInputRootElement"] [data-testid="stIconMaterial"], [data-testid="stTextInputRootElement"] span { color: var(--muted) !important; opacity: 1 !important; }
[data-testid="stSelectbox"] [role="group"] { background: var(--surface-2) !important; border-color: var(--border) !important; }
[data-testid="stSelectbox"] [role="group"] * { color: var(--text) !important; }
[data-testid="stSelectboxVirtualDropdown"] { background: var(--surface) !important; border: 1px solid var(--border); border-radius: 10px; }
[data-testid="stSelectboxVirtualDropdown"] [role="option"], [data-testid="stSelectboxVirtualDropdown"] [role="option"] * { color: var(--text) !important; }
[data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover, [data-testid="stSelectboxVirtualDropdown"] [role="option"][aria-selected="true"] { background: var(--surface-2) !important; }
[data-testid="stSliderThumbValue"], [data-testid="stSliderThumbValue"] p { color: var(--accent) !important; }
[data-testid="stSliderTickBar"], [data-testid="stSliderTickBar"] * { color: var(--muted) !important; }
[data-testid="stToast"] { background: var(--surface) !important; border: 1px solid var(--border); box-shadow: 0 8px 24px var(--shadow); }
[data-testid="stToast"] * { color: var(--text) !important; }
[data-testid="stSidebarCollapseButton"] button, [data-testid="stExpandSidebarButton"] { color: var(--muted); }
[data-testid="stButtonGroup"] button[role="radio"] { background: var(--surface-2) !important; border: 1px solid var(--border) !important; }
[data-testid="stButtonGroup"] button[role="radio"], [data-testid="stButtonGroup"] button[role="radio"] * { color: var(--text) !important; }
[data-testid="stButtonGroup"] button[role="radio"][aria-checked="true"] { background: var(--btn) !important; border-color: var(--btn) !important; }
[data-testid="stButtonGroup"] button[role="radio"][aria-checked="true"], [data-testid="stButtonGroup"] button[role="radio"][aria-checked="true"] * { color: var(--on-accent) !important; }

/* ---------- title bar ---------- */
.st-key-topbar {
  position: sticky; top: 3.4rem; z-index: 50; padding: .9rem 1.1rem; margin-bottom: 1rem;
  background: linear-gradient(135deg, var(--top1) 0%, var(--top2) 70%); border:1px solid var(--border);
  border-radius: 16px; box-shadow: 0 8px 24px var(--shadow);
}
.jf-title { font-size: 1.5rem; font-weight: 700; letter-spacing: -.01em; margin:0; color: var(--text); }
.jf-title b {
  background: linear-gradient(100deg, var(--title-a) 20%, var(--title-b) 45%, var(--title-a) 70%); background-size: 220% 100%;
  -webkit-background-clip: text; background-clip: text; color: transparent; animation: jf-shine 3.5s ease-in-out infinite;
}
@keyframes jf-shine { 0%,100% { background-position: 100% 0; } 50% { background-position: 0 0; } }
.jf-sub { color: var(--muted); font-size: .9rem; margin-top: .15rem; }

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"] { background: var(--sidebar); border-right: 1px solid var(--border); }
.jf-brand { display:flex; align-items:center; gap:.6rem; padding:.4rem .2rem 1rem; }
.jf-logo { width:36px; height:36px; border-radius:10px; display:grid; place-items:center; color:var(--on-accent);
  background: linear-gradient(135deg, var(--accent), var(--logo2)); font-weight:700; }
.jf-brand span { font-weight:700; font-size:1.1rem; color: var(--text); }
.jf-nav-label { color: var(--muted); font-size:.72rem; letter-spacing:.12em; text-transform:uppercase; margin:.6rem 0 .3rem .3rem; }
section[data-testid="stSidebar"] .stButton > button {
  width:100%; justify-content:flex-start; border:1px solid transparent; background:transparent;
  color: var(--text); padding:.65rem .85rem; border-radius:12px; font-weight:500; min-height:44px;
  transition: background .18s var(--ease), transform .18s var(--ease), border-color .18s var(--ease);
}
section[data-testid="stSidebar"] .stButton > button > div { justify-content:flex-start; width:100%; gap:.6rem; }
section[data-testid="stSidebar"] .stButton > button p { text-align:left; color: var(--text); }
section[data-testid="stSidebar"] .stButton > button:hover {
  background: var(--surface-2); border-color: var(--border); transform: translateX(3px);
}
section[data-testid="stSidebar"] .stButton > button:active { transform: translateX(3px) scale(.98); }
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  background: linear-gradient(90deg, rgba(var(--accent-rgb),.28), rgba(var(--accent-rgb),.08));
  border-color: rgba(var(--accent-rgb),.55); box-shadow: inset 3px 0 0 var(--accent);
}

/* ---------- stat cards ---------- */
.jf-stats { display:grid; grid-template-columns: repeat(4, 1fr); gap:.75rem; margin:.2rem 0 1rem; }
.jf-stat { background: var(--surface); border:1px solid var(--border); border-radius:14px; padding:.8rem 1rem;
  transition: transform .2s var(--ease), border-color .2s var(--ease); }
.jf-stat:hover { transform: translateY(-2px); border-color: var(--accent); }
/* numbers count up from 0: --num is a registered integer, so CSS can animate it */
@property --num { syntax: '<integer>'; inherits: false; initial-value: 0; }
@property --p { syntax: '<number>'; inherits: false; initial-value: 0; }
.jf-stat .n { font-family:'Fira Code', monospace; font-size:1.6rem; font-weight:600; font-variant-numeric: tabular-nums; color: var(--text);
  counter-reset: num var(--num); animation: jf-count 1s var(--ease) backwards; }
.jf-stat .n::after { content: counter(num); }
@keyframes jf-count { from { --num: 0; } }
.jf-stat .l { color: var(--muted); font-size:.8rem; }
@media (max-width: 700px) { .jf-stats { grid-template-columns: repeat(2, 1fr); } }

/* ---------- job card ---------- */
div[class*="st-key-card-"] {
  background: var(--surface); border:1px solid var(--border) !important; border-radius:16px;
  padding: .9rem 1rem .6rem; margin-bottom:.8rem;
  transition: transform .2s var(--ease), border-color .2s var(--ease), box-shadow .2s var(--ease);
  animation: jf-in .35s var(--ease) backwards;  /* backwards: never holds a transform, so hover lift still works */
  position: relative; overflow: hidden;
}
div[class*="st-key-card-"]:hover {
  transform: translateY(-3px); border-color: var(--accent) !important; box-shadow: 0 12px 28px var(--shadow);
}
/* spotlight: a soft glow that follows the mouse (--mx/--my are set by SPOTLIGHT_JS; falls back to the top) */
div[class*="st-key-card-"]::before {
  content:""; position:absolute; inset:0; pointer-events:none; z-index:0; opacity:0; transition: opacity .25s var(--ease);
  background: radial-gradient(280px circle at var(--mx, 50%) var(--my, 0%), rgba(var(--accent-rgb),.18), transparent 65%);
}
div[class*="st-key-card-"]:hover::before { opacity:1; }
div[class*="st-key-card-"] > div { position:relative; z-index:1; }
@keyframes jf-in { from { opacity:0; transform: translateY(8px); } to { opacity:1; transform:none; } }
/* cards fade and rise as they scroll into view (Chrome/Edge); other browsers keep the load animation above */
@supports (animation-timeline: view()) {
  div[class*="st-key-card-"] {
    animation: jf-reveal linear backwards; animation-timeline: view(); animation-range: entry 0% entry 40%;
  }
}
@keyframes jf-reveal { from { opacity:0; transform: translateY(28px) scale(.98); } to { opacity:1; transform:none; } }
.jf-row { display:flex; gap:1rem; align-items:center; }
.jf-ring { --p:0; flex:0 0 64px; width:64px; height:64px; border-radius:50%;
  background: conic-gradient(var(--c) calc(var(--p) * 1%), var(--track) 0); display:grid; place-items:center;
  animation: jf-ring 1s var(--ease) backwards; }
@keyframes jf-ring { from { --p: 0; } }
.jf-ring > span { width:50px; height:50px; border-radius:50%; background: var(--surface); display:grid; place-items:center; color: var(--text);
  font-family:'Fira Code', monospace; font-weight:600; font-size:1.05rem; }
.jf-main { min-width:0; flex:1; }
.jf-job { font-weight:600; font-size:1.05rem; line-height:1.3; color: var(--text); }
.jf-meta { color: var(--muted); font-size:.9rem; margin:.1rem 0 .45rem; }
.jf-fit { font-size:.78rem; font-weight:600; padding:.2rem .55rem; border-radius:999px; border:1px solid currentColor; white-space:nowrap; }
.jf-chips { display:flex; flex-wrap:wrap; gap:.35rem; }
.jf-chip { font-size:.75rem; padding:.18rem .55rem; border-radius:999px; background: var(--surface-2); border:1px solid var(--border); color: var(--text); }
.jf-chip.pos { border-color: rgba(34,197,94,.5); }
.jf-chip.neg { border-color: rgba(248,113,113,.55); }
.jf-chip em { font-style:normal; font-family:'Fira Code', monospace; margin-left:.3rem; }
.jf-chip.pos em { color: var(--green); } .jf-chip.neg em { color: var(--red); }

/* ---------- buttons in main area ---------- */
[data-testid="stMain"] .stButton > button, [data-testid="stMain"] a[data-testid="stBaseLinkButton-primary"], [data-testid="stMain"] a[data-testid="stBaseLinkButton-secondary"] {
  border-radius:10px; min-height:44px; font-weight:500; transition: transform .15s var(--ease), box-shadow .15s var(--ease);
}
[data-testid="stMain"] .stButton > button[kind="secondary"] { background: var(--surface); border:1px solid var(--border); }
[data-testid="stMain"] .stButton > button[kind="secondary"], [data-testid="stMain"] .stButton > button[kind="secondary"] * { color: var(--text) !important; }
[data-testid="stMain"] .stButton > button[kind="secondary"]:hover { border-color: var(--accent); }
[data-testid="stMain"] .stButton > button[kind="primary"], [data-testid="stMain"] a[data-testid="stBaseLinkButton-primary"] {
  background: var(--btn); border:1px solid var(--btn); }
[data-testid="stMain"] .stButton > button[kind="primary"], [data-testid="stMain"] .stButton > button[kind="primary"] *,
[data-testid="stMain"] a[data-testid="stBaseLinkButton-primary"], [data-testid="stMain"] a[data-testid="stBaseLinkButton-primary"] * { color: var(--on-accent) !important; }
[data-testid="stMain"] .stButton > button:hover, [data-testid="stMain"] a[data-testid^="stBaseLinkButton"]:hover { transform: translateY(-1px); box-shadow: 0 6px 14px var(--shadow); }
[data-testid="stMain"] .stButton > button:active { transform: scale(.97); }
[data-testid="stBaseButton-tertiary"], [data-testid="stBaseButton-tertiary"] * { color: var(--accent) !important; }
[data-testid="stTextAreaRootElement"], [data-testid="stTextArea"] textarea {
  background: var(--surface-2) !important; border-color: var(--border) !important; }
[data-testid="stTextArea"] textarea { color: var(--text) !important; -webkit-text-fill-color: var(--text); }
/* sidebar: the active page slides in */
section[data-testid="stSidebar"] .stButton > button[kind="primary"] { animation: jf-nav-in .3s var(--ease); }
@keyframes jf-nav-in { from { opacity:.5; transform: translateX(-8px); } to { opacity:1; transform:none; } }

/* loading skeleton shown while Refresh reads your emails */
.jf-skel { height:104px; border-radius:16px; margin-bottom:.8rem; border:1px solid var(--border);
  background: linear-gradient(90deg, var(--surface) 25%, var(--skel2) 37%, var(--surface) 63%); background-size: 400% 100%;
  animation: jf-shimmer 1.3s ease infinite; }
@keyframes jf-shimmer { from { background-position: 100% 0; } to { background-position: 0 0; } }

/* confetti burst when you mark a job as applied (invisible by default, so reduced-motion shows nothing) */
.jf-confetti { position:fixed; left:50%; top:38%; width:0; height:0; pointer-events:none; z-index:9999; }
.jf-confetti span { position:absolute; width:8px; height:12px; border-radius:2px; background: var(--c); opacity:0;
  animation: jf-burst .95s var(--ease) forwards; }
@keyframes jf-burst {
  0% { opacity:1; transform: translate(0,0) rotate(0); }
  100% { opacity:0; transform: translate(var(--dx), var(--dy)) rotate(var(--rot)); }
}
:focus-visible { outline: 2px solid var(--accent) !important; outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
"""


def build_css(theme=DEFAULT_THEME):
    t = THEMES.get(theme, THEMES[DEFAULT_THEME])
    variables = ":root {" + "".join(f" --{k.replace('_', '-')}: {v};" for k, v in t.items()) + " }"
    return variables + BASE_CSS


def fit_label(score, theme=DEFAULT_THEME):
    """(label, color) for a score. Words as well as color, so color is never the only signal."""
    t = THEMES.get(theme, THEMES[DEFAULT_THEME])
    if score >= 80:
        return "Great fit", t["great"]
    if score >= 60:
        return "Good fit", t["good"]
    if score >= 40:
        return "Possible", t["possible"]
    return "Weak", t["weak"]


def parse_reason(reason):
    """'Egypt +10 | senior role -10' -> [('Egypt', 10), ('senior role', -10)]"""
    parts = []
    for chunk in (reason or "").split(" | "):
        m = re.match(r"^(.*?)\s*([+-]\d+)$", chunk.strip())
        parts.append((m.group(1), int(m.group(2))) if m else (chunk.strip(), 0))
    return [p for p in parts if p[0]]


FEED_SOURCES = ("Remotive", "Remote OK", "We Work Remotely", "Jobicy", "Himalayas", "Working Nomads")


def source_label(row):
    """Where a job came from. LinkedIn rows store the alert email subject, so show a clean name instead."""
    source = row["source"] if "source" in row.keys() else ""
    return source if source in FEED_SOURCES else "LinkedIn"


def card_html(row, theme=DEFAULT_THEME):
    score = int(row["score"] or 0)
    label, color = fit_label(score, theme)
    chips = "".join(
        f'<span class="jf-chip {"pos" if d > 0 else "neg" if d < 0 else ""}">{html.escape(name)}<em>{d:+d}</em></span>'
        for name, d in parse_reason(row["reason"])
    )
    place = html.escape(row["location"] or "location not stated")
    return (
        '<div class="jf-row">'
        f'<div class="jf-ring" role="img" aria-label="Match score {score} out of 100" style="--p:{score};--c:{color}"><span>{score}</span></div>'
        '<div class="jf-main">'
        f'<div class="jf-job">{html.escape(row["title"])}</div>'
        f'<div class="jf-meta">{html.escape(row["company"])} &middot; {place} &middot; via {html.escape(source_label(row))}</div>'
        f'<div class="jf-chips">{chips}</div>'
        "</div>"
        f'<div class="jf-fit" style="color:{color}">{label}</div>'
        "</div>"
    )


def applied_status(row, follow_days=7, now=None):
    """(text, tone) for the Applied tab. Tone is 'due' (follow up), 'good' (interview), 'bad' (rejected) or 'quiet'.
    Jobs that already replied, or have no saved date, never ask for a follow-up."""
    if row["reply"] == "interview":
        return "Interview", "good"
    if row["reply"] == "rejected":
        return "Rejected", "bad"
    if not row["applied_at"]:
        return "Applied (date not saved)", "quiet"
    days = ((now or datetime.now(timezone.utc)) - datetime.fromisoformat(row["applied_at"])).days
    text = "Applied today" if days <= 0 else "Applied yesterday" if days == 1 else f"Applied {days} days ago"
    return (text + " · Follow up?", "due") if days >= follow_days else (text, "quiet")


def applied_groups(rows):
    """[(title, rows)] for the Applied page: waiting first (oldest first), then Interview, then Rejected. Empty groups are left out."""
    waiting = sorted((r for r in rows if not r["reply"]), key=lambda r: (r["applied_at"] is None, r["applied_at"] or ""))
    groups = [("Waiting for a reply", waiting),
              ("Interview", [r for r in rows if r["reply"] == "interview"]),
              ("Rejected", [r for r in rows if r["reply"] == "rejected"])]
    return [(title, part) for title, part in groups if part]


def applied_line_html(text, tone, theme=DEFAULT_THEME):
    """The 'Applied 8 days ago · Follow up?' line, colored from the theme (amber when due, green for an interview, red when rejected)."""
    t = THEMES.get(theme, THEMES[DEFAULT_THEME])
    color = {"due": t["possible"], "good": t["green"], "bad": t["red"]}.get(tone, t["muted"])
    return f'<div style="color:{color};font-weight:600;font-size:14px;margin:2px 0 8px">{html.escape(text)}</div>'


def stat_html(items):
    """items: [(label, number)] -> the four stat cards. The number counts up from 0 (see .jf-stat .n)."""
    cards = "".join(
        f'<div class="jf-stat"><div class="n" style="--num:{int(n)}" role="text" aria-label="{int(n)} {html.escape(label)}"></div>'
        f'<div class="l">{html.escape(label)}</div></div>'
        for label, n in items
    )
    return f'<div class="jf-stats">{cards}</div>'


def skeleton_html(count=3):
    return "".join('<div class="jf-skel" aria-hidden="true"></div>' for _ in range(count))


_CONFETTI = [  # (dx, dy, rotation, color key): fixed so the burst always looks the same
    (-120, -90, 220, "great"), (-80, -140, -160, "possible"), (-30, -170, 300, "accent"), (30, -160, -240, "great"),
    (85, -130, 180, "possible"), (125, -85, -300, "accent"), (-150, -30, 120, "accent"), (150, -25, -120, "great"),
    (-95, 20, 260, "possible"), (100, 30, -260, "accent"), (-45, 50, 200, "great"), (50, 60, -200, "possible"),
]


def confetti_html(theme=DEFAULT_THEME):
    t = THEMES.get(theme, THEMES[DEFAULT_THEME])
    bits = "".join(
        f'<span style="--dx:{dx}px;--dy:{dy}px;--rot:{rot}deg;--c:{t[key]}"></span>' for dx, dy, rot, key in _CONFETTI
    )
    return f'<div class="jf-confetti" aria-hidden="true">{bits}</div>'


# Runs inside a tiny iframe and reaches the page: moves each card's glow to follow the mouse.
SPOTLIGHT_JS = """
<script>
const doc = window.parent.document;
if (!window.parent.__jfSpotlight) {
  window.parent.__jfSpotlight = true;
  doc.addEventListener('pointermove', (e) => {
    const card = e.target.closest && e.target.closest('[class*="st-key-card-"]');
    if (!card) return;
    const r = card.getBoundingClientRect();
    card.style.setProperty('--mx', (e.clientX - r.left) + 'px');
    card.style.setProperty('--my', (e.clientY - r.top) + 'px');
  }, { passive: true });
}
</script>
"""
