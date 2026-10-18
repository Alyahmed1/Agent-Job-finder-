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
