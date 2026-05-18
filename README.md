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
└── run.py                  # Main pipeline orchestrator and data-integrity checker