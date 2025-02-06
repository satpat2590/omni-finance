import feedparser
import json
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent, FakeUserAgent
from urllib.parse import urljoin


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
         # Extract headline and link
            headline_tag = article.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            headline = headline_tag.get_text(strip=True) if headline_tag else "No headline"
            link_tag = headline_tag.find('a') if headline_tag else None
            article_url = link_tag.get('href') if link_tag else "No URL"  

            print(article, "\n\n")

    return articles


def scrape_reuters_news2():
    # Define the Reuters Business URL
    url = "https://www.reuters.com/business/"
    
    # Set up headers (using a random user agent for stealth)
    headers = {
        "User-Agent": UserAgent().random,
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/"
    }
    
    # Make the HTTP request
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch page, status code: {response.status_code}")
        return []

    # Parse the returned HTML content with BeautifulSoup
    soup = BeautifulSoup(response.content, "html.parser")
    # Locate the main content area
    main_content = soup.find("main")
    if not main_content:
        print("Could not find the <main> element in the HTML.")
        return []

    # Find all article cards by their data-testid attribute
    article_elements = main_content.find_all(attrs={"data-testid": "MediaStoryCard"})
    if not article_elements:
        print("No articles found on the page.")
        return []

    # Base URL used for converting relative links to absolute links
    base_url = "https://www.reuters.com"
    articles = []

    # Iterate over each article element and extract details
    for article in article_elements:
        # 1. Extract headline and URL:
        #    The headline is contained within one of the heading tags.
        headline_tag = article.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if headline_tag:
            print(headline_tag)
            headline = headline_tag.get_text(strip=True)
            # Often the headline has an <a> tag with the URL.
            link_tag = headline_tag.find("a")
        else:
            headline = None
            link_tag = article.find("a")
        
        # Extract the article URL and ensure it is absolute
        article_url = link_tag.get("href") if link_tag else None
        if article_url and article_url.startswith("/"):
            article_url = base_url + article_url

        # 2. Extract category:
        #    Look for a <span> with data-testid="Label" that contains an <a> element.
        category = None
        category_span = article.find("span", attrs={"data-testid": "Label"})
        if category_span:
            category_a = category_span.find("a")
            if category_a:
                category = category_a.get_text(strip=True)
                # Add code here to remove the 8 characters at end of word if it equals "category"

        # 3. Extract publication datetime:
        #    The <time> element holds the datetime attribute.
        publication_datetime = None
        time_tag = article.find("time")
        if time_tag and time_tag.has_attr("datetime"):
            publication_datetime = time_tag["datetime"]

        # 4. Extract description:
        #    The description text is often in a <p> tag.
        description = None
        description_tag = article.find("p")
        if description_tag:
            description = description_tag.get_text(strip=True)

        # 5. Extract image details:
        #    Look for the first <img> tag to get the image URL and alt text.
        image_url = None
        image_alt = None
        img_tag = article.find("img")
        if img_tag:
            image_url = img_tag.get("src")
            image_alt = img_tag.get("alt")
        
        # Create a dictionary for the article's extracted information
        article_data = {
            "headline": headline,
            "url": article_url,
            "category": category,
            "publication_datetime": publication_datetime,
            "description": description,
            "image_url": image_url,
            "image_alt": image_alt,
        }
        articles.append(article_data)

        # Print out the article's information (optional)
        print(article_data, "\n\n")

    return articles



# Run the code baby!!!
if __name__=="__main__":
    news = scrape_reuters_news2()
    print(f"Scraped {len(news)} articles.")

    news = fetch_yahoo_finance_rss()
    print(f"Fetched {len(news)} articles.")
