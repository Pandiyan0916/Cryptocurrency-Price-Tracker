"""
run_web.py - Entry point script to start the CoinPulse Web Application.
"""

import sys
import uvicorn
from webapp.config import DEFAULT_HOST, DEFAULT_PORT

if __name__ == "__main__":
    print(f"Starting CoinPulse Web Server at http://{DEFAULT_HOST}:{DEFAULT_PORT}...")
    uvicorn.run("webapp.main:app", host=DEFAULT_HOST, port=DEFAULT_PORT, reload=False)
