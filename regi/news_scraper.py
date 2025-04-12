import feedparser
import datetime
import json
from pathlib import Path
import os, sys
from bs4 import BeautifulSoup
from fake_useragent import UserAgent, FakeUserAgent
from urllib.parse import urljoin
from typing import Dict
import logging
import logging.config

# Add modules from base repo
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from regi.session import RequestSession
from regi.omnidb import OmniDB


"""
    STANDALONE METHODS
"""

def get_logging_config() -> dict:
    jpath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config/loggingConfig.json")
    config_dict = None
    with open(jpath, 'r') as f:
        config_dict = json.load(f)

    return config_dict


def save_json(spath: str, data: Dict, logger) -> None:
    """
        Save the data in some JSON file specified by spath

    :param spath: The path to the json file in which the data will be stored
    :param data: The json data to store into a file
    """
    logger.info(f"Saving data in {spath}...")
    with open(spath, 'w+') as f:
        json.dump(data, f)

    
def request_to_reuters(session: RequestSession) -> bytes:
    """
        Make a call to the reuters business site and pull the full HTML response
    """
 # Define the Reuters Business URL
    url = "https://www.reuters.com/business/" 
    
    return session.get(url)

def fetch_yahoo_finance_rss(logger) -> list:
    """
        Pull all of the feeds from Yahoo Finance RSS
    """
    url = "https://finance.yahoo.com/news/rss"
    feed = feedparser.parse(url)
    articles = []

    for entry in feed.entries:
        articles.append({
            "title": entry.title,
            "title_detail": entry.title_detail,
            "link": entry.link,
            "published": entry.published,
        })
    
    logger.info(f"There are {len(articles)} articles in the Yahoo Finance RSS feed")

    return articles

def pull_json(jpath: str) -> dict:
 # Open the path to the JSON file as a fp, and then return the data as a dict
    with open(jpath, 'r') as f:
        return json.load(f)

