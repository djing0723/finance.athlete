import os

from cs50 import SQL
import finnhub
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import json
from datetime import date, datetime
import pytz

from helpers import apology, login_required, lookup, news_lookup, usd, company_profile

# Configure application
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
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY_IEX"):
    raise RuntimeError("API_KEY_IEX not set")
if not os.environ.get("API_KEY_FINNHUB"):
    raise RuntimeError("API_KEY_FINNHUB not set")

# Set up finnhub client
print(os.getenv("API_KEY_FINNHUB"))
finnhub_client = finnhub.Client(api_key=os.getenv("API_KEY_FINNHUB"))

@app.route("/")
@login_required
def index():

    user_id = session["user_id"]
    rows = db.execute("SELECT user_id, ticker, SUM(quantity) as quantity, SUM(price* quantity)/SUM(quantity) as CostBasis FROM positions where user_id = :id GROUP BY user_id, ticker HAVING sum(quantity)<>0", id = session["user_id"])
    user_cash = round(db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"],2)

    """create a SQL database to update stock prices 3 times a day. This way, we don't have to keep on calling the API, saving us API calls and page load time"""

    """get the dates"""
    current_date = date.today().strftime('%Y-%m-%d')
    current_time = datetime.now(pytz.timezone("America/New_York"))
    current_minute = str(current_time.minute)
    hour_min = int(str(current_time.hour) + current_minute)
    time_to_display = str(current_time.hour) + ":" + current_minute
    if (current_time.minute < 10):
        current_minute = str(0) + str(current_time.minute)
        hour_min = int(str(current_time.hour) + current_minute)
        time_to_display = str(current_time.hour) + ":" + current_minute


    """price_rows = db.execute("SELECT date, time, ticker, price, change, industry FROM prices")
    if len(price_rows) == 0:
        for i in range(0, len(rows)):
            quote = lookup(rows[i]["ticker"])
            profile = company_profile(rows[i]["ticker"])
            if profile is not None:
                rows[i]["industry"] = profile["industry"]
            else:
                rows[i]["industry"] = "ADR"
            price = quote["price"]
            change = quote["change"]
            db.execute("INSERT INTO prices (date, time, ticker, price, industry, change) VALUES(?,?,?,?,?, ?, ?)", current_date, hour_min, rows[i]["ticker"], price, profile["industry"], change)"""

    price_rows = db.execute("SELECT date, time, ticker, price, change, industry FROM prices")
    price_rows_tickers = []
    price_rows_tickers.clear()

    rows_tickers = []
    rows_tickers.clear()

    for i in range(0, len(price_rows)):
        price_rows_tickers.append(price_rows[i]["ticker"])

    for i in range(0, len(rows)):
        rows_tickers.append(rows[i]["ticker"])

    for ticker in rows_tickers:
        if ticker not in price_rows_tickers:
            quote = lookup(ticker)
            profile = company_profile(ticker)
            industry = ""
            if profile is not None:
                industry = profile["industry"]
            else:
                industry = "ADR"
            price = quote["price"]
            change = quote["change"]
            db.execute("INSERT INTO prices (date, time, ticker, price, industry, change) VALUES(?,?,?,?, ?, ?)",  current_date, hour_min, ticker, price, industry, change)

    price_rows = db.execute("SELECT date, time, ticker, price, change, industry FROM prices")
    print(price_rows)

    day = datetime.today().weekday()
    if (day >= 0 and day <= 5):
        print("hello world")

    rows2 = []
    rows2.clear()
    rows2.append(["Company", "Amount"])

    rows3 = []
    rows3.clear()
    rows3.append(["Industry", "Amount"])

    industry_list = []
    industry_list.clear()

    spy_pct_string = "0%"
    qqq_pct_string = "0%"

    if len(rows)!=0:
        user_equity = 0

        for i in range(0, len(rows)):
            price_lookup = db.execute("SELECT date, time, ticker, price, change, industry FROM prices")
            quote = db.execute("SELECT date, time, ticker, price, change, industry FROM prices WHERE ticker = :ticker", ticker = rows[i]["ticker"])[0]
            if (len(quote) == 0):
                quote = lookup(rows[i]["ticker"])
            if (quote["date"] != current_date):
                quote = lookup(rows[i]["ticker"])
                price = quote["price"]
                change = quote["change"]

                profile = company_profile(rows[i]["ticker"])
                industry = ""
                if profile is not None:
                    industry = profile["industry"]
                else:
                    industry = "ADR"
                db.execute("UPDATE prices SET date = :date, time = :time, price = :price, industry = :industry, change = :change WHERE ticker = :ticker", date = current_date, time = hour_min, price = price, industry = industry, change = change, ticker = rows[i]["ticker"])
                spy_pct_string = "{:.2%}".format(float(lookup("spy")["change"]))
                qqq_pct_string = "{:.2%}".format(float(lookup("qqq")["change"]))

            elif (quote["date"] == current_date and hour_min >= 1230 and hour_min < 1530 and quote["time"] < 1230):
                quote = lookup(rows[i]["ticker"])
                price = quote["price"]
                change = quote["change"]

                profile = company_profile(rows[i]["ticker"])
                industry = ""
                if profile is not None:
                    industry = profile["industry"]
                else:
                    industry = "ADR"
                db.execute("UPDATE prices SET date = :date, time = :time, price = :price, industry = :industry, change = :change WHERE ticker = :ticker", date = current_date, time = hour_min, price = price, industry = industry, change = change, ticker = rows[i]["ticker"])
                spy_pct_string = "{:.2%}".format(float(lookup("spy")["change"]))
                qqq_pct_string = "{:.2%}".format(float(lookup("qqq")["change"]))
            elif (quote["date"] == current_date and hour_min >= 1530 and hour_min < 1630 and quote["time"] < 1530):
                quote = lookup(rows[i]["ticker"])
                price = quote["price"]
                change = quote["change"]

                profile = company_profile(rows[i]["ticker"])
                industry = ""
                if profile is not None:
                    industry = profile["industry"]
                else:
                    industry = "ADR"
                db.execute("UPDATE prices SET date = :date, time = :time, price = :price, industry = :industry, change = :change WHERE ticker = :ticker", date = current_date, time = hour_min, price = price, industry = industry, change = change, ticker = rows[i]["ticker"])
                spy_pct_string = "{:.2%}".format(float(lookup("spy")["change"]))
                qqq_pct_string = "{:.2%}".format(float(lookup("qqq")["change"]))
            elif (quote["date"] == current_date and hour_min >= 1630 and quote["time"] < 1630):
                quote = lookup(rows[i]["ticker"])
                price = quote["price"]
                change = quote["change"]

                profile = company_profile(rows[i]["ticker"])
                industry = ""
                if profile is not None:
                    industry = profile["industry"]
                else:
                    industry = "ADR"
                db.execute("UPDATE prices SET date = :date, time = :time, price = :price, industry = :industry, change = :change WHERE ticker = :ticker", date = current_date, time = hour_min, price = price, industry = industry, change = change, ticker = rows[i]["ticker"])
                spy_pct_string = "{:.2%}".format(float(lookup("spy")["change"]))
                qqq_pct_string = "{:.2%}".format(float(lookup("qqq")["change"]))

            quote = db.execute("SELECT date, time, ticker, price, change, industry FROM prices WHERE ticker = :ticker", ticker = rows[i]["ticker"])[0]
            #todo. if date is not a weekday on price update, check if last update was friday close. if not, update it
            #todo. if date is a weekday and we are in market hours, check if it has the latest time update.
            #todo. if date is a weekday and we are at close, update to the latest price if it is not there already
            """quote = lookup(rows[i]["ticker"])
            profile = company_profile(rows[i]["ticker"])
            if profile is not None:
                rows[i]["industry"] = profile["industry"]
            else:
                rows[i]["industry"] = "ADR"""

            rows[i]["industry"] = quote["industry"]
            rows[i]["price"] = quote["price"]
            rows[i]["CostBasis"] = rows[i]["CostBasis"]
            rows[i]["change"] = quote["change"]
            return_number = (rows[i]["price"]/rows[i]["CostBasis"])-1
            price_total = rows[i]["quantity"]*rows[i]["price"]

            rows2.append([quote["ticker"], price_total])

            if (rows[i]["industry"] not in industry_list):
                industry_list.append(rows[i]["industry"])
                rows3.append([rows[i]["industry"], 0])

            user_equity += price_total
            cost_total = rows[i]["quantity"]*rows[i]["CostBasis"]

            rows[i]["pctchange"] = "{:.2%}".format(float(quote["change"]))
            rows[i]["totalreturn_usd"] = usd(price_total - cost_total)
            rows[i]["total_usd"] = usd(round(rows[i]["quantity"]*rows[i]["price"],2))
            rows[i]["price_usd"] = usd(quote["price"])
            rows[i]["CostBasis"] = usd(round(rows[i]["CostBasis"],2))

            rows[i]["return"] = "{:.2%}".format(return_number)

        total = user_cash + user_equity

        overall_pct = 0

        for i in range(0, len(rows)):
            rows[i]["portfolio_percentage"] = "{:.2%}".format(rows[i]["price"] * rows[i]["quantity"] / total)
            overall_pct += (float(rows[i]["change"]) * (rows[i]["quantity"] * rows[i]["price"]))/total
            for j in range(0, len(rows3)):
                industry = rows3[j][0]
                if industry == rows[i]["industry"]:
                    rows3[j][1] += (rows[i]["quantity"] * rows[i]["price"])

        print(rows3)

        overall_pct_string = "{:.2%}".format(overall_pct)


    else:
        user_equity = 0
        total = user_cash
        rows = []
        rows2 = []
        overall_pct_string = "0%"

    return render_template("index.html", rows = rows, rows2 = rows2, rows3 = rows3, user_cash = usd(user_cash), user_equity = usd(user_equity), total = usd(total), overall_pct = overall_pct_string, spy_pct_string = spy_pct_string, qqq_pct_string = qqq_pct_string, time_to_display= time_to_display)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():

    if request.method == "GET":
        return render_template("buy.html")
    else:
        ticker = request.form.get("ticker")
        quantity = int(request.form.get("quantity"))
        price = 0

        if lookup(ticker) is not None:
            price = lookup(ticker)["price"]
        else:
            return apology("Invalid Ticker", 403)

        total = quantity * price
        user_id = session["user_id"]
        user_cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]

        if total>user_cash:
            return apology("You spent too much", 403)
        else:
            user_cash = user_cash - total
            action = "buy"
            db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash = user_cash, id = user_id)
            db.execute("INSERT INTO positions (user_id, action, ticker, quantity, price) VALUES(?,?,?,?,?)",  user_id, action, ticker, quantity, price)
        return redirect("/")

