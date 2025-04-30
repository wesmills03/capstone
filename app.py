from flask import Flask, render_template, request, redirect, url_for
import yfinance as yf
import plotly.graph_objs as go
import plotly.io as pio
import requests
from datetime import datetime
from urllib.parse import urlparse
from markupsafe import Markup
import re

NEWS_API_KEY = "883ab179e0c1433f92eb192dbcf19e47"

app = Flask(__name__)

# python app.py runserver

# formulas

glossary_terms = {
    "Fair Value": "The estimated intrinsic value of a stock based on fundamentals like earnings, growth potential, and market conditions.",
    "Stock": "A stock is a type of investment that represents an ownership share in a company.",
    "Stock Ticker": "A stock ticker is a short abbreviation used to uniquely identify publicly traded shares of a particular stock on a particular stock market.",
    "Earnings Per Share (EPS)": "A company's net profit divided by the number of outstanding shares, indicating profitability on a per-share basis.",
    "P/E Ratio": "The Price-to-Earnings Ratio. It’s calculated by dividing the market price per share by the EPS. It is used to evaluate a stock's valuation.",
    "RSI (Relative Strength Index)": "A momentum oscillator measuring the speed and change of price movements. RSI helps identify overbought or oversold conditions in a stock.",
    "Market Price": "The current trading price of a stock in the market.",
    "Dividend": "A portion of a company's profit distributed to shareholders. It can provide a regular income stream for investors.",
    "Historical P/E": "An average P/E ratio based on past performance, often used as a benchmark for valuation.",
    "Forward P/E": "A P/E ratio that uses expected future earnings, offering a projection-based valuation.",
    "Discounted Cash Flow (DCF)": "A method used to determine the value of an investment based on its expected future cash flows, discounted back to their present value.",
    "Dividend Discount Model (DDM)": "A valuation model that estimates the fair value of a stock by discounting the expected future dividends back to their present value."
}


def format_datetime(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.strftime("%b %d, %Y, %I:%M %p")


app.jinja_env.filters['format_datetime'] = format_datetime


def link_glossary(text):
    if not text or not isinstance(text, str):
        return text

    for term in glossary_terms:
        slug = term.replace(' ', '-')
        pattern = rf'\b{re.escape(term)}\b'
        link = url_for("glossary") + f"#term-{slug}"
        replacement = f'<a href="{link}">{term}</a>'
        text = re.sub(pattern, replacement, text)
    return Markup(text)


app.jinja_env.filters['link_glossary'] = link_glossary


def get_stock_news(ticker):
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": ticker,  # just searches the ticker
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 5,  # article limit
        "apiKey": NEWS_API_KEY
    }

    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            articles = data.get("articles", [])
            news_items = []
            for article in articles:
                news_items.append({
                    "title": article.get("title"),
                    "url": article.get("url"),
                    "description": article.get("description"),
                    "publishedAt": article.get("publishedAt")
                })
            return news_items
        else:
            print(f"News API error: {response.status_code} {response.text}")
            return []
    except Exception as e:
        print(f"Error fetching news: {str(e)}")
        return []


def calculate_rsi(ticker, period=14):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        if hist.empty or "Close" not in hist:
            return "Data unavailable ⚠️"
        close_prices = hist["Close"]
        delta = close_prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi.iloc[-1], 2) if not rsi.isna().all() else "Data unavailable ⚠️"
    except Exception as e:
        return f"Error fetching RSI: {str(e)}"


def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        stock_data = stock.history(period="1d", timeout=10)
        if stock_data.empty:
            return None, None, "Stock data unavailable"
        price = stock_data["Close"].iloc[-1]
        eps = stock.info.get("trailingEps", None)
        current_pe = stock.info.get("trailingPE", None)
        historical_pe = stock.info.get("forwardPE", None)
        # error for missing data
        if eps is None or eps <= 0:
            return price, eps, "Insufficient data to calculate fair value"
        if current_pe is None:
            current_pe = round(price / eps, 2)
        if historical_pe is None:
            historical_pe = 20  # default fallback
        return price, eps, (current_pe, historical_pe)
    except Exception as e:
        return None, None, f"Error fetching data: {str(e)}"


def calculate_pe_fair_value(price, eps, pe_tuple):
    current_pe, historical_pe = pe_tuple
    if eps is None:
        return None, "Data unavailable ⚠️"
    fair_value = round(historical_pe * eps, 2)
    if current_pe and historical_pe:
        if current_pe > historical_pe:
            valuation = "Overvalued 📈"
        elif current_pe < historical_pe:
            valuation = "Undervalued 📉"
        else:
            valuation = "Fairly Valued ⚖️"
    else:
        valuation = "Data unavailable ⚠️"
    return fair_value, valuation


