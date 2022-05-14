import os.path as path
import re
import time
from logic.utils import conv_time

from core.db import SessionLocal

import logic.shares_outstanding.chwrap.search as chwr
from logic.func import find_full_name
from logic.shares_outstanding.func import save_db
from logic.shares_outstanding.shares_sec_macro import sec
from models.models import UK

import ocrmypdf

import pdftotext

import pikepdf

import sqlalchemy


def regular_ex_uk(reg, text):
    shares = re.findall(reg, text)
    for each in shares:
        if each.isdigit() and len(each) > 5:
            return each


def find_shares_demo(text):
    text = text.lower()

    regs = [
        (x, "")
        for x in [
            " ",
            ",",
            ".",
            ":",
            "{",
            "}",
            "[",
            "]",
            "@",
            "~",
            "`",
            "^",
            "#",
            "±",
            "+",
            "%",
            '"',
            "'",
            ";",
            "_",
            "=",
            "*",
            "©",
            "®",
            "!",
            "?",
            "<",
            ">",
            "|",
            "/",
            "(",
            ")",
            "if",
            "any",
            "pages",
            "including",
            "continuation",
            "ordinary",
            "£0.00",
            "f50000 ",
            "50000",
            "5000",
            "000\n",
        ]
    ]
    regs.append(("§", "5"))

    for rep in regs:
        text = text.replace(*rep)

    if "numberofshares" and "statementofcapital" in text:
        all_cases = (
            r"otals\n*(\d+)[^0123456789]\n*",
            r"total\n*number\n*of\n*shares\n*(\d+)[^0123456789]\n*",
            r"totals\n*aggregate\n*nominal\n*value\n*(\d+)[^0123456789]\n*",
            r"number\n*of\n*shares\n*aggregate\n*nominal\n*value\n*(\d+)[^0123456789]\n*",
            r"number\n*of\n*shares\n*total\n*aggregate\n*nominal\n*value\n*(\d+)[^0123456789]\n*",
            r"\n*total\n*aggregate\n*nominal\n*value\n*(\d+)[^0123456789],\n*total\n*number\n*of\n*shares\n*",
            r"\n*aggregate\n*nominal\n*value\n*(\d+)[^0123456789]\n*number\n*of\n*shares\n*",
            r"\n*(\d+)[^0123456789]\n*total\n*aggregate\n*nominal/n*value\n*total\n*number\n*of\n*shares\n*",
            r"\n*(\d+)[^0123456789]\n*aggregate\n*nominal\n*value\n*totals\n*",
            r"shares\n*nominal\n*value\n*amount\n*unpaid\n*(\d+)[^0123456789]\n*aggregate\n*nominal\n*value\n*number\n*of\n*shares\n*totals\n*",
            r"aggregate\n*amount\n*unpaid(\d+)[^0123456789]\n*",
            r"total\n*number\n*(\d+)[^0123456789]\n*of\n*shares\n*",
            r"\n*(\d+)[^0123456789]\n*aggregate\n*nominal\n*value\n*number\n*of\n*shares\n*totals\n*",
            r"\n*shares\n*nominal\n*value\n*amount\n*unpaid\n*(\d+)[^0123456789]\n*",
            r"number\n*ofshares\n*total\n*aggregate\n*nominal\n*value\n*total\n*aggregate\n*amount\n*unpaid\n*(\d+)[^0123456789]\n*",
            r"\n*(\d+)[^0123456789]\n*totals",
            r"\n*aggregate\n*nominal\n*value\n(\d+)[^0123456789]",
            r"0etc\n*(\d+)\n*",
        )

        for each_case in all_cases:
            final = regular_ex_uk(each_case, text)
            if final:
                return final


def make_pdf(file_in, file_out):
    try:
        ocrmypdf.ocr(
            file_in,
            file_out,
            output_type="pdfa",
            pdf_renderer="hocr",
            language="eng",
            oversample=460,
            use_threads=True,
        )
    except:
        pass
    with open(file_out, "rb") as f:
        text = pdftotext.PDF(f)
    return text


def get_filings(search_client, company_number, start_index, name, ticker):
    time.sleep(1)
    response = search_client.filing_history(
        company_number, items_per_page="100", start_index=str(start_index)
    )
    response = response.json()
    filings = [
        filing
        for filing in response.get("items")
        if filing.get("type") == "SH01"
        and filing.get("links")
        and int(filing.get("action_date")[:4]) > 2012
    ]
    for filing in filings:
        date = conv_time(filing.get("action_date"))
        with SessionLocal() as session:
            same_year_and_month = (
                session.query(UK)
                .filter(
                    UK.name == name,
                    sqlalchemy.extract("month", UK.date) == date.strftime("%m"),
                    sqlalchemy.extract("year", UK.date) == date.strftime("%Y"),
                )
                .first()
            )
            if not same_year_and_month:
                document_id = (
                    filing.get("links").get("document_metadata").split("/")[-1]
                )
                pdf = f"data/documents/pdf/{name}-{document_id}.pdf"
                url_in_database = (
                    session.query(UK)
                    .filter(
                        UK.url == pdf,
                    )
                    .first()
                )
                if not url_in_database:
                    if not path.exists(pdf):
                        try:
                            time.sleep(1)
                            document = search_client.document(document_id)
                        except:
                            time.sleep(5)
                            document = search_client.document(document_id)

                        print(document.status_code)
                        document = document.content
                        with open(pdf, "wb") as f:
                            f.write(document)
                    shares = None
                    pages = pikepdf.open(pdf)
                    for index, page in enumerate(pages.pages):
                        if index > 0:
                            page_pdf = pikepdf.Pdf.new()
                            page_pdf.pages.append(page)
                            page_pdf_path = f"data/documents/pdf/{document_id}-{name}-{str(index)}.pdf"
                            page_pdf.save(page_pdf_path)
                            text = make_pdf(page_pdf_path, page_pdf_path)[0]
                            shares = find_shares_demo(text)
                            if shares:
                                break
                    if shares:
                        save_db(
                            session,
                            UK,
                            name,
                            ticker,
                            date,
                            shares=round(float(shares) / 1000000, 3),
                            form="SH01",
                            country="uk",
                            url=pdf,
                        )

    if response.get("items_per_page") + start_index < response.get("total_count"):
        get_filings(search_client, company_number, start_index + 100, name, ticker)


def get_uk_comp(each_company):
    ticker = each_company.get("ticker")
    name = each_company.get("name")
    json_companies_search = None
    try:
        print(name)
        time.sleep(2)
        search_client = chwr.Search(access_token="a483267e-c3b7-4b67-abaf-eac5788399a2")
        print("hello")
        json_companies_search = (
            search_client.search_companies(term=find_full_name(ticker))
            .json()
            .get("items")[0]
        )
    except:
        sec(each_company, uk=True)
    if json_companies_search:
        company_number = json_companies_search.get("company_number")
        print("not done yet")
        get_filings(search_client, company_number, 0, name, ticker)
