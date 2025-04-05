import sqlite3
import os
import datetime
from contextlib import contextmanager
import logging
import json
import logging.config
import pandas as pd 
import numpy as np

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
    def sqlite_connect(self):
        """
        Context manager providing a cursor to interact with the SQLite database.
        Automatically commits if successful, and rolls back on errors.
        """
        conn = sqlite3.connect(self.db_path)
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