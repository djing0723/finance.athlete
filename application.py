import os

#import psycopg2
from cs50 import SQL
import sqlite3
import finnhub
from flask import Flask, flash, redirect, render_template, request, session, send_file
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import json
#from newsapi import NewsApiClient
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import pytz
from helpers import apology, login_required, lookup, news_lookup, usd, company_profile, timecheck
from helpers2 import prices_update, financials_update
from millify import millify
import csv

# Configure application

#pip install finnhub-python
#git config --global user.name djing0723
#git config --global user.email "darius.jing@yale.edu"
#pip install psycopg2-binary
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
#db = SQL("sqlite:///finance.db")
#db = SQL(os.environ.get("postgres://jfbpknqvvinlsw:a0b3987fc025df9455b8ce55e807c2f572bec567efae497c3bb03525f3017c7b@ec2-54-146-118-15.compute-1.amazonaws.com:5432/d4kvpncu0qvihd") or "sqlite:///finance.db")
db = SQL("postgres://jfbpknqvvinlsw:a0b3987fc025df9455b8ce55e807c2f572bec567efae497c3bb03525f3017c7b@ec2-54-146-118-15.compute-1.amazonaws.com:5432/d4kvpncu0qvihd")
#db = sqlite3.connect('finance.db', check_same_thread = False)

# Make sure API key is set
"""if not os.environ.get("API_KEY_IEX"):
    raise RuntimeError("API_KEY_IEX not set")
if not os.environ.get("API_KEY_FINNHUB"):
    raise RuntimeError("API_KEY_FINNHUB not set")"""

# Set up finnhub client
#print(os.getenv("API_KEY_FINNHUB"))
finnhub_client = finnhub.Client(api_key="bv77j6f48v6qefljqrr0")

