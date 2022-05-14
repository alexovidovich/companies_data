import time
import requests
from logic.utils import standartify_str
from logic.var import headers_json
from logic.func import request_to_sec
from logic.names.utils import clear_name, delete_spaces


def condition_to_write(ticker, name, already_in, original_name=None, session=None):
    # проверяю есть ли такой же тикер или имя в бд и если есть, то просто добавляю original_names
    condition = ticker not in [x.ticker for x in already_in] or (
        clear_name(name) not in [clear_name(x.name) for x in already_in]
        and next(
            (
                False
                for each_name in [clear_name(x.name) for x in already_in]
                if clear_name(name) in each_name
                and each_name.strip().index(clear_name(name)) == 0
            ),
            True,
        )
    )
    if not condition and original_name and session:
        ticker_or_name_in_db_objs = [
            x
            for x in already_in
            if ticker == x.ticker
            or (
                clear_name(name) in clear_name(x.name)
                and clear_name(x.name)[:2] == clear_name(name)[:2]
            )
        ]
        if ticker_or_name_in_db_objs:
            for each_ticker_or_name_obj in ticker_or_name_in_db_objs:
                if original_name not in each_ticker_or_name_obj.original_names:
                    each_ticker_or_name_obj.original_names = (
                        each_ticker_or_name_obj.original_names + ";" + original_name
                    )
        session.commit()
    return condition


def condition_for_matching_norm_names(norm_name, norm_name_from_source):
    norm_name = standartify_str(norm_name, ["(", ")"], True)
    norm_name_from_source = standartify_str(norm_name_from_source, ["(", ")"], True)
    return (
        norm_name in norm_name_from_source
        and norm_name[:2] == norm_name_from_source[:2]
        and norm_name_from_source.index(norm_name) == 0
    )


def get_condition_total_bigger_zero(url, params, count=0):
    # делаю запрос и проверяю кол-во объектов в нем, нужно > 0
    if count < 10:
        try:
            json_response = request_to_sec(
                url, requests.post, headers_json, params
            ).json()
            condition = json_response.get("hits").get("total").get("value") > 0
            return json_response, condition
        except:
            time.sleep(2)
            count += 1
            return get_condition_total_bigger_zero(url, params, count)
    else:
        return (None, None)


def condition_for_nasdaq(
    name, each_name_from_exchange, filtered_names_objcects_with_spaces, ind
):
    # сравниваю фильтрванное имя без пробелов с каждым именем из биржи без пробелов,хочу чтобы строка из биржи начиналось с моего имени,
    # а также хочу удалить все пробелы в строке со всеми пробелами только в пределах моего имени(если оно есть в строке и строка с него начинается)
    # и убедиться что после этого имени идет пробел, а не какой-то другой символ (например takedaclone имя из биржевого списка, а у меня takeda имя, мне это не подойдет,
    # тк нужно чтобы было takeda Pharmaceutical Company. где пробел после takeda)
    return (
        clear_name(name) in each_name_from_exchange[0]
        and each_name_from_exchange[0].index(clear_name(name)) == 0
        and (
            (
                delete_spaces(
                    clear_name(name), filtered_names_objcects_with_spaces[ind]
                )
                + " "
            )[
                each_name_from_exchange[0].index(clear_name(name))
                + len(clear_name(name))
            ]
            == " "
        )
    )
