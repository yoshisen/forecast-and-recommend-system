"""Upload schema catalog used by parser and API guide endpoint."""
from __future__ import annotations

from typing import Any


SHEET_ALIAS_CATALOG: dict[str, list[str]] = {
    "transaction": ["transaction", "transactions", "orders", "order", "取引", "トランザクション"],
    "transaction_items": [
        "transactionitems",
        "transaction_items",
        "orderitems",
        "order_items",
        "orderdetails",
        "transaction_details",
        "取引明細",
        "トランザクション明細",
    ],
    "product": ["product", "products", "item", "items", "sku", "商品", "プロダクト"],
    "customer": ["customer", "customers", "user", "users", "member", "顧客", "カスタマー"],
    "store": ["store", "stores", "shop", "shops", "location", "店舗", "ストア"],
    "inventory": ["inventory", "stock", "stocklevel", "在庫", "インベントリ"],
    "promotion": ["promotion", "promotions", "campaign", "プロモーション"],
    "weather": ["weather", "climate", "天気"],
    "holiday": ["holiday", "holidays", "festival", "祝日", "ホリデー"],
    "customer_behavior": ["customerbehavior", "customer_behavior", "userbehavior", "顧客行動"],
    "product_association": ["productassociation", "product_association", "association", "商品関連"],
    "review": ["review", "reviews", "feedback", "rating", "レビュー"],
}


