# BondPrediction - Project TODO List

This roadmap details the phases required to scale the project from a raw historical data downloader into a predictive Machine Learning framework capable of short, medium, and long-term commodity forecasting.

## Phase 1: Data Expansion & Infrastructure (Current Focus)
- [ ] **Expand Historical Scope:** Update `fetch_data.py` to pull the last 5 to 10 years of data instead of a rolling 30 days.
- [ ] **Data Storage Upgrade:** Switch from individual flat `.csv` files to a local database (like SQLite) or partitioned files (like Parquet) to efficiently query millions of rows of hourly data.
- [ ] **Feature Engineering:** Create input signals for the AI, including:
    * Technical indicators (RSI, Moving Averages, MACD).
    * Time features (Hour of day, day of week, month of year).
    * Lag features (What was the price 1 hour ago? 24 hours ago? 7 days ago?).

## Phase 2: Short-Term Model (24-Hour Horizon)
- [ ] **Objective:** Predict the next 24 hours, hour-by-hour.
- [ ] **Model Selection:** Build a Time-Series model well-suited for high-frequency patterns:
    * *Options:* XGBoost / LightGBM (fast, highly accurate with structured features) or an LSTM / GRU Neural Network (deep learning for sequential data).
- [ ] **Evaluation:** Implement a "Walk-Forward" validation strategy to test the model on past data without leaking the future into the past.

## Phase 3: Medium & Long-Term Models (1-Week, 1-Month, 1-Year)
- [ ] **Objective:** Predict daily closing values for 1 week and 1 month, and macro trends for 1 year ahead.
- [ ] **Strategy Split:** * For 1-Week/1-Month: Use a multi-step forecasting model (predicting day $t+1$, then using that to predict $t+2$, etc.).
    * For 1-Year: Train a separate macro-model using downsampled **daily or weekly data** rather than hourly data, focusing on long-term moving averages and cycles.

## Phase 4: User Interface & Dashboard
- [ ] **Create a Web UI:** Build a simple web dashboard using **Streamlit** or **Dash**.
- [ ] **Data Visualization:** Plot interactive interactive charts showing:
    * Historical data trends.
    * The 24-hour forecasted timeline with confidence intervals (upper/lower bounds).
- [ ] **Automation:** Set up a cron-job or GitHub Action to automatically run the sync and update the predictions once a day.