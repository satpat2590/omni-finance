#!/usr/bin/env python3
import os
import sys
import argparse
import json
import datetime
from pathlib import Path

# Add the project root to the path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)

# Import our modules
from regi.dashboard import FinancialDashboard
from regi.scheduler import FinancialScheduler
from regi.strategy_analyzer import StrategyAnalyzer
from regi.news_scraper import RegiNewsScraper
from regi.SEC import SEC
from regi.crypto import Crypto
from regi.omnidb import OmniDB

class RegiFinancialApp:
    """
    Main application class for REGI Financial Bot.
    Coordinates all components and provides a CLI interface.
    """
    
    def __init__(self):
        self.dashboard = FinancialDashboard()
        self.scheduler = FinancialScheduler()
        self.strategy_analyzer = StrategyAnalyzer()
        self.news_scraper = RegiNewsScraper()
        self.sec_analyzer = SEC()
        self.db = OmniDB()
        
        # Ensure data directory exists
        self.data_dir = os.path.join(root_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Ensure logs directory exists
        self.logs_dir = os.path.join(root_dir, "logs")
        os.makedirs(self.logs_dir, exist_ok=True)
        
        print(f"REGI Financial Bot initialized. Data dir: {self.data_dir}")
    
    def run_daily_report(self):
        """Generate and save a daily financial report"""
        print("Generating daily financial report...")
        report = self.dashboard.generate_daily_report()
        report_path = self.dashboard.save_report(report)
        print(f"Daily report saved to {report_path}")
        return report
    
    def run_investment_analysis(self, risk_profile=None):
        """Generate investment analysis and recommendations"""
        if risk_profile:
            self.strategy_analyzer.set_risk_tolerance(risk_profile)
        
        print(f"Generating investment analysis with {self.strategy_analyzer.risk_tolerance} risk profile...")
        
        # Get the current portfolio from the dashboard
        current_prices = {
            "AAPL": 155.0,  # This would be fetched from an API in real implementation
            "MSFT": 310.0,
            "BTC": 42000.0,
            "ETH": 2100.0
        }
        portfolio = self.dashboard.get_portfolio_value(current_prices)
        
        # Generate the investment report
        report = self.strategy_analyzer.generate_investment_report(portfolio)
        report_path = self.strategy_analyzer.save_report(report)
        
        print(f"Investment analysis saved to {report_path}")
        return report
    
    def fetch_news(self):
        """Fetch and save the latest financial news"""
        print("Fetching financial news...")
        yfinance_data, reuters_data = self.news_scraper.grab_news()
        
        # Save news to JSON files
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        yfinance_path = os.path.join(self.data_dir, f"yfinance_news_{timestamp}.json")
        with open(yfinance_path, 'w') as f:
            json.dump(yfinance_data, f, indent=4)
        
        reuters_path = os.path.join(self.data_dir, f"reuters_news_{timestamp}.json")
        with open(reuters_path, 'w') as f:
            json.dump(reuters_data, f, indent=4)
        
        print(f"Yahoo Finance news saved to {yfinance_path}")
        print(f"Reuters news saved to {reuters_path}")
        
        return {"yfinance": yfinance_data, "reuters": reuters_data}
    
    def analyze_crypto(self, crypto_symbols=None):
        """Analyze cryptocurrency data"""
        print("Analyzing cryptocurrency data...")
        
        # Here we would interface with the Crypto class to fetch latest data
        # For now, we'll use the OmniDB directly
        
        if crypto_symbols is None:
            crypto_symbols = ["BTC", "ETH"]  # Default to major cryptos
        
        results = {}
        for symbol in crypto_symbols:
            # Convert symbol to numeric ID if needed
            crypto_id = 1 if symbol == "BTC" else 2  # This is just an example mapping
            
            analysis = self.db.analyze_crypto_bull_bear(crypto_id=crypto_id)
            results[symbol] = analysis
        
        # Save results
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        results_path = os.path.join(self.data_dir, f"crypto_analysis_{timestamp}.json")
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=4)
        
        print(f"Crypto analysis saved to {results_path}")
        return results
    
    def analyze_sec_filings(self, tickers=None):
        """Analyze SEC filings for specified tickers"""
        print("Analyzing SEC filings...")
        
        if tickers is None:
            tickers = ["AAPL", "MSFT"]  # Default to major stocks
        
        # Convert tickers to CIK numbers
        cik_list = []
        for ticker in tickers:
            if ticker in self.sec_analyzer.cik_map:
                cik_list.append(self.sec_analyzer.cik_map[ticker])
                print(f"Found CIK for {ticker}: {self.sec_analyzer.cik_map[ticker]}")
            else:
                print(f"No CIK found for {ticker}")
        
        # Fetch and analyze filings
        self.sec_analyzer.fetch_sec_filings(cik_list)
        
        print(f"SEC filings analyzed for {len(cik_list)} companies")
        return {"analyzed_ciks": cik_list}
    
    def start_scheduler(self):
        """Start the automated scheduler"""
        print("Starting the financial scheduler...")
        self.scheduler.run()
    
    def run_once(self, task):
        """Run a specific task once"""
        if task == "daily_report":
            return self.run_daily_report()
        elif task == "investment_analysis":
            return self.run_investment_analysis()
        elif task == "news":
            return self.fetch_news()
        elif task == "crypto":
            return self.analyze_crypto()
        elif task == "sec":
            return self.analyze_sec_filings()
        else:
            print(f"Unknown task: {task}")
            return None
    
    def update_portfolio(self, action, asset_class, symbol, quantity, price):
        """Update the portfolio with a buy or sell transaction"""
        print(f"{action} {quantity} of {symbol} ({asset_class}) at ${price}")
        
        if asset_class.lower() == "stock":
            self.dashboard.update_stock_position(
                symbol, 
                float(quantity), 
                float(price), 
                is_buy=(action.lower() == "buy")
            )
        elif asset_class.lower() == "crypto":
            self.dashboard.update_crypto_position(
                symbol, 
                float(quantity), 
                float(price), 
                is_buy=(action.lower() == "buy")
            )
        else:
            print(f"Unknown asset class: {asset_class}")
            return False
            
        print(f"Portfolio updated successfully")
        return True
    
    def show_portfolio(self):
        """Display the current portfolio"""
        current_prices = {
            "AAPL": 155.0,  # This would be fetched from an API in real implementation
            "MSFT": 310.0,
            "BTC": 42000.0,
            "ETH": 2100.0
        }
        portfolio = self.dashboard.get_portfolio_value(current_prices)
        
        print("\n=== PORTFOLIO SUMMARY ===")
        print(f"Total Value: ${portfolio['total_value']:.2f}")
        print(f"Total Cost: ${portfolio['total_cost']:.2f}")
        print(f"Total P&L: ${portfolio['total_pnl']:.2f} ({(portfolio['total_pnl'] / portfolio['total_cost']) * 100:.2f}%)")
        
        print("\n--- STOCKS ---")
        print(f"Total Value: ${portfolio['stocks']['total_value']:.2f}")
        for symbol, data in portfolio['stocks']['holdings'].items():
            print(f"  {symbol}: {data['qty']} shares @ ${data['current_price']:.2f} = ${data['current_value']:.2f} " + 
                  f"(P&L: ${data['pnl']:.2f}, {data['pnl_percent']:.2f}%)")
        
        print("\n--- CRYPTO ---")
        print(f"Total Value: ${portfolio['crypto']['total_value']:.2f}")
        for symbol, data in portfolio['crypto']['holdings'].items():
            print(f"  {symbol}: {data['qty']} units @ ${data['current_price']:.2f} = ${data['current_value']:.2f} " + 
                  f"(P&L: ${data['pnl']:.2f}, {data['pnl_percent']:.2f}%)")
        
        return portfolio

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="REGI Financial Bot")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Daily report command
    daily_parser = subparsers.add_parser("daily", help="Generate daily financial report")
    
    # Investment analysis command
    invest_parser = subparsers.add_parser("invest", help="Generate investment analysis")
    invest_parser.add_argument("--risk", choices=["conservative", "moderate", "aggressive"], 
                              default="moderate", help="Risk profile to use")
    
    # News command
    news_parser = subparsers.add_parser("news", help="Fetch financial news")
    
    # Crypto command
    crypto_parser = subparsers.add_parser("crypto", help="Analyze cryptocurrency")
    crypto_parser.add_argument("--symbols", nargs="+", help="Crypto symbols to analyze")
    
    # SEC command
    sec_parser = subparsers.add_parser("sec", help="Analyze SEC filings")
    sec_parser.add_argument("--tickers", nargs="+", help="Stock tickers to analyze")
    
    # Scheduler command
    scheduler_parser = subparsers.add_parser("scheduler", help="Start the automated scheduler")
    
    # Portfolio commands
    portfolio_parser = subparsers.add_parser("portfolio", help="Portfolio management")
    portfolio_subparsers = portfolio_parser.add_subparsers(dest="portfolio_command", help="Portfolio command")
    
    # Show portfolio
    show_parser = portfolio_subparsers.add_parser("show", help="Show current portfolio")
    
    # Buy command
    buy_parser = portfolio_subparsers.add_parser("buy", help="Record a buy transaction")
    buy_parser.add_argument("--type", choices=["stock", "crypto"], required=True, help="Asset type")
    buy_parser.add_argument("--symbol", required=True, help="Asset symbol")
    buy_parser.add_argument("--quantity", required=True, type=float, help="Quantity to buy")
    buy_parser.add_argument("--price", required=True, type=float, help="Price per unit")
    
    # Sell command
    sell_parser = portfolio_subparsers.add_parser("sell", help="Record a sell transaction")
    sell_parser.add_argument("--type", choices=["stock", "crypto"], required=True, help="Asset type")
    sell_parser.add_argument("--symbol", required=True, help="Asset symbol")
    sell_parser.add_argument("--quantity", required=True, type=float, help="Quantity to sell")
    sell_parser.add_argument("--price", required=True, type=float, help="Price per unit")
    
    return parser.parse_args()

def main():
    """Main entry point for the application"""
    args = parse_args()
    app = RegiFinancialApp()
    
    if args.command == "daily":
        app.run_daily_report()
    
    elif args.command == "invest":
        app.run_investment_analysis(args.risk)
    
    elif args.command == "news":
        app.fetch_news()
    
    elif args.command == "crypto":
        app.analyze_crypto(args.symbols)
    
    elif args.command == "sec":
        app.analyze_sec_filings(args.tickers)
    
    elif args.command == "scheduler":
        app.start_scheduler()
    
    elif args.command == "portfolio":
        if args.portfolio_command == "show":
            app.show_portfolio()
        
        elif args.portfolio_command == "buy":
            app.update_portfolio("buy", args.type, args.symbol, args.quantity, args.price)
        
        elif args.portfolio_command == "sell":
            app.update_portfolio("sell", args.type, args.symbol, args.quantity, args.price)
    
    else:
        print("Please specify a command. Use -h for help.")

if __name__ == "__main__":
    main()