@app.route("/", methods=["GET", "POST"])
@login_required
def index():

    weekno = datetime.today().weekday()

    #select the user and get their positions, done by accessing the SQL database
    user_id = session["user_id"]
    rows = db.execute("SELECT user_id, ticker, SUM(quantity) as quantity, SUM(price* quantity)/SUM(quantity) as costbasis FROM positions where user_id = :id GROUP BY user_id, ticker HAVING sum(quantity)<>0", id = session["user_id"])
    user_cash = round(db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"],2)

    #create a SQL database to update stock prices 3 times a day. This way, we don't have to keep on calling the API, saving us API calls and page load time

    #get the date to track what date and what time stock prices have been updated.
    current_date = datetime.now(pytz.timezone('US/Eastern')).date()
    current_time = datetime.now(pytz.timezone("America/New_York"))
    current_minute = str(current_time.minute)
    hour_min = int(str(current_time.hour) + current_minute)

    #formatting time to display on our website
    time_to_display = str(current_time.hour) + ":" + current_minute
    if (current_time.minute < 10):
        current_minute = str(0) + str(current_time.minute)
        hour_min = int(str(current_time.hour) + current_minute)
        time_to_display = str(current_time.hour) + ":" + current_minute

    #boolean to check if the user requested a manual update
    manual_update = request.form.get("Update") == "Update"

    #select all our price rows to check what stocks we have prices for, as well as what time they were made
    #create two rows to check if all our user's tickers are in the price tickers
    price_rows = db.execute("SELECT date, time, ticker, price, change, industry FROM prices")
    price_rows_tickers = []
    price_rows_tickers.clear()

    rows_tickers = []
    rows_tickers.clear()

    #initialize strings to change
    spy_pct_string = ""
    qqq_pct_string = ""

    #price_rows = db.execute("SELECT date, time, ticker, price, change, industry FROM prices")

    #select SPY and QQQ prices to see if they have been recently updated. if they do not exist in the db, insert them. If they do, select the latest price of each stock, and update if we need to.
    spy = db.execute("SELECT date, time, ticker, price, change FROM prices WHERE ticker = :ticker", ticker = "SPY")
    spy_data = 0
    if (len(spy) == 0):
        price = lookup("SPY")["price"]
        change = lookup("SPY")["change"]
        db.execute("INSERT INTO prices (date, time, ticker, price, industry, change) VALUES(?,?,?,?, ?, ?)",  current_date, hour_min, "SPY", price, "misc.", change)
    else:
        spy_rows = spy[0]
        if (timecheck("SPY") or manual_update):
            prices_update("SPY")
    spy_data = db.execute("SELECT date, time, ticker, price, change FROM prices WHERE ticker = :ticker", ticker = "SPY")[0]


    qqq = db.execute("SELECT date, time, ticker, price, change FROM prices WHERE ticker = :ticker", ticker = "QQQ")
    qqq_data = 0
    if (len(qqq) == 0):
        price = lookup("QQQ")["price"]
        change = lookup("QQQ")["change"]
        db.execute("INSERT INTO prices (date, time, ticker, price, industry, change) VALUES(?,?,?,?, ?, ?)",  current_date, hour_min, "QQQ", price, "misc.", change)
    else:
        qqq_rows = qqq[0]
        if (timecheck("QQQ") or manual_update):
            prices_update("QQQ")
    qqq_data = db.execute("SELECT date, time, ticker, price, change FROM prices WHERE ticker = :ticker", ticker = "QQQ")[0]

    #display the market changes
    spy_pct_string = "{:.2%}".format((spy_data)["change"])
    qqq_pct_string = "{:.2%}".format((qqq_data)["change"])

    #create new array to use in javascript. Need to append the headers so google charts knows the labels
    rows2 = []
    rows2.clear()
    rows2.append(["Company", "Amount"])

    rows3 = []
    rows3.clear()
    rows3.append(["Industry", "Amount"])

    industry_list = []
    industry_list.clear()

    style_list = []
    style_list.clear()
    style_list.append(["Style", "Amount"])

    country_list = []
    country_list.clear()
    country_list.append(["Country", "Amount"])

    #loop through user positions and add relevant lists
    if len(rows)!=0:
        user_equity = 0
        total = user_cash

        for i in range(0, len(rows)):
            #price_lookup = db.execute("SELECT date, time, ticker, price, change, industry FROM prices")
            quote = db.execute("SELECT date, time, ticker, price, change, industry FROM prices WHERE ticker = :ticker", ticker = rows[i]["ticker"])
            #select the latest quote from prices. if it is not in our prices table, we update its price, then reassign quote to be used
            if (len(quote) == 0):
                prices_update(rows[i]["ticker"])

            #if it is time to update or the user clicks to update, then we update
            if (timecheck(rows[i]["ticker"]) or manual_update):
                prices_update(rows[i]["ticker"])

            quote = db.execute("SELECT date, time, ticker, price, change, industry FROM prices WHERE ticker = :ticker ORDER BY date, time DESC", ticker = rows[i]["ticker"])[0]

            #add dicts to give more insight into allocation
            rows[i]["industry"] = quote["industry"]
            rows[i]["price"] = quote["price"]
            rows[i]["costbasis"] = rows[i]["costbasis"]
            rows[i]["change"] = quote["change"]
            #how much an user made on average for their positions. Calcualtes based on the average cost of their stocks
            return_number = (rows[i]["price"]/rows[i]["costbasis"])-1

            #price_total is the total market value. We append this to row 2 to be used in javascript to draw the pie chart
            price_total = rows[i]["quantity"]*rows[i]["price"]
            rows2.append([quote["ticker"], price_total])

            #if add all industries to rows3 to draw this in google charts
            if (rows[i]["industry"] not in industry_list):
                industry_list.append(rows[i]["industry"])
                rows3.append([rows[i]["industry"], 0])

            #calculate total amount user has
            user_equity += price_total
            cost_total = rows[i]["quantity"]*rows[i]["costbasis"]

            #more insights calculated
            rows[i]["pctchange"] = "{:.2%}".format(float(quote["change"]))
            rows[i]["totalreturn_usd"] = usd(price_total - cost_total)
            rows[i]["total_usd"] = usd(round(rows[i]["quantity"]*rows[i]["price"],2))
            rows[i]["price_usd"] = usd(quote["price"])
            rows[i]["costbasis"] = usd(round(rows[i]["costbasis"],2))

            #each stock's return
            rows[i]["return"] = "{:.2%}".format(return_number)

        #total calculated to calculate % change of each stock compared to portfolio so we can calculated daily change
        total = user_cash + user_equity

        overall_pct = 0

        #caclculate total % change of portfolio
        for i in range(0, len(rows)):
            rows[i]["portfolio_percentage"] = "{:.2%}".format(rows[i]["price"] * rows[i]["quantity"] / total)
            overall_pct += (float(rows[i]["change"]) * (rows[i]["quantity"] * rows[i]["price"]))/total
            for j in range(0, len(rows3)):
                industry = rows3[j][0]
                if industry == rows[i]["industry"]:
                    rows3[j][1] += (rows[i]["quantity"] * rows[i]["price"])

        overall_pct_string = "{:.2%}".format(overall_pct)

    #if they have no positions, just set things to 0.
    else:
        user_equity = 0
        total = user_cash
        rows = []
        rows2 = []
        overall_pct_string = "0%"

    if len(db.execute("SELECT * FROM performance WHERE user_id = :user_id AND date = :current_date", user_id = user_id, current_date= current_date)) == 0:
        if weekno < 5:
            db.execute("INSERT INTO performance (user_id, portfolio, date) VALUES(?,?,?)", user_id, total, current_date)
    else:
        db.execute("UPDATE performance SET portfolio = :total WHERE user_id = :id AND date = :current_date", total = total, id = user_id, current_date = current_date)

    #query the total amount per style
    style_rows = db.execute("SELECT style, sum(marketvalue) as marketvalue from (SELECT prices.price * sum(quantity) as marketvalue, lower(trim(style)) as style, user_id, positions.ticker, SUM(quantity) as quantity, SUM(positions.price* quantity)/SUM(quantity) as costbasis FROM positions join prices on prices.ticker = positions.ticker where user_id = :user_id GROUP BY user_id, style, positions.ticker, prices.price HAVING sum(quantity)<>0) AS total_positions group by style", user_id = user_id)

    #append the styles and amount, we can now graph this in index
    for i in range(0, len(style_rows)):
        style_list.append([style_rows[i]["style"], style_rows[i]["marketvalue"]])

    country_rows = db.execute("SELECT country, sum(marketvalue) as marketvalue from (SELECT prices.price * sum(quantity) as marketvalue, country, user_id, positions.ticker, SUM(quantity) as quantity, SUM(positions.price* quantity)/SUM(quantity) as costbasis FROM positions join prices on prices.ticker = positions.ticker where user_id = :user_id GROUP BY user_id, country, positions.ticker, prices.price HAVING sum(quantity)<>0) AS total_positions group by country", user_id = user_id)
    for i in range(0, len(country_rows)):
        if country_rows is not None:
            country_list.append([country_rows[i]["country"], country_rows[i]["marketvalue"]])

    #select all the times of our price updates
    time_rows = db.execute("SELECT prices.time, user_id, positions.ticker, SUM(quantity) as quantity, SUM(positions.price* quantity)/SUM(quantity) as costbasis FROM positions join prices on prices.ticker = positions.ticker where user_id = :user_id GROUP BY user_id, positions.ticker, prices.time HAVING sum(quantity)<>0 ", user_id = user_id)
    time_rows_time = str(hour_min)

    if (len(time_rows) != 0):
        time_rows_time = str(time_rows[0]["time"])

    #change the 3 or 4 number int to a string which we can display on our webpage
    first_half = ""
    second_half = ""
    if (len(time_rows_time) == 4):
        second_half = time_rows_time[-2:]
        first_half = time_rows_time[:2]
        time_to_display = first_half + ":" + second_half
    if (len(time_rows_time) == 3):
        second_half = time_rows_time[-2:]
        first_half = time_rows_time[:1]
        time_to_display = first_half + ":" + second_half


    #everyone is given a default watchlist. after registering, everyone is setn to the index. from there, you are assigned default watchlist
    watchlist =  db.execute("SELECT * FROM watchlist_name WHERE user_id = :user_id AND watchlist_name = :watchlist_name", user_id = user_id, watchlist_name = "default")
    if len(watchlist) == 0:
        #print("the length is 0")
        db.execute("INSERT INTO watchlist_name (watchlist_name, user_id) VALUES(?,?)",  "default", user_id)

    #creating calendar array
   #calendar = []
    #calendar.clear()

    #calculate two weeks ago and two weeks later. will be the timeframe of our relevant earnings
    """two_weeks_ago = (date.today() + relativedelta(weeks = -2)).strftime("%Y-%m-%d")
    two_weeks_later = (date.today() + relativedelta(weeks = 2)).strftime("%Y-%m-%d")

    #get the closest earnings for each stock in our portfolio
    for i in range(0, len(rows)):
        latest_ec = db.execute("SELECT * FROM earnings_calendar WHERE symbol = :symbol AND date_updated = :date_updated AND real = :real", symbol = rows[i]["ticker"], date_updated = current_date, real = "true")
        latest_ec_fill = db.execute("SELECT * FROM earnings_calendar WHERE symbol = :symbol AND date_updated = :date_updated AND real = :real", symbol = rows[i]["ticker"], date_updated = current_date, real = "false")

        if (len(latest_ec_fill) == 0 and len(latest_ec) == 0):
            ec1 = finnhub_client.earnings_calendar(_from=two_weeks_ago, to=two_weeks_later, symbol = rows[i]["ticker"])["earningsCalendar"]
            if (len(ec1) != 0):
                ec = ec1[0]
                if (ec["date"] >= two_weeks_ago and ec["date"] <= two_weeks_later):
                    db.execute("INSERT INTO earnings_calendar (date, epsactual, epsestimate, hour, quarter, revenueactual, revenueestimate, symbol, year, date_updated, real) VALUES(?,?,?,?,?,?,?,?,?,?,?)", ec["date"], ec["epsactual"], ec["epsestimate"], ec["hour"], ec["quarter"], ec["revenueactual"], ec["revenueestimate"], ec["symbol"], ec["year"], current_date, "true")
                else:
                    db.execute("INSERT INTO earnings_calendar (date, epsactual, epsestimate, hour, quarter, revenueactual, revenueestimate, symbol, year, date_updated, real) VALUES(?,?,?,?,?,?,?,?,?,?,?)", current_date, 0, 0, 0, 0,0, 0, rows[i]["ticker"], 0, current_date, "false")

                #db.execute("SELECT * FROM earnings_calendar WHERE symbol = :symbol AND date_updated = :date_updated", symbol = rows[i]["ticker"], date_updated = current_date
    prev_earnings = db.execute("SELECT DISTINCT epsactual, epsestimate, revenueestimate, revenueactual, hour, date, quarter,symbol,year FROM earnings_calendar WHERE date >= :date_two_weeks_ago AND date < :current_date AND symbol in (SELECT ticker FROM total_positions WHERE user_id = :user_id) AND real = :real ORDER BY date DESC", date_two_weeks_ago = two_weeks_ago, current_date = current_date, user_id = user_id, real = "true")
    for i in range(0, len(prev_earnings)):
        prev_earnings[i]["epsbeat"] = "{:.2%}".format(prev_earnings[i]["epsactual"]/prev_earnings[i]["epsestimate"]-1)
        prev_earnings[i]["revenueBeat"] = "{:.2%}".format(prev_earnings[i]["revenueactual"]/prev_earnings[i]["revenueestimate"]-1)
        prev_earnings[i]["epsactual"] = usd(prev_earnings[i]["epsactual"])
        prev_earnings[i]["epsestimate"] = usd(prev_earnings[i]["epsestimate"] )
        prev_earnings[i]["revenueestimate"] = "$" + millify(prev_earnings[i]["revenueestimate"], precision = 2)
        prev_earnings[i]["revenueactual"] = "$" + millify(prev_earnings[i]["revenueactual"], precision = 2)
        if prev_earnings[i]["hour"] == "bmo":
            prev_earnings[i]["hour"] = "Pre Market"
        if prev_earnings[i]["hour"] == "amc":
            prev_earnings[i]["hour"] = "After Market"
#same as previous earnings
    future_earnings = db.execute("SELECT DISTINCT epsactual, epsestimate, revenueestimate, revenueactual, hour, date, quarter,symbol,year FROM earnings_calendar WHERE date >= :current_date AND date < :two_weeks_later AND symbol in (SELECT ticker FROm total_positions WHERE user_id = :user_id) AND real = :real ORDER BY date ASC", two_weeks_later = two_weeks_later, current_date = current_date, user_id = user_id, real = "true")
    for i in range(0, len(future_earnings)):
        future_earnings[i]["epsestimate"] = usd(future_earnings[i]["epsestimate"])
        future_earnings[i]["revenueestimate"] = "$" + millify(future_earnings[i]["revenueestimate"], precision = 2)
        if future_earnings[i]["hour"] == "bmo":
            future_earnings[i]["hour"] = "Pre Market"
        if future_earnings[i]["hour"] == "amc":
            future_earnings[i]["hour"] = "After Market"

    #print("EARNS: ", future_earnings);
    #print("Prev: ", prev_earnings);"""
    print(financials_update("WORK"))
    return render_template("index.html", rows = rows, rows2 = rows2, rows3 = rows3, user_cash = usd(user_cash), user_equity = usd(user_equity), total = usd(total), overall_pct = overall_pct_string, spy_pct_string = spy_pct_string, qqq_pct_string = qqq_pct_string, time_to_display= time_to_display, style_list = style_list, country_list = country_list)

@app.route("/watchlist", methods = ["GET", "POST"])
@login_required
def watchlist():
    #get all the user's watchlists
    user_id = session["user_id"]
    watchlists = []
    watchlist =  db.execute("SELECT watchlist_name.watchlist_id, watchlist_name, stock FROM watchlist_name LEFT JOIN watchlist_positions ON watchlist_name.watchlist_id = watchlist_positions.watchlist_id WHERE watchlist_name = :watchlist_name AND user_id = :user_id", watchlist_name = "default", user_id = user_id)

    if (request.method == "GET"):
    #add a default watchlist for everyone who logs on in case for some reason, they bypass index into watchlist
        watchlists =  db.execute("SELECT * FROM watchlist_name WHERE user_id = :user_id", user_id = user_id)

        if watchlists is None:
            db.execute("INSERT INTO watchlist_name (watchlist_name, user_id) VALUES(?,?)",  "default", user_id)
            watchlists =  db.execute("SELECT * FROM watchlist_name WHERE user_id = :user_id", user_id = user_id)

        watchlist =  db.execute("SELECT watchlist_name.watchlist_id, watchlist_name, stock FROM watchlist_name LEFT JOIN watchlist_positions ON watchlist_name.watchlist_id = watchlist_positions.watchlist_id WHERE watchlist_name = :watchlist_name AND user_id = :user_id", watchlist_name = "default", user_id = user_id)

    if (request.method == "POST"):

        if not request.form.get("watchlist"):
            return apology("Select a watchlist", 403)

        #there should be an user-selected watchlist. direct the page to this watchlist
        sel_watchlist = request.form.get("watchlist")
        #print(sel_watchlist)
        watchlists =  db.execute("SELECT * FROM watchlist_name WHERE user_id = :user_id", user_id = user_id)

        #make sure there is a default watchlist
        if watchlists is None:
            db.execute("INSERT INTO watchlist_name (watchlist_name, user_id) VALUES(?,?)",  "default", user_id)
            watchlists =  db.execute("SELECT * FROM watchlist_name WHERE user_id = :user_id", user_id = user_id)

        #select the watchlist the user had selected
        watchlist =  db.execute("SELECT watchlist_name.watchlist_id, watchlist_name, stock FROM watchlist_name LEFT JOIN watchlist_positions ON watchlist_name.watchlist_id = watchlist_positions.watchlist_id WHERE watchlist_name.watchlist_id = :sel_watchlist AND user_id = :user_id", sel_watchlist = sel_watchlist, user_id = user_id)

    #if there is a stock in the watchlist, select the prices of the stock. We changed it so that we just reference the chart widget to get the price information. This saves API calls and is faster, so this is commented out right now. Same in delete and add stock.
    """if (watchlist[0]["stock"] is not None):
        for i in range(0, len(watchlist)):
            price_lookup = db.execute("SELECT date, time, ticker, price, change, industry FROM prices")
            quote = db.execute("SELECT date, time, ticker, price, change, industry FROM prices WHERE ticker = :ticker", ticker = watchlist[i]["stock"])


            if (len(quote) == 0):
                prices_update(watchlist[i]["stock"])
                quote = db.execute("SELECT date, time, ticker, price, change, industry FROM prices WHERE ticker = :ticker", ticker = watchlist[i]["stock"])[0]

            quote = db.execute("SELECT date, time, ticker, price, change, industry FROM prices WHERE ticker = :ticker", ticker = watchlist[i]["stock"])[0]


            if (timecheck(watchlist[i]["stock"])):
                prices_update(watchlist[i]["stock"])

            print(watchlist[i])
            watchlist[i]["change"] = "{:.2%}".format(quote["change"])"""

    return render_template("watchlist.html", watchlists = watchlists, watchlist = watchlist)

@app.route("/addwatchlist", methods = ["GET","POST"])
@login_required
def addwatchlist():
    #redirect the user
    if (request.method == "GET"):
        return redirect("/watchlist")
    user_id = session["user_id"]
    watchlist_name = request.form.get("watchlist")
    existing_watchlists = db.execute("SELECT * FROM watchlist_name WHERE user_id = :user_id AND watchlist_name = :watchlist_name", user_id = user_id, watchlist_name = watchlist_name)

    #need to make sure that this watchlist does not exist
    if (len(existing_watchlists) != 0):
        return apology("Watchlist already exists", 403)

    #add the watchlist into our watchlist table
    db.execute("INSERT INTO watchlist_name (watchlist_name, user_id) VALUES(?,?)",  watchlist_name, user_id)
    watchlists =  db.execute("SELECT * FROM watchlist_name WHERE user_id = :user_id", user_id = user_id)
    watchlist =  db.execute("SELECT watchlist_name.watchlist_id, watchlist_name, stock FROM watchlist_name LEFT JOIN watchlist_positions ON watchlist_name.watchlist_id = watchlist_positions.watchlist_id WHERE watchlist_name = :watchlist_name AND user_id = :user_id", watchlist_name = watchlist_name, user_id = user_id)

    #return watchlist.html with our new watchlist selected
    return render_template("watchlist.html", watchlists = watchlists, watchlist = watchlist)

@app.route("/delwatchlist", methods = ["GET", "POST"])
@login_required
def delwatchlist():

    #redirect the user
    if (request.method == "GET"):
        return redirect("/watchlist")
    user_id = session["user_id"]
    watchlist_id = request.form.get("watchlist_id")
    watchlist_name =  db.execute("SELECT * FROM watchlist_name WHERE user_id = :user_id AND watchlist_id = :watchlist_id", user_id = user_id, watchlist_id = watchlist_id)[0]["watchlist_name"]
    #make sure user does not delete default watchlist because everyone needs a watchlist
    if (watchlist_name == "default"):
        return apology("Cannot delete default watchlist", 403)
    existing_watchlists = db.execute("SELECT * FROM watchlist_name WHERE user_id = :user_id AND watchlist_id = :watchlist_id", user_id = user_id, watchlist_id = watchlist_id)
    #make sure the user is for some reason not deleting an existing watchlist
    if (len(existing_watchlists) == 0):
        return apology("Does not exist", 403)
    db.execute("DELETE FROM watchlist_name WHERE watchlist_id = :watchlist_id", watchlist_id = watchlist_id)
    db.execute("DELETE FROM watchlist_positions WHERE watchlist_id = :watchlist_id", watchlist_id = watchlist_id)

    #select the default watchlist to return
    watchlists =  db.execute("SELECT * FROM watchlist_name WHERE user_id = :user_id", user_id = user_id)
    watchlist =  db.execute("SELECT watchlist_name.watchlist_id, watchlist_name, stock FROM watchlist_name LEFT JOIN watchlist_positions ON watchlist_name.watchlist_id = watchlist_positions.watchlist_id WHERE watchlist_name = :watchlist_name AND user_id = :user_id", watchlist_name = "default", user_id = user_id)

    """
    if (watchlist[0]["stock"] is not None):
        for i in range(0, len(watchlist)):
            price_lookup = db.execute("SELECT date, time, ticker, price, change, industry FROM prices")
            quote = db.execute("SELECT date, time, ticker, price, change, industry FROM prices WHERE ticker = :ticker", ticker = watchlist[i]["stock"])

            if (len(quote) == 0):
                prices_update(watchlist[i]["stock"])
                quote = db.execute("SELECT date, time, ticker, price, change, industry FROM prices WHERE ticker = :ticker", ticker = watchlist[i]["stock"])[0]

            quote = db.execute("SELECT date, time, ticker, price, change, industry FROM prices WHERE ticker = :ticker", ticker = watchlist[i]["stock"])[0]


            if (timecheck(watchlist[i]["stock"])):
                prices_update(watchlist[i]["stock"])

            print(watchlist[i])
            watchlist[i]["change"] = "{:.2%}".format(quote["change"])
    else:
         (watchlist[0]["stock"]) = ""
         """

    return render_template("watchlist.html", watchlists = watchlists, watchlist = watchlist)

@app.route("/addstockwatchlist", methods = ["POST"])
@login_required
def addstockwatchlist():
    #get the user ID and current watchlist
    user_id = session["user_id"]
    watchlist_id = request.form.get("watchlist_id")
    stock = request.form.get("stock").upper().strip()
    #make sure the user is selecting the correct ticker
    if (lookup(stock) is None):
        return apology("Invalid Ticker", 403)
    #insert that ticker into the watchlist table
    db.execute("INSERT INTO watchlist_positions (watchlist_id, stock) VALUES(?,?)",  watchlist_id, stock)
    watchlists =  db.execute("SELECT * FROM watchlist_name WHERE user_id = :user_id", user_id = user_id)
    watchlist =  db.execute("SELECT watchlist_name.watchlist_id, watchlist_name, stock FROM watchlist_name LEFT JOIN watchlist_positions ON watchlist_name.watchlist_id = watchlist_positions.watchlist_id WHERE watchlist_name.watchlist_id = :watchlist_id AND user_id = :user_id", watchlist_id = watchlist_id, user_id = user_id)

    #big block commented out because we decided to use a widget for the price rather than IEX API to save load time and calls. Might reincorporate this though, so just left it commented out for now
    """
    if (watchlist[0]["stock"] is not None):
        for i in range(0, len(watchlist)):
            price_lookup = db.execute("SELECT date, time, ticker, price, change, industry FROM prices")
            quote = db.execute("SELECT date, time, ticker, price, change, industry FROM prices WHERE ticker = :ticker", ticker = watchlist[i]["stock"])

            if (len(quote) == 0):
                prices_update(watchlist[i]["stock"])
                quote = db.execute("SELECT date, time, ticker, price, change, industry FROM prices WHERE ticker = :ticker", ticker = watchlist[i]["stock"])[0]

            quote = db.execute("SELECT date, time, ticker, price, change, industry FROM prices WHERE ticker = :ticker", ticker = watchlist[i]["stock"])[0]


            if (timecheck(watchlist[i]["stock"])):
                prices_update(watchlist[i]["stock"])

            print(watchlist[i])
            watchlist[i]["change"] = "{:.2%}".format(quote["change"])
    else:
         (watchlist[0]["stock"]) = ""

    for i in range(0, len(watchlist)):
        price_lookup = db.execute("SELECT date, time, ticker, price, change, industry FROM prices")
        quote = db.execute("SELECT date, time, ticker, price, change, industry FROM prices WHERE ticker = :ticker", ticker = watchlist[i]["stock"])

        if (len(quote) == 0):
            prices_update(watchlist[i]["stock"])
            quote = db.execute("SELECT date, time, ticker, price, change, industry FROM prices WHERE ticker = :ticker", ticker = watchlist[i]["stock"])[0]

        quote = db.execute("SELECT date, time, ticker, price, change, industry FROM prices WHERE ticker = :ticker", ticker = watchlist[i]["stock"])[0]


        if (timecheck(watchlist[i]["stock"])):
            prices_update(watchlist[i]["stock"])

        watchlist[i]["change"] = "{:.2%}".format(quote["change"])"""



    return render_template("watchlist.html", watchlists = watchlists, watchlist = watchlist)


@app.route("/delstockwatchlist", methods = ["POST"])
@login_required
def delstockwatchlist():
    #get the user id and watchlist to delete
    user_id = session["user_id"]
    watchlist_id = request.form.get("watchlist_id")
    stock = request.form.get("stock").upper().strip()
    if (lookup(stock) is None):
        return apology("Invalid Ticker", 403)
    db.execute("DELETE FROM watchlist_positions WHERE UPPER(stock) = :stock AND watchlist_id = :watchlist_id", stock = stock, watchlist_id = watchlist_id)
    watchlists =  db.execute("SELECT * FROM watchlist_name WHERE user_id = :user_id", user_id = user_id)
    watchlist =  db.execute("SELECT watchlist_name.watchlist_id, watchlist_name, stock FROM watchlist_name LEFT JOIN watchlist_positions ON watchlist_name.watchlist_id = watchlist_positions.watchlist_id WHERE watchlist_name.watchlist_id = :watchlist_id AND user_id = :user_id", watchlist_id = watchlist_id, user_id = user_id)
    """
    if (watchlist[0]["stock"] is not None):
        for i in range(0, len(watchlist)):
            price_lookup = db.execute("SELECT date, time, ticker, price, change, industry FROM prices")
            quote = db.execute("SELECT date, time, ticker, price, change, industry FROM prices WHERE ticker = :ticker", ticker = watchlist[i]["stock"])

            if (len(quote) == 0):
                prices_update(watchlist[i]["stock"])
                quote = db.execute("SELECT date, time, ticker, price, change, industry FROM prices WHERE ticker = :ticker", ticker = watchlist[i]["stock"])[0]

            quote = db.execute("SELECT date, time, ticker, price, change, industry FROM prices WHERE ticker = :ticker", ticker = watchlist[i]["stock"])[0]


            if (timecheck(watchlist[i]["stock"])):
                prices_update(watchlist[i]["stock"])

            print(watchlist[i])
            watchlist[i]["change"] = "{:.2%}".format(quote["change"])
    else:
         (watchlist[0]["stock"]) = ""
         return redirect("/watchlist")

    for i in range(0, len(watchlist)):
        price_lookup = db.execute("SELECT date, time, ticker, price, change, industry FROM prices")
        quote = db.execute("SELECT date, time, ticker, price, change, industry FROM prices WHERE ticker = :ticker", ticker = watchlist[i]["stock"])

        if (len(quote) == 0):
            prices_update(watchlist[i]["stock"])
            quote = db.execute("SELECT date, time, ticker, price, change, industry FROM prices WHERE ticker = :ticker", ticker = watchlist[i]["stock"])[0]

        quote = db.execute("SELECT date, time, ticker, price, change, industry FROM prices WHERE ticker = :ticker", ticker = watchlist[i]["stock"])[0]


        if (timecheck(watchlist[i]["stock"])):
            prices_update(watchlist[i]["stock"])

        watchlist[i]["change"] = "{:.2%}".format(quote["change"])
    """
    #delete the stock and return the default one
    return render_template("watchlist.html", watchlists = watchlists, watchlist = watchlist)


@app.route("/tradelog", methods = ["GET", "POST"])
@login_required
def tradelog():
    #get the user ID. if method is get, show all trades
    user_id = session["user_id"]
    if request.method == "GET":
        rows = db.execute("SELECT * FROM positions WHERE user_id = :id ORDER BY date DESC", id = session["user_id"])
        return render_template("tradelog.html", rows = rows)
        return apology("TODO")

    #if the method is post, we must calculate how the new trade will impact our positions.
    if request.method == "POST":
        mult = 1
        total = 0
        ticker = request.form.get("ticker").upper().strip()
        #check for valid stock
        if lookup(ticker) is None:
            return apology("Invalid Ticker")
        if (request.form.get("ticker") is not None and request.form.get("buysell") is not None and request.form.get("quantity") is not None and request.form.get("cost") is not None):
            if (request.form.get("buysell")) == "buy":
                mult = 1
            else:
                mult = -1
                #update positions to calculate cost basis correctly
            quantity = mult * int(request.form.get("quantity"))
            cost = float(request.form.get("cost"))
            cash = float(request.form.get("cash"))
            total = quantity * cost - cash
            db.execute("INSERT INTO positions (user_id, action, ticker, quantity, price, cash_inout, style) VALUES(?,?,?,?,?, ?,?)",  user_id, request.form.get("buysell"), ticker, quantity, cost, cash, request.form.get("style").lower().strip())
        else:
            return apology("Missing inputs")

        #update the user's cash
        user_cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]
        user_cash = user_cash - total
        db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash = user_cash, id = user_id)
        #redirect back to show all of our trades
        return redirect("/tradelog")

