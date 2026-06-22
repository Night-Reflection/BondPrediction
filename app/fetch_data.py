import os
import datetime
import pandas as pd
import requests
from sqlalchemy import create_engine, text
import app.functions as fn
from app.functions import logger, engine

TICKER_MAPPING = {
    "Gold": "GC=F",
    "Silver": "SI=F",
    "Copper": "HG=F"
}

def fetch_and_save_commodity_data(requested_commodities=None):
    """
    Fetches missing delta historical data from Yahoo Finance and performs an
    UPSERT to ensure recent partial candles are refreshed and completed.
    """
    if requested_commodities is None:
        targets = list(TICKER_MAPPING.keys())
    else:
        targets = [c for c in requested_commodities if c in TICKER_MAPPING]

    if not targets:
        logger.warning("No valid commodities requested for fetch.")
        return

    logger.info(f"Executing network sync for: {', '.join(targets).title()}...")
    
    today = datetime.datetime.now()
    max_retention_limit = today - datetime.timedelta(days=720)
    
    sync_plan = {}
    oldest_required_start = today
    
    # Step 1: Establish correct lookback horizons per target asset
    for asset_name in targets:
        last_db_time = fn.get_latest_timestamp_from_db(asset_name)
        
        if last_db_time:
            # Look back 2 hours prior to the latest entry to catch/overwrite incomplete candles
            start_date = last_db_time - datetime.timedelta(hours=2)
            if start_date < max_retention_limit:
                start_date = max_retention_limit
            logger.info(f"Incremental Sync Active: {asset_name} checking delta since {start_date}")
        else:
            start_date = max_retention_limit
            logger.info(f"Full Baseline Ingestion Active for {asset_name}. Fetching maximum allowed window.")
            
        sync_plan[asset_name] = start_date
        if start_date < oldest_required_start:
            oldest_required_start = start_date

    # Use the oldest required timestamp across all targets for the base queries
    start_ts = int(oldest_required_start.timestamp())
    end_ts = int(today.timestamp())

    try:
        logger.info(f"Downloading EUR/USD currency baseline grid back to {oldest_required_start}...")
        fx_url = "https://query2.finance.yahoo.com/v8/finance/chart/EURUSD=X"
        headers = {"User-Agent": "Mozilla/5.0"}
        fx_res = requests.get(fx_url, params={"period1": start_ts, "period2": end_ts, "interval": "1h"}, headers=headers, timeout=15)
        
        fx_json = fx_res.json()
        result = fx_json["chart"]["result"][0]
        fx_timestamps = result["timestamp"]
        fx_closes = result["indicators"]["quote"][0]["close"]
        
        fx_dict = {}
        for ts, close in zip(fx_timestamps, fx_closes):
            if ts is None or close is None:
                continue
            hour_stamp = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:00:00")
            fx_dict[hour_stamp] = float(close)

        for asset_name in targets:
            ticker = TICKER_MAPPING[asset_name]
            logger.info(f"Downloading historical data layer for: {asset_name.title()}")
            
            asset_url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
            asset_res = requests.get(asset_url, params={"period1": start_ts, "period2": end_ts, "interval": "1h"}, headers=headers, timeout=15)
            
            asset_json = asset_res.json()
            if not asset_json["chart"]["result"]:
                logger.warning(f"Empty data block returned for ticker {ticker}. Skipping.")
                continue
                
            res_data = asset_json["chart"]["result"][0]
            timestamps = res_data["timestamp"]
            quote = res_data["indicators"]["quote"][0]
            
            opens = quote["open"]
            highs = quote["high"]
            lows = quote["low"]
            closes = quote["close"]
            volumes = quote["volume"]
            
            records = []
            for i in range(len(timestamps)):
                ts = timestamps[i]
                if ts is None or closes[i] is None:
                    continue
                    
                hour_stamp = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:00:00")
                fx_rate = fx_dict.get(hour_stamp, 1.09)
                
                raw_open = opens[i] if opens[i] is not None else closes[i]
                raw_high = highs[i] if highs[i] is not None else closes[i]
                raw_low = lows[i] if lows[i] is not None else closes[i]
                raw_vol = volumes[i] if volumes[i] is not None else 0
                
                records.append({
                    "Timestamp": hour_stamp,
                    "Open_EUR": round((float(raw_open) / fx_rate), 6),
                    "High_EUR": round((float(raw_high) / fx_rate), 6),
                    "Low_EUR": round((float(raw_low) / fx_rate), 6),
                    "Close_EUR": round((float(closes[i]) / fx_rate), 6),
                    "Volume": int(raw_vol)
                })
                
            if not records:
                continue
                
            df = pd.DataFrame(records)
            df = df.sort_values(by=['Timestamp', 'Volume'], ascending=[True, False])
            df = df.drop_duplicates(subset=['Timestamp'], keep='first')
            
            with engine.connect() as conn:
                result = conn.execute(text("SELECT id FROM assets WHERE name ILIKE :name"), {"name": asset_name}).fetchone()
                
                if result:
                    asset_id = result[0]
                    df = df.rename(columns={
                        "Timestamp": "timestamp",
                        "Open_EUR": "open_eur",
                        "High_EUR": "high_eur",
                        "Low_EUR": "low_eur",
                        "Close_EUR": "close_eur",
                        "Volume": "volume"
                    })
                    df['asset_id'] = asset_id
                    
                    try:
                        db_records = df.to_dict(orient='records')
                        
                        # CHANGED TO AN UPSERT: Overwrites price and volume metrics if timestamps match
                        insert_query = text("""
                            INSERT INTO price_history (asset_id, timestamp, open_eur, high_eur, low_eur, close_eur, volume)
                            VALUES (:asset_id, :timestamp, :open_eur, :high_eur, :low_eur, :close_eur, :volume)
                            ON CONFLICT (asset_id, timestamp) 
                            DO UPDATE SET 
                                open_eur = EXCLUDED.open_eur,
                                high_eur = EXCLUDED.high_eur,
                                low_eur = EXCLUDED.low_eur,
                                close_eur = EXCLUDED.close_eur,
                                volume = EXCLUDED.volume;
                            """)
                        
                        conn.execute(insert_query, db_records)
                        conn.commit()
                        logger.info(f"Successfully synced and updated {len(df)} rows for asset: {asset_name}")
                        
                    except Exception as e:
                        logger.error(f"Failed to write data to database for {asset_name}: {str(e)}")
                else:
                    logger.error(f"Asset {asset_name} not found in database. Skipping write.")

        logger.info("Requested commodity data processing completed.")

    except Exception as e:
        logger.error(f"Critical execution error during data fetching: {str(e)}")