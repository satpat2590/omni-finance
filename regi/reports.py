#!/usr/bin/env python3
"""
REGI Finance Bot - Report Generator

This module exports data from the OmniDB SQLite database to Excel/CSV files for analysis.
It provides comprehensive views of cryptocurrency data, news articles, and market trends.

Usage:
  python report_generator.py --type crypto --output crypto_report.xlsx
  python report_generator.py --type news --output news_report.xlsx
  python report_generator.py --type full --output finance_report.xlsx
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np
import datetime
import sqlite3
import logging
import logging.config
import json
from pathlib import Path

# Ensure we can import from the regi package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import REGI modules
from regi.omnidb import OmniDB, get_logging_config

# Set up logging
logconfig = get_logging_config()
logging.config.dictConfig(logconfig)
logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generate Excel/CSV reports from the OmniDB database"""
    
    def __init__(self, output_file=None):
        """
        Initialize the report generator
        
        :param output_file: Path to save the report file (defaults to timestamp-based name)
        """
        self.db = OmniDB()
        self.reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
        
        # Set default output path if none provided
        if output_file is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_file = None
        else:
            self.output_file = os.path.join(self.base_dir, output_file)
        
        # Ensure output directory exists
        os.makedirs(self.reports_dir, exist_ok=True)
            
    def generate_crypto_report(self, writer=None):
        """
        Generate cryptocurrency market data report
        
        :param writer: Excel writer object to add sheets to (creates new if None)
        :return: The Excel writer object
        """
        logger.info("Generating cryptocurrency report...")
        if not self.output_file:
            self.output_file = os.path.join(self.reports_dir, f"crypto_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx")
        
        # Create Excel writer if not provided
        close_writer = False
        if writer is None:
            writer = pd.ExcelWriter(self.output_file, engine='xlsxwriter')
            close_writer = True
        
        workbook = writer.book
        
        # Create formats for styling
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        percent_format = workbook.add_format({'num_format': '0.00%'})
        currency_format = workbook.add_format({'num_format': '$#,##0.00'})
        
        # 1. Top Cryptocurrencies by Market Cap
        try:
            query = """
                SELECT c.id, c.name, c.symbol, m.price_usd, m.market_cap_usd, m.volume_24h_usd,
                       m.percent_change_1h, m.percent_change_24h, m.percent_change_7d,
                       m.circulating_supply, m.total_supply, m.max_supply, m.timestamp
                FROM cryptocurrency c
                JOIN (
                    SELECT crypto_id, MAX(timestamp) as max_time
                    FROM crypto_market_data
                    GROUP BY crypto_id
                ) latest ON c.id = latest.crypto_id
                JOIN crypto_market_data m ON latest.crypto_id = m.crypto_id AND latest.max_time = m.timestamp
                ORDER BY m.market_cap_usd DESC
                LIMIT 100
            """
            conn = sqlite3.connect(self.db.db_path)
            top_cryptos = pd.read_sql(query, conn)
            
            # Write to Excel
            sheet_name = 'Top Cryptocurrencies'
            top_cryptos.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Format the sheet
            worksheet = writer.sheets[sheet_name]
            for idx, col in enumerate(top_cryptos.columns):
                # Set column width based on content
                max_len = max(top_cryptos[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(idx, idx, max_len)
            
            # Add headers
            for col_num, value in enumerate(top_cryptos.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Apply formatting to price and percentage columns
            for row_num in range(1, len(top_cryptos) + 1):
                worksheet.write_number(row_num, 3, top_cryptos.iloc[row_num-1]['price_usd'], currency_format)
                worksheet.write_number(row_num, 4, top_cryptos.iloc[row_num-1]['market_cap_usd'], currency_format)
                worksheet.write_number(row_num, 5, top_cryptos.iloc[row_num-1]['volume_24h_usd'], currency_format)
                
                # Format percentage columns
                for col_idx in [6, 7, 8]:  # percent_change columns
                    if not pd.isna(top_cryptos.iloc[row_num-1].iloc[col_idx]):
                        worksheet.write_number(
                            row_num, col_idx, 
                            float(top_cryptos.iloc[row_num-1].iloc[col_idx]) / 100,  # Convert to decimal for Excel percentage
                            percent_format
                        )
            
            logger.info(f"Added {len(top_cryptos)} cryptocurrencies to the report")
        except Exception as e:
            logger.error(f"Error generating top cryptocurrencies sheet: {str(e)}")
        
        # 2. Crypto Price History (for top 5 cryptos)
        try:
            top_5_symbols = top_cryptos.head(5)['symbol'].tolist()
            
            for symbol in top_5_symbols:
                try:
                    # Get crypto_id for the symbol
                    query = "SELECT id FROM cryptocurrency WHERE symbol = ?"
                    crypto_id = pd.read_sql(query, conn, params=(symbol,)).iloc[0]['id']
                    
                    # Get historical data
                    query = """
                        SELECT timestamp, price_usd, market_cap_usd, volume_24h_usd,
                               percent_change_24h, percent_change_7d
                        FROM crypto_market_data
                        WHERE crypto_id = ?
                        ORDER BY timestamp DESC
                        LIMIT 30
                    """
                    history_df = pd.read_sql(query, conn, params=(str(crypto_id),))
                    
                    if not history_df.empty:
                        # Convert timestamp to datetime
                        history_df['timestamp'] = pd.to_datetime(history_df['timestamp'])
                        
                        # Write to Excel
                        sheet_name = f'{symbol} History'
                        history_df.to_excel(writer, sheet_name=sheet_name, index=False)
                        
                        # Format the sheet
                        worksheet = writer.sheets[sheet_name]
                        for idx, col in enumerate(history_df.columns):
                            max_len = max(history_df[col].astype(str).map(len).max(), len(col)) + 2
                            worksheet.set_column(idx, idx, max_len)
                        
                        # Add headers
                        for col_num, value in enumerate(history_df.columns.values):
                            worksheet.write(0, col_num, value, header_format)
                        
                        # Apply formatting
                        for row_num in range(1, len(history_df) + 1):
                            worksheet.write_number(row_num, 1, history_df.iloc[row_num-1]['price_usd'], currency_format)
                            worksheet.write_number(row_num, 2, history_df.iloc[row_num-1]['market_cap_usd'], currency_format)
                            worksheet.write_number(row_num, 3, history_df.iloc[row_num-1]['volume_24h_usd'], currency_format)
                            
                            # Format percentage columns
                            for col_idx in [4, 5]:  # percent_change columns
                                if not pd.isna(history_df.iloc[row_num-1].iloc[col_idx]):
                                    worksheet.write_number(
                                        row_num, col_idx, 
                                        float(history_df.iloc[row_num-1].iloc[col_idx]) / 100,
                                        percent_format
                                    )
                        
                        logger.info(f"Added price history for {symbol}")
                    else:
                        logger.warning(f"No price history found for {symbol}")
                
                except Exception as e:
                    logger.error(f"Error processing history for {symbol}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error generating price history sheets: {str(e)}")
        
        # 3. Technical Indicators
        try:
            query = """
            SELECT c.symbol, 
                   s.timestamp, 
                   s.daily_return, 
                   s.ma_7d, 
                   s.std_7d, 
                   s.RSI, 
                   s.signal
            FROM crypto_signals s
            JOIN cryptocurrency c ON s.crypto_id = c.id
            ORDER BY c.symbol, s.timestamp DESC
            LIMIT 1000
            """
            
            indicators_df = pd.read_sql(query, conn)
            
            if not indicators_df.empty:
                # Write to Excel
                sheet_name = 'Technical Indicators'
                indicators_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Format the sheet
                worksheet = writer.sheets[sheet_name]
                for idx, col in enumerate(indicators_df.columns):
                    max_len = max(indicators_df[col].astype(str).map(len).max(), len(col)) + 2
                    worksheet.set_column(idx, idx, max_len)
                
                # Add headers
                for col_num, value in enumerate(indicators_df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                logger.info(f"Added technical indicators for {indicators_df['symbol'].nunique()} cryptocurrencies")
            else:
                logger.warning("No technical indicators found in the database")
        
        except Exception as e:
            logger.error(f"Error generating technical indicators sheet: {str(e)}")
        
        conn.close()
        
        # Close the writer if we created it
        if close_writer:
            writer.close()
            logger.info(f"Cryptocurrency report saved to {self.output_file}")
        
        return writer
    
    def generate_news_report(self, writer=None):
        """
        Generate news articles report
        
        :param writer: Excel writer object to add sheets to (creates new if None)
        :return: The Excel writer object
        """
        logger.info("Generating news report...")
        if not self.output_file:
            self.output_file = os.path.join(self.reports_dir, f"news_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx")

        # Create Excel writer if not provided
        close_writer = False
        if writer is None:
            writer = pd.ExcelWriter(self.output_file, engine='xlsxwriter')
            close_writer = True
        
        workbook = writer.book
        
        # Create header format
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        conn = sqlite3.connect(self.db.db_path)
        
        # 1. Recent News Articles
        try:
            query = """
                SELECT 
                    a.id, 
                    s.name AS source, 
                    a.title, 
                    a.url, 
                    a.published_date, 
                    a.summary,
                    a.fetch_date
                FROM 
                    news_articles a
                JOIN 
                    news_sources s ON a.source_id = s.id
                ORDER BY 
                    a.published_date DESC
                LIMIT 200
            """
            
            articles_df = pd.read_sql(query, conn)
            
            if not articles_df.empty:
                # Write to Excel
                sheet_name = 'Recent News'
                articles_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Format the sheet
                worksheet = writer.sheets[sheet_name]
                for idx, col in enumerate(articles_df.columns):
                    # Adjust column width based on content
                    if col in ['title', 'summary', 'url']:
                        worksheet.set_column(idx, idx, 50)  # Wider for text content
                    else:
                        max_len = max(articles_df[col].astype(str).map(len).max(), len(col)) + 2
                        worksheet.set_column(idx, idx, max_len)
                
                # Add headers
                for col_num, value in enumerate(articles_df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                logger.info(f"Added {len(articles_df)} recent news articles to the report")
            else:
                logger.warning("No news articles found in the database")
        
        except Exception as e:
            logger.error(f"Error generating recent news sheet: {str(e)}")
        
        # 2. News Categories
        try:
            query = """
                SELECT 
                    c.name AS category,
                    COUNT(ac.article_id) AS article_count
                FROM 
                    news_categories c
                JOIN 
                    article_categories ac ON c.id = ac.category_id
                GROUP BY 
                    c.name
                ORDER BY 
                    article_count DESC
            """
            
            categories_df = pd.read_sql(query, conn)
            
            if not categories_df.empty:
                # Write to Excel
                sheet_name = 'News Categories'
                categories_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Format the sheet
                worksheet = writer.sheets[sheet_name]
                for idx, col in enumerate(categories_df.columns):
                    max_len = max(categories_df[col].astype(str).map(len).max(), len(col)) + 2
                    worksheet.set_column(idx, idx, max_len)
                
                # Add headers
                for col_num, value in enumerate(categories_df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Add a pie chart
                chart = workbook.add_chart({'type': 'pie'})
                chart.add_series({
                    'name': 'News Categories',
                    'categories': [sheet_name, 1, 0, len(categories_df), 0],
                    'values': [sheet_name, 1, 1, len(categories_df), 1],
                })
                chart.set_title({'name': 'News Article Categories'})
                chart.set_style(10)
                worksheet.insert_chart('D2', chart, {'x_offset': 25, 'y_offset': 10, 'x_scale': 1.5, 'y_scale': 1.5})
                
                logger.info(f"Added {len(categories_df)} news categories to the report")
            else:
                logger.warning("No news categories found in the database")
        
        except Exception as e:
            logger.error(f"Error generating news categories sheet: {str(e)}")
        
        # 3. News Sources
        try:
            query = """
                SELECT 
                    s.name AS source,
                    COUNT(a.id) AS article_count
                FROM 
                    news_sources s
                JOIN 
                    news_articles a ON s.id = a.source_id
                GROUP BY 
                    s.name
                ORDER BY 
                    article_count DESC
            """
            
            sources_df = pd.read_sql(query, conn)
            
            if not sources_df.empty:
                # Write to Excel
                sheet_name = 'News Sources'
                sources_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Format the sheet
                worksheet = writer.sheets[sheet_name]
                for idx, col in enumerate(sources_df.columns):
                    max_len = max(sources_df[col].astype(str).map(len).max(), len(col)) + 2
                    worksheet.set_column(idx, idx, max_len)
                
                # Add headers
                for col_num, value in enumerate(sources_df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Add a bar chart
                chart = workbook.add_chart({'type': 'column'})
                chart.add_series({
                    'name': 'Article Count',
                    'categories': [sheet_name, 1, 0, len(sources_df), 0],
                    'values': [sheet_name, 1, 1, len(sources_df), 1],
                })
                chart.set_title({'name': 'Articles by Source'})
                chart.set_style(10)
                worksheet.insert_chart('D2', chart, {'x_offset': 25, 'y_offset': 10, 'x_scale': 1.5, 'y_scale': 1.5})
                
                logger.info(f"Added {len(sources_df)} news sources to the report")
            else:
                logger.warning("No news sources found in the database")
        
        except Exception as e:
            logger.error(f"Error generating news sources sheet: {str(e)}")
        
        # 4. News Timeline (articles per day)
        try:
            query = """
                SELECT 
                    DATE(published_date) AS date,
                    COUNT(id) AS article_count
                FROM 
                    news_articles
                WHERE
                    published_date IS NOT NULL
                GROUP BY 
                    DATE(published_date)
                ORDER BY 
                    date DESC
                LIMIT 60
            """
            
            timeline_df = pd.read_sql(query, conn)
            
            if not timeline_df.empty:
                # Sort chronologically for the chart
                timeline_df = timeline_df.sort_values('date')
                
                # Write to Excel
                sheet_name = 'News Timeline'
                timeline_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Format the sheet
                worksheet = writer.sheets[sheet_name]
                for idx, col in enumerate(timeline_df.columns):
                    max_len = max(timeline_df[col].astype(str).map(len).max(), len(col)) + 2
                    worksheet.set_column(idx, idx, max_len)
                
                # Add headers
                for col_num, value in enumerate(timeline_df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Add a line chart
                chart = workbook.add_chart({'type': 'line'})
                chart.add_series({
                    'name': 'Articles per Day',
                    'categories': [sheet_name, 1, 0, len(timeline_df), 0],
                    'values': [sheet_name, 1, 1, len(timeline_df), 1],
                    'marker': {'type': 'circle', 'size': 4},
                    'line': {'width': 2.25}
                })
                chart.set_title({'name': 'News Articles per Day'})
                chart.set_style(10)
                chart.set_legend({'position': 'none'})
                worksheet.insert_chart('D2', chart, {'x_offset': 25, 'y_offset': 10, 'x_scale': 2, 'y_scale': 1.5})
                
                logger.info(f"Added news timeline with {len(timeline_df)} days to the report")
            else:
                logger.warning("No timeline data could be generated")
        
        except Exception as e:
            logger.error(f"Error generating news timeline sheet: {str(e)}")
        
        conn.close()
        
        # Close the writer if we created it
        if close_writer:
            writer.close()
            logger.info(f"News report saved to {self.output_file}")
        
        return writer
    
    def generate_crypto_metrics_sheet(self, writer):
        """
        Generate a crypto metrics summary sheet with market indicators
        
        :param writer: Excel writer object
        """
        logger.info("Generating crypto metrics summary...")
        if not self.output_file:
            self.output_file = os.path.join(self.reports_dir, f"crypto_metrics_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx")

        workbook = writer.book
        
        # Create formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        bull_format = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
        bear_format = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
        neutral_format = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C5700'})
        
        # Get top cryptocurrencies
        conn = sqlite3.connect(self.db.db_path)
        
        try:
            query = """
                SELECT c.id, c.name, c.symbol, m.price_usd, m.market_cap_usd,
                       m.percent_change_24h, m.percent_change_7d
                FROM cryptocurrency c
                JOIN (
                    SELECT crypto_id, MAX(timestamp) as max_time
                    FROM crypto_market_data
                    GROUP BY crypto_id
                ) latest ON c.id = latest.crypto_id
                JOIN crypto_market_data m ON latest.crypto_id = m.crypto_id AND latest.max_time = m.timestamp
                ORDER BY m.market_cap_usd DESC
                LIMIT 20
            """
            
            top_cryptos = pd.read_sql(query, conn)
            
            # Get signals data
            metrics_data = []
            
            for _, crypto in top_cryptos.iterrows():
                crypto_id = crypto['id']
                symbol = crypto['symbol']
                name = crypto['name']
                price = crypto['price_usd']
                market_cap = crypto['market_cap_usd']
                change_24h = crypto['percent_change_24h']
                change_7d = crypto['percent_change_7d']
                
                # Get technical indicators
                indicators_query = """
                    SELECT daily_return, ma_7d, std_7d, RSI, signal
                    FROM crypto_signals
                    WHERE crypto_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """
                
                indicators = pd.read_sql(indicators_query, conn, params=(str(crypto_id),))
                
                if not indicators.empty:
                    daily_return = indicators.iloc[0]['daily_return']
                    ma_7d = indicators.iloc[0]['ma_7d']
                    std_7d = indicators.iloc[0]['std_7d']
                    rsi = indicators.iloc[0]['RSI']
                    signal = indicators.iloc[0]['signal']
                else:
                    daily_return = None
                    ma_7d = None
                    std_7d = None
                    rsi = None
                    signal = "No Signal"
                
                # Calculate volatility (if possible)
                if std_7d is not None and ma_7d is not None and ma_7d != 0:
                    volatility = (std_7d / ma_7d) * 100  # Coefficient of variation as percentage
                else:
                    volatility = None
                
                # Determine trend based on available indicators
                if signal == "Bullish Signal" or (change_24h is not None and change_24h > 5):
                    trend = "Bullish"
                elif signal == "Bearish Signal" or (change_24h is not None and change_24h < -5):
                    trend = "Bearish"
                else:
                    trend = "Neutral"
                
                metrics_data.append({
                    'Symbol': symbol,
                    'Name': name,
                    'Price': price,
                    'Market Cap': market_cap,
                    '24h Change': change_24h,
                    '7d Change': change_7d,
                    'Daily Return': daily_return,
                    'RSI': rsi,
                    'Volatility': volatility,
                    'Trend': trend
                })
            
            # Create DataFrame
            metrics_df = pd.DataFrame(metrics_data)
            
            # Create sheet
            sheet_name = 'Crypto Metrics'
            metrics_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Format the sheet
            worksheet = writer.sheets[sheet_name]
            
            # Set column widths
            worksheet.set_column('A:A', 8)    # Symbol
            worksheet.set_column('B:B', 20)   # Name
            worksheet.set_column('C:C', 15)   # Price
            worksheet.set_column('D:D', 20)   # Market Cap
            worksheet.set_column('E:F', 12)   # 24h/7d Change
            worksheet.set_column('G:G', 15)   # Daily Return
            worksheet.set_column('H:H', 10)   # RSI
            worksheet.set_column('I:I', 12)   # Volatility
            worksheet.set_column('J:J', 12)   # Trend
            
            # Add headers
            for col_num, value in enumerate(metrics_df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Apply conditional formatting
            for row_num in range(1, len(metrics_df) + 1):
                # Format the trend column
                trend = metrics_df.iloc[row_num-1]['Trend']
                if trend == 'Bullish':
                    worksheet.write(row_num, 9, trend, bull_format)
                elif trend == 'Bearish':
                    worksheet.write(row_num, 9, trend, bear_format)
                else:
                    worksheet.write(row_num, 9, trend, neutral_format)
            
            # Add conditional formatting for RSI
            worksheet.conditional_format(1, 7, len(metrics_df), 7, {
                'type': 'cell',
                'criteria': 'greater than',
                'value': 70,
                'format': bear_format
            })
            
            worksheet.conditional_format(1, 7, len(metrics_df), 7, {
                'type': 'cell',
                'criteria': 'less than',
                'value': 30,
                'format': bull_format
            })
            
            # Add conditional formatting for 24h Change
            worksheet.conditional_format(1, 4, len(metrics_df), 4, {
                'type': 'cell',
                'criteria': 'greater than',
                'value': 0,
                'format': bull_format
            })
            
            worksheet.conditional_format(1, 4, len(metrics_df), 4, {
                'type': 'cell',
                'criteria': 'less than',
                'value': 0,
                'format': bear_format
            })
            
            logger.info(f"Added crypto metrics summary for {len(metrics_df)} cryptocurrencies")
            
        except Exception as e:
            logger.error(f"Error generating crypto metrics sheet: {str(e)}")
        
        conn.close()
    
    def generate_full_report(self):
        """
        Generate a comprehensive report with all data
        """
        logger.info("Generating comprehensive finance report...")
        if not self.output_file:
            self.output_file = os.path.join(self.reports_dir, f"full_report_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx")

        # Create Excel writer
        writer = pd.ExcelWriter(self.output_file, engine='xlsxwriter')
        
        # Generate report components
        writer = self.generate_crypto_report(writer)
        writer = self.generate_news_report(writer)
        
        # Add a summary sheet with metrics
        self.generate_crypto_metrics_sheet(writer)
        
        # Close the writer
        writer.close()
        
        logger.info(f"Comprehensive finance report saved to {self.output_file}")
        
        return self.output_file

def main():
    """Main function to run the report generator"""
    parser = argparse.ArgumentParser(description='REGI Finance Bot Report Generator')
    parser.add_argument('-t', '--type', choices=['crypto', 'news', 'full'], default='full',
                        help='Type of report to generate')
    parser.add_argument('-o', '--output', default=None,
                        help='Output file path (default: reports/finance_report_TIMESTAMP.xlsx)')
    
    args = parser.parse_args()
    
    report_generator = ReportGenerator(output_file=args.output)
    
    if args.type == 'crypto':
        report_generator.generate_crypto_report()
    elif args.type == 'news':
        report_generator.generate_news_report()
    else:  # full
        report_generator.generate_full_report()
    
    print("\nReport generation complete!")

if __name__ == "__main__":
    main()