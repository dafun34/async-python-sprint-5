import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from src.models.base import Base


class File(Base):
    __tablename__ = "files"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(String, ForeignKey("users.email"), nullable=False)
    name = Column(String)
    created_ad = Column(DateTime, default=datetime.utcnow)
    path = Column(String(length=300), unique=True)
    size = Column(Integer)
    is_downloadable = Column(Boolean, default=False)