@app.route("/tradelog", methods = ["GET", "POST"])
@login_required
def tradelog():
    user_id = session["user_id"]
    if request.method == "GET":
        rows = db.execute("SELECT * FROM positions WHERE user_id = :id", id = session["user_id"])
        return render_template("tradelog.html", rows = reversed(rows))
        return apology("TODO")
    if request.method == "POST":
        mult = 1
        total = 0
        ticker = request.form.get("ticker")
        if lookup(ticker) is None:
            return apology("Invalid Ticker")
        if (request.form.get("ticker") is not None and request.form.get("buysell") is not None and request.form.get("quantity") is not None and request.form.get("cost") is not None):
            if (request.form.get("buysell")) == "buy":
                mult = 1
            else:
                mult = -1
            quantity = mult * int(request.form.get("quantity"))
            cost = float(request.form.get("cost"))
            cash = float(request.form.get("cash"))
            total = quantity * cost - cash
            db.execute("INSERT INTO positions (user_id, action, ticker, quantity, price, cash_inout) VALUES(?,?,?,?,?, ?)",  user_id, request.form.get("buysell"), ticker, quantity, cost, cash)
        else:
            return apology("Missing inputs")

        user_cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]
        user_cash = user_cash - total
        db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash = user_cash, id = user_id)
        return redirect("/tradelog")

