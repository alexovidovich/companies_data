import math
from datetime import datetime
from functools import reduce

from bs4 import BeautifulSoup

from core.db import SessionLocal

from logic.func import (
    get_hits,
    request_to_sec,
    write_db,
)
from logic.insiders.func import (
    get_historical_prices,
    get_stocks_rows,
    get_text,
    security_title_filter,
    unite_derivatives_nonderivatives_and_commit,
    write_owner_db,
)
from logic.insiders.insider_from_sec import get_insider_transactions_from_sec
from logic.insiders.insiders_6k_missing import get_html_tables
from logic.utils import conv_time, deconv_time, standartify_str
from logic.var import headers_html, headers_json

from models.models import Number_of_objects, Transactions_and_holdings

import requests


def create_owner_list(session, all_owners):
    owners = [
        {
            "cik": get_text(owner.find("rptownercik")),
            "name": get_text(owner.find("rptownername")),
            "is_director": get_text(owner.find("isdirector"), True),
            "is_officer": get_text(owner.find("isofficer"), True),
            "is_ten_percent_owner": get_text(
                owner.find("istenpercentowner"),
                True,
            ),
            "is_other": get_text(owner.find("isother"), True),
            "officer_title": get_text(owner.find("officertitle")),
            "other_text": get_text(owner.find("othertext")),
        }
        for owner in all_owners
    ]
    owners = write_owner_db(session=session, owners=owners)
    return owners


def transaction_code_generator(transaction_code):
    if transaction_code:
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
        market = ["p", "s"]
        for symb in market:
            if symb in transaction_code:
                return "1"
        if "n/a" in transaction_code:
            return None
        else:
            return "0"
    return None


def make_obj_for_db(source, stock_rows, table, what_to_search, owner_and_issuer_obj):
    db_obj = [
        {
            "security_title": security_title_filter(
                get_text(recieved_obj.find("securitytitle")), what_to_search
            ),
            "transaction_date": conv_time(
                get_text(recieved_obj.find("transactiondate"), date=True),
            ),
            "transaction_code": transaction_code_generator(
                get_text(recieved_obj.find("transactioncode"))
            ),
            "equity_swap_involved": get_text(recieved_obj.find("equityswapinvolved")),
            "transaction_shares": get_text(
                recieved_obj.find("transactionshares"), float_=True
            )
            or get_text(recieved_obj.find("underlyingsecurityshares"), float_=True),
            "shares_owned_following_transaction": get_text(
                recieved_obj.find("sharesownedfollowingtransaction"), float_=True
            ),
            "transaction_price_per_share": get_text(
                recieved_obj.find("transactionpricepershare")
            ),
            "market_price": get_historical_prices(
                stock_rows,
                date=owner_and_issuer_obj.get("period_ending"),
            )
            if source == "nasdaq"
            else get_historical_prices(
                stock_rows, date=owner_and_issuer_obj.get("period_ending"), format=True
            ),
            "underlying_security_title": security_title_filter(
                get_text(recieved_obj.find("underlyingsecuritytitle")),
                what_to_search,
                underlying=True,
            ),
            "conversion_or_exercise_price": get_text(
                recieved_obj.find("conversionorexerciseprice")
            ),
            "transaction_acquired_disposed_code": get_text(
                recieved_obj.find("transactionacquireddisposedcode")
            ),
            "exercise_date": conv_time(
                get_text(recieved_obj.find("exercisedate"), date=True),
            ),
            "expiration_date": conv_time(
                get_text(recieved_obj.find("expirationdate"), date=True),
            ),
            "direct_or_indirect_ownership": get_text(
                recieved_obj.find("directorindirectownership")
            ),
            "nature_of_ownership": get_text(recieved_obj.find("natureofownership")),
            "type": what_to_search,
        }
        for recieved_obj in table.find_all(
            what_to_search,
        )
        if recieved_obj
    ]
    print(db_obj)

    return [
        {
            **each_obj,
            **owner_and_issuer_obj,
        }
        for each_obj in db_obj
        if each_obj
        and each_obj.get("security_title")
        and (
            each_obj.get("transaction_shares")
            or each_obj.get("shares_owned_following_transaction")
        )
        # and each_obj.get("transaction_price_per_share")
        and (
            owner_and_issuer_obj.get("company_ticker").lower()
            == owner_and_issuer_obj.get("issuer_ticker").lower()
            or int(owner_and_issuer_obj.get("issuer_cik"))
            == int(owner_and_issuer_obj.get("company_cik"))
        )
    ]


def find_info_in_table(
    source, stock_rows, table, owner_and_issuer_obj, what_table_types: list
):
    info_list = (
        reduce(
            lambda x, y: x + y,
            [
                make_obj_for_db(
                    source,
                    stock_rows,
                    table,
                    type,
                    owner_and_issuer_obj,
                )
                for type in what_table_types
            ],
        )
        if table
        else None
    )
    # print(info_list)
    if info_list:
        return info_list
    else:
        return []


