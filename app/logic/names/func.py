import re
import time
import datetime
import requests
from bs4 import BeautifulSoup
from logic.var import headers_html
from logic.names.var import same_words
from logic.utils import deconv_time, standartify_str
from logic.names.conditions import (
    condition_for_matching_norm_names,
    get_condition_total_bigger_zero,
)
from logic.names.utils import clear_name, delete_many_spaces, normalize_name
from logic.func import request_to_sec, get_hits
from logic.insiders.func import get_text


def get_cik_and_ticker_by_name_or_number_of_simular_comp(
    name, get_number_of_simular_comp=False, ticker=None
):
    name = delete_many_spaces(
        standartify_str(
            name,
            [
                "-",
                "/",
                ",",
                ".",
                "&",
            ],
            to_what=" ",
        )
    )
    url = "https://efts.sec.gov/LATEST/search-index"
    params = {"keysTyped": name, "narrow": True}
    json_response, condition = get_condition_total_bigger_zero(url, params)
    if not condition and ticker:
        params.update({"keysTyped": ticker})
        json_response, condition = get_condition_total_bigger_zero(url, params)
    if get_number_of_simular_comp and json_response:
        return int(json_response.get("hits").get("total").get("value"))
    if condition and int(json_response.get("hits").get("total").get("value")) < 17:
        for each_response_obj in json_response.get("hits").get("hits"):
            source = each_response_obj.get("_source")
            if source:
                normalized_name = normalize_name(name, brack=True)
                normalized_each_name = normalize_name(source.get("entity"), brack=True)
                if condition_for_matching_norm_names(
                    normalized_name, normalized_each_name
                ):
                    cik = (10 - len(each_response_obj.get("_id"))) * "0" + str(
                        each_response_obj.get("_id")
                    )
                    ticker = each_response_obj.get("tickers")
                    return (cik, ticker)
            else:
                return (None, None)
    return (None, None)


def get_4_form_ticker(hit, name, ticker):
    cik = hit.get("_source").get("ciks")[0]
    _, _, _, new_url = get_hits(hit, cik)
    xml_or_html = request_to_sec(new_url, requests.get, headers_html)
    try:
        main = BeautifulSoup(xml_or_html.text.lower(), "lxml")
        issuer = main.find("issuer")
        issuer_name = get_text(issuer.find("issuername")) if issuer else None
        issuer_ticker = get_text(issuer.find("issuertradingsymbol")) if issuer else None
        issuer_cik = get_text(issuer.find("issuercik")) if issuer else None
        if (
            issuer
            and issuer_name
            and clear_name(name) in clear_name(issuer_name)
            and clear_name(issuer_name).index(clear_name(name)) == 0
        ):
            if clear_name(ticker) == clear_name(issuer_ticker):
                return (ticker.upper(), False, issuer_cik)
            else:
                return (issuer_ticker.upper(), True, issuer_cik)
    except:
        print(new_url, "ERROR IN GETTING FORM 4")
    return (None, None, None)


