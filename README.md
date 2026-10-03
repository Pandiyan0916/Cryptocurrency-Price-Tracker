# CoinPulse — Enterprise Cryptocurrency Price Tracker & Analytics Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Selenium](https://img.shields.io/badge/Selenium-4.0%2B-43B02A.svg)](https://www.selenium.dev/)
[![Tests](https://img.shields.io/badge/Tests-172%20Passed-brightgreen.svg)](https://docs.pytest.org/)

CoinPulse is a dual-tier cryptocurrency tracking and analytics platform combining a **High-Performance Web Dashboard** (FastAPI + Async HTTP) with an **Automated Headless Web Scraping Engine** (Selenium WebDriver). It features real-time price monitoring, dynamic currency conversion, portfolio management, multi-asset technical comparison charts, historical logging, and authenticated CSV data exports.

## Project Specifications & Core Features

### Features Checklist

1. **Live Price Scraping**: Scrapes real-time prices, 24h volume, 24h percentage change, and market capitalization for leading cryptocurrencies.
2. **Dynamic Page Handling**: Uses Selenium WebDriver with explicit element waiting (`WebDriverWait`) to parse dynamic, client-side rendered HTML content accurately.
3. **Top 10 / Top 50 Coins Data**: Extracts structured details (coin name, symbol, price, 24h change, market cap) for top cryptocurrencies.
4. **CSV Export**: Saves extracted data into structured CSV files for analysis (`crypto_prices.csv`, `top_50_crypto_markets_YYYY-MM-DD.csv`, `historical_prices.csv`) without scientific notation artifacts (e.g. `0.00000001` instead of `1e-8`).
5. **Headless Browser Option**: Supports `--headless` mode for running automated background scraping without opening browser windows.
6. **Historical Logging**: Appends timestamped snapshots (`# Downloaded At: YYYY-MM-DD HH:MM:SS UTC`) to CSV files enabling long-term trend tracking over time.
7. **Filtering by Price or Change**: Filter coins based on custom conditions (price threshold `--min-price`/`--max-price`, highest 24-hour gainers `--top-gainers`, or losers `--top-losers`).

### Project Outcomes

1. **Real-Time Market Monitoring**: Continuous tracking of live cryptocurrency prices and market fluctuations.
2. **Trend Analysis**: Timestamped historical CSV logging supports future trend forecasting and comparative analysis.
3. **Custom Alert & Filtering Logic**: Integrated filters for precise price threshold monitoring and investment decision-making.
4. **Dashboard Ready**: Structured CSV export and REST endpoints connect seamlessly to visualization tools and web dashboards.
5. **Portfolio Tracking**: Full user portfolio management and watchlist tracking with local storage isolation and automatic state cleaning on logout.

---

## Technologies Used

* **Python 3.10+**: Primary programming language for web server, API, and automation.
* **Selenium WebDriver**: Dynamic web scraping and automated browser control.
* **pandas**: Data manipulation, cleaning, and CSV persistence.
* **webdriver_manager**: Automatic ChromeDriver binary download and driver lifecycle management.
* **time**: Scraping delay throttling and high-precision UTC timestamps.
* **Google Chrome & ChromeDriver**: Headless browser automation.
* **FastAPI & Uvicorn**: Asynchronous backend REST web application server.
* **SQLite & PBKDF2-HMAC-SHA256**: Secure user authentication database.

---

## Project Structure

```
crypto-price-tracker/
├── run.py                   # CLI Entry point for Selenium WebDriver scraper
├── run_web.py               # Web Application entry point (FastAPI uvicorn server)
├── requirements.txt         # Project dependencies
├── .env.example             # Environment variable template
│
├── webapp/                  # Production Web Application (FastAPI + ES6 Frontend)
│   ├── main.py              # API Routes & Web Controllers
│   ├── config.py            # Cache TTLs, rate limits, and server settings
│   ├── schemas.py           # Pydantic data schemas
│   ├── services/
│   │   ├── coingecko.py     # Async REST API Integration Client
│   │   ├── cache.py         # In-memory TTL Caching Service
│   │   ├── auth_db.py       # User Authentication & Database Service
│   │   ├── fallback.py      # Resilient offline data fallbacks
│   │   └── scraper_service.py # WebApp scraper orchestration
│   └── static/              # Vanilla ES6+ HTML5/CSS3 Dashboard Frontend
│       ├── css/             # Glassmorphism Design System & Theme Styles
│       └── js/              # Modular ES6 Web Application Controllers
│
├── src/                     # Core Selenium Web Scraping Engine
│   ├── scraper.py           # Chrome WebDriver initialization & scraping engine
│   ├── parsers.py           # HTML parsing logic
│   ├── validators.py        # Record validation & schema sanitization
│   ├── filters.py          # Data filtering logic
│   ├── storage.py           # Historical CSV persistence
│   └── main.py              # Scraper orchestrator & CLI parser
│
└── tests/                   # Pytest Automated Test Suite (172 unit/integration tests)
```

---

## Prerequisites & Installation

### Requirements
* **Python**: `3.10` or higher
* **Google Chrome Browser**: Installed locally (required for Selenium WebDriver execution)

### 1. Environment Setup

```bash
# Clone repository
git clone https://github.com/your-org/crypto-price-tracker.git
cd crypto-price-tracker

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (PowerShell):
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration (`.env`)

Copy `.env.example` to `.env` to configure application parameters:

```bash
cp .env.example .env
```

```env
# Optional API Key (CoinGecko Demo or Pro)
COINGECKO_API_KEY=

# Cache Expiry Overrides (seconds)
CACHE_TTL_MARKETS=60
CACHE_TTL_GLOBAL=120
CACHE_TTL_CHART=300
```

---

## Usage Guide

### Running the Web Application

Launch the FastAPI web server locally on `http://127.0.0.1:8000`:

```bash
python run_web.py
```

*Navigate to `http://127.0.0.1:8000` in your web browser.*

### Running the CLI Web Scraper

Execute the Selenium scraper directly from the command line:

```bash
# Standard interactive scrape (Top 10 coins)
python run.py

# Run in background Headless Mode
python run.py --headless

# Filter by Price & Gainers
python run.py --headless --min-price 1.00 --max-price 50000.00 --top-gainers 5

# Export top 50 records to custom CSV location
python run.py --limit 50 --output data/custom_export.csv
```

---

## Test Suite & Quality Assurance

The codebase includes comprehensive pytest coverage verifying data parsers, API endpoints, authentication workflows, caching layer, and filtering rules.

> **Note**: Ensure your virtual environment is activated (`venv\Scripts\activate` on Windows or `source venv/bin/activate` on Linux/macOS) prior to running tests, or call `venv\Scripts\python.exe` directly so all dependencies (`httpx`, `fastapi`, `pydantic`) are loaded.

To execute the test suite:

**Windows:**
```powershell
venv\Scripts\python.exe -m pytest -v
```

**Linux / macOS:**
```bash
source venv/bin/activate
python -m pytest -v
```

```text
======================= 172 passed in 4.21s =======================
```

---

## Security & Best Practices

1. **Zero Secret Hardcoding**: Secrets and credentials managed via `.env` environment variables.
2. **Password Security**: Passwords stored using PBKDF2 key derivation with HMAC-SHA256.
3. **Session Safety**: Local storage assets (portfolio data, watchlists, auth tokens) are completely cleared upon user logout.
4. **Data Sanitization**: Prevents scientific notation display issues in exported financial datasets.

---

## License

Internal Enterprise Distribution / MIT License. All rights reserved.

