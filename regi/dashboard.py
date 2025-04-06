import os
import json
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Any, Optional
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Import your existing modules
from regi.crypto import Crypto
from regi.news_scraper import RegiNewsScraper
from regi.SEC import SEC
from regi.omnidb import OmniDB

class FinancialDashboard:
    """
    A unified dashboard that consolidates data from various financial sources
    (stocks, crypto, SEC filings, news) and provides a comprehensive view.
    """
    
    def __init__(self):
        self.db = OmniDB()  # Reuse your existing database
        
        # Initialize data collectors
        self.news_scraper = RegiNewsScraper()
        self.sec_analyzer = SEC()
        
        # Portfolio tracking
        self.portfolio = {
            'stocks': {},  # symbol -> {qty, avg_cost}
            'crypto': {}   # symbol -> {qty, avg_cost}
        }
        
        # Load portfolio if it exists
        self._load_portfolio()
        
    def _load_portfolio(self):
        """Load portfolio data from a JSON file if it exists."""
        portfolio_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/portfolio.json")
        if os.path.exists(portfolio_path):
            with open(portfolio_path, 'r') as f:
                self.portfolio = json.load(f)
    
    def save_portfolio(self):
        """Save the current portfolio to a JSON file."""
        portfolio_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/portfolio.json")
        with open(portfolio_path, 'w') as f:
            json.dump(self.portfolio, f, indent=4)
    
    def update_stock_position(self, symbol: str, qty: float, price: float, is_buy: bool = True):
        """
        Update a stock position in the portfolio.
        
        Args:
            symbol: The stock ticker symbol
            qty: Quantity of shares
            price: Price per share
            is_buy: If True, this is a buy; if False, this is a sell
        """
        if symbol not in self.portfolio['stocks']:
            if not is_buy:
                raise ValueError(f"Cannot sell {symbol} as it's not in your portfolio")
            self.portfolio['stocks'][symbol] = {'qty': 0, 'avg_cost': 0, 'total_cost': 0}
        
        current = self.portfolio['stocks'][symbol]
        
        if is_buy:
            # Calculate new average cost
            new_total = current['total_cost'] + (qty * price)
            new_qty = current['qty'] + qty
            new_avg = new_total / new_qty if new_qty > 0 else 0
            
            self.portfolio['stocks'][symbol] = {
                'qty': new_qty,
                'avg_cost': new_avg,
                'total_cost': new_total
            }
        else:  # Selling
            if qty > current['qty']:
                raise ValueError(f"Cannot sell {qty} shares of {symbol}, you only have {current['qty']}")
            
            # Update quantity but keep the average cost the same
            new_qty = current['qty'] - qty
            new_total = current['avg_cost'] * new_qty
            
            if new_qty == 0:
                del self.portfolio['stocks'][symbol]
            else:
                self.portfolio['stocks'][symbol] = {
                    'qty': new_qty,
                    'avg_cost': current['avg_cost'],
                    'total_cost': new_total
                }
        
        self.save_portfolio()
    
    def update_crypto_position(self, symbol: str, qty: float, price: float, is_buy: bool = True):
        """
        Update a cryptocurrency position in the portfolio.
        
        Args:
            symbol: The crypto symbol
            qty: Quantity of coins/tokens
            price: Price per coin/token
            is_buy: If True, this is a buy; if False, this is a sell
        """
        if symbol not in self.portfolio['crypto']:
            if not is_buy:
                raise ValueError(f"Cannot sell {symbol} as it's not in your portfolio")
            self.portfolio['crypto'][symbol] = {'qty': 0, 'avg_cost': 0, 'total_cost': 0}
        
        current = self.portfolio['crypto'][symbol]
        
        if is_buy:
            # Calculate new average cost
            new_total = current['total_cost'] + (qty * price)
            new_qty = current['qty'] + qty
            new_avg = new_total / new_qty if new_qty > 0 else 0
            
            self.portfolio['crypto'][symbol] = {
                'qty': new_qty,
                'avg_cost': new_avg,
                'total_cost': new_total
            }
        else:  # Selling
            if qty > current['qty']:
                raise ValueError(f"Cannot sell {qty} tokens of {symbol}, you only have {current['qty']}")
            
            # Update quantity but keep the average cost the same
            new_qty = current['qty'] - qty
            new_total = current['avg_cost'] * new_qty
            
            if new_qty == 0:
                del self.portfolio['crypto'][symbol]
            else:
                self.portfolio['crypto'][symbol] = {
                    'qty': new_qty,
                    'avg_cost': current['avg_cost'],
                    'total_cost': new_total
                }
        
        self.save_portfolio()
    
    def get_portfolio_value(self, current_prices: Dict[str, float] = None):
        """
        Calculate the current value of the portfolio.
        
        Args:
            current_prices: Dictionary mapping symbols to current prices
                           If None, prices will be fetched from APIs
        
        Returns:
            Dictionary with portfolio values
        """
        # Implement price fetching if current_prices is None
        # For now, we'll assume prices are provided
        
        if current_prices is None:
            # In a real implementation, you would fetch prices here
            current_prices = {}
        
        result = {
            'stocks': {
                'total_value': 0,
                'total_cost': 0,
                'pnl': 0,
                'holdings': {}
            },
            'crypto': {
                'total_value': 0,
                'total_cost': 0,
                'pnl': 0,
                'holdings': {}
            }
        }
        
        # Calculate stock values
        for symbol, data in self.portfolio['stocks'].items():
            price = current_prices.get(symbol, 0)
            current_value = data['qty'] * price
            pnl = current_value - data['total_cost']
            pnl_percent = (pnl / data['total_cost']) * 100 if data['total_cost'] > 0 else 0
            
            result['stocks']['holdings'][symbol] = {
                'qty': data['qty'],
                'avg_cost': data['avg_cost'],
                'current_price': price,
                'current_value': current_value,
                'pnl': pnl,
                'pnl_percent': pnl_percent
            }
            
            result['stocks']['total_value'] += current_value
            result['stocks']['total_cost'] += data['total_cost']
        
        result['stocks']['pnl'] = result['stocks']['total_value'] - result['stocks']['total_cost']
        
        # Calculate crypto values
        for symbol, data in self.portfolio['crypto'].items():
            price = current_prices.get(symbol, 0)
            current_value = data['qty'] * price
            pnl = current_value - data['total_cost']
            pnl_percent = (pnl / data['total_cost']) * 100 if data['total_cost'] > 0 else 0
            
            result['crypto']['holdings'][symbol] = {
                'qty': data['qty'],
                'avg_cost': data['avg_cost'],
                'current_price': price,
                'current_value': current_value,
                'pnl': pnl,
                'pnl_percent': pnl_percent
            }
            
            result['crypto']['total_value'] += current_value
            result['crypto']['total_cost'] += data['total_cost']
            
        result['crypto']['pnl'] = result['crypto']['total_value'] - result['crypto']['total_cost']
        
        # Overall portfolio stats
        result['total_value'] = result['stocks']['total_value'] + result['crypto']['total_value']
        result['total_cost'] = result['stocks']['total_cost'] + result['crypto']['total_cost']
        result['total_pnl'] = result['stocks']['pnl'] + result['crypto']['pnl']
        
        return result
    
    def generate_portfolio_report(self, output_format='json'):
        """Generate a report of the current portfolio in the specified format."""
        # Placeholder for implementation
        pass
    
    def visualize_portfolio(self):
        """Create data visualizations for the portfolio."""
        # Create a pie chart of portfolio allocation
        stock_value = sum(data['total_cost'] for data in self.portfolio['stocks'].values())
        crypto_value = sum(data['total_cost'] for data in self.portfolio['crypto'].values())
        
        fig = make_subplots(
            rows=2, cols=2,
            specs=[[{'type': 'domain'}, {'type': 'domain'}], [{'colspan': 2}, None]],
            subplot_titles=('Asset Allocation', 'Top Holdings', 'Portfolio Performance')
        )
        
        # Asset allocation pie chart
        labels = ['Stocks', 'Cryptocurrencies']
        values = [stock_value, crypto_value]
        
        fig.add_trace(
            go.Pie(labels=labels, values=values, name="Asset Allocation"),
            row=1, col=1
        )
        
        # Top holdings pie chart
        holdings = []
        for symbol, data in self.portfolio['stocks'].items():
            holdings.append({'symbol': symbol, 'value': data['total_cost'], 'type': 'Stock'})
            
        for symbol, data in self.portfolio['crypto'].items():
            holdings.append({'symbol': symbol, 'value': data['total_cost'], 'type': 'Crypto'})
            
        holdings.sort(key=lambda x: x['value'], reverse=True)
        top_holdings = holdings[:5]
        
        if len(holdings) > 5:
            others_value = sum(h['value'] for h in holdings[5:])
            top_holdings.append({'symbol': 'Others', 'value': others_value, 'type': 'Various'})
        
        fig.add_trace(
            go.Pie(
                labels=[h['symbol'] for h in top_holdings],
                values=[h['value'] for h in top_holdings],
                name="Top Holdings"
            ),
            row=1, col=2
        )
        
        # TODO: Add time-series performance chart in the bottom row
        
        fig.update_layout(
            title_text="Portfolio Overview",
            height=800,
            width=1000
        )
        
        return fig
    
    def fetch_latest_news(self, symbols=None):
        """
        Fetch the latest news relevant to the portfolio.
        
        Args:
            symbols: List of specific symbols to fetch news for.
                   If None, fetch news for all portfolio holdings.
        
        Returns:
            List of news items
        """
        if symbols is None:
            symbols = list(self.portfolio['stocks'].keys()) + list(self.portfolio['crypto'].keys())
        
        yfinance_data, reuters_data = self.news_scraper.grab_news()
        
        # Filter news for portfolio symbols
        # This is a simple implementation - you might want to use NLP for better matching
        filtered_news = []
        
        for news in yfinance_data:
            if any(symbol.lower() in news['title'].lower() for symbol in symbols):
                filtered_news.append({
                    'source': 'Yahoo Finance',
                    'title': news['title'],
                    'link': news['link'],
                    'published': news['published'],
                    'relevance': 'portfolio'
                })
        
        for news in reuters_data:
            if news['headline'] and any(symbol.lower() in news['headline'].lower() for symbol in symbols):
                filtered_news.append({
                    'source': 'Reuters',
                    'title': news['headline'],
                    'link': news['url'],
                    'published': news['publication_datetime'],
                    'relevance': 'portfolio'
                })
        
        return filtered_news
    
    def analyze_sec_filings(self, tickers=None):
        """
        Analyze SEC filings for portfolio stocks or specified tickers.
        
        Args:
            tickers: List of specific tickers to analyze.
                   If None, analyze filings for all portfolio stocks.
        
        Returns:
            Analysis results
        """
        if tickers is None:
            tickers = list(self.portfolio['stocks'].keys())
        
        # Convert tickers to CIK numbers using the mapping in SEC.py
        cik_list = []
        for ticker in tickers:
            if ticker in self.sec_analyzer.cik_map:
                cik_list.append(self.sec_analyzer.cik_map[ticker])
        
        # Fetch and analyze filings
        self.sec_analyzer.fetch_sec_filings(cik_list)
        
        # TODO: Implement analysis of the fetched data
        
        return {"status": "SEC analysis completed", "analyzed_ciks": cik_list}
    
    def get_crypto_insights(self, crypto_ids=None):
        """
        Get insights for cryptocurrencies in the portfolio.
        
        Args:
            crypto_ids: List of specific crypto IDs to analyze.
                      If None, analyze all portfolio cryptocurrencies.
        
        Returns:
            Crypto analysis results
        """
        if crypto_ids is None:
            crypto_ids = list(self.portfolio['crypto'].keys())
            
        results = {}
        for crypto_id in crypto_ids:
            # Convert symbol to numeric ID if needed
            numeric_id = crypto_id  # This would require a mapping in a real implementation
            
            # Use your existing OmniDB analyze_crypto_bull_bear method
            analysis = self.db.analyze_crypto_bull_bear(crypto_id=numeric_id)
            results[crypto_id] = analysis
            
        return results
    
    def generate_daily_report(self, email_report=False):
        """
        Generate a comprehensive daily report with portfolio status,
        market news, and actionable insights.
        
        Args:
            email_report: If True, send the report via email
            
        Returns:
            Report data dictionary
        """
        report = {
            'timestamp': datetime.datetime.now().isoformat(),
            'portfolio_summary': self.get_portfolio_value(),
            'news': self.fetch_latest_news(),
            'crypto_insights': self.get_crypto_insights(),
            # Add more sections as needed
        }
        
        if email_report:
            self._send_email_report(report)
            
        return report
    
    def _send_email_report(self, report):
        """Send the report via email. Implementation depends on your email service."""
        # Placeholder for email sending implementation
        pass
    
    def save_report(self, report, filename=None):
        """Save the report to a file."""
        if filename is None:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"financial_report_{timestamp}.json"
            
        report_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), f"data/{filename}")
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=4)
            
        return report_path

# Example usage
if __name__ == "__main__":
    dashboard = FinancialDashboard()
    
    # Example: Add some portfolio positions
    dashboard.update_stock_position("AAPL", 10, 150.0)
    dashboard.update_stock_position("MSFT", 5, 300.0)
    dashboard.update_crypto_position("BTC", 0.1, 40000.0)
    dashboard.update_crypto_position("ETH", 1.5, 2000.0)
    
    # Get portfolio summary
    portfolio = dashboard.get_portfolio_value({
        "AAPL": 155.0,
        "MSFT": 310.0,
        "BTC": 42000.0,
        "ETH": 2100.0
    })
    
    print(json.dumps(portfolio, indent=4))
    
    # Generate daily report
    report = dashboard.generate_daily_report()
    dashboard.save_report(report)
    
    print(f"Report saved to {os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data/')}")
