import re
import time
from datetime import datetime
from functools import reduce
from urllib.parse import unquote

from bs4 import BeautifulSoup

from logic.func import exchanging_to_usd, write_db
from logic.utils import conv_time, deconv_time, standartify_str
from logic.var import headers_html

from models.models import Owners, Transactions_and_holdings

import pandas as pd

import requests


def get_barchart_price(ticker):
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
                return df.to_dict()
            except:
                pass


def get_stock_price_missing(ticker):
    all_pages = []
    count = 0
    try:
        while True:
            td = []
            url = f"https://stockinvest.us/stock-price/{ticker}?page={count}"
            g = requests.get(url, headers=headers_html)
            main = BeautifulSoup(g.text, "lxml")
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
                    if conv_time(each_day.find_all("td")[0].text)
                    > conv_time("2010-01-01")
                ]
                if pre_table and table:
                    all_pages += list(table)
            else:
                break
            count += 1
            print(count)
        return all_pages
    except:
        return None


def get_historical_prices(rows, date, format=False):
    if rows:
        try:

            close = (
                next(
                    (
                        float(row.get("close").replace("$", "").replace(",", "."))
                        for row in rows
                        if datetime.strptime(
                            row.get("date").replace("/", "-"), "%m-%d-%Y"
                        )
                        <= date
                    ),
                    None,
                )
                if not format
                else next(
                    (
                        float(row.get("close").replace("$", "").replace(",", "."))
                        for row in rows
                        if datetime.strptime(
                            row.get("date").replace("/", "-"), "%Y-%m-%d"
                        )
                        <= date
                    ),
                    None,
                )
            )
            return close
        except:
            print("wrong")
            pass


def convert_symbol_to_usd(some_str, date):
    if some_str.endswith("."):
        some_str = some_str[0 : len(some_str) - 1].lower()

    if "£" in some_str or "gb" in some_str or "gbp" in some_str:
        usd = exchanging_to_usd(
            float(
                standartify_str(
                    some_str,
                    [",", " ", "£", "$", "gbp", "gb", "dkk"],
                    True,
                )
            ),
            "GBP",
            deconv_time(date),
        )

    if "dkk" in some_str:
        usd = exchanging_to_usd(
            float(
                standartify_str(
                    some_str,
                    [",", " ", "£", "$", "gbp", "gb", "dkk"],
                    True,
                )
            ),
            "DKK",
            deconv_time(date),
        )
    else:
        if some_str:
            usd = float(
                standartify_str(
                    some_str,
                    [",", " ", "£", "$", "gbp", "gb", "usd", "dkk"],
                    True,
                ),
            )
        else:
            return None
    return usd


def get_text(bs_obj, bool_=False, float_=False, date=False):
    if not isinstance(bs_obj, str):
        bs_obj = bs_obj.get("value") if bs_obj and bs_obj.get("value") else bs_obj
        bs_obj = bs_obj.text.replace("\n", "") if bs_obj else bs_obj

    if bool_ and bs_obj:
        bs_obj = "1" if bs_obj.lower() == "true" else bs_obj
        bs_obj = "0" if bs_obj.lower() == "false" else bs_obj
        bs_obj = bool(int(bs_obj)) if bs_obj.isdigit() else bs_obj
    bs_obj = float(bs_obj) if bs_obj and float_ else bs_obj
    bs_obj = None if not bs_obj else bs_obj
    bs_obj = bs_obj[:10] if bs_obj and date else bs_obj
    return bs_obj


def convert_pence(some_str):
    if "pence" in some_str:
        pound = round(float(standartify_str(some_str, [",", " ", "pence"])) / 100, 3)
        return "£" + str(pound)
    else:
        return some_str


def make_normal_date(date, period_ending):
    try:
        try:
            date = conv_time(date)
        except:
            day_and_year = "-".join(re.findall(r"\d+", date)).split("-")
            month = datetime.strptime(
                "".join(re.findall(r"[A-Za-z]", date)), "%B"
            ).month
            date = conv_time(f"{day_and_year[1]}-{month}-{day_and_year[0]}")
    except:
        date = period_ending
    if not date:
        date = period_ending
    return date


def check_if_sth(what_to_search: list, where):
    got = next(
        (x for x in what_to_search[1] if x in where),
        None,
    )
    if got:
        return what_to_search[0].replace("_", " ")


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


def get_stocks_rows(ticker):
    ticker = ticker.upper()
    date_for_req = deconv_time(datetime.now())
    test_from_date = "2012-12-25"
    from_date = "2010-12-25"
    source = "nasdaq"
    try:
        rows = make_req_to_nasdaq(ticker, test_from_date, date_for_req)
        if rows:
            return rows, source
        else:
            rows = make_req_to_nasdaq(ticker, from_date, date_for_req)
            if rows:
                return rows, source
    except:
        rows = make_req_to_nasdaq(ticker, from_date, date_for_req)
        if rows:
            return rows, source
    if not rows:
        rows = get_stock_price_missing(ticker)
        if not rows:
            rows = get_barchart_price(ticker)
        source = "stockinvest"
        if rows:
            return rows, source
    return (None, None)


def check_if_words_in_str(words, some_str):
    some_str = standartify_str(some_str, [",", "\n", " ", "-"], True)
    result = next((True for x in words if isinstance(x, str) and x in some_str), False)
    if not result:
        result = next(
            (
                all([y in some_str for y in x])
                for x in words
                if isinstance(x, list) and all([y in some_str for y in x])
            ),
            False,
        )
    return result


def check_if_derivative(some_str):
    restricted_trigers = [["restricted", "share"]]
    options_trigers = [["option", "issue"], ["option", "grant"]]
    resticted = check_if_words_in_str(restricted_trigers, some_str)
    option = check_if_words_in_str(options_trigers, some_str)
    return resticted, option


