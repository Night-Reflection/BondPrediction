-- init.sql

-- Connect to the database that Docker Compose automatically created
\c market_predictions;

-- 1. Create Assets tracking table
CREATE TABLE assets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL
);

-- 2. Create the Price History table
CREATE TABLE price_history (
    id BIGSERIAL PRIMARY KEY,
    asset_id INT REFERENCES assets(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    open_eur NUMERIC(12, 6) NOT NULL,
    high_eur NUMERIC(12, 6) NOT NULL,
    low_eur NUMERIC(12, 6) NOT NULL,
    close_eur NUMERIC(12, 6) NOT NULL,
    volume BIGINT NOT NULL,
    UNIQUE(asset_id, timestamp) 
);

-- 3. Create Indexes for fast querying
CREATE INDEX idx_price_history_asset_time ON price_history(asset_id, timestamp DESC);

-- 4. Seed your initial assets
INSERT INTO assets (name) VALUES ('Copper'), ('Gold'), ('Silver');