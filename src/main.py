import sys, os 

# Add modules from base repo
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from regi.news_scraper import RegiNewsScraper
from regi.crypto import Crypto 
from regi.SEC import SEC 




