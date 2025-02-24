from flask import Flask, render_template, request
import yfinance as yf

app = Flask(__name__)

# To run the program, open the terminal and enter: python app.py runserver
#   YFRateLimitError? Try updating yfinance: pip install --upgrade yfinance


# Returns annual dividend growth rate for each year
def get_dividend_g(stock):
    dividends = stock.dividends  # historical dividends

    if dividends.empty:
        return None, None

    annual_dividend = dividends.resample('Y').sum()  # total annual dividend
    annual_dividend_growth_rate = annual_dividend.pct_change().dropna()  # dividend growth rate for each year 

    return annual_dividend_growth_rate

    # geometric_mean_dividend_growth_rate = (annual_dividend_growth_rate + 1).prod() ** (1/len(annual_dividend_growth_rate)) - 1  # geometric mean to account for compounding data
    # arithmetic_mean_dividend_growth_rate = np.mean(annual_dividend_growth_rate)  # arithmetic mean for posterity


@app.route("/", methods=["GET", "POST"])
def index():
    price = None
    error_message = None
    longName = None
    ticker_name = None
    # fair_value = None

    if request.method == "POST":
        ticker_name = request.form.get("stockTicker")

        if ticker_name:
            # Fetch stock data
            ticker = yf.Ticker(ticker_name)
            info = ticker.info

            longName = info["longName"]
            price = info.get("regularMarketPrice", "Price not found")

            # D = info.get("dividendRate", 0) # Annual Dividend (D)

    return render_template("firstsite.html", ticker_name=ticker_name, value=price, longName=longName, error_message=error_message)


if __name__ == "__main__":
    app.run(debug=True)
