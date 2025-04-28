import sys, os 

# Add modules from base repo
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from regi.news_scraper import RegiNewsScraper
from regi.crypto import Crypto 
from regi.SEC import SEC 
from regi.omnidb import OmniDB


if __name__=="__main__":
    rns = RegiNewsScraper()
    crypto = Crypto()
    db = OmniDB()
    #sec = SEC()

 # Run the news scraper
    yfinance_data, reuters_data = rns.grab_news()

 # Run the crypto data pull
    cryptos, market_data, metadata = crypto.fetch_crypto_data()
    crypto.insert_data_into_db(cryptos, market_data, metadata)

 # Calculate technical indicators
    db.analyze_all_bull_bear()

