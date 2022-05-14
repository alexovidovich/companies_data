from logic.cash_and_research.cash_or_res_and_dev import check_api_for_cash_or_research

from models.models import Research


def research_and_dev(table):
    check_api_for_cash_or_research(
        table,
        Research,
        "research_and_development",
        keys=[
            "facts.ifrs-full.ResearchAndDevelopmentExpense.units",
            "facts.us-gaap.ResearchAndDevelopmentExpense.units",
            "facts.us-gaap.ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost.units",
            "facts.ifrs-full.ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost.units",
        ],
    )
