from sqlalchemy import create_engine

DB_USER = "postgres"
DB_PASSWORD = "kasmai"   # pakeisk į savo tikrą slaptažodį
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "forestdb"

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
