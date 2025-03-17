from flask import Flask, render_template, request
import yfinance as yf

app = Flask(__name__)

# To run the program, open the terminal and enter: python app.py runserver
#   YFRateLimitError? Try updating yfinance: pip install --upgrade yfinance


# Returns the risk-free rate (decimal) based on the U.S. 10-Year Treasury Yield (r_f)
def get_risk_free_rate():
    try:
        treasury = yf.Ticker("^TNX")  # Ticker for the 10-Year Treasury Yield
        rf = treasury.info.get("regularMarketPrice", treasury.info.get("regularMarketPreviousClose", None))  # Uses regularMarketPreviousClose as a fallback in the case of market closures
        return rf / 100 if rf else None  # Convert percentage to decimal (.0418 returned would represent 4.18% yield)
    except Exception as e:
        print(f"Error fetching risk-free rate: {e}")
        return None


# Returns an estimate of the market return using historical S&P 500 data.
def get_market_return():
    try:
        sp500 = yf.Ticker("^GSPC")
        decadeData = sp500.history(period="10y")  # Gets 10 years of sp500 data
        if decadeData.empty or "Close" not in decadeData:
            return None

        annual_close = decadeData["Close"].resample('YE').last()  # Resamples daily prices to get yearly closing prices
        if annual_close.empty or len(annual_close) < 2:
            return None  # Not enough data to compute returns

        annual_returns = annual_close.pct_change().dropna()  # Calculates yearly returns
        if annual_returns.empty:
            return None  # Avoid division by zero

        market_return = (1 + annual_returns).prod() ** (1 / len(annual_returns)) - 1  # Geometric mean
        return market_return  # .11017 returned would represent 11.02% market return
    except Exception as e:
        print(f"Error fetching market return: {e}")
        return None


# Returns constant growth rate in perpetuity expected for the dividends (g)
def get_constant_growth_rate(dividends):
    try:
        if dividends is None or dividends.empty:
            return None

        annual_dividend = dividends.resample('YE').sum()  # total annual dividend

        if len(annual_dividend) < 2:
            return None  # Not enough data to compute growth

        annual_dividend_growth_rate = annual_dividend.pct_change().dropna()  # dividend growth rate for each year
        if annual_dividend_growth_rate.empty:
            return None  # Avoid division by zero

        geometric_mean_dividend_growth_rate = (annual_dividend_growth_rate + 1).prod() ** (1 / len(annual_dividend_growth_rate)) - 1  # geometric mean to account for compounding data

        return geometric_mean_dividend_growth_rate  # (g)
    except Exception as e:
        print(f"Error computing growth rate: {e}")
        return None


# Returns the estimated dividend for next year
def get_D1(info, dividends):
    try:
        D0 = info.get("dividendRate", None)
        if D0 is None or D0 <= 0:
            return None  # Avoid calculations with missing or invalid dividendRate

        # D0 = dividends.tail(4).sum()  # Quarterly dividends (sum last 4). dividendRate might not reflect recent changes (e.g., a dividend cut).
        g = get_constant_growth_rate(dividends)

        if g is None:
            return None

        D1 = D0 * (1 + g)
        return D1
    except Exception as e:
        print(f"Error computing D1: {e}")
        return None


# Returns the company's cost of capital equity (r) using the Capital Asset Pricing Model (CAPM)
def get_cost_of_equity(beta):
    try:
        rf = get_risk_free_rate()
        rm = get_market_return()

        if beta is None or rf is None or rm is None:
            return None

        cost_of_equity = rf + beta * (rm - rf)
        return cost_of_equity
    except Exception as e:
        print(f"Error computing cost of equity: {e}")
        return None


# # Gordon Growth Model - Variant of the Dividend Discount Model (DDM), assumes a stable dividend growth rate (g).
# # Returns the fair value of a dividend-paying stock, assuming a stable dividend growth rate (g).
# def get_GGM(stock):
#     info = stock.info
#     dividends = stock.dividends  # historical dividends
#     beta = info.get("beta")

#     D1 = get_D1(info, dividends)  # Value of dividends at the end of the first period
#     r = get_cost_of_equity(beta)  # Constant cost of equity capital for the company
#     g = get_constant_growth_rate(dividends)  # Constant growth rate in perpetuity expected for the dividends

#     if dividends.empty or D1 is None or r is None or g is None or r <= g:
#         return None

#     fairValue = D1 / (r - g)
#     return fairValue


# Extended function to compute the GGM with debug information.
def get_GGM_debug(stock):
    debug = {}
    info = stock.info
    dividends = stock.dividends  # Historical dividends
    beta = info.get("beta")

    try:
        # Compute intermediate variables
        D1 = get_D1(info, dividends)
        r = get_cost_of_equity(beta)
        g = get_constant_growth_rate(dividends)
        risk_free_rate = get_risk_free_rate()
        market_return = get_market_return()

        debug["D1"] = D1
        debug["r"] = r
        debug["g"] = g
        debug["risk_free_rate"] = risk_free_rate
        debug["market_return"] = market_return
        debug["error"] = None
        debug["beta"] = beta

        # Check for errors
        if dividends.empty:
            debug["error"] = "Dividends data is empty."
        if D1 is None:
            debug["error"] = "D₁ is None (dividendRate or growth rate missing)."
        if r is None:
            debug["error"] = "Cost of equity (r) is None."
        if g is None:
            debug["error"] = "Dividend growth rate (g) is None."
        if r <= g:
            debug["error"] = "Cost of equity (r) is less than or equal to growth rate (g); invalid for DDM."

        fairValue = D1 / (r - g)

        debug["fairValue"] = None if debug["error"] else fairValue
    except Exception as e:
        debug["error"] = f"Unexpected error: {e}"
        debug["fairValue"] = None

    if g is None or r is None or D1 is None:
        debug["error"] = f"Invalid values detected: D1={D1}, r={r}, g={g}"
        debug["fairValue"] = None
        return debug

    return debug


# Gordon Growth Model - Returns the fair value of a dividend-paying stock.
def get_GGM(stock):
    debug = get_GGM_debug(stock)
    return debug


@app.route("/", methods=["GET", "POST"])
def index():
    price = None
    error_message = None
    longName = None
    ticker_name = None
    ggm_debug = None

    if request.method == "POST":
        ticker_name = request.form.get("stockTicker")

        if ticker_name:
            try:
                # Fetch stock data
                ticker = yf.Ticker(ticker_name)
                info = ticker.info

                longName = info.get("longName", "Name not found")
                price = info.get("regularMarketPrice", "Price not found")
                ggm_debug = get_GGM(ticker)
            except Exception as e:
                error_message = f"Error: {e}"

    return render_template("firstsite.html", ticker_name=ticker_name, value=price, longName=longName, ggm_debug=ggm_debug, error_message=error_message)


if __name__ == "__main__":
    app.run(debug=True)