"""
    ANALYTICS ABSTRACTION
"""
class RegiNewsScraper():
    def __init__(self):
        print(f"\n[REGI] - {datetime.datetime.now()} - REGI (Finance Bot) is starting up...\n")

     # Configuration
        headers = {
            "User-Agent": UserAgent().random,
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }
        self.reqsesh = RequestSession()
        self.session = self.reqsesh.session
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.base_dir, "data")
        self.db = OmniDB()

     # Configure the logger
        logconfig = get_logging_config()
        logging.config.dictConfig(logconfig)
        
     # Instantiate the logger
        self.logger = logging.getLogger(__name__)


    def grab_news(self) -> 'tuple[Dict, Dict]':
        """
            This is the main method to pull all data and return as a tuple of dictionaries. 

        :return: A tuple of dictionaries containing Yahoo Finance and Reuters news data. 
        """
     # Make a request to https://www.reuters.com/business/ and instantiate a BeautifulSoup object with the content
        reuters_data = request_to_reuters(self.session)
        self.reuters_soup = None
        print(f"\nReuters data is of type: {type(reuters_data)}")
     # If the data was successfully retrieved, then open up the soup
        if reuters_data:
            self.reuters_soup = BeautifulSoup(reuters_data.content, features="html.parser")
        # Analyze the Reuters data
            reuters_data = self.analyze_reuters_data()
        else:
            self.logger.info(f"No data returned from Reuters...")
     
     # Analyze Yahoo Finance data
        yfinance_data = fetch_yahoo_finance_rss(logger=self.logger)

        spath_yfinance = os.path.join(self.data_dir, f"yfinance_{datetime.datetime.now().strftime('%Y%m%d')}_{datetime.datetime.now().strftime('%H%M%S')}.json")
        spath_reuters = os.path.join(self.data_dir, f"reuters_{datetime.datetime.now().strftime('%Y%m%d')}_{datetime.datetime.now().strftime('%H%M%S')}.json")

        if yfinance_data:
            save_json(spath=spath_yfinance, data=yfinance_data, logger=self.logger)
        if reuters_data:
            save_json(spath=spath_reuters, data=reuters_data, logger=self.logger)

     # Store it within the Omni DB
        self.db.store_articles_from_scraper(yfinance_data=yfinance_data, reuters_data=reuters_data)

        return yfinance_data, reuters_data

        
    def analyze_reuters_data(self) -> list:
        """
            Find all MediaStoryCard class divs from the HTML and then extract key elements to create structured news data
        """
     # Analyze the contents of the data
        # Locate the main content area
        main_content = self.reuters_soup.find("main")
        if not main_content:
            self.logger.info("Could not find the <main> element in the HTML")
            return []
        
     # Find all article cards by their data-testid attribute
        article_elements = main_content.find_all(attrs={"data-testid": "MediaStoryCard"})
        if not article_elements:
            self.logger.info("No articles found on the page")
            return []

     # Base URL used for converting relative links to absolute links
        articles = []

     # Iterate over each article element and extract details
        for article in article_elements:
            article_data = self.analyze_article(article)
            articles.append(article_data)

        self.logger.info(f"There are {len(articles)} in the Reuter's business page")
        return articles


    def analyze_article(self, article) -> Dict:
        """
            Take each MediaStoryCard div and then extract pertinent information from it.

            Currently, we store all of these in a dictionary:
                [heading, url, category, publication_date, description, image_url, image_alt]

        :param article: The HTML of the MediaStoryCard div which pertains to a single article
        :return: A dictionary containing all of the extracted information. 
        """

        base_url = "https://www.reuters.com"

     # 1. Extract image details:
     #    Look for the first <img> tag to get the image URL and alt text.
        image_url = None
        image_alt = None
        img_tag = article.find("img")
        if img_tag:
            image_url = img_tag.get("src")
            image_alt = img_tag.get("alt")

     # 2. Extract URL:
     #    The headline is contained within one of the heading tags.
        a_tags = article.find_all(attrs={"aria-hidden": "true"})
        url_tag = a_tags[0]
        url = url_tag.get("href")
    
     # Grab the heading for the article
        heading_element = article.find_all(attrs={"data-testid": "Heading"})
        if heading_element:
            heading = heading_element[0].get_text(strip=True)

     # Grab the link from the article
        link_element = article.find_all(attrs={"data-testid": "Link"})
        category = None
        if link_element:
            category_dirty = link_element[0].get_text(strip=True)
            if category_dirty.endswith("category"):
                category = category_dirty[:-len("category")]
                if len(category) == 0:
                    category = None

     # 3. Extract publication datetime:
     #    The <time> element holds the datetime attribute.
        publication_datetime = None
        time_tag = article.find("time")
        if time_tag and time_tag.has_attr("datetime"):
            publication_datetime = time_tag["datetime"]
        
        #print((heading, category, publication_datetime, image_url, image_alt), "\n")

     # 4. Use the article link to summary the article itself
        article_url = None
        article_summary = None
        if url:
            article_url = base_url + url
            article_summary = self.fetch_article_summary(article_url)

        article_data = {
            "headline": heading,
            "url": article_url,
            "category": category,
            "publication_datetime": publication_datetime,
            "description": article_summary,
            "image_url": image_url,
            "image_alt": image_alt,
        }

        return article_data            
         
    def fetch_article_summary(self, url: str) -> str:
            """
                Given an article URL, make a request to the article page and extract a rough summary.
                This implementation first attempts to extract the content of a meta description, and if not found,
                it falls back to the first paragraph text.

            :param url: The url to the article which you are attempting to scrape from
            :return: A string containing a summary of the article
            """
            try:
                response = self.reqsesh.get(url)
            except Exception as e:
                print(f"Error fetching article {url}: {e}")
                return ""
            
            if response.status_code != 200:
                print(f"Failed to fetch article at {url}, status code: {response.status_code}")
                return ""

            article_soup = BeautifulSoup(response.content, "html.parser")

            # Attempt 1: Look for a meta description
            meta_desc = article_soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                return meta_desc.get("content").strip()

            # Attempt 2: Fallback to the first paragraph text
            first_paragraph = article_soup.find("p")
            if first_paragraph:
                return first_paragraph.get_text(strip=True)

            return ""
    
if __name__=="__main__":
    reginews = RegiNewsScraper()
    reginews.grab_news()

