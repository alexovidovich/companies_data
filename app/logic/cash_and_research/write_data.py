from logic.cash_and_research.cash.func import (
    cash_check_if_fresh_and_late_data_and_commit,
)
from logic.cash_and_research.research_and_development.func import (
    research_check_if_fresh_and_late_data_and_commit,
    get_missing_year_only_research_obj,
    make_year_data_from_q,
    get_only_year_data,
)
from logic.func import exchanging_to_usd
from logic.utils import conv_time


def write_data(obj_of_current_company, session, model, param):
    sorted_db_objects = (
        sorted(
            [
                x
                for x in obj_of_current_company.get("list_of_ready_info").get("values")
                if x.get("start")
            ],
            key=lambda x: (conv_time(x.get("filed")), conv_time(x.get("start"))),
        )
        if param == "research_and_development"
        else sorted(
            obj_of_current_company.get("list_of_ready_info").get("values"),
            key=lambda x: conv_time(x.get("filed")),
        )
    )
    args_to_check_if_fresh = None
    for each_cash_or_dev_obj in sorted_db_objects:
        begin_date = conv_time("2013-01-01")
        condition = (
            (
                conv_time(each_cash_or_dev_obj.get("filed")) >= begin_date
                and conv_time(each_cash_or_dev_obj.get("end")) >= begin_date
                and conv_time(each_cash_or_dev_obj.get("start")) >= begin_date
            )
            if each_cash_or_dev_obj.get("start")
            else (
                conv_time(each_cash_or_dev_obj.get("filed")) >= begin_date
                and conv_time(each_cash_or_dev_obj.get("end")) >= begin_date
            )
        )
        if condition:
            to_base = {
                "end_date": each_cash_or_dev_obj.get("end"),
                "form": each_cash_or_dev_obj.get("form"),
                "date": each_cash_or_dev_obj.get("filed"),
                "name": obj_of_current_company.get("each_company").get("name"),
                "ticker": obj_of_current_company.get("each_company").get("ticker"),
                param: each_cash_or_dev_obj.get("val"),
            }
            if each_cash_or_dev_obj.get("start"):
                to_base.update(
                    {
                        "start_date": each_cash_or_dev_obj.get("start"),
                    },
                )
            if (
                obj_of_current_company.get("list_of_ready_info").get("currency").lower()
                != "usd"
            ):
                to_base.update(
                    {
                        param: exchanging_to_usd(
                            int(each_cash_or_dev_obj.get("val")),
                            obj_of_current_company.get("list_of_ready_info").get(
                                "currency"
                            ),
                            each_cash_or_dev_obj.get("end"),
                        )
                    }
                )
            args_to_check_if_fresh = {
                "session": session,
                "model": model,
                "name": obj_of_current_company.get("each_company").get("name"),
                "to_base": to_base,
            }
            if param == "research_and_development":
                args_to_check_if_fresh.update(
                    {
                        "param": "research_and_development",
                    },
                )
                if each_cash_or_dev_obj.get("start"):
                    get_only_year_data(
                        **args_to_check_if_fresh,
                    )
                    research_check_if_fresh_and_late_data_and_commit(
                        **args_to_check_if_fresh,
                    )
                    get_missing_year_only_research_obj(
                        **args_to_check_if_fresh,
                    )

            elif param == "cash_and_cash_equivalents":
                cash_check_if_fresh_and_late_data_and_commit(
                    **args_to_check_if_fresh,
                )
    if param == "research_and_development" and args_to_check_if_fresh:
        make_year_data_from_q(
            **args_to_check_if_fresh,
        )
