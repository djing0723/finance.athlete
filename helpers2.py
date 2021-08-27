import os
import requests
import urllib.parse

from cs50 import SQL
from flask import redirect, render_template, request, session
from functools import wraps
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from helpers import timecheck, lookup, company_profile
import pytz
import finnhub
#import psycopg2


#db = SQL("sqlite:///finance.db")
#db = SQL(os.environ.get("postgres://jfbpknqvvinlsw:a0b3987fc025df9455b8ce55e807c2f572bec567efae497c3bb03525f3017c7b@ec2-54-146-118-15.compute-1.amazonaws.com:5432/d4kvpncu0qvihd") or "sqlite:///finance.db")
db = SQL("postgresql://jfbpknqvvinlsw:a0b3987fc025df9455b8ce55e807c2f572bec567efae497c3bb03525f3017c7b@ec2-54-146-118-15.compute-1.amazonaws.com:5432/d4kvpncu0qvihd")


#this helps us update prices when we want
def prices_update(ticker):
    #get the current date to compare to prices table
    ticker = ticker.upper().strip()
    current_date = datetime.now(pytz.timezone('US/Eastern')).date()
    print(current_date)
    current_time = datetime.now(pytz.timezone('US/Eastern'))
    current_minute = str(current_time.minute)
    if (len(current_minute) < 2):
        current_minute = str(0) + current_minute
    hour_min = int(str(current_time.hour) + current_minute)

    #what do we have prices for
    price_rows_tickers = db.execute("SELECT DISTINCT lower(trim(ticker)) as ticker FROM prices")
    price_row_tickers_values = []
    price_row_tickers_values.clear()
    if len(price_rows_tickers)>0:
        for price in price_rows_tickers:
            price_row_tickers_values.append(price["ticker"])

    print(lookup(ticker))
    
    #if it's not in there, call IEX to get a quote and insert
    if ticker.lower().strip() not in price_row_tickers_values:
        print(ticker.lower().strip())
        quote = lookup(ticker)
        profile = company_profile(ticker)
        industry = ""
        if profile is not None:
            industry = profile["industry"]
            country = profile["country"]
        else:
            industry = "misc."
            country = "misc."
        if quote is not None: 
            price = quote["price"]
        else: 
            price = 0
        change = 0
        if quote["change"] is not None:
            change = float(quote["change"])
        db.execute("INSERT INTO prices (date, time, ticker, price, industry, change, country) VALUES(?,?,?,?, ?, ?,?)",  current_date, hour_min, ticker, price, industry, change, country)

    #else, update it through here
    else:
        quote = lookup(ticker)
        price = quote["price"]
        change = 0
        if quote["change"] is not None:
            change = float(quote["change"])
        profile = company_profile(ticker)
        if profile is not None:
            industry = profile["industry"]
            country = profile["country"]
        else:
            industry = "misc."
            country = "misc."
        db.execute("UPDATE prices SET date = :date, time = :time, price = :price, industry = :industry, change = :change, country = :country WHERE ticker = :ticker", date = current_date, time = hour_min, price = price, industry = industry, change = change, ticker = ticker, country = country)

finnhub_client = finnhub.Client(api_key = "bvbb94v48v6q7r401fn0")

