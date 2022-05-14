import time
import datetime


def conv_time(time):
    if time:
        return datetime.datetime.strptime(time, "%Y-%m-%d")


import csv
import codecs
import numpy as np


def normalize(data):
    x_norm = (data - np.min(data)) / (np.max(data) - np.min(data))
    return x_norm


with open("stocktwits (5).csv", "r", newline="", encoding="utf-8") as f:
    # ___________________________________MAIN__________________________________
    raws = csv.DictReader(x.replace("\0", "") for x in f)
    raws = [
        value
        for index, value in enumerate(raws)
        if conv_time(value.get("created_at")[:10]).year > 2012
    ]
    raws_datetime = list(
        reversed(sorted(raws, key=lambda x: conv_time(x.get("created_at")[:10])))
    )

    # ___________________________________EACH YEAR__________________________________
    set_years = list(
        set([conv_time(x.get("created_at")[:10]).year for x in raws_datetime])
    )
    all_years_final = {}
    for each_year in set_years:
        each_year_raws = [
            x
            for x in raws_datetime
            if conv_time(x.get("created_at")[:10]).year == each_year
        ]

        # print([f"{x:.9f}" for x in normalized_list])
        # print(max(normalized_list), min(normalized_list))
        all_posts_for_each_user = [
            (
                int(each_raw.get("user_id")),
                each_raw.get("user_name"),
                each_raw.get("created_at")[:10],
            )
            for each_raw in each_year_raws
        ]
        np_all_posts_for_each_user = np.array(
            [int(each_raw.get("ideas")) for each_raw in each_year_raws]
        )
        normalized_all_posts_for_each_user = list(
            set(
                zip(
                    list(normalize(np_all_posts_for_each_user)), all_posts_for_each_user
                )
            )
        )
        # ___________________________________НОРМАЛИЗОВАННОЕ КОЛ-ВО ВСЕХ ЛАЙКОВ ОТ ПОСТОВ ЭТОГО ЮЗЕРА ПРО ЭТУ КОМПАНИЮ__________________________________

        all_posts_likes_of_this_user_for_this_company = [
            sum(
                [
                    int(j.get("likes"))
                    for j in each_year_raws
                    if j.get("user_id") == each_raw.get("user_id")
                ]
            )
            for each_raw in each_year_raws
        ]
        np_all_posts_likes_of_this_user_for_this_company = np.array(
            all_posts_likes_of_this_user_for_this_company
        )

        normalized_all_posts_likes_of_this_user_for_this_company = list(
            set(
                zip(
                    list(normalize(np_all_posts_likes_of_this_user_for_this_company)),
                    all_posts_for_each_user,
                )
            )
        )
        # ___________________________________официальный__________________________________
        official_or_not = list(
            set(
                zip(
                    [x.get("official") for x in each_year_raws],
                    all_posts_for_each_user,
                )
            )
        )
        # ___________________________________НОРМАЛИЗОВАННОЕ КОЛ-ВО ВСЕХ КОММЕНТОВ ОТ ПОСТОВ ЭТОГО ЮЗЕРА ПРО ЭТУ КОМПАНИЮ__________________________________
        all_posts_replies_of_this_user_for_this_company = [
            sum(
                [
                    int(j.get("replies"))
                    for j in each_year_raws
                    if j.get("user_id") == each_raw.get("user_id")
                ]
            )
            for each_raw in each_year_raws
        ]
        np_all_posts_replies_of_this_user_for_this_company = np.array(
            all_posts_replies_of_this_user_for_this_company
        )

        normalized_all_posts_replies_of_this_user_for_this_company = list(
            set(
                zip(
                    list(normalize(np_all_posts_replies_of_this_user_for_this_company)),
                    all_posts_for_each_user,
                )
            )
        )
        # ___________________________________НОРМАЛИЗОВАННОЕ КОЛ-ВО ВСЕХ РЕПОСТОВ ОТ ПОСТОВ ЭТОГО ЮЗЕРА ПРО ЭТУ КОМПАНИЮ__________________________________
        all_posts_shares_of_this_user_for_this_company = [
            sum(
                [
                    int(j.get("reshares_count"))
                    for j in each_year_raws
                    if j.get("user_id") == each_raw.get("user_id")
                ]
            )
            for each_raw in each_year_raws
        ]
        np_all_posts_shares_of_this_user_for_this_company = np.array(
            all_posts_shares_of_this_user_for_this_company
        )

        normalized_all_posts_shares_of_this_user_for_this_company = list(
            set(
                zip(
                    list(normalize(np_all_posts_shares_of_this_user_for_this_company)),
                    all_posts_for_each_user,
                )
            )
        )

        final_this_year = {
            str(each_year): {
                "posts": normalized_all_posts_for_each_user,
                "likes": normalized_all_posts_likes_of_this_user_for_this_company,
                "replies": normalized_all_posts_replies_of_this_user_for_this_company,
                "shares": normalized_all_posts_shares_of_this_user_for_this_company,
            }
        }
        all_years_final.update(final_this_year)

    # ___________________________________FOLLOWERS__________________________________
    all_time_raws_followers = [
        (int(x.get("followers")), (x.get("user_id"), x.get("created_at")[:10]))
        for x in each_year_raws
    ]
    np_all_time_raws_followers = np.array([x[0] for x in all_time_raws_followers])
    normalized_list_all_time_raws_followers = list(
        normalize(np_all_time_raws_followers)
    )
    normalized_list_all_time_raws_followers = list(
        set(
            zip(
                normalized_list_all_time_raws_followers,
                [x[1] for x in all_time_raws_followers],
            )
        )
    )
    # ___________________________________ОТНОШЕНИЕ КОЛ-ВА ПОСТОВ ПРО ЭТУ КОМПАНИЮ К ОБЩЕМУ КОЛ-ВУ ПОСТОВ КАЖДОГО ЮЗЕРА__________________________________
    one_company_all_posts_of_user_divided_by_all_posts_of_user = list(
        set(
            [
                (
                    len(
                        [
                            ""
                            for j in raws_datetime
                            if j.get("user_id") == each_raw.get("user_id")
                        ]
                    )
                    / int(each_raw.get("ideas")),
                    each_raw.get("user_id"),
                    each_raw.get("user_name"),
                    each_raw.get("created_at")[:10],
                )
                for each_raw in raws_datetime
            ]
        )
    )

    # ___________________________________НОРМАЛИЗОВАННОЕ КОЛ-ВО ВСЕХ ПОСТОВ ВСЕХ ЮЗЕРОВ ПРО ЭТУ КОМПАНИЮ__________________________________

    ready_data = {
        "followers": normalized_list_all_time_raws_followers,
        "divided_posts": one_company_all_posts_of_user_divided_by_all_posts_of_user,
        "officaial": official_or_not,
        "historical": all_years_final,
    }
    print(ready_data.get("historical").get("2018").get("replies"))
