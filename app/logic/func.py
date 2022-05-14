import csv
import json
import re
import time

from bs4 import BeautifulSoup

from logic.names.utils import normalize_name
from logic.utils import conv_time, standartify_str
from logic.var import headers_html as headers

import requests


def get_hits(each_hit, cik):
    period_ending = each_hit.get("_source").get("period_ending")
    file_date = each_hit.get("_source").get("file_date")
    form = each_hit.get("_source").get("form")
    id = each_hit.get("_id").split(":")
    id = (
        id[0].replace("-", "").replace(":", "/") + "/" + id[1]
        if not re.search(r":\d\d\d\d.xml", ":" + id[1])
        else id[0].replace("-", "").replace(":", "/") + "/" + id[0] + "-" + id[1]
    )
    new_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{id}"
    return form, file_date, period_ending, new_url


def write_db(model, session, obj_to_write):
    company = model(**obj_to_write)
    session.add(company)
    session.flush()
    session.commit()
    session.refresh(company)
    return company


def check(i, form):
    if i[0] in form.replace("-", "").lower():
        if i[1] == "not6" and "6" not in form:
            return True
        elif i[1] == "6" and "6" in form:
            return True
        elif i[1] == "":
            return True
        return False


def remove_nesting(main_dict, main=None, priv_name=None, iter_i=0):
    new_dict = main_dict.copy()
    for each in main_dict:
        if isinstance(main_dict.get(each), dict):
            new_name = priv_name + "." + each if priv_name else each
            if iter_i == 0:
                remove_nesting(main_dict.get(each), new_dict, new_name, iter_i + 1)
            else:
                remove_nesting(main_dict.get(each), main, new_name, iter_i + 1)
        else:
            if iter_i > 0:
                main[priv_name + "." + each] = main_dict.get(each)
    final = new_dict.copy()
    for each in new_dict:
        if isinstance(new_dict.get(each), dict):
            del final[each]
    return final


def get_per_of_45_days_from_file(file):
    per = []
    without_45 = []
    history_first = read_json(file)
    file_date = ""
    end_date = ""
    for each_obj in history_first:
        file_date = each_obj.get("file_date")
        end_date = each_obj.get("period_ending")
        delta = conv_time(file_date) - conv_time(end_date)
        per.append(delta.days)
        if delta.days <= 45:
            without_45.append(each_obj)
    print(len([x for x in per if x > 55]) / len(per) * 100)


def read_json(file_name):
    with open(file_name, "r") as f:
        return json.load(f)


def write_json(file_name, what_to_write):
    with open(file_name, "w") as f:
        json.dump(what_to_write, f, indent=2)


def get_all_model_obj_by_name(session, model, name):
    return sorted(
        list(session.query(model).filter(model.name == name).all()),
        key=lambda each_database_obj: each_database_obj.date,
    )


def sort_data_of_one_company(file):
    already_read = read_json(file)
    already_sorted = sorted(already_read, key=lambda k: k["file_date"])
    write_json(file, already_sorted)


def find_full_name(ticker):
    url = f"https://www.nasdaq.com/market-activity/stocks/{ticker}"
    print(url, headers)
    req_obj = requests.get(url, headers=headers).text
    # print(req_obj)
    main = BeautifulSoup(req_obj, "lxml")
    real_uk_name = (
        main.find("span", {"class": "symbol-page-header__name"})
        .text.lower()
        .split("plc")[0]
        + "plc"
    )
    return real_uk_name


def make_cik(each_comp):
    return "0" * (10 - len(str(each_comp.get("cik_str")))) + str(
        each_comp.get("cik_str")
    )


def get_company_cik(name, ticker=None):
    splited_name = name.split()
    name = ""
    for each_part_slited in splited_name:
        name += each_part_slited + " "
    name = name.strip()
    csvFilePath = "data/names.csv"
    with open(csvFilePath) as csv_file:
        companies = csv.DictReader(csv_file)
        for company in companies:
            # print(name.lower(), company.get("name").lower())
            if ticker and company.get("ticker").lower() == ticker.lower():
                return company.get("cik")
            elif not ticker and (
                company.get("current_name")
                and company.get("formerly_names")
                and company.get("formerly_names").split("||")
                and normalize_name(name) in normalize_name(company.get("name"))
                or normalize_name(name) in normalize_name(company.get("current_name"))
                or normalize_name(name) in normalize_name(company.get("original_names"))
                or next(
                    (
                        True
                        for x in company.get("formerly_names").split("||")
                        if normalize_name(name) in normalize_name(x)
                    ),
                    False,
                )
            ):
                print("return")
                return (company.get("cik"), company.get("ticker"))
            elif normalize_name(name) in normalize_name(company.get("name")):
                print("return")
                return (company.get("cik"), company.get("ticker"))
    print("return")
    return (None, None)


def is_uk_company(ticker, companies, uk):
    return (
        any(
            company["ticker"] == ticker and company.get("country") != "United Kingdom"
            for company in companies
        )
        if not uk
        else True
    )


def exchanging_to_usd(amount, currency, date):
    if standartify_str(str(amount), [" ", ",", "."]) != "0" and amount != 0:
        url = f"https://www.x-rates.com/historical/?from={currency}&amount={amount}&date={date}"
        print(url)
        d = requests.get(url).text
        got = BeautifulSoup(d, features="lxml")
        try:
            usd = [
                x.find_all("td")[1].text
                for x in got.find_all("table")[0].find("tbody").find_all("tr")
                if standartify_str(x.find_all("td")[0].text, [" "], True) == "usdollar"
            ]
            return float(usd[0])
        except:
            return None
    return 0


def request_to_sec(url, method, headers, req_body=None, count=0):
    if count < 10:
        try:
            params = {"url": url}
            if method.__name__ == "post":
                params.update({"json": req_body})
            params.update({"headers": headers})
            time.sleep(0.07)
            response = method(**params)
            if not response.text:
                time.sleep(0.07)
                response = method(**params)
            return response
        except:
            count += 1
            return request_to_sec(url, method, headers, req_body=None, count=count)
    else:
        return


def open_csv(path):
    with open(path, "r") as f:
        file_dict = csv.DictReader(f)
        file_dict = [x for x in file_dict]
        return file_dict


def save_data_to_csv(headers, records, filepath, mode="a+"):
    with open(filepath, mode=mode, newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if mode == "w":
            writer.writerow(headers)
        if records:
            writer.writerow(records)
