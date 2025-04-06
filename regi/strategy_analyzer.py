import os
import json
import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
import matplotlib.pyplot as plt
import yfinance as yf

# Import your existing modules
from regi.omnidb import OmniDB
from regi.news_scraper import RegiNewsScraper

class StrategyAnalyzer:
    """
    Analyzes financial data and provides investment strategy recommendations
    based on technical indicators, market trends, and portfolio composition.
    """
    
    def __init__(self, risk_tolerance='moderate'):
        """
        Initialize the strategy analyzer with a risk tolerance setting.
        
        Args:
            risk_tolerance: 'conservative', 'moderate', or 'aggressive'
        """
        self.risk_tolerance = risk_tolerance
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db = OmniDB()  # Database connection
        self.news_scraper = RegiNewsScraper()  # For sentiment analysis
        
        # Risk profiles define how to weight different factors
        self.risk_profiles = {
            'conservative': {
                'volatility_weight': 0.4,
                'trend_weight': 0.2,
                'fundamental_weight': 0.4,
                'max_allocation_single_asset': 0.1,  # 10%
                'max_crypto_allocation': 0.05,       # 5%
                'min_cash_reserve': 0.20,            # 20%
            },
            'moderate': {
                'volatility_weight': 0.3,
                'trend_weight': 0.3,
                'fundamental_weight': 0.4,
                'max_allocation_single_asset': 0.15, # 15%
                'max_crypto_allocation': 0.15,       # 15%
                'min_cash_reserve': 0.10,            # 10%
            },
            'aggressive': {
                'volatility_weight': 0.2,
                'trend_weight': 0.5,
                'fundamental_weight': 0.3,
                'max_allocation_single_asset': 0.25, # 25%
                'max_crypto_allocation': 0.30,       # 30%
                'min_cash_reserve': 0.05,            # 5%
            }
        }
    
    def set_risk_tolerance(self, risk_tolerance):
        """Change the risk tolerance setting."""
        if risk_tolerance not in self.risk_profiles:
            raise ValueError(f"Invalid risk tolerance: {risk_tolerance}. Choose from {list(self.risk_profiles.keys())}")
        self.risk_tolerance = risk_tolerance
        return self.risk_profiles[risk_tolerance]
        
    def get_stock_data(self, symbol: str, period: str = '1y') -> pd.DataFrame:
        """
        Retrieve historical stock data using yfinance.
        
        Args:
            symbol: Stock ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            
        Returns:
            DataFrame with historical stock data
        """
        try:
            stock = yf.Ticker(symbol)
            df = stock.history(period=period)
            return df
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators for a stock DataFrame.
        
        Args:
            df: DataFrame with stock data (must contain 'Close' column)
            
        Returns:
            DataFrame with added technical indicators
        """
        if df.empty or 'Close' not in df.columns:
            return df
        
        # Create a copy to avoid modifying the original
        df_indicators = df.copy()
        
        # Calculate moving averages
        df_indicators['MA50'] = df_indicators['Close'].rolling(window=50).mean()
        df_indicators['MA200'] = df_indicators['Close'].rolling(window=200).mean()
        
        # Calculate RSI (Relative Strength Index)
        delta = df_indicators['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        
        rs = gain / loss
        df_indicators['RSI'] = 100 - (100 / (1 + rs))
        
        # Calculate MACD (Moving Average Convergence Divergence)
        exp12 = df_indicators['Close'].ewm(span=12, adjust=False).mean()
        exp26 = df_indicators['Close'].ewm(span=26, adjust=False).mean()
        df_indicators['MACD'] = exp12 - exp26
        df_indicators['MACD_Signal'] = df_indicators['MACD'].ewm(span=9, adjust=False).mean()
        df_indicators['MACD_Hist'] = df_indicators['MACD'] - df_indicators['MACD_Signal']
        
        # Calculate Bollinger Bands
        df_indicators['MA20'] = df_indicators['Close'].rolling(window=20).mean()
        df_indicators['STD20'] = df_indicators['Close'].rolling(window=20).std()
        df_indicators['BB_Upper'] = df_indicators['MA20'] + (df_indicators['STD20'] * 2)
        df_indicators['BB_Lower'] = df_indicators['MA20'] - (df_indicators['STD20'] * 2)
        
        # Calculate volatility (standard deviation of returns)
        df_indicators['Returns'] = df_indicators['Close'].pct_change()
        df_indicators['Volatility'] = df_indicators['Returns'].rolling(window=21).std() * np.sqrt(252)  # Annualized
        
        return df_indicators
    
    def analyze_stock(self, symbol: str, period: str = '1y') -> Dict[str, Any]:
        """
        Perform comprehensive analysis of a stock.
        
        Args:
            symbol: Stock ticker symbol
            period: Time period for historical data
            
        Returns:
            Dictionary with analysis results
        """
        # Get stock data
        df = self.get_stock_data(symbol, period)
        if df.empty:
            return {"error": f"No data available for {symbol}"}
        
        # Calculate technical indicators
        df_indicators = self.calculate_technical_indicators(df)
        
        # Get the most recent data for analysis
        current = df_indicators.iloc[-1]
        prev = df_indicators.iloc[-2] if len(df_indicators) > 1 else current
        
        # Determine current trend
        if current['MA50'] > current['MA200']:
            trend = "bullish"
        elif current['MA50'] < current['MA200']:
            trend = "bearish"
        else:
            trend = "neutral"
        
        # Check for golden cross or death cross
        if prev['MA50'] <= prev['MA200'] and current['MA50'] > current['MA200']:
            cross = "golden cross (bullish)"
        elif prev['MA50'] >= prev['MA200'] and current['MA50'] < current['MA200']:
            cross = "death cross (bearish)"
        else:
            cross = "none"
        
        # RSI interpretation
        if current['RSI'] < 30:
            rsi_signal = "oversold (bullish)"
        elif current['RSI'] > 70:
            rsi_signal = "overbought (bearish)"
        else:
            rsi_signal = "neutral"
        
        # MACD interpretation
        if current['MACD'] > current['MACD_Signal']:
            macd_signal = "bullish"
        else:
            macd_signal = "bearish"
        
        # Bollinger Bands interpretation
        if current['Close'] > current['BB_Upper']:
            bb_signal = "overbought (bearish)"
        elif current['Close'] < current['BB_Lower']:
            bb_signal = "oversold (bullish)"
        else:
            bb_signal = "neutral"
        
        # Calculate performance metrics
        start_price = df['Close'].iloc[0] if not df.empty else None
        end_price = df['Close'].iloc[-1] if not df.empty else None
        
        if start_price is not None and end_price is not None:
            price_change = (end_price - start_price) / start_price * 100
        else:
            price_change = None
        
        # Get volatility
        volatility = current.get('Volatility', None)
        
        # Fetch company info
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            company_name = info.get('shortName', symbol)
            sector = info.get('sector', 'Unknown')
            industry = info.get('industry', 'Unknown')
            pe_ratio = info.get('trailingPE', None)
            pb_ratio = info.get('priceToBook', None)
            dividend_yield = info.get('dividendYield', None) * 100 if info.get('dividendYield') else None
        except:
            company_name = symbol
            sector = "Unknown"
            industry = "Unknown"
            pe_ratio = None
            pb_ratio = None
            dividend_yield = None
        
        # Generate analysis summary
        analysis = {
            "symbol": symbol,
            "company_name": company_name,
            "sector": sector,
            "industry": industry,
            "current_price": end_price,
            "performance": {
                "price_change_percent": price_change,
                "period": period
            },
            "technical_indicators": {
                "trend": trend,
                "cross": cross,
                "rsi": {
                    "value": current['RSI'] if 'RSI' in current else None,
                    "signal": rsi_signal
                },
                "macd": {
                    "value": current['MACD'] if 'MACD' in current else None,
                    "signal": macd_signal
                },
                "bollinger_bands": {
                    "upper": current['BB_Upper'] if 'BB_Upper' in current else None,
                    "lower": current['BB_Lower'] if 'BB_Lower' in current else None,
                    "signal": bb_signal
                },
                "volatility": volatility
            },
            "fundamental_indicators": {
                "pe_ratio": pe_ratio,
                "pb_ratio": pb_ratio,
                "dividend_yield": dividend_yield
            },
            "analysis_date": datetime.datetime.now().isoformat()
        }
        
        # Overall recommendation based on technical signals
        bullish_signals = 0
        bearish_signals = 0
        
        if trend == "bullish": bullish_signals += 1
        if trend == "bearish": bearish_signals += 1
        
        if "bullish" in cross: bullish_signals += 1
        if "bearish" in cross: bearish_signals += 1
        
        if "bullish" in rsi_signal: bullish_signals += 1
        if "bearish" in rsi_signal: bearish_signals += 1
        
        if macd_signal == "bullish": bullish_signals += 1
        if macd_signal == "bearish": bearish_signals += 1
        
        if "bullish" in bb_signal: bullish_signals += 1
        if "bearish" in bb_signal: bearish_signals += 1
        
        if bullish_signals > bearish_signals:
            analysis["recommendation"] = "BUY"
        elif bearish_signals > bullish_signals:
            analysis["recommendation"] = "SELL"
        else:
            analysis["recommendation"] = "HOLD"
        
        # Adjust recommendation based on risk tolerance
        if self.risk_tolerance == "conservative" and analysis["recommendation"] == "BUY" and (volatility or 0) > 0.25:
            analysis["recommendation"] = "HOLD"
            analysis["recommendation_note"] = "Downgraded to HOLD due to high volatility and conservative risk profile"
        
        return analysis
    
    def analyze_portfolio_allocation(self, portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze portfolio allocation and provide rebalancing recommendations.
        
        Args:
            portfolio: Portfolio data with stocks and crypto holdings
            
        Returns:
            Analysis results and recommendations
        """
        # Calculate current allocation
        total_value = portfolio.get('total_value', 0)
        if total_value <= 0:
            return {"error": "Invalid portfolio value"}
        
        # Get our risk profile
        profile = self.risk_profiles[self.risk_tolerance]
        
        # Calculate current allocations
        stocks_allocation = portfolio.get('stocks', {}).get('total_value', 0) / total_value
        crypto_allocation = portfolio.get('crypto', {}).get('total_value', 0) / total_value
        
        # Identify over-allocated assets
        over_allocated_stocks = []
        for symbol, data in portfolio.get('stocks', {}).get('holdings', {}).items():
            allocation = data.get('current_value', 0) / total_value
            if allocation > profile['max_allocation_single_asset']:
                over_allocated_stocks.append({
                    'symbol': symbol,
                    'current_allocation': allocation,
                    'max_allocation': profile['max_allocation_single_asset'],
                    'excess_value': (allocation - profile['max_allocation_single_asset']) * total_value
                })
        
        over_allocated_crypto = []
        for symbol, data in portfolio.get('crypto', {}).get('holdings', {}).items():
            allocation = data.get('current_value', 0) / total_value
            if allocation > profile['max_allocation_single_asset']:
                over_allocated_crypto.append({
                    'symbol': symbol,
                    'current_allocation': allocation,
                    'max_allocation': profile['max_allocation_single_asset'],
                    'excess_value': (allocation - profile['max_allocation_single_asset']) * total_value
                })
        
        # Create analysis and recommendations
        analysis = {
            "current_allocation": {
                "stocks": stocks_allocation,
                "crypto": crypto_allocation,
                "cash": 1 - stocks_allocation - crypto_allocation
            },
            "target_allocation": {
                "stocks_max": 1 - profile['min_cash_reserve'] - profile['max_crypto_allocation'],
                "crypto_max": profile['max_crypto_allocation'],
                "cash_min": profile['min_cash_reserve']
            },
            "rebalancing_needed": False,
            "recommendations": []
        }
        
        # Check if crypto allocation is too high
        if crypto_allocation > profile['max_crypto_allocation']:
            analysis["rebalancing_needed"] = True
            excess_crypto = (crypto_allocation - profile['max_crypto_allocation']) * total_value
            analysis["recommendations"].append({
                "action": "REDUCE",
                "asset_class": "crypto",
                "amount": excess_crypto,
                "reason": f"Crypto allocation ({crypto_allocation:.1%}) exceeds maximum ({profile['max_crypto_allocation']:.1%})"
            })
        
        # Check if cash reserves are too low
        cash_allocation = 1 - stocks_allocation - crypto_allocation
        if cash_allocation < profile['min_cash_reserve']:
            analysis["rebalancing_needed"] = True
            shortfall = (profile['min_cash_reserve'] - cash_allocation) * total_value
            analysis["recommendations"].append({
                "action": "INCREASE",
                "asset_class": "cash",
                "amount": shortfall,
                "reason": f"Cash reserves ({cash_allocation:.1%}) below minimum ({profile['min_cash_reserve']:.1%})"
            })
        
        # Add individual asset over-allocation recommendations
        for stock in over_allocated_stocks:
            analysis["rebalancing_needed"] = True
            analysis["recommendations"].append({
                "action": "REDUCE",
                "asset": stock['symbol'],
                "asset_class": "stock",
                "amount": stock['excess_value'],
                "reason": f"{stock['symbol']} allocation ({stock['current_allocation']:.1%}) exceeds maximum ({profile['max_allocation_single_asset']:.1%})"
            })
            
        for crypto in over_allocated_crypto:
            analysis["rebalancing_needed"] = True
            analysis["recommendations"].append({
                "action": "REDUCE",
                "asset": crypto['symbol'],
                "asset_class": "crypto",
                "amount": crypto['excess_value'],
                "reason": f"{crypto['symbol']} allocation ({crypto['current_allocation']:.1%}) exceeds maximum ({profile['max_allocation_single_asset']:.1%})"
            })
        
        return analysis
    
    def analyze_news_sentiment(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Analyze sentiment of recent news for specified symbols.
        
        Args:
            symbols: List of ticker symbols to analyze
            
        Returns:
            Sentiment analysis results
        """
        # Get news for the symbols
        yfinance_data, reuters_data = self.news_scraper.grab_news()
        
        # Simple keyword-based sentiment analysis
        # In a real implementation, you'd use a more sophisticated NLP approach
        positive_keywords = [
            'growth', 'profit', 'increase', 'rise', 'positive', 'beat', 'exceed',
            'up', 'gain', 'success', 'bullish', 'opportunity', 'strong'
        ]
        
        negative_keywords = [
            'decline', 'drop', 'fall', 'loss', 'negative', 'miss', 'below',
            'down', 'weak', 'bearish', 'risk', 'concern', 'warn', 'cut', 'reduce'
        ]
        
        results = {}
        for symbol in symbols:
            symbol_results = {
                'symbol': symbol,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'sentiment_score': 0,
                'sentiment': 'neutral',
                'top_news': []
            }
            
            # Check Yahoo Finance news
            for news in yfinance_data:
                if symbol.lower() in news['title'].lower():
                    # Calculate sentiment
                    positive_score = sum(1 for word in positive_keywords if word.lower() in news['title'].lower())
                    negative_score = sum(1 for word in negative_keywords if word.lower() in news['title'].lower())
                    
                    sentiment = 'neutral'
                    if positive_score > negative_score:
                        sentiment = 'positive'
                        symbol_results['positive_count'] += 1
                    elif negative_score > positive_score:
                        sentiment = 'negative'
                        symbol_results['negative_count'] += 1
                    else:
                        symbol_results['neutral_count'] += 1
                    
                    # Add to top news
                    symbol_results['top_news'].append({
                        'title': news['title'],
                        'source': 'Yahoo Finance',
                        'link': news['link'],
                        'sentiment': sentiment
                    })
            
            # Check Reuters news
            for news in reuters_data:
                if news['headline'] and symbol.lower() in news['headline'].lower():
                    # Calculate sentiment
                    positive_score = sum(1 for word in positive_keywords if word.lower() in news['headline'].lower())
                    negative_score = sum(1 for word in negative_keywords if word.lower() in news['headline'].lower())
                    
                    sentiment = 'neutral'
                    if positive_score > negative_score:
                        sentiment = 'positive'
                        symbol_results['positive_count'] += 1
                    elif negative_score > positive_score:
                        sentiment = 'negative'
                        symbol_results['negative_count'] += 1
                    else:
                        symbol_results['neutral_count'] += 1
                    
                    # Add to top news
                    symbol_results['top_news'].append({
                        'title': news['headline'],
                        'source': 'Reuters',
                        'link': news['url'],
                        'sentiment': sentiment
                    })
            
            # Calculate overall sentiment score
            total_news = (symbol_results['positive_count'] + symbol_results['negative_count'] + 
                         symbol_results['neutral_count'])
            
            if total_news > 0:
                symbol_results['sentiment_score'] = (symbol_results['positive_count'] - 
                                                   symbol_results['negative_count']) / total_news
                
                if symbol_results['sentiment_score'] > 0.2:
                    symbol_results['sentiment'] = 'positive'
                elif symbol_results['sentiment_score'] < -0.2:
                    symbol_results['sentiment'] = 'negative'
                else:
                    symbol_results['sentiment'] = 'neutral'
            
            # Limit top news to 5 items
            symbol_results['top_news'] = symbol_results['top_news'][:5]
            
            results[symbol] = symbol_results
        
        return results
    
    def generate_trading_signals(self, portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate trading signals for assets in the portfolio.
        
        Args:
            portfolio: Portfolio data
            
        Returns:
            Trading signals for portfolio assets
        """
        signals = {
            'stocks': {},
            'crypto': {},
            'recommendations': []
        }
        
        # Analyze all stocks in the portfolio
        for symbol in portfolio.get('stocks', {}).get('holdings', {}):
            analysis = self.analyze_stock(symbol)
            signals['stocks'][symbol] = {
                'signal': analysis.get('recommendation', 'HOLD'),
                'analysis': analysis
            }
            
            # Add to recommendations
            if analysis.get('recommendation') in ['BUY', 'SELL']:
                signals['recommendations'].append({
                    'action': analysis['recommendation'],
                    'symbol': symbol,
                    'asset_class': 'stock',
                    'current_price': analysis.get('current_price'),
                    'reason': f"Technical signals: {analysis.get('recommendation')} based on {analysis.get('technical_indicators', {}).get('trend', 'N/A')} trend"
                })
        
        # For crypto, we'll use the OmniDB analysis
        for symbol in portfolio.get('crypto', {}).get('holdings', {}):
            # Convert symbol to numeric ID if needed
            crypto_id = symbol  # This would require a mapping in a real implementation
            
            # Use existing analyze_crypto_bull_bear method
            analysis = self.db.analyze_crypto_bull_bear(crypto_id=crypto_id)
            
            if "Bullish" in analysis:
                signal = "BUY"
            elif "Bearish" in analysis:
                signal = "SELL"
            else:
                signal = "HOLD"
            
            signals['crypto'][symbol] = {
                'signal': signal,
                'analysis': analysis
            }
            
            # Add to recommendations if not HOLD
            if signal in ['BUY', 'SELL']:
                signals['recommendations'].append({
                    'action': signal,
                    'symbol': symbol,
                    'asset_class': 'crypto',
                    'reason': analysis
                })
        
        return signals
    
    def generate_investment_report(self, portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a comprehensive investment report with analysis and recommendations.
        
        Args:
            portfolio: Portfolio data
            
        Returns:
            Investment report with analysis and recommendations
        """
        # Analyze portfolio allocation
        allocation_analysis = self.analyze_portfolio_allocation(portfolio)
        
        # Get symbols from portfolio
        stock_symbols = list(portfolio.get('stocks', {}).get('holdings', {}).keys())
        crypto_symbols = list(portfolio.get('crypto', {}).get('holdings', {}).keys())
        
        # Analyze news sentiment
        sentiment_analysis = self.analyze_news_sentiment(stock_symbols + crypto_symbols)
        
        # Generate trading signals
        trading_signals = self.generate_trading_signals(portfolio)
        
        # Compile the report
        report = {
            'date': datetime.datetime.now().isoformat(),
            'risk_profile': self.risk_tolerance,
            'portfolio_value': portfolio.get('total_value', 0),
            'allocation_analysis': allocation_analysis,
            'sentiment_analysis': sentiment_analysis,
            'trading_signals': trading_signals,
            'recommendations': []
        }
        
        # Combine all recommendations
        if allocation_analysis.get('recommendations'):
            report['recommendations'].extend(allocation_analysis['recommendations'])
        
        if trading_signals.get('recommendations'):
            report['recommendations'].extend(trading_signals['recommendations'])
        
        # Add sentiment-based recommendations
        for symbol, sentiment_data in sentiment_analysis.items():
            if sentiment_data['sentiment'] == 'positive' and symbol in stock_symbols:
                # Check if we already have a BUY recommendation for this symbol
                existing_rec = False
                for rec in report['recommendations']:
                    if rec.get('symbol') == symbol and rec.get('action') == 'BUY':
                        existing_rec = True
                        break
                
                if not existing_rec:
                    report['recommendations'].append({
                        'action': 'WATCH_BUY',
                        'symbol': symbol,
                        'asset_class': 'stock' if symbol in stock_symbols else 'crypto',
                        'reason': f"Positive news sentiment: {sentiment_data['sentiment_score']:.2f}"
                    })
            
            elif sentiment_data['sentiment'] == 'negative' and symbol in stock_symbols:
                # Check if we already have a SELL recommendation for this symbol
                existing_rec = False
                for rec in report['recommendations']:
                    if rec.get('symbol') == symbol and rec.get('action') == 'SELL':
                        existing_rec = True
                        break
                
                if not existing_rec:
                    report['recommendations'].append({
                        'action': 'WATCH_SELL',
                        'symbol': symbol,
                        'asset_class': 'stock' if symbol in stock_symbols else 'crypto',
                        'reason': f"Negative news sentiment: {sentiment_data['sentiment_score']:.2f}"
                    })
        
        return report
    
    def save_report(self, report, filename=None):
        """Save the report to a file."""
        if filename is None:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"investment_report_{timestamp}.json"
            
        report_path = os.path.join(self.base_dir, f"data/{filename}")
        
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=4)
            
        return report_path

# Example usage
if __name__ == "__main__":
    analyzer = StrategyAnalyzer(risk_tolerance='moderate')
    
    # Example portfolio
    portfolio = {
        'stocks': {
            'total_value': 75000,
            'total_cost': 70000,
            'holdings': {
                'AAPL': {
                    'qty': 50,
                    'avg_cost': 150,
                    'current_value': 8000,
                    'total_cost': 7500
                },
                'MSFT': {
                    'qty': 30,
                    'avg_cost': 250,
                    'current_value': 9000,
                    'total_cost': 7500
                }
            }
        },
        'crypto': {
            'total_value': 15000,
            'total_cost': 12000,
            'holdings': {
                'BTC': {
                    'qty': 0.25,
                    'avg_cost': 40000,
                    'current_value': 12000,
                    'total_cost': 10000
                },
                'ETH': {
                    'qty': 2,
                    'avg_cost': 1000,
                    'current_value': 3000,
                    'total_cost': 2000
                }
            }
        },
        'total_value': 90000,
        'total_cost': 82000
    }
    
    # Analyze a single stock
    analysis = analyzer.analyze_stock('AAPL')
    print(f"AAPL Analysis: {analysis['recommendation']}")
    
    # Generate comprehensive report
    report = analyzer.generate_investment_report(portfolio)
    report_path = analyzer.save_report(report)
    
    print(f"Investment report saved to {report_path}")
    print(f"Recommendations: {len(report['recommendations'])}")
    for i, rec in enumerate(report['recommendations']):
        print(f"{i+1}. {rec['action']} {rec.get('symbol', rec.get('asset_class', ''))} - {rec['reason']}")