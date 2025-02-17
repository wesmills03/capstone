from flask import Flask, render_template, request
import yfinance as yf

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    value = None
    ticker = None

    if request.method == "POST":
        ticker = request.form.get("ticker").upper()  # Get user input
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Try different fields in case regularMarketPrice is missing
            value = info.get("regularMarketPrice") or info.get("currentPrice") or info.get("lastPrice")

            if value is None:
                value = "Price not available"

        except Exception as e:
            value = f"Error retrieving stock data: {e}"

    return render_template("index.html", value=value, ticker=ticker)

if __name__ == "__main__":
    app.run(debug=True)