FIELD_ALIAS_CATALOG: dict[str, list[str]] = {
    # Core identifiers
    "transaction_id": ["transactionid", "transaction_id", "trans_id", "order_id", "orderid", "txn_id"],
    "transaction_item_id": ["transaction_item_id", "transactionitemid", "order_item_id", "line_id"],
    "customer_id": ["customerid", "customer_id", "cust_id", "user_id", "userid", "member_id"],
    "product_id": ["productid", "product_id", "prod_id", "item_id", "itemid", "sku_id"],
    "store_id": ["storeid", "store_id", "shop_id", "shopid", "location_id", "branch_id"],
    "promotion_id": ["promotion_id", "promo_id", "campaign_id"],
    "inventory_id": ["inventory_id", "stock_id"],
    "review_id": ["review_id", "feedback_id"],
    "supplier_id": ["supplier_id", "vendor_id"],
    "cashier_id": ["cashier_id", "operator_id"],
    "coupon_id": ["coupon_id", "voucher_id"],
    "receipt_number": ["receipt_number", "receipt_no", "receipt_id"],

    # Transaction date/time
    "transaction_date": ["transactiondate", "transaction_date", "date", "order_date", "orderdate", "sale_date"],
    "transaction_time": ["transactiontime", "transaction_time", "time", "order_time", "sale_time"],
    "transaction_timestamp": ["transaction_timestamp", "transaction_datetime", "order_datetime", "event_timestamp"],

    # Amount and price
    "total_amount": ["totalamount", "total_amount", "amount", "total", "total_price"],
    "total_amount_jpy": ["total_amount_jpy", "amount_jpy", "gross_amount_jpy", "order_amount_jpy"],
    "discount_amount_jpy": ["discount_amount_jpy", "discount_jpy", "promo_discount_jpy"],
    "tax_amount_jpy": ["tax_amount_jpy", "tax_jpy", "vat_amount_jpy"],
    "unit_price": ["unit_price", "unitprice", "price_per_unit"],
    "unit_price_jpy": ["unit_price_jpy", "selling_price_jpy", "price_jpy", "sales_price_jpy"],
    "original_price_jpy": ["original_price_jpy", "list_price_jpy", "regular_price_jpy"],
    "discount_price_jpy": ["discount_price_jpy", "net_price_jpy", "promo_price_jpy"],
    "line_total": ["line_total", "line_amount", "line_sales"],
    "line_total_jpy": ["line_total_jpy", "line_amount_jpy", "line_sales_jpy"],
    "retail_price": ["retailprice", "retail_price", "shelf_price"],
    "retail_price_jpy": ["retail_price_jpy", "retailpricejpy", "msrp_jpy"],
    "cost_price": ["costprice", "cost_price", "cost"],
    "cost_price_jpy": ["cost_price_jpy", "costpricejpy", "purchase_price_jpy"],
    "item_margin_jpy": ["item_margin_jpy", "margin_jpy", "gross_margin_jpy"],

    # Quantity and counts
    "quantity": ["quantity", "qty", "units", "sales_qty"],
    "purchase_count": ["purchase_count", "buy_count", "txn_count"],
    "basket_size_items": ["basket_size_items", "basket_items", "items_per_order"],

    # Product attributes
    "product_name": ["productname", "product_name", "name", "item_name", "sku_name"],
    "brand": ["brand", "brand_name"],
    "category_level1": ["categorylevel1", "category_level1", "category1", "main_category", "category_l1"],
    "category_level2": ["categorylevel2", "category_level2", "category2", "sub_category", "category_l2"],
    "category_level3": ["categorylevel3", "category_level3", "category3", "category_l3"],
    "unit_of_measure": ["unit_of_measure", "uom", "unit"],
    "package_size": ["package_size", "pack_size"],
    "weight_g": ["weight_g", "weight_gram", "grams"],
    "shelf_life_days": ["shelf_life_days", "shelf_days", "expiry_days"],
    "perishable_flag": ["perishable_flag", "is_perishable"],
    "organic_flag": ["organic_flag", "is_organic"],
    "private_label_flag": ["private_label_flag", "is_private_label"],
    "seasonal_flag": ["seasonal_flag", "is_seasonal"],
    "launch_date": ["launch_date", "release_date"],

    # Customer attributes
    "registration_date": ["registrationdate", "registration_date", "reg_date", "join_date", "signup_date"],
    "birth_date": ["birth_date", "birthday", "dob"],
    "age": ["age", "customer_age"],
    "gender": ["gender", "sex"],
    "income_level": ["income_level", "income_band"],
    "education_level": ["education_level", "education"],
    "occupation": ["occupation", "job"],
    "marital_status": ["marital_status", "marriage_status"],
    "household_size": ["household_size", "family_size"],
    "has_children": ["has_children", "children_flag"],
    "children_age_range": ["children_age_range", "kid_age_range"],
    "loyalty_tier": ["loyalty_tier", "member_tier"],
    "total_lifetime_value_jpy": ["total_lifetime_value_jpy", "clv_jpy", "lifetime_value_jpy"],
    "preferred_store_id": ["preferred_store_id", "home_store_id"],
    "waon_card_number": ["waon_card_number", "loyalty_card_number"],

    # Store attributes
    "store_name": ["store_name", "shop_name"],
    "store_type": ["store_type", "shop_type"],
    "store_size_sqm": ["store_size_sqm", "store_area_sqm"],
    "location_type": ["location_type", "site_type"],
    "opening_date": ["opening_date", "open_date"],
    "opening_hours": ["opening_hours", "business_hours"],
    "average_foot_traffic": ["average_foot_traffic", "avg_foot_traffic", "foot_traffic"],
    "postcode": ["postcode", "postal_code", "zip_code"],
    "prefecture": ["prefecture", "state", "province"],
    "city": ["city", "town"],
    "latitude": ["latitude", "lat"],
    "longitude": ["longitude", "lon", "lng"],
    "parking_spaces": ["parking_spaces", "parking_capacity"],

    # Promotion attributes
    "promotion_name": ["promotion_name", "campaign_name"],
    "promotion_type": ["promotion_type", "campaign_type"],
    "start_date": ["start_date", "promo_start_date"],
    "end_date": ["end_date", "promo_end_date"],
    "discount_rate": ["discount_rate", "promo_discount_rate"],
    "min_purchase_amount_jpy": ["min_purchase_amount_jpy", "min_amount_jpy"],
    "max_discount_jpy": ["max_discount_jpy", "discount_cap_jpy"],

    # Inventory attributes
    "stock_quantity": ["stock_quantity", "stock_qty", "inventory_quantity"],
    "reorder_point": ["reorder_point", "reorder_level"],
    "max_stock_level": ["max_stock_level", "max_inventory_level"],
    "last_restock_date": ["last_restock_date", "restock_date"],
    "expiry_date": ["expiry_date", "expire_date"],
    "shelf_location": ["shelf_location", "bin_location"],
    "days_on_shelf": ["days_on_shelf", "shelf_days"],
    "stockout_flag": ["stockout_flag", "is_stockout"],

    # External context
    "holiday_name": ["holiday_name", "festival_name"],
    "holiday_type": ["holiday_type", "holiday_category"],
    "is_long_weekend": ["is_long_weekend", "long_weekend_flag"],
    "temperature_celsius": ["temperature_celsius", "temp_c", "temperature"],
    "humidity_percent": ["humidity_percent", "humidity"],
    "precipitation_mm": ["precipitation_mm", "rain_mm", "rainfall_mm"],
    "weather_condition": ["weather_condition", "weather_type"],

    # Behavior / analytics extension
    "avg_basket_size": ["avg_basket_size", "average_basket_size"],
    "avg_transaction_value_jpy": ["avg_transaction_value_jpy", "average_order_value_jpy", "aov_jpy"],
    "purchase_frequency": ["purchase_frequency", "buy_frequency"],
    "last_purchase_date": ["last_purchase_date", "latest_purchase_date"],
    "days_since_last_purchase": ["days_since_last_purchase", "recency_days"],
    "preferred_categories": ["preferred_categories", "favorite_categories"],
    "price_sensitivity": ["price_sensitivity", "price_elasticity_band"],
    "promotion_response_rate": ["promotion_response_rate", "promo_response_rate"],
    "channel_preference": ["channel_preference", "preferred_channel"],
    "churn_risk_score": ["churn_risk_score", "churn_score"],

    # Association and review extension
    "product_id_a": ["product_id_a", "lhs_product_id"],
    "product_id_b": ["product_id_b", "rhs_product_id"],
    "support": ["support", "support_score"],
    "confidence": ["confidence", "confidence_score"],
    "lift": ["lift", "lift_score"],
    "co_purchase_count_30d": ["co_purchase_count_30d", "co_buy_count_30d"],
    "review_date": ["review_date", "feedback_date"],
    "rating_score": ["rating_score", "rating"],
    "sentiment_score": ["sentiment_score", "sentiment"],
    "review_channel": ["review_channel", "feedback_channel"],

    # Payment / channel
    "payment_method": ["payment_method", "pay_method"],
    "waon_points_used": ["waon_points_used", "points_used"],
    "waon_points_earned": ["waon_points_earned", "points_earned"],
    "channel": ["channel", "sales_channel"],
    "return_flag": ["return_flag", "is_returned"],
    "product_barcode": ["product_barcode", "barcode", "jan_code"],
}


