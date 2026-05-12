from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    create_engine,
    inspect,
    text,
)
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
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
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
    transaction_id = Column(String, nullable=True)
    purchased_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

User.purchased_plans = relationship("PurchasedPlan", back_populates="user")
PurchasedPlan.user = relationship("User", back_populates="purchased_plans")

def ensure_user_columns():
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = [column["name"] for column in inspector.get_columns("users")]
    existing_column_set = set(existing_columns)
    desired_prefix = ["id", "first_name", "last_name", "username", "email"]

    with engine.begin() as connection:
        if "full_name" in existing_column_set or existing_columns[:5] != desired_prefix:
            rebuild_users_table(connection, existing_column_set)
            return

        column_statements = {
            "email_verified": "ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE",
            "verification_token": "ALTER TABLE users ADD COLUMN verification_token VARCHAR",
            "verification_token_expires": "ALTER TABLE users ADD COLUMN verification_token_expires TIMESTAMP",
            "first_name": "ALTER TABLE users ADD COLUMN first_name VARCHAR",
            "last_name": "ALTER TABLE users ADD COLUMN last_name VARCHAR",
        }

        for column_name, statement in column_statements.items():
            if column_name not in existing_column_set:
                connection.execute(text(statement))


def rebuild_users_table(connection, existing_columns: set[str]) -> None:
    user_foreign_keys = get_user_foreign_keys(connection)
    first_name_value = select_existing_or_default(existing_columns, "first_name", "NULL")
    last_name_value = select_existing_or_default(existing_columns, "last_name", "NULL")
    email_verified_value = select_existing_or_default(existing_columns, "email_verified", "FALSE")
    is_active_value = select_existing_or_default(existing_columns, "is_active", "TRUE")
    verification_token_value = select_existing_or_default(existing_columns, "verification_token", "NULL")
    verification_token_expires_value = select_existing_or_default(
        existing_columns,
        "verification_token_expires",
        "NULL",
    )
    reset_token_value = select_existing_or_default(existing_columns, "reset_token", "NULL")
    reset_token_expires_value = select_existing_or_default(
        existing_columns,
        "reset_token_expires",
        "NULL",
    )
    created_at_value = select_existing_or_default(existing_columns, "created_at", "CURRENT_TIMESTAMP")

    if "full_name" in existing_columns:
        first_name_value = (
            "COALESCE("
            f"NULLIF({first_name_value}, ''), "
            "NULLIF(split_part(full_name, ' ', 1), '')"
            ")"
        )
        last_name_value = (
            "COALESCE("
            f"NULLIF({last_name_value}, ''), "
            "NULLIF(trim(substring("
            "full_name from char_length(split_part(full_name, ' ', 1)) + 1"
            ")), '')"
            ")"
        )

    drop_user_foreign_keys(connection, user_foreign_keys)

    connection.execute(text("DROP TABLE IF EXISTS users_reordered"))
    connection.execute(text("ALTER SEQUENCE IF EXISTS users_id_seq OWNED BY NONE"))
    connection.execute(text("ALTER TABLE users RENAME TO users_reordered"))
    connection.execute(
        text(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                first_name VARCHAR,
                last_name VARCHAR,
                username VARCHAR NOT NULL,
                email VARCHAR NOT NULL,
                hashed_password VARCHAR NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                email_verified BOOLEAN DEFAULT FALSE,
                verification_token VARCHAR,
                verification_token_expires TIMESTAMP,
                reset_token VARCHAR,
                reset_token_expires TIMESTAMP,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    connection.execute(text("CREATE SEQUENCE IF NOT EXISTS users_id_seq"))
    connection.execute(text("ALTER TABLE users ALTER COLUMN id SET DEFAULT nextval('users_id_seq')"))
    connection.execute(text("ALTER SEQUENCE users_id_seq OWNED BY users.id"))
    connection.execute(
        text(
            f"""
            INSERT INTO users (
                id,
                first_name,
                last_name,
                username,
                email,
                hashed_password,
                is_active,
                email_verified,
                verification_token,
                verification_token_expires,
                reset_token,
                reset_token_expires,
                created_at
            )
            SELECT
                id,
                {first_name_value},
                {last_name_value},
                username,
                email,
                hashed_password,
                COALESCE({is_active_value}, TRUE),
                COALESCE({email_verified_value}, FALSE),
                {verification_token_value},
                {verification_token_expires_value},
                {reset_token_value},
                {reset_token_expires_value},
                {created_at_value}
            FROM users_reordered
            """
        )
    )
    connection.execute(
        text(
            """
            SELECT setval(
                'users_id_seq',
                GREATEST(COALESCE((SELECT MAX(id) FROM users), 0), 1),
                TRUE
            )
            """
        )
    )
    connection.execute(text("DROP TABLE users_reordered"))
    connection.execute(text("CREATE UNIQUE INDEX ix_users_username ON users(username)"))
    connection.execute(text("CREATE UNIQUE INDEX ix_users_email ON users(email)"))
    connection.execute(text("CREATE INDEX ix_users_id ON users(id)"))

    restore_user_foreign_keys(connection, user_foreign_keys)


def select_existing_or_default(
    existing_columns: set[str],
    column_name: str,
    default_value: str,
) -> str:
    return column_name if column_name in existing_columns else default_value


def get_user_foreign_keys(connection) -> list[dict]:
    return list(
        connection.execute(
            text(
                """
                SELECT
                    format('%I.%I', table_namespace.nspname, table_class.relname) AS table_name,
                    quote_ident(constraint_info.conname) AS constraint_name,
                    pg_get_constraintdef(constraint_info.oid) AS constraint_definition
                FROM pg_constraint constraint_info
                JOIN pg_class table_class
                    ON table_class.oid = constraint_info.conrelid
                JOIN pg_namespace table_namespace
                    ON table_namespace.oid = table_class.relnamespace
                WHERE constraint_info.confrelid = 'users'::regclass
                    AND constraint_info.contype = 'f'
                """
            )
        )
        .mappings()
        .all()
    )


def drop_user_foreign_keys(connection, foreign_keys: list[dict]) -> None:
    for foreign_key in foreign_keys:
        connection.execute(
            text(
                f"ALTER TABLE {foreign_key['table_name']} "
                f"DROP CONSTRAINT {foreign_key['constraint_name']}"
            )
        )


def restore_user_foreign_keys(connection, foreign_keys: list[dict]) -> None:
    for foreign_key in foreign_keys:
        connection.execute(
            text(
                f"ALTER TABLE {foreign_key['table_name']} "
                f"ADD CONSTRAINT {foreign_key['constraint_name']} "
                f"{foreign_key['constraint_definition']}"
            )
        )


def init_db():
    Base.metadata.create_all(bind=engine)
    ensure_user_columns()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
