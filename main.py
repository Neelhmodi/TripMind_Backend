import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging at startup so that logs from db.py and other modules are printed
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)

from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path)

from api.app import app  # noqa: F401 — uvicorn uses `app`

if __name__ == "__main__":
    import uvicorn

    missing = []
    if not os.environ.get("SERPAPI_KEY"):
        missing.append("SERPAPI_KEY")
    if missing:
        print(f"\nERROR: Missing environment variables: {', '.join(missing)}")
        print("Add them to your .env file and restart.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  TripMind AI — FastAPI Backend")
    print("=" * 60)
    print("  API     : http://localhost:8000")
    print("  Docs    : http://localhost:8000/docs")
    print("  Health  : http://localhost:8000/api/v1/health")
    print("=" * 60 + "\n")

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
