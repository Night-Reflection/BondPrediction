# BondPrediction - Commodity Data Pipeline

A robust, modular Python data pipeline designed to synchronize hourly historical data for Gold, Silver, and Copper from Yahoo Finance, completely converted into EUR per gram.

## Project Structure
```text
BONDPREDICTION/
│
├── app/
│   ├── fetch_data.py       # Core data extraction and conversion logic
│   └── functions.py        # Helper/utility functions
│
├── data/                   # Automatically generated directory for CSV outputs
│   ├── copper_30d.csv
│   ├── gold_30d.csv
│   └── silver_30d.csv
│
├── logs/                   # Log directory utilizing rotating file handlers
│   └── app.log
│
├── .gitignore              # Tells Git to ignore environments, cache, and logs
├── requirements.txt        # Third-party dependencies
└── run.py                  # Main pipeline orchestrator
```

## Features
* **Currency Conversion:** Automatically downloads matching EURUSD=X rates to convert historical USD prices to EUR.
* **Metric Standardization:** Automatically scales standard US exchange units (Troy Ounces, Pounds) into uniform prices per Gram.
* **Deduplication:** Robust sorting logic handles live-data pipeline edge cases by removing duplicate timestamps, maintaining chronological data integrity.
* **Targeted Recovery:** run.py calls functions.py which validates the structural health of local datasets post-sync and triggers localized recovery fetches exclusively for failed assets.

## Quick Start

1. **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2. **Run the Pipeline:**
    ```bash
    python run.py
    ```

## Self note
git add .\
git commit -m "Reason"\
git push