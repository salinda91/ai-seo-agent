import os
import secrets
from pathlib import Path
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
DATA_DIR = BASE_DIR / "data"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"

DATA_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

TOKEN_FILE = DATA_DIR / ".agent_token"

def get_or_create_token() -> str:
    env_token = os.getenv("AI_SEO_AGENT_TOKEN")
    if env_token:
        return env_token
    if TOKEN_FILE.exists():
        try:
            token = TOKEN_FILE.read_text().strip()
            if len(token) >= 16:
                return token
        except Exception:
            pass
    token = secrets.token_hex(24)
    try:
        TOKEN_FILE.write_text(token)
    except Exception:
        pass
    return token

class Settings(BaseSettings):
    app_name: str = "AI SEO Automation Agent"
    host: str = "127.0.0.1"
    port: int = 8765
    debug: bool = False
    
    agent_token: str = get_or_create_token()
    
    # Database
    db_path: Path = DATA_DIR / "ai_seo.db"
    database_url: str = f"sqlite+aiosqlite:///{db_path}"
    
    # Chrome Profile Isolation
    # Dedicated profile path separate from normal user personal data
    local_app_data: str = os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
    chrome_user_data_dir: str = os.path.join(local_app_data, "AI_SEO_Agent", "ChromeProfile")
    chrome_executable: str = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    
    # Gemini AI Configuration
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = "gemini-2.5-flash"
    
    # Automation limits
    default_automation_mode: str = "supervised"  # recommendation, supervised, autonomous
    daily_action_limit: int = 50
    browser_timeout_ms: int = 30000
    action_delay_ms: int = 600

    model_config = ConfigDict(env_file=".env", extra="allow")

settings = Settings()
