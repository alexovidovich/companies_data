from datetime import timedelta

from logic.func import (
    write_db,
)
from logic.utils import conv_time, deconv_time

from models.models import Research_year

from sqlalchemy import extract


def get_late_start_and_late_date(session, model, name, to_base):
    start_date = (
        conv_time(to_base.get("start_date"))
        if isinstance(to_base.get("start_date"), str)
        else to_base.get("start_date")
    )
    date = (
        conv_time(to_base.get("date"))
        if isinstance(to_base.get("date"), str)
        else to_base.get("date")
    )
    late_start = (
        session.query(model)
        .filter(
            model.name == name,
            model.start_date > start_date,
        )
        .first()
    )
    late_date = (
        session.query(model)
        .filter(
            model.name == name,
            model.date > date,
        )
        .first()
    )
    return late_start, late_date


def for_commit_or_not(session, model, name, to_base, eq_only=False):
    if not eq_only:
        same_start_date = (
            session.query(model)
            .filter(
                model.name == name,
                model.start_date == conv_time(to_base.get("start_date")),
                model.end_date < conv_time(to_base.get("end_date")),
            )
            .first()
        )
        same_end_date = (
            session.query(model)
            .filter(
                model.name == name,
                model.start_date < conv_time(to_base.get("start_date")),
                model.end_date == conv_time(to_base.get("end_date")),
            )
            .first()
        )
        if same_start_date:

            to_base.update(
                {
                    "start_date": deconv_time(
                        same_start_date.end_date + timedelta(days=1)
                    ),
                    "research_and_development": float(
                        to_base.get("research_and_development"),
                    )
                    - same_start_date.research_and_development,
                }
            )
        if same_end_date:
            if (
                same_end_date.research_and_development
                - float(to_base.get("research_and_development"))
                > 0
                and conv_time(
                    to_base.get("start_date"),
                )
                - timedelta(days=1)
                > same_end_date.start_date
            ):
                same_end_date.end_date = (
                    conv_time(
                        to_base.get("start_date"),
                    )
                    - timedelta(days=1)
                )
                same_end_date.research_and_development = (
                    same_end_date.research_and_development
                    - float(to_base.get("research_and_development"))
                )
                session.commit()
    equal = (
        session.query(model)
        .filter(
            model.name == name,
            model.start_date == conv_time(to_base.get("start_date")),
            model.end_date == conv_time(to_base.get("end_date")),
            model.research_and_development
            == float(to_base.get("research_and_development")),
        )
        .first()
    )
    equal_2 = (
        session.query(model)
        .filter(
            model.name == name,
            model.date == conv_time(to_base.get("date")),
            model.start_date == conv_time(to_base.get("start_date")),
            model.end_date == conv_time(to_base.get("end_date")),
            model.research_and_development
            != float(to_base.get("research_and_development")),
        )
        .first()
    )
    late_start, late_date = get_late_start_and_late_date(session, model, name, to_base)
    return late_start, late_date, equal, equal_2, to_base


def get_only_year_data(session, model, name, to_base, param=None):
    late_start, late_date, equal, equal_2, to_base = for_commit_or_not(
        session, Research_year, name, to_base, eq_only=True
    )
    if (
        333
        < (
            conv_time(to_base.get("end_date")) - conv_time(to_base.get("start_date"))
        ).days
        < 390
        and not equal_2
        and not equal
        and not late_start
        and not late_date
    ):
        write_db(Research_year, session, to_base)


def make_year_data_from_q(session, model, name, to_base, param=None):
    years = {}
    all_rows = list(
        session.query(model)
        .filter(
            model.name == name,
        )
        .all()
    )

    for row in all_rows:
        if (row.end_date - row.start_date).days < 400:
            if years.get(str(row.start_date.year)) and years.get(
                str(row.end_date.year)
            ):
                years.update(
                    {
                        str(row.start_date.year): [
                            *years.get(str(row.start_date.year)),
                            row,
                        ]
                    }
                )
            elif not years.get(str(row.start_date.year)) and not years.get(
                str(row.end_date.year)
            ):
                years.update({str(row.start_date.year): [row]})
    for each_year in list(years.keys()):
        if (
            len(years.get(each_year)) == 4
            or (
                len(years.get(each_year)) == 3
                and next(
                    (
                        True
                        for x in years.get(each_year)
                        if (x.end_date - x.start_date).days > 150
                    ),
                    None,
                )
            )
            or (
                len(years.get(each_year)) == 1
                and (
                    years.get(each_year)[0].end_date
                    - years.get(each_year)[0].start_date
                ).days
                > 333
            )
        ):
            first_month_row = next(
                (row for row in years.get(each_year) if row.start_date.month == 1), None
            )
            last_month_row = next(
                (row for row in years.get(each_year) if row.end_date.month == 12), None
            )
            if first_month_row and last_month_row:
                to_base.update(
                    {
                        "form": None,
                        "date": last_month_row.date,
                        "end_date": last_month_row.end_date,
                        "start_date": first_month_row.start_date,
                        "research_and_development": sum(
                            [y.research_and_development for y in years.get(each_year)]
                        ),
                    }
                )
                equel = (
                    session.query(Research_year)
                    .filter(
                        Research_year.name == name,
                        extract("year", Research_year.start_date)
                        == to_base.get("start_date").year,
                        extract("year", Research_year.end_date)
                        == to_base.get("end_date").year,
                    )
                    .first()
                )
                late_start, late_date = get_late_start_and_late_date(
                    session, Research_year, name, to_base
                )
                if not equel and not late_start and not late_date:
                    write_db(Research_year, session, to_base)


