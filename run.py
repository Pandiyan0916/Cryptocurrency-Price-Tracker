"""
run.py – Thin entry-point for the Cryptocurrency Price Tracker.

Usage
-----
    python run.py [options]
    python run.py --help
"""

import sys
from src.main import main

if __name__ == "__main__":
    sys.exit(main())
