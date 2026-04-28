from __future__ import annotations

from collections import Counter
from itertools import combinations
from pathlib import Path
import math

import numpy as np
import pandas as pd


OUTPUT_DIR = Path(__file__).resolve().parent
SCENARIO_YEAR = 2025
RNG_SEED = 20250427

STORE_ID = "S000001"
STORE_NAME = "LUKE Drug & Beauty Omiya"
PREFECTURE = "Saitama"
CITY = "Saitama"
POSTCODE = "3300854"
LATITUDE = 35.9067
LONGITUDE = 139.6288

SUGI_STORE_COUNT = 31
CATCHMENT_POPULATION = 32000
VISITS_PER_PERSON_PER_YEAR = 5.8
BASE_CAPTURE_RATE = 0.27
COMPETITION_PENALTY_PER_STORE = 0.002
CAPTURE_RATE = max(0.12, BASE_CAPTURE_RATE - SUGI_STORE_COUNT * COMPETITION_PENALTY_PER_STORE)

ANNUAL_TRANSACTIONS_TARGET = int(
    round(CATCHMENT_POPULATION * VISITS_PER_PERSON_PER_YEAR * CAPTURE_RATE)
)
CUSTOMER_POOL_SIZE = max(5500, int(round(ANNUAL_TRANSACTIONS_TARGET / 5.0)))


CATEGORY_SPECS = [
    ("OTC_Medicine", "ColdFlu", 18, (680, 2480), 0.62, 1.35, 0, 0),
    ("OTC_Medicine", "Allergy", 10, (780, 2980), 0.63, 1.18, 0, 1),
    ("Skincare", "FacialCare", 16, (580, 2980), 0.58, 1.08, 0, 1),
    ("Cosmetics", "Makeup", 14, (680, 3680), 0.56, 0.92, 0, 1),
    ("Oral_Care", "Dental", 12, (220, 1280), 0.54, 1.04, 0, 0),
    ("Hair_Care", "Shampoo", 12, (420, 1680), 0.55, 1.00, 0, 0),
    ("Baby_Care", "Diaper", 10, (980, 3980), 0.65, 0.83, 0, 0),
    ("Supplements", "Vitamins", 14, (620, 2480), 0.60, 1.06, 0, 0),
    ("Daily_Necessities", "Household", 14, (180, 1480), 0.52, 1.22, 0, 0),
    ("Hygiene", "Sanitary", 12, (220, 1180), 0.53, 1.12, 0, 0),
    ("Beverage", "Drink", 10, (90, 320), 0.48, 1.18, 1, 1),
    ("Snack", "Food", 8, (110, 420), 0.50, 1.07, 1, 1),
]


NATIONAL_HOLIDAYS_2025 = {
    "2025-01-01": "New Year Day",
    "2025-01-13": "Coming of Age Day",
    "2025-02-11": "National Foundation Day",
    "2025-02-23": "Emperor Birthday",
    "2025-02-24": "Emperor Birthday Substitute",
    "2025-03-20": "Vernal Equinox Day",
    "2025-04-29": "Showa Day",
    "2025-05-03": "Constitution Memorial Day",
    "2025-05-04": "Greenery Day",
    "2025-05-05": "Children Day",
    "2025-05-06": "Children Day Substitute",
    "2025-07-21": "Marine Day",
    "2025-08-11": "Mountain Day",
    "2025-09-15": "Respect for the Aged Day",
    "2025-09-23": "Autumnal Equinox Day",
    "2025-10-13": "Sports Day",
    "2025-11-03": "Culture Day",
    "2025-11-23": "Labor Thanksgiving Day",
    "2025-11-24": "Labor Thanksgiving Substitute",
}


TEMP_NORMAL = {
    1: 5.4,
    2: 6.6,
    3: 10.1,
    4: 15.4,
    5: 20.1,
    6: 23.3,
    7: 27.2,
    8: 28.8,
    9: 25.0,
    10: 18.8,
    11: 12.9,
    12: 7.7,
}

RAIN_TOTAL_MM = {
    1: 35,
    2: 50,
    3: 117,
    4: 124,
    5: 137,
    6: 180,
    7: 154,
    8: 168,
    9: 210,
    10: 171,
    11: 92,
    12: 45,
}

RAIN_PROB = {
    1: 0.17,
    2: 0.20,
    3: 0.31,
    4: 0.34,
    5: 0.37,
    6: 0.45,
    7: 0.40,
    8: 0.41,
    9: 0.47,
    10: 0.41,
    11: 0.29,
    12: 0.19,
}


MONTH_DEMAND_FACTOR = {
    1: 1.08,
    2: 0.93,
    3: 1.05,
    4: 1.00,
    5: 1.04,
    6: 0.98,
    7: 1.02,
    8: 1.10,
    9: 0.97,
    10: 1.01,
    11: 1.03,
    12: 1.20,
}

WEEKDAY_DEMAND_FACTOR = {
    0: 0.93,
    1: 0.95,
    2: 1.00,
    3: 1.03,
    4: 1.09,
    5: 1.22,
    6: 1.18,
}


CUSTOMER_SEGMENTS = [
    {
        "name": "family",
        "weight": 0.34,
        "age_min": 28,
        "age_max": 52,
        "income_levels": ["middle", "upper_middle", "high"],
        "education_levels": ["college", "graduate"],
        "occupations": ["office", "service", "medical", "teacher"],
        "marital_weights": [0.18, 0.82],
        "household_range": (3, 5),
        "children_prob": 0.85,
        "activity_shape": 2.1,
        "activity_scale": 1.2,
    },
    {
        "name": "young_worker",
        "weight": 0.28,
        "age_min": 22,
        "age_max": 39,
        "income_levels": ["middle", "upper_middle"],
        "education_levels": ["college", "graduate"],
        "occupations": ["office", "engineer", "service", "sales"],
        "marital_weights": [0.57, 0.43],
        "household_range": (1, 3),
        "children_prob": 0.27,
        "activity_shape": 2.2,
        "activity_scale": 1.0,
    },
    {
        "name": "senior",
        "weight": 0.26,
        "age_min": 55,
        "age_max": 82,
        "income_levels": ["middle", "upper_middle"],
        "education_levels": ["high_school", "college"],
        "occupations": ["retired", "part_time", "self_employed"],
        "marital_weights": [0.26, 0.74],
        "household_range": (1, 3),
        "children_prob": 0.08,
        "activity_shape": 2.5,
        "activity_scale": 0.95,
    },
    {
        "name": "student",
        "weight": 0.12,
        "age_min": 18,
        "age_max": 27,
        "income_levels": ["low", "middle"],
        "education_levels": ["high_school", "college"],
        "occupations": ["student", "part_time"],
        "marital_weights": [0.94, 0.06],
        "household_range": (1, 2),
        "children_prob": 0.01,
        "activity_shape": 1.6,
        "activity_scale": 0.9,
    },
]


