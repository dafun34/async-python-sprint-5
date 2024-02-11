from sqlalchemy import Column, String

from src.models.base import Base


class User(Base):
    __tablename__ = "users"
    email = Column(String, unique=True, nullable=False, primary_key=True)
    password = Column(String(255), nullable=False)
