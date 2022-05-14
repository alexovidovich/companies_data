import re
from datetime import timedelta

from bs4 import BeautifulSoup

from logic.func import get_company_cik, write_db
from logic.insiders.func import (
    convert_pence,
    convert_symbol_to_usd,
    get_historical_prices,
    get_text,
    make_normal_date,
    transaction_code_generator,
    understand_derivative_or_not,
    unite_derivatives_nonderivatives_and_commit,
    write_owner_db,
)
from logic.utils import conv_time, standartify_str

from models.models import Transactions_and_holdings


def get_from_row(where_to_search, word_to_search):
    value = next(
        (
            next(
                standartify_str(each_td_inside.text, ["\n", "\xa0"])
                for each_td_inside in list(reversed(each_row.find_all("td")))
                if len(each_td_inside.text) > 5
            )
            for each_row in where_to_search
            if word_to_search.replace(" ", "")
            in standartify_str(each_row.text, ["\n", "\xa0", " "], True)
        ),
        None,
    )
    return value


def my_find_all(x):
    result = re.findall(
        r"(?:\s*([\£|\$]\s*\d+\.*\d*)\s*|(\d+\.*\d*\s*pence)\s*|\s*(usd\s*\d+\.*\d*)\s*|\s*(gbp\s*\d+\.*\d*)\s*|\s*(dkk\s*\d+\.*\d*)\s*|(\d+\.*\d*\s*dkk)\s*|^\s*(0)\s*$)",
        x,
    )
    if result:
        return result[0]
    return [" "]


def get_from_tr(where_to_search, words_to_search="", reverse=None):
    volume_lst = []
    price_lst = []
    for each_row in where_to_search:
        in_here = False
        for word_to_search in words_to_search:
            if reverse:
                if word_to_search.replace(" ", "") in standartify_str(
                    each_row.text, ["\n", "\xa0", " ", ","], True
                ):
                    in_here = True
            else:
                if (
                    word_to_search.replace(" ", "")
                    in standartify_str(each_row.text, ["\n", "\xa0", " ", ","], True)
                    and len(
                        standartify_str(each_row.text, ["\n", "\xa0", " ", ","], True)
                    )
                    < 45
                    or standartify_str(each_row.text, ["\n", "\xa0", " ", ","]) == "0"
                ):
                    value = standartify_str(each_row.text, ["\n", "\xa0"], True)
                    price_lst.append(value)
        if reverse and not in_here:
            if len(standartify_str(each_row.text, ["\n", "\xa0", " ", ","], True)) < 45:
                value = standartify_str(each_row.text, ["\n", "\xa0"])
                volume_lst.append(value)
    if volume_lst:
        return [
            ".".join(re.findall(r"\d+", x.replace(",", "")))
            for x in volume_lst
            if "".join(re.findall(r"\d+", standartify_str(x, [",", "."]))).isdigit()
        ]
    elif price_lst:
        price_lst = [
            standartify_str(
                convert_pence(
                    [each_predict for each_predict in my_find_all(x) if each_predict][0]
                ),
                [",", " "],
            )
            for x in price_lst
            if "".join(re.findall(r"\d+", standartify_str(x, [",", "."]))).isdigit()
        ]
        return price_lst
    else:
        return []


