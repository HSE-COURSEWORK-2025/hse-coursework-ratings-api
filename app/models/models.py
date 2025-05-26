from pydantic import BaseModel
from enum import Enum
from typing import List


class DataItem(BaseModel):
    dataType: str | None = ""
    value: str | None = ""


class DataType(str, Enum):
    # Исходные типы
    SLEEP_SESSION_DATA                    = "SleepSessionData"
    BLOOD_OXYGEN_DATA                     = "BloodOxygenData"
    HEART_RATE_RECORD                     = "HeartRateRecord"
    ACTIVE_CALORIES_BURNED_RECORD         = "ActiveCaloriesBurnedRecord"
    BASAL_METABOLIC_RATE_RECORD           = "BasalMetabolicRateRecord"
    BLOOD_PRESSURE_RECORD                 = "BloodPressureRecord"
    BODY_FAT_RECORD                       = "BodyFatRecord"
    BODY_TEMPERATURE_RECORD               = "BodyTemperatureRecord"
    BONE_MASS_RECORD                      = "BoneMassRecord"
    DISTANCE_RECORD                       = "DistanceRecord"
    EXERCISE_SESSION_RECORD               = "ExerciseSessionRecord"
    HYDRATION_RECORD                      = "HydrationRecord"
    SPEED_RECORD                          = "SpeedRecord"
    STEPS_RECORD                          = "StepsRecord"
    TOTAL_CALORIES_BURNED_RECORD          = "TotalCaloriesBurnedRecord"
    WEIGHT_RECORD                         = "WeightRecord"
    BASAL_BODY_TEMPERATURE_RECORD         = "BasalBodyTemperatureRecord"
    FLOORS_CLIMBED_RECORD                 = "FloorsClimbedRecord"
    INTERMENSTRUAL_BLEEDING_RECORD        = "IntermenstrualBleedingRecord"
    LEAN_BODY_MASS_RECORD                 = "LeanBodyMassRecord"
    MENSTRUATION_FLOW_RECORD              = "MenstruationFlowRecord"
    NUTRITION_RECORD                      = "NutritionRecord"
    POWER_RECORD                          = "PowerRecord"
    RESPIRATORY_RATE_RECORD               = "RespiratoryRateRecord"
    RESTING_HEART_RATE_RECORD             = "RestingHeartRateRecord"
    SKIN_TEMPERATURE_RECORD               = "SkinTemperatureRecord"

    # Дополнительно добавленные типы
    HEIGHT_RECORD                         = "HeightRecord"
    ACTIVITY_SEGMENT_RECORD               = "ActivitySegmentRecord"
    CYCLING_PEDALING_CADENCE_RECORD       = "CyclingPedalingCadenceRecord"
    CYCLING_PEDALING_CUMULATIVE_RECORD    = "CyclingPedalingCumulativeRecord"
    HEART_MINUTES_RECORD                  = "HeartMinutesRecord"
    ACTIVE_MINUTES_RECORD                 = "ActiveMinutesRecord"
    STEP_CADENCE_RECORD                   = "StepCadenceRecord"


class TokenData(BaseModel):
    google_sub: str
    email: str
    name: str
    picture: str


class KafkaRawDataMsg(BaseModel):
    rawData: dict | List[dict]
    dataType: str
    userData: TokenData


class DataRecord(BaseModel):
    X: float
    Y: float

class DataWithOutliers(BaseModel):
    data: List[DataRecord]
    outliersX: List[float]


class Prediction(BaseModel):
    result: str
    diagnosisName: str


class ProgressPayload(BaseModel):
    progress: str
    email: str
