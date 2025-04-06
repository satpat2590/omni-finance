# REGI the Financial Guru

Regi is going to be the financial bot which is going to utilize various techniques such as RAG for finding pertinent information to help with financial analysis. 

Additionally, the bot will be using CoA (Chain of Agents), where it will employ various LLM agents which will perform specialized tasks to assist in managing my financial life. 

Currently, the plan is to create an email feed delivered to me which will create news snippets which are digestible by me every morning. 
Over time, the plan will be to use the news information to make predictions on various stocks and cryptos, in which I will be investing in. 

Initially, Regi will perform paper trading so that I can gauge the accuracy in its trades. If Regi begins to make profit, then we will continue. 
If the accuracy is below a certain threshold (consistently losing money), then we will work on employing better tactics to align Regi as a financial guru. 

## Semantic Extracts of News

We scrape news from Reuters and the Yahoo Finance RSS feeds. Over time, we will find better ways to collect up to date information so that we can begin to track it historically, and make market predictions based on them. 

## LLM Configuration

We have not gone this far yet! We will likely be using a mix of DeepSeek 

## REGI Financial Guru Bot - Project Structure
====================================

```
regi/                               # Main package directory
│
├── __init__.py                     # Package initialization
├── session.py                      # HTTP session management (existing)
├── news_scraper.py                 # News scraping module (existing)
├── SEC.py                          # SEC filing analysis (existing)
├── crypto.py                       # Cryptocurrency analysis (existing)
├── omnidb.py                       # Database handling (existing)
│
├── dashboard.py                    # NEW: Financial dashboard (portfolio management)
├── scheduler.py                    # NEW: Automated task scheduler
├── strategy_analyzer.py            # NEW: Investment strategy analysis
│
├── data/                           # Data storage directory
│   ├── portfolio.json              # Portfolio data
│   ├── financial_report_*.json     # Generated reports
│   ├── crypto_insights_*.json      # Crypto analysis results
│   ├── sec_analysis_*.json         # SEC filing analysis
│   └── financial_news_*.json       # Scraped news data
│
├── logs/                           # Log files directory
│   └── app.log                     # Application logs
│
└── config/                         # Configuration files
    ├── loggingConfig.json          # Logging configuration (existing)
    ├── cik.json                    # CIK to ticker mapping (existing)
    └── scheduler_config.json       # NEW: Scheduler configuration
│
main.py                             # NEW: Main application entry point
README.md                           # Project documentation
```

## Module Descriptions

### Existing Modules

1. **session.py**: Manages HTTP sessions for web requests with features like request retries and user agent rotation.

2. **news_scraper.py**: Scrapes financial news from sources like Reuters and Yahoo Finance.

3. **SEC.py**: Extracts and analyzes SEC filings for publicly traded companies.

4. **crypto.py**: Interfaces with CoinMarketCap API to analyze cryptocurrency data.

5. **omnidb.py**: SQLite database manager for storing and analyzing financial data.

### New Modules

1. **dashboard.py**: Central dashboard for portfolio management, tracking investments, and generating reports.

2. **scheduler.py**: Automated scheduler for running tasks at predefined intervals (daily reports, data collection, analysis).

3. **strategy_analyzer.py**: Analyzes financial data to generate investment strategies and recommendations based on technical indicators, market trends, and risk profiles.

4. **main.py**: Main application entry point with CLI interface for managing all system functions.

## Data Flows

1. **Portfolio Management**:
   - User → main.py → dashboard.py → portfolio.json

2. **News Analysis**:
   - Scheduler → news_scraper.py → financial_news_*.json
   - financial_news_*.json → strategy_analyzer.py → investment recommendations

3. **Crypto Analysis**:
   - Scheduler → crypto.py → omnidb.py → crypto_insights_*.json
   - crypto_insights_*.json → dashboard.py → portfolio reports

4. **SEC Filing Analysis**:
   - Scheduler → SEC.py → sec_analysis_*.json
   - sec_analysis_*.json → strategy_analyzer.py → investment recommendations

5. **Daily Reports**:
   - Scheduler → dashboard.py (collects data from all sources) → financial_report_*.json

## System Capabilities

1. **Portfolio Tracking**:
   - Record buy/sell transactions for stocks and cryptocurrencies
   - Track performance, profit/loss, and allocation metrics
   - Visualize portfolio composition and performance over time

2. **Automated Analysis**:
   - Daily financial reports summarizing portfolio status and market news
   - Technical analysis of stocks using indicators like RSI, MACD, Bollinger Bands
   - Cryptocurrency trend analysis
   - SEC filing monitoring for corporate developments

3. **Investment Recommendations**:
   - Generate buy/sell/hold signals based on technical indicators
   - Portfolio rebalancing recommendations based on risk profile
   - Sentiment analysis from financial news
   - Long-term investment opportunity identification

4. **Scheduling**:
   - Configurable automated tasks (daily, hourly, weekly)
   - Data collection and analysis at optimal times
   - Notification system for important signals and events

## Usage Examples

1. **Generate Daily Report**:
   ```
   python main.py daily
   ```

2. **Analyze Investment Strategy**:
   ```
   python main.py invest --risk moderate
   ```

3. **Fetch Financial News**:
   ```
   python main.py news
   ```

4. **Record Stock Purchase**:
   ```
   python main.py portfolio buy --type stock --symbol AAPL --quantity 10 --price 150.0
   ```

5. **View Current Portfolio**:
   ```
   python main.py portfolio show
   ```

6. **Start Automated Scheduler**:
   ```
   python main.py scheduler
   ```

7. **Analyze Specific Cryptocurrencies**:
   ```
   python main.py crypto --symbols BTC ETH
   ```

8. **Analyze SEC Filings for Specific Companies**:
   ```
   python main.py sec --tickers AAPL MSFT
   ```
