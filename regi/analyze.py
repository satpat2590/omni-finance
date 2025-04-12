#!/usr/bin/env python3
"""
REGI Finance Bot - Comprehensive Analysis Tool

This script performs a complete data collection and analysis run:
1. Collects fresh data from all sources
2. Runs technical analysis on cryptocurrency data
3. Analyzes news sentiment and correlations
4. Generates a summary report

Usage:
  python analyze_all.py --collect-data  # Collect new data and analyze
  python analyze_all.py                 # Only analyze existing data
"""

import os
import sys
import time
import argparse
import json
import logging
import datetime
import pandas as pd
import sqlite3
from pathlib import Path

# Ensure we can import from the regi package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import REGI modules
from regi.news_scraper import RegiNewsScraper, fetch_yahoo_finance_rss, request_to_reuters, save_json
from regi.SEC import SEC
from regi.crypto import Crypto
from regi.omnidb import OmniDB
from regi.session import RequestSession

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/analysis_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("REGI_Analysis")

# Make sure necessary directories exist
os.makedirs('logs', exist_ok=True)
os.makedirs('data', exist_ok=True)
os.makedirs('reports', exist_ok=True)

class FinanceAnalyzer:
    def __init__(self):
        self.db = OmniDB()
        self.report_data = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "crypto_analysis": {},
            "news_analysis": {},
            "sec_analysis": {},
            "correlations": {}
        }
    
    def collect_all_data(self):
        """Collect data from all sources"""
        logger.info("Starting comprehensive data collection...")
        
        # Collect news data
        try:
            logger.info("Collecting news data...")
            news_scraper = RegiNewsScraper()
            yahoo_data, reuters_data = news_scraper.grab_news()
            logger.info(f"Collected {len(yahoo_data)} Yahoo Finance articles and {len(reuters_data)} Reuters articles")
        except Exception as e:
            logger.error(f"Error collecting news data: {str(e)}")
        
        # Collect SEC data
        try:
            logger.info("Collecting SEC data...")
            sec = SEC()
            logger.info("SEC data collection completed")
        except Exception as e:
            logger.error(f"Error collecting SEC data: {str(e)}")
        
        # Collect crypto data
        try:
            logger.info("Collecting cryptocurrency data...")
            crypto = Crypto()
            cryptos, market_data, metadata = crypto.fetch_crypto_data()
            crypto.insert_data_into_db(cryptos, market_data, metadata)
            logger.info("Cryptocurrency data collection completed")
        except Exception as e:
            logger.error(f"Error collecting cryptocurrency data: {str(e)}")
        
        logger.info("All data collection completed")

    def analyze_crypto_trends(self):
        """Analyze cryptocurrency trends and generate insights"""
        logger.info("Analyzing cryptocurrency trends...")
        
        # Get all cryptocurrencies
        crypto_df = self.db.get_all_cryptos()
        if crypto_df.empty:
            logger.warning("No cryptocurrency data found in database")
            return
        
        # Sample of top cryptos by market cap
        try:
            conn = sqlite3.connect(self.db.db_path)
            top_cryptos_query = """
                SELECT c.id, c.name, c.symbol, m.price_usd, m.market_cap_usd, m.percent_change_24h
                FROM cryptocurrency c
                JOIN crypto_market_data m ON c.id = m.crypto_id
                WHERE m.timestamp = (
                    SELECT MAX(timestamp) FROM crypto_market_data
                )
                ORDER BY m.market_cap_usd DESC
                LIMIT 20
            """
            top_cryptos = pd.read_sql(top_cryptos_query, conn)
            conn.close()
            
            # Store in report data
            self.report_data["crypto_analysis"]["top_cryptos"] = top_cryptos.to_dict(orient='records')
            
            # Analyze top 10 cryptos
            bull_bear_signals = {}
            for _, crypto in top_cryptos.head(10).iterrows():
                crypto_id = crypto['id']
                signal = self.db.analyze_crypto_bull_bear(crypto_id=str(crypto_id))
                bull_bear_signals[crypto['symbol']] = signal
            
            self.report_data["crypto_analysis"]["signals"] = bull_bear_signals
            logger.info(f"Analyzed trends for top 10 cryptocurrencies")
            
            # Get volatility metrics
            volatility_data = {}
            for _, crypto in top_cryptos.head(5).iterrows():
                crypto_id = crypto['id']
                indicators_df = self.db.calculate_technical_indicators(crypto_id=str(crypto_id))
                if not indicators_df.empty and 'std_7d' in indicators_df.columns:
                    latest = indicators_df.iloc[-1]
                    volatility_data[crypto['symbol']] = {
                        "std_7d": float(latest['std_7d']) if not pd.isna(latest['std_7d']) else None,
                        "rsi": float(latest['RSI']) if not pd.isna(latest['RSI']) else None,
                        "price": float(latest['price_usd']) if 'price_usd' in indicators_df.columns else None
                    }
            
            self.report_data["crypto_analysis"]["volatility"] = volatility_data
            
        except Exception as e:
            logger.error(f"Error in crypto trend analysis: {str(e)}")

    def analyze_news_data(self):
        """Analyze news data and extract key trends"""
        logger.info("Analyzing news data...")
        
        try:
            # Find the most recent news files
            news_files = [f for f in os.listdir('data') if f.startswith('yfinance_') or f.startswith('reuters_')]
            if not news_files:
                logger.warning("No news data files found")
                return
            
            # Sort by creation time and get the newest
            news_files.sort(key=lambda x: os.path.getctime(os.path.join('data', x)), reverse=True)
            
            # Get the newest Yahoo Finance and Reuters files
            yfinance_file = next((f for f in news_files if f.startswith('yfinance_')), None)
            reuters_file = next((f for f in news_files if f.startswith('reuters_')), None)
            
            news_data = []
            
            # Process Yahoo Finance data
            if yfinance_file:
                with open(os.path.join('data', yfinance_file), 'r') as f:
                    yahoo_data = json.load(f)
                    for article in yahoo_data:
                        news_data.append({
                            "source": "Yahoo Finance",
                            "title": article.get("title", ""),
                            "date": article.get("published", ""),
                            "link": article.get("link", "")
                        })
            
            # Process Reuters data
            if reuters_file:
                with open(os.path.join('data', reuters_file), 'r') as f:
                    reuters_data = json.load(f)
                    for article in reuters_data:
                        news_data.append({
                            "source": "Reuters",
                            "title": article.get("headline", ""),
                            "date": article.get("publication_datetime", ""),
                            "link": article.get("url", ""),
                            "category": article.get("category", "")
                        })
            
            # Simple category analysis for Reuters articles
            if reuters_file:
                categories = {}
                for article in reuters_data:
                    cat = article.get("category")
                    if cat:
                        categories[cat] = categories.get(cat, 0) + 1
                
                self.report_data["news_analysis"]["reuters_categories"] = categories
            
            # Store the most recent articles
            self.report_data["news_analysis"]["recent_articles"] = news_data[:20]
            logger.info(f"Analyzed {len(news_data)} news articles")
            
        except Exception as e:
            logger.error(f"Error in news analysis: {str(e)}")

    def generate_report(self):
        """Generate a comprehensive analysis report"""
        logger.info("Generating analysis report...")
        
        report_path = os.path.join('reports', f'finance_analysis_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        
        # Add summary information
        self.report_data["summary"] = {
            "report_generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "crypto_analyzed": len(self.report_data["crypto_analysis"].get("signals", {})),
            "news_analyzed": len(self.report_data["news_analysis"].get("recent_articles", [])),
        }
        
        # Save the report
        with open(report_path, 'w') as f:
            json.dump(self.report_data, f, indent=2)
        
        logger.info(f"Analysis report saved to {report_path}")
        return report_path

def main():
    """Main function to run the analysis"""
    parser = argparse.ArgumentParser(description='REGI Finance Bot Comprehensive Analysis')
    parser.add_argument('-c', '--collect-data', action='store_true', help='Collect new data before analysis')
    
    args = parser.parse_args()
    
    analyzer = FinanceAnalyzer()
    
    if args.collect_data:
        analyzer.collect_all_data()
    
    # Run analysis
    analyzer.analyze_crypto_trends()
    analyzer.analyze_news_data()
    
    # Generate report
    report_path = analyzer.generate_report()
    print(f"\nAnalysis complete! Report saved to: {report_path}")

if __name__ == "__main__":
    main()
