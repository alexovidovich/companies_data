from logic.func import write_db
from models.models import Names
from logic.names.conditions import (
    condition_to_write,
)
from logic.names.exchange import get_exchange
from logic.names.utils import (
    clear_name,
    slice_names,
)
from logic.names.cik import get_cik
from yahoo_fin.stock_info import get_company_info
from logic.names.func import (
    # changing_ticker,
    get_ticker_or_cik_only_by_sec,
)


def not_listed_companies(
    name, names_from_two_ex, already_in, file_out, session, original_name
):
    print("not in exchanges now")
    to_base = {}
    # получаю тикер и имя из sec и при возможности cik
    ticker, name_from_sec, cik = get_ticker_or_cik_only_by_sec(name)
    if name_from_sec:
        name = clear_name(
            slice_names(name_from_sec).strip(),
            lower=False,
            spaces=False,
            dots=False,
            slash_dash=False,
        )
    if ticker:
        if not cik:
            cik, formerly, now = get_cik(name, ticker, by_sec_already_done=True)
        else:
            _, formerly, now = get_cik(
                name=name, ticker=ticker, cik=cik, not_exist_only=True
            )
        exchange = get_exchange(ticker)
        country_from_yahoo = None
        try:
            country_from_yahoo = (
                get_company_info(ticker.lower()).to_dict().get("Value").get("country")
            )
        except:
            pass
        to_base = {
            "name": name,
            "ticker": ticker,
            "country": country_from_yahoo,
            "listed": True,
            "exchange": exchange,
            "cik": cik,
            "formerly_names": formerly,
            "current_name": now,
            "original_names": original_name,
        }
        print(to_base)
        if ticker.lower() not in [x[0].lower() for x in names_from_two_ex]:
            to_base.update({"listed": False})

        if condition_to_write(
            ticker, name, already_in, original_name, session
        ) and to_base.get("exchange"):
            write_db(Names, session, to_base)
        # new_ticker, new_name = changing_ticker(ticker=ticker)
        # if new_name:
        #     new_name = clear_name(
        #         slice_names(new_name).strip(),
        #         lower=False,
        #         spaces=False,
        #         dots=False,
        #         slash_dash=False,
        #     )
        # if new_ticker:
        #     country_from_yahoo = None
        #     try:
        #         country_from_yahoo = (
        #             get_company_info(ticker.lower())
        #             .to_dict()
        #             .get("Value")
        #             .get("country")
        #         )
        #     except:
        #         pass
        #     exchange = get_exchange(new_ticker)
        #     cik, formerly, now = get_cik(new_name, new_ticker)
        #     to_base = {
        #         "name": new_name,
        #         "ticker": new_ticker,
        #         "country": country_from_yahoo,
        #         "listed": True,
        #         "exchange": exchange,
        #         "cik": cik,
        #         "formerly_names": formerly,
        #         "current_name": now,
        #         "original_names": original_name,
        #     }
        #     if new_ticker.lower() not in [x[0].lower() for x in names_from_two_ex]:
        #         to_base.update({"listed": False})
        #     if condition_to_write(
        #         new_ticker, new_name, already_in, original_name, session
        #     ) and to_base.get("exchange"):
        #         write_db(Names, session, to_base)
    if to_base:
        return True