def get_volume_or_price(transaction_info, what_needed, date, found_price=True):
    where_volume = None
    for index, each_row in enumerate(transaction_info):
        if "volume(s)" in standartify_str(
            each_row.text,
            ["\n", "\xa0", " ", ","],
            True,
        ) and "price(s)" in standartify_str(
            each_row.text,
            ["\n", "\xa0", " ", ","],
            True,
        ):
            where_volume = index
    if transaction_info[(where_volume + 1) :]:
        find_any_word = next(
            (
                ind
                for ind, row in enumerate(transaction_info[(where_volume + 1) :])
                if re.findall(
                    r"^\s*(\(*[a-z][\)|\.])$",
                    standartify_str(
                        row.find_all("td")[0].text,
                        ["\n", "\xa0", " ", ","],
                    ),
                )
            ),
            None,
        )
        if find_any_word:
            till = where_volume + 1 + find_any_word
            if what_needed == "volume" and transaction_info[where_volume:till]:
                volumes = []
                for each_transction in transaction_info[where_volume:till]:
                    got_volume = [
                        standartify_str(
                            each_volume,
                            [
                                "\n",
                                "\xa0",
                                ",",
                                " ",
                            ],
                            True,
                        )
                        for each_volume in get_from_tr(
                            list(reversed(each_transction.find_all("td"))),
                            words_to_search=[
                                "$",
                                "£",
                                "dkk",
                                "gbp",
                                "usd",
                                "pence",
                                "aggregated",
                            ],
                            reverse=True,
                        )
                    ]
                    if got_volume:
                        if found_price is None and not volumes:
                            volumes += [got_volume[0]]
                        else:
                            volumes += got_volume
                if volumes:
                    return sum([float(x) for x in volumes if len(x.split(".")) < 3])
            elif what_needed == "price" and transaction_info[where_volume:till]:
                price = None
                for each_transction in transaction_info[where_volume:till]:

                    got_price = [
                        standartify_str(
                            each_price,
                            [
                                "\n",
                                "\xa0",
                                ",",
                                " ",
                            ],
                            True,
                        )
                        for each_price in get_from_tr(
                            each_transction.find_all("td"),
                            words_to_search=[
                                "$",
                                "£",
                                "pence",
                                "usd",
                                "us",
                                "gbp",
                                "dkk",
                            ],
                        )
                    ]
                    if got_price:
                        price = convert_symbol_to_usd(got_price[0], date)
                        break
                return price
    return None


def find_index(list_of_values, exist, index, each_tr):
    if not exist:
        for begin_part in list_of_values:
            if standartify_str(begin_part, [" "], True) in standartify_str(
                each_tr.text, ["\n", "\xa0", " "], True
            ):
                return index
    return exist


def create_owners(session, owner_info):
    owners = [
        {
            "name": standartify_str(
                get_from_row(owner_info, "name"),
                [
                    "\n",
                    "\xa0",
                ],
            ).strip(),
            "is_other": True,
            "other_text": standartify_str(
                get_from_row(owner_info, "status"),
                [
                    "\n",
                    "\xa0",
                ],
            ).strip(),
        }
    ]
    owners = write_owner_db(session=session, owners=owners)
    return owners


def create_transaction(
    object_from_scan, transaction_info, date, stock_rows, owner_and_issuer_obj, source
):
    if object_from_scan:
        transaction = object_from_scan
        transaction.update(
            {
                "conversion_or_exercise_price": get_volume_or_price(
                    transaction_info,
                    "price",
                    date=date,
                )
                if transaction.get("underlying_security_title")
                else None,
                "transaction_price_per_share": get_volume_or_price(
                    transaction_info,
                    "price",
                    date=date,
                )
                if not transaction.get("underlying_security_title")
                else None,
                "market_price": get_historical_prices(
                    stock_rows,
                    date=make_normal_date(
                        get_from_row(transaction_info, "date of"),
                        owner_and_issuer_obj.get("period_ending"),
                    ),
                )
                if source == "nasdaq"
                else get_historical_prices(
                    stock_rows,
                    date=date,
                    format=True,
                ),
                "transaction_shares": get_volume_or_price(
                    transaction_info,
                    "volume",
                    date=date,
                    found_price=get_volume_or_price(
                        transaction_info, "price", date=date
                    ),
                ),
                "transaction_date": date,  # now it's str
                "transaction_code": transaction_code_generator(
                    get_from_row(transaction_info, "place of")
                ),
            }
        )
        return transaction


