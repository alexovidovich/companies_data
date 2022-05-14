import requests
from bs4 import BeautifulSoup
from logic.var import headers_html


def get_barchart_exchange_by_ticker(ticker):
    url = f"https://www.barchart.com/stocks/quotes/{ticker}/overview"
    try:
        info_html = requests.get(url, headers=headers_html).text
        main = BeautifulSoup(info_html, "lxml")
        all_spans = main.find_all("span", {"class": "symbol-trade-time"})
        exchange = next(
            (
                x.text.replace("[", "").replace("]", "")
                for x in all_spans
                if "nasdaq" in x.text.lower() or "nyse" in x.text.lower()
            ),
            None,
        )
        if "nyse" in exchange.lower():
            exchange = "NYSE"
        if "nasdaq" in exchange.lower():
            exchange = "NASDAQ"
        return exchange
    except:
        return


def get_stockinvest_exchange_by_ticker(ticker):
    url = f"https://stockinvest.us/stock-price/{ticker}"
    try:
        info_html = requests.get(url, headers=headers_html).text
        main = BeautifulSoup(info_html, "lxml")
        all_spans = main.find_all(
            "span", {"class": "badge badge-ticker badge-default badge-outline"}
        )
        exchange = next(
            (
                x.text.replace(":", "")
                .replace('"', "")
                .replace("[", "")
                .replace("]", "")
                for x in all_spans
                if "nasdaq" in x.text.lower() or "nyse" in x.text.lower()
            ),
            None,
        )
        if "nyse" in exchange.lower():
            exchange = "NYSE"
        if "nasdaq" in exchange.lower():
            exchange = "NASDAQ"
        return exchange

    except:
        return


def get_exchange(ticker):
    exchange = get_barchart_exchange_by_ticker(ticker)
    if not exchange:
        exchange = get_stockinvest_exchange_by_ticker(ticker)
    return exchange
