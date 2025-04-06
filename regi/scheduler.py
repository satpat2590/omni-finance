import schedule
import time
import os
import json
import datetime
import logging
from pathlib import Path
import sys

# Add the project root to the Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from regi.dashboard import FinancialDashboard
from regi.session import get_logging_config

def setup_logging():
    """Configure logging for the scheduler"""
    logconfig = get_logging_config()
    logging.config.dictConfig(logconfig)
    return logging.getLogger(__name__)

class FinancialScheduler:
    """
    Scheduler for running financial analyses at predetermined times.
    Uses the 'schedule' package to manage recurring tasks.
    """
    
    def __init__(self):
        self.logger = setup_logging()
        self.dashboard = FinancialDashboard()
        self.scheduled_jobs = []
        self.running = False
        
        # Load configuration if it exists
        self.config_path = os.path.join(root_dir, "config/scheduler_config.json")
        self.config = self._load_config()
        
        self.logger.info("Financial Scheduler initialized")
    
    def _load_config(self):
        """Load scheduler configuration from JSON file"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading scheduler config: {e}")
                return self._get_default_config()
        else:
            self.logger.info("No scheduler config found, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self):
        """Return default configuration for the scheduler"""
        return {
            "daily_report": {
                "enabled": True,
                "time": "17:00",  # 5 PM local time
                "email": False
            },
            "crypto_analysis": {
                "enabled": True,
                "frequency": "6h"  # Every 6 hours
            },
            "news_scraping": {
                "enabled": True,
                "frequency": "4h"  # Every 4 hours
            },
            "sec_analysis": {
                "enabled": True,
                "day": "Monday",  # Weekly on Monday
                "time": "09:00"   # 9 AM local time
            }
        }
    
    def save_config(self):
        """Save the current configuration to a JSON file"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)
        self.logger.info("Scheduler configuration saved")
    
    def _run_daily_report(self):
        """Generate and save the daily financial report"""
        try:
            self.logger.info("Generating daily financial report")
            report = self.dashboard.generate_daily_report(
                email_report=self.config["daily_report"]["email"]
            )
            report_path = self.dashboard.save_report(report)
            self.logger.info(f"Daily report saved to {report_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error generating daily report: {e}")
            return False
    
    def _run_crypto_analysis(self):
        """Run cryptocurrency analysis"""
        try:
            self.logger.info("Running cryptocurrency analysis")
            insights = self.dashboard.get_crypto_insights()
            
            # Save insights to a file
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            insights_path = os.path.join(root_dir, f"data/crypto_insights_{timestamp}.json")
            
            with open(insights_path, 'w') as f:
                json.dump(insights, f, indent=4)
                
            self.logger.info(f"Crypto insights saved to {insights_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error running crypto analysis: {e}")
            return False
    
    def _run_news_scraping(self):
        """Scrape financial news"""
        try:
            self.logger.info("Scraping financial news")
            news = self.dashboard.fetch_latest_news()
            
            # Save news to a file
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            news_path = os.path.join(root_dir, f"data/financial_news_{timestamp}.json")
            
            with open(news_path, 'w') as f:
                json.dump(news, f, indent=4)
                
            self.logger.info(f"Financial news saved to {news_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error scraping news: {e}")
            return False
    
    def _run_sec_analysis(self):
        """Analyze SEC filings"""
        try:
            self.logger.info("Analyzing SEC filings")
            analysis = self.dashboard.analyze_sec_filings()
            
            # Save analysis to a file
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            sec_path = os.path.join(root_dir, f"data/sec_analysis_{timestamp}.json")
            
            with open(sec_path, 'w') as f:
                json.dump(analysis, f, indent=4)
                
            self.logger.info(f"SEC analysis saved to {sec_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error analyzing SEC filings: {e}")
            return False
    
    def _parse_frequency(self, freq_str):
        """Parse a frequency string like '4h' or '30m' into seconds"""
        unit = freq_str[-1]
        value = int(freq_str[:-1])
        
        if unit == 'm':
            return value * 60
        elif unit == 'h':
            return value * 60 * 60
        elif unit == 'd':
            return value * 24 * 60 * 60
        else:
            raise ValueError(f"Unknown time unit: {unit}")
    
    def schedule_jobs(self):
        """Set up all scheduled jobs based on configuration"""
        schedule.clear()
        
        # Schedule daily report
        if self.config["daily_report"]["enabled"]:
            schedule.every().day.at(self.config["daily_report"]["time"]).do(self._run_daily_report)
            self.logger.info(f"Scheduled daily report at {self.config['daily_report']['time']}")
        
        # Schedule crypto analysis
        if self.config["crypto_analysis"]["enabled"]:
            freq = self.config["crypto_analysis"]["frequency"]
            seconds = self._parse_frequency(freq)
            schedule.every(seconds).seconds.do(self._run_crypto_analysis)
            self.logger.info(f"Scheduled crypto analysis every {freq}")
        
        # Schedule news scraping
        if self.config["news_scraping"]["enabled"]:
            freq = self.config["news_scraping"]["frequency"]
            seconds = self._parse_frequency(freq)
            schedule.every(seconds).seconds.do(self._run_news_scraping)
            self.logger.info(f"Scheduled news scraping every {freq}")
        
        # Schedule SEC analysis
        if self.config["sec_analysis"]["enabled"]:
            day = self.config["sec_analysis"]["day"]
            time = self.config["sec_analysis"]["time"]
            
            if day.lower() == "monday":
                schedule.every().monday.at(time).do(self._run_sec_analysis)
            elif day.lower() == "tuesday":
                schedule.every().tuesday.at(time).do(self._run_sec_analysis)
            elif day.lower() == "wednesday":
                schedule.every().wednesday.at(time).do(self._run_sec_analysis)
            elif day.lower() == "thursday":
                schedule.every().thursday.at(time).do(self._run_sec_analysis)
            elif day.lower() == "friday":
                schedule.every().friday.at(time).do(self._run_sec_analysis)
            
            self.logger.info(f"Scheduled SEC analysis every {day} at {time}")
    
    def run(self):
        """Run the scheduler in a loop"""
        self.schedule_jobs()
        self.running = True
        
        self.logger.info("Financial Scheduler running. Press Ctrl+C to stop.")
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Scheduler stopped by user")
            self.running = False
    
    def run_once(self, job_name):
        """Run a specific job once, bypassing the schedule"""
        if job_name == "daily_report":
            return self._run_daily_report()
        elif job_name == "crypto_analysis":
            return self._run_crypto_analysis()
        elif job_name == "news_scraping":
            return self._run_news_scraping()
        elif job_name == "sec_analysis":
            return self._run_sec_analysis()
        else:
            self.logger.error(f"Unknown job name: {job_name}")
            return False
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        self.logger.info("Scheduler stopped")

if __name__ == "__main__":
    scheduler = FinancialScheduler()
    
    # Process command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--run-once" and len(sys.argv) > 2:
            job_name = sys.argv[2]
            print(f"Running {job_name} once...")
            scheduler.run_once(job_name)
        else:
            print("Unknown command line arguments")
            print("Usage: python scheduler.py")
            print("       python scheduler.py --run-once [job_name]")
            sys.exit(1)
    else:
        # Start the scheduler
        scheduler.run()
