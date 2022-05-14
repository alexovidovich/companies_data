import requests
from logic.utils import standartify_str
from logic.var import headers_html
from logic.func import write_db
from logic.names.conditions import condition_for_nasdaq, condition_to_write
from logic.names.utils import slice_names, clear_name, delete_many_spaces
from logic.names.cik import get_cik
from logic.names.func import (
    # changing_ticker,
    get_cik_and_ticker_by_name_or_number_of_simular_comp,
)
from models.models import Names


def find_ticker_by_name_nyse_nasdaq(name, names, already_in, original_name, session):
    name = name.strip()
    # смотрю кол-во найденых компаний по этому имени
    number_of_simular_comp = get_cik_and_ticker_by_name_or_number_of_simular_comp(
        name, get_number_of_simular_comp=True
    )
    # если не нашлось, то тогда немного меняю имя, убираю двойные и более пробелы, заменяя символы и пробую еще разок
    if number_of_simular_comp == 0:
        name_for_request = clear_name(
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
        number_of_simular_comp = get_cik_and_ticker_by_name_or_number_of_simular_comp(
            name_for_request, get_number_of_simular_comp=True
        )
    # если не нашел более 25(просто примерное число на практике определил) значит вероятность попасть в нужную компанию высокая(тк бывают original_names из одного слова и порой это слово слишком частое)
    if number_of_simular_comp < 25:
        filtered_names_objcects = []
        filtered_names_objcects_with_spaces = []
        not_filtered_name_objcects = []
        # фильтрую имена, чтобы не были пустыми пробелами(такое случается, разработчики биржи такое допускают)
        for x in [
            x
            for x in names
            if slice_names(x[1])
            and not clear_name(slice_names(x[1]), spaces=False).strip().isspace()
        ]:
            # тикер, имя, страна, биржа
            t, n, country, exchange = x
            # закидываю нефильтрованные имена из биржи
            not_filtered_name_objcects.append(n)
            n = slice_names(n)
            # затем имена без пробелов фильтрованные
            filtered_names_objcects.append(
                (clear_name(n).strip(), t, country, exchange)
            )
            # и имена фильтрованные с пробелами
            filtered_names_objcects_with_spaces.append(
                clear_name(n, spaces=False).strip()
            )
        # теперь просматриваю общее кол-во компаний которые находятся в биржах по этому имени
        all_fits = [
            each_name_from_exchange
            for ind, each_name_from_exchange in enumerate(filtered_names_objcects)
            if condition_for_nasdaq(
                name, each_name_from_exchange, filtered_names_objcects_with_spaces, ind
            )
        ]
        # использую тот же фильтр что и выше, проверяю можно ли записать в бд(есть ли в бд, если есть просто дописываю original_names и забиваю,
        #  а также проверяю длину найденных компаний(если длина будет большой, значит это частое слово в начале имен компаний))
        for ind, each_name_from_exchange in enumerate(filtered_names_objcects):
            if (
                condition_for_nasdaq(
                    name,
                    each_name_from_exchange,
                    filtered_names_objcects_with_spaces,
                    ind,
                )
                and condition_to_write(
                    each_name_from_exchange[1], name, already_in, original_name, session
                )
                and len(all_fits) <= 3
            ):
                company_info_to_final = [
                    (
                        clear_name(
                            slice_names(not_filtered_name_objcects[ind]),
                            lower=False,
                            spaces=False,
                            dots=False,
                            slash_dash=False,
                        ).strip(),
                        each_name_from_exchange[1],
                        each_name_from_exchange[2],
                        True,
                        each_name_from_exchange[3],
                    )
                ]
                # нахожу новый тикер, если такой есть, в 99 процентах или даже в 100 нет, но на всякий случай
                # new_ticker, new_name = changing_ticker(
                #     ticker=each_name_from_exchange[1]
                # )
                # if new_ticker and condition_to_write(
                #     new_ticker, name, already_in, original_name, session
                # ):
                #     company_info_to_final.append(
                #         (
                #             clear_name(
                #                 slice_names(new_name),
                #                 lower=False,
                #                 spaces=False,
                #                 dots=False,
                #                 slash_dash=False,
                #             ).strip(),
                #             new_ticker,
                #             each_name_from_exchange[2],
                #             True,
                #             each_name_from_exchange[3],
                #         )
                #     )
                return company_info_to_final


def get_nasdaq_nyse_info():
    names_from_two_ex = []
    for exchange in ["NASDAQ", "NYSE", "AMEX"]:
        url = f"https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25&offset=0&exchange={exchange}&download=true"
        response = requests.get(url, headers=headers_html)
        all_rows = response.json().get("data").get("rows")
        names_from_ex = [
            (
                x.get("symbol"),
                x.get("name"),
                x.get("country"),
                standartify_str(exchange, ["[", "]"]),
            )
            for x in all_rows
        ]
        names_from_two_ex.extend(names_from_ex)
    return names_from_two_ex


def listed_companies(
    name, names_from_two_ex, already_in, file_out, session, original_name
):
    to_base_list = []
    if not to_base_list:
        # получаю список из двух или одного картежей(я переделаю еще это сразу под объекты(осталось от записи в csv без бд), на всякий случай, если вдруг одновременно на бирже будут два тикера, один не будет обновляться, а другой будет,
        # то это просто смена тикера(для предусмотрительности чтобы собрать и тот и другой)
        to_base_list = find_ticker_by_name_nyse_nasdaq(
            name, names_from_two_ex, already_in, original_name, session
        )
    if to_base_list:
        for each_info in to_base_list:
            # проверяю на наличие уже в бд(вторая проверка, чтобы перестраховаться), первая находится в find_ticker_by_name_nyse_nasdaq, в condition_to_write(там если повторяется запись, то дописывается original_names)
            if (
                each_info[1] not in [x.ticker for x in already_in]
                or (
                    clear_name(each_info[0])
                    not in [clear_name(x.name) for x in already_in]
                    and clear_name(name) not in [clear_name(x.name) for x in already_in]
                )
            ) and each_info[-1]:
                # добываю cik , прошлые и ненышние имена
                cik, formerly, now = get_cik(each_info[0], each_info[1])
                # формирую объект и пишу в бд
                to_base = {
                    "name": each_info[0],
                    "ticker": each_info[1],
                    "country": each_info[2],
                    "listed": each_info[3],
                    "exchange": each_info[4],
                    "cik": cik,
                    "formerly_names": formerly,
                    "current_name": now,
                    "original_names": original_name,
                }
                write_db(Names, session, to_base)
                return True
            else:
                print(each_info, "WRONG")
    else:
        return None
