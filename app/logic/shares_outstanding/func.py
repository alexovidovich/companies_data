import datetime

from logic.func import (
    check,
    write_db,
)

from logic.utils import conv_time


def make_real_numbers_of_shares_outstanding(
    all_sec_objects,
    each_shares_outstanding_object,
):
    if all_sec_objects:
        dif_1 = [
            all_sec_objects[-1].shares_outstanding * 1000000,
            float(each_shares_outstanding_object.get("val")) * 1000,
        ]
        dif_2 = [
            all_sec_objects[-1].shares_outstanding * 1000000,
            float(each_shares_outstanding_object.get("val")) / 1000,
        ]
        if 100 - (min(dif_1) / max(dif_1)) * 100 <= 20:
            shares_outstanding = round(
                float(each_shares_outstanding_object.get("val")) / 1000, 2
            )
        elif 100 - (min(dif_2) / max(dif_2)) * 100 <= 20:
            shares_outstanding = round(
                float(each_shares_outstanding_object.get("val")) / 1000000000, 2
            )
        else:
            shares_outstanding = round(
                float(each_shares_outstanding_object.get("val")) / 1000000, 2
            )
    else:
        shares_outstanding = (
            round(float(each_shares_outstanding_object.get("val")) / 1000000000, 2)
            if float(each_shares_outstanding_object.get("val")) > 1000000000
            else round(float(each_shares_outstanding_object.get("val")) / 1000000, 2)
        )

    return shares_outstanding


def save_db(
    session,
    model,
    name,
    ticker,
    date=None,
    end_date=None,
    shares=None,
    country=None,
    url=None,
    form=None,
):

    obj_to_write = (
        {
            "name": str(name),
            "ticker": str(ticker),
            "date": date,
            "shares_outstanding": shares,
            "end_date": end_date,
            "form": form,
        }
        if end_date
        else {
            "name": str(name),
            "ticker": str(ticker),
            "date": date,
            "shares_outstanding": shares,
        }
    )
    if country == "uk":
        obj_to_write.update({"url": url})
    from_date = datetime.datetime(2013, 1, 1)
    if date > from_date:
        db_obj_shares_with_such_date = (
            session.query(model).filter(model.name == name, model.date == date).first()
        )
        if end_date:
            lst_objects_of_model = session.query(model).filter(model.name == name).all()
            late = next(
                (
                    each_object_of_model
                    for each_object_of_model in lst_objects_of_model
                    if each_object_of_model.end_date > conv_time(end_date)
                    and each_object_of_model.date < date
                ),
                None,
            )
            if not late:
                if not db_obj_shares_with_such_date:
                    write_db(model, session, obj_to_write)
                elif db_obj_shares_with_such_date.form and form:
                    if db_obj_shares_with_such_date.end_date == conv_time(end_date):
                        prio = (
                            ("a", "not6"),
                            ("q", ""),
                            ("k", "not6"),
                            ("f", ""),
                            ("a", "6"),
                            ("6", ""),
                        )
                        my_form = next(
                            index for index, i in enumerate(prio) if check(i, form)
                        )
                        form_from_db = next(
                            index
                            for index, i in enumerate(prio)
                            if check(i, db_obj_shares_with_such_date.form)
                        )
                        if my_form <= form_from_db:
                            session.delete(db_obj_shares_with_such_date)
                            write_db(model, session, obj_to_write)
                    elif db_obj_shares_with_such_date.end_date < conv_time(end_date):
                        session.delete(db_obj_shares_with_such_date)
                        write_db(model, session, obj_to_write)
        elif not db_obj_shares_with_such_date:
            write_db(model, session, obj_to_write)
