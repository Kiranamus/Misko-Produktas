from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

from .db_config import DATABASE_URL as DEFAULT_DATABASE_URL

DATABASE_URL = os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL

if not DATABASE_URL:
    raise RuntimeError(
        "Database configuration is missing. Set DATABASE_URL in the environment "
        "or define it in app/db_config.py."
    )

engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    verification_token_expires = Column(DateTime, nullable=True)
    reset_token = Column(String, nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PurchasedPlan(Base):
    __tablename__ = "purchased_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(String, nullable=False)
    transaction_id = Column(String, nullable=True)  # Added this field
    purchased_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

User.purchased_plans = relationship("PurchasedPlan", back_populates="user")
PurchasedPlan.user = relationship("User", back_populates="purchased_plans")

def ensure_user_columns():
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    column_statements = {
        "email_verified": "ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE",
        "verification_token": "ALTER TABLE users ADD COLUMN verification_token VARCHAR",
        "verification_token_expires": "ALTER TABLE users ADD COLUMN verification_token_expires TIMESTAMP",
    }

    with engine.begin() as connection:
        for column_name, statement in column_statements.items():
            if column_name not in existing_columns:
                connection.execute(text(statement))


def init_db():
    Base.metadata.create_all(bind=engine)
    ensure_user_columns()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
