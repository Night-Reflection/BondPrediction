import pandas as pd
from sqlalchemy import text
from functions import engine


def print_row_counts():
    """
    Prints the total number of historical price rows saved 
    for every commodity in the database.
    """
    query = text("""
        SELECT a.name AS commodity, COUNT(ph.id) AS total_rows
        FROM assets a
        LEFT JOIN price_history ph ON a.id = ph.asset_id
        GROUP BY a.name
        ORDER BY total_rows DESC;
    """)
    
    print("\n--- ROW COUNTS PER COMMODITY ---")
    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn)
        print(df.to_string(index=False))


def print_latest_commodity_data(commodity_name, limit=20):
    """
    Fetches and prints the latest rows for a specific commodity.
    Matches the name case-insensitively (e.g., 'gold' or 'Gold').
    """
    query = text("""
        SELECT ph.timestamp, ph.open_eur, ph.high_eur, ph.low_eur, ph.close_eur, ph.volume
        FROM price_history ph
        JOIN assets a ON ph.asset_id = a.id
        WHERE a.name ILIKE :name
        ORDER BY ph.timestamp DESC
        LIMIT :limit;
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn, params={"name": commodity_name, "limit": limit})
        
    if df.empty:
        print(f"\nNo data found for commodity matching: '{commodity_name}'")
    else:
        print(f"\n--- LATEST {limit} ROWS FOR {commodity_name.upper()} ---")
        print(df.to_string(index=False))

     
def print_oldest_commodity_data(commodity_name, limit=20):
    """
    Fetches and prints the oldest rows for a specific commodity.
    Matches the name case-insensitively (e.g., 'gold' or 'Gold').
    """
    query = text("""
        SELECT ph.timestamp, ph.open_eur, ph.high_eur, ph.low_eur, ph.close_eur, ph.volume
        FROM price_history ph
        JOIN assets a ON ph.asset_id = a.id
        WHERE a.name ILIKE :name
        ORDER BY ph.timestamp ASC
        LIMIT :limit;
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn, params={"name": commodity_name, "limit": limit})
        
    if df.empty:
        print(f"\nNo data found for commodity matching: '{commodity_name}'")
    else:
        print(f"\n--- OLDEST {limit} ROWS FOR {commodity_name.upper()} ---")
        print(df.to_string(index=False))


def clear_database_data(commodity_name=None):
    """
    Clears price data from the database.
    - If commodity_name is provided: Clears only that specific asset's history.
    - If commodity_name is None (default): Wipes ALL historical data across all assets.
    """
    with engine.connect() as conn:
        if commodity_name:
            # 1. Clear data for only one specific commodity
            delete_query = text("""
                DELETE FROM price_history 
                WHERE asset_id = (SELECT id FROM assets WHERE name ILIKE :name);
            """)
            result = conn.execute(delete_query, {"name": commodity_name})
            conn.commit()
            print(f"\nSuccessfully cleared history for: {commodity_name.upper()}")
        else:
            # 2. Clear absolutely everything
            # TRUNCATE is faster and cleaner than DELETE for wiping a whole table
            delete_query = text("TRUNCATE TABLE price_history RESTART IDENTITY CASCADE;")
            conn.execute(delete_query)
            conn.commit()
            print("\nWARNING: All price history tracking data has been fully wiped!")


# --- SCRATCHPAD: Call your functions down here ---
if __name__ == "__main__":
    
    # Example 1: View row summary counts across Gold, Silver, Copper
    #print_row_counts()
    
    # Example 2: Manually check latest data entries for Gold
    print_latest_commodity_data("gold", limit=10)
    
    # Example 3: Manually check oldest data entries for Gold
    # print_oldest_commodity_data("gold", limit=10)
    
    # Example 4: Clear ONLY silver data (uncomment to run)
    # clear_database_data("silver")
    
    # Example 5: Nuke ALL historical data to start completely fresh (uncomment to run)
    # clear_database_data()
    
    ...