from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://alexuknow:ethan333@127.0.0.1/companies"
SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://alexuknow:ethan333@postgres_database/companies"  # docker version

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