SHEET_FIELD_GUIDE: dict[str, dict[str, Any]] = {
    "transaction": {
        "description": "Order header. Customer, store and transaction-level amount/time.",
        "minimum_fields": ["transaction_id", "customer_id", "transaction_date"],
        "recommended_fields": [
            "store_id",
            "transaction_time",
            "total_amount_jpy",
            "discount_amount_jpy",
            "tax_amount_jpy",
            "payment_method",
        ],
        "optional_fields": ["coupon_id", "waon_points_used", "waon_points_earned", "channel", "receipt_number", "cashier_id"],
    },
    "transaction_items": {
        "description": "Order line-items. The most important fact table for all analysis.",
        "minimum_fields": ["transaction_id", "product_id"],
        "recommended_fields": ["transaction_item_id", "quantity", "unit_price_jpy", "line_total_jpy"],
        "optional_fields": ["original_price_jpy", "discount_price_jpy", "promotion_id", "return_flag", "product_barcode"],
    },
    "product": {
        "description": "Product master and category/price attributes.",
        "minimum_fields": ["product_id"],
        "recommended_fields": ["product_name", "category_level1", "retail_price_jpy", "cost_price_jpy"],
        "optional_fields": [
            "category_level2",
            "category_level3",
            "brand",
            "unit_of_measure",
            "package_size",
            "weight_g",
            "perishable_flag",
            "seasonal_flag",
        ],
    },
    "customer": {
        "description": "Customer master for recommendation/classification/clustering.",
        "minimum_fields": ["customer_id"],
        "recommended_fields": ["registration_date", "age", "gender"],
        "optional_fields": ["loyalty_tier", "income_level", "household_size", "preferred_store_id", "total_lifetime_value_jpy"],
    },
    "store": {
        "description": "Store attributes and geolocation context.",
        "minimum_fields": ["store_id"],
        "recommended_fields": ["store_name", "prefecture", "city", "store_type"],
        "optional_fields": ["latitude", "longitude", "store_size_sqm", "average_foot_traffic"],
    },
    "promotion": {
        "description": "Promotion campaigns and effect windows.",
        "minimum_fields": ["promotion_id"],
        "recommended_fields": ["start_date", "end_date", "discount_rate"],
        "optional_fields": ["promotion_name", "promotion_type", "min_purchase_amount_jpy", "max_discount_jpy"],
    },
    "inventory": {
        "description": "Inventory snapshot for stock-risk analysis.",
        "minimum_fields": ["product_id"],
        "recommended_fields": ["store_id", "stock_quantity", "reorder_point"],
        "optional_fields": ["last_restock_date", "expiry_date", "days_on_shelf", "stockout_flag"],
    },
    "weather": {
        "description": "Weather by date and region for demand-impact features.",
        "minimum_fields": ["date"],
        "recommended_fields": ["prefecture", "temperature_celsius", "precipitation_mm"],
        "optional_fields": ["humidity_percent", "weather_condition"],
    },
    "holiday": {
        "description": "Holiday calendar for seasonality and promotion response.",
        "minimum_fields": ["date"],
        "recommended_fields": ["holiday_name"],
        "optional_fields": ["holiday_type", "is_long_weekend"],
    },
    "customer_behavior": {
        "description": "Derived customer behavior snapshot for richer segmentation and recommendation.",
        "minimum_fields": ["customer_id"],
        "recommended_fields": ["avg_transaction_value_jpy", "purchase_frequency", "days_since_last_purchase"],
        "optional_fields": ["promotion_response_rate", "churn_risk_score", "preferred_categories"],
    },
    "product_association": {
        "description": "商品ペアの関連ルールスナップショット。クロスセル分析の拡張入力。",
        "minimum_fields": ["product_id_a", "product_id_b"],
        "recommended_fields": ["support", "confidence", "lift"],
        "optional_fields": ["co_purchase_count_30d"],
    },
    "review": {
        "description": "レビュー事実テーブル。評価と感情特徴の拡張入力。",
        "minimum_fields": ["review_id", "product_id", "customer_id"],
        "recommended_fields": ["review_date", "rating_score", "sentiment_score"],
        "optional_fields": ["review_channel"],
    },
}


