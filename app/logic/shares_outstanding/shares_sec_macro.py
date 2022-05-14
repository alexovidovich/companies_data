import csv
import datetime
import json
import time

from bs4 import BeautifulSoup

from core.db import SessionLocal

from logic.utils import conv_time, standartify_str
from logic.func import (
    get_all_model_obj_by_name,
    get_hits,
    is_uk_company,
    remove_nesting,
    write_db,
)
from logic.shares_outstanding.func import (
    make_real_numbers_of_shares_outstanding,
    save_db,
)
from logic.var import headers_html, headers_json, headers_sec

from models.models import Macrotrends, Number_of_objects, SEC, Sharesoutstandinghistory

import requests


def sharesoutstandinghistory(each_company, cont=None):
    model = Sharesoutstandinghistory
    ticker = each_company.get("ticker")
    name = each_company.get("name")
    url = f"https://www.sharesoutstandinghistory.com/?symbol={ticker.lower()}"
    req_obj = requests.get(url)
    req_obj = req_obj.text
    main = BeautifulSoup(req_obj, "lxml")
    mn = (
        main.find("div", id="SharesOutstandingHistory_ROS_RightRail_1")
        .parent.find("table")
        .find_all("tr")
    )
    if len(mn) > 2:
        for tr in mn[3:]:
            date = tr.find_all("td")[0].text
            date = date.split("/")
            date = datetime.datetime(int(date[-1]), int(date[-3]), int(date[-2]))
            shares_outstanding = float(tr.find_all("td")[1].text[:-1])
            if tr.find_all("td")[1].text[-1] == "B":
                shares_outstanding *= 1000
            with SessionLocal() as session:
                save_db(session, model, name, ticker, date, shares=shares_outstanding)
    else:
        print("not found", name)
        if cont:
            try:
                pass
                # sec(each_company, cont=True)
            except:
                print(
                    f"The company {name} is not in the USA and has no info on macrotrends and sharesoutstandinghistory. \
                        \nCheck the name and the ticker of this company and try again"
                )


def macrotrends(each_company):
    model = Macrotrends
    ticker = each_company.get("ticker")
    name = each_company.get("name")
    url = f"https://www.macrotrends.net/stocks/charts/{ticker.lower()}"
    prep = requests.get(url)
    req_obj = requests.get(str(prep.url) + "shares-outstanding").text
    main = BeautifulSoup(req_obj, "lxml")
    if len(main.find_all("table", {"class": "historical_data_table table"})) > 0:
        trs = (
            main.find_all("table", {"class": "historical_data_table table"})[1]
            .find("tbody")
            .find_all("tr")
        )
        for tr in reversed(trs):
            container = tr.find_all("td")
            date = container[0].text
            date = conv_time(date)
            shares = container[1].text
            if container[1].text == "":
                shares = "0"
            shares_outstanding = float(shares.replace(",", "."))
            with SessionLocal() as session:
                save_db(session, model, name, ticker, date, shares=shares_outstanding)
    # else:
    #     sharesoutstandinghistory(each_company, cont=True)


def get_missing(session, model, name, ticker, cik):
    results = session.query(SEC).filter(SEC.name == name).first()
    if not results:
        url_to_parse = "https://efts.sec.gov/LATEST/search-index"
        body = json.dumps(
            {
                "dateRange": "custom",
                "category": "custom",
                "entityName": name.upper(),
                "startdt": "2013-01-01",
                "enddt": "2021-09-22",
                "forms": ["10-K", "10-KT", "10-Q", "20-F", "40-F"],
            }
        )
        find_req = requests.post(url_to_parse, data=body, headers=headers_json).json()
        find_req = find_req.get("hits")
        hits = find_req.get("hits")
        for each_hit in hits:
            form, file_date, period_ending, new_url = get_hits(each_hit, cik)
            new_req = requests.get(new_url, headers=headers_html).text
            main = BeautifulSoup(new_req, "lxml")
            tds = main.find_all("td")
            if tds:
                for td in tds:
                    if (
                        "commonstock,$"
                        in standartify_str(
                            td.text,
                            [" "],
                            True,
                        )
                        and ";" not in td.text.lower().replace(" ", "")
                    ):
                        for span in td.parent.find_all("span") + td.parent.find_all(
                            "div"
                        ):
                            if standartify_str(span.text, [","]).isdigit():
                                with SessionLocal() as session:
                                    save_db(
                                        session,
                                        model,
                                        name,
                                        ticker,
                                        conv_time(file_date),
                                        period_ending,
                                        round(
                                            float(standartify_str(span.text, [","]))
                                            / 1000000,
                                            2,
                                        ),
                                        form=form,
                                    )
                                break