@app.route("/edit", methods = ["GET", "POST"])
@login_required
def edit():
    user_id = session["user_id"]
    if request.method == "GET":
        return redirect("/")
    #send us to edit.html, which will send the trade's information to guide the user
    if request.method == "POST":
        trade_id = request.form.get("Edit")
        #print(trade_id)
        rows = db.execute("SELECT * FROM positions WHERE user_id = :id AND trade_id = :trade_id", id = session["user_id"], trade_id = trade_id)
        return render_template("/edit.html", rows = rows)

@app.route("/update", methods = ["POST"])
def update():
    #select user information
    user_id = session["user_id"]
    trade_id = request.form.get("submit")
    rows = db.execute("SELECT * FROM positions WHERE user_id = :id AND trade_id = :trade_id", id = session["user_id"], trade_id = trade_id)[0]
    total = rows["quantity"]  * rows["price"] - rows["cash_inout"]

    #make sure there is sufficient information
    if (request.form.get("ticker") is not None and request.form.get("buysell") is not None and request.form.get("quantity") is not None and request.form.get("cost") is not None):
        mult = 1
        if (request.form.get("buysell")) == "buy":
            mult = 1
        else:
            mult = -1

        #update positions with new formation
        quantity2 = int(request.form.get("quantity")) * mult

        ticker2 = request.form.get("ticker").upper().strip()
        cost2 = float(request.form.get("cost"))
        cash2 = float(request.form.get("cash"))
        total2 = quantity2 * cost2 - cash2
        #we now need the difference in costs to update how much cash we now have if we changed things.
        total_difference = total2 - total

        user_cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]
        user_cash = user_cash - total_difference
        db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash = user_cash, id = user_id)

        db.execute("UPDATE positions SET action = :action2, ticker = :ticker2, quantity = :quantity2, price = :cost2, cash_inout = :cash2, style = :style WHERE trade_id = :trade_id", action2 = request.form.get("buysell"), ticker2 = ticker2, cost2 = cost2, cash2 = cash2, quantity2 = quantity2, trade_id = trade_id, style = request.form.get("style").lower())
        return redirect("/")
    else:
        return apology("Missing inputs")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted


        if not request.form.get("username"):
            return apology("must provide username", 403)

        username = request.form.get("username")
        selected_username = db.execute("SELECT username FROM users WHERE username = ?", username)

        if len(selected_username) !=0:
            return apology("User already exists", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        elif not request.form.get("port"):
            return apology("must provide password", 403)

        elif not request.form.get("confirmation"):
            return apology("must confirm password", 403)

        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords must match")

        else:
            password = generate_password_hash(request.form.get("password"))
            portfolio =  request.form.get("port")
            db.execute("INSERT INTO users(username, hash, cash) VALUES (?,?,?)", username, password, portfolio)

        return render_template("login.html")

    else:
        return render_template("register.html")
    return apology("TODO")

@app.route("/earningscalendar", methods = ["GET"])
@login_required
def earnings_calendar():

    current_date = datetime.now(pytz.timezone('US/Eastern')).date()
    current_time = datetime.now(pytz.timezone("America/New_York"))
    current_minute = str(current_time.minute)
    hour_min = int(str(current_time.hour) + current_minute)
       #creating calendar array
   #calendar = []
    #calendar.clear()
    user_id = session["user_id"]
    rows = db.execute("SELECT user_id, ticker, SUM(quantity) as quantity, SUM(price* quantity)/SUM(quantity) as costbasis FROM positions where user_id = :id GROUP BY user_id, ticker HAVING sum(quantity)<>0", id = session["user_id"])
    #calculate two weeks ago and two weeks later. will be the timeframe of our relevant earnings
    two_weeks_ago = (date.today() + relativedelta(weeks = -2)).strftime("%Y-%m-%d")
    two_weeks_later = (date.today() + relativedelta(weeks = 2)).strftime("%Y-%m-%d")

    #get the closest earnings for each stock in our portfolio
    for i in range(0, len(rows)):
        latest_ec = db.execute("SELECT * FROM earnings_calendar WHERE symbol = :symbol AND date_updated = :date_updated AND real = :real", symbol = rows[i]["ticker"], date_updated = current_date, real = "true")
        latest_ec_fill = db.execute("SELECT * FROM earnings_calendar WHERE symbol = :symbol AND date_updated = :date_updated AND real = :real", symbol = rows[i]["ticker"], date_updated = current_date, real = "false")

        if (len(latest_ec_fill) == 0 and len(latest_ec) == 0):
            ec1 = finnhub_client.earnings_calendar(_from=two_weeks_ago, to=two_weeks_later, symbol = rows[i]["ticker"])["earningsCalendar"]
            if (len(ec1) != 0):
                ec = ec1[0]
                if (ec["date"] >= two_weeks_ago and ec["date"] <= two_weeks_later):
                    db.execute("INSERT INTO earnings_calendar (date, epsactual, epsestimate, hour, quarter, revenueactual, revenueestimate, symbol, year, date_updated, real) VALUES(?,?,?,?,?,?,?,?,?,?,?)", ec["date"], ec["epsActual"], ec["epsEstimate"], ec["hour"], ec["quarter"], ec["revenueActual"], ec["revenueEstimate"], ec["symbol"], ec["year"], current_date, "true")
                else:
                    db.execute("INSERT INTO earnings_calendar (date, epsActual, epsEstimate, hour, quarter, revenueActual, revenueEstimate, symbol, year, date_updated, real) VALUES(?,?,?,?,?,?,?,?,?,?,?)", current_date, 0, 0, 0, 0,0, 0, rows[i]["ticker"], 0, current_date, "false")

                #db.execute("SELECT * FROM earnings_calendar WHERE symbol = :symbol AND date_updated = :date_updated", symbol = rows[i]["ticker"], date_updated = current_date
    prev_earnings = db.execute("SELECT DISTINCT epsactual, epsestimate, revenueestimate, revenueactual, hour, date, quarter,symbol,year FROM earnings_calendar WHERE date >= :date_two_weeks_ago AND date < :current_date AND symbol in (SELECT ticker FROM positions where user_id = :user_id GROUP BY ticker HAVING sum(quantity)<>0) AND real = :real ORDER BY date DESC", date_two_weeks_ago = two_weeks_ago, current_date = current_date, user_id = user_id, real = "true")
    for i in range(0, len(prev_earnings)):
        if prev_earnings[i]["epsestimate"] != 0 and prev_earnings[i]["epsestimate"]  is not None and prev_earnings[i]["epsactual"] is not None:
            prev_earnings[i]["epsbeat"] = "{:.2%}".format(prev_earnings[i]["epsactual"]/prev_earnings[i]["epsestimate"]-1)
        else:
            prev_earnings[i]["epsbeat"] = 0
        if prev_earnings[i]["revenueestimate"] != 0 and prev_earnings[i]["revenueestimate"] is not None and prev_earnings[i]["revenueactual"] is not None:
            prev_earnings[i]["revenuebeat"] = "{:.2%}".format(prev_earnings[i]["revenueactual"]/prev_earnings[i]["revenueestimate"]-1)
        else:
            prev_earnings[i]["epsbeat"] = 0
        if prev_earnings[i]["epsactual"] is not None:
            prev_earnings[i]["epsactual"] = usd(prev_earnings[i]["epsactual"])
        else:
            prev_earnings[i]["epsactual"] = 0
        if prev_earnings[i]["epsestimate"] is not None:
            prev_earnings[i]["epsestimate"] = usd(prev_earnings[i]["epsestimate"] )
        else:
            prev_earnings[i]["epsestimate"] = 0
        if prev_earnings[i]["revenueestimate"] != 0 and prev_earnings[i]["revenueestimate"] is not None:
            prev_earnings[i]["revenueestimate"] = "$" + millify(prev_earnings[i]["revenueestimate"], precision = 2)
        if prev_earnings[i]["revenueactual"] != 0 and prev_earnings[i]["revenueactual"] is not None:
            prev_earnings[i]["revenueactual"] = "$" + millify(prev_earnings[i]["revenueactual"], precision = 2)
        if prev_earnings[i]["hour"] == "bmo":
            prev_earnings[i]["hour"] = "Pre Market"
        if prev_earnings[i]["hour"] == "amc":
            prev_earnings[i]["hour"] = "After Market"
#same as previous earnings
    future_earnings = db.execute("SELECT DISTINCT epsactual, epsestimate, revenueestimate, revenueactual, hour, date, quarter,symbol,year FROM earnings_calendar WHERE date >= :current_date AND date < :two_weeks_later AND symbol in (SELECT ticker FROM positions where user_id = :user_id GROUP BY ticker HAVING sum(quantity)<>0) AND real = :real ORDER BY date ASC", two_weeks_later = two_weeks_later, current_date = current_date, user_id = user_id, real = "true")
    for i in range(0, len(future_earnings)):
        if future_earnings[i]["epsestimate"] != 0 and future_earnings[i]["epsestimate"] is not None:
            future_earnings[i]["epsestimate"] = usd(future_earnings[i]["epsestimate"])
        if future_earnings[i]["revenueestimate"] != 0 and future_earnings[i]["revenueestimate"] is not None:
            future_earnings[i]["revenueestimate"] = "$" + millify(future_earnings[i]["revenueestimate"], precision = 2)
        if future_earnings[i]["hour"] == "bmo":
            future_earnings[i]["hour"] = "Pre Market"
        if future_earnings[i]["hour"] == "amc":
            future_earnings[i]["hour"] = "After Market"

    return render_template("earnings.html", prev_earnings = prev_earnings, future_earnings = future_earnings)
    #print("EARNS: ", future_earnings);
    #print("Prev: ", prev_earnings);

@app.route("/stock", methods = ["GET", "POST"])
@login_required
def stock():
    if request.method == "GET":

        #if the method is get, just return a method to search for stocks
        method = "GET"
        return render_template("stock_search.html", method = method)

    #else, we can scrape information about the stock
    if request.method == "POST":
        method = "POST"
        ticker = request.form.get("stock-index").upper().strip()

        #tradingview chart URL
        url_passin = "https://www.tradingview.com/symbols/" + ticker + "/"
        news = news_lookup(ticker)
        profile = company_profile(ticker)
        industry =""
        sa_url_passin = ""
        ms_url_passin = ""
        wsj_url_passin = ""
        url = ""

        #print(profile)
        if profile is not None:
            industry = profile["industry"]
        else:
            industry = "misc."

        #get some information about the stocks
        financials = finnhub_client.company_basic_financials(ticker, 'all')['metric']
        #target_price = finnhub_client.price_target(ticker)
        comps = finnhub_client.company_peers(ticker)
        quote = finnhub_client.quote(ticker)
        #print(financials)

        if (financials is not None and profile is not None and quote is not None):
        #image = profile["logo"]
            industry = profile["industry"]
            url = profile["url"]
            ms_exchange = "xnys"
            if (profile["exchange"] == "NASDAQ NMS - GLOBAL MARKET"):
                ms_exchange = "xnas"
            #print(ms_exchange)
            sa_url_passin = "https://seekingalpha.com/symbol/" + ticker
            ms_url_passin = "https://www.morningstar.com/stocks/" + ms_exchange + "/" + ticker + "/quote"
            wsj_url_passin = "https://finance.yahoo.com/quote/"+ticker

            # Profile
            profile = finnhub_client.company_profile2(symbol=ticker)
            # Quote
            # Basic Financials
            financials = finnhub_client.company_basic_financials(ticker, 'all')['metric']
            # Target
            #target_price = finnhub_client.price_target(ticker)
            #print(target_price)
            # Convert financials to
            str_financials = {
                "fiveTwoHigh": financials['52WeekHigh'],
                "fiveTwoLow": financials['52WeekLow'],
                "tenDayAvgVol": financials['10DayAverageTradingVolume'],
                "debtToEquity": financials['totalDebt/totalEquityQuarterly']
            }
            financials.update(str_financials)
        else:
            quote = []
            quote.clear()

        return render_template("stock.html", ticker = ticker.upper(), url_passin = url_passin,method = method, news = news, industry = industry, url = url, sa_url_passin=sa_url_passin, ms_url_passin = ms_url_passin, wsj_url_passin = wsj_url_passin, profile=profile, quote=quote, financials = financials, comps = comps)

@app.route("/markets", methods=["GET", "POST"])
@login_required
def markets():
    #finnhub_client.company_basic_financials('TSLA', 'all')['metric']['52WeekHigh']
    #return markets.html
    news = finnhub_client.general_news("general")
    #pass in finnhub news
    for i in range(0, len(news)):
        news[i]["date"] = datetime.utcfromtimestamp(news[i]["datetime"]).strftime('%m-%d-%Y')
    return render_template("markets.html",news = news)

@app.route("/documentation", methods=["GET", "POST"])
@login_required
def documentation():
    #return documentation page. nothign to pass in here
    return render_template("documentation.html")

@app.route("/comps", methods=["GET", "POST"])
@login_required
def comps():

    current_date = datetime.now(pytz.timezone('US/Eastern')).date()
    current_time = datetime.now(pytz.timezone("America/New_York"))
    current_minute = str(current_time.minute)
    hour_min = int(str(current_time.hour) + current_minute)

    user_id = session["user_id"]

    if request.method == "GET":
        return render_template("comps_search.html")

    if request.method == "POST":
        ticker = request.form.get("comp_ticker").strip().upper()
        financials1 = finnhub_client.company_basic_financials(ticker, 'all')['metric']
        financials2 = finnhub_client.company_profile2(symbol = ticker)

        if lookup(ticker) is None:
            return apology("Unsupported Ticker", 400)
        if financials1 is None:
            return apology("Unsupported Ticker", 400)
        if len(financials1) == 0:
            return apology("Unsupported Ticker", 400)

        existing_comps = db.execute("SELECT * FROM comps_tickers WHERE user_id = :user_id AND ticker = :ticker", user_id = user_id, ticker = ticker)

        if (len(existing_comps) == 0):
            fh_comps = finnhub_client.company_peers(ticker)
            if ticker not in fh_comps:
                fh_comps.append(ticker)
            for comp in fh_comps:
                comp_financials = financials_update(comp)
                if len(comp_financials) != 0:
                    db.execute("INSERT INTO comps_tickers (user_id, ticker, comp) VALUES (?,?,?)", user_id, ticker, comp)
                    existing_comps_table = db.execute("SELECT * FROM company_financials WHERE ticker = :ticker AND updated = :updated", ticker = comp, updated = current_date)
                    if len(existing_comps_table) == 0:
                        db.execute("INSERT INTO company_financials (ticker, evsales, evebitda, revgrowththree, revgrowthttm, epsgrowththree, operatingmarginttm, roettm, debtequity, roi, netmargin, marketcap, netdebt, shares, updated, ev, beta, peratio, grossmargin) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", comp, comp_financials["evsales"], comp_financials["evebitda"], comp_financials["revgrowththree"], comp_financials["revgrowthttm"], comp_financials["epsgrowththree"], comp_financials["operatingmarginttm"],comp_financials["roettm"], comp_financials["debttoequity"],comp_financials["roi"],comp_financials["netmargin"], comp_financials["marketcap"], comp_financials["netdebt"], comp_financials["shares"], current_date, comp_financials["ev"], comp_financials["beta"], comp_financials["peratio"], comp_financials["grossmargin"])


        for i in range(0, len(existing_comps)):
            comp_ticker = existing_comps[i]["comp"]
            ct_financials = db.execute("SELECT * FROM company_financials WHERE ticker = :ticker AND updated = :current_date", ticker = comp_ticker, current_date = current_date)
            if len(ct_financials) == 0:

                comp_financials = financials_update(comp_ticker)
                updated = current_date

                if len(comp_financials) != 0:
                    db.execute("INSERT INTO company_financials (ticker, evsales, evebitda, revgrowththree, revgrowthttm, epsgrowththree, operatingmarginttm, roettm, debtequity, roi, netmargin, marketcap, netdebt, shares, updated, ev, beta, peratio, grossmargin) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", comp_ticker, comp_financials["evsales"], comp_financials["evebitda"], comp_financials["revgrowththree"], comp_financials["revgrowthttm"], comp_financials["epsgrowththree"], comp_financials["operatingmarginttm"],comp_financials["roettm"], comp_financials["debttoequity"],comp_financials["roi"],comp_financials["netmargin"], comp_financials["marketcap"], comp_financials["netdebt"], comp_financials["shares"], current_date, comp_financials["ev"], comp_financials["beta"], comp_financials["peratio"], comp_financials["grossmargin"])

        comps = db.execute("SELECT * FROM comps_tickers JOIN company_financials ON comps_tickers.comp = company_financials.ticker WHERE comps_tickers.ticker = :ticker AND comps_tickers.user_id = :user_id AND updated = :current_date", ticker = ticker, user_id = user_id, current_date = current_date)
        return render_template("comps.html", comps = comps, parent_ticker = ticker)

@app.route("/addstockcomps", methods=["GET", "POST"])
@login_required
def addstockcomps():
    current_date = datetime.now(pytz.timezone('US/Eastern')).date()
    user_id = session["user_id"]

    if request.method == "GET":
        return render_template("comps_search.html")

    if request.method == "POST":
        ticker = request.form.get("stock").strip().upper()
        parent_ticker = request.form.get("parent_ticker").strip().upper()
        add_financials = financials_update(ticker)

        if (len(add_financials) == 0):
            return apology("Ticker not found", 404)

        current_financials = db.execute("SELECT * FROM company_financials WHERE ticker = :ticker AND updated = :current_date", ticker = ticker, current_date = current_date)
        current_comps = db.execute("SELECT * FROM comps_tickers WHERE user_id = :user_id AND ticker = :parent_ticker AND comp = :ticker", user_id = user_id, parent_ticker = parent_ticker, ticker = ticker)

        if (len(current_comps) > 0):
            return apology("Comp already exists", 404)
        else:
            db.execute("INSERT INTO comps_tickers (user_id, ticker, comp) VALUES (?,?,?)", user_id, parent_ticker, ticker)

        if len(current_financials) == 0:
            comp_financials = financials_update(ticker)
            updated = current_date

            db.execute("INSERT INTO company_financials (ticker, evsales, evebitda, revgrowththree, revgrowthttm, epsgrowththree, operatingmarginttm, roettm, debtequity, roi, netmargin, marketcap, netdebt, shares, updated, ev, beta, peratio, grossmargin) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ticker, comp_financials["evsales"], comp_financials["evebitda"], comp_financials["revgrowththree"], comp_financials["revgrowthttm"], comp_financials["epsgrowththree"], comp_financials["operatingmarginttm"],comp_financials["roettm"], comp_financials["debttoequity"],comp_financials["roi"],comp_financials["netmargin"], comp_financials["marketcap"], comp_financials["netdebt"], comp_financials["shares"], current_date, comp_financials["ev"], comp_financials["beta"], comp_financials["peratio"], comp_financials["grossmargin"])

        comps = db.execute("SELECT * FROM comps_tickers JOIN company_financials ON comps_tickers.comp = company_financials.ticker WHERE comps_tickers.ticker = :parent_ticker AND comps_tickers.user_id = :user_id AND updated = :current_date", parent_ticker = parent_ticker, user_id = user_id,current_date = current_date)
        return render_template("comps.html", comps = comps, parent_ticker = parent_ticker)

@app.route("/delstockcomps", methods=["POST"])
@login_required
def delstockcomps():
    current_date = datetime.now(pytz.timezone('US/Eastern')).date()
    user_id = session["user_id"]

    if request.method == "POST":
        ticker = request.form.get("stock").strip().upper()
        parent_ticker = request.form.get("parent_ticker").strip().upper()

        if ticker == parent_ticker:
            return apology("Cannot delete parent ticker", 404)

        db.execute("DELETE FROM comps_tickers WHERE user_id = :user_id AND ticker = :parent_ticker AND comp = :ticker", user_id = user_id, parent_ticker = parent_ticker, ticker = ticker)

        comps = db.execute("SELECT * FROM comps_tickers JOIN company_financials ON comps_tickers.comp = company_financials.ticker WHERE comps_tickers.ticker = :parent_ticker AND comps_tickers.user_id = :user_id AND updated = :current_date", parent_ticker = parent_ticker, user_id = user_id, current_date = current_date)
        return render_template("comps.html", comps = comps, parent_ticker = parent_ticker,current_date = current_date)

@app.route("/downloadcomps", methods=["POST"])
@login_required
def downloadcomps():
    current_date = datetime.now(pytz.timezone('US/Eastern')).date()
    user_id = session["user_id"]

    if request.method == "POST":
        parent_ticker = request.form.get("parent_ticker").strip().upper()

        comps_dl = db.execute("SELECT comps_tickers.comp, company_financials.marketcap, company_financials.ev, company_financials.evsales, company_financials.evebitda, company_financials.peratio, company_financials.revgrowththree, company_financials.revgrowthttm, company_financials.epsgrowththree, company_financials.grossmargin, company_financials.operatingmarginttm,  company_financials.netmargin, company_financials.roettm, company_financials.roi, company_financials.debtequity FROM comps_tickers JOIN company_financials ON comps_tickers.comp = company_financials.ticker  WHERE comps_tickers.ticker = :parent_ticker AND comps_tickers.user_id = :user_id AND updated = :current_date",current_date = current_date, parent_ticker = parent_ticker, user_id = user_id)
        comps_dl_keys =  comps_dl[0].keys()

        comps = db.execute("SELECT DISTINCT * FROM comps_tickers JOIN company_financials ON comps_tickers.comp = company_financials.ticker WHERE comps_tickers.ticker = :parent_ticker AND comps_tickers.user_id = :user_id AND updated = :current_date", parent_ticker = parent_ticker, user_id = user_id, current_date = current_date)

        print(comps)

        filename = parent_ticker + "_comps.csv"

        with open("file.csv", 'w', newline='') as f:
            #for row in comps_dl:
            writer = csv.DictWriter(f, comps_dl_keys)
            writer.writeheader()
            writer.writerows(comps_dl)

        return send_file('file.csv',
                     mimetype='text/csv',
                     attachment_filename=filename,
                     as_attachment=True)
        return render_template("comps.html", comps = comps, parent_ticker = parent_ticker)

@app.route("/performance", methods=["GET", "POST"])
@login_required
def performance():
    user_id = session["user_id"]
    rows = db.execute("SELECT date, portfolio FROM performance WHERE user_id = :user_id ORDER BY date DESC", user_id = user_id)
    for i in range(0, len(rows)):
        rows[i]["portfolio"] = round(rows[i]["portfolio"],2)
    return render_template("performance.html", rows = rows)

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

if __name__ == "__main__":
 port = int(os.environ.get("PORT", 8080))
 app.run(host="0.0.0.0", port=port)

