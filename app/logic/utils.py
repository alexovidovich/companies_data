import datetime


def standartify_str(
    some_str, args_to_replace, lower=False, to_what="", nothing_after_arg=False
):
    some_str = some_str.lower() if lower else some_str
    for each_arg_to_replace in args_to_replace:
        if nothing_after_arg:
            try:
                index_of_end_of_each_arg_to_replace = (
                    some_str.index(each_arg_to_replace) + len(each_arg_to_replace) - 1
                )
                if some_str[index_of_end_of_each_arg_to_replace] == some_str[-1] or (
                    some_str[index_of_end_of_each_arg_to_replace + 1] == " "
                ):
                    some_str = some_str.replace(each_arg_to_replace, to_what)
            except:
                pass
        else:
            some_str = some_str.replace(each_arg_to_replace, to_what)
    return some_str


def conv_time(time_, other_patern=None):
    if time_:
        if isinstance(time_, str):
            if other_patern:
                return datetime.datetime.strptime(time_, "%m-%d-%Y")
            return datetime.datetime.strptime(time_, "%Y-%m-%d")
        else:
            return time_


def deconv_time(time_):
    if time_:
        if isinstance(time_, str):
            return time_
        else:
            return time_.strftime("%Y-%m-%d")