@app.route("/edit", methods = ["GET", "POST"])
@login_required
def edit():
    user_id = session["user_id"]
    if request.method == "GET":
        return redirect("/")
    if request.method == "POST":
        trade_id = request.form.get("Edit")
        print(trade_id)
        rows = db.execute("SELECT * FROM positions WHERE user_id = :id AND trade_id = :trade_id", id = session["user_id"], trade_id = trade_id)
        return render_template("/edit.html", rows = rows)

@app.route("/update", methods = ["POST"])
def update():
    user_id = session["user_id"]
    trade_id = request.form.get("submit")
    rows = db.execute("SELECT * FROM positions WHERE user_id = :id AND trade_id = :trade_id", id = session["user_id"], trade_id = trade_id)[0]
    total = rows["quantity"]  * rows["price"] - rows["cash_inout"]

    if (request.form.get("ticker") is not None and request.form.get("buysell") is not None and request.form.get("quantity") is not None and request.form.get("cost") is not None):
        mult = 1
        if (request.form.get("buysell")) == "buy":
            mult = 1
        else:
            mult = -1

        quantity2 = int(request.form.get("quantity")) * mult

        ticker2 = request.form.get("ticker")
        cost2 = float(request.form.get("cost"))
        cash2 = float(request.form.get("cash"))
        total2 = quantity2 * cost2 - cash2
        total_difference = total2 - total

        user_cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]
        user_cash = user_cash - total_difference
        db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash = user_cash, id = user_id)

        db.execute("UPDATE positions SET action = :action2, ticker = :ticker2, quantity = :quantity2, price = :cost2, cash_inout = :cash2 WHERE trade_id = :trade_id", action2 = request.form.get("buysell"), ticker2 = ticker2, cost2 = cost2, cash2 = cash2, quantity2 = quantity2, trade_id = trade_id)
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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    ticker = request.form.get("ticker")

    if request.method == "GET":
        return render_template("quote.html")

    if request.method == "POST":
        if lookup(ticker) is not None:
            price = usd(lookup(ticker)["price"])
        else:
            return apology("Invalid Ticker", 403)
        return render_template("quote.html", ticker = ticker, price = price)

    return apology("TODO")


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

        elif not request.form.get("confirmation"):
            return apology("must confirm password", 403)

        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords must match")

        else:
            password = generate_password_hash(request.form.get("password"))
            db.execute("INSERT INTO users(username, hash) VALUES (?,?)", username, password)

        return render_template("login.html")

    else:
        return render_template("register.html")
    return apology("TODO")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    rows = db.execute("SELECT user_id, ticker, SUM(quantity) as quantity, SUM(price* quantity)/SUM(quantity) as CostBasis FROM positions where user_id = :id GROUP BY user_id, ticker HAVING sum(quantity)<>0", id = session["user_id"])

    if request.method == "POST":

        if not request.form.get("quantity"):
            return apology("must provide quantity", 403)

        ticker = request.form.get("ticker")
        price = lookup(ticker)["price"]
        current_quantity = int(db.execute("SELECT SUM(quantity) as quantity FROM positions where user_id = :id AND ticker = :ticker GROUP BY user_id, ticker", id = session["user_id"], ticker = ticker)[0]["quantity"])
        if len(db.execute("SELECT SUM(quantity) as quantity FROM positions where user_id = :id AND ticker = :ticker GROUP BY user_id, ticker", id = session["user_id"], ticker = ticker)) == 0:
            return apology("You do not own that stock")
        quantity = -1*int(request.form.get("quantity"))

        if (-1*quantity) > current_quantity:
            return apology("not enough stock", 403)

        user_id = session["user_id"]
        action = 'sell'
        total = -1*quantity * price
        user_cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]+total
        db.execute("INSERT INTO positions (user_id, action, ticker, quantity, price) VALUES(?,?,?,?,?)",  user_id, action, ticker, quantity, price)
        db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash = user_cash, id = user_id)
        return redirect("/")

    return render_template("sell.html", rows = rows)

