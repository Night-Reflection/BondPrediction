# BondPrediction - Commodity Data Pipeline

A robust, modular Python data pipeline designed to synchronize hourly historical data for Gold, Silver, and Copper from Yahoo Finance, completely converted into EUR per gram. Data is persisted in a PostgreSQL database (run via Docker) instead of flat CSV files, with built-in health checks and targeted recovery for stale or missing data.

## Project Structure
```text
BONDPREDICTION/
│
├── app/
│   ├── fetch_data.py       # Core data extraction, EUR/gram conversion, and DB writes
│   ├── functions.py        # Data integrity / health-check helpers
│   └── manage_db.py        # Standalone CLI utilities for inspecting and clearing the database
│
├── logs/                   # Log directory utilizing rotating file handlers
│   └── app.log
│
├── .env                    # Environment-specific configuration (not committed to Git)
├── .gitignore              # Tells Git to ignore environments, cache, and logs
├── docker-compose.yml      # Defines the PostgreSQL container and its persistent volume
├── init.sql                # Database schema (assets, price_history) and seed data
├── requirements.txt        # Third-party dependencies
├── run.py                  # Main pipeline orchestrator
├── selfnotes.md            # Personal/working notes (not part of the published docs)
├── start.bat               # Windows helper script: boots Docker DB, waits for readiness, runs the pipeline
└── TODO.md                 # Outstanding tasks / ideas backlog
```

## File Overview

* **run.py** — Entry point. Loops through the tracked commodities (Gold, Silver, Copper), uses `functions.verify_data_integrity()` to check whether each asset's database data is healthy and current, and only triggers a fetch for the assets that actually need it.

* **app/fetch_data.py** — Does the heavy lifting: downloads the EUR/USD FX rate series and each commodity's hourly OHLCV data from Yahoo Finance, converts prices from USD per Troy Ounce/Pound into EUR per gram, deduplicates timestamps, and upserts the results into the `price_history` table (`ON CONFLICT ... DO NOTHING` keeps re-runs safe). Also owns the shared `logger` and SQLAlchemy `engine` used across the app.

* **app/functions.py** — Houses `verify_data_integrity()`, which queries Postgres for the most recent timestamp of a given commodity and flags it as stale if it's older than an allowed delay (4 hours normally, extended to 60 hours over the weekend when markets are closed).

* **app/manage_db.py** — A standalone maintenance script (not used by the automated pipeline) for manually inspecting the database: print row counts per commodity, view the latest/oldest rows for a commodity, or wipe data for one asset or the entire table. Intended to be run directly and edited in its `__main__` scratchpad.

* **docker-compose.yml** — Spins up a `postgres:16-alpine` container (`market_predictions` database, mapped to host port `5433`), mounts `init.sql` for first-run initialization, and persists data in a named Docker volume so it survives restarts.

* **init.sql** — Creates the `assets` and `price_history` tables, adds an index for fast time-series lookups, and seeds the three tracked commodities (Gold, Silver, Copper).

* **start.bat** — Convenience launcher for Windows: starts the Docker Compose stack, polls `pg_isready` until Postgres is accepting connections, then runs `run.py`.

* **.env** — Holds environment-specific values (e.g. credentials/connection settings) kept out of version control via `.gitignore`.

* **selfnotes.md / TODO.md** — Personal working files used during development; not part of the pipeline's runtime behavior.

## Features
* **Currency Conversion:** Automatically downloads matching EURUSD=X rates to convert historical USD prices to EUR.
* **Metric Standardization:** Automatically scales standard US exchange units (Troy Ounces, Pounds) into uniform prices per gram.
* **Deduplication:** Robust sorting logic handles live-data pipeline edge cases by removing duplicate timestamps, maintaining chronological data integrity.
* **PostgreSQL Storage:** Historical data is stored in a Dockerized Postgres database (`assets` + `price_history` tables) rather than CSV files, with a unique constraint per asset/timestamp to keep upserts idempotent.
* **Targeted Recovery:** `run.py` calls `functions.py`, which validates the freshness of each asset's database records post-sync and triggers localized recovery fetches exclusively for the assets that failed their health check.
* **Weekend-Aware Health Checks:** The staleness threshold automatically relaxes on weekends, when markets are closed and no new data is expected.

## Quick Start

1. **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2. **Start the Database (Docker):**
    ```bash
    docker compose up -d
    ```
    This creates the Postgres container and applies `init.sql` on first run.

3. **Run the Pipeline:**
    ```bash
    python run.py
    ```

   On Windows, `start.bat` automates steps 2 and 3: it boots the database container, waits until it's ready, and then launches the pipeline.

## Database Maintenance

For ad-hoc inspection or cleanup, use `app/manage_db.py` directly (uncomment the example calls at the bottom of the file as needed):
```bash
python app/manage_db.py
```
This lets you print row counts per commodity, view the latest/oldest rows for an asset, or clear historical data for one asset or all of them.