import os
import sys
import json
import datetime
import logging
import logging.config
import asyncio

# Use ccxt Pro (which you must install separately with `pip install ccxtpro`)
import ccxt # type: ignore

# Add modules from base repo
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from regi.session import RequestSession
from regi.omnidb import OmniDB 

def get_logging_config() -> dict:
    jpath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config/loggingConfig.json")
    config_dict = None
    with open(jpath, 'r') as f:
        config_dict = json.load(f)
    return config_dict

class Crypto:
    def __init__(self):
        """
        Initialize with environment-based API key, logging, and database references.
        """
        self.API_KEY = os.environ.get('COIN_MARKET_CAP_API', 'YOUR_API_KEY')
        self.headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': self.API_KEY,
        }
        self.latest_list_url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
        self.latest_list_params = {
            'start': '1',
            'limit': '5000',
            'convert': 'USD'
        }

        # Configure the logger
        logconfig = get_logging_config()
        logging.config.dictConfig(logconfig)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Logging has been configured using the JSON file.")
        
        # Custom library init
        self.reqsesh = RequestSession(headers=self.headers)
        self.db = OmniDB()

    def insert_data_into_db(self, cryptos=None, market_data=None, metadata=None):
        """
        Simple wrapper to send data to OmniDB (cryptos, market_data, metadata).
        """
        if cryptos:
            self.db.insert_cryptos(cryptos)
        if market_data:
            self.db.insert_market_data(market_data)
        if metadata:
            self.db.insert_metadata(metadata)

    def fetch_crypto_data(self) -> tuple:
        """
        Example method that hits CoinMarketCap's REST API for the latest listings.
        Returns a tuple of (cryptos, market_data, metadata).
        """
        response = self.reqsesh.get(self.latest_list_url)  # Byte response
        data = json.loads(response)

        cryptos = []
        market_data = []
        metadata = []
        
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        for coin in data.get("data", []):
            crypto_id = coin["id"]
            symbol = coin["symbol"]
            name = coin["name"]
            slug = coin["slug"]
            first_historical = coin["date_added"]
            last_updated = coin["last_updated"]
            status = "active"  # or custom logic

            cryptos.append((crypto_id, symbol, name, slug, first_historical, last_updated, status))
            
            quote = coin["quote"]["USD"]
            market_data.append((
                crypto_id,
                timestamp,
                quote["price"],
                quote["market_cap"],
                quote["volume_24h"],
                quote["percent_change_1h"],
                quote["percent_change_24h"],
                quote["percent_change_7d"],
                coin["circulating_supply"],
                coin["total_supply"],
                coin["max_supply"]
            ))

            # Use coin["tags"] as categories for metadata
            category = ", ".join(coin.get("tags", []))
            metadata.append((crypto_id, None, None, None, None, category))

        self.logger.info(f"{len(cryptos)} cryptocurrencies extracted from the REST API.")
        return cryptos, market_data, metadata

    ############################################
    # CCXT Pro: ASYNC METHODS (REST + WebSocket)
    ############################################

    async def fetch_binance_orderbook_rest(self, symbol="BTC/USDT", limit=10) -> dict:
        """
        Example of using ccxt Pro for a RESTful call, but in async mode.
        
        :param symbol: The trading pair, e.g. "BTC/USDT"
        :param limit: Depth of the order book
        :return: JSON/dict structure representing the order book
        """
        # ccxt Pro usage is asynchronous
        exchange = ccxt.binance()
        await exchange.load_markets()

        # This is actually a normal REST call (not WebSocket),
        # but using ccxt Pro’s asynchronous methods
        orderbook = await exchange.fetch_order_book(symbol, limit=limit)
        await exchange.close()

        self.logger.info(f"Fetched Binance order book for {symbol} with limit={limit}.")
        return orderbook

    async def stream_market_data_ws(self, symbol="BTC/USDT"):
        """
        Example: Subscribe to real-time ticker updates from Binance via WebSocket.
        This runs an infinite loop (until you break it externally).

        :param symbol: The trading pair, e.g. "BTC/USDT"
        """
        exchange = ccxt.binance()
        await exchange.load_markets()
        self.logger.info(f"Starting WebSocket stream for {symbol}...")

        try:
            while True:
                # watch_ticker is an asynchronous subscription method
                ticker = await exchange.fetch_ticker(symbol)
                # This ticker updates in real-time as data streams in
                self.logger.info(f"Live Ticker: {symbol} => {ticker['last']}, Volume: {ticker['baseVolume']}")
        except Exception as e:
            self.logger.error(f"Error in WebSocket stream: {e}")
        finally:
            # Properly close connection
            await exchange.close()
            self.logger.info("WebSocket connection closed.")

# ###############
# Example usage #
# ###############
if __name__ == "__main__":
    crypto = Crypto()

    # 1) Synchronous flow: fetch CMC data, insert into DB
    cryptos, market_data, metadata = crypto.fetch_crypto_data()
    crypto.insert_data_into_db(cryptos, market_data, metadata)

    # 2) Async ccxt Pro demonstration
    async def main():
        # REST: get an orderbook snapshot
        ob = await crypto.fetch_binance_orderbook_rest("BTC/USDT", limit=5)
        print(f"\nREST Orderbook: {ob}\n")

        # WebSocket: stream market data (this will keep running)
        # You can comment this out if you just want a one-off call
        await crypto.stream_market_data_ws("BTC/USDT")

    # Run the async code
    asyncio.run(main())