def get_html_tables(
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
    print("in 6k")
    replace_args_in_all_tables = [",", "\n", "\xa0"]
    main = BeautifulSoup(xml_or_html.text, "lxml")
    all_tables = [
        each_table
        for each_table in main.find_all("table")
        if "detailsofthetransaction"
        in standartify_str(each_table.text, [*replace_args_in_all_tables, " "], True)
        and (
            "detailsofpdmr"
            in standartify_str(
                each_table.text, [*replace_args_in_all_tables, " "], True
            )
            or "detailsoftheperson"
            in standartify_str(
                each_table.text, [*replace_args_in_all_tables, " "], True
            )
        )
        and len(each_table.find_all("tr")) > 1
        and (
            "name"
            in standartify_str(
                each_table.find_all("tr")[1].text, replace_args_in_all_tables, True
            )
            or "name"
            in standartify_str(
                each_table.find_all("tr")[2].text, replace_args_in_all_tables, True
            )
            or "name"
            in standartify_str(
                each_table.find_all("tr")[3].text, replace_args_in_all_tables, True
            )
        )
        and "price(s)andvolume(s)"
        in standartify_str(each_table.text, [*replace_args_in_all_tables, " "], True)
        and "position/status"
        in standartify_str(each_table.text, [*replace_args_in_all_tables, " "], True)
        and "lei"
        in standartify_str(each_table.text, [*replace_args_in_all_tables, " "], True)
        and "placeofthetransaction"
        in standartify_str(each_table.text, [*replace_args_in_all_tables, " "], True)
    ]
    if not all_tables:
        write_db(Transactions_and_holdings, session, {"url": url})

    for each_table in all_tables:
        tr_reasonn = next(
            (
                each_tr
                for each_tr in each_table.find_all("tr")
                if "reasonforthenotification" in each_tr.text.lower().replace(" ", "")
            ),
            None,
        )
        if tr_reasonn:
            tr_reasonn.decompose()
        default_split = [0, 4, 7]
        owner_begin = ["details of pdmr", "details of the person discharging"]
        issuer_begin = ["details of the issuer"]
        transaction_begin = ["details of the transaction"]
        indexes_separation = [None, None, None]
        for index, each_tr in enumerate(each_table.find_all("tr")):
            indexes_separation[0] = find_index(
                owner_begin, indexes_separation[0], index, each_tr
            )
            indexes_separation[1] = find_index(
                issuer_begin, indexes_separation[1], index, each_tr
            )
            indexes_separation[2] = find_index(
                transaction_begin, indexes_separation[2], index, each_tr
            )
        for i, value in enumerate(indexes_separation):
            if not value:
                indexes_separation[i] = default_split[i]
        if list(sorted(indexes_separation)) == indexes_separation:
            owner_info = each_table.find_all("tr")[
                (indexes_separation[0] + 1) : indexes_separation[1]
            ]
            issuer_info = each_table.find_all("tr")[
                (indexes_separation[1] + 1) : indexes_separation[2]
            ]
            transaction_info = each_table.find_all("tr")[(indexes_separation[2] + 1) :]
            if owner_info and issuer_info and transaction_info:
                owners = create_owners(session, owner_info)
                issuer_name = standartify_str(
                    get_from_row(issuer_info, "name"),
                    ["\n", "\xa0", "inc", "plc", "INC", "PLC", "Group", "group"],
                ).strip()
                issuer_cik, issuer_ticker = get_company_cik(issuer_name)
                if issuer_ticker and issuer_ticker not in ["none", "None", "NONE"]:
                    owner_and_issuer_obj = {
                        "url": url,
                        "company_name": company.get("name"),
                        "company_ticker": company.get("ticker"),
                        "file_date": conv_time(get_text(file_date, date=True)),
                        "period_ending": conv_time(get_text(period_ending, date=True)),
                        "owners": owners,
                        "issuer_cik": issuer_cik,
                        "issuer_name": issuer_name,
                        "issuer_ticker": issuer_ticker,
                        "transaction_form_type": str(form),
                    }
                    date = make_normal_date(
                        get_from_row(transaction_info, "date of"),
                        owner_and_issuer_obj.get("period_ending") - timedelta(days=1),
                    )
                    a_d_code = get_from_row(transaction_info, "nature")
                    description = get_from_row(transaction_info, "description")
                    object_from_scan = understand_derivative_or_not(
                        a_d_code, description
                    )
                    transaction = create_transaction(
                        object_from_scan,
                        transaction_info,
                        date,
                        stock_rows,
                        owner_and_issuer_obj,
                        source,
                    )
                    url_in_db = (
                        session.query(Transactions_and_holdings)
                        .filter(
                            Transactions_and_holdings.url
                            == owner_and_issuer_obj.get("url")
                        )
                        .first()
                    )
                    if (
                        not url_in_db
                        and transaction
                        and (
                            transaction.get("conversion_or_exercise_price")
                            or transaction.get("transaction_price_per_share")
                            or transaction.get("transaction_shares")
                        )
                    ):
                        unite_derivatives_nonderivatives_and_commit(
                            session, [{**transaction, **owner_and_issuer_obj}], []
                        )
                    else:
                        write_db(Transactions_and_holdings, session, {"url": url})