def get_ticker_or_cik_only_by_sec(name, cik_only=False):
    time.sleep(1)
    # пробую два вариант имени для запроса в edgar, с заменой символов и без, а также проверяю кол-во похожих компаний
    name = delete_many_spaces(name)
    now = deconv_time(datetime.datetime.now())
    url = "https://efts.sec.gov/LATEST/search-index"
    params = {
        "dateRange": "custom",
        "entityName": name,
        "startdt": "2001-01-01",
        "enddt": now,
    }
    print(name)
    json_response, condition = get_condition_total_bigger_zero(url, params)
    number_of_simular_comp = get_cik_and_ticker_by_name_or_number_of_simular_comp(
        name, get_number_of_simular_comp=True
    )
    if not condition:
        name = clear_name(
            delete_many_spaces(
                standartify_str(
                    name,
                    [
                        "-",
                        "/",
                        ",",
                        ".",
                        "&",
                    ],
                    to_what=" ",
                )
            ),
            lower=False,
            spaces=False,
            dots=False,
            slash_dash=False,
        )
        params.update(
            {
                "entityName": name,
            }
        )

        print(name)
        json_response, condition = get_condition_total_bigger_zero(url, params)
    if number_of_simular_comp == 0:
        number_of_simular_comp = get_cik_and_ticker_by_name_or_number_of_simular_comp(
            name, get_number_of_simular_comp=True
        )
    if condition and number_of_simular_comp < 17:
        global_cik = None
        for each_response_obj in json_response.get("hits").get("hits"):
            for each_name in each_response_obj.get("_source").get("display_names"):
                print(each_name)
                # нормализую имена
                normalized_name = normalize_name(name)
                normalized_each_name = normalize_name(each_name)
                # нахожу одно в другом
                if condition_for_matching_norm_names(
                    normalized_name, normalized_each_name
                ):
                    # забераю cik из Filing entity/person
                    cik_from_entity = re.findall(
                        r"\(cik(\d+)\)", each_name.lower().replace(" ", "")
                    )
                    print(cik_from_entity, each_name.lower())
                    # делаю глобальную переменную cik в этой функции
                    if cik_from_entity and not global_cik:
                        global_cik = cik_from_entity[0]
                    # нахожу тикер из Filing entity/person
                    tickers = re.findall(r"\(([A-Za-z0-9_]+)\)", normalized_each_name)
                    ticker = next(
                        (
                            delete_many_spaces(x.replace("(", "").replace(")", ""))
                            for x in tickers
                            if len(x) < 6
                            and "usa" not in x.lower()
                            and "cik" not in x.lower()
                        ),
                        None,
                    )
                    # достаю имя из Filing entity/person
                    if not ticker:
                        ticker = ""
                        modified_name = each_name
                    else:
                        modified_name = each_name.split(ticker.upper())[0]

                    new_name_from_sec = normalize_name(
                        modified_name.split("(")[0],
                        lower=False,
                        brack=True,
                        dash=False,
                        dots=False,
                        and_word=False,
                    ).strip()
                    # запрашиваю формы 3 и 4 с xml
                    new_params = {
                        **params,
                        "category": "custom",
                        "forms": ["4", "3"],
                        "size": 50,
                    }
                    new_json_response, new_condition = get_condition_total_bigger_zero(
                        url, new_params
                    )
                    if new_condition:
                        constancy = 0
                        rand = 0
                        has_new_ticker = ""
                        all_got_tickers = []
                        # итерируюсь по объектам внутри этого запроса
                        for hit in new_json_response.get("hits").get("hits"):
                            time.sleep(0.1)
                            # проверяю имя на совпадение а также вытаскиваю из формы тикер, затем сранвиваю с тикером из Filing entity/person и cik
                            new_ticker, different, cik = get_4_form_ticker(
                                hit, name, ticker
                            )
                            # если есть cik то делаю его глобальным, заменяя cik из Filing entity/person
                            if cik:
                                print("cik from 4 form")
                                global_cik = cik
                            if cik_only:
                                # для использования функции только для добычи cik
                                return (None, None, global_cik)
                            # складирую тикеры из форм, а также добавляю параметр рандома, если тикер новый не найден(объект не подходит, проблемы с индефекцией компании)
                            # и параметр постоянства
                            if new_ticker:
                                if different and not has_new_ticker:
                                    has_new_ticker = new_ticker
                                constancy += 1
                                all_got_tickers.append(new_ticker)
                            else:
                                rand += 1
                        # в случае если объектов 6 и более, то тикер должен повториться хотя бы 2 раза и рандом должен быть явно меньше постоянства и если меньше 5
                        # то должен быть хоть 1 тикер и рандом меньше постоянства
                        if (
                            len(new_json_response.get("hits").get("hits")) > 5
                            and constancy > 2
                            and rand < constancy
                        ) or (
                            len(new_json_response.get("hits").get("hits")) <= 5
                            and constancy > 0
                            and rand < constancy
                        ):
                            # если есть отличный от Filing entity/person тикер то пробую найти самый частый их всех тикеров в формах 3,4
                            if has_new_ticker:
                                all_got_tickers_dict = {
                                    x: 0 for x in set(all_got_tickers)
                                }
                                for each_ticker in all_got_tickers:
                                    all_got_tickers_dict.update(
                                        {
                                            each_ticker: all_got_tickers_dict.get(
                                                each_ticker
                                            )
                                            + 1
                                        }
                                    )
                                max_times = max(
                                    all_got_tickers_dict,
                                    key=all_got_tickers_dict.get,
                                )
                                # возращаю самый частый
                                return (max_times, new_name_from_sec, global_cik)
                            else:
                                # если нет отличного от Filing entity/person тикера то возвращаю из Filing entity/person
                                return (ticker.upper(), new_name_from_sec, global_cik)
                        elif constancy == 0 and rand == 0:
                            # если нет инфы в этих формах(старые)
                            print((ticker.upper(), new_name_from_sec, global_cik))
                            return (ticker.upper(), new_name_from_sec, global_cik)
                    elif ticker:
                        # если вовсе нет форм 3/4
                        if cik_only:
                            return (None, None, global_cik)
                        return (ticker.upper(), new_name_from_sec, global_cik)
    return (None, None, None)


