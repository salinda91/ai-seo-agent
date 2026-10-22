import logging
from typing import Tuple

logger = logging.getLogger("ai_seo.browser.recovery")

# Common indicators for challenges requiring human takeover
CAPTCHA_PATTERNS = [
    "recaptcha",
    "g-recaptcha",
    "hcaptcha",
    "cf-turnstile",
    "challenge-running",
    "cf-browser-verification",
    "arkoselabs",
    "funcaptcha",
    "perimeterx",
    "datadome",
]

MFA_PATTERNS = [
    "2-Step Verification",
    "Enter the code",
    "Verify it's you",
    "Check your phone",
    "Get a verification code",
    "Confirm your identity",
    "Security key",
    "Google Authenticator",
    "Two-factor authentication",
]

LOGIN_EXPIRED_PATTERNS = [
    "Sign in - Google Accounts",
    "Your session has expired",
    "Please log in again",
    "Session timed out",
    "Log In ‹",
]

class ObstacleDetector:
    """
    Detects CAPTCHA, 2FA/MFA challenges, session expiration, and blocking dialogs.
    Instructs the agent to pause and yield for human takeover rather than failing blindly.
    """

    @staticmethod
    async def check_obstacles(page) -> Tuple[bool, str, str]:
        """
        Returns:
            (has_obstacle: bool, obstacle_type: str, details: str)
            obstacle_type can be: 'none', 'captcha', 'mfa', 'session_expired', 'permission_modal'
        """
        try:
            url = page.url
            title = await page.title()
            
            # Check URL patterns
            if "accounts.google.com/signin" in url or "accounts.google.com/v3/signin" in url:
                if any(p.lower() in title.lower() for p in ["2-step", "verify", "challenge"]):
                    return True, "mfa", f"Google MFA / 2-Step Verification detected on {url}"
                return True, "session_expired", f"Google Login / Session expired. Authentication required on {url}"

            # Check page content for MFA
            page_text = ""
            try:
                page_text = await page.evaluate("() => document.body ? document.body.innerText.slice(0, 10000) : ''")
            except Exception:
                pass

            for pattern in MFA_PATTERNS:
                if pattern.lower() in page_text.lower() or pattern.lower() in title.lower():
                    return True, "mfa", f"MFA challenge: '{pattern}' found on {url}"

            # Check for CAPTCHA elements in DOM
            for pattern in CAPTCHA_PATTERNS:
                selector = f"[class*='{pattern}'], [id*='{pattern}'], iframe[src*='{pattern}']"
                try:
                    elem = await page.query_selector(selector)
                    if elem and await elem.is_visible():
                        return True, "captcha", f"CAPTCHA element matching '{pattern}' visible on {url}"
                except Exception:
                    pass

            # Check for Cloudflare Turnstile / Challenge
            if "Just a moment..." in title or "Attention Required! | Cloudflare" in title:
                return True, "captcha", f"Cloudflare verification screen detected on {url}"

            # Check for WordPress login screen if unexpected
            if "wp-login.php" in url and "wp-admin" not in url:
                return True, "session_expired", f"WordPress session expired. Redirected to {url}"

            return False, "none", "Page clean"
        except Exception as e:
            logger.warning(f"Error checking obstacles: {e}")
            return False, "none", f"Check error: {str(e)}"
