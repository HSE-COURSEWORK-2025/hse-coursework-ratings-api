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

Base = declarative_base()


class DataType(enum.Enum):
    SLEEP_SESSION_DATA = "SleepSessionData"
    BLOOD_OXYGEN_DATA = "BloodOxygenData"
    HEART_RATE_RECORD = "HeartRateRecord"
    ACTIVE_CALORIES_BURNED_RECORD = "ActiveCaloriesBurnedRecord"
    BASAL_METABOLIC_RATE_RECORD = "BasalMetabolicRateRecord"
    BLOOD_PRESSURE_RECORD = "BloodPressureRecord"
    BODY_FAT_RECORD = "BodyFatRecord"
    BODY_TEMPERATURE_RECORD = "BodyTemperatureRecord"
    BONE_MASS_RECORD = "BoneMassRecord"
    DISTANCE_RECORD = "DistanceRecord"
    EXERCISE_SESSION_RECORD = "ExerciseSessionRecord"
    HYDRATION_RECORD = "HydrationRecord"
    SPEED_RECORD = "SpeedRecord"
    STEPS_RECORD = "StepsRecord"
    TOTAL_CALORIES_BURNED_RECORD = "TotalCaloriesBurnedRecord"
    WEIGHT_RECORD = "WeightRecord"
    BASAL_BODY_TEMPERATURE_RECORD = "BasalBodyTemperatureRecord"
    FLOORS_CLIMBED_RECORD = "FloorsClimbedRecord"
    INTERMENSTRUAL_BLEEDING_RECORD = "IntermenstrualBleedingRecord"
    LEAN_BODY_MASS_RECORD = "LeanBodyMassRecord"
    MENSTRUATION_FLOW_RECORD = "MenstruationFlowRecord"
    NUTRITION_RECORD = "NutritionRecord"
    POWER_RECORD = "PowerRecord"
    RESPIRATORY_RATE_RECORD = "RespiratoryRateRecord"
    RESTING_HEART_RATE_RECORD = "RestingHeartRateRecord"
    SKIN_TEMPERATURE_RECORD = "SkinTemperatureRecord"


class RawRecords(Base):
    __tablename__ = "raw_records"

    id = Column(Integer, primary_key=True, index=True)
    data_type = Column(
        SQLEnum(DataType, name="data_type_enum"),
        nullable=False,
        index=True,
    )
    email = Column(String, nullable=False, index=True)
    time = Column(DateTime(timezone=True), nullable=False, index=True)
    value = Column(Text, nullable=False)

    def __repr__(self):
        return (
            f"<SampleRecord(id={self.id}, data_type={self.data_type.name}, "
            f"email={self.email}, time={self.time}, value={self.value})>"
        )