def sub_words(name, func_to_exec, args):
    to_return = func_to_exec(*args)
    # пробую с обычным именем
    if any(to_return):
        return to_return
    # если символов 3 и более обрезаю последнее слово
    if not any(to_return) and len(name.split(" ")) > 2:
        to_return = func_to_exec(*[" ".join(name.split(" ")[:-1]), *args[1:]])
    # если символов 4 и более обрезаю последние 2 слова
    if not any(to_return) and len(name.split(" ")) > 3:
        to_return = func_to_exec(*[" ".join(name.split(" ")[:-2]), *args[1:]])
    # если не нашлось заменяю слова на синонимы из переменной same_words
    if not any(to_return):
        for same_word_list in same_words:
            same_word_inside_name = next(
                (
                    each_word
                    for each_word in same_word_list
                    if each_word in [x.strip() for x in name.split(" ")]
                    or each_word.capitalize() in [x.strip() for x in name.split(" ")]
                    or each_word.upper() in [x.strip() for x in name.split(" ")]
                ),
                None,
            )
            if same_word_inside_name:
                for each_word in same_word_list:
                    if (
                        each_word.strip().lower()
                        != same_word_inside_name.strip().lower()
                    ):
                        name = standartify_str(
                            name,
                            [
                                same_word_inside_name,
                                same_word_inside_name.capitalize(),
                                same_word_inside_name.upper(),
                            ],
                            to_what=each_word,
                        )
                        args[0] = name
                        to_return = func_to_exec(*args)
                        if any(to_return):
                            return to_return
    return to_return


def get_formerly_names(cik, name):
    url_to_sec_gov = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&owner=include&count=40"
    xml_or_html = request_to_sec(url_to_sec_gov, requests.get, headers_html)
    if xml_or_html and "CIK" in xml_or_html.text:
        main = BeautifulSoup(xml_or_html.text, "lxml")
        name_from_source = (
            main.find("span", {"class": "companyName"})
            .getText()
            .split("\n")[0]
            .split("CIK")[0]
        )
        formerly_name = main.find("p", {"class": "identInfo"}).text.split("formerly")
        formerly_names = []
        for each_formerly_name in formerly_name:
            formerly_list = re.findall(r": (.*) \(filings", each_formerly_name)
            if formerly_list:
                formerly_names.extend([x.strip() for x in formerly_list])
        return ("||".join(list(set(formerly_names))), name_from_source.strip())
    return (None, None)


# def changing_ticker(name=None, ticker=None):
#     url = "https://api.nasdaq.com/api/quote/list-type-extended/symbolchangehistory"
#     all_ticker_changing_objects = (
#         requests.get(url, headers=headers_html)
#         .json()
#         .get("data")
#         .get("symbolChangeHistoryTable")
#         .get("rows")
#     )
#     if name:
#         name_found = next(
#             (
#                 (x.get("newSymbol"), x.get("companyName"))
#                 for x in all_ticker_changing_objects
#                 if clear_name(x.get("companyName")) == clear_name(name)
#             ),
#             None,
#         )
#         if name_found:
#             return name_found
#     if ticker:
#         ticker_found = next(
#             (
#                 (x.get("newSymbol"), x.get("companyName"))
#                 for x in all_ticker_changing_objects
#                 if clear_name(x.get("oldSymbol")) == clear_name(ticker)
#             ),
#             None,
#         )
#         if ticker_found:
#             return ticker_found
#     return (None, None)
