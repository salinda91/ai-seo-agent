import pytest
from agent.core.security import is_safe_url_for_crawling, sanitize_untrusted_text, verify_token
from agent.core.config import settings

def test_ssrf_blocking_private_ips():
    # Loopback
    safe, msg = is_safe_url_for_crawling("http://127.0.0.1/admin")
    assert not safe
    assert "private/local IP" in msg or "blocked" in msg

    # Localhost
    safe, msg = is_safe_url_for_crawling("http://localhost:8080")
    assert not safe

    # Cloud metadata
    safe, msg = is_safe_url_for_crawling("http://169.254.169.254/latest/meta-data/")
    assert not safe

    # Private class A / C
    safe, _ = is_safe_url_for_crawling("http://10.0.0.1/secret")
    assert not safe
    safe, _ = is_safe_url_for_crawling("http://192.168.1.1/router")
    assert not safe

def test_safe_public_urls():
    safe, _ = is_safe_url_for_crawling("https://example.com")
    assert safe
    safe, _ = is_safe_url_for_crawling("https://google.com/search")
    assert safe

def test_sanitize_untrusted_text():
    dirty = "Hello\x00World\x08! Normal text."
    clean = sanitize_untrusted_text(dirty)
    assert "\x00" not in clean
    assert "\x08" not in clean
    assert "Hello" in clean

def test_verify_token():
    assert verify_token(settings.agent_token)
    assert not verify_token("invalid_token")
    assert not verify_token("")
    assert not verify_token(None)
