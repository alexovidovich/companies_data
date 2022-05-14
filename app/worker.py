import os
from celery import Celery

from logic.cash_and_research.cash.cash_and_cash_equivalents import (
    cash_and_cash_equivalents,
)
from logic.cash_and_research.research_and_development.research_and_dev import (
    research_and_dev,
)
from logic.country import get_company_country
from logic.f13.getting_f13 import main
from logic.insiders.insiders import init_insiders
from logic.names.get_companies import get_new_companies
from logic.names.prices import get_prices_from_ready_csv
from logic.shares_outstanding.uk import get_uk_comp
from logic.shares_outstanding.shares_sec_macro import (
    macrotrends,
    sec,
    sharesoutstandinghistory,
)

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")


@celery.task(queue="queue1")
def get_new_companies_search(
    file_in,
    file_out,
    file_type,
):
    get_new_companies(
        file_in,
        file_out,
        file_type,
    )


@celery.task(queue="queue2")
def get_prices_from_ready_csv_search(file_in):
    get_prices_from_ready_csv(file_in)


@celery.task(queue="queue2")
def init_insiders_search(company):
    init_insiders(company)


@celery.task(queue="queue1")
def cash_and_cash_equivalents_search(companies):
    cash_and_cash_equivalents(companies)


@celery.task(queue="queue1")
def research_and_dev_search(companies):
    research_and_dev(companies)


@celery.task(queue="queue2")
def macrotrends_search(each_company):
    macrotrends(each_company)


@celery.task(queue="queue2")
def sharesoutstandinghistory_search(each_company):
    sharesoutstandinghistory(each_company)


@celery.task(queue="queue2")
def SEC_search(company, no_country=True):
    sec(company, no_country=no_country)


@celery.task(queue="queue2")
def get_country(each_company):
    get_company_country(each_company)


@celery.task(queue="queue1")
def get_uk(each_company):
    get_uk_comp(each_company)


@celery.task(queue="queue2")
def get_f13(company):
    main(company)
