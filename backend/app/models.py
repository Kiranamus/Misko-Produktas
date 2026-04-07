from sqlalchemy import Column, Integer, String, DateTime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password = Column(String)

    reset_token = Column(String, nullable=True)
    reset_token_expire = Column(DateTime, nullable=True)
