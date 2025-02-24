import os
from fake_useragent import UserAgent, FakeUserAgent
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import requests
import datetime
import time, random

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
            
            return response.content
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            print(e)

