from models.models import Cash

from logic.cash_and_research.cash_or_res_and_dev import check_api_for_cash_or_research


def cash_and_cash_equivalents(table):
    check_api_for_cash_or_research(
        table,
        Cash,
        "cash_and_cash_equivalents",
        keys=[
            "facts.us-gaap.CashAndCashEquivalentsAtCarryingValue.units",
            "facts.ifrs-full.CashAndCashEquivalents.units",
            "facts.us-gaap.CashAndCashEquivalentsFairValueDisclosure.units",
        ],
    )
