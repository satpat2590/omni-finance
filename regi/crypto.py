from requests import Request, Session
import json
import os, sys, re
import datetime
from typing import Tuple
import logging
import logging.config

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

class Crypto():

    def __init__(self):
     # Configuration
        self.API_KEY = os.environ['COIN_MARKET_CAP_API']
        self.headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': self.API_KEY,
        }
        self.latest_list_url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
        self.latest_list_params = {
            'start':'1',
            'limit':'5000',
            'convert':'USD'
        }   
        
     # Configure the logger
        logconfig = get_logging_config()
        logging.config.dictConfig(logconfig)
        
     # Instantiate the logger
        self.logger = logging.getLogger(__name__)
        self.logger.info("Logging has been configured using the JSON file.")
        
     # Custom library init
        reqsesh = RequestSession(headers=self.headers)
        self.db = OmniDB()

        response = reqsesh.get(self.latest_list_url)

        ##
        ##  Market data is grouped as such: 
        ##                 crypto_id, timestamp, quote["price"], quote["market_cap"],
        ##        quote["volume_24h"], quote["percent_change_1h"], quote["percent_change_24h"],
        ##        quote["percent_change_7d"], coin["circulating_supply"], coin["total_supply"],
        ##        coin["max_supply"]
        ##

        cryptos, market_data, metadata = self.fetch_crypto_data(response)
        
        self.db.insert_cryptos(cryptos)
        self.db.insert_market_data(market_data)
        self.db.insert_metadata(metadata)
        res = self.db.analyze_crypto_bull_bear(crypto_id=1)
        print(res)

    def fetch_crypto_data(self, api_response: str) -> tuple:
        """
        Parses the CoinMarketCap API response and extracts cryptocurrency information.
        
        :param api_response: JSON string from CoinMarketCap API
        :return: Tuple containing (cryptos, market_data, metadata)
        """
        data = json.loads(api_response)
        
        cryptos = []
        market_data = []
        metadata = []
        
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")  # Current UTC timestamp
        
        for coin in data.get("data", []):
            crypto_id = coin["id"]
            symbol = coin["symbol"]
            name = coin["name"]
            slug = coin["slug"]
            first_historical = coin["date_added"]
            last_updated = coin["last_updated"]
            status = "active"  # Assume active, modify if needed

            cryptos.append((crypto_id, symbol, name, slug, first_historical, last_updated, status))
            
            # Market data
            quote = coin["quote"]["USD"]
            market_data.append((
                crypto_id, timestamp, quote["price"], quote["market_cap"],
                quote["volume_24h"], quote["percent_change_1h"], quote["percent_change_24h"],
                quote["percent_change_7d"], coin["circulating_supply"], coin["total_supply"],
                coin["max_supply"]
            ))

            # Metadata
            category = ", ".join(coin.get("tags", []))  # Convert list of tags to a string
            metadata.append((crypto_id, None, None, None, None, category))

        self.logger.info(f"{len(cryptos)} cryptocurrencies were extracted from the API response.")

        return cryptos, market_data, metadata

if __name__=="__main__":
    crypto = Crypto()