TASK_MINIMUM_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "forecast": {
        "required_sheets": ["transaction_items", "transaction", "product"],
        "minimum_fields_by_sheet": {
            "transaction_items": ["transaction_id", "product_id"],
            "transaction": ["transaction_id", "transaction_date"],
            "product": ["product_id"],
        },
        "usefulness": "critical",
    },
    "recommend": {
        "required_sheets": ["transaction_items", "transaction", "customer", "product"],
        "minimum_fields_by_sheet": {
            "transaction_items": ["transaction_id", "product_id"],
            "transaction": ["transaction_id", "customer_id"],
            "customer": ["customer_id"],
            "product": ["product_id"],
        },
        "usefulness": "critical",
    },
    "classification": {
        "required_sheets": ["transaction_items", "transaction", "customer"],
        "minimum_fields_by_sheet": {
            "transaction_items": ["transaction_id", "product_id"],
            "transaction": ["transaction_id", "customer_id", "transaction_date"],
            "customer": ["customer_id"],
        },
        "usefulness": "high",
    },
    "association": {
        "required_sheets": ["transaction_items", "transaction", "product"],
        "minimum_fields_by_sheet": {
            "transaction_items": ["transaction_id", "product_id"],
            "transaction": ["transaction_id"],
            "product": ["product_id"],
        },
        "usefulness": "high",
    },
    "clustering": {
        "required_sheets": ["transaction_items", "transaction", "customer"],
        "minimum_fields_by_sheet": {
            "transaction_items": ["transaction_id", "product_id"],
            "transaction": ["transaction_id", "customer_id", "transaction_date"],
            "customer": ["customer_id"],
        },
        "usefulness": "high",
    },
    "prophet": {
        "required_sheets": ["transaction_items", "transaction", "product"],
        "minimum_fields_by_sheet": {
            "transaction_items": ["transaction_id"],
            "transaction": ["transaction_id", "transaction_date"],
            "product": ["product_id"],
        },
        "usefulness": "high",
    },
}


