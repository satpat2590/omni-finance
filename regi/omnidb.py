import sqlite3
import os
import datetime
from contextlib import contextmanager
import logging
import json
import logging.config
import pandas as pd 
import numpy as np
import time
import random

def get_logging_config() -> dict:
    """
    Retrieve the logging configuration from a JSON file.

    :return: A dictionary that can be used to configure logging for the module.
    """
    jpath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config/loggingConfig.json")
    with open(jpath, 'r') as f:
        config_dict = json.load(f)
    return config_dict

class OmniDB:
    def __init__(self):
        """
        Initializes the OmniDB class by setting up the database path and configuring logging.
        """
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/omni.db")
        print(self.db_path)

        logconfig = get_logging_config()
        logging.config.dictConfig(logconfig)

        self.logger = logging.getLogger(__name__)

    @contextmanager
    def sqlite_connect2(self, timeout=30):
        """
        Context manager providing a cursor to interact with the SQLite database.
        Automatically commits if successful, and rolls back on errors.
        """
        conn = sqlite3.connect(self.db_path, timeout=timeout)
        cursor = conn.cursor()

        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.warning(f"Error rolling back due to: {e}\n")
            raise e
        finally:
            cursor.close()
            conn.close()

    @contextmanager
    def sqlite_connect(self, timeout=60, max_retries=5, retry_delay=1.0):
        """
        Context manager providing a cursor to interact with the SQLite database.
        Automatically commits if successful, and rolls back on errors.
        Implements retry logic for database locks.

        :param timeout: SQLite connection timeout in seconds
        :param max_retries: Maximum number of retries in case of database locks
        :param retry_delay: Base delay between retries in seconds (exponential backoff applied)
        """
        conn = None
        cursor = None
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                conn = sqlite3.connect(self.db_path, timeout=timeout)
                conn.execute("PRAGMA foreign_keys = ON")
                cursor = conn.cursor()
                
                yield cursor
                
                # If we get here, operation was successful
                conn.commit()
                return
                
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and retry_count < max_retries:
                    retry_count += 1
                    # Exponential backoff with jitter
                    delay = retry_delay * (2 ** (retry_count - 1)) * (0.5 + random.random())
                    self.logger.warning(f"Database locked, retrying in {delay:.2f} seconds (attempt {retry_count}/{max_retries})")
                    
                    # Clean up before retry
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.rollback()
                        conn.close()
                    
                    time.sleep(delay)
                else:
                    # Either not a lock error or we've exceeded retries
                    self.logger.error(f"SQLite error: {str(e)}")
                    if conn:
                        conn.rollback()
                    raise
                    
            except Exception as e:
                self.logger.error(f"Error during database operation: {str(e)}")
                if conn:
                    conn.rollback()
                raise
                
            finally:
                # This block is executed after the try/except block,
                # but only if we didn't continue the while loop
                if retry_count == max_retries:
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.close()
        
        # If we've exhausted all retries
        if retry_count > max_retries:
            self.logger.error(f"Failed to acquire database lock after {max_retries} retries")
            raise sqlite3.OperationalError(f"Database still locked after {max_retries} retries")
        
    def initialize_database(self):
        """
        Initialize all tables if they don't exist.
        This method should be called during initialization of the OmniDB instance.
        """
        # Execute the SQL from omni.sql file
        sql_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config/omni.sql")
        if os.path.exists(sql_path):
            with open(sql_path, 'r') as f:
                sql_script = f.read()
            
            with self.sqlite_connect() as cursor:
                cursor.executescript(sql_script)
            
            self.logger.info("Initialized all tables using SQL script")

