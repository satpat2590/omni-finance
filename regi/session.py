import os, json 
from fake_useragent import UserAgent, FakeUserAgent
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import requests
import datetime
import time, random
import logging 
import logging.config

def get_logging_config() -> dict:
    jpath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config/loggingConfig.json")
    config_dict = None
    with open(jpath, 'r') as f:
        config_dict = json.load(f)

    return config_dict

class RequestSession():
    def __init__(self, headers=None):
        print(f"\n[REQUEST SESSION] - {datetime.datetime.now()} - Initializing the session now...")
     # Configuration
        if headers == None:
            headers = {
                    "User-Agent": UserAgent().random,
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://www.google.com/",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            }
        self.session = requests.Session()
        self.session.headers.update(headers)

     # Configure the logger
        logconfig = get_logging_config()
        logging.config.dictConfig(logconfig)
        
     # Instantiate the logger
        self.logger = logging.getLogger(__name__)
        self.logger.info("Logging has been configured using the JSON file.")


    def get(self, url: str|bytes, params=None) -> bytes:
        time.sleep(random.uniform(2, 5))

    # Make the HTTP request
        try:
            if params:
                response = self.session.get(url, params=params)
            else:
                response = self.session.get(url)

            if response.status_code != 200:
                print(f"Failed to fetch page, status code: {response.status_code}")
                return []
            
            return response
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            print(e)

