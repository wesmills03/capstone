from flask import Flask, render_template, request
import yfinance as yf
import plotly.graph_objs as go
import plotly.io as pio
import pandas as pd

app = Flask(__name__)

# Function to calculate RSI
def calculate_rsi(ticker, period=14):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")  # Get 1 month of data to calculate RSI

        if hist.empty or "Close" not in hist:
            return "Data unavailable ⚠️"

        close_prices = hist["Close"]
        delta = close_prices.diff()

        # Separate gains and losses
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        # Calculate RSI
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # Return latest RSI value
        return round(rsi.iloc[-1], 2) if not rsi.isna().all() else "Data unavailable ⚠️"

    except Exception as e:
        return f"Error fetching RSI: {str(e)}"

# Function to fetch stock data and calculate fair value using P/E ratio
def get_pe_fair_value(ticker):
    try:
        stock = yf.Ticker(ticker)

        # Fetch stock price with timeout
        stock_data = stock.history(period="1d", timeout=10)
        if stock_data.empty:
            return None, None, None, None, "Stock data unavailable", "Data unavailable ⚠️", "Data unavailable ⚠️"

        # Get latest market price
        price = stock_data["Close"].iloc[-1]

        # Get EPS (Earnings Per Share, TTM)
        eps = stock.info.get("trailingEps", None)

        # Get Current P/E Ratio
        current_pe = stock.info.get("trailingPE", None)

        # Get Historical P/E Ratio
        historical_pe = stock.info.get("forwardPE", None)  # Use forward P/E as fallback

        # Calculate RSI
        rsi = calculate_rsi(ticker)

        # If no EPS is available, return an error
        if eps is None or eps <= 0:
            return price, "N/A", current_pe, historical_pe, "Insufficient data to calculate fair value", "Data unavailable ⚠️", rsi

        # If current P/E is missing, manually calculate it
        if current_pe is None and price:
            current_pe = round(price / eps, 2)

        # If historical P/E is missing, use a default value (industry average P/E)
        if historical_pe is None:
            historical_pe = 20  # Default P/E ratio for large-cap stocks

        # Calculate Fair Value using P/E Model
        fair_value = round(historical_pe * eps, 2)

        # Compare P/E ratios to determine valuation status
        if current_pe and historical_pe:
            if current_pe > historical_pe:
                valuation = "Overvalued 📈"
            elif current_pe < historical_pe:
                valuation = "Undervalued 📉"
            else:
                valuation = "Fairly Valued ⚖️"
        else:
            valuation = "Data unavailable ⚠️"

        return price, eps, current_pe, historical_pe, fair_value, valuation, rsi

    except Exception as e:
        return None, None, None, None, f"Error fetching data: {str(e)}", "Data unavailable ⚠️", "Data unavailable ⚠️"

# Function to fetch stock chart
def get_stock_chart(ticker_name):
    stock = yf.Ticker(ticker_name)
    hist = stock.history(period="6mo")  

    if hist.empty:
        return None

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], mode='lines', name='Close Price'))
    fig.update_layout(title=f"Stock Price Chart for {ticker_name}", xaxis_title="Date", yaxis_title="Price ($)")

    return pio.to_html(fig, full_html=False)

# Route to handle user input and calculate fair value
@app.route("/", methods=["GET", "POST"])
def index():
    price = None
    eps = None
    current_pe = None
    historical_pe = None
    fair_value = None
    valuation = None
    rsi = "Data unavailable ⚠️"  # Ensure RSI is always defined
    ticker_name = None
    stock_chart = None
    error_message = None

    if request.method == "POST":
        ticker_name = request.form.get("stockTicker")

        if ticker_name:
            try:
                price, eps, current_pe, historical_pe, fair_value, valuation, rsi = get_pe_fair_value(ticker_name)
                stock_chart = get_stock_chart(ticker_name)
            except Exception as e:
                error_message = f"Error fetching data: {str(e)}"

    return render_template("firstsite.html", ticker_name=ticker_name, price=price, eps=eps, current_pe=current_pe, historical_pe=historical_pe, fair_value=fair_value, valuation=valuation, rsi=rsi, stock_chart=stock_chart, error_message=error_message)

if __name__ == "__main__":
    app.run(debug=True)
