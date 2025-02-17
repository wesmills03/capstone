from flask import Flask, render_template
import yfinance as yf

app = Flask(__name__)


@app.route("/")
def index():
    ticker = yf.Ticker("AAPL")
    info = ticker.info
    return render_template("index.html", value=info["regularMarketPrice"])


if __name__ == "__main__":
    app.run()