def prepare_for_saving_sec_shares(session, found, model, name, ticker):
    for each_shares_outstanding_object in found:
        all_sec_objects = get_all_model_obj_by_name(session, model, name)
        shares_outstanding = make_real_numbers_of_shares_outstanding(
            all_sec_objects,
            each_shares_outstanding_object,
        )
        if shares_outstanding:
            date = conv_time(each_shares_outstanding_object.get("filed"))
            form = each_shares_outstanding_object.get("form")
            end_date = each_shares_outstanding_object.get("end")
            save_db(
                session,
                model,
                name,
                ticker,
                date,
                end_date,
                shares_outstanding,
                form=form,
            )


def sec(each_company, cik=None, cont=None, uk=False, no_country=False):
    model = SEC
    ticker = each_company.get("ticker")
    name = each_company.get("name")
    csvFilePath = "data/countries.csv"
    with open(csvFilePath) as csv_file:
        companies = csv.DictReader(csv_file)
        condition = (
            True
            if no_country
            else is_uk_company(
                ticker,
                companies,
                uk,
            )
        )
        if condition:
            cik = each_company.get("cik")
            if cik:
                time.sleep(0.3)
                url = f"http://data.sec.gov/api/xbrl/companyfacts/CIK{str(cik)}.json"
                req = requests.get(url, headers=headers_sec)
                if req:
                    req_obj = req.json()
                    keys = [
                        "facts.ifrs-full.NumberOfSharesOutstanding.units.shares",
                        "facts.dei.EntityCommonStockSharesOutstanding.units.shares",
                        "facts.us-gaap.CommonStockSharesOutstanding.units.shares",
                        "facts.us-gaap.WeightedAverageNumberOfDilutedSharesOutstanding.units.shares",
                        "facts.us-gaap.WeightedAverageNumberOfShareOutstandingBasicAndDiluted.units.shares",
                        "facts.ifrs-full.AdjustedWeightedAverageShares.units.shares",
                    ]
                    found = next(
                        (
                            remove_nesting(req_obj).get(path_get)
                            for path_get in keys
                            if remove_nesting(req_obj).get(path_get)
                        ),
                        None,
                    )
                    if found:
                        with SessionLocal() as session:
                            prev_req = (
                                session.query(Number_of_objects)
                                .filter(
                                    Number_of_objects.ticker == ticker,
                                    Number_of_objects.position == "SEC",
                                )
                                .first()
                            )
                            if not prev_req:
                                prepare_for_saving_sec_shares(
                                    session, found, model, name, ticker
                                )
                                get_missing(session, model, name, ticker, cik)
                                is_in_db_after_func = (
                                    session.query(model)
                                    .filter(
                                        model.ticker == each_company.get("ticker"),
                                    )
                                    .first()
                                )
                                if is_in_db_after_func:
                                    number_of_objects_in_each_company = {
                                        "company": name,
                                        "ticker": ticker,
                                        "date": datetime.datetime.now(),
                                        "position": "SEC",
                                        "number": len(found),
                                    }
                                    prev_req = write_db(
                                        Number_of_objects,
                                        session,
                                        number_of_objects_in_each_company,
                                    )
                            else:
                                dif_hours = (
                                    (datetime.datetime.now() - prev_req.date).seconds
                                    // 3600
                                ) < 24  # how many hours till next req
                                dif_total_objects = len(found) - prev_req.number
                                if dif_total_objects > 0:
                                    prepare_for_saving_sec_shares(
                                        session,
                                        list(reversed(found))[:dif_total_objects],
                                        model,
                                        name,
                                        ticker,
                                    )
                                    get_missing(session, model, name, ticker, cik)
                                    prev_req.date = datetime.datetime.now()
                                    prev_req.number = len(found)
                                    session.commit()
                    else:
                        print("NOT FOUND", cik)
            else:
                if cont:
                    print(
                        f"The company {name} is not in the USA and has no info on macrotrends and sharesoutstandinghistory. \
                            \nCheck the name and the ticker of this company and try again",
                    )
                else:
                    print(f"The company {name} is not in the USA")