def financials_update(ticker):

    financials = {}

    ct_fh_financials1 = finnhub_client.company_basic_financials(ticker, 'all')['metric']
    ct_fh_financials2 = finnhub_client.company_profile2(symbol = ticker)

    share_count = ct_fh_financials2["shareOutstanding"]
    financials["shares"] = share_count

    financials["ebitda"] = 0
    if "ebitdPerShareTTM" in ct_fh_financials1.keys():
        if ct_fh_financials1["ebitdPerShareTTM"] is not None:
            financials['ebitda'] = share_count * ct_fh_financials1["ebitdPerShareTTM"]

    financials["sales"] = 0
    if "revenuePerShareTTM" in ct_fh_financials1.keys():  
        if ct_fh_financials1["revenuePerShareTTM"] is not None:
            financials['sales'] = share_count * ct_fh_financials1["revenuePerShareTTM"]

    market_cap = 0
    if "marketCapitalization" in ct_fh_financials1.keys():
        if ct_fh_financials1["marketCapitalization"] is not None:
            financials["marketcap"] = ct_fh_financials1["marketCapitalization"]
            market_cap = ct_fh_financials1["marketCapitalization"]
        else: 
            financials["marketcap"] = 0
    else: 
        financials["marketcap"] = 0

    net_debt = 0
    financials["netdebt"] = 0
    if "netDebtAnnual" in ct_fh_financials1.keys():
        if ct_fh_financials1["netDebtAnnual"] is not None:
            financials["netdebt"] = ct_fh_financials1["netDebtAnnual"]
        else: 
            financials["netdebt"] = 0
        net_debt = financials["netdebt"]
    else: 
        financials["netdebt"] = 0

    ev = market_cap + net_debt
    financials['ev'] = market_cap + net_debt

    financials["evsales"] = 0
    if (financials['sales'] != 0 ):
        evsales = ev/financials['sales']
        financials['evsales'] = evsales
    else: 
        financials['evsales'] = 0

    financials["evebitda"] = 0
    if (financials['ebitda']!=0 ):
        evebitda = ev/financials['ebitda']
        financials['evebitda'] = evebitda
    else: 
        financials['evebitda'] = 0

   #financials["revgrowththree"] = 0
    #if (ct_fh_financials1["revenueGrowth3Y"] is not None):
    if "revenueGrowth3Y" in ct_fh_financials1.keys():
        financials['revgrowththree'] = ct_fh_financials1["revenueGrowth3Y"]
    else: 
        financials['revgrowththree'] = None 

    if "peNormalizedAnnual" in ct_fh_financials1.keys():
        financials['peratio'] = ct_fh_financials1["peNormalizedAnnual"]
    else: 
        financials['peratio'] = None

    #financials["revgrowthttm"] = 0
   # if (ct_fh_financials1["revenueGrowthTTMYoy"] is not None):
    if "revenueGrowthTTMYoy" in ct_fh_financials1.keys():
        financials['revgrowthttm'] = ct_fh_financials1["revenueGrowthTTMYoy"]
    else: 
        financials['revgrowthttm'] = 0

    """financials["epsgrowththree"] = 0
    if (ct_fh_financials1["epsGrowth3Y"] is not None):"""
    if "epsGrowth3Y" in ct_fh_financials1.keys():
        financials['epsgrowththree'] = ct_fh_financials1["epsGrowth3Y"]
    else: 
        financials['epsgrowththree'] = 0

    """financials["operatingmarginttm"] = 0
    if (ct_fh_financials1["operatingMarginTTM"] is not None):"""

    if "operatingMarginTTM" in ct_fh_financials1.keys():
        financials['operatingmarginttm'] = ct_fh_financials1["operatingMarginTTM"]
    else: 
        financials['operatingmarginttm'] = 0
    #financials["roeTTM"] = 0
    #if (ct_fh_financials1["roeTTM"] is not None):
    if "roeTTM" in ct_fh_financials1.keys():
        financials['roettm'] = ct_fh_financials1["roeTTM"]
    else: 
        financials['roettm'] = 0

    #financials["debttoequity"] = 0
    #if (ct_fh_financials1["totalDebt/totalEquityQuarterly"] is not None):
    if "totalDebt/totalEquityQuarterly" in ct_fh_financials1.keys():
        financials['debttoequity'] = ct_fh_financials1["totalDebt/totalEquityQuarterly"]
    else: 
        financials['debttoequity'] = 0

   # financials["roi"] = 0
    #if (ct_fh_financials1["roiTTM"] is not None):
    if "roiTTM" in ct_fh_financials1.keys():
        financials['roi'] = ct_fh_financials1["roiTTM"]
    else: 
        financials['roi'] = 0

    #financials["netmargin"] = 0
    #if (ct_fh_financials1["netProfitMarginTTM"] is not None):
    if "netProfitMarginTTM" in ct_fh_financials1.keys():
        financials['netmargin'] = ct_fh_financials1["netProfitMarginTTM"]
    else: 
        financials['netmargin'] = 0

    #financials["beta"] = 0
   # if (ct_fh_financials1["beta"] is not None):
    if "beta" in ct_fh_financials1.keys():
        financials['beta'] = ct_fh_financials1["beta"]
    else: 
        financials['beta'] = 0

    return financials
