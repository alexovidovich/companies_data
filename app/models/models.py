from core.db import Base

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
)
from sqlalchemy.orm import relationship


class Names(Base):
    id = Column(Integer, primary_key=True, index=True, unique=True)
    name = Column(String)
    ticker = Column(String)
    country = Column(String)
    listed = Column(Boolean)
    exchange = Column(String)
    cik = Column(String)
    formerly_names = Column(String)
    current_name = Column(String)
    original_names = Column(String)
    __tablename__ = "names"


class Number_of_objects(Base):
    id = Column(Integer, primary_key=True, index=True, unique=True)
    company = Column(String)
    ticker = Column(String)
    date = Column(DateTime)
    position = Column(String)
    number = Column(Integer)
    last_object_date = Column(DateTime)
    __tablename__ = "number_of_objects"


class Macrotrends(Base):
    id = Column(Integer, primary_key=True, index=True, unique=True)
    name = Column(String)
    ticker = Column(String)
    date = Column(DateTime)
    shares_outstanding = Column(Float)
    __tablename__ = "macrotrends"


class Sharesoutstandinghistory(Base):
    id = Column(Integer, primary_key=True, index=True, unique=True)
    name = Column(String)
    ticker = Column(String)
    date = Column(DateTime)
    shares_outstanding = Column(Float)
    __tablename__ = "Sharesoutstandinghistory"


class SEC(Base):
    id = Column(Integer, primary_key=True, index=True, unique=True)
    name = Column(String)
    ticker = Column(String)
    date = Column(DateTime)
    end_date = Column(DateTime)
    shares_outstanding = Column(Float)
    form = Column(String)
    __tablename__ = "SEC"


class countries(Base):
    id = Column(Integer, primary_key=True, index=True, unique=True)
    name = Column(String)
    ticker = Column(String)
    new_ticker = Column(String)
    country = Column(String)
    cik = Column(String)

    __tablename__ = "countries"


class UK(Base):
    id = Column(Integer, primary_key=True, index=True, unique=True)
    name = Column(String)
    ticker = Column(String)
    date = Column(DateTime)
    shares_outstanding = Column(Float)
    url = Column(String)
    form = Column(
        String,
        default="SH01",
    )
    __tablename__ = "uk"


class Institutional_holdings_2(Base):
    id = Column(Integer, primary_key=True, index=True, unique=True)
    name = Column(String)
    ticker = Column(String)
    file_date = Column(DateTime)
    end_date = Column(DateTime)
    form = Column(String, default="F-13")
    percentage = Column(Float)
    shares = Column(Float)
    alg = Column(Integer)
    __tablename__ = "institutional_holdings_2"


class Institutional_holdings_raw_3(Base):
    id = Column(Integer, primary_key=True, index=True, unique=True)
    name = Column(String)
    ticker = Column(String)
    file_date = Column(DateTime)
    end_date = Column(DateTime)
    cik = Column(String)
    shares = Column(Float)
    form = Column(String, default="F-13")
    url = Column(String)

    __tablename__ = "institutional_holdings_raw_3"


class Cash(Base):
    id = Column(Integer, primary_key=True, index=True, unique=True)
    name = Column(String)
    ticker = Column(String)
    date = Column(DateTime)
    end_date = Column(DateTime)
    cash_and_cash_equivalents = Column(Float)
    form = Column(String)
    __tablename__ = "Cash"


class Research(Base):
    id = Column(Integer, primary_key=True, index=True, unique=True)
    name = Column(String)
    ticker = Column(String)
    date = Column(DateTime)
    end_date = Column(DateTime)
    start_date = Column(DateTime)
    research_and_development = Column(Float)
    form = Column(String)
    __tablename__ = "Research"


class Research_year(Base):
    id = Column(Integer, primary_key=True, index=True, unique=True)
    name = Column(String)
    ticker = Column(String)
    date = Column(DateTime)
    end_date = Column(DateTime)
    start_date = Column(DateTime)
    research_and_development = Column(Float)
    form = Column(String)
    __tablename__ = "Research_year"


association_table = Table(
    "association_owners",
    Base.metadata,
    Column("owners_id", ForeignKey("owners.id")),
    Column("transactions_and_holdings_id", ForeignKey("transactions_and_holdings.id")),
)


class Owners(Base):
    id = Column(Integer, primary_key=True, index=True, unique=True)
    cik = Column(String)
    name = Column(String)
    is_director = Column(Boolean)
    is_officer = Column(Boolean)
    is_ten_percent_owner = Column(Boolean)
    is_other = Column(Boolean)
    officer_title = Column(String)
    other_text = Column(String)
    __tablename__ = "owners"


class Transactions_and_holdings(Base):
    id = Column(Integer, primary_key=True, index=True, unique=True)
    url = Column(String)
    empty = Column(Boolean)
    company_name = Column(String)
    company_ticker = Column(String)
    company_cik = Column(String)
    period_of_report = Column(DateTime)
    file_date = Column(DateTime)
    period_ending = Column(DateTime)
    owners = relationship(
        "Owners", secondary=association_table, backref="Transactions_and_holdings"
    )
    issuer_cik = Column(String)
    issuer_name = Column(String)
    issuer_ticker = Column(String)
    security_title = Column(String)
    transaction_date = Column(DateTime)
    transaction_form_type = Column(String)
    transaction_code = Column(String)
    equity_swap_involved = Column(String)
    transaction_shares = Column(Float)
    shares_owned_following_transaction = Column(Float)
    transaction_price_per_share = Column(Float)
    underlying_security_title = Column(String)
    conversion_or_exercise_price = Column(Float)
    market_price = Column(Float)
    exercise_date = Column(DateTime)
    expiration_date = Column(DateTime)
    transaction_acquired_disposed_code = Column(String)
    direct_or_indirect_ownership = Column(String)
    nature_of_ownership = Column(String)
    type = Column(String)
    __tablename__ = "transactions_and_holdings"
