import os
import requests
import urllib.parse

from cs50 import SQL
from flask import redirect, render_template, request, session
from functools import wraps
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import pytz
import finnhub

#import psycopg2

#db = SQL("sqlite:///finance.db")
#db = SQL(os.environ.get("postgres://jfbpknqvvinlsw:a0b3987fc025df9455b8ce55e807c2f572bec567efae497c3bb03525f3017c7b@ec2-54-146-118-15.compute-1.amazonaws.com:5432/d4kvpncu0qvihd") or "sqlite:///finance.db")
db = SQL("postgresql://jfbpknqvvinlsw:a0b3987fc025df9455b8ce55e807c2f572bec567efae497c3bb03525f3017c7b@ec2-54-146-118-15.compute-1.amazonaws.com:5432/d4kvpncu0qvihd")


api_key_iex = "pk_59fbe731d8a4431396e520b9e2e2ed87"
api_key_finnhub1 = "bv77j6f48v6qefljqrr0"
api_key_finnhub2 = "bvbb94v48v6q7r401fn0"

finnhub_client = finnhub.Client(api_key="bv77j6f48v6qefljqrr0")

#api_key_finnhub2 = "bvbb94v48v6q7r401fn0"

def timecheck(quote):

    #timecheck checks to see if we've updated in that time of day because we only update three times a week
    current_date = datetime.now(pytz.timezone('US/Eastern')).date()
    current_time = datetime.now(pytz.timezone('US/Eastern'))
    print(current_date)
    current_minute = str(current_time.minute)
    if (len(current_minute) < 2):
        current_minute = str(0) + current_minute
    hour_min = int(str(current_time.hour) + current_minute)

    #adjust time ints to check
    time_to_display = str(current_time.hour) + ":" + current_minute
    if (current_time.minute < 10):
        current_minute = str(0) + str(current_time.minute)
        hour_min = int(str(current_time.hour) + current_minute)
        time_to_display = str(current_time.hour) + ":" + current_minute

    #get the latest quote for that ticker
    #quote =  db.execute("SELECT date, time, ticker, price, change FROM prices WHERE ticker = :ticker ORDER BY date, time DESC", ticker = ticker)[0]

    ticker = quote["ticker"]
    
    #if there is no quote, we need to update it in our prices database
    if quote["price"] is None:
        ticker_quote = lookup(ticker)
        price = ticker_quote["price"]
        change = ticker_quote["change"]
        profile = company_profile(ticker)
        industry = ""
        if profile is not None:
            industry = profile["industry"]
        else:
            industry = "misc."
        db.execute("UPDATE prices SET date = :date, time = :time, price = :price, industry = :industry, change = :change WHERE ticker = :ticker", date = current_date, time = hour_min, price = price, industry = industry, change = change, ticker = ticker)

    #check the time of days to update accordingly
    first_check = (quote["date"] < current_date)
    second_check = (quote["date"] == current_date and hour_min >= 930 and hour_min < 1230 and quote["time"] < 930)
    first_third_check = (quote["date"] == current_date and hour_min < 1530 and hour_min >= 1230 and quote["time"] < 1230)
    second_third_check = (quote["date"] == current_date and hour_min >= 1530 and hour_min < 1630 and quote["time"] < 1530)
    third_third_check = (quote["date"] == current_date and hour_min >= 1600 and quote["time"] < 1600)

    return (first_check or second_check or first_third_check or second_third_check or third_third_check)

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.
        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code

def login_required(f):
    """
    Decorate routes to require login.
    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    #Look up quote for symbol.
    # Contact API
    symbol = symbol.lower()
    try:
        url = f"https://cloud.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key_iex}"
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    """try:
    except (KeyError, TypeError, ValueError):
        return none"""
    quote = response.json()
    return {
        "name": quote["companyName"],
        "price": float(quote["latestPrice"]),
        "symbol": quote["symbol"],
        "change": quote["changePercent"]
    }

"""
def lookup(symbol): 
    quote = finnhub_client.quote(symbol)
    if quote is None: 
        return none

    return {
        "name": symbol,
        "price": float(quote["c"]),
        "symbol": symbol, 
        "change": (float(quote["c"])-float(quote["pc"]))/float(quote["pc"])
    }
    """


def news_lookup(symbol):
    today = date.today()
    today_sixmonths = today + relativedelta(months=- 6)
    d1 = today.strftime("%Y-%m-%d")
    d2 = today_sixmonths.strftime("%Y-%m-%d")

    api_input = "&from=" + d2 + "&to=" + d1 + "&"
    # Contact API
    try:
        url = f"https://finnhub.io/api/v1/company-news?symbol={urllib.parse.quote_plus(symbol)}{api_input}token={api_key_finnhub1}"
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        news = response.json()
        return_news = []
        return_news.clear()
        i = 0
        for new in news:
            return_news.append({"datetime": datetime.utcfromtimestamp(new["datetime"]).strftime('%m-%d-%Y'),"headline": new["headline"],"source": new["source"],"summary": new["summary"],"url": new["url"], "image": new["image"]})
        return return_news
    except (KeyError, TypeError, ValueError):
        return None

def company_profile(symbol):
    # Contact API
    try:
        url = f"https://finnhub.io/api/v1/stock/profile2?symbol={urllib.parse.quote_plus(symbol)}&token={api_key_finnhub2}"
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        profile = response.json()
        return {
            "name": profile["ticker"],
            "industry": profile["finnhubIndustry"],
            "country": profile["country"],
            "exchange": profile["exchange"],
            "url": profile["weburl"],
            "logo": profile["logo"]
        }
    except (KeyError, TypeError, ValueError):
        return None

def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"