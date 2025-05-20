import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    Enum as SQLEnum,
)
from sqlalchemy.sql import expression
from sqlalchemy.orm import declarative_base
from app.models.models import DataType


Base = declarative_base()


class RawRecords(Base):
    __tablename__ = "raw_records"

    id = Column(Integer, primary_key=True, index=True)
    data_type = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    time = Column(DateTime(timezone=True), nullable=False, index=True)
    value = Column(Text, nullable=False)

    def __repr__(self):
        return (
            f"<SampleRecord(id={self.id}, data_type={self.data_type.name}, "
            f"email={self.email}, time={self.time}, value={self.value})>"
        )