@app.route("/stock", methods = ["GET", "POST"])
@login_required
def stock():
    if request.method == "GET":
        method = "GET"
        return render_template("stock_search.html", method = method)
    if request.method == "POST":
        method = "POST"
        ticker = request.form.get("stock-index")

        url_passin = "https://www.tradingview.com/symbols/" + ticker + "/"
        news = news_lookup(ticker)
        profile = company_profile(ticker)
        industry =""
        sa_url_passin = ""
        ms_url_passin = ""
        wsj_url_passin = ""
        url = ""
        if profile is not None:
            industry = profile["industry"]
        else:
            industry = "ADR"


        if (profile is not None):
        #image = profile["logo"]
            industry = profile["industry"]
            url = profile["url"]
            ms_exchange = "xnys"
            if (profile["exchange"] == "NASDAQ NMS - GLOBAL MARKET"):
                ms_exchange = "xnas"
            print(ms_exchange)
            sa_url_passin = "https://seekingalpha.com/symbol/" + ticker
            ms_url_passin = "https://www.morningstar.com/stocks/" + ms_exchange + "/" + ticker + "/quote"
            wsj_url_passin = "https://www.wsj.com/market-data/quotes/"+ticker+"?mod=searchresults_companyquotes"

            profile = finnhub_client.company_profile2(symbol='AAPL')
            """Quote"""
            quote = finnhub_client.quote('AAPL')
            """Basic financials"""
            financials = requests.get('https://finnhub.io/api/v1/stock/metric?symbol=AAPL&metric=all&token=buuru5f48v6rf2qob8p0')
            print(financials.json())

    return render_template("stock.html", ticker = ticker, url_passin = url_passin,method = method, news = news, industry = industry, url = url, sa_url_passin=sa_url_passin, ms_url_passin = ms_url_passin, wsj_url_passin = wsj_url_passin, financials = comp_financials, profile=profile, quote=quote, financicals=financials)

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

