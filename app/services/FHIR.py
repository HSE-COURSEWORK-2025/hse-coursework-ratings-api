from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from fhir.resources.bundle import Bundle
from fhir.resources.observation import Observation
from app.services.auth import get_current_user
from app.services.db.db_session import get_session
from app.services.db.schemas import RawRecords
from app.models.models import DataType


class FHIRTransformer:
    """
    Собирает FHIR Bundle и Observation полностью на dict’ах,
    без сторонних библиотек, с учётом соответствия DataType → коды FHIR.
    """

    # Пример соответствия: DataType → (system, code, display, unit, unitSystem, unitCode)
    _CODE_MAP: Dict[DataType, Dict[str, str]] = {
        # 1. Sleep Session Stages (e.g., N1, N2, REM) – суммарная длительность стадий сна
        DataType.SLEEP_SESSION_DATA: {
            "system": "http://loinc.org",
            "code": "94602-0",
            "display": "Sleep stage, total duration",
            "unit": "min",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "min",
        },
        DataType.SLEEP_SESSION_STAGES_DATA: {
            "system": "http://loinc.org",
            "code": "94602-0",
            "display": "Sleep stage, total duration",
            "unit": "min",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "min",
        },
        # 2. Sleep Session Total Time – общее время сна
        DataType.SLEEP_SESSION_TIME_DATA: {
            "system": "http://loinc.org",
            "code": "75989-8",
            "display": "Sleep duration",
            "unit": "min",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "min",
        },
        # 3. Blood Oxygen (SpO2)
        DataType.BLOOD_OXYGEN_DATA: {
            "system": "http://loinc.org",
            "code": "59408-5",
            "display": "Oxygen saturation in Arterial blood by Pulse oximetry",
            "unit": "%",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "%",
        },
        # 4. Heart Rate (текущий, во время активности и т.д.)
        DataType.HEART_RATE_RECORD: {
            "system": "http://loinc.org",
            "code": "8867-4",
            "display": "Heart rate",
            "unit": "beats/minute",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "/min",
        },
        # 5. Active Calories Burned (энергия, израсходованная во время активности)
        DataType.ACTIVE_CALORIES_BURNED_RECORD: {
            "system": "http://loinc.org",
            "code": "55422-1",
            "display": "Active energy expenditure",
            "unit": "kcal",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "kcal",
        },
        # 6. Basal Metabolic Rate (BMR)
        DataType.BASAL_METABOLIC_RATE_RECORD: {
            "system": "http://loinc.org",
            "code": "41987-7",
            "display": "Basal metabolic rate",
            "unit": "kcal/day",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "kcal/d",
        },
        # 7. Blood Pressure (систолическое, единица – mmHg; здесь взят систолический показатель)
        DataType.BLOOD_PRESSURE_RECORD: {
            "system": "http://loinc.org",
            "code": "8480-6",
            "display": "Systolic blood pressure",
            "unit": "mm[Hg]",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "mm[Hg]",
        },
        # 8. Body Fat Percentage
        DataType.BODY_FAT_RECORD: {
            "system": "http://loinc.org",
            "code": "91511-1",
            "display": "Body fat [Percent]",
            "unit": "%",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "%",
        },
        # 9. Body Temperature (температура тела)
        DataType.BODY_TEMPERATURE_RECORD: {
            "system": "http://loinc.org",
            "code": "8310-5",
            "display": "Body temperature",
            "unit": "Cel",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "Cel",
        },
        # 10. Bone Mass (масса костей)
        DataType.BONE_MASS_RECORD: {
            "system": "http://loinc.org",
            "code": "39156-5",
            "display": "Bone mass",
            "unit": "kg",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "kg",
        },
        # 11. Distance Traveled (пройденное расстояние)
        DataType.DISTANCE_RECORD: {
            "system": "http://loinc.org",
            "code": "41957-6",
            "display": "Distance traveled",
            "unit": "km",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "km",
        },
        # 12. Exercise Session Duration (длительность тренировки)
        DataType.EXERCISE_SESSION_RECORD: {
            "system": "http://loinc.org",
            "code": "55423-9",
            "display": "Exercise duration",
            "unit": "min",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "min",
        },
        # 13. Hydration (объем выпитой жидкости)
        DataType.HYDRATION_RECORD: {
            "system": "http://loinc.org",
            "code": "75323-6",
            "display": "Fluid intake",
            "unit": "mL",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "mL",
        },
        # 14. Speed (скорость передвижения)
        DataType.SPEED_RECORD: {
            "system": "http://loinc.org",
            "code": "41985-1",
            "display": "Speed",
            "unit": "m/s",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "m/s",
        },
        # 15. Steps Count (количество шагов)
        DataType.STEPS_RECORD: {
            "system": "http://loinc.org",
            "code": "41950-5",
            "display": "Number of steps in 24 hour Measured",
            "unit": "count",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "{count}",
        },
        # 16. Total Calories Burned (общий расход калорий)
        DataType.TOTAL_CALORIES_BURNED_RECORD: {
            "system": "http://loinc.org",
            "code": "55423-9",
            "display": "Total energy expenditure",
            "unit": "kcal",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "kcal",
        },
        # 17. Weight (вес тела)
        DataType.WEIGHT_RECORD: {
            "system": "http://loinc.org",
            "code": "29463-7",
            "display": "Body Weight",
            "unit": "kg",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "kg",
        },
        # 18. Basal Body Temperature (базальная температура)
        DataType.BASAL_BODY_TEMPERATURE_RECORD: {
            "system": "http://loinc.org",
            "code": "8331-1",
            "display": "Basal body temperature",
            "unit": "Cel",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "Cel",
        },
        # 19. Floors Climbed (этажи, которые подняты)
        DataType.FLOORS_CLIMBED_RECORD: {
            "system": "http://loinc.org",
            "code": "8302-2",
            "display": "Number of floors climbed",
            "unit": "count",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "{count}",
        },
        # 20. Intermenstrual Bleeding (промежуточное маточное кровотечение)
        DataType.INTERMENSTRUAL_BLEEDING_RECORD: {
            "system": "http://snomed.info/sct",
            "code": "28447008",
            "display": "Intermenstrual bleeding",
            "unit": "",
            "unitSystem": "",
            "unitCode": "",
        },
        # 21. Lean Body Mass (безжировая масса тела)
        DataType.LEAN_BODY_MASS_RECORD: {
            "system": "http://loinc.org",
            "code": "75727-7",
            "display": "Lean body mass",
            "unit": "kg",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "kg",
        },
        # 22. Menstruation Flow (объем менструального кровотечения)
        DataType.MENSTRUATION_FLOW_RECORD: {
            "system": "http://loinc.org",
            "code": "68232-0",
            "display": "Menstrual flow volume",
            "unit": "mL",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "mL",
        },
        # 23. Nutrition (питание: калории, белки, жиры и т.д.)
        DataType.NUTRITION_RECORD: {
            "system": "http://loinc.org",
            "code": "72166-2",
            "display": "Nutritional intake",
            "unit": "kcal",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "kcal",
        },
        # 24. Power (мощность во время тренировки, например велоэргометр)
        DataType.POWER_RECORD: {
            "system": "http://loinc.org",
            "code": "41986-9",
            "display": "Power",
            "unit": "W",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "W",
        },
        # 25. Respiratory Rate (частота дыхания)
        DataType.RESPIRATORY_RATE_RECORD: {
            "system": "http://loinc.org",
            "code": "9279-1",
            "display": "Respiratory rate",
            "unit": "breaths/minute",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "/min",
        },
        # 26. Resting Heart Rate (пульс в покое)
        DataType.RESTING_HEART_RATE_RECORD: {
            "system": "http://loinc.org",
            "code": "9269-2",
            "display": "Resting heart rate",
            "unit": "beats/minute",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "/min",
        },
        # 27. Skin Temperature (температура кожи)
        DataType.SKIN_TEMPERATURE_RECORD: {
            "system": "http://loinc.org",
            "code": "8310-5",
            "display": "Skin temperature",  # Используется тот же код, что и для общей температуры тела
            "unit": "Cel",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "Cel",
        },
        # 28. Height (рост)
        DataType.HEIGHT_RECORD: {
            "system": "http://loinc.org",
            "code": "8302-2",
            "display": "Body height",
            "unit": "cm",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "cm",
        },
        # 29. Activity Segment (сегмент активности, например прогулка/бег)
        DataType.ACTIVITY_SEGMENT_RECORD: {
            "system": "http://loinc.org",
            "code": "55423-9",
            "display": "Exercise duration",  # Используем тот же код для длительности сегмента
            "unit": "min",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "min",
        },
        # 30. Cycling Pedaling Cadence (каденс при езде на велосипеде)
        DataType.CYCLING_PEDALING_CADENCE_RECORD: {
            "system": "http://loinc.org",
            "code": "8312-1",
            "display": "Pedal cadence",
            "unit": "rpm",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "rpm",
        },
        # 31. Cycling Pedaling Cumulative (накопительная каденция, общее количество оборотов)
        DataType.CYCLING_PEDALING_CUMULATIVE_RECORD: {
            "system": "http://loinc.org",
            "code": "33884-6",
            "display": "Pedal strokes",
            "unit": "count",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "{count}",
        },
        # 32. Heart Minutes (минуты в целевой зоне пульса)
        DataType.HEART_MINUTES_RECORD: {
            "system": "http://loinc.org",
            "code": "55425-4",
            "display": "Minutes of elevated heart rate",
            "unit": "min",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "min",
        },
        # 33. Active Minutes (минуты активности)
        DataType.ACTIVE_MINUTES_RECORD: {
            "system": "http://loinc.org",
            "code": "55424-7",
            "display": "Activity duration",
            "unit": "min",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "min",
        },
        # 34. Step Cadence (каденс при ходьбе / беге: шаги в минуту)
        DataType.STEP_CADENCE_RECORD: {
            "system": "http://loinc.org",
            "code": "9287-4",
            "display": "Step rate",
            "unit": "steps/minute",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "/min",
        },
        DataType.SLEEP_SESSION_TIME_DATA: {
            "system": "http://loinc.org",
            "code": "93832-4",
            "display": "Sleep duration",
            "unit": "min",
            "unitSystem": "http://unitsofmeasure.org",
            "unitCode": "min"
        }
    }

    @classmethod
    def build_observation_dict(cls, rec: RawRecords) -> Optional[Dict[str, Any]]:
        """
        Собирает словарь Observation для одной записи.
        Если для data_type нет кода в _CODE_MAP, возвращает observation
        с code.text без valueQuantity.
        """
        dt = DataType(rec.data_type)
        base = {
            "resourceType": "Observation",
            "id": str(rec.id),
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                        }
                    ]
                }
            ],
            "code": {},
            "subject": {"identifier": {"value": rec.email}},
            "effectiveDateTime": rec.time.isoformat(),
        }

        # Если есть детальное соответствие — строим valueQuantity
        if dt in cls._CODE_MAP:
            cmap = cls._CODE_MAP[dt]
            base["code"] = {
                "coding": [
                    {
                        "system": cmap["system"],
                        "code": cmap["code"],
                        "display": cmap["display"],
                    }
                ],
                "text": cmap["display"],
            }
            # пытаемся привести value к числу
            try:
                val = float(rec.value)
            except Exception:
                val = None

            if val is not None:
                base["valueQuantity"] = {
                    "value": val,
                    "unit": cmap["unit"],
                    "system": cmap["unitSystem"],
                    "code": cmap["unitCode"],
                }
            else:
                # fallback на строковое значение
                base["valueString"] = rec.value
        else:
            # если нет специфики — просто текстовый код
            base["code"] = {"text": rec.data_type}
            base["valueString"] = rec.value

        return base

    @classmethod
    def build_bundle_dict(cls, records: List[RawRecords]) -> Dict[str, Any]:
        entries = []
        for rec in records:
            obs = cls.build_observation_dict(rec)
            if not obs:
                continue
            entries.append({"fullUrl": f"urn:uuid:{rec.id}", "resource": obs})

        return {"resourceType": "Bundle", "type": "collection", "entry": entries}
