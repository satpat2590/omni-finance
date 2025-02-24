from requests import Request, Session
import json
import os, sys, re

# Add modules from base repo
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from regi.session import RequestSession

if __name__=="__main__":
    API_KEY = os.environ['COIN_MARKET_CAP_API']
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
    parameters = {
        'start':'1',
        'limit':'5000',
        'convert':'USD'
    }
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': API_KEY,
    }

    reqsesh = RequestSession(headers=headers)

    response = reqsesh.get(url)

    res_cleaned = json.loads(response)
    jsonres = json.dumps(res_cleaned, indent=4)

    print(jsonres)
