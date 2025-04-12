-- Create cryptocurrency master table
CREATE TABLE IF NOT EXISTS cryptocurrency (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    first_historical_data TIMESTAMP,
    last_historical_data TIMESTAMP,
    status TEXT CHECK (status IN ('active', 'inactive'))
);

-- Create time-series market data table
CREATE TABLE IF NOT EXISTS crypto_market_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crypto_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    price_usd REAL NOT NULL,
    market_cap_usd REAL NOT NULL,
    volume_24h_usd REAL NOT NULL,
    percent_change_1h REAL,
    percent_change_24h REAL,
    percent_change_7d REAL,
    circulating_supply REAL,
    total_supply REAL,
    max_supply REAL,
    UNIQUE(crypto_id, timestamp),
    FOREIGN KEY (crypto_id) REFERENCES cryptocurrency(id) ON DELETE CASCADE
);

-- Create metadata table
CREATE TABLE IF NOT EXISTS crypto_metadata (
    crypto_id INTEGER PRIMARY KEY,
    logo_url TEXT,
    website_url TEXT,
    technical_doc TEXT,
    description TEXT,
    category TEXT,
    FOREIGN KEY (crypto_id) REFERENCES cryptocurrency(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS crypto_signals (
    crypto_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    daily_return REAL,
    ma_7d REAL,
    std_7d REAL,
    RSI REAL,
    signal TEXT,
    PRIMARY KEY (crypto_id, timestamp)
);

-- Table for news sources (Reuters, Yahoo Finance, etc.)
CREATE TABLE IF NOT EXISTS news_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    base_url TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default news sources
INSERT OR IGNORE INTO news_sources (name, base_url, description) VALUES 
('Yahoo Finance', 'https://finance.yahoo.com', 'Yahoo Finance RSS feed'),
('Reuters', 'https://www.reuters.com', 'Reuters Business news');

-- Table for news article categories
CREATE TABLE IF NOT EXISTS news_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT
);

-- Insert common financial categories
INSERT OR IGNORE INTO news_categories (name) VALUES 
('Business'), ('Markets'), ('Economy'), ('Technology'), 
('Companies'), ('Commodities'), ('Stocks'), ('Cryptocurrencies');

-- Main news articles table
CREATE TABLE IF NOT EXISTS news_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    published_date TIMESTAMP,
    fetch_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    summary TEXT,
    content TEXT,
    image_url TEXT,
    image_alt TEXT,
    sentiment_score REAL,
    sentiment_label TEXT,
    is_processed INTEGER DEFAULT 0,
    FOREIGN KEY (source_id) REFERENCES news_sources(id) ON DELETE CASCADE
);

-- Article categories junction table (many-to-many relationship)
CREATE TABLE IF NOT EXISTS article_categories (
    article_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    PRIMARY KEY (article_id, category_id),
    FOREIGN KEY (article_id) REFERENCES news_articles(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES news_categories(id) ON DELETE CASCADE
);

-- Table for tracking asset mentions in articles
CREATE TABLE IF NOT EXISTS article_mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,
    asset_type TEXT NOT NULL,  -- 'stock' or 'crypto'
    asset_symbol TEXT NOT NULL,
    mention_count INTEGER DEFAULT 1,
    is_primary INTEGER DEFAULT 0,  -- Is this the primary subject of the article
    FOREIGN KEY (article_id) REFERENCES news_articles(id) ON DELETE CASCADE,
    UNIQUE(article_id, asset_type, asset_symbol)
);

-- Table for vector embeddings to support RAG applications
CREATE TABLE IF NOT EXISTS article_embeddings (
    id TEXT PRIMARY KEY,  -- UUID
    article_id INTEGER NOT NULL,
    chunk_text TEXT,      -- The text chunk that was embedded
    chunk_index INTEGER,  -- Position of this chunk in the article
    embedding_data BLOB,  -- Binary serialized vector data
    embedding_model TEXT, -- Model name/version used
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES news_articles(id) ON DELETE CASCADE,
    UNIQUE(article_id, chunk_index)
);


-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_crypto_symbol ON cryptocurrency(symbol);
CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON crypto_market_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_market_data_crypto_id ON crypto_market_data(crypto_id);

-- Indexes for news tables
CREATE INDEX IF NOT EXISTS idx_news_articles_source ON news_articles(source_id);
CREATE INDEX IF NOT EXISTS idx_news_articles_date ON news_articles(published_date);
CREATE INDEX IF NOT EXISTS idx_news_articles_processed ON news_articles(is_processed);
CREATE INDEX IF NOT EXISTS idx_article_mentions_symbol ON article_mentions(asset_symbol);
CREATE INDEX IF NOT EXISTS idx_article_mentions_type ON article_mentions(asset_type);
CREATE INDEX IF NOT EXISTS idx_article_embeddings_article ON article_embeddings(article_id);


-- Views for better select queries
CREATE VIEW IF NOT EXISTS vw_recent_news AS
SELECT 
    a.id, 
    s.name AS source, 
    a.title, 
    a.url, 
    a.published_date, 
    a.summary, 
    a.sentiment_label,
    a.fetch_date,
    a.is_processed
FROM 
    news_articles a
JOIN 
    news_sources s ON a.source_id = s.id
ORDER BY 
    a.published_date DESC;

-- View for news articles mentioning specific assets
CREATE VIEW IF NOT EXISTS vw_asset_news AS
SELECT 
    m.asset_type,
    m.asset_symbol,
    a.id AS article_id,
    s.name AS source,
    a.title,
    a.url,
    a.published_date,
    a.sentiment_label,
    m.mention_count,
    m.is_primary
FROM 
    article_mentions m
JOIN 
    news_articles a ON m.article_id = a.id
JOIN 
    news_sources s ON a.source_id = s.id
ORDER BY 
    m.asset_symbol, a.published_date DESC;