SEGMENT_CATEGORY_PREFS = {
    "family": ["Baby_Care", "Daily_Necessities", "Hygiene", "Beverage", "Snack"],
    "young_worker": ["Cosmetics", "Skincare", "Hair_Care", "Beverage", "Snack"],
    "senior": ["OTC_Medicine", "Supplements", "Oral_Care", "Daily_Necessities"],
    "student": ["Cosmetics", "Snack", "Beverage", "Hair_Care"],
}


PAYMENT_WEIGHTS_BY_SEGMENT = {
    "family": [0.18, 0.32, 0.39, 0.11],
    "young_worker": [0.09, 0.37, 0.26, 0.28],
    "senior": [0.35, 0.24, 0.35, 0.06],
    "student": [0.16, 0.21, 0.28, 0.35],
}

PAYMENT_METHODS = ["cash", "card", "waon", "mobile"]


HOUR_SLOTS = np.array([9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22])
HOUR_WEIGHTS = np.array([0.03, 0.05, 0.08, 0.09, 0.08, 0.07, 0.06, 0.08, 0.11, 0.12, 0.12, 0.07, 0.03, 0.01])
HOUR_WEIGHTS = HOUR_WEIGHTS / HOUR_WEIGHTS.sum()


def _dates_2025() -> pd.DatetimeIndex:
    return pd.date_range(f"{SCENARIO_YEAR}-01-01", f"{SCENARIO_YEAR}-12-31", freq="D")


