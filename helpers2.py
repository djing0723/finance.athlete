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

db = SQL("sqlite:///finance.db")

#this helps us update prices when we want
def prices_update(ticker):
    #get the current date to compare to prices table
    ticker = ticker.upper().strip()
    current_date = date.today().strftime('%Y-%m-%d')
    current_time = datetime.now(pytz.timezone("America/New_York"))
    current_minute = str(current_time.minute)
    if (len(current_minute) < 2):
        current_minute = str(0) + current_minute
    hour_min = int(str(current_time.hour) + current_minute)

    #what do we have prices for
    price_rows_tickers = db.execute("SELECT DISTINCT lower(trim(ticker)) FROM prices")
    price_row_tickers_values = []
    price_row_tickers_values.clear()
    for price in price_rows_tickers:
        price_row_tickers_values.append(price["lower(trim(ticker))"])

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
        change = quote["change"]
        db.execute("INSERT INTO prices (date, time, ticker, price, industry, change) VALUES(?,?,?,?, ?, ?)",  current_date, hour_min, ticker, price, industry, change)

    #else, update it through here
    else:
        quote = lookup(ticker)
        price = quote["price"]
        change = float(quote["change"])
        profile = company_profile(ticker)
        if profile is not None:
            industry = profile["industry"]
        else:
            industry = "misc."
        db.execute("UPDATE prices SET date = :date, time = :time, price = :price, industry = :industry, change = :change WHERE ticker = :ticker", date = current_date, time = hour_min, price = price, industry = industry, change = change, ticker = ticker)

