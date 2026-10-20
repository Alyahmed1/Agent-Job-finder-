from score import load_profile, score_job
from ui import card_html, fit_label, parse_reason


def test_reason_round_trips_into_chips():
    job = {"title": "Junior Machine Learning Engineer", "location": "Cairo, Egypt"}
    result = score_job(load_profile(), job)
    parts = parse_reason(result["reason"])
    assert parts[0][1] == 70
    assert ("Egypt", 10) in parts and ("junior-friendly", 10) in parts
    assert result["score"] == 90


def test_fit_labels_use_words_not_just_color():
    assert fit_label(90)[0] == "Great fit"
    assert fit_label(65)[0] == "Good fit"
    assert fit_label(45)[0] == "Possible"
    assert fit_label(10)[0] == "Weak"


def test_card_escapes_html_in_job_text():
    row = {"title": "<script>x</script>", "company": "A&B", "location": None, "score": 55, "reason": "Egypt +10"}
    out = card_html(row)
    assert "<script>" not in out and "A&amp;B" in out and "location not stated" in out


def test_stat_cards_carry_the_number_for_the_count_up_animation():
    from ui import stat_html
    out = stat_html([("New jobs", 59), ("Saved", 0)])
    assert "--num:59" in out and "--num:0" in out and "New jobs" in out


def test_skeleton_and_confetti_are_hidden_from_screen_readers():
    from ui import confetti_html, skeleton_html
    assert skeleton_html(2).count("jf-skel") == 2 and 'aria-hidden="true"' in skeleton_html(1)
    assert 'aria-hidden="true"' in confetti_html()


def test_every_theme_has_the_same_tokens_and_readable_text():
    from ui import THEMES

    def lum(hex_color):
        r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
        lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

    def contrast(a, b):
        hi, lo = sorted((lum(a), lum(b)), reverse=True)
        return (hi + 0.05) / (lo + 0.05)

    keys = set(THEMES["Dark"])
    for name, t in THEMES.items():
        assert set(t) == keys, name
        assert contrast(t["text"], t["surface"]) >= 4.5, name
        assert contrast(t["muted"], t["surface"]) >= 4.5, name
        assert contrast(t["on_accent"], t["btn"]) >= 4.5, name
        assert contrast(t["great"], t["surface"]) >= 3, name   # large/bold label


def test_build_css_swaps_colors_per_theme_and_falls_back_to_dark():
    from ui import THEMES, build_css
    assert list(THEMES) == ["Light", "Dark"]
    assert "--bg: #F4F5FA" in build_css("Light")
    assert build_css("nope") == build_css("Dark")


def test_settings_remember_the_theme(tmp_path, monkeypatch):
    import settings
    monkeypatch.setattr(settings, "PATH", tmp_path / "s.json")
    assert settings.load_theme({"Dark", "Light"}, "Dark") == "Dark"
    settings.save_theme("Light")
    assert settings.load_theme({"Dark", "Light"}, "Dark") == "Light"
    settings.save_theme("Gone")
    assert settings.load_theme({"Dark", "Light"}, "Dark") == "Dark"


def test_card_says_which_site_the_job_came_from():
    from ui import card_html, source_label
    base = {"title": "t", "company": "c", "location": "Worldwide (Remote)", "score": 60, "reason": "x +1"}
    assert "via Remote OK" in card_html({**base, "source": "Remote OK"})
    # LinkedIn rows store the alert email subject, which must not leak into the card
    linkedin = {**base, "source": "'junior software engineer' and similar jobs"}
    assert source_label(linkedin) == "LinkedIn" and "via LinkedIn" in card_html(linkedin)


def test_applied_status_asks_for_a_follow_up_only_after_a_week_without_a_reply():
    from datetime import datetime, timedelta, timezone
    from ui import applied_status
    now = datetime(2026, 10, 20, tzinfo=timezone.utc)
    ago = lambda d: (now - timedelta(days=d)).isoformat()
    row = lambda **k: {"applied_at": None, "reply": None, **k}
    assert applied_status(row(applied_at=ago(0)), 7, now) == ("Applied today", "quiet")
    assert applied_status(row(applied_at=ago(1)), 7, now) == ("Applied yesterday", "quiet")
    assert applied_status(row(applied_at=ago(6)), 7, now) == ("Applied 6 days ago", "quiet")
    assert applied_status(row(applied_at=ago(7)), 7, now) == ("Applied 7 days ago · Follow up?", "due")
    assert applied_status(row(applied_at=ago(30), reply="interview"), 7, now) == ("Interview", "good")   # a reply removes the tag
    assert applied_status(row(applied_at=ago(30), reply="rejected"), 7, now) == ("Rejected", "bad")
    assert applied_status(row(), 7, now) == ("Applied (date not saved)", "quiet")                      # marked before dates existed


def test_applied_page_splits_into_four_tabs():
    from datetime import datetime, timedelta, timezone
    from ui import applied_tabs
    now = datetime(2026, 10, 20, tzinfo=timezone.utc)
    ago = lambda d: (now - timedelta(days=d)).isoformat()
    rows = [{"id": "rej", "applied_at": ago(20), "reply": "rejected"},
            {"id": "old", "applied_at": ago(10), "reply": None},      # waiting 10 days: follow up
            {"id": "int", "applied_at": ago(12), "reply": "interview"},
            {"id": "new", "applied_at": ago(2), "reply": None},       # waiting 2 days: still Applied
            {"id": "older", "applied_at": ago(30), "reply": None},
            {"id": "nodate", "applied_at": None, "reply": None}]      # marked before dates existed: never due
    tabs = applied_tabs(rows, 7, now)
    ids = {name: [r["id"] for r in part] for name, part in tabs.items()}
    assert ids == {"Applied": ["new", "nodate"], "Follow up": ["older", "old"],      # oldest first; no date last
                   "Interview": ["int"], "Rejected": ["rej"]}
    assert list(tabs) == ["Applied", "Follow up", "Interview", "Rejected"]
    assert applied_tabs([], 7, now) == {"Applied": [], "Follow up": [], "Interview": [], "Rejected": []}


def test_card_extras_depend_on_the_applied_tab():
    from ui import card_extras
    assert card_extras("Egypt") == ("tailor", "note") and card_extras("Saved") == ("tailor", "note")
    assert card_extras("Applied", None) == ("note",)                    # Applied and Follow up: just the note
    assert card_extras("Applied", "interview") == ("tailor", "note")    # interview: both, to prepare
    assert card_extras("Applied", "rejected") == ()                     # rejected: a closed case