def form_3_4_5_getting_info(
    session,
    company,
    source,
    stock_rows,
    file_date,
    period_ending,
    form,
    url,
    xml_or_html,
):
    main = BeautifulSoup(xml_or_html.text.lower(), "lxml")
    period_of_report = get_text(main.find("periodofreport"))
    issuer = main.find("issuer")
    issuer_cik = get_text(issuer.find("issuercik")) if issuer else None
    issuer_name = get_text(issuer.find("issuername")) if issuer else None
    issuer_ticker = get_text(issuer.find("issuertradingsymbol")) if issuer else None
    owners = create_owner_list(session, main.find_all("reportingowner"))
    owner_and_issuer_obj = {
        "url": url,
        "company_name": company.get("name"),
        "company_ticker": company.get("ticker"),
        "company_cik": company.get("cik"),
        "period_of_report": conv_time(get_text(period_of_report, date=True)),
        "file_date": conv_time(get_text(file_date, date=True)),
        "period_ending": conv_time(get_text(period_ending, date=True)),
        "owners": owners,
        "issuer_cik": issuer_cik,
        "issuer_name": issuer_name,
        "issuer_ticker": issuer_ticker,
        "transaction_form_type": str(form),
    }
    print(owner_and_issuer_obj)
    non_derivative_table = main.find("nonderivativetable")
    derivative_table = main.find("derivativetable")

    non_derivative = find_info_in_table(
        source,
        stock_rows,
        non_derivative_table,
        owner_and_issuer_obj,
        [
            "nonderivativeholding",
            "nonderivativetransaction",
        ],
    )
    derivative = find_info_in_table(
        source,
        stock_rows,
        derivative_table,
        owner_and_issuer_obj,
        [
            "derivativeholding",
            "derivativetransaction",
        ],
    )
    if derivative or non_derivative:
        print("to_form")
        unite_derivatives_nonderivatives_and_commit(session, non_derivative, derivative)
    else:
        print("to_db")
        raw = write_db(Transactions_and_holdings, session, {"url": url})
        print(raw)
    print(url)


def get_all_hits_info(
    session,
    each_100_elem,
    company,
    req_body,
    url,
    number_of_one_page_object=100,
    func_to_get_doc_info=None,
):
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
            stock_rows, source = get_stocks_rows(company.get("ticker"))

            for hit in hits:
                cik = hit.get("_source").get("ciks")[0]
                form, file_date, period_ending, new_url = get_hits(hit, cik)
                url_in_database = (
                    session.query(Transactions_and_holdings)
                    .filter(
                        Transactions_and_holdings.url == new_url,
                    )
                    .first()
                )

                if not url_in_database:
                    print("URL NOT IN DATABASE")
                    print(new_url)
                    xml_or_html = request_to_sec(new_url, requests.get, headers_html)
                    if xml_or_html:
                        func_to_get_doc_info(
                            session,
                            company,
                            source,
                            stock_rows,
                            file_date,
                            period_ending,
                            form,
                            new_url,
                            xml_or_html,
                        )
                    else:
                        print("connection error")
    else:
        print("connection error")


def main_insider(session, company, url, forms, position, func_to_get_doc_info, q=""):
    req_body = {
        "q": q,
        "dateRange": "custom",
        "category": "custom",
        "ciks": [company.get("cik")],
        "entityName": company.get("name"),
        "startdt": "2013-01-01",
        "enddt": "{}".format(deconv_time(datetime.now())),
        "forms": forms,
        "from": 0,
        "size": 2,
    }
    api_response = request_to_sec(url, requests.post, headers_json, req_body)
    if api_response:
        total = api_response.json().get("hits").get("total").get("value")
        prev_req = (
            session.query(Number_of_objects)
            .filter(
                Number_of_objects.ticker == company.get("ticker"),
                Number_of_objects.position == position,
            )
            .first()
        )
        if not prev_req:

            for each_100_elem in range(1, math.ceil(int(total) / 100) + 1):
                get_all_hits_info(
                    session,
                    each_100_elem,
                    company,
                    req_body,
                    url,
                    func_to_get_doc_info=func_to_get_doc_info,
                )
            is_in_db_after_func = (
                session.query(Transactions_and_holdings)
                .filter(
                    Transactions_and_holdings.company_ticker == company.get("ticker"),
                )
                .first()
            )
            if is_in_db_after_func:
                condition = (
                    ".xml" in is_in_db_after_func.url
                    if position == "transactions_and_holdings"
                    else ".xml" not in is_in_db_after_func.url
                )
                if condition:
                    number_obj = {
                        "company": company.get("name"),
                        "ticker": company.get("ticker"),
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
                number_of_one_page_object_for_current_iter = 0
                for each_100_elem in range(1, math.ceil(dif_total_objects / 100) + 1):
                    number_of_one_page_object_for_current_iter = (
                        dif_total_objects if dif_total_objects < 100 else 100
                    )
                    get_all_hits_info(
                        session,
                        each_100_elem,
                        company,
                        req_body,
                        url,
                        number_of_one_page_object=number_of_one_page_object_for_current_iter,
                        func_to_get_doc_info=func_to_get_doc_info,
                    )
                    dif_total_objects -= 100
                prev_req.date = datetime.now()
                prev_req.number = int(total)
                session.commit()
    else:
        print("connection error")


def init_insiders(company):
    with SessionLocal() as session:
        print(company)
        url = "https://efts.sec.gov/LATEST/search-index"
        company_in_db_by_html = (
            session.query(Number_of_objects)
            .filter(
                Number_of_objects.ticker == company.get("ticker"),
                Number_of_objects.position
                == "transactions_and_holdings_html_version_6k",
            )
            .first()
        )
        if not company_in_db_by_html:
            main_insider(
                session=session,
                company=company,
                url=url,
                forms=["3", "4", "5"],
                position="transactions_and_holdings",
                func_to_get_doc_info=form_3_4_5_getting_info,
            )
            get_insider_transactions_from_sec(
                company=company,
                session=session,
                form_3_4_5_getting_info=form_3_4_5_getting_info,
            )
        company_in_db = (
            session.query(Number_of_objects)
            .filter(
                Number_of_objects.ticker == company.get("ticker"),
                Number_of_objects.position == "transactions_and_holdings",
            )
            .first()
        )
        if not company_in_db:
            main_insider(
                session=session,
                company=company,
                url=url,
                forms=["6-K"],
                position="transactions_and_holdings_html_version_6k",
                func_to_get_doc_info=get_html_tables,
                q="transaction",
            )
