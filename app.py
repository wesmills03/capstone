from flask import Flask, render_template, request
import yfinance as yf

app = Flask(__name__)

# To run the program, open the terminal and enter: python app.py runserver
#   YFRateLimitError? Try updating yfinance: pip install --upgrade yfinance


@app.route("/", methods=["GET", "POST"])
def index():
    price = None
    error_message = None
    longName = None
    ticker_name = None
    if request.method == "POST":
        ticker_name = request.form.get("stockTicker")
        if ticker_name:
            ticker = yf.Ticker(ticker_name)
            info = ticker.info
            longName = info['longName']
            price = info.get("regularMarketPrice", "Price not found")

    return render_template("firstsite.html", ticker_name=ticker_name, value=price, longName=longName, error_message=error_message)


if __name__ == "__main__":
    app.run(debug=True)
