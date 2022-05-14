import time
import requests
from logic.utils import conv_time, deconv_time
from bs4 import BeautifulSoup
from logic.var import headers_html
from urllib.parse import unquote
import pandas as pd
import datetime
from yahoo_fin.stock_info import get_data
from logic.func import open_csv


def make_req_to_nasdaq(ticker, test_from_date, date_for_req, count=0):
    url = f"https://api.nasdaq.com/api/quote/{ticker}/historical?assetclass=stocks&fromdate={test_from_date}&limit=9999&todate={date_for_req}"
    if count < 10:
        try:
            response = requests.get(url, headers=headers_html).json()
            rows = response.get("data").get("tradesTable").get("rows")
            return rows
        except:
            count += 1
            rows = make_req_to_nasdaq(ticker, test_from_date, date_for_req, count)
            if rows:
                return rows
    else:
        return


def get_stockinvest_price(ticker, name):
    name = name.replace("/", "_")
    all_pages = []
    count = 0
    while True:
        td = []
        url = f"https://stockinvest.us/stock-price/{ticker}?page={count}"
        g = requests.get(url, headers=headers_html)
        main = BeautifulSoup(g.text, "lxml")
        name_from_source = (
            main.find_all("div", {"class": "panel-body"})[0]
            .getText()
            .strip()
            .split("\n")[0]
        )
        if name_from_source:
            name = name_from_source.replace("/", "_")
        td = next((x for x in main.find_all("td") if "Close" in x.text), None)
        any_info_more = main.find("div", {"class": "table-responsive"})
        if any_info_more:
            any_info_more = any_info_more.find_all("tr")
        else:
            any_info_more = 2
        if (
            td
            and "COULDN'T FIND" not in g.text
            and len(any_info_more) > 1
            and count < 50
        ):
            pre_table = td.parent.parent.find_all("tr")[1:]
            table = [
                {
                    "ticker": ticker,
                    "date": each_day.find_all("td")[0].text,
                    "close": each_day.find_all("td")[-2].text,
                }
                for each_day in pre_table
                # if float(each_day.find_all("td")[-1].text.replace(" ", ""))
                # and
                if conv_time(each_day.find_all("td")[0].text) > conv_time("2010-01-01")
            ]
            if pre_table and table:
                all_pages += list(table)
        else:
            break
        count += 1
        print(count)
    path = f"data/stockinvest/{ticker}---{name}.csv"
    if all_pages:
        # print(all_pages)
        df = pd.DataFrame([list(x.values()) for x in all_pages])
        df.columns = ["ticker", "date", "close"]
        df.to_csv(path, index=False)


def get_barchart_price(ticker, name):
    with requests.Session() as s:
        headers = {}
        headers.update(headers_html)
        s.get("https://www.barchart.com/stocks/quotes/AAPL/overview", headers=headers)
        headers["X-XSRF-TOKEN"] = unquote(s.cookies["XSRF-TOKEN"])
        url_to_check_date = f"https://www.barchart.com/proxies/timeseries/queryeod.ashx?symbol={ticker}&data=daily&maxrecords=10000&volume=contract&order=asc&dividends=false&backadjust=false&daystoexpiration=1&contractroll=expiration"
        print(url_to_check_date)
        try:
            response_to_check_date = s.get(url_to_check_date, headers=headers)
            txt_data = response_to_check_date.text
        except:
            time.sleep(2)
            response_to_check_date = s.get(url_to_check_date, headers=headers)
            txt_data = response_to_check_date.text
        print(txt_data)
        try:
            time.sleep(0.1)
            to_find_source_name = s.get(
                f"https://www.barchart.com/stocks/quotes/{ticker}/overview",
                headers=headers,
            )
            if to_find_source_name:
                main = BeautifulSoup(to_find_source_name.text, "lxml")
                source_name = main.find_all("span", {"class": "symbol"})[0].text
                if source_name:
                    name = source_name
        except:
            pass
        if txt_data.replace(" ", "").replace("\n", ""):
            try:
                df = pd.DataFrame([x.split(",") for x in txt_data.split("\n")])
                df.columns = [
                    "ticker",
                    "date",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ]
                name = name.replace("/", "_")
                df.to_csv(f"data/barchart/{ticker}---{name}.csv", index=False)
            except:
                pass


def get_yahoo_price(ticker, name):
    try:
        yahoo_rows = get_data(ticker, interval="1d")
        yahoo_rows.reset_index(
            level=0,
            inplace=True,
        )
        yahoo_rows.columns = [
            "date",
            "open",
            "high",
            "low",
            "close",
            "adjclose",
            "volume",
            "ticker",
        ]
        name = name.replace("/", "_")
        yahoo_rows.to_csv(f"data/yahoo/{ticker}.csv", index=False)
    except:
        pass


def get_nasdaq_price(ticker, name):
    test_from_date = "2009-12-25"
    from_date = "2007-12-25"

    date_for_req = deconv_time(datetime.datetime.now())
    try:
        nasdaq_rows = make_req_to_nasdaq(ticker, test_from_date, date_for_req)
        if nasdaq_rows:
            pass
        else:
            nasdaq_rows = make_req_to_nasdaq(ticker, from_date, date_for_req)
    except:
        nasdaq_rows = make_req_to_nasdaq(ticker, from_date, date_for_req)
    if not nasdaq_rows:
        print(ticker, "not found")
        return ticker
    else:
        # try:
        headers = [
            "ticker",
        ] + list(nasdaq_rows[1].keys())
        nasdaq_rows = [
            tuple(
                [
                    ticker,
                ]
                + list(x.values())
            )
            for x in nasdaq_rows
            if conv_time(x.get("date").replace("/", "-"), other_patern=True)
            > conv_time("2010-01-01")
        ]
        name = name.replace("/", "_")
        path = f"data/nasdaq/{ticker}.csv"
        df = pd.DataFrame(nasdaq_rows)
        df.columns = headers
        print(df)
        df.to_csv(path, index=False)
        # except:
        #     pass


def get_ticker_prices(company=None):
    name, ticker = company
    get_stockinvest_price(ticker, name)
    get_barchart_price(ticker, name)
    get_yahoo_price(ticker, name)
    get_nasdaq_price(ticker, name)


def get_prices_from_ready_csv(file_in):
    all_rows = open_csv(file_in)
    for each_row in all_rows:
        if each_row.get("listed"):
            get_ticker_prices((each_row.get("name"), each_row.get("ticker")))
