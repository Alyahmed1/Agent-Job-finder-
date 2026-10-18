from collect.parse import parse_alert_html

HTML = """
<table><tr><td>
  <a href="https://www.linkedin.com/comm/jobs/view/111/?x=1">Data Engineer</a>
  <p>Coca-Cola HBC · New Cairo (Hybrid)</p><p>Easy Apply</p>
</td></tr>
<tr><td>
  <a href="https://www.linkedin.com/comm/jobs/view/222/"><img src="x"></a>
  <p>Backend Developer</p><p>Acme · Cairo, Egypt</p>
</td></tr></table>
<a href="https://www.linkedin.com/comm/jobs/view/111/?y=2">Data Engineer</a>
"""


def test_parses_title_company_location_and_dedupes():
    jobs = parse_alert_html(HTML)
    assert [j["id"] for j in jobs] == ["111", "222"]
    assert jobs[0]["title"] == "Data Engineer"
    assert jobs[0]["company"] == "Coca-Cola HBC"
    assert jobs[0]["location"] == "New Cairo (Hybrid)"
    assert jobs[1]["company"] == "Acme"
