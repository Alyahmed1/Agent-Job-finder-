from score import load_profile, score_job

PROFILE = load_profile()


def s(title, location="Cairo, Egypt"):
    return score_job(PROFILE, {"title": title, "location": location})["score"]


def test_tier_order():
    assert s("Machine Learning Engineer") > s("Backend Developer") > s("Software Engineer")


def test_genai_and_ai_developer_are_tier_1():
    assert s("Gen AI Engineer") == s("Machine Learning Engineer")
    assert s("AI Developer") == s("Machine Learning Engineer")


def test_data_engineer_matches_backend_tier():
    assert s("Data Engineer") == s("Backend Developer") == s("Full Stack Engineer")


def test_senior_is_lower_than_junior():
    assert s("Junior Data Engineer") > s("Senior Data Engineer")


def test_egypt_beats_abroad():
    assert s("Backend Developer", "Cairo, Egypt") > s("Backend Developer", "Dubai, UAE")


def test_senior_is_only_a_small_penalty():
    assert s("Senior Machine Learning Engineer") > s("Junior Software Engineer")
    assert s("Machine Learning Engineer") - s("Senior Machine Learning Engineer") == 10


def test_management_is_penalised_more_than_senior():
    assert s("Engineering Manager") < s("Senior Backend Developer")


def test_ai_in_title_alone_is_not_enough():
    assert s("AI Designer") < 30
    assert s("Platform Deployment Engineer (AI Factory Delivery)") < s("Backend Developer")
    assert s("Applied AI Engineer") >= 70


def test_agents_and_ai_deployment_are_tier_1():
    top = s("Machine Learning Engineer")
    assert s("AI Agent Developer") == top
    assert s("Agentic Systems Engineer") == top
    assert s("AI Deployment Engineer") == top


def test_mobile_web_and_deploy_roles_are_tier_2():
    tier2 = s("Backend Developer")
    assert s("Mobile Developer") == tier2
    assert s("Flutter Developer") == tier2
    assert s("Web Developer") == tier2
    assert s("DevOps Engineer") == tier2
    assert s("Deployment Engineer") == tier2


def test_ranks_mix_a_strong_backend_job_can_beat_a_plain_ai_job():
    assert s("Junior Backend Developer", "Cairo, Egypt") > s("Machine Learning Engineer", "Dubai, UAE")
    # but at equal quality the AI job still wins
    assert s("Machine Learning Engineer") > s("Backend Developer")


def test_linux_ai_job_stays_in_tier_1_but_near_its_bottom():
    result = score_job(PROFILE, {"title": "Junior AI Engineer (Linux)", "location": "Cairo, Egypt"})
    assert result["score"] == 64
    assert "Tier 1" in result["reason"] and "Linux (not preferred)" in result["reason"]
    assert result["score"] < s("Machine Learning Engineer")
    assert result["score"] > s("Software Engineer", "Dubai, UAE")


def test_linux_without_ai_is_not_boosted():
    assert "Tier 1" not in score_job(PROFILE, {"title": "Linux Systems Engineer", "location": "Cairo"})["reason"]


def test_stack_mismatch_and_no_match_rank_low():
    assert s("Senior .NET Developer") < 30
    assert s("IT Coordinator") < 30