FIELD_UTILITY_CATALOG: list[dict[str, Any]] = [
    {
        "field": "transaction_id",
        "utility": "critical",
        "granularity": ["transaction", "transaction_items"],
        "used_by": ["forecast", "recommend", "classification", "association", "clustering", "prophet"],
    },
    {
        "field": "product_id",
        "utility": "critical",
        "granularity": ["transaction_items", "product"],
        "used_by": ["forecast", "recommend", "association", "clustering"],
    },
    {
        "field": "customer_id",
        "utility": "critical",
        "granularity": ["transaction", "customer"],
        "used_by": ["recommend", "classification", "clustering"],
    },
    {
        "field": "transaction_date",
        "utility": "critical",
        "granularity": ["transaction", "timeseries"],
        "used_by": ["forecast", "classification", "clustering", "prophet"],
    },
    {
        "field": "quantity",
        "utility": "high",
        "granularity": ["transaction_items"],
        "used_by": ["forecast", "recommend", "classification", "clustering", "prophet"],
    },
    {
        "field": "line_total_jpy",
        "utility": "high",
        "granularity": ["transaction_items"],
        "used_by": ["forecast", "classification", "clustering", "prophet"],
    },
    {
        "field": "store_id",
        "utility": "high",
        "granularity": ["transaction", "store"],
        "used_by": ["forecast", "recommend", "clustering"],
    },
    {
        "field": "category_level1",
        "utility": "medium",
        "granularity": ["product"],
        "used_by": ["recommend", "clustering"],
    },
    {
        "field": "retail_price_jpy",
        "utility": "medium",
        "granularity": ["product", "transaction_items"],
        "used_by": ["forecast", "recommend"],
    },
    {
        "field": "discount_price_jpy",
        "utility": "medium",
        "granularity": ["transaction_items"],
        "used_by": ["forecast", "prophet"],
    },
    {
        "field": "age",
        "utility": "medium",
        "granularity": ["customer"],
        "used_by": ["classification", "clustering"],
    },
    {
        "field": "gender",
        "utility": "medium",
        "granularity": ["customer"],
        "used_by": ["classification", "clustering"],
    },
    {
        "field": "promotion_id",
        "utility": "medium",
        "granularity": ["transaction_items", "promotion"],
        "used_by": ["forecast", "recommend"],
    },
    {
        "field": "discount_rate",
        "utility": "medium",
        "granularity": ["promotion"],
        "used_by": ["forecast", "recommend"],
    },
    {
        "field": "stock_quantity",
        "utility": "medium",
        "granularity": ["inventory"],
        "used_by": ["forecast", "clustering"],
    },
    {
        "field": "temperature_celsius",
        "utility": "medium",
        "granularity": ["weather"],
        "used_by": ["forecast", "prophet"],
    },
    {
        "field": "precipitation_mm",
        "utility": "medium",
        "granularity": ["weather"],
        "used_by": ["forecast", "prophet"],
    },
    {
        "field": "is_long_weekend",
        "utility": "medium",
        "granularity": ["holiday"],
        "used_by": ["forecast", "prophet"],
    },
    {
        "field": "churn_risk_score",
        "utility": "nice_to_have",
        "granularity": ["customer_behavior"],
        "used_by": ["classification", "recommend"],
    },
    {
        "field": "product_id_a",
        "utility": "nice_to_have",
        "granularity": ["product_association"],
        "used_by": ["association"],
    },
    {
        "field": "product_id_b",
        "utility": "nice_to_have",
        "granularity": ["product_association"],
        "used_by": ["association"],
    },
    {
        "field": "support",
        "utility": "medium",
        "granularity": ["product_association"],
        "used_by": ["association"],
    },
    {
        "field": "confidence",
        "utility": "medium",
        "granularity": ["product_association"],
        "used_by": ["association"],
    },
    {
        "field": "lift",
        "utility": "medium",
        "granularity": ["product_association"],
        "used_by": ["association"],
    },
    {
        "field": "rating_score",
        "utility": "nice_to_have",
        "granularity": ["review"],
        "used_by": ["recommend", "classification"],
    },
    {
        "field": "sentiment_score",
        "utility": "nice_to_have",
        "granularity": ["review"],
        "used_by": ["recommend", "classification"],
    },
]


