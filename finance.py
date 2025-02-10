import yfinance as yahooFinance

stock = yahooFinance.Ticker("META")

# print(GetFacebookInformation.info)
print(stock.fast_info["last_price"])