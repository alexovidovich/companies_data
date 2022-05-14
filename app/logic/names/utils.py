from logic.utils import standartify_str


def delete_spaces(word, where):
    # имею две строки, одна без пробелов с обрезанием всяких ltd и тд, другая с пробелами без обрезания строки.
    # из последней забираю все пробелы в пределах первой строки
    # (если первой строки нет во второй(если убрать пробелы), то возвращаю None), но оставляю все пробелы после
    where = list(where)
    ind = 0
    while ind < len(where):
        if word in "".join(where):
            return "".join(where)
        if where[ind] == " ":
            where.pop(ind)
            ind -= 1
        ind += 1
        print(where)


def delete_many_spaces(string):
    # заменяю двойные и тройные пробелы на одиночный
    for x in range(1, 10):
        string = string.replace(x * " ", " ")
    return string


def normalize_name(name, lower=True, brack=False, dash=True, and_word=True, dots=True):
    # замена определенных символов в строке по аргументу(по надобности, для унивирасальности), замена символов на пробелы
    if brack:
        name = standartify_str(name, ["(", ")"])
    if dash:
        name = standartify_str(
            name,
            ["-", "/"],
            to_what=" ",
        )
    if and_word:
        name = standartify_str(
            name,
            ["&"],
            to_what=" ",
        )
    if dots:
        name = standartify_str(
            name,
            ["."],
            to_what=" ",
        )
    replace_args = [" inc", " ltd", " plc", " llc"]
    # заменяю строки выше в replace_args, если после них ничего нет
    normalized_name = delete_many_spaces(
        standartify_str(
            standartify_str(
                standartify_str(name, ["'", "/NEW/"]),
                [","],
                to_what=" ",
            ),
            replace_args,
            lower,
            nothing_after_arg=True,
        ).strip()
    )
    return normalized_name


def slice_names(n):
    # обрезаю имена по определенным словам
    if "common s" in n.lower():
        n = n.split("common")[0].split("Common")[0].split("COmmon")[0]
    if " class" in n.lower():
        n = n.split("class")[0].split("Class")[0]
    if "american deposit" in n.lower():
        n = n.split("american")[0].split("American")[0]
    if "depositary" in n.lower():
        n = n.split("depositary")[0].split("Depositary")[0]
    if "ordinary" in n.lower():
        n = n.split("ordinary")[0].split("Ordinary")[0]
    if "limited" in n.lower():
        n = n.split("limited")[0].split("Limited")[0]
    if " ads" in n.lower():
        n = n.split("ADS")[0]
    if "voting s" in n.lower():
        n = n.split("Voting")[0].split("voting")[0]
    if "subordinate" in n.lower():
        n = n.split("Subordinate")[0].split("subordinate")[0]
    if "(" in n:
        n = n.split("(")[0]
    return n.replace("  ", " ")


def clear_name(
    name, lower=True, spaces=True, dots=True, slash_dash=True, only_sub_encoding=False
):
    # замена определенных символов в строке по аргументу(по надобности, для унивирасальности), удаление символов, а также всех ltd и тд
    name = (
        name.replace("\u0131", "i")
        .replace("\u00f8", "o")
        .replace("\u0142", "l")
        .replace("\u00e6", "ae")
        .replace("\u00ae", "")
        .replace("\u0141", "l")
        .replace("\u00d8", "o")
        .replace("\u00df", "s")
        .replace("\u0391", "a")
    )
    if only_sub_encoding:
        return name
    args_to_replace_if_nothing_after = [
        " inc",
        " plc",
        " co",
        " llc",
        " ltd",
        " Inc",
        " Plc",
        " Co",
        " Llc",
        " Ltd",
    ]
    if lower:
        name = name.lower()
    args_to_replace = [
        "@",
        "#",
        "$",
        ",",
        ",inc",
        ",plc",
        ",co",
        ",llc",
        ",ltd",
        ".inc",
        ".plc",
        ".co",
        ".llc",
        ".ltd",
        "inc.",
        "plc.",
        "co.",
        "llc.",
        "ltd.",
    ]
    name = standartify_str(
        standartify_str(
            standartify_str(name, args_to_replace),
            [x.upper() for x in args_to_replace],
        ),
        [x.capitalize() for x in args_to_replace],
    )
    name = standartify_str(
        name, args_to_replace_if_nothing_after, nothing_after_arg=True
    )
    if spaces:
        name = name.replace(" ", "")
    if dots:
        name = name.replace(".", "")
    if slash_dash:
        name = name.replace("-", "").replace("/", "")
    return delete_many_spaces(name).strip()
