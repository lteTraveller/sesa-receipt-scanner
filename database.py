import os
from datetime import datetime
from typing import Any, Dict, List
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

# Neon connection string format: postgresql://user:password@ep-xyz.region.neon.tech/neondb?sslmode=require
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is missing. Check your .env file.")

# Fix schema prefix if copied as 'postgres://' from some dashboards
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ScannedDocument(Base):
    __tablename__ = "scanned_documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    merchant_name = Column(String(255), nullable=True)
    document_type = Column(String(100), default="Receipt")
    document_date = Column(String(50), nullable=True)
    total_amount = Column(Float, nullable=True)
    tax_amount = Column(Float, nullable=True)
    currency = Column(String(10), default="USD")
    payment_method = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True)
    raw_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Create tables if they don't already exist."""
    Base.metadata.create_all(bind=engine)


def insert_scanned_record(data: Dict[str, Any]) -> int:
    """Insert an extracted document record into Neon DB."""
    session = SessionLocal()
    try:
        record = ScannedDocument(
            merchant_name=data.get("merchant_name"),
            document_type=data.get("document_type", "Receipt"),
            document_date=data.get("document_date"),
            total_amount=data.get("total_amount"),
            tax_amount=data.get("tax_amount"),
            currency=data.get("currency", "USD"),
            payment_method=data.get("payment_method"),
            category=data.get("category"),
            raw_summary=data.get("raw_summary"),
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record.id
    except Exception as exc:
        session.rollback()
        raise exc
    finally:
        session.close()


def fetch_all_records() -> pd.DataFrame:
    """Fetch existing database records to display live in Streamlit."""
    session = SessionLocal()
    try:
        query = session.query(ScannedDocument).order_by(ScannedDocument.created_at.desc())
        df = pd.read_sql(query.statement, session.bind)
        return df
    finally:
        session.close()