
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
)
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class RatingRecords(Base):
    __tablename__ = "rating_records"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    value = Column(Float, nullable=False)
