import datetime
import math

from core.db import SessionLocal

from dateutil.relativedelta import relativedelta

from logic.f13.parse import txt_parse, xml_parse
from logic.func import get_hits, request_to_sec, write_db
from logic.utils import conv_time, deconv_time
from logic.var import headers_html, headers_json

from models.models import (
    Institutional_holdings_2,
    Institutional_holdings_raw_3,
    Number_of_objects,
    SEC,
    UK,
)

import requests


def get_all_hits_info(
    session,
    each_100_elem,
    name,
    ticker,
    req_body,
    url,
    number_of_one_page_object=100,
):
    req_body.update(
        {"from": (each_100_elem - 1) * 100, "size": number_of_one_page_object},
    )
    api_response = request_to_sec(url, requests.post, headers_json, req_body)
    if api_response:
        try:
            hits = api_response.json().get("hits").get("hits")
        except:
            hits = None
        if hits:
            real_name = name
            splited = name.split(" ")
            if len(splited) > 2:
                name = splited[0] + splited[1]
            name = name.lower().replace(" ", "")
            for hit in hits:
                cik = hit.get("_source").get("ciks")[0]
                form, file_date, period_ending, new_url = get_hits(hit, cik)
                url_in_database = (
                    session.query(Institutional_holdings_raw_3)
                    .filter(
                        Institutional_holdings_raw_3.url == new_url,
                        Institutional_holdings_raw_3.ticker == ticker,
                    )
                    .first()
                )

                if not url_in_database:
                    print("not in db")
                    print(new_url)
                    xml_or_html = request_to_sec(new_url, requests.get, headers_html)
                    if xml_or_html:
                        xml_or_html = xml_or_html.text
                        clas = ""
                        # start parsing
                        if ".xml" in new_url.lower()[-6:]:
                            share, clas = xml_parse(xml_or_html, name)
                        elif ".txt" in new_url.lower()[-6:]:
                            share, clas = txt_parse(xml_or_html, real_name)
                        else:
                            share = ""
                        print(share)
                        if share or share == 0:
                            if clas.lower().replace(" ", "") == "sh":
                                obj_to_write = {
                                    "url": new_url,
                                    "name": real_name,
                                    "ticker": ticker,
                                    "file_date": file_date,
                                    "end_date": period_ending,
                                    "shares": share,
                                    "cik": cik,
                                    "form": form,
                                }
                                write_db(
                                    Institutional_holdings_raw_3, session, obj_to_write
                                )
                            else:
                                print("only url to db")
                                obj_to_write = {
                                    "ticker": ticker,
                                    "url": new_url,
                                }
                                write_db(
                                    Institutional_holdings_raw_3, session, obj_to_write
                                )
                        else:
                            print("only url to db")
                            obj_to_write = {
                                "ticker": ticker,
                                "url": new_url,
                            }
                            write_db(
                                Institutional_holdings_raw_3, session, obj_to_write
                            )
                    else:
                        print("got_connection_error", new_url)
                else:
                    print("url in db")
        else:
            print("connection lost hits")


def get_xml_f13(session, URL, name, ticker, start, end, track):
    req_body = {
        "q": name,
        "dateRange": "custom",
        "category": "custom",
        "startdt": start,
        "enddt": end,
        "forms": ["13F-HR", "13F-NT", "13FCONP"],
        "from": 0,
        "size": 2,
    }
    api_response = request_to_sec(URL, requests.post, headers_json, req_body)
    position = f"institutional_holdings:{start}"
    print(req_body)
    if api_response:
        try:
            total = api_response.json().get("hits").get("total").get("value")
        except:
            api_response = request_to_sec(URL, requests.post, headers_json, req_body)
            first_hits = api_response.json().get("hits")
            if first_hits:
                total = first_hits.get("total").get("value")
            else:
                total = 0
        prev_req = (
            session.query(Number_of_objects)
            .filter(
                Number_of_objects.ticker == ticker,
                Number_of_objects.position == position,
            )
            .first()
        )

        if not prev_req:
            for each_100_elem in range(1, math.ceil(int(total) / 100) + 1):

                # func place
                get_all_hits_info(
                    session,
                    each_100_elem,
                    name,
                    ticker,
                    req_body,
                    URL,
                )
            is_in_db_after_func = (
                session.query(Institutional_holdings_raw_3)
                .filter(
                    Institutional_holdings_raw_3.ticker == ticker,
                )
                .first()
            )
            if is_in_db_after_func:
                number_obj = {
                    "company": name,
                    "ticker": ticker,
                    "date": datetime.datetime.now(),
                    "position": position,
                    "number": int(total),
                }
                prev_req = write_db(Number_of_objects, session, number_obj)
        else:
            dif_hours = (
                (datetime.datetime.now() - prev_req.date).seconds // 3600
            ) < 24  # how many hours till next req
            dif_total_objects = int(total) - prev_req.number
            if dif_total_objects > 0:  # add dif_hours
                for each_100_elem in range(1, math.ceil(dif_total_objects / 100) + 1):
                    number_of_one_page_object_for_current_iter = (
                        dif_total_objects if dif_total_objects < 100 else 100
                    )
                    # func place
                    get_all_hits_info(
                        session,
                        each_100_elem,
                        name,
                        ticker,
                        req_body,
                        URL,
                        number_of_one_page_object=number_of_one_page_object_for_current_iter,
                    )
                    dif_total_objects -= 100
                prev_req.date = datetime.datetime.now()
                prev_req.number = int(total)
                session.commit()

    else:
        print("connection problem")


