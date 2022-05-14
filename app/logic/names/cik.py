import requests
from bs4 import BeautifulSoup
from logic.var import headers_html
import re
from logic.func import request_to_sec
from logic.names.conditions import (
    condition_for_matching_norm_names,
)
from logic.names.utils import normalize_name
from logic.names.func import (
    sub_words,
    get_formerly_names,
    get_ticker_or_cik_only_by_sec,
    get_cik_and_ticker_by_name_or_number_of_simular_comp,
)


def get_cik_by_name_via_sec_company_search(name, ticker):
    url = f"https://www.sec.gov/cgi-bin/browse-edgar?CIK={ticker}&Find=Search&owner=exclude&action=getcompany"
    xml_or_html = request_to_sec(url, requests.get, headers_html)
    try:
        if xml_or_html and "CIK" in xml_or_html.text:
            main = BeautifulSoup(xml_or_html.text, "lxml")
            name_from_source = (
                main.find("span", {"class": "companyName"})
                .getText()
                .split("\n")[0]
                .split("CIK")[0]
            )
            norm_name = normalize_name(name, brack=True)
            norm_name_from_source = normalize_name(name_from_source, brack=True)
            if condition_for_matching_norm_names(norm_name, norm_name_from_source):
                cik = re.findall(
                    r"CIK#: (\d+)",
                    main.find("span", {"class": "companyName"}).getText(),
                )[0]
                return cik
    except:
        return


def iter_cik_parsers(
    name=None, ticker=None, cik=None, by_sec_already_done=False, not_exist_only=None
):

    if not not_exist_only:
        # ищу в api edgar с кастомными параметрами, поиск отличается значительно от клиентских парметров из edgar
        cik, _ = get_cik_and_ticker_by_name_or_number_of_simular_comp(
            name, ticker=ticker
        )
        if not cik and not by_sec_already_done:
            # использую имя для поиска в обычном api edgar с клиентскими параметрами
            _, _, cik = get_ticker_or_cik_only_by_sec(name, cik_only=True)
        if not cik:
            #  использую тикер и имя чтобы найти cik(все передается через get параметры, поэтому часто ненеаходит, тк имя может быть модифицированным
            # но иногда срабатывает, когда в других не срабатывает )
            cik = get_cik_by_name_via_sec_company_search(name, ticker)
    if cik and name:
        # по cik добываю formerly_names, current_name
        formerly, now = get_formerly_names(cik, name)
        cik = cik.strip()
        if len(str(cik)) < 10:
            cik = (10 - len(str(cik))) * "0" + str(cik)
        return (cik, formerly, now)
    return (None, None, None)


def get_cik(
    name=None, ticker=None, cik=None, by_sec_already_done=False, not_exist_only=None
):
    # пробую заменять слова на синонимы чтобы найти cik компании в разных местах, передаю в функцию sub_words, которая по очереди заменяет,
    # если таковые имеются и выполняет колбэк iter_cik_parsers
    to_return = sub_words(
        name,
        iter_cik_parsers,
        [name, ticker, cik, by_sec_already_done, not_exist_only],
    )
    return to_return
