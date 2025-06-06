import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    Enum as SQLEnum,
    ForeignKey,
    Float
)
from sqlalchemy.sql import expression
from sqlalchemy.orm import declarative_base, relationship
from app.models.models import DataType


Base = declarative_base()


class RatingRecords(Base):
    __tablename__ = "rating_records"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    value = Column(Float, nullable=False)
