from logic.utils import standartify_str
import unicodedata
from logic.func import read_json, open_csv
from logic.names.utils import clear_name, slice_names
from logic.names.not_listed import not_listed_companies
from logic.names.listed import listed_companies, get_nasdaq_nyse_info
from logic.names.var import same_words
import functools
from core.db import SessionLocal
from models.models import Names


def manipulations_with_each_name(name, file_out, names_from_two_ex, original_name):
    # открываю сессию, достаю все что есть в бд, и запускаю алг по поиску в биржах(listed_companies), если не находит, то запускаю по поиску в edgar(not_listed_companies)
    with SessionLocal() as session:
        already_in = session.query(Names).all()
        not_listed = None
        listed = listed_companies(
            name, names_from_two_ex, already_in, file_out, session, original_name
        )
        if not listed and next(
            (False for x in already_in if original_name in x.original_names), True
        ):
            print("not_listed", name)
            not_listed = not_listed_companies(
                name, names_from_two_ex, already_in, file_out, session, original_name
            )
        if not_listed or listed:
            return True


def get_new_companies(file_in, file_out, file_type, for_one_name=None):
    # смотрю множество ли имен мне нужно обработать или одно, если много то из какого формата(json,csv)
    if for_one_name:
        names = [for_one_name]
    elif file_type == "csv":
        names = [x.get("original_names").split(";")[0] for x in open_csv(file_in)]
    elif file_type == "json":
        names = functools.reduce(lambda c, x: c + x, read_json(file_in), [])
    # убираю артефакты кодировки
    names = [
        clear_name(
            "".join(
                ch
                for ch in unicodedata.normalize("NFKD", y)
                if not unicodedata.combining(ch)
            ),
            only_sub_encoding=True,
        )
        for y in names
    ]
    # получаю все компании из нужных бирж
    names_from_two_ex = get_nasdaq_nyse_info()
    # итерируюсь по именам, запоминаю оригинальное имя, убираю все лишнее в именах через метод slice_names, на всякий случай
    for name in names:
        print(name)
        original_name = name
        name = slice_names(name).strip()
        same_word_inside_name = None
        # пробую искать все данные по этому имени
        found_a_row = manipulations_with_each_name(
            name, file_out, names_from_two_ex, original_name
        )
        # если не нашлось, то пробую подменять различные слова на синонимы из переменной same_words и запускаю алг также как и выше
        if not found_a_row:
            for same_word_list in same_words:
                same_word_inside_name = next(
                    (
                        each_word
                        for each_word in same_word_list
                        if each_word in [x.strip() for x in name.split(" ")]
                        or each_word.capitalize()
                        in [x.strip() for x in name.split(" ")]
                        or each_word.upper() in [x.strip() for x in name.split(" ")]
                    ),
                    None,
                )
                if same_word_inside_name:
                    done = None
                    for each_word in same_word_list:
                        if (
                            each_word.strip().lower()
                            != same_word_inside_name.strip().lower()
                        ):
                            name = standartify_str(
                                name,
                                [
                                    same_word_inside_name,
                                    same_word_inside_name.capitalize(),
                                    same_word_inside_name.upper(),
                                ],
                                to_what=each_word,
                            )
                            done = manipulations_with_each_name(
                                name, file_out, names_from_two_ex, original_name
                            )
                    if done:
                        break
