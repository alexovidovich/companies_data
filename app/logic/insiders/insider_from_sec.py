from datetime import datetime

from bs4 import BeautifulSoup


from logic.func import request_to_sec, write_db
from logic.insiders.func import get_stocks_rows
from logic.utils import conv_time
from logic.var import headers_html

from models.models import Number_of_objects, Transactions_and_holdings

import requests


def get_table(company, count):
    url = f"https://www.sec.gov/cgi-bin/own-disp?action=getissuer&CIK={company.get('cik')}&type=&dateb=&owner=include&start={count}"
    response = request_to_sec(url, requests.get, headers_html)
    main = BeautifulSoup(response.text, "lxml")
    table = main.find("div").find_all("table")[-1].find_all("tr")
    return table


def get_insider_transactions_from_sec(company, session, form_3_4_5_getting_info):
    last_object_date = None
    last_object_from_db = (
        session.query(Number_of_objects)
        .filter(
            Number_of_objects.ticker == company.get("ticker"),
            Number_of_objects.position == "transactions_and_holdings_sec_version",
        )
        .first()
    )
    if last_object_from_db:
        last_object_date_from_db = last_object_from_db.last_object_date
    count = 0
    all_transactions = []
    while True:
        stock_rows, source = get_stocks_rows(company.get("ticker"))
        table = get_table(company, count)
        if len(table) > 1:
            for each_tr in table:
                link = "https://www.sec.gov" + each_tr.find("a", href=True)["href"]
                response_for_details = request_to_sec(link, requests.get, headers_html)
                main_details = BeautifulSoup(response_for_details.text, "lxml")

                file_date = next(
                    (
                        x.parent.find_all("div")[1].text
                        for x in main_details.find_all("div", string="Filing Date")
                    ),
                    None,
                )

                period_ending = next(
                    (
                        x.parent.find_all("div")[1].text
                        for x in main_details.find_all("div", string="Period of Report")
                    ),
                    None,
                )

                if not last_object_date:
                    last_object_date = conv_time(period_ending)

                print(link, file_date, period_ending)
                splited_link = link.split("data/")
                document_link = next(
                    (
                        splited_link[0]
                        + "data/"
                        + "/".join(splited_link[1].split("/")[:1])
                        + "/"
                        + "/".join(x["href"].split("data/")[1].split("/")[1:])
                        for x in main_details.find_all("a")
                        if ".xml" in x.text
                    ),
                    None,
                )
                xml_or_html = request_to_sec(document_link, requests.get, headers_html)
                transaction = [x.text for x in each_tr.find_all("td")]

                if (
                    period_ending
                    and last_object_from_db
                    and last_object_date_from_db > conv_time(period_ending)
                ):
                    last_object_from_db.date = datetime.now()
                    last_object_from_db.last_object_date = last_object_date
                    return
                if file_date and conv_time(file_date) < conv_time("2013-01-01"):
                    write_db(
                        Number_of_objects,
                        session,
                        obj_to_write={
                            "company": company.get("name"),
                            "ticker": company.get("ticker"),
                            "date": datetime.now(),
                            "position": "transactions_and_holdings_sec_version",
                            "last_object_date": last_object_date,
                        },
                    )
                    return
                url_in_database = (
                    session.query(Transactions_and_holdings)
                    .filter(
                        Transactions_and_holdings.url == document_link,
                    )
                    .first()
                )
                print(url_in_database)

                if (
                    transaction
                    and not url_in_database
                    and conv_time(file_date) > conv_time("2013-01-01")
                ):
                    form = transaction[4]

                    form_3_4_5_getting_info(
                        session,
                        company,
                        source,
                        stock_rows,
                        file_date,
                        period_ending,
                        form,
                        document_link,
                        xml_or_html,
                    )

        else:
            print("end")
            print(len(all_transactions))
            write_db(
                Number_of_objects,
                session,
                obj_to_write={
                    "company": company.get("name"),
                    "ticker": company.get("ticker"),
                    "date": datetime.now(),
                    "position": "transactions_and_holdings_sec_version",
                    "last_object_date": last_object_date,
                },
            )
            return
        count += 80
