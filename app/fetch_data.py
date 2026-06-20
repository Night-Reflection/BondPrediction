import os
import datetime
import logging
from logging.handlers import RotatingFileHandler
import pandas as pd
import requests
from sqlalchemy import create_engine, text

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
DB_URL = "postgresql://admin:CommoditiesPredictionPass123@127.0.0.1:5433/market_predictions"
engine = create_engine(DB_URL, echo=False)

os.makedirs(LOG_DIR, exist_ok=True)

# --- ROTATING LOGGER SETUP ---
log_filename = os.path.join(LOG_DIR, "app.log")
logger = logging.getLogger("BulletproofDataSync")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = RotatingFileHandler(log_filename, maxBytes=10*1024*1024, backupCount=2)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

TICKER_MAPPING = {
    "Gold": "GC=F",
    "Silver": "SI=F",
    "Copper": "HG=F"
}

def fetch_and_save_commodity_data(requested_commodities=None):
    """
    Fetches historical data from Yahoo Finance.
    
    requested_commodities: List of strings e.g., ['Gold'] or ['Gold', 'Copper']. 
    
    If None, fetches all available commodities.
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
    one_year_ago = today - datetime.timedelta(days=1*365)
    
    start_ts = int(one_year_ago.timestamp())
    end_ts = int(today.timestamp())

    try:
        logger.info("Downloading EUR/USD currency conversion baseline table...")
        
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
            
            if asset_name in ["Gold", "Silver"]:
                unit_divider = 31.1034768  # Convert Troy Ounce -> Grams
            elif asset_name == "Copper":
                unit_divider = 453.59237   # Convert Pounds -> Grams
            else:
                unit_divider = 1.0
            
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
                    "Open_EUR": round((float(raw_open) / fx_rate) / unit_divider, 6),
                    "High_EUR": round((float(raw_high) / fx_rate) / unit_divider, 6),
                    "Low_EUR": round((float(raw_low) / fx_rate) / unit_divider, 6),
                    "Close_EUR": round((float(closes[i]) / fx_rate) / unit_divider, 6),
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
                        
                        insert_query = text("""
                            INSERT INTO price_history (asset_id, timestamp, open_eur, high_eur, low_eur, close_eur, volume)
                            VALUES (:asset_id, :timestamp, :open_eur, :high_eur, :low_eur, :close_eur, :volume)
                            ON CONFLICT (asset_id, timestamp) DO NOTHING;
                            """)
                        
                        conn.execute(insert_query, db_records)
                        conn.commit()
                        
                        logger.info(f"Successfully committed {len(df)} rows to database for asset: {asset_name}")
                        
                    except Exception as e:
                        logger.error(f"Failed to write data to database for {asset_name}: {str(e)}")
                else:
                    logger.error(f"Asset {asset_name} not found in database. Skipping database write.")

        logger.info("Requested commodity data processing completed.")

    except Exception as e:
        logger.error(f"Critical execution error during data sync: {str(e)}")