def d_a_code_filter(some_str):
    a_trigers = [
        "acquisition",
        "purchase",
        "frants",
        "issue",
        "award",
        "grant",
        "receipt",
        "vesting",
        "reinvest",
        "thereinvest",
        ["exerciseof", "options"],
    ]
    d_trigers = [
        ["sell", "share"],
        ["sale", "share"],
        ["sale", "ads"],
        ["disposal", "share"],
        ["disposed", "share"],
    ]
    cut_trigers = [
        ["between", "accounts"],
        "withholding",
        ["received", "cash"],
        "tospouse",
        "revaluation",
        "cashpayout",
        "conversion",
        "gift",
        "personalshareholding",
        "othertransaction",
        "family",
    ]
    restricted, option = check_if_derivative(some_str)
    a = check_if_words_in_str(a_trigers, some_str)
    d = check_if_words_in_str(d_trigers, some_str)
    cut = check_if_words_in_str(cut_trigers, some_str)
    if not cut:
        if d:
            return "d", option, restricted
        elif a:
            return "a", option, restricted
        else:
            return (None, None, None)
    else:
        return (None, None, None)


def title_filter(some_str):
    restricted, option = check_if_derivative(some_str)
    ads_trigers = ["ads", ["american", "share", "depo"]]
    shares_trigers = ["share", "ordin"]
    ads = check_if_words_in_str(ads_trigers, some_str)
    shares = check_if_words_in_str(shares_trigers, some_str)

    if ads:
        return "American Depositary Shares", option, restricted
    elif shares:
        return "Ordinary Shares", option, restricted
    else:
        return (None, None, None)


def understand_derivative_or_not(a_d_code, description):
    d_a, option_d_a, restricted_d_a = d_a_code_filter(a_d_code)
    title, option_t, restricted_t = title_filter(description)
    option = option_d_a or option_t
    restricted = restricted_d_a or restricted_t
    if d_a and title:
        this_elem = {}
        if restricted:
            this_elem.update(
                {
                    "underlying_security_title": "restricted_stock_units",
                    "type": "derivativetransaction",
                }
            )
        elif option:
            this_elem.update(
                {
                    "underlying_security_title": "stock_option",
                    "type": "derivativetransaction",
                }
            )
        this_elem.update(
            {
                "transaction_acquired_disposed_code": d_a,
                "security_title": title,
                "type": "nonderivativetransaction",
            }
        )
        return this_elem


def transaction_code_generator(transaction_code):
    transaction_code = standartify_str(
        transaction_code,
        [
            ",",
            " ",
            ".",
            "&",
        ],
        True,
    )
    market = ["xlon", "xnys", "xyns", "exchange", "xnms", "aimx", "nasdaq"]
    for symb in market:
        if symb in transaction_code:
            return "1"
    if "n/a" in transaction_code:
        return None
    else:
        return "0"


def security_title_filter(title, type_, underlying=None):
    selectors = (
        (
            (
                ("nonderivativetransaction", "nonderivativeholding"),
                {
                    "preferred_stock": ["pref", "prf"],
                    "common_stock": ["com", "cmm", "cmn", "juni", "ordin", "shares"],
                },
            ),
            (
                ("derivativetransaction", "derivativeholding"),
                {
                    "preferred_stock": ["pref", "prf"],
                    "stock_option": ["stock option", "option", "nqso", "opit", "opt"],
                    "stock_warrant": ["warrant", "warant"],
                    "phantom_stock": ["phantom", "shadow"],
                    "stock_appreciation_rights": ["appreciation", "rights", "sar"],
                    "restricted_stock_units": ["restricted", "stock units", "rsu"],
                },
            ),
        )
        if not underlying
        else (
            (
                ("derivativetransaction", "derivativeholding"),
                {
                    "preferred_stock": ["pref", "prf"],
                    "common_stock": ["com", "cmm", "cmn", "juni", "ordin", "shares"],
                },
            ),
        )
    )
    except_words = {
        "stock_option": ["sell", "put"],
        "stock_warrant": ["sell", "put"],
    }
    for selector in selectors:
        types, lst_what_to_search = selector
        if type_ in types:
            for each_what_to_search in lst_what_to_search.items():
                got = next(
                    (x for x in each_what_to_search[1] if x in title),
                    None,
                )
                if got:
                    option_or_warrant = except_words.get(each_what_to_search[0])
                    if option_or_warrant:
                        ok = next((x for x in option_or_warrant if x in title), None)
                        if ok:
                            return None
                    return each_what_to_search[0].replace("_", " ")


def unite_derivatives_nonderivatives_and_commit(session, non_derivative, derivative):
    transactions_and_or_holdings = reduce(
        lambda x, y: x + y,
        [non_derivative, derivative],
    )
    for each_ready_obj in transactions_and_or_holdings:
        write_db(Transactions_and_holdings, session, each_ready_obj)


def write_owner_db(session, owners):
    for index, owner in enumerate(owners):
        same_obj = (
            session.query(Owners)
            .filter(
                Owners.name == owner.get("name"),
                Owners.is_director == owner.get("is_director"),
                Owners.cik == owner.get("cik"),
                Owners.is_officer == owner.get("is_officer"),
                Owners.is_ten_percent_owner == owner.get("is_ten_percent_owner"),
                Owners.is_other == owner.get("is_other"),
                Owners.officer_title == owner.get("officer_title"),
                Owners.other_text == owner.get("other_text"),
            )
            .first()
        )
        if not same_obj:

            new_owner = write_db(Owners, session, owner)
            owners[index] = new_owner
        else:
            owners[index] = same_obj
    return owners
