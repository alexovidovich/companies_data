import csv
import datetime
import time

from core.db import SessionLocal

from logic.cash_and_research.cash.func import deep, find_missing
from logic.cash_and_research.write_data import write_data
from logic.func import get_company_cik, is_uk_company, write_db
from logic.utils import deconv_time
from logic.var import headers_sec as headers, timeout

from models.models import Number_of_objects

import requests


def cash_or_research(
    ticker,
    name,
    keys,
    model,
    cik=None,
    uk=False,
    param=None,
    session=None,
):
    time.sleep(1)
    csvFilePath = "data/countries.csv"
    with open(csvFilePath) as csv_file:
        companies = csv.DictReader(csv_file)
        condition = is_uk_company(
            ticker,
            companies,
            uk,
        )
        if condition:
            if not cik:
                cik = get_company_cik(
                    name,
                    ticker,
                )
            if cik:
                url = f"http://data.sec.gov/api/xbrl/companyfacts/CIK{str(cik)}.json"
                print(url)
                req = requests.get(url, headers=headers, timeout=timeout)
                if "NoSuchKey" not in req.text:
                    req_obj = req.json()
                    found = None
                    working_keys = [
                        each_working_key.split(".") for each_working_key in keys
                    ]
                    found = sorted(
                        [
                            to_found
                            for to_found in [
                                deep(req_obj, path_get, url)
                                for path_get in working_keys
                            ]
                            if to_found and to_found.get("values")
                        ],
                        key=lambda x: len(x.get("values")),
                    )
                    if found:
                        print(param)
                        prev_req = (
                            session.query(Number_of_objects)
                            .filter(
                                Number_of_objects.ticker == ticker,
                                Number_of_objects.position == param,
                            )
                            .first()
                        )
                        if not prev_req:
                            obj_of_current_company = {
                                "each_company": {
                                    "name": name,
                                    "ticker": ticker,
                                },
                                "list_of_ready_info": found[-1],
                            }
                            write_data(obj_of_current_company, session, model, param)
                            is_in_db_after_func = (
                                session.query(model)
                                .filter(
                                    model.ticker == ticker,
                                )
                                .first()
                            )
                            if is_in_db_after_func:
                                number_of_objects_in_each_company = {
                                    "company": name,
                                    "ticker": ticker,
                                    "date": datetime.datetime.now(),
                                    "position": param,
                                    "number": len(found[-1].get("values")),
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
                            dif_total_objects = (
                                int(len(found[-1].get("values"))) - prev_req.number
                            )
                            print(dif_total_objects)
                            if dif_total_objects > 0:  # add dif_hours
                                # print(found[-1])
                                found[-1].update(
                                    {
                                        "values": list(
                                            list(reversed(found[-1].get("values")))[
                                                :dif_total_objects
                                            ]
                                        )
                                    }
                                )
                                obj_of_current_company = {
                                    "each_company": {
                                        "name": name,
                                        "ticker": ticker,
                                    },
                                    "list_of_ready_info": found[-1],
                                }
                                write_data(
                                    obj_of_current_company, session, model, param
                                )
                                prev_req.date = datetime.datetime.now()
                                prev_req.number = int(len(found[-1].get("values")))
                                session.commit()


def check_api_for_cash_or_research(table, model, param, keys):
    # "cash_and_cash_equivalents" cash
    now = datetime.datetime.now()
    str_now = deconv_time(now)
    with SessionLocal() as session:
        for each_company in table:

            cash_or_research(
                each_company.get("ticker"),
                each_company.get("name"),
                cik=each_company.get("cik"),
                keys=keys,
                model=model,
                param=param,
                session=session,
                uk=True,
            )
            if param == "cash_and_cash_equivalents":
                find_missing(each_company, session, model, now, str_now)
