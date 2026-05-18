import os
import pandas as pd
from .fetch_data import DATA_DIR, logger
import datetime

def verify_data_integrity(commodity):
    """
    Performs a check if file and data exists and if data is up to date
    """
    csv_path = os.path.join(DATA_DIR, f"{commodity}_30d.csv")
    
    if not os.path.exists(csv_path):
        logger.warning(f"Health Check Failed: {csv_path} does not exist.")
        return False
    
    try:
        df = pd.read_csv(csv_path)
        
        if df.empty:
            logger.warning(f"Health Check Failed: {commodity} file is empty.")
            return False
            
        if len(df) < 10: 
            logger.warning(f"Health Check Failed: {commodity} has critically missing row counts.")
            return False
        
        f1 = open(csv_path, "r")
        last_line = f1.readlines()[-1]
        f1.close()
        
        now = datetime.datetime.now()
        now = now.strftime("%Y-%m-%d %H:00:00")
        
        if now not in last_line:
            logger.warning(f"Health Check Failed: {commodity} data is not up to date.")
            return False
            
        return True

    except Exception as e:
        logger.error(f"Error reading file for {commodity} during validation: {e}")
        return False