DEGRADE_POLICY: list[dict[str, str]] = [
    {
        "condition": "Missing optional sheets/columns",
        "behavior": "Parser keeps available columns and skips unsupported joins.",
    },
    {
        "condition": "Missing quantity but ids are present",
        "behavior": "Recommendation pipeline uses transaction count fallback (quantity=1).",
    },
    {
        "condition": "Missing amount columns",
        "behavior": "Forecast/total analysis falls back to quantity-based pseudo amount.",
    },
    {
        "condition": "Task required sheets missing",
        "behavior": "Task status becomes skipped, other analysis paths continue.",
    },
]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value not in seen:
            output.append(value)
            seen.add(value)
    return output


def build_parser_field_mappings() -> dict[str, list[str]]:
    """Build parser mapping dictionary from the field alias catalog."""
    mappings: dict[str, list[str]] = {}
    for field_name, aliases in FIELD_ALIAS_CATALOG.items():
        mappings[field_name] = _dedupe([field_name, *aliases])
    return mappings


def build_upload_schema_payload() -> dict[str, Any]:
    """Return payload for frontend upload schema guide page."""
    sheets = []
    for sheet_name, config in SHEET_FIELD_GUIDE.items():
        sheets.append(
            {
                "sheet": sheet_name,
                "aliases": SHEET_ALIAS_CATALOG.get(sheet_name, []),
                "description": config["description"],
                "minimum_fields": config.get("minimum_fields", []),
                "recommended_fields": config.get("recommended_fields", []),
                "optional_fields": config.get("optional_fields", []),
            }
        )

    field_catalog = []
    for field_row in FIELD_UTILITY_CATALOG:
        field_name = field_row["field"]
        field_catalog.append(
            {
                "field": field_name,
                "aliases": FIELD_ALIAS_CATALOG.get(field_name, [field_name]),
                "utility": field_row.get("utility", "medium"),
                "granularity": field_row.get("granularity", []),
                "used_by": field_row.get("used_by", []),
            }
        )

    return {
        "version": "schema-v2-planning",
        "naming_rules": {
            "style": "snake_case",
            "date_suffix": "*_date",
            "time_suffix": "*_time",
            "timestamp_suffix": "*_timestamp",
            "amount_suffix": "*_jpy",
            "id_suffix": "*_id",
            "windows": ["*_7d", "*_14d", "*_30d", "*_90d"],
        },
        "sheets": sheets,
        "task_requirements": TASK_MINIMUM_REQUIREMENTS,
        "field_catalog": field_catalog,
        "degrade_policy": DEGRADE_POLICY,
        "notes": [
            "Users can upload fewer columns. Missing optional columns will not block parsing.",
            "Provide minimum required fields for each target task to avoid task-level training failures.",
            "For CSV/ZIP uploads, use recognizable sheet-like file names such as transaction_items.csv.",
            "Prefixes or suffixes in file names are tolerated, but explicit sheet names are recommended.",
        ],
    }


def _field_hint(field_name: str) -> dict[str, Any]:
    aliases = FIELD_ALIAS_CATALOG.get(field_name, [field_name])
    return {
        "field": field_name,
        "aliases": aliases[:10],
    }


def _build_task_reason_fields(
    missing_sheets: list[str],
    missing_fields_by_sheet: dict[str, list[str]],
) -> tuple[str, str | None, str]:
    """タスクの不足状態から理由コード・互換理由・日本語理由を構築する。"""
    if missing_sheets:
        detail = ", ".join(missing_sheets)
        return (
            "missing_required_sheets",
            f"missing_required_sheets: {detail}",
            f"必須シート不足: {detail}",
        )

    if missing_fields_by_sheet:
        pairs = []
        for sheet_name, missing_fields in missing_fields_by_sheet.items():
            pairs.append(f"{sheet_name}[{', '.join(missing_fields)}]")
        detail = "; ".join(pairs)
        return (
            "missing_required_fields",
            f"missing_required_fields: {detail}",
            f"必須フィールド不足: {detail}",
        )

    return ("ok", None, "問題ありません")


