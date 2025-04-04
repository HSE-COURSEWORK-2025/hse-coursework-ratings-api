from datetime import datetime, timedelta
import random
from typing import List
import pandas as pd
from typing import Dict, Any
from app.models.getData import DataElementSchema, DataType


def generate_random_data(
    data_type: DataType, outlier_prob: float = 0.05
) -> List[DataElementSchema]:
    base_time = datetime.now()
    data = []
    n_points = random.randint(500, 2500)

    # Базовые диапазоны и настройки выбросов
    ranges = {
        DataType.PULSE: {
            "normal": (60, 100),
            "outlier": (lambda: random.choice([(30, 59), (101, 140)])),
        },
        DataType.BLOOD_OXYGEN: {"normal": (90, 100), "outlier": (lambda: (70, 89))},
        DataType.STRESS_LVL: {
            "normal": (0, 100),
            "outlier": (lambda: random.choice([(-20, -1), (101, 120)])),
        },
        DataType.RESPIRATORY_RATE: {
            "normal": (12, 20),
            "outlier": (lambda: random.choice([(6, 11), (21, 30)])),
        },
        DataType.SLEEP_TIME: {
            "normal": (0, 24),
            "outlier": (lambda: random.choice([(-5, -1), (25, 30)])),
        },
    }

    config = ranges[data_type]

    for i in range(n_points):
        x_value = (base_time + timedelta(hours=i)).timestamp()

        # Генерируем выбросы с заданной вероятностью
        if random.random() < outlier_prob:
            min_val, max_val = config["outlier"]()
        else:
            min_val, max_val = config["normal"]

        y_value = random.randint(min_val, max_val)
        data.append(DataElementSchema(X=x_value, Y=y_value))

    return sorted(data, key=lambda item: item.X)


def analyze_and_return_json(raw_data: List[DataElementSchema]) -> Dict[str, Any]:
    # Создаем DataFrame с целочисленными X
    df = pd.DataFrame([{"x": item.X, "y": item.Y} for item in raw_data])

    # Ищем выбросы по значению Y
    q1 = df["y"].quantile(0.25)
    q3 = df["y"].quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    outliers = df[(df["y"] < lower_bound) | (df["y"] > upper_bound)]

    return {
        "data": [{"X": row.x, "Y": row.y} for row in df.itertuples()],
        "outliersX": outliers["x"].tolist(),
    }
