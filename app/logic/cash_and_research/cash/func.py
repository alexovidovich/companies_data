import math
import re
from datetime import datetime

from bs4 import BeautifulSoup

from logic.func import get_all_model_obj_by_name, get_hits, request_to_sec, write_db
from logic.utils import conv_time, standartify_str
from logic.var import headers_html, headers_json

from models.models import Number_of_objects

import requests


class Dive:
    def __init__(self, cls, times):
        self.cls = cls
        self.times = times
        return self.each_depth_times()

    def each_depth_times(self):
        for _ in range(self.times):
            if self.cls.parent:
                self.cls = self.cls.parent


def deep(each_cash_obj, path, url):
    for each_path in path:
        if each_cash_obj:
            each_cash_obj = each_cash_obj.get(each_path)

    if each_cash_obj:
        each_cash_obj = sorted(
            [
                {
                    "objects_from_api": each_cash_obj.get(key_for_search),
                    "currencies": key_for_search,
                }
                for key_for_search in each_cash_obj.keys()
                if len(key_for_search) < 5
            ],
            key=lambda x: len(x.get("objects_from_api")),
        )[-1]
        return {
            "values": each_cash_obj.get("objects_from_api"),
            "currency": each_cash_obj.get("currencies"),
            "url": url,
        }


def make_real_numbers_of_cash_and_cash_equivalents(
    last_cash_obj,
    cash_and_cash_equivalents,
):
    dif_1 = [
        last_cash_obj.cash_and_cash_equivalents,
        float(cash_and_cash_equivalents),
    ]
    if (max(dif_1) / min(dif_1)) > 10000:
        cash_and_cash_equivalents = round(float(cash_and_cash_equivalents) * 1000000, 2)
    elif (max(dif_1) / min(dif_1)) > 10:
        cash_and_cash_equivalents = round(float(cash_and_cash_equivalents) * 1000, 2)
    else:
        cash_and_cash_equivalents = round(float(cash_and_cash_equivalents), 2)
    return cash_and_cash_equivalents


def get_value_from_htm(html):
    final = []
    del_char = "[\n,. ]"
    find_tags = ["ix:nonfraction", "td"]
    depth = range(1, 6)
    for each_depth in depth:
        for find_tag in find_tags:
            final.append(
                [
                    add
                    for add in [
                        [
                            standartify_str(predicted_str_as_digit.text, ["\n"])
                            for predicted_str_as_digit in Dive(
                                each_html_part,
                                each_depth,
                            ).cls.find_all(find_tag)
                            if Dive(each_html_part, each_depth).cls.name == "tr"
                            and re.sub(
                                del_char, "", predicted_str_as_digit.text
                            ).isdigit()
                            and len(predicted_str_as_digit.text) > 3
                        ]
                        for each_html_part in html
                    ]
                    if 1 < len(add) < 3
                ]
            )
    final = tuple(set([tuple(elem[0]) for elem in final if elem]))
    if final:
        return final[0]


def cash_check_if_fresh_and_late_data_and_commit(
    session,
    model,
    name,
    to_base,
    param=None,
):
    fresh = (
        session.query(model)
        .filter(
            model.name == name,
            model.date == conv_time(to_base.get("date")),
            model.end_date < conv_time(to_base.get("end_date")),
        )
        .first()
    )
    same = (
        session.query(model)
        .filter(
            model.name == name,
            model.date == conv_time(to_base.get("date")),
            model.end_date == conv_time(to_base.get("end_date")),
            model.cash_and_cash_equivalents == to_base.get("cash_and_cash_equivalents"),
        )
        .first()
    )

    # db_date=date_now, db_start <= start_now,
    if fresh:
        session.delete(fresh)
    late_end = (
        session.query(model)
        .filter(
            model.name == name,
            model.end_date > conv_time(to_base.get("end_date")),
        )
        .first()
    )
    if not late_end and not same:
        write_db(model, session, to_base)