def percentage(session, final, name, ticker, alg):
    print(final, "final_len", len(final))
    print(alg)
    sec = list(
        session.query(SEC)
        .filter(
            SEC.ticker == ticker,
        )
        .all()
    )
    uk = list(
        session.query(UK)
        .filter(
            UK.ticker == ticker,
        )
        .all()
    )
    companies = [
        dict((col, getattr(row, col)) for col in row.__table__.columns.keys())
        for row in sec + uk
    ]

    check = [
        (str(company.get("date")), float(company.get("shares_outstanding")))
        for company in companies
        if company.get("name").lower() == name.lower()
    ]
    print(check, "check")
    for index, each in enumerate(final):
        period_ending = conv_time(each.get("file_date"))
        for each_check in range(1, len(check)):
            check_date_1 = conv_time(check[each_check - 1][0][:-9])
            check_date_2 = conv_time(check[each_check][0][:-9])
            check_end = conv_time(check[-1][0][:-9])
            check_start = conv_time(check[1][0][:-9])

            if not each.get("done"):
                if (
                    each_check == 1
                    and period_ending < check_start
                    or check_date_1 <= period_ending <= check_date_2
                ):
                    per = round(
                        (
                            each.get("shares")
                            / (float(check[each_check - 1][1]) * 1000000)
                        )
                        * 100,
                        6,
                    )
                    final[index]["value"] = final[index]["shares"]
                    final[index]["shares"] = per
                    final[index]["done"] = True
                elif (
                    each_check == list(range(1, len(check)))[-1]
                    and period_ending > check_end
                ):
                    per = round(
                        (each.get("shares") / (float(check[each_check][1]) * 1000000))
                        * 100,
                        6,
                    )
                    final[index]["value"] = final[index]["shares"]
                    final[index]["shares"] = per
                    final[index]["done"] = True

    with SessionLocal() as session:
        for each_obj in final:
            found = (
                session.query(Institutional_holdings_2)
                .filter(
                    Institutional_holdings_2.name == name,
                    Institutional_holdings_2.file_date
                    == conv_time(each_obj.get("file_date")),
                    Institutional_holdings_2.end_date
                    == conv_time(each_obj.get("end_date")),
                    Institutional_holdings_2.alg == alg,
                )
                .first()
            )
            if not found:
                obj_to_write = {
                    "name": name,
                    "ticker": ticker,
                    "file_date": each_obj.get("file_date"),
                    "end_date": each_obj.get("end_date"),
                    "form": "F-13",
                    "percentage": each_obj.get("shares"),
                    "shares": each_obj.get("value"),
                    "alg": alg,
                }
                in_db = (
                    session.query(Institutional_holdings_2)
                    .filter(
                        Institutional_holdings_2.ticker == ticker,
                        Institutional_holdings_2.file_date
                        == obj_to_write.get("file_date"),
                        Institutional_holdings_2.end_date
                        == obj_to_write.get("end_date"),
                        Institutional_holdings_2.percentage
                        == obj_to_write.get("percentage"),
                        Institutional_holdings_2.shares == obj_to_write.get("shares"),
                        Institutional_holdings_2.alg == obj_to_write.get("alg"),
                    )
                    .first()
                )
                if not in_db:
                    print(obj_to_write, "object_to_write")
                    write_db(Institutional_holdings_2, session, obj_to_write)
    return final


