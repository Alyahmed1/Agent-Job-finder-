from classify import tags


def test_egypt_remote_and_relocation_lists():
    assert tags("Cairo, Egypt (Hybrid)") == {"egypt"}
    assert tags("Worldwide (Remote)") == {"remote"}
    assert tags("Egypt (Remote)") == {"egypt", "remote"}
    assert tags("Qesm El Maadi (On-site)") == {"egypt"}
    assert tags("Heliopolis (On-site)") == {"egypt"}
    assert tags("United Arab Emirates") == {"relocation"}
    assert tags("Montreal, Quebec, Canada") == {"relocation"}
    assert tags("") == {"relocation"}


def test_another_home_country_from_the_profile():
    from classify import home_cities, home_name
    profile = {"locations": {"priority": "Germany", "home_cities": ["Germany", "Berlin"]}}
    cities = home_cities(profile)
    assert tags("Berlin (Hybrid)", cities) == {"egypt"}   # the home tag keeps its inside name
    assert tags("Cairo, Egypt", cities) == {"relocation"}
    assert home_name(profile) == "Germany"
    assert home_name({}) == "Egypt" and "cairo" in home_cities({})