def build_products(rng: np.random.Generator) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    product_index = 1

    brand_pool = [
        "LUKE Select",
        "SoraCare",
        "NeoWell",
        "AquaSkin",
        "LifeRoot",
        "MediTrust",
        "PureOne",
        "DailyFit",
    ]

    for cat1, cat2, count, price_range, cost_ratio, demand_weight, perishable, seasonal in CATEGORY_SPECS:
        for item_no in range(1, count + 1):
            product_id = f"P{product_index:06d}"

            if product_index == 1:
                rows.append(
                    {
                        "product_id": "P000001",
                        "product_name": "LUKE Cold Relief Tablets 24",
                        "brand": "LUKE Select",
                        "category_level1": "OTC_Medicine",
                        "category_level2": "ColdFlu",
                        "category_level3": "ColdFlu_Tablet",
                        "retail_price_jpy": 1480,
                        "cost_price_jpy": 890,
                        "unit_of_measure": "pack",
                        "package_size": "24tabs",
                        "weight_g": 54,
                        "supplier_id": "SUP001",
                        "shelf_life_days": 730,
                        "perishable_flag": 0,
                        "seasonal_flag": 1,
                        "organic_flag": 0,
                        "private_label_flag": 1,
                        "launch_date": "2024-09-01",
                        "_category_level1": "OTC_Medicine",
                        "_popularity_weight": 3.5,
                    }
                )
                product_index += 1
                continue

            retail_price = int(rng.integers(price_range[0] // 10, price_range[1] // 10 + 1) * 10)
            cost_price = int(max(40, round(retail_price * rng.uniform(cost_ratio - 0.08, cost_ratio + 0.04))))
            shelf_life_days = int(rng.integers(60, 365 if perishable else 1200))
            launch_offset = int(rng.integers(0, 1399))
            launch_date = pd.Timestamp("2022-01-01") + pd.Timedelta(days=launch_offset)

            rows.append(
                {
                    "product_id": product_id,
                    "product_name": f"{cat2} Item {item_no:02d}",
                    "brand": str(rng.choice(brand_pool)),
                    "category_level1": cat1,
                    "category_level2": cat2,
                    "category_level3": f"{cat2}_Type{int(rng.integers(1, 5))}",
                    "retail_price_jpy": retail_price,
                    "cost_price_jpy": cost_price,
                    "unit_of_measure": "piece" if cat1 not in {"Beverage", "Snack"} else "unit",
                    "package_size": f"{int(rng.integers(1, 7))}pack",
                    "weight_g": int(rng.integers(40, 1200)),
                    "supplier_id": f"SUP{int(rng.integers(1, 21)):03d}",
                    "shelf_life_days": shelf_life_days,
                    "perishable_flag": perishable,
                    "seasonal_flag": seasonal,
                    "organic_flag": int(rng.random() < 0.10),
                    "private_label_flag": int(rng.random() < 0.26),
                    "launch_date": launch_date.strftime("%Y-%m-%d"),
                    "_category_level1": cat1,
                    "_popularity_weight": float(max(0.05, rng.lognormal(mean=math.log(demand_weight), sigma=0.45))),
                }
            )
            product_index += 1

    return pd.DataFrame(rows)


def build_promotions() -> pd.DataFrame:
    rows = [
        ("PR0001", "New Year Essentials", "seasonal", "2025-01-01", "2025-01-05", 0.12, 1500, 1200, "Daily_Necessities"),
        ("PR0002", "Cold and Flu Focus", "health", "2025-01-10", "2025-02-15", 0.14, 1200, 1000, "OTC_Medicine"),
        ("PR0003", "Pollen Guard", "seasonal", "2025-02-20", "2025-04-10", 0.13, 1300, 1000, "OTC_Medicine"),
        ("PR0004", "Spring Skin Care", "beauty", "2025-03-15", "2025-04-30", 0.11, 1800, 1300, "Skincare"),
        ("PR0005", "Golden Week Family", "seasonal", "2025-04-26", "2025-05-06", 0.10, 2200, 1600, "Baby_Care"),
        ("PR0006", "UV Beauty Campaign", "beauty", "2025-05-20", "2025-07-15", 0.12, 2000, 1400, "Cosmetics"),
        ("PR0007", "Rainy Season Hygiene", "seasonal", "2025-06-10", "2025-07-05", 0.10, 1200, 800, "Hygiene"),
        ("PR0008", "Summer Hydration", "seasonal", "2025-07-20", "2025-08-31", 0.08, 1000, 600, "Beverage"),
        ("PR0009", "Obon Home Stockup", "seasonal", "2025-08-09", "2025-08-18", 0.09, 1800, 1200, "Daily_Necessities"),
        ("PR0010", "Autumn Immunity", "health", "2025-09-10", "2025-10-15", 0.11, 1800, 1200, "Supplements"),
        ("PR0011", "Sports Recovery", "lifestyle", "2025-10-01", "2025-10-31", 0.09, 1400, 900, "Supplements"),
        ("PR0012", "Dry Skin Rescue", "beauty", "2025-11-01", "2025-12-10", 0.13, 1800, 1300, "Skincare"),
        ("PR0013", "Year End Household", "seasonal", "2025-12-15", "2025-12-31", 0.12, 1800, 1400, "Daily_Necessities"),
        ("PR0014", "Holiday Snack Week", "seasonal", "2025-12-20", "2025-12-31", 0.08, 900, 500, "Snack"),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "promotion_id",
            "promotion_name",
            "promotion_type",
            "start_date",
            "end_date",
            "discount_rate",
            "min_purchase_amount_jpy",
            "max_discount_jpy",
            "target_category_level1",
        ],
    ).assign(target_store_id=STORE_ID)


def build_holiday() -> pd.DataFrame:
    dates = _dates_2025()
    holiday_map: dict[pd.Timestamp, dict[str, object]] = {}

    for date_str, name in NATIONAL_HOLIDAYS_2025.items():
        d = pd.Timestamp(date_str)
        weight = 1.25 if name in {"New Year Day", "Children Day"} else 1.0
        holiday_map[d] = {
            "date": d,
            "holiday_name": name,
            "holiday_type": "national",
            "is_long_weekend": 0,
            "holiday_weight": weight,
        }

    for d in dates:
        if d.weekday() >= 5 and d not in holiday_map:
            holiday_map[d] = {
                "date": d,
                "holiday_name": "Weekend",
                "holiday_type": "weekend",
                "is_long_weekend": 0,
                "holiday_weight": 0.55,
            }

    closed_dates = {d for d in dates if d.weekday() >= 5} | set(holiday_map.keys())

    for d, row in holiday_map.items():
        left = d
        right = d
        while (left - pd.Timedelta(days=1)) in closed_dates:
            left = left - pd.Timedelta(days=1)
        while (right + pd.Timedelta(days=1)) in closed_dates:
            right = right + pd.Timedelta(days=1)
        span_days = (right - left).days + 1
        row["is_long_weekend"] = 1 if span_days >= 3 else 0

    result = pd.DataFrame(list(holiday_map.values())).sort_values("date").reset_index(drop=True)
    result["date"] = result["date"].dt.strftime("%Y-%m-%d")
    return result


def build_weather(rng: np.random.Generator) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for d in _dates_2025():
        month = int(d.month)
        day_of_year = int(d.dayofyear)
        base_temp = TEMP_NORMAL[month]
        seasonal_wave = 2.4 * math.sin(2 * math.pi * (day_of_year - 80) / 365)
        temperature = base_temp + seasonal_wave + float(rng.normal(0, 2.0))

        rain_probability = RAIN_PROB[month]
        if float(rng.random()) < rain_probability:
            shape = 1.8
            scale = max(0.1, RAIN_TOTAL_MM[month] / (30.0 * rain_probability * shape))
            precipitation = float(rng.gamma(shape=shape, scale=scale))
        else:
            precipitation = 0.0

        humidity = float(np.clip(48 + precipitation * 1.4 + (28 - temperature) * 0.55 + rng.normal(0, 6), 35, 98))
        wind_speed = float(np.clip(rng.normal(2.6 + (1.2 if precipitation > 12 else 0.0), 0.9), 0.3, 11.0))
        pressure = float(np.clip(rng.normal(1015 - precipitation * 0.35, 4.2), 986, 1034))

        if precipitation >= 15:
            weather_condition = "heavy_rain"
        elif precipitation >= 3:
            weather_condition = "rainy"
        elif humidity >= 78:
            weather_condition = "cloudy"
        else:
            weather_condition = "sunny"

        rows.append(
            {
                "date": d.strftime("%Y-%m-%d"),
                "prefecture": PREFECTURE,
                "temperature_celsius": round(temperature, 2),
                "humidity_percent": round(humidity, 2),
                "precipitation_mm": round(precipitation, 2),
                "weather_condition": weather_condition,
                "wind_speed_mps": round(wind_speed, 2),
                "pressure_hpa": round(pressure, 1),
            }
        )

    return pd.DataFrame(rows)


def build_customers(rng: np.random.Generator, customer_count: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    segment_names = [seg["name"] for seg in CUSTOMER_SEGMENTS]
    segment_weights = np.array([seg["weight"] for seg in CUSTOMER_SEGMENTS], dtype=float)
    segment_weights = segment_weights / segment_weights.sum()
    segment_map = {seg["name"]: seg for seg in CUSTOMER_SEGMENTS}

    loyalty_tiers = ["silver", "gold", "platinum"]
    loyalty_weights = [0.54, 0.34, 0.12]

    for idx in range(1, customer_count + 1):
        customer_id = f"C{idx:06d}"
        segment_name = str(rng.choice(segment_names, p=segment_weights))
        seg = segment_map[segment_name]

        age = int(rng.integers(seg["age_min"], seg["age_max"] + 1))
        birth_year = SCENARIO_YEAR - age
        birth_month = int(rng.integers(1, 13))
        birth_day = int(rng.integers(1, 29))

        registration_offset = int(rng.integers(0, 2556))
        registration_date = pd.Timestamp("2019-01-01") + pd.Timedelta(days=registration_offset)

        has_children = int(float(rng.random()) < float(seg["children_prob"]))
        if has_children:
            children_age_range = str(rng.choice(["0-5", "6-12", "13-18"], p=[0.30, 0.45, 0.25]))
        else:
            children_age_range = "none"

        household_min, household_max = seg["household_range"]
        household_size = int(rng.integers(household_min, household_max + 1))

        marital_status = str(rng.choice(["single", "married"], p=seg["marital_weights"]))
        gender = str(rng.choice(["F", "M"], p=[0.54, 0.46]))

        income_level = str(rng.choice(seg["income_levels"]))
        education_level = str(rng.choice(seg["education_levels"]))
        occupation = str(rng.choice(seg["occupations"]))
        loyalty_tier = str(rng.choice(loyalty_tiers, p=loyalty_weights))

        activity_weight = float(rng.gamma(shape=seg["activity_shape"], scale=seg["activity_scale"]))
        if loyalty_tier == "gold":
            activity_weight *= 1.20
        elif loyalty_tier == "platinum":
            activity_weight *= 1.45

        if idx == 1:
            segment_name = "family"
            age = 36
            birth_year = SCENARIO_YEAR - age
            gender = "F"
            marital_status = "married"
            has_children = 1
            children_age_range = "6-12"
            household_size = 4
            income_level = "upper_middle"
            education_level = "college"
            occupation = "office"
            loyalty_tier = "platinum"
            activity_weight = max(activity_weight, 6.5)

        lifetime_base = 42000 + activity_weight * 62000 + (7000 if loyalty_tier == "gold" else 0) + (18000 if loyalty_tier == "platinum" else 0)
        total_lifetime_value = int(max(12000, round(lifetime_base + rng.normal(0, 12000))))

        rows.append(
            {
                "customer_id": customer_id,
                "registration_date": registration_date.strftime("%Y-%m-%d"),
                "birth_date": f"{birth_year:04d}-{birth_month:02d}-{birth_day:02d}",
                "age": age,
                "gender": gender,
                "income_level": income_level,
                "education_level": education_level,
                "occupation": occupation,
                "marital_status": marital_status,
                "household_size": household_size,
                "has_children": has_children,
                "children_age_range": children_age_range,
                "prefecture": PREFECTURE,
                "city": CITY,
                "postcode": f"33{int(rng.integers(1000, 9999)):04d}",
                "loyalty_tier": loyalty_tier,
                "total_lifetime_value_jpy": total_lifetime_value,
                "preferred_store_id": STORE_ID,
                "waon_card_number": f"WAON{idx:010d}",
                "customer_type": segment_name,
                "_segment": segment_name,
                "_activity_weight": activity_weight,
            }
        )

    return pd.DataFrame(rows)


def build_promotion_calendar(promotions_df: pd.DataFrame) -> dict[pd.Timestamp, list[dict[str, object]]]:
    calendar: dict[pd.Timestamp, list[dict[str, object]]] = {}
    for row in promotions_df.to_dict(orient="records"):
        start = pd.Timestamp(str(row["start_date"]))
        end = pd.Timestamp(str(row["end_date"]))
        payload = {
            "promotion_id": str(row["promotion_id"]),
            "target_category_level1": str(row["target_category_level1"]),
            "discount_rate": float(row["discount_rate"]),
            "min_purchase_amount_jpy": int(row["min_purchase_amount_jpy"]),
            "max_discount_jpy": int(row["max_discount_jpy"]),
        }
        for d in pd.date_range(start, end, freq="D"):
            calendar.setdefault(d, []).append(payload)
    return calendar


def build_daily_transaction_plan(
    weather_df: pd.DataFrame,
    holiday_df: pd.DataFrame,
    promotion_calendar: dict[pd.Timestamp, list[dict[str, object]]],
    rng: np.random.Generator,
) -> pd.DataFrame:
    dates = _dates_2025()
    weather_map = weather_df.copy()
    weather_map["date"] = pd.to_datetime(weather_map["date"])
    weather_map = weather_map.set_index("date")

    holiday_map = holiday_df.copy()
    holiday_map["date"] = pd.to_datetime(holiday_map["date"])
    holiday_dates = set(holiday_map["date"])
    long_weekend_dates = set(holiday_map.loc[holiday_map["is_long_weekend"] == 1, "date"])

    raw_scores: list[float] = []

    for d in dates:
        day = weather_map.loc[d]
        temperature = float(day["temperature_celsius"])
        precipitation = float(day["precipitation_mm"])

        weather_factor = 1.0
        if precipitation > 25:
            weather_factor *= 0.78
        elif precipitation > 10:
            weather_factor *= 0.87
        elif precipitation > 2:
            weather_factor *= 0.94

        if temperature > 33:
            weather_factor *= 0.90
        elif temperature < 0:
            weather_factor *= 0.91
        elif 18 <= temperature <= 27:
            weather_factor *= 1.03

        active_promos = promotion_calendar.get(d, [])
        promo_strength = sum(float(p["discount_rate"]) for p in active_promos)
        promo_factor = 1 + min(0.24, 0.04 * len(active_promos) + 0.18 * promo_strength)

        holiday_factor = 1.14 if d in holiday_dates else 1.0
        if d in long_weekend_dates and d not in holiday_dates:
            holiday_factor *= 1.05

        score = (
            WEEKDAY_DEMAND_FACTOR[d.weekday()]
            * MONTH_DEMAND_FACTOR[d.month]
            * weather_factor
            * promo_factor
            * holiday_factor
            * float(rng.lognormal(mean=0.0, sigma=0.08))
        )
        raw_scores.append(max(0.01, score))

    raw_array = np.array(raw_scores, dtype=float)
    expected = raw_array * (ANNUAL_TRANSACTIONS_TARGET / raw_array.sum())
    counts = np.floor(expected).astype(int)

    remaining = ANNUAL_TRANSACTIONS_TARGET - int(counts.sum())
    fractions = expected - counts

    if remaining > 0:
        order = np.argsort(fractions)[::-1]
        counts[order[:remaining]] += 1
    elif remaining < 0:
        order = np.argsort(fractions)
        idx = 0
        while remaining < 0 and idx < len(order):
            pos = int(order[idx])
            if counts[pos] > 10:
                counts[pos] -= 1
                remaining += 1
            idx += 1

    return pd.DataFrame({"date": dates, "transaction_count": counts})


def _seasonal_category_multiplier(month: int, temperature: float) -> dict[str, float]:
    mult: dict[str, float] = {}
    if month in {2, 3, 4}:
        mult["OTC_Medicine"] = 1.25
        mult["Supplements"] = 1.10
    if month in {6, 7, 8}:
        mult["Beverage"] = 1.35
        mult["Skincare"] = 1.12
        mult["Cosmetics"] = 1.08
        mult["Hygiene"] = 1.06
    if month in {11, 12, 1}:
        mult["OTC_Medicine"] = max(mult.get("OTC_Medicine", 1.0), 1.18)
        mult["Daily_Necessities"] = 1.12
    if temperature >= 30:
        mult["Beverage"] = max(mult.get("Beverage", 1.0), 1.22)
    if temperature <= 5:
        mult["OTC_Medicine"] = max(mult.get("OTC_Medicine", 1.0), 1.12)
    return mult


def build_transactions_and_items(
    daily_plan_df: pd.DataFrame,
    products_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    promotions_df: pd.DataFrame,
    weather_df: pd.DataFrame,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    promotion_calendar = build_promotion_calendar(promotions_df)

    customers_internal = customers_df.copy()
    activity_weights = customers_internal["_activity_weight"].to_numpy(dtype=float)
    activity_weights = activity_weights / activity_weights.sum()

    customer_ids = customers_internal["customer_id"].tolist()
    customer_segments = dict(zip(customers_internal["customer_id"], customers_internal["_segment"]))
    customer_tiers = dict(zip(customers_internal["customer_id"], customers_internal["loyalty_tier"]))

    products_internal = products_df.copy()
    products_internal["_category_level1"] = products_internal["_category_level1"].astype(str)

    category_base = (
        products_internal.groupby("_category_level1")["_popularity_weight"].sum().sort_index().to_dict()
    )
    categories = list(category_base.keys())
    category_idx = {c: i for i, c in enumerate(categories)}

    product_lookup = products_internal.set_index("product_id").to_dict(orient="index")

    products_by_category: dict[str, dict[str, np.ndarray]] = {}
    for cat, group in products_internal.groupby("_category_level1"):
        ids = group["product_id"].to_numpy()
        w = group["_popularity_weight"].to_numpy(dtype=float)
        w = w / w.sum()
        products_by_category[cat] = {"ids": ids, "weights": w}

    weather_map = weather_df.copy()
    weather_map["date"] = pd.to_datetime(weather_map["date"])
    weather_map = weather_map.set_index("date")

    transactions: list[dict[str, object]] = []
    items: list[dict[str, object]] = []

    transaction_counter = 1
    item_counter = 1

    for row in daily_plan_df.itertuples(index=False):
        current_date = pd.Timestamp(row.date)
        tx_count = int(row.transaction_count)
        active_promos = promotion_calendar.get(current_date, [])

        temperature = float(weather_map.loc[current_date, "temperature_celsius"])
        seasonal_mult = _seasonal_category_multiplier(current_date.month, temperature)
        is_weekend = current_date.weekday() >= 5

        for _ in range(tx_count):
            transaction_id = f"T{transaction_counter:06d}"

            if transaction_counter <= 80:
                customer_id = customer_ids[(transaction_counter - 1) % min(40, len(customer_ids))]
            else:
                customer_id = str(rng.choice(customer_ids, p=activity_weights))

            segment = str(customer_segments.get(customer_id, "young_worker"))
            loyalty_tier = str(customer_tiers.get(customer_id, "silver"))

            tx_type_probs = np.array([0.48, 0.41, 0.11])
            if is_weekend:
                tx_type_probs = np.array([0.38, 0.42, 0.20])
            tx_type = str(rng.choice(["quick", "regular", "stockup"], p=tx_type_probs))

            if tx_type == "quick":
                distinct_items = int(rng.integers(1, 3))
            elif tx_type == "regular":
                distinct_items = int(rng.integers(2, 5))
            else:
                distinct_items = int(rng.integers(4, 8))

            forced_product_ids: list[str] = []
            if float(rng.random()) < 0.075:
                forced_product_ids = ["P000001", "P000005"]
                if tx_type == "stockup" and float(rng.random()) < 0.35:
                    forced_product_ids.append("P000021")

            distinct_items = max(distinct_items, len(forced_product_ids))

            category_weights = np.array([category_base[c] for c in categories], dtype=float)

            for pref_cat in SEGMENT_CATEGORY_PREFS.get(segment, []):
                if pref_cat in category_idx:
                    category_weights[category_idx[pref_cat]] *= 1.75

            for cat, mult in seasonal_mult.items():
                if cat in category_idx:
                    category_weights[category_idx[cat]] *= mult

            for promo in active_promos:
                target_cat = str(promo["target_category_level1"])
                if target_cat in category_idx:
                    category_weights[category_idx[target_cat]] *= 1.0 + min(0.6, float(promo["discount_rate"]) * 3.2)

            category_weights = category_weights / category_weights.sum()

            basket_quantity = 0
            total_amount = 0
            total_discount = 0
            used_promotions: list[str] = []
            selected_products: set[str] = set()

            for item_pos in range(distinct_items):
                if item_pos < len(forced_product_ids):
                    product_id = forced_product_ids[item_pos]
                    category = str(product_lookup[product_id]["_category_level1"])
                else:
                    category = str(rng.choice(categories, p=category_weights))
                    pool = products_by_category[category]

                    product_id = str(rng.choice(pool["ids"], p=pool["weights"]))
                    retry = 0
                    while product_id in selected_products and retry < 4:
                        product_id = str(rng.choice(pool["ids"], p=pool["weights"]))
                        retry += 1
                selected_products.add(product_id)

                product = product_lookup[product_id]

                if category in {"Daily_Necessities", "Beverage", "Snack", "Baby_Care"}:
                    quantity = int(rng.choice([1, 2, 3, 4, 5], p=[0.46, 0.29, 0.16, 0.07, 0.02]))
                else:
                    quantity = int(rng.choice([1, 2, 3], p=[0.76, 0.20, 0.04]))

                if tx_type == "stockup":
                    quantity += int(rng.choice([0, 1, 2], p=[0.58, 0.34, 0.08]))
                quantity = int(min(quantity, 8))

                original_price = int(product["retail_price_jpy"])
                cost_price = int(product["cost_price_jpy"])

                matching_promos = [p for p in active_promos if str(p["target_category_level1"]) == category]

                promo_apply_prob = 0.58
                if loyalty_tier == "gold":
                    promo_apply_prob += 0.05
                elif loyalty_tier == "platinum":
                    promo_apply_prob += 0.08
                if tx_type == "quick":
                    promo_apply_prob -= 0.05

                discount_rate = 0.0
                promotion_id = ""
                if matching_promos and float(rng.random()) < promo_apply_prob:
                    promo_weights = np.array([float(p["discount_rate"]) for p in matching_promos], dtype=float)
                    promo_weights = promo_weights / promo_weights.sum()
                    chosen = matching_promos[int(rng.choice(np.arange(len(matching_promos)), p=promo_weights))]
                    discount_rate = float(np.clip(rng.normal(float(chosen["discount_rate"]), 0.015), 0.02, 0.35))
                    promotion_id = str(chosen["promotion_id"])
                    used_promotions.append(promotion_id)
                elif float(rng.random()) < 0.06:
                    discount_rate = float(rng.uniform(0.02, 0.08))

                discount_price = int(max(30, round(original_price * (1 - discount_rate))))
                line_total = int(quantity * discount_price)
                discount_amount = int((original_price - discount_price) * quantity)
                margin = int(line_total - quantity * cost_price)

                return_rate = 0.007 if category in {"Cosmetics", "Hair_Care"} else 0.003
                return_flag = int(float(rng.random()) < return_rate)

                items.append(
                    {
                        "transaction_item_id": f"TI{item_counter:07d}",
                        "transaction_id": transaction_id,
                        "product_id": product_id,
                        "quantity": quantity,
                        "unit_price_jpy": discount_price,
                        "original_price_jpy": original_price,
                        "discount_price_jpy": discount_price,
                        "line_total_jpy": line_total,
                        "promotion_id": promotion_id,
                        "return_flag": return_flag,
                        "product_barcode": f"49{int(product_id[1:]):011d}",
                        "tax_rate": 0.1,
                        "tax_included_flag": 1,
                        "item_margin_jpy": margin,
                    }
                )

                item_counter += 1
                basket_quantity += quantity
                total_amount += line_total
                total_discount += discount_amount

            payment_method = str(rng.choice(PAYMENT_METHODS, p=PAYMENT_WEIGHTS_BY_SEGMENT.get(segment, [0.2, 0.3, 0.3, 0.2])))
            omni_prob = {
                "family": 0.07,
                "young_worker": 0.14,
                "senior": 0.04,
                "student": 0.13,
            }.get(segment, 0.08)
            channel = "omni" if float(rng.random()) < omni_prob else "offline"

            waon_points_earned = int(total_amount // 200)
            waon_points_used = 0
            if payment_method == "waon" and float(rng.random()) < 0.30:
                waon_points_used = int(rng.integers(20, min(800, max(40, total_amount // 2)) + 1))
            elif payment_method == "mobile" and float(rng.random()) < 0.10:
                waon_points_used = int(rng.integers(10, min(400, max(20, total_amount // 3)) + 1))

            coupon_id = ""
            if used_promotions and float(rng.random()) < 0.40:
                coupon_id = f"CP{used_promotions[0][2:]}"

            hour = int(rng.choice(HOUR_SLOTS, p=HOUR_WEIGHTS))
            minute = int(rng.choice(np.arange(0, 60, 5)))
            second = int(rng.choice([0, 15, 30, 45]))

            transactions.append(
                {
                    "transaction_id": transaction_id,
                    "customer_id": customer_id,
                    "store_id": STORE_ID,
                    "transaction_date": current_date.strftime("%Y-%m-%d"),
                    "transaction_time": f"{hour:02d}:{minute:02d}:{second:02d}",
                    "total_amount_jpy": total_amount,
                    "discount_amount_jpy": total_discount,
                    "tax_amount_jpy": int(round(total_amount * 0.1)),
                    "payment_method": payment_method,
                    "cashier_id": f"K{int(rng.integers(1, 13)):03d}",
                    "receipt_number": f"R{current_date.strftime('%m%d')}{transaction_counter:08d}",
                    "coupon_id": coupon_id,
                    "waon_points_used": waon_points_used,
                    "waon_points_earned": waon_points_earned,
                    "channel": channel,
                    "basket_size_items": basket_quantity,
                    "transaction_type": tx_type,
                }
            )

            transaction_counter += 1

    transaction_df = pd.DataFrame(transactions)
    item_df = pd.DataFrame(items)
    return transaction_df, item_df


def build_inventory(products_df: pd.DataFrame, items_df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    qty_by_product = items_df.groupby("product_id")["quantity"].sum().to_dict()
    rows: list[dict[str, object]] = []

    for idx, row in enumerate(products_df.to_dict(orient="records"), start=1):
        product_id = str(row["product_id"])
        annual_qty = float(qty_by_product.get(product_id, 0.0))
        avg_daily = annual_qty / 365.0

        reorder_point = int(max(12, round(avg_daily * 9)))
        max_stock_level = int(max(reorder_point + 20, round(avg_daily * 30)))
        stock_quantity = int(max(8, round(avg_daily * float(rng.uniform(14, 22)))))

        if stock_quantity > max_stock_level:
            stock_quantity = max_stock_level

        restock_date = pd.Timestamp("2025-12-01") + pd.Timedelta(days=int(rng.integers(0, 31)))

        if int(row.get("perishable_flag", 0)) == 1:
            shelf_life_days = int(row.get("shelf_life_days", 120))
            expiry_date = (restock_date + pd.Timedelta(days=shelf_life_days)).strftime("%Y-%m-%d")
        else:
            expiry_date = ""

        turnover_30d = float((avg_daily * 30) / max(stock_quantity, 1))

        rows.append(
            {
                "inventory_id": f"INV{idx:06d}",
                "product_id": product_id,
                "store_id": STORE_ID,
                "snapshot_date": "2025-12-31",
                "stock_quantity": stock_quantity,
                "reorder_point": reorder_point,
                "max_stock_level": max_stock_level,
                "last_restock_date": restock_date.strftime("%Y-%m-%d"),
                "expiry_date": expiry_date,
                "shelf_location": f"{str(row['category_level1'])[:2].upper()}-{idx % 30:02d}",
                "days_on_shelf": int(rng.integers(1, 25)),
                "stockout_flag": int(stock_quantity < reorder_point * 0.9 and float(rng.random()) < 0.25),
                "inventory_turnover_30d": round(turnover_30d, 3),
            }
        )

    return pd.DataFrame(rows)


def build_customer_behavior(
    customers_df: pd.DataFrame,
    transaction_df: pd.DataFrame,
    items_df: pd.DataFrame,
    products_df: pd.DataFrame,
) -> pd.DataFrame:
    base = customers_df[["customer_id"]].copy()

    tx = transaction_df.copy()
    tx["transaction_date"] = pd.to_datetime(tx["transaction_date"])
    snapshot_date = pd.Timestamp("2025-12-31")

    tx_metrics = (
        tx.groupby("customer_id")
        .agg(
            tx_count=("transaction_id", "nunique"),
            avg_basket_size=("basket_size_items", "mean"),
            avg_transaction_value_jpy=("total_amount_jpy", "mean"),
            last_purchase_date=("transaction_date", "max"),
        )
        .reset_index()
    )

    tx_metrics["days_since_last_purchase"] = (snapshot_date - tx_metrics["last_purchase_date"]).dt.days
    tx_metrics["purchase_frequency"] = tx_metrics["tx_count"] / 12.0

    promo_response = (
        tx.assign(_has_discount=(tx["discount_amount_jpy"] > 0).astype(int))
        .groupby("customer_id")["_has_discount"]
        .mean()
        .rename("promotion_response_rate")
        .reset_index()
    )

    channel_pref = (
        tx.groupby(["customer_id", "channel"]).size().reset_index(name="count").sort_values(["customer_id", "count"], ascending=[True, False])
    )
    channel_pref = channel_pref.drop_duplicates(subset=["customer_id"]).rename(columns={"channel": "channel_preference"})
    channel_pref = channel_pref[["customer_id", "channel_preference"]]

    item_detail = items_df.merge(tx[["transaction_id", "customer_id"]], on="transaction_id", how="left")
    item_detail = item_detail.merge(products_df[["product_id", "category_level1"]], on="product_id", how="left")

    item_detail["discount_ratio_line"] = (
        (item_detail["original_price_jpy"] - item_detail["discount_price_jpy"])
        / item_detail["original_price_jpy"].replace(0, np.nan)
    )
    item_detail["discount_ratio_line"] = item_detail["discount_ratio_line"].fillna(0)

    price_sensitivity = (
        item_detail.groupby("customer_id")["discount_ratio_line"].mean().rename("price_sensitivity").reset_index()
    )

    pref_cat = (
        item_detail.groupby(["customer_id", "category_level1"]) ["quantity"].sum().reset_index()
    )
    if not pref_cat.empty:
        pref_cat = pref_cat.sort_values(["customer_id", "quantity"], ascending=[True, False]).drop_duplicates("customer_id")
        pref_cat = pref_cat.rename(columns={"category_level1": "preferred_categories"})[["customer_id", "preferred_categories"]]
    else:
        pref_cat = pd.DataFrame(columns=["customer_id", "preferred_categories"])

    behavior = base.merge(tx_metrics, on="customer_id", how="left")
    behavior = behavior.merge(promo_response, on="customer_id", how="left")
    behavior = behavior.merge(channel_pref, on="customer_id", how="left")
    behavior = behavior.merge(price_sensitivity, on="customer_id", how="left")
    behavior = behavior.merge(pref_cat, on="customer_id", how="left")

    behavior["tx_count"] = behavior["tx_count"].fillna(0)
    behavior["avg_basket_size"] = behavior["avg_basket_size"].fillna(0)
    behavior["avg_transaction_value_jpy"] = behavior["avg_transaction_value_jpy"].fillna(0)
    behavior["purchase_frequency"] = behavior["purchase_frequency"].fillna(0)
    behavior["days_since_last_purchase"] = behavior["days_since_last_purchase"].fillna(365)
    behavior["promotion_response_rate"] = behavior["promotion_response_rate"].fillna(0)
    behavior["price_sensitivity"] = behavior["price_sensitivity"].fillna(0)
    behavior["channel_preference"] = behavior["channel_preference"].fillna("offline")
    behavior["preferred_categories"] = behavior["preferred_categories"].fillna("Daily_Necessities")

    freq_q = max(float(behavior["purchase_frequency"].quantile(0.9)), 1e-6)
    ticket_q = max(float(behavior["avg_transaction_value_jpy"].quantile(0.9)), 1e-6)

    freq_norm = np.clip(behavior["purchase_frequency"] / freq_q, 0, 1)
    recency_norm = np.clip(behavior["days_since_last_purchase"] / 90.0, 0, 1)
    ticket_norm = np.clip(behavior["avg_transaction_value_jpy"] / ticket_q, 0, 1)

    behavior["churn_risk_score"] = np.clip(0.55 * recency_norm + 0.30 * (1 - freq_norm) + 0.15 * (1 - ticket_norm), 0, 1)

    behavior["snapshot_date"] = "2025-12-31"
    behavior["last_purchase_date"] = behavior["last_purchase_date"].fillna(pd.Timestamp("2025-01-01")).dt.strftime("%Y-%m-%d")

    out = behavior[
        [
            "customer_id",
            "snapshot_date",
            "avg_basket_size",
            "avg_transaction_value_jpy",
            "purchase_frequency",
            "last_purchase_date",
            "days_since_last_purchase",
            "preferred_categories",
            "price_sensitivity",
            "promotion_response_rate",
            "channel_preference",
            "churn_risk_score",
        ]
    ].copy()

    out["avg_basket_size"] = out["avg_basket_size"].round(3)
    out["avg_transaction_value_jpy"] = out["avg_transaction_value_jpy"].round(2)
    out["purchase_frequency"] = out["purchase_frequency"].round(3)
    out["price_sensitivity"] = out["price_sensitivity"].round(4)
    out["promotion_response_rate"] = out["promotion_response_rate"].round(4)
    out["churn_risk_score"] = out["churn_risk_score"].round(4)
    out["days_since_last_purchase"] = out["days_since_last_purchase"].astype(int)
    return out


def build_product_association(items_df: pd.DataFrame) -> pd.DataFrame:
    baskets = (
        items_df.groupby("transaction_id")["product_id"]
        .agg(lambda s: sorted(set(str(v) for v in s.tolist())))
        .tolist()
    )
    transaction_count = max(len(baskets), 1)

    pair_counts: Counter[tuple[str, str]] = Counter()
    product_counts: Counter[str] = Counter()

    for basket in baskets:
        if not basket:
            continue
        for p in basket:
            product_counts[p] += 1
        for a, b in combinations(basket, 2):
            if a <= b:
                pair_counts[(a, b)] += 1
            else:
                pair_counts[(b, a)] += 1

    minimum_pair_count = max(20, int(round(transaction_count * 0.0015)))
    rows: list[dict[str, object]] = []

    for (a, b), co_count in pair_counts.items():
        if co_count < minimum_pair_count:
            continue

        support = co_count / transaction_count
        conf = co_count / max(product_counts[a], 1)
        prob_b = product_counts[b] / transaction_count
        lift = conf / prob_b if prob_b > 0 else 0.0

        rows.append(
            {
                "product_id_a": a,
                "product_id_b": b,
                "snapshot_date": "2025-12-31",
                "support": round(float(support), 6),
                "confidence": round(float(conf), 6),
                "lift": round(float(lift), 6),
                "co_purchase_count_30d": int(max(1, round(co_count / 12.2))),
            }
        )

    if not rows:
        rows = [
            {
                "product_id_a": "P000001",
                "product_id_b": "P000002",
                "snapshot_date": "2025-12-31",
                "support": 0.01,
                "confidence": 0.2,
                "lift": 1.1,
                "co_purchase_count_30d": 10,
            }
        ]

    result = pd.DataFrame(rows)
    result["_rank"] = result["support"] * result["confidence"] * result["lift"]
    result = result.sort_values("_rank", ascending=False).drop(columns=["_rank"]).head(250)
    return result.reset_index(drop=True)


def build_review(
    transactions_df: pd.DataFrame,
    items_df: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    tx = transactions_df[["transaction_id", "customer_id", "transaction_date"]].copy()
    tx["transaction_date"] = pd.to_datetime(tx["transaction_date"])

    detail = items_df.merge(tx, on="transaction_id", how="left")
    detail = detail[
        [
            "transaction_id",
            "product_id",
            "customer_id",
            "transaction_date",
            "original_price_jpy",
            "discount_price_jpy",
            "promotion_id",
            "return_flag",
        ]
    ].drop_duplicates(subset=["transaction_id", "product_id", "customer_id"])

    if detail.empty:
        return pd.DataFrame(
            [
                {
                    "review_id": "RV0000001",
                    "product_id": "P000001",
                    "customer_id": "C000001",
                    "review_date": "2025-01-05",
                    "rating_score": 4,
                    "sentiment_score": 0.4,
                    "review_channel": "app",
                }
            ]
        )

    review_count = min(max(2000, int(len(transactions_df) * 0.11)), 5200, len(detail))
    sampled_idx = rng.choice(detail.index.to_numpy(), size=review_count, replace=False)
    sampled = detail.loc[sampled_idx].reset_index(drop=True)

    rows: list[dict[str, object]] = []
    for i, row in sampled.iterrows():
        original = float(row["original_price_jpy"])
        discounted = float(row["discount_price_jpy"])
        discount_ratio = 0.0 if original <= 0 else max(0.0, min(0.9, (original - discounted) / original))

        base = 3.6 + 0.35 * (1 if discount_ratio >= 0.1 else 0) - 0.50 * float(row["return_flag"]) + float(rng.normal(0, 0.85))
        rating = int(np.clip(round(base), 1, 5))
        sentiment = float(np.clip((rating - 3) / 2.0 + rng.normal(0, 0.18), -1, 1))

        review_delay = int(rng.integers(0, 21))
        review_date = pd.Timestamp(row["transaction_date"]) + pd.Timedelta(days=review_delay)
        if review_date.year > SCENARIO_YEAR:
            review_date = pd.Timestamp(f"{SCENARIO_YEAR}-12-31")

        channel = str(rng.choice(["app", "web", "store"], p=[0.58, 0.27, 0.15]))

        rows.append(
            {
                "review_id": f"RV{i + 1:07d}",
                "product_id": str(row["product_id"]),
                "customer_id": str(row["customer_id"]),
                "review_date": review_date.strftime("%Y-%m-%d"),
                "rating_score": rating,
                "sentiment_score": round(sentiment, 4),
                "review_channel": channel,
            }
        )

    return pd.DataFrame(rows)


def build_store(total_transactions: int) -> pd.DataFrame:
    avg_transactions_per_day = total_transactions / 365.0
    avg_foot_traffic = int(round(avg_transactions_per_day / 0.62))

    return pd.DataFrame(
        [
            {
                "store_id": STORE_ID,
                "store_name": STORE_NAME,
                "store_type": "drugstore",
                "prefecture": PREFECTURE,
                "city": CITY,
                "postcode": POSTCODE,
                "latitude": LATITUDE,
                "longitude": LONGITUDE,
                "store_size_sqm": 980,
                "parking_spaces": 42,
                "location_type": "urban_residential",
                "opening_date": "2022-03-15",
                "opening_hours": "09:00-22:00",
                "average_foot_traffic": avg_foot_traffic,
                "competitor_sugi_store_count": SUGI_STORE_COUNT,
            }
        ]
    )


def write_csv(name: str, df: pd.DataFrame):
    path = OUTPUT_DIR / f"{name}.csv"
    df.to_csv(path, index=False)
    print(f"generated: {name}.csv ({len(df)} rows, {len(df.columns)} cols)")


def main():
    rng = np.random.default_rng(RNG_SEED)

    products = build_products(rng)
    promotions = build_promotions()
    holiday = build_holiday()
    weather = build_weather(rng)
    customers = build_customers(rng, CUSTOMER_POOL_SIZE)

    promotion_calendar = build_promotion_calendar(promotions)
    daily_plan = build_daily_transaction_plan(weather, holiday, promotion_calendar, rng)

    transactions, transaction_items = build_transactions_and_items(
        daily_plan_df=daily_plan,
        products_df=products,
        customers_df=customers,
        promotions_df=promotions,
        weather_df=weather,
        rng=rng,
    )

    stores = build_store(len(transactions))
    inventory = build_inventory(products, transaction_items, rng)
    customer_behavior = build_customer_behavior(customers, transactions, transaction_items, products)
    product_association = build_product_association(transaction_items)
    review = build_review(transactions, transaction_items, rng)

    products_out = products.drop(columns=["_category_level1", "_popularity_weight"], errors="ignore")
    customers_out = customers.drop(columns=["_segment", "_activity_weight"], errors="ignore")

    write_csv("transaction", transactions)
    write_csv("transaction_items", transaction_items)
    write_csv("product", products_out)
    write_csv("customer", customers_out)
    write_csv("store", stores)
    write_csv("promotion", promotions)
    write_csv("inventory", inventory)
    write_csv("weather", weather)
    write_csv("holiday", holiday)
    write_csv("customer_behavior", customer_behavior)
    write_csv("product_association", product_association)
    write_csv("review", review)

    print("scenario_year:", SCENARIO_YEAR)
    print("sugi_store_count:", SUGI_STORE_COUNT)
    print("capture_rate:", round(CAPTURE_RATE, 4))
    print("target_transactions:", ANNUAL_TRANSACTIONS_TARGET)
    print("actual_transactions:", len(transactions))
    print("actual_transaction_items:", len(transaction_items))
    print("customers:", len(customers_out))


if __name__ == "__main__":
    main()