def get_missing_year_only_research_obj(session, model, name, to_base, param=None):
    all_rows = (
        session.query(model)
        .filter(
            model.name == name,
        )
        .all()
    )
    exist = next((x for x in all_rows if (x.end_date - x.start_date).days < 333), None)
    late_start, late_date = get_late_start_and_late_date(session, model, name, to_base)
    delta_end_start = (
        conv_time(to_base.get("end_date")) - conv_time(to_base.get("start_date"))
    ).days > 333
    if not late_start and not exist:
        _, _, equal, equal_2, to_base = for_commit_or_not(
            session, model, name, to_base, eq_only=True
        )
        if (
            not late_start
            and not late_date
            and not equal
            and not equal_2
            and delta_end_start
            and to_base.get("research_and_development") > 0
        ):
            write_db(model, session, to_base)


def research_check_if_fresh_and_late_data_and_commit(
    session,
    model,
    name,
    to_base,
    param=None,
):
    late_start, late_date = get_late_start_and_late_date(session, model, name, to_base)
    delta_end_start = (
        conv_time(to_base.get("end_date")) - conv_time(to_base.get("start_date"))
    ).days < 333
    if not late_start:
        late_start, late_date, equal, equal_2, to_base = for_commit_or_not(
            session, model, name, to_base
        )
        if (
            not late_start
            and not late_date
            and not equal
            and not equal_2
            and delta_end_start
            and (
                conv_time(to_base.get("end_date"))
                - conv_time(to_base.get("start_date"))
            ).days
            > 20
            and to_base.get("research_and_development") > 0
        ):
            write_db(model, session, to_base)
    else:
        months = [1, 12]
        if (
            not delta_end_start
            and conv_time(to_base.get("end_date")).month in months
            and conv_time(to_base.get("start_date")).month in months
        ):
            print(to_base.get("start_date"), to_base.get("end_date"))
            all_the_same_year = (
                session.query(model)
                .filter(
                    model.name == name,
                    extract("year", model.start_date)
                    == int(conv_time(to_base.get("start_date")).year),
                )
                .all()
            )

            print(int(conv_time(to_base.get("start_date")).year))
            print("NUMBER:::", len(all_the_same_year))
            if all_the_same_year:
                new_start_date = None
                new_end_date = None
                if len(all_the_same_year) == 1:
                    if (
                        all_the_same_year[0].start_date.month == 1
                        and (
                            all_the_same_year[0].end_date
                            - all_the_same_year[0].start_date
                        ).days
                        < 333
                    ):
                        new_start_date = deconv_time(
                            all_the_same_year[0].end_date + timedelta(days=1)
                        )
                        new_end_date = to_base.get("end_date")
                if len(all_the_same_year) in [2, 3]:
                    all_the_same_year = sorted(
                        list(all_the_same_year), key=lambda x: x.start_date
                    )
                    # есть пробелы между записями?
                    one_of_spaces = next(
                        (
                            True
                            for index in range(0, len(all_the_same_year) - 1)
                            if (
                                all_the_same_year[index + 1].start_date
                                - all_the_same_year[index].end_date
                            ).days
                            > 5
                        ),
                        None,
                    )
                    if not one_of_spaces:
                        # с края
                        if next(
                            (
                                x
                                for x in all_the_same_year
                                if x.start_date.month == 1
                                and (x.end_date - x.start_date).days < 333
                            ),
                            None,
                        ):
                            new_start_date = deconv_time(
                                all_the_same_year[-1].end_date + timedelta(days=1)
                            )
                            new_end_date = to_base.get("end_date")
                year_row_in_db = next(
                    (
                        x
                        for x in all_the_same_year
                        if (x.end_date - x.start_date).days > 333
                    ),
                    None,
                )
                if new_end_date and new_start_date:
                    if year_row_in_db:
                        session.delete(year_row_in_db)
                        session.commit()

                    research_and_development = (
                        float(
                            to_base.get("research_and_development"),
                        )
                        - sum([x.research_and_development for x in all_the_same_year])
                    )
                    if research_and_development:
                        to_base.update(
                            {
                                "start_date": new_start_date,
                                "end_date": new_end_date,
                                "research_and_development": research_and_development,
                            }
                        )
                        (
                            late_start,
                            late_date,
                            equal,
                            equal_2,
                            to_base,
                        ) = for_commit_or_not(session, model, name, to_base)

                        if (
                            not late_date
                            and not late_start
                            and not equal
                            and not equal_2
                            and (
                                conv_time(to_base.get("end_date"))
                                - conv_time(to_base.get("start_date"))
                            ).days
                            > 20
                            and to_base.get("research_and_development") > 0
                        ):

                            write_db(model, session, to_base)
