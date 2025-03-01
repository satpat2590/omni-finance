import sqlite3
import os 
import datetime
from contextlib import contextmanager 

        

class OmniDB():

    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/omni.db")
        print(self.db_path)

    @contextmanager
    def sqlite_connect(self):
        """
            This is the main resource manager to use for all CRUD methods we create
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"[OMNI DB] - Error rolling back due to: {e}\n")
            raise e 
        finally:
            cursor.close()
            conn.close()




####### CRYPTO DATA API #######
    def insert_cryptos(self, cryptos):
            """Insert or ignore new cryptocurrencies."""
            query = """
            INSERT OR IGNORE INTO cryptocurrency (id, symbol, name, slug, first_historical_data, last_historical_data, status)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """
            with self.sqlite_connect() as cursor:
                cursor.executemany(query, cryptos)

    def insert_market_data(self, market_data):
        """Insert or update market data, ensuring no duplicate timestamps."""
        query = """
        INSERT INTO crypto_market_data 
        (crypto_id, timestamp, price_usd, market_cap_usd, volume_24h_usd, 
         percent_change_1h, percent_change_24h, percent_change_7d, 
         circulating_supply, total_supply, max_supply)
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

    def insert_metadata(self, metadata):
        """Insert or update cryptocurrency metadata."""
        query = """
        INSERT INTO crypto_metadata (crypto_id, logo_url, website_url, technical_doc, description, category)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(crypto_id) 
        DO UPDATE SET 
            category = excluded.category;
        """
        with self.sqlite_connect() as cursor:
            cursor.executemany(query, metadata)

    ## **🔹 READ Operations**
    
    def get_all_cryptos(self):
        """Retrieve all cryptocurrencies."""
        query = "SELECT * FROM cryptocurrency;"
        with self.sqlite_connect() as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    def get_market_data(self, crypto_id, start_date=None, end_date=None):
        """Retrieve market data for a given crypto_id and optional date range."""
        query = "SELECT * FROM crypto_market_data WHERE crypto_id = ?"
        params = [crypto_id]

        if start_date and end_date:
            query += " AND timestamp BETWEEN ? AND ?"
            params.extend([start_date, end_date])

        with self.sqlite_connect() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def get_latest_market_data(self, crypto_id):
        """Retrieve the latest market data for a given crypto_id."""
        query = """
        SELECT * FROM crypto_market_data 
        WHERE crypto_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 1;
        """
        with self.connect() as cursor:
            cursor.execute(query, (crypto_id,))
            return cursor.fetchone()

    ## **🔹 UPDATE Operations**
    
    def update_crypto_status(self, crypto_id, new_status):
        """Update the status of a cryptocurrency (active/inactive)."""
        query = "UPDATE cryptocurrency SET status = ? WHERE id = ?"
        with self.connect() as cursor:
            cursor.execute(query, (new_status, crypto_id))

    def update_market_data(self, crypto_id, timestamp, new_price):
        """Update market data for a specific timestamp."""
        query = """
        UPDATE crypto_market_data 
        SET price_usd = ? 
        WHERE crypto_id = ? AND timestamp = ?
        """
        with self.connect() as cursor:
            cursor.execute(query, (new_price, crypto_id, timestamp))

    ## **🔹 DELETE Operations**
    
    def delete_crypto(self, crypto_id):
        """Delete a cryptocurrency and its related market data."""
        query_crypto = "DELETE FROM cryptocurrency WHERE id = ?"
        query_market = "DELETE FROM crypto_market_data WHERE crypto_id = ?"
        
        with self.connect() as cursor:
            cursor.execute(query_market, (crypto_id,))
            cursor.execute(query_crypto, (crypto_id,))

    def delete_old_market_data(self, cutoff_date):
        """Delete market data older than a specific date."""
        query = "DELETE FROM crypto_market_data WHERE timestamp < ?"
        with self.connect() as cursor:
            cursor.execute(query, (cutoff_date,))

    


