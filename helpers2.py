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
import psycopg2


#db = SQL("sqlite:///finance.db")
#db = SQL(os.environ.get("postgres://jfbpknqvvinlsw:a0b3987fc025df9455b8ce55e807c2f572bec567efae497c3bb03525f3017c7b@ec2-54-146-118-15.compute-1.amazonaws.com:5432/d4kvpncu0qvihd") or "sqlite:///finance.db")
db = SQL("postgres://jfbpknqvvinlsw:a0b3987fc025df9455b8ce55e807c2f572bec567efae497c3bb03525f3017c7b@ec2-54-146-118-15.compute-1.amazonaws.com:5432/d4kvpncu0qvihd")


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

    #if it's not in there, call IEX to get a quote and insert
    if ticker.lower().strip() not in price_row_tickers_values:
        print(ticker.lower().strip())
        quote = lookup(ticker)
        profile = company_profile(ticker)
        industry = ""
        if profile is not None:
            industry = profile["industry"]
        else:
            industry = "misc."
        price = quote["price"]
        change = 0
        if quote["change"] is not None:
            change = float(quote["change"])
        db.execute("INSERT INTO prices (date, time, ticker, price, industry, change) VALUES(?,?,?,?, ?, ?)",  current_date, hour_min, ticker, price, industry, change)

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
        else:
            industry = "misc."
        db.execute("UPDATE prices SET date = :date, time = :time, price = :price, industry = :industry, change = :change WHERE ticker = :ticker", date = current_date, time = hour_min, price = price, industry = industry, change = change, ticker = ticker)

finnhub_client = finnhub.Client(api_key = "bvbb94v48v6q7r401fn0")

def financials_update(ticker):

    financials = {}

    ct_fh_financials1 = finnhub_client.company_basic_financials(ticker, 'all')['metric']
    ct_fh_financials2 = finnhub_client.company_profile2(symbol = ticker)

    if (len(ct_fh_financials1) == 0 or len(ct_fh_financials2) == 0):
        return financials

    share_count = ct_fh_financials2["shareOutstanding"]
    financials["shares"] = share_count

    financials["ebitda"] = 0
    if ct_fh_financials1["ebitdPerShareTTM"] is not None:
        financials['ebitda'] = share_count * ct_fh_financials1["ebitdPerShareTTM"]

    financials['sales'] = 0
    if ct_fh_financials1["revenuePerShareTTM"] is not None:
        financials['sales'] = share_count * ct_fh_financials1["revenuePerShareTTM"]

    market_cap = ct_fh_financials1["marketCapitalization"]
    financials["marketcap"] = market_cap
    net_debt = ct_fh_financials1["netDebtAnnual"]
    financials["netdebt"] = net_debt
    ev = market_cap + net_debt
    financials['ev'] = market_cap + net_debt

    financials["evsales"] = 0
    if (financials['sales'] != 0):
        evsales = ev/financials['sales']
        financials['evsales'] = evsales

    evebitda = 0
    if (financials['ebitda']!=0):
        evebitda = ev/financials['ebitda']
    financials['evebitda'] = evebitda

   #financials["revgrowththree"] = 0
    #if (ct_fh_financials1["revenueGrowth3Y"] is not None):
    financials['revgrowththree'] = ct_fh_financials1["revenueGrowth3Y"]

    #financials["revgrowthttm"] = 0
   # if (ct_fh_financials1["revenueGrowthTTMYoy"] is not None):
    financials['revgrowthttm'] = ct_fh_financials1["revenueGrowthTTMYoy"]

    """financials["epsgrowththree"] = 0
    if (ct_fh_financials1["epsGrowth3Y"] is not None):"""
    financials['epsgrowththree'] = ct_fh_financials1["epsGrowth3Y"]

    """financials["operatingmarginttm"] = 0
    if (ct_fh_financials1["operatingMarginTTM"] is not None):"""
    financials['operatingmarginttm'] = ct_fh_financials1["operatingMarginTTM"]

    #financials["roeTTM"] = 0
    #if (ct_fh_financials1["roeTTM"] is not None):
    financials['roettm'] = ct_fh_financials1["roeTTM"]

    #financials["debttoequity"] = 0
    #if (ct_fh_financials1["totalDebt/totalEquityQuarterly"] is not None):
    financials['debttoequity'] = ct_fh_financials1["totalDebt/totalEquityQuarterly"]

   # financials["roi"] = 0
    #if (ct_fh_financials1["roiTTM"] is not None):
    financials['roi'] = ct_fh_financials1["roiTTM"]

    #financials["netmargin"] = 0
    #if (ct_fh_financials1["netProfitMarginTTM"] is not None):
    financials['netmargin'] = ct_fh_financials1["netProfitMarginTTM"]

    #financials["beta"] = 0
   # if (ct_fh_financials1["beta"] is not None):
    financials['beta'] = ct_fh_financials1["beta"]
    print(financials)
    return financials

