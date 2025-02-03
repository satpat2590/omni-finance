import feedparser
import json
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent, FakeUserAgent


def fetch_yahoo_finance_rss():
    url = "https://finance.yahoo.com/news/rss"
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries:
        #print(json.dumps(entry.title_detail, indent=4), "\n")
        articles.append({
            "title": entry.title,
            "title_detail": entry.title_detail,
            "link": entry.link,
            "published": entry.published,
        })
    return articles


def scrape_reuters_news():
    url = "https://www.reuters.com/business/"
    headers = {
        "User-Agent": UserAgent().random,
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/" 
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    articles = []

    content = soup.find('main')
    articles = content.find_all(attrs={"data-testid": "MediaStoryCard"})

    if not articles:
        print(f"\n[HARVEY] - Unable to find articles from the <main> element in HTML.\n")
    else:
        for article in articles:
            print(article, "\n\n")
         # Extract headline and link
            headline_tag = article.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            headline = headline_tag.get_text(strip=True) if headline_tag else "No headline"
            link_tag = headline_tag.find('a') if headline_tag else None
            article_url = link_tag.get('href') if link_tag else "No URL"  

    return articles

news = scrape_reuters_news()
print(f"Scraped {len(news)} articles.")

news = fetch_yahoo_finance_rss()
print(f"Fetched {len(news)} articles.")