def create_real_history_data_of_one_company(session, name, ticker, history_first, alg):
    print(history_first, "final_len_2", len(history_first))
    without = []
    history_first = sorted(history_first, key=lambda x: x.get("file_date"))
    if alg != 1:
        cut = 137 if alg == 3 else 45
        for each_obj in history_first:
            file_date = each_obj.get("file_date")
            end_date = each_obj.get("period_ending")
            delta = conv_time(file_date) - conv_time(end_date)
            if delta.days <= cut:
                without.append(each_obj)
        history_first = sorted(without, key=lambda x: x.get("file_date"))
    founds = []
    final = []
    end_date_prev_q = ""
    file_date = ""
    end_date = ""
    for each_obj in history_first:
        if alg != 1 and end_date:
            if conv_time(each_obj.get("file_date")) > conv_time(
                end_date
            ) + relativedelta(days=45):
                if each_obj.get("period_ending") != end_date:
                    for index, each_found in enumerate(founds):
                        condition = (
                            each_found.get("period_ending") != end_date
                            and each_found.get("period_ending") != end_date_prev_q
                            if alg == 3
                            else each_found.get("period_ending") != end_date
                        )
                        if condition:
                            each_found.update({"shares": 0.0})
                            founds[index] = each_found
        if each_obj.get("file_date") != file_date:
            if end_date and file_date:
                sum_shares = sum([x.get("shares") for x in founds])
                final.append(
                    {"file_date": file_date, "end_date": end_date, "shares": sum_shares}
                )
        index, x = next(
            (
                (index, x)
                for index, x in enumerate(founds)
                if x.get("cik") == each_obj.get("cik")
            ),
            (None, None),
        )
        if x:
            x.update(
                {
                    "shares": each_obj.get("shares"),
                    "period_ending": each_obj.get("period_ending"),
                }
            )
            founds[index] = x
        else:
            founds.append(
                {
                    "cik": each_obj.get("cik"),
                    "period_ending": each_obj.get("period_ending"),
                    "shares": each_obj.get("shares"),
                }
            )
        file_date = each_obj.get("file_date")
        if end_date and each_obj.get("period_ending") != end_date:
            end_date_prev_q = end_date
        end_date = each_obj.get("period_ending")
    percentage(session, final, name, ticker, alg)


def main(company):
    name, ticker = company.get("name"), company.get("ticker")
    with SessionLocal() as session:
        before_exe = (
            session.query(Institutional_holdings_raw_3)
            .filter(
                Institutional_holdings_raw_3.ticker == ticker,
            )
            .all()
        )
        url = "https://efts.sec.gov/LATEST/search-index"
        now_date = datetime.datetime.now()

        old = conv_time("2013-01-01")
        print(old)
        delta = math.ceil((now_date - old).days / 365)
        print(delta)
        for track in range(delta * 4):
            if (old + relativedelta(months=3)) < now_date:
                get_xml_f13(
                    session,
                    url,
                    name,
                    ticker,
                    deconv_time(old),
                    deconv_time((old + relativedelta(months=3))),
                    track,
                )
            else:
                get_xml_f13(
                    session,
                    url,
                    name,
                    ticker,
                    deconv_time(old),
                    deconv_time(now_date),
                    track,
                )
                break

            old += relativedelta(months=+3)
        after_exe = (
            session.query(Institutional_holdings_raw_3)
            .filter(
                Institutional_holdings_raw_3.ticker == ticker,
            )
            .all()
        )

        if after_exe and (len(after_exe) - len(before_exe)) > 0:
            shares = [
                {
                    "period_ending": deconv_time(x.end_date),
                    "file_date": deconv_time(x.file_date),
                    "cik": x.cik,
                    "shares": x.shares,
                    "form": x.form,
                }
                for x in session.query(Institutional_holdings_raw_3)
                .filter(Institutional_holdings_raw_3.name == name)
                .all()
            ]
            for alg in range(1, 4):
                create_real_history_data_of_one_company(
                    session, name, ticker, shares, alg
                )