def alternative_formula(price, eps, pe_tuple):
    # adds a 5% premium
    if price is None:
        return None, "Data unavailable ⚠️"
    alt_value = round(price * 1.05, 2)
    return alt_value, "Calculated via alternative formula"


def calculate_ddm_fair_value(ticker):
    stock = yf.Ticker(ticker)
    dividend = stock.info.get("dividendRate", None)
    if dividend is None or dividend <= 0:
        return None, "Dividend data unavailable for DDM"
    growth = 0.03       # assumed 3% growth rate
    discount_rate = 0.08  # assumed 8% discount rate
    fair_value = dividend * (1 + growth) / (discount_rate - growth)
    return round(fair_value, 2), "Calculated via Dividend Discount Model (DDM)"


def calculate_dcf_fair_value(ticker):
    stock = yf.Ticker(ticker)
    eps = stock.info.get("trailingEps", None)
    if eps is None:
        return None, "EPS data unavailable for DCF calculation"
    growth_rate = 0.05   # assumed 5% annual growth
    discount_rate = 0.10  # assumed 10% discount rate
    years = 10
    # sum of discounted EPS over the next 10 years
    projected_value = sum([eps * ((1 + growth_rate) ** year) / ((1 + discount_rate) ** year) for year in range(1, years + 1)])
    return round(projected_value, 2), "Calculated via simplified Discounted Cash Flow (DCF)"


def get_stock_chart(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="6mo")
    if hist.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], mode='lines', name='Close Price'))
    fig.update_layout(
        title=f"Stock Price Chart for {ticker}",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        template="plotly_dark",
        paper_bgcolor="#2B2B2B",
        plot_bgcolor="#2B2B2B",
        font_color="#EAEAEA"
    )
    return pio.to_html(fig, full_html=False)


def get_company_logo(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        website = info.get("website", "")
        if website:
            parsed = urlparse(website)
            # parsed.netloc is the domain (or use parsed.path if netloc is empty)
            domain = parsed.netloc if parsed.netloc else parsed.path
            if domain:
                logo_url = f"https://logo.clearbit.com/{domain}"
                return logo_url
        return None
    except Exception as e:
        print(f"Error fetching company logo: {str(e)}")
        return None


# routes

# home route
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        ticker = request.form.get("stockTicker")
        if ticker:
            # defaults to P/E valuation method
            return redirect(url_for("stock_details", ticker=ticker, formula="pe"))
    return render_template("home.html")


# calculator route
@app.route("/stock", methods=["GET", "POST"])
def stock_details():
    ticker = request.args.get("ticker", None)
    formula = request.args.get("formula", "pe")  # default is pe
    stock = yf.Ticker(ticker)
    long_name = stock.info.get("longName", ticker)  # fallback to ticker if not available
    error_message = None
    stock_chart = None
    rsi = "Data unavailable ⚠️"
    news_items = []

    if ticker is None:
        return redirect(url_for("home"))

    # allows a new ticker search from the top bar
    if request.method == "POST":
        new_ticker = request.form.get("stockTicker")
        if new_ticker:
            return redirect(url_for("stock_details", ticker=new_ticker, formula=formula))

    # gets base stock data
    price, eps, pe_data_or_error = get_stock_data(ticker)
    if isinstance(pe_data_or_error, str):
        error_message = pe_data_or_error
        current_pe = historical_pe = None
        fair_value = None
        valuation = None
    else:
        current_pe, historical_pe = pe_data_or_error
        # select valuation method
        if formula == "pe":
            fair_value, valuation = calculate_pe_fair_value(price, eps, pe_data_or_error)
        elif formula == "alt":
            fair_value, valuation = alternative_formula(price, eps, pe_data_or_error)
        elif formula == "ddm":
            fair_value, valuation = calculate_ddm_fair_value(ticker)
        elif formula == "dcf":
            fair_value, valuation = calculate_dcf_fair_value(ticker)
        else:
            fair_value, valuation = None, "Unknown formula selected"

    rsi = calculate_rsi(ticker)
    stock_chart = get_stock_chart(ticker)
    news_items = get_stock_news(ticker)
    company_logo = get_company_logo(ticker)

    return render_template("stock.html",
                           ticker=ticker,
                           long_name=long_name,
                           price=price,
                           eps=eps,
                           current_pe=current_pe,
                           historical_pe=historical_pe,
                           fair_value=fair_value,
                           valuation=valuation,
                           rsi=rsi,
                           stock_chart=stock_chart,
                           news_items=news_items,
                           error_message=error_message,
                           company_logo=company_logo,
                           selected_formula=formula)


# glossary route
@app.route("/glossary")
def glossary():
    return render_template("glossary.html", glossary_terms=glossary_terms)


if __name__ == "__main__":
    app.run(debug=True)
