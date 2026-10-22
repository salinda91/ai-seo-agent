import pytest
from agent.crawler.analyzer import PageSEOAnalyzer

SAMPLE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Enterprise AI SEO Agent &amp; Autonomous Automation</title>
    <meta name="description" content="Discover how the autonomous browser-controlled AI SEO agent optimizes your Google search rankings without Search Console API dependencies.">
    <link rel="canonical" href="https://example.com/ai-seo">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
    <h1>Autonomous SEO Specialist</h1>
    <h2>On-Page Audit Features</h2>
    <p>This is a comprehensive description of our modern browser automation technology.</p>
    <img src="/logo.png" alt="Company Logo">
    <img src="/banner.png">
    <a href="/pricing">Pricing</a>
    <a href="https://google.com">Search</a>
</body>
</html>
"""

def test_page_seo_analyzer():
    res = PageSEOAnalyzer.analyze("https://example.com/ai-seo", SAMPLE_HTML)

    assert "Enterprise AI SEO Agent" in res["title"]
    assert "Discover how" in res["meta_description"]
    assert res["h1"] == "Autonomous SEO Specialist"
    assert res["canonical"] == "https://example.com/ai-seo"
    assert res["images_without_alt"] == 1
    assert "https://example.com/pricing" in res["internal_links"]
    assert "https://google.com" in res["external_links"]

    # Defect check
    issue_types = [i["type"] for i in res["issues"]]
    assert "images_missing_alt" in issue_types

def test_missing_title_and_description():
    empty_html = "<html><body><h1>Only H1</h1></body></html>"
    res = PageSEOAnalyzer.analyze("https://example.com/empty", empty_html)

    issue_types = [i["type"] for i in res["issues"]]
    assert "missing_title" in issue_types
    assert "missing_meta_description" in issue_types
    assert "missing_canonical" in issue_types
