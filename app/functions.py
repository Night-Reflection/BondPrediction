import os
import pandas as pd
import logging
from logging.handlers import RotatingFileHandler
import datetime
from sqlalchemy import text, create_engine

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_URL = "postgresql://admin:CommoditiesPredictionPass123@127.0.0.1:5433/market_predictions"
engine = create_engine(DB_URL, echo=False)
LOG_DIR = os.path.join(BASE_DIR, "logs")

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

def verify_data_integrity(commodity):
    """
    Performs a check if data exists in PostgreSQL and if the records are up to date
    """
    # Default allowed delay during the week
    allowed_delay_hours = 0
    
    query = text("""
        SELECT ph.timestamp 
        FROM price_history ph
        JOIN assets a ON ph.asset_id = a.id
        WHERE a.name ILIKE :commodity
        ORDER BY ph.timestamp DESC
        LIMIT 1;
    """)
    
    try:
        with engine.connect() as conn:
            # Fetch the absolute newest timestamp for this asset
            result = conn.execute(query, {"commodity": commodity}).fetchone()
            
            # If no row comes back, the asset has no historical data yet
            if not result:
                logger.warning(f"Health Check Failed: No database records found for {commodity}.")
                return False
                
            # Extract and drop the timezone attribute so it matches local naive time
            last_timestamp = result[0].replace(tzinfo=None)
            
            # Normal local machine time (offset-naive)
            now = datetime.datetime.now()
            
            # Calculate the time difference
            time_diff = now - last_timestamp

            # Handle weekend logic
            if now.weekday() in [5, 6]:
                logger.info(f"Health Check Note: It's the weekend, market data may be paused.")
                allowed_delay_hours = 60
            
            if time_diff.total_seconds() > allowed_delay_hours * 3600:
                logger.warning(f"Health Check Failed: {commodity} database data is stale. Last entry: {last_timestamp}")
                return False
                
            logger.info(f"Health Check Passed: {commodity} data is healthy and up to date.")
            return True

    except Exception as e:
        logger.error(f"Error checking database for {commodity} during health check: {e}")
        return False
    
def get_latest_timestamp_from_db(asset_name):
    """
    Queries the database for the newest timestamp recorded for a given asset.
    Returns a datetime object if found, otherwise returns None.
    """
    query = text("""
        SELECT ph.timestamp 
        FROM price_history ph
        JOIN assets a ON ph.asset_id = a.id
        WHERE a.name ILIKE :name
        ORDER BY ph.timestamp DESC
        LIMIT 1;
    """)
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"name": asset_name}).fetchone()
            if result and result[0]:
                # Strip timezone info to remain offset-naive and compatible with app setups
                return result[0].replace(tzinfo=None)
    except Exception as e:
        logger.error(f"Failed to fetch baseline sync timestamp for {asset_name}: {e}")
    return None