import pytest
from agent.intelligence.keyword_research import KeywordResearcher

def test_search_intent_classification():
    researcher = KeywordResearcher()

    assert researcher.determine_search_intent("buy seo software discount") == "transactional"
    assert researcher.determine_search_intent("best enterprise rank tracking tool") == "commercial"
    assert researcher.determine_search_intent("how to audit meta tags tutorial") == "informational"
    assert researcher.determine_search_intent("google search console login") == "navigational"

def test_opportunity_score_calculation():
    researcher = KeywordResearcher()

    # Striking distance keyword: Page 2, decent impressions, low CTR -> High opportunity score
    score = researcher.calculate_opportunity_score(
        impressions=2500,
        clicks=12,
        ctr=0.005,
        position=11.5
    )
    assert score >= 70.0

    # Low impression query -> Low opportunity score
    score_low = researcher.calculate_opportunity_score(
        impressions=10,
        clicks=1,
        ctr=0.10,
        position=2.0
    )
    assert score_low < 50.0
