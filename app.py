from flask import Flask, render_template, request
import yfinance as yf

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    price = None
    if request.method == "POST":
        ticker_name = request.form.get("stockTicker")
        if ticker_name:
            ticker = yf.Ticker(ticker_name)
            info = ticker.info
            price = info.get("regularMarketPrice", "Price not found")
    return render_template("firstsite.html", value=price)


if __name__ == "__main__":
    app.run(debug=True)
