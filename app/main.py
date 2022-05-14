from fastapi import BackgroundTasks, FastAPI, Response

# from logic.cash_and_research.cash.cash_and_cash_equivalents import (
#     cash_and_cash_equivalents,
# )
# from logic.cash_and_research.research_and_development.research_and_dev import (
#     research_and_dev,
# )
# from logic.country import get_company_country
# from logic.f13.getting_f13 import main
from logic.func import open_csv

# from logic.insiders.insiders import init_insiders
# from logic.names.get_companies import get_new_companies
# from logic.names.prices import get_prices_from_ready_csv
# from logic.shares_outstanding.shares_sec_macro import (
#     macrotrends,
#     sharesoutstandinghistory,
# )
# from logic.shares_outstanding.shares_sec_macro import sec
# from logic.shares_outstanding.uk import get_uk_comp

from worker import (
    SEC_search,
    get_country,
    get_f13,
    get_uk,
    macrotrends_search,
    sharesoutstandinghistory_search,
    get_prices_from_ready_csv_search,
    get_new_companies_search,
    init_insiders_search,
    cash_and_cash_equivalents_search,
    research_and_dev_search,
)


app = FastAPI()


class FinParser:
    def __init__(
        self,
        csvFilePath,
        source,
        csvOutFilePath,
    ):
        self.csvFilePath = csvFilePath
        self.source = source
        self.csvOutFilePath = csvOutFilePath

    def parse(self):
        self.exe()

    def exe(self):
        companies = open_csv(self.csvFilePath)
        if self.source == "prices":

            get_prices_from_ready_csv_search.delay(file_in=self.csvFilePath)
            # get_prices_from_ready_csv(file_in=self.csvFilePath)
        elif self.source == "names":
            # get_new_companies(
            #     file_in=self.csvFilePath,
            #     file_out=self.csvOutFilePath,
            #     file_type="csv",
            # )
            get_new_companies_search.delay(
                file_in=self.csvFilePath,
                file_out=self.csvOutFilePath,
                file_type="csv",
            )
        elif self.source == "cash":
            # cash_and_cash_equivalents(companies)
            cash_and_cash_equivalents_search.delay(companies)
        elif self.source == "r&d":
            # research_and_dev(companies)
            research_and_dev_search.delay(companies)
        else:
            for company in companies:
                if self.source == "sec":
                    SEC_search.delay(company, no_country=True)
                    # sec(company, no_country=True)
                elif self.source == "insiders":
                    # init_insiders(company)
                    init_insiders_search.delay(company)
                elif self.source == "uk" and  "united kingdom" in company.get("country").lower() :
                    # get_uk_comp(company)
                    get_uk.delay(company)
                elif self.source == "f13":
                    get_f13.delay(company)
                    # main(company)
                elif self.source == "findcountry":
                    get_country.delay(company)
                    # get_company_country(company)
                elif self.source == "macrotrends":
                    # macrotrends(company)
                    macrotrends_search.delay(company)
                elif self.source == "sharesoutstandinghistory":
                    # sharesoutstandinghistory(company)
                    sharesoutstandinghistory_search.delay(company)


@app.get("/{method}")  # can be an entry point without a web app
async def write_database(background_tasks: BackgroundTasks, method):
    if method.lower() in [
        "r&d",
        "f13",
        "uk",
        "sec",
        "findcountry",
        "macrotrends",
        "sharesoutstandinghistory",
        "cash",
        "insiders",
        "names",
        "prices",
    ]:
        parser = FinParser(
            csvFilePath="data/names.csv",
            source=f"{method}",
            csvOutFilePath="data/names_new_version.csv",
        )
        background_tasks.add_task(parser.parse)
        return Response(content="your database is being created")
    return Response(content="wrong method")