def build_field_readiness_from_parsed_data(parsed_data: dict[str, Any]) -> dict[str, Any]:
    """Analyze uploaded data columns and return sheet/task field readiness."""
    parsed_data = parsed_data or {}
    available_sheets = sorted(parsed_data.keys())

    sheets: list[dict[str, Any]] = []
    for sheet_name, guide in SHEET_FIELD_GUIDE.items():
        minimum_fields = guide.get("minimum_fields", [])
        recommended_fields = guide.get("recommended_fields", [])
        optional_fields = guide.get("optional_fields", [])

        if sheet_name not in parsed_data:
            sheets.append(
                {
                    "sheet": sheet_name,
                    "present": False,
                    "column_count": 0,
                    "present_columns": [],
                    "missing_minimum_fields": minimum_fields,
                    "missing_recommended_fields": recommended_fields,
                    "missing_optional_fields": optional_fields,
                    "minimum_ready": False,
                    "coverage_ratio": 0.0,
                }
            )
            continue

        df = parsed_data[sheet_name]
        columns = [str(col) for col in getattr(df, "columns", [])]
        column_set = set(columns)

        missing_minimum = [field for field in minimum_fields if field not in column_set]
        missing_recommended = [field for field in recommended_fields if field not in column_set]
        missing_optional = [field for field in optional_fields if field not in column_set]

        considered = len(minimum_fields) + len(recommended_fields)
        covered = considered - len(missing_minimum) - len(missing_recommended)
        coverage_ratio = float(covered / considered) if considered > 0 else 1.0

        sheets.append(
            {
                "sheet": sheet_name,
                "present": True,
                "column_count": len(columns),
                "present_columns": columns,
                "missing_minimum_fields": missing_minimum,
                "missing_recommended_fields": missing_recommended,
                "missing_optional_fields": missing_optional,
                "minimum_ready": len(missing_minimum) == 0,
                "coverage_ratio": round(coverage_ratio, 4),
            }
        )

    tasks: dict[str, Any] = {}
    for task_name, config in TASK_MINIMUM_REQUIREMENTS.items():
        required_sheets = config.get("required_sheets", [])
        minimum_fields_by_sheet = config.get("minimum_fields_by_sheet", {})

        missing_sheets = [sheet for sheet in required_sheets if sheet not in parsed_data]
        missing_fields_by_sheet: dict[str, list[str]] = {}
        missing_field_hints: dict[str, list[dict[str, Any]]] = {}

        for sheet_name, required_fields in minimum_fields_by_sheet.items():
            if sheet_name not in parsed_data:
                continue
            columns = set(str(col) for col in getattr(parsed_data[sheet_name], "columns", []))
            missing_fields = [field for field in required_fields if field not in columns]
            if missing_fields:
                missing_fields_by_sheet[sheet_name] = missing_fields
                missing_field_hints[sheet_name] = [_field_hint(field) for field in missing_fields]

        can_train_with_fields = len(missing_sheets) == 0 and len(missing_fields_by_sheet) == 0
        reason_code, reason, reason_ja = _build_task_reason_fields(
            missing_sheets=missing_sheets,
            missing_fields_by_sheet=missing_fields_by_sheet,
        )

        tasks[task_name] = {
            "required_sheets": required_sheets,
            "minimum_fields_by_sheet": minimum_fields_by_sheet,
            "missing_required_sheets": missing_sheets,
            "missing_required_fields_by_sheet": missing_fields_by_sheet,
            "missing_required_field_hints": missing_field_hints,
            "can_train_with_fields": can_train_with_fields,
            "reason_code": reason_code,
            "reason": reason,
            "reason_ja": reason_ja,
        }

    task_trainable_count = sum(1 for item in tasks.values() if item.get("can_train_with_fields"))
    sheet_present_count = sum(1 for item in sheets if item.get("present"))

    return {
        "summary": {
            "available_sheets": available_sheets,
            "sheet_present_count": sheet_present_count,
            "sheet_expected_count": len(SHEET_FIELD_GUIDE),
            "task_trainable_count": task_trainable_count,
            "task_total_count": len(tasks),
        },
        "sheets": sheets,
        "tasks": tasks,
    }
