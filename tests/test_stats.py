from stats import tab_stats


def job(location, score):
    return {"location": location, "score": score}


EGYPT = [job("Cairo, Egypt", 90), job("Giza (On-site)", 50)]
REMOTE = [job("Worldwide (Remote)", 85), job("Worldwide (Remote)", 60), job("Egypt (Remote)", 70)]
SAVED = [job("Cairo, Egypt", 80), job("Worldwide (Remote)", 70)]
APPLIED = [job("Worldwide (Remote)", 90)]


def test_each_tab_shows_its_own_numbers():
    assert tab_stats("Egypt", "egypt", EGYPT, SAVED, APPLIED) == [
        ("New jobs", 2), ("Great fits (80+)", 1), ("Saved", 1), ("Applied", 0)]
    assert tab_stats("Remote", "remote", REMOTE, SAVED, APPLIED) == [
        ("New jobs", 3), ("Great fits (80+)", 1), ("Saved", 1), ("Applied", 1)]
    assert tab_stats("Relocation", "relocation", [], SAVED, APPLIED) == [
        ("New jobs", 0), ("Great fits (80+)", 0), ("Saved", 0), ("Applied", 0)]


def test_list_pages_show_their_total_and_where_the_jobs_are():
    assert tab_stats("Saved", None, SAVED, SAVED, APPLIED) == [
        ("Saved", 2), ("Egypt", 1), ("Remote", 1), ("Relocation", 0)]
