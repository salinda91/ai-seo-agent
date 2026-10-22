import argparse
import sys
import uvicorn
from agent.core.config import settings

def main():
    parser = argparse.ArgumentParser(description="Autonomous Browser-Controlled AI SEO Specialist Agent")
    parser.add_argument("--host", default=settings.host, help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=settings.port, help="Bind port (default: 8765)")
    parser.add_argument("--reload", action="store_true", help="Enable live code reload")
    args = parser.parse_args()

    print("=" * 65)
    print("  AUTONOMOUS BROWSER-CONTROLLED AI SEO SPECIALIST AGENT")
    print("=" * 65)
    print(f" Server URL:              http://{args.host}:{args.port}")
    print(f" Dedicated Chrome Profile: {settings.chrome_user_data_dir}")
    print(f" Pairing Secret Token:    {settings.agent_token}")
    print("=" * 65)
    print(" Note: The browser will open using the dedicated profile.")
    print(" Log into Google / CMS once in that session to retain cookies.")
    print("=" * 65)

    uvicorn.run(
        "agent.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )

if __name__ == "__main__":
    main()
