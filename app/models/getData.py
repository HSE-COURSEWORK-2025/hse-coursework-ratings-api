from typing import List
from pydantic import BaseModel
from enum import Enum


class DataType(Enum):
    PULSE: str = "PULSE"
    BLOOD_OXYGEN: str = "BLOOD_OXYGEN"
    STRESS_LVL: str = "STRESS_LVL"
    RESPIRATORY_RATE: str = "RESPIRATORY_RATE"
    SLEEP_TIME: str = "SLEEP_TIME"


class DataElementSchema(BaseModel):
    X: float
    Y: float


class AnalyzedDataSchema(BaseModel):
    data: List[DataElementSchema]
    outliersX: List[float]
