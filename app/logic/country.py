import requests
from bs4 import BeautifulSoup
from logic.func import write_db, make_cik
from core.db import SessionLocal
from logic.var import headers_html as headers
from models.models import countries
import json
from logic.utils import standartify_str


def get_cik_for_comp(name, ticker):
    with open("./data/data.json", "r") as f:
        list_of_comp = json.load(f)
        cik = next(
            (
                make_cik(each_comp)
                for each_comp in list(list_of_comp.values())
                if each_comp.get("ticker") == ticker.upper()
            ),
            None,
        )
        if not cik:
            cik = next(
                (
                    make_cik(each_comp)
                    for each_comp in list(list_of_comp.values())
                    if standartify_str(name, [" "], True)
                    in standartify_str(each_comp.get("title"), [" "], True)
                ),
                None,
            )
        if cik:
            return cik


def get_company_country(each_company):
    model = countries
    ticker = each_company.get("ticker")
    name = each_company.get("name")
    country = None
    places = ["NASDAQ", "BMV", "NYSE", "TLV"]
    for place in places:
        url = f"https://www.google.com/finance/quote/{ticker.upper()}:{place}"
        req_obj = requests.get(url, headers=headers).text
        html_str = (
            "<c-wiz "
            + req_obj.split("</script><c-wiz")[1].split("</c-wiz><script")[0]
            + "</c-wiz>"
        )
        main = BeautifulSoup(html_str, "lxml")
        for a in main.find_all("a", href=True):
            if "google.com/maps/place" in a["href"]:
                country = a.get_text(separator=" ")
        if country:
            break

    if country:
        country = country.replace("Headquartered in ", "")

    obj_to_write = {
        "name": str(name),
        "ticker": str(ticker),
        "country": country,
        "cik": each_company.get("cik"),
    }
    print(obj_to_write)

    with SessionLocal() as session:
        results = (
            session.query(model)
            .filter(model.name == name, model.country == country)
            .first()
        )
        if not results:
            write_db(model, session, obj_to_write)