def get_all_hits_info(
    session,
    model,
    each_100_elem,
    company,
    req_body,
    url,
    number_of_one_page_object=100,
):
    name, ticker = company.get("name"), company.get("ticker")
    req_body.update(
        {"from": (each_100_elem - 1) * 100, "size": number_of_one_page_object}
    )
    api_response = request_to_sec(url, requests.post, headers_json, req_body)
    if api_response:
        try:
            hits = api_response.json().get("hits").get("hits")
        except:
            pass
        if hits:
            for hit in reversed(hits):
                all_database_obj = get_all_model_obj_by_name(session, model, name)
                last_cash_obj = all_database_obj[-1]
                last_date = last_cash_obj.date
                # get info about each_cash_object
                form, file_date, period_ending, new_url = get_hits(
                    hit, hit.get("_source").get("ciks")[0]
                )
                # if it has bigger date:
                if conv_time(file_date) > last_date:
                    # get the file
                    response = requests.get(new_url, headers=headers_html).text.lower()
                    pat, pat2 = (r"&#\d+;", r"&\w{1,5};")
                    response = re.sub(pat2, "", re.sub(pat, "", response))
                    main = BeautifulSoup(response, "lxml")
                    needed_html = list(
                        set(
                            [
                                main
                                for main in [
                                    next(
                                        (
                                            x
                                            for x in main.find_all(tag)
                                            if standartify_str(x.text, [" "], True)
                                            == "cashandcashequivalents"
                                        ),
                                        None,
                                    )
                                    for tag in ["div", "span", "p", "td", "font"]
                                ]
                                if main
                            ]
                        )
                    )
                    cash_and_cash_equivalents = get_value_from_htm(needed_html)
                    if cash_and_cash_equivalents:
                        cash_and_cash_equivalents = (
                            make_real_numbers_of_cash_and_cash_equivalents(
                                last_cash_obj,
                                standartify_str(
                                    cash_and_cash_equivalents[0], [" ", ","]
                                ),
                            )
                        )
                        to_base = {
                            "name": name,
                            "ticker": ticker,
                            "cash_and_cash_equivalents": float(
                                cash_and_cash_equivalents,
                            ),
                            "date": file_date,
                            "end_date": period_ending,
                            "form": form,
                        }
                        cash_check_if_fresh_and_late_data_and_commit(
                            session,
                            model,
                            name,
                            to_base,
                        )
                    else:
                        print(f"error-{name}:{file_date}----{form}")
                    print(new_url)


def find_missing(each_company, session, model, now, str_now):
    # iter companies
    print("in MISSING")
    ticker, name = each_company.get("ticker"), each_company.get("name")
    cik = each_company.get("cik")
    all_database_obj = get_all_model_obj_by_name(session, model, name)
    # get everything about company
    if all_database_obj:
        # took last object
        last_database_obj = all_database_obj[-1]
        # has all forms?
        if last_database_obj.date <= conv_time(
            f"{now.year}-{now.month}-{now.day}"
        ):  # ставить свежий год
            # check the edgar api to objects with links for html files
            # print("here")
            url = "https://efts.sec.gov/LATEST/search-index"
            req_body = {
                "category": "custom",
                "entityName": f"{cik}",
                "forms": ["10-K", "10-KT", "10-Q", "10-QT", "20-F", "40-F"],
                "startdt": "2016-10-13",
                "enddt": f"{str_now}",
                "from": 0,
                "size": 2,
            }
            api_response = request_to_sec(url, requests.post, headers_json, req_body)
            if api_response:
                response_from_api_edgar_json = api_response.json()
                total = (
                    response_from_api_edgar_json.get("hits").get("total").get("value")
                )
                position = "cash_and_cash_equivalents_html"
                prev_req = (
                    session.query(Number_of_objects)
                    .filter(
                        Number_of_objects.ticker == each_company.get("ticker"),
                        Number_of_objects.position == position,
                    )
                    .first()
                )
                if not prev_req:
                    for each_100_elem in range(1, math.ceil(int(total) / 100) + 1):
                        get_all_hits_info(
                            session,
                            model,
                            each_100_elem,
                            each_company,
                            req_body,
                            url,
                        )
                    number_obj = {
                        "company": each_company.get("name"),
                        "ticker": each_company.get("ticker"),
                        "date": datetime.now(),
                        "position": position,
                        "number": int(total),
                    }
                    prev_req = write_db(Number_of_objects, session, number_obj)
                else:
                    dif_hours = (
                        (datetime.now() - prev_req.date).seconds // 3600
                    ) < 24  # how many hours till next req
                    dif_total_objects = int(total) - prev_req.number
                    if dif_total_objects > 0:  # add dif_hours
                        for each_100_elem in range(
                            1, math.ceil(dif_total_objects / 100) + 1
                        ):
                            number_of_one_page_object_for_current_iter = (
                                dif_total_objects if dif_total_objects < 100 else 100
                            )
                            get_all_hits_info(
                                session,
                                model,
                                each_100_elem,
                                each_company,
                                req_body,
                                url,
                                number_of_one_page_object=number_of_one_page_object_for_current_iter,
                            )
                            dif_total_objects -= 100

                        prev_req.date = datetime.now()
                        prev_req.number = int(total)
                        session.commit()
