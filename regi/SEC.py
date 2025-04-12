import json, csv, os, sys, re 
import datetime
from bs4 import BeautifulSoup
from fake_useragent import UserAgent, FakeUserAgent
import requests
from sec_cik_mapper import StockMapper 
from typing import Dict

# Add modules from base repo
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from regi.session import RequestSession


def save_json(spath: str, data: Dict) -> None:
    """
        Save the data in some JSON file specified by spath

    :param spath: The path to the json file in which the data will be stored
    :param data: The json data to store into a file
    """
    print(f"\n[OMNI] - {datetime.datetime.now()} - Saving data in {spath}...\n")
    with open(spath, 'w+') as f:
        json.dump(data, f)

class SEC():
    """
        This class will be used to scrape information from the SEC website for publically traded companies
    """

    def __init__(self):
        self.start = datetime.datetime.now()

     # Configuration
        self.reqsesh = RequestSession()
        self.url_template = "https://data.sec.gov/submissions/CIK##########.json"
        self.url_xbrl = "https://data.sec.gov/api/xbrl/companyconcept/CIK##########/us-gaap/AccountsPayableCurrent.json"
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.base_dir, "data")
        jpath = os.path.join(self.base_dir, "config/cik.json")
        self.cik_map = None
        with open(jpath, 'r') as f:
            self.cik_map = json.load(f)

        self.cik_list = [self.cik_map[ticker] for ticker in ['PLTR', 'BABA', 'VALE', 'WMT', 'SMCI']]
        print(f"Printing out the following tickers' CIK numbers: {self.cik_list}")
        for cik in self.cik_list:
            print(f"{cik}")
            gaap_record = self.fetch_accounts_payable(cik)
            if gaap_record:
                gaap_record_cleaned = gaap_record.content.decode('utf-8')
                print(gaap_record_cleaned)
            

        self.fetch_sec_filings(self.cik_list)

     # Key = Ticker; Value = CIK
        #self.ticker_mapping = pull_json(jpath) 

    def fetch_sec_filings(self, cik_list: list[str]) -> None:
        """
        Fetch filings for a list of companies and save the aggregated data.
        
        :param cik_list: List of 10-digit CIK strings.
        """
        aggregated_filings = {}
        for cik in cik_list:
            filings_data = self.extract_data(cik)
            print(filings_data, "\n\n")
            if filings_data:
                aggregated_filings[cik] = filings_data
            else:
                print(f"No data found for CIK: {cik}")

        # Save aggregated data
        spath = os.path.join(self.base_dir, f'data/filings_{datetime.datetime.now().strftime('%Y%m%d')}_{datetime.datetime.now().strftime('%H%M%S')}.json')
        #save_json(spath, aggregated_filings)

    def fetch_accounts_payable(self, cik: str) -> bytes:
        """
        Fetch filings for a list of companies and save the aggregated data.
        
        :param cik_list: List of 10-digit CIK strings.
        """
        aggregated_filings = {}
        filings_data = self.extract_data(cik)
        if filings_data:
            return filings_data 
        else:
            print(f"\n[SEC] - No accounts payable data found...")
            return b""

    def extract_data(self, cik: str) -> bytes:
        print(f"\n[REGI] - Extracting data for the following CIK (Central Index Key): {cik}\n")
#        url = self.url_template.replace('##########', cik)
        url = self.url_xbrl.replace('##########', cik)

        print(url)
        res = self.reqsesh.get(url)

        return res


if __name__=="__main__":
    sec = SEC()