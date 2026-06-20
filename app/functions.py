import os
import pandas as pd
from .fetch_data import logger, engine
import datetime
from sqlalchemy import text

def verify_data_integrity(commodity):
    """
    Performs a check if data exists in PostgreSQL and if the records are up to date
    """
    # Default allowed delay during the week
    allowed_delay_hours = 4
    
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