#############################################
############### CRYPTO TABLES ###############
#############################################

    def create_signals_table(self):
        """
        Create the 'crypto_signals' table if it does not exist.
        This table will store the technical indicators for each crypto/timestamp pair.
        
        :return: None
        """
        create_table_query = """
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
        """
        with self.sqlite_connect() as cursor:
            cursor.execute(create_table_query)
            self.logger.info("Ensured that crypto_signals table exists.")

    ##################
    # CREATE Methods #
    ##################

    def insert_cryptos(self, cryptos):
        """
        Insert or ignore new cryptocurrencies into the `cryptocurrency` table.

        :param cryptos: A list of tuples, where each tuple corresponds to:
                        (id, symbol, name, slug, first_historical_data, last_historical_data, status)
        :return: None
        """
        query = """
            INSERT OR IGNORE INTO cryptocurrency (
                id, symbol, name, slug, first_historical_data, last_historical_data, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        with self.sqlite_connect() as cursor:
            cursor.executemany(query, cryptos)
            self.logger.info(f"{len(cryptos)} coins inserted into the cryptocurrency table.")

    def insert_market_data(self, market_data):
        """
        Insert or update market data into the `crypto_market_data` table.
        Uses ON CONFLICT for (crypto_id, timestamp) to update existing records.

        :param market_data: A list of tuples where each tuple corresponds to:
                            (crypto_id, timestamp, price_usd, market_cap_usd, volume_24h_usd,
                             percent_change_1h, percent_change_24h, percent_change_7d,
                             circulating_supply, total_supply, max_supply)
        :return: None
        """
        query = """
            INSERT INTO crypto_market_data (
                crypto_id, timestamp, price_usd, market_cap_usd, volume_24h_usd,
                percent_change_1h, percent_change_24h, percent_change_7d,
                circulating_supply, total_supply, max_supply
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(crypto_id, timestamp)
            DO UPDATE SET
                price_usd = excluded.price_usd,
                market_cap_usd = excluded.market_cap_usd,
                volume_24h_usd = excluded.volume_24h_usd,
                percent_change_1h = excluded.percent_change_1h,
                percent_change_24h = excluded.percent_change_24h,
                percent_change_7d = excluded.percent_change_7d,
                circulating_supply = excluded.circulating_supply,
                total_supply = excluded.total_supply,
                max_supply = excluded.max_supply;
        """
        with self.sqlite_connect() as cursor:
            cursor.executemany(query, market_data)
            self.logger.info(f"{len(market_data)} data items inserted/updated in the crypto_market_data table.")

    def insert_metadata(self, metadata):
        """
        Insert or update cryptocurrency metadata into the `crypto_metadata` table.
        Uses ON CONFLICT(crypto_id) to update existing records.

        :param metadata: A list of tuples where each tuple corresponds to:
                         (crypto_id, logo_url, website_url, technical_doc, description, category)
        :return: None
        """
        query = """
            INSERT INTO crypto_metadata (
                crypto_id, logo_url, website_url, technical_doc, description, category
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(crypto_id)
            DO UPDATE SET
                category = excluded.category;
        """
        with self.sqlite_connect() as cursor:
            cursor.executemany(query, metadata)
            self.logger.info(f"{len(metadata)} metadata items inserted/updated in the crypto_metadata table.")

    ###############
    # READ Methods#
    ###############

    def get_all_cryptos(self) -> pd.DataFrame:
        """
        Retrieve all cryptocurrencies from the `cryptocurrency` table.

        :return: A pandas DataFrame containing all records from the `cryptocurrency` table.
        """
        query = "SELECT * FROM cryptocurrency;"
        with self.sqlite_connect() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            if rows:
                df = pd.DataFrame(rows, columns=[desc[0] for desc in cursor.description])
                self.logger.info(f"SELECT query on 'cryptocurrency' was successful!")
                return df
            else:
                return pd.DataFrame()  # Return empty DataFrame if no records

    def get_market_data(self, crypto_id: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Retrieve market data for a given crypto_id and optional date range.

        :param crypto_id: The ID of the cryptocurrency.
        :param start_date: Start date for the query range (YYYY-MM-DD HH:MM:SS).
        :param end_date: End date for the query range (YYYY-MM-DD HH:MM:SS).
        :return: A pandas DataFrame containing all matching market data records.
        """
        query = "SELECT * FROM crypto_market_data WHERE crypto_id = ?"
        params = [crypto_id]

        if start_date and end_date:
            query += " AND timestamp BETWEEN ? AND ?"
            params.extend([start_date, end_date])

        with self.sqlite_connect() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            if rows:
                df = pd.DataFrame(rows, columns=[desc[0] for desc in cursor.description])
                self.logger.info(f"SELECT query on 'crypto_market_data' was successful!")
                return df
            else:
                return pd.DataFrame()

    def get_latest_market_data(self, crypto_id: str) -> pd.DataFrame:
        """
        Retrieve the latest (most recent) market data for a given crypto_id.

        :param crypto_id: The ID of the cryptocurrency.
        :return: A pandas DataFrame with a single row (latest timestamp) or empty if not found.
        """
        query = """
            SELECT *
            FROM crypto_market_data
            WHERE crypto_id = ?
            ORDER BY timestamp DESC
            LIMIT 1;
        """
        with self.sqlite_connect() as cursor:
            cursor.execute(query, (crypto_id,))
            row = cursor.fetchone()
            if row:
                df = pd.DataFrame([row], columns=[desc[0] for desc in cursor.description])
                self.logger.info(f"SELECT query on 'crypto_market_data' was successful!")
                return df
            else:
                return pd.DataFrame()

    ################
    # UPDATE Methods
    ################

    def update_crypto_status(self, crypto_id: str, new_status: str):
        """
        Update the status of a given cryptocurrency (e.g., active/inactive).

        :param crypto_id: The ID of the cryptocurrency to be updated.
        :param new_status: The new status to assign (e.g., "active", "inactive").
        :return: None
        """
        query = "UPDATE cryptocurrency SET status = ? WHERE id = ?"
        with self.sqlite_connect() as cursor:
            cursor.execute(query, (new_status, crypto_id))
            self.logger.info(f"Status of {crypto_id} updated to {new_status}.")

    def update_market_data(self, crypto_id: str, timestamp: str, new_price: float):
        """
        Update the price for a given crypto_id at a specific timestamp.

        :param crypto_id: The ID of the cryptocurrency.
        :param timestamp: The timestamp (YYYY-MM-DD HH:MM:SS) of the record to update.
        :param new_price: The new price_usd value.
        :return: None
        """
        query = """
            UPDATE crypto_market_data
            SET price_usd = ?
            WHERE crypto_id = ? AND timestamp = ?
        """
        with self.sqlite_connect() as cursor:
            cursor.execute(query, (new_price, crypto_id, timestamp))
            self.logger.info(f"Market data for {crypto_id} at {timestamp} updated to price {new_price}.")

    ################
    # DELETE Methods
    ################

    def delete_crypto(self, crypto_id: str):
        """
        Delete a cryptocurrency and its related market data from the database.
        The associated metadata (if any) is preserved.

        :param crypto_id: The ID of the cryptocurrency to be removed.
        :return: None
        """
        query_crypto = "DELETE FROM cryptocurrency WHERE id = ?"
        query_market = "DELETE FROM crypto_market_data WHERE crypto_id = ?"

        with self.sqlite_connect() as cursor:
            cursor.execute(query_market, (crypto_id,))
            cursor.execute(query_crypto, (crypto_id,))
            self.logger.info(f"{crypto_id} was deleted from all tables (metadata preserved).")

    def delete_old_market_data(self, cutoff_date: str):
        """
        Delete market data older than a specific date.

        :param cutoff_date: All records with timestamps older than this date (YYYY-MM-DD HH:MM:SS) will be removed.
        :return: None
        """
        query = "DELETE FROM crypto_market_data WHERE timestamp < ?"
        with self.sqlite_connect() as cursor:
            cursor.execute(query, (cutoff_date,))
            self.logger.info(f"All data older than {cutoff_date} was deleted from crypto_market_data.")


    #########################################
    # ANALYTICS & TECHNICAL INDICATOR METHODS
    #########################################

    def calculate_technical_indicators(self, crypto_id: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Retrieve market data for a specified crypto_id and date range, then calculate
        various analytics or technical indicators that might help identify trends
        (bearish or bullish).

        :param crypto_id: The ID of the cryptocurrency.
        :param start_date: Optional start date for the data (YYYY-MM-DD HH:MM:SS).
        :param end_date: Optional end date for the data (YYYY-MM-DD HH:MM:SS).
        :return: A pandas DataFrame including the original market data plus new columns
                 for calculated indicators.
        """
        df = self.get_market_data(crypto_id, start_date, end_date)
        if df.empty:
            self.logger.warning(f"No market data found for {crypto_id} in given date range.")
            return df

        # Convert timestamp column to datetime if needed
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.sort_values(by='timestamp', inplace=True)

        # ---------- Example Metrics: Daily Returns & Rolling Averages ---------- #
        if 'price_usd' in df.columns:
            # 1. Daily Return (percentage)
            df['daily_return'] = df['price_usd'].pct_change() * 100

            # 2. 7-Day Moving Average Price
            df['ma_7d'] = df['price_usd'].rolling(window=7).mean()

            # 3. 7-Day Rolling Standard Deviation (volatility proxy)
            df['std_7d'] = df['price_usd'].rolling(window=7).std()

        # ---------- Example RSI Calculation (14-day) ---------- #
        window_length = 14
        delta = df['price_usd'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window_length).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window_length).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))

        # ---------- Generate Simple Signal ---------- #
        conditions = [
            (df['RSI'] > 70),
            (df['RSI'] < 30)
        ]
        choices = ['Bearish Signal', 'Bullish Signal']
        df['signal'] = np.select(conditions, choices, default='Neutral/No signal')

        return df

    def save_indicators_to_db(self, indicators_df: pd.DataFrame):
        """
        Insert or replace indicator rows into the 'crypto_signals' table.
        Expects columns: ['crypto_id', 'timestamp', 'daily_return', 'ma_7d', 'std_7d', 'RSI', 'signal'].
        
        :param indicators_df: The pandas DataFrame with indicator columns to store.
        :return: None
        """
        if indicators_df.empty:
            self.logger.warning("No indicator data to save.")
            return
        
        # Ensure the table exists
        self.create_signals_table()

        # Convert timestamps back to string if they're in datetime form
        if pd.api.types.is_datetime64_any_dtype(indicators_df['timestamp']):
            indicators_df['timestamp'] = indicators_df['timestamp'].astype(str)

        # Prepare the data for insertion
        # We only insert columns relevant to the signals table
        records = indicators_df[[
            'crypto_id',
            'timestamp',
            'daily_return',
            'ma_7d',
            'std_7d',
            'RSI',
            'signal'
        ]].to_records(index=False)  # Convert df to numpy recarray, then to list of tuples

        insert_query = """
        INSERT OR REPLACE INTO crypto_signals (
            crypto_id, 
            timestamp, 
            daily_return, 
            ma_7d, 
            std_7d, 
            RSI, 
            signal
        )
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """

        with self.sqlite_connect() as cursor:
            cursor.executemany(insert_query, records)
            self.logger.info(f"Saved {len(records)} indicator records to crypto_signals table.")

    def analyze_crypto_bull_bear(self, crypto_id: str, start_date: str = None, end_date: str = None) -> str:
        """
        A simple method that returns a short textual assessment of the crypto's
        recent trend, based on the final row's RSI or daily return.

        :param crypto_id: The ID of the cryptocurrency to analyze.
        :param start_date: Optional start date for the data (YYYY-MM-DD HH:MM:SS).
        :param end_date: Optional end date for the data (YYYY-MM-DD HH:MM:SS).
        :return: A string indicating "Bullish", "Bearish", or "Neutral".
        """
        df = self.calculate_technical_indicators(crypto_id, start_date, end_date)
        if df.empty:
            return "No data available to determine a trend."

        # Save the updated DataFrame to db so we can do future queries without recalculating
        self.save_indicators_to_db(df)

        latest_row = df.iloc[-1]

        if latest_row['signal'] == 'Bullish Signal':
            return f"Bullish outlook for {crypto_id} based on RSI signal."
        elif latest_row['signal'] == 'Bearish Signal':
            return f"Bearish outlook for {crypto_id} based on RSI signal."
        else:
            return f"Neutral signals for {crypto_id} at the moment."
        
#############################################
################ NEWS TABLES ################
#############################################

    def get_source_id(self, source_name):
        """
        Get the ID for a news source, creating it if it doesn't exist.
        
        :param source_name: Name of the news source (e.g., 'Reuters', 'Yahoo Finance')
        :return: The ID of the source
        """
        with self.sqlite_connect() as cursor:
            # Try to get existing source
            cursor.execute("SELECT id FROM news_sources WHERE name = ?", (source_name,))
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
            # Create new source if it doesn't exist
            cursor.execute(
                "INSERT INTO news_sources (name) VALUES (?)",
                (source_name,)
            )
            self.logger.info(f"Created new news source: {source_name}")
            return cursor.lastrowid
        
    ################
    # READ Methods
    ################

    def get_category_id(self, category_name):
        """
        Get the ID for a news category, creating it if it doesn't exist.
        
        :param category_name: Name of the category (e.g., 'Business', 'Technology')
        :return: The ID of the category
        """
        if not category_name or category_name.strip() == '':
            return None
        
        with self.sqlite_connect() as cursor:
            # Try to get existing category
            cursor.execute("SELECT id FROM news_categories WHERE name = ?", (category_name,))
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
        with self.sqlite_connect() as cursor:
            # Create new category if it doesn't exist
            cursor.execute(
                "INSERT INTO news_categories (name) VALUES (?)",
                (category_name,)
            )
            self.logger.info(f"Created new news category: {category_name}")
            return cursor.lastrowid

    def get_recent_articles(self, limit=50, source=None, category=None):
        """
        Get recent news articles with optional filtering.
        
        :param limit: Maximum number of articles to return
        :param source: Filter by source name (optional)
        :param category: Filter by category name (optional)
        :return: List of article dictionaries
        """
        query = """
            SELECT 
                a.id, 
                s.name AS source,
                a.title,
                a.url,
                a.published_date,
                a.fetch_date,
                a.summary
            FROM 
                news_articles a
            JOIN 
                news_sources s ON a.source_id = s.id
        """
        
        params = []
        where_clauses = []
        
        if source:
            where_clauses.append("s.name = ?")
            params.append(source)
        
        if category:
            query += """
                JOIN 
                    article_categories ac ON a.id = ac.article_id
                JOIN 
                    news_categories c ON ac.category_id = c.id
            """
            where_clauses.append("c.name = ?")
            params.append(category)
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY a.published_date DESC LIMIT ?"
        params.append(limit)
        
        articles = []
        with self.sqlite_connect() as cursor:
            cursor.execute(query, params)
            
            for row in cursor.fetchall():
                articles.append({
                    "id": row[0],
                    "source": row[1],
                    "title": row[2],
                    "url": row[3],
                    "published_date": row[4],
                    "fetch_date": row[5],
                    "summary": row[6]
                })
        
        return articles

    def get_articles_by_asset(self, asset_symbol, asset_type='stock', limit=20):
        """
        Get articles that mention a specific asset.
        
        :param asset_symbol: Symbol of the asset (e.g., 'AAPL')
        :param asset_type: Type of asset ('stock' or 'crypto')
        :param limit: Maximum number of articles to return
        :return: List of article dictionaries
        """
        query = """
            SELECT 
                a.id,
                s.name AS source,
                a.title,
                a.url,
                a.published_date,
                a.summary,
                m.mention_count,
                m.is_primary
            FROM 
                article_mentions m
            JOIN 
                news_articles a ON m.article_id = a.id
            JOIN 
                news_sources s ON a.source_id = s.id
            WHERE 
                m.asset_symbol = ? AND m.asset_type = ?
            ORDER BY 
                a.published_date DESC, m.mention_count DESC
            LIMIT ?
        """
        
        articles = []
        with self.sqlite_connect() as cursor:
            cursor.execute(query, (asset_symbol, asset_type, limit))
            
            for row in cursor.fetchall():
                articles.append({
                    "id": row[0],
                    "source": row[1],
                    "title": row[2],
                    "url": row[3],
                    "published_date": row[4],
                    "summary": row[5],
                    "mention_count": row[6],
                    "is_primary": bool(row[7])
                })
        
        return articles

    ################
    # CREATE Methods
    ################
    
    def store_article(self, title, url, source_name, published_date=None, summary=None, 
                    content=None, image_url=None, image_alt=None, categories=None):
        """
        Store an article in the database, along with its categories.
        
        :param title: Article title
        :param url: Article URL (must be unique)
        :param source_name: Name of the source (e.g., 'Reuters', 'Yahoo Finance')
        :param published_date: Publication date (optional)
        :param summary: Article summary/description (optional)
        :param content: Full article content (optional)
        :param image_url: URL to article image (optional)
        :param image_alt: Alt text for image (optional)
        :param categories: List of category names (optional)
        :return: The ID of the inserted/updated article
        """
        if not url or not title:
            self.logger.warning("Cannot store article without URL and title")
            return None
        
        # Get or create source
        source_id = self.get_source_id(source_name)
        
        # Check if article already exists
        with self.sqlite_connect() as cursor:
            cursor.execute("SELECT id FROM news_articles WHERE url = ?", (url,))
            existing = cursor.fetchone()
            
            if existing:
                article_id = existing[0]
                # Update existing article
                cursor.execute("""
                    UPDATE news_articles SET
                        title = ?, 
                        source_id = ?,
                        published_date = ?,
                        summary = ?,
                        content = ?,
                        image_url = ?,
                        image_alt = ?,
                        fetch_date = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (title, source_id, published_date, summary, content, 
                    image_url, image_alt, article_id))
                
                self.logger.info(f"Updated existing article: {title}")
            else:
                # Insert new article
                cursor.execute("""
                    INSERT INTO news_articles (
                        title, url, source_id, published_date, summary, 
                        content, image_url, image_alt, fetch_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (title, url, source_id, published_date, summary, 
                    content, image_url, image_alt))
                
                article_id = cursor.lastrowid
                self.logger.info(f"Inserted new article: {title}")
            
        with self.sqlite_connect() as cursor:
            # Process categories if provided
            if categories and isinstance(categories, list):
                # Clear existing categories for this article
                cursor.execute("DELETE FROM article_categories WHERE article_id = ?", (article_id,))
                
                # Add new categories
                for category_name in categories:
                    category_id = self.get_category_id(category_name)
                    if category_id:
                        cursor.execute("""
                            INSERT INTO article_categories (article_id, category_id)
                            VALUES (?, ?)
                        """, (article_id, category_id))
        
        return article_id
    
    def store_reuters_article(self, article_data):
        """
        Store an article from Reuters in the database.
        
        :param article_data: Dictionary with Reuters article data
        :return: The ID of the inserted/updated article
        """
        title = article_data.get('headline', '')
        url = article_data.get('url', '')
        published_date = article_data.get('publication_datetime', '')
        summary = article_data.get('description', '')
        image_url = article_data.get('image_url', '')
        image_alt = article_data.get('image_alt', '')
        
        # Get category if available
        categories = []
        if article_data.get('category'):
            categories = [article_data['category']]
        
        # Store the article
        article_id = self.store_article(
            title=title,
            url=url,
            source_name='Reuters',
            published_date=published_date,
            summary=summary,
            image_url=image_url,
            image_alt=image_alt,
            categories=categories
        )
        
        # Extract ticker mentions from title
        #if article_id and title:
        #    self.extract_asset_mentions(article_id, title, 'stock')
        #    
        #    # If we have a summary, extract from that too
        #    if summary:
        #        self.extract_asset_mentions(article_id, summary, 'stock')
        
        return article_id

    def store_yahoo_finance_article(self, article_data):
        """
        Store an article from Yahoo Finance in the database.
        
        :param article_data: Dictionary with Yahoo Finance article data
        :return: The ID of the inserted/updated article
        """
        title = article_data.get('title', '')
        url = article_data.get('link', '')
        published_date = article_data.get('published', '')
        
        # Store the article
        article_id = self.store_article(
            title=title,
            url=url,
            source_name='Yahoo Finance',
            published_date=published_date,
            categories=['Finance']  # Default category
        )
        
        # Extract ticker mentions from title
        #if article_id and title:
        #    self.extract_asset_mentions(article_id, title, 'stock')
        
        return article_id

    def store_articles_from_scraper2(self, yfinance_data, reuters_data):
        """
        Store all articles from the news scraper.
        
        :param yfinance_data: List of articles from Yahoo Finance
        :param reuters_data: List of articles from Reuters
        :return: Dictionary with count of articles stored
        """
        yahoo_count = 0
        reuters_count = 0
        
        # Process Yahoo Finance articles
        for article in yfinance_data:
            if self.store_yahoo_finance_article(article):
                yahoo_count += 1
        
        # Process Reuters articles
        for article in reuters_data:
            if self.store_reuters_article(article):
                reuters_count += 1
        
        self.logger.info(f"Stored {yahoo_count} Yahoo Finance articles and {reuters_count} Reuters articles")
        
        return {
            "yahoo_finance": yahoo_count,
            "reuters": reuters_count,
            "total": yahoo_count + reuters_count
        }
    
    def store_articles_from_scraper(self, yfinance_data, reuters_data):
        """
        Store all articles from the news scraper in a single database transaction.
        
        :param yfinance_data: List of articles from Yahoo Finance
        :param reuters_data: List of articles from Reuters
        :return: Dictionary with count of articles stored
        """
        yahoo_count = 0
        reuters_count = 0
        
        # Use a single database connection for all operations
        with self.sqlite_connect() as cursor:
            # Process Yahoo Finance articles
            for article in yfinance_data:
                title = article.get('title', '')
                url = article.get('link', '')
                published_date = article.get('published', '')
                
                if not url or not title:
                    continue
                    
                # Get source ID
                cursor.execute("SELECT id FROM news_sources WHERE name = ?", ('Yahoo Finance',))
                result = cursor.fetchone()
                if result:
                    source_id = result[0]
                else:
                    cursor.execute("INSERT INTO news_sources (name) VALUES (?)", ('Yahoo Finance',))
                    source_id = cursor.lastrowid
                
                # Check if article exists
                cursor.execute("SELECT id FROM news_articles WHERE url = ?", (url,))
                existing = cursor.fetchone()
                
                if existing:
                    article_id = existing[0]
                    # Update existing article
                    cursor.execute("""
                        UPDATE news_articles SET
                            title = ?, 
                            source_id = ?,
                            published_date = ?,
                            fetch_date = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (title, source_id, published_date, article_id))
                else:
                    # Insert new article
                    cursor.execute("""
                        INSERT INTO news_articles (
                            title, url, source_id, published_date, fetch_date
                        ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (title, url, source_id, published_date))
                    
                    article_id = cursor.lastrowid
                
                # Add default Finance category
                cursor.execute("SELECT id FROM news_categories WHERE name = ?", ('Finance',))
                result = cursor.fetchone()
                if result:
                    category_id = result[0]
                else:
                    cursor.execute("INSERT INTO news_categories (name) VALUES (?)", ('Finance',))
                    category_id = cursor.lastrowid
                    
                # Clear existing categories
                cursor.execute("DELETE FROM article_categories WHERE article_id = ?", (article_id,))
                
                # Add Finance category
                cursor.execute("""
                    INSERT INTO article_categories (article_id, category_id)
                    VALUES (?, ?)
                """, (article_id, category_id))
                
                yahoo_count += 1
            
            # Process Reuters articles
            for article in reuters_data:
                title = article.get('headline', '')
                url = article.get('url', '')
                published_date = article.get('publication_datetime', '')
                summary = article.get('description', '')
                image_url = article.get('image_url', '')
                image_alt = article.get('image_alt', '')
                
                if not url or not title:
                    continue
                    
                # Get source IDo
                    cursor.execute("INSERT INTO news_sources (name) VALUES (?)", ('Reuters',))
                    source_id = cursor.lastrowid
                
                # Check if article exists
                cursor.execute("SELECT id FROM news_articles WHERE url = ?", (url,))
                existing = cursor.fetchone()
                
                if existing:
                    article_id = existing[0]
                    # Update existing article
                    cursor.execute("""
                        UPDATE news_articles SET
                            title = ?, 
                            source_id = ?,
                            published_date = ?,
                            summary = ?,
                            image_url = ?,
                            image_alt = ?,
                            fetch_date = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (title, source_id, published_date, summary, image_url, image_alt, article_id))
                else:
                    # Insert new article
                    cursor.execute("""
                        INSERT INTO news_articles (
                            title, url, source_id, published_date, summary, image_url, image_alt, fetch_date
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (title, url, source_id, published_date, summary, image_url, image_alt))
                    
                    article_id = cursor.lastrowid
                
                # Process category if available
                if article.get('category'):
                    category_name = article.get('category')
                    
                    # Get category ID
                    cursor.execute("SELECT id FROM news_categories WHERE name = ?", (category_name,))
                    result = cursor.fetchone()
                    if result:
                        category_id = result[0]
                    else:
                        cursor.execute("INSERT INTO news_categories (name) VALUES (?)", (category_name,))
                        category_id = cursor.lastrowid
                    
                    # Clear existing categories
                    cursor.execute("DELETE FROM article_categories WHERE article_id = ?", (article_id,))
                    
                    # Add category
                    cursor.execute("""
                        INSERT INTO article_categories (article_id, category_id)
                        VALUES (?, ?)
                    """, (article_id, category_id))
                
                reuters_count += 1
        
        self.logger.info(f"Stored {yahoo_count} Yahoo Finance articles and {reuters_count} Reuters articles")
        
        return {
            "yahoo_finance": yahoo_count,
            "reuters": reuters_count,
            "total": yahoo_count + reuters_count
        }