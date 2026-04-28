"""Total sales amount forecasting utilities for the Home workbench."""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd


def _daily_amount_history(parsed_data: Dict[str, pd.DataFrame]) -> pd.Series:
    """Build daily total amount series from uploaded parsed data."""
    if "transaction_items" not in parsed_data:
        return pd.Series(dtype="float64")

    items_df = parsed_data["transaction_items"].copy()

    if "transaction" in parsed_data and {
        "transaction_id",
        "transaction_date",
    }.issubset(parsed_data["transaction"].columns):
        trans_df = parsed_data["transaction"][["transaction_id", "transaction_date"]].copy()
        items_df = items_df.merge(trans_df, on="transaction_id", how="left")

    if "transaction_date" in items_df.columns:
        date_col = "transaction_date"
    elif "date" in items_df.columns:
        date_col = "date"
    else:
        return pd.Series(dtype="float64")

    items_df["_date"] = pd.to_datetime(items_df[date_col], errors="coerce").dt.floor("D")
    items_df = items_df.dropna(subset=["_date"])

    if "line_total" in items_df.columns:
        amount_col = "line_total"
    elif "line_total_jpy" in items_df.columns:
        amount_col = "line_total_jpy"
    elif "total_amount" in items_df.columns:
        amount_col = "total_amount"
    elif "total_amount_jpy" in items_df.columns:
        amount_col = "total_amount_jpy"
    elif {"quantity", "unit_price"}.issubset(items_df.columns):
        items_df["_calc_amount"] = pd.to_numeric(items_df["quantity"], errors="coerce").fillna(0) * pd.to_numeric(
            items_df["unit_price"], errors="coerce"
        ).fillna(0)
        amount_col = "_calc_amount"
    elif {"quantity", "unit_price_jpy"}.issubset(items_df.columns):
        items_df["_calc_amount"] = pd.to_numeric(items_df["quantity"], errors="coerce").fillna(0) * pd.to_numeric(
            items_df["unit_price_jpy"], errors="coerce"
        ).fillna(0)
        amount_col = "_calc_amount"
    else:
        # Last fallback: quantity as pseudo amount
        amount_col = "quantity" if "quantity" in items_df.columns else None

    if amount_col is None:
        return pd.Series(dtype="float64")

    daily = (
        items_df.groupby("_date")[amount_col]
        .sum(min_count=1)
        .fillna(0)
        .sort_index()
        .astype(float)
    )
    return daily


def _naive_weekday_forecast(parsed_data: Dict[str, pd.DataFrame], horizon: int) -> Dict[str, Any]:
    daily = _daily_amount_history(parsed_data)
    if daily.empty:
        today = pd.Timestamp.now().floor("D")
        dates = pd.date_range(start=today + timedelta(days=1), periods=horizon)
        totals = [0.0] * horizon
        return {
            "method": "naive_empty",
            "dates": [d.strftime("%Y-%m-%d") for d in dates],
            "totals": totals,
            "cumulative_total": 0.0,
            "avg_daily_total": 0.0,
            "fallback_used": True,
            "model_ready": False,
            "note": "No daily sales history available in uploaded data.",
        }

    last_date = daily.index.max()
    weekday_means = daily.groupby(daily.index.weekday).mean().to_dict()
    overall_mean = float(daily.tail(min(28, len(daily))).mean())

    dates = [last_date + timedelta(days=idx + 1) for idx in range(horizon)]
    totals = [
        float(weekday_means.get(d.weekday(), overall_mean))
        for d in dates
    ]

    return {
        "method": "naive_weekday_avg",
        "dates": [d.strftime("%Y-%m-%d") for d in dates],
        "totals": totals,
        "cumulative_total": float(np.sum(totals)),
        "avg_daily_total": float(np.mean(totals)) if totals else 0.0,
        "fallback_used": True,
        "model_ready": False,
        "note": "Using weekday-average fallback before forecast model is ready.",
    }


def _prepare_pair_pricing(features_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[Tuple[str, str], float]]:
    pair_cols = ["product_id", "store_id"]
    if not all(col in features_df.columns for col in pair_cols):
        return pd.DataFrame(), {}

    if "sales_quantity" in features_df.columns:
        quantity_col = "sales_quantity"
    elif "quantity" in features_df.columns:
        quantity_col = "quantity"
    else:
        return pd.DataFrame(), {}

    amount_col = "sales_amount" if "sales_amount" in features_df.columns else quantity_col

    grouped = features_df.groupby(pair_cols, as_index=False).agg(
        sales_quantity=(quantity_col, "sum"),
        sales_amount=(amount_col, "sum"),
    )

    grouped["sales_quantity"] = grouped["sales_quantity"].replace(0, np.nan)
    grouped["avg_unit_price"] = (grouped["sales_amount"] / grouped["sales_quantity"]).replace([np.inf, -np.inf], np.nan).fillna(1.0)

    pair_price = {
        (str(row["product_id"]), str(row["store_id"])): float(row["avg_unit_price"])
        for _, row in grouped.iterrows()
    }
    return grouped, pair_price


def _model_based_total_forecast(app: Any, horizon: int, top_n_pairs: int = 20) -> Dict[str, Any] | None:
    pipeline = getattr(app.state, "forecast_pipeline", None)
    if pipeline is None:
        return None

    features_df = getattr(pipeline, "features_df", None)
    if features_df is None or not isinstance(features_df, pd.DataFrame) or features_df.empty:
        return None

    pair_stats, pair_price = _prepare_pair_pricing(features_df)
    if pair_stats.empty:
        return None

    top_pairs_df = pair_stats.sort_values("sales_amount", ascending=False).head(max(1, top_n_pairs))
    pairs = [(str(row["product_id"]), str(row["store_id"])) for _, row in top_pairs_df.iterrows()]

    forecasts = pipeline.batch_forecast(pairs, horizon)
    valid_forecasts = [f for f in forecasts if isinstance(f, dict) and "predictions" in f and "dates" in f]
    if not valid_forecasts:
        return None

    date_axis = valid_forecasts[0]["dates"]
    totals = np.zeros(len(date_axis), dtype=float)

    for item in valid_forecasts:
        pair = (str(item.get("product_id")), str(item.get("store_id")))
        unit_price = pair_price.get(pair, 1.0)
        pred_qty = np.array(item.get("predictions", []), dtype=float)
        if len(pred_qty) != len(totals):
            continue
        totals += np.clip(pred_qty, 0, None) * unit_price

    return {
        "method": "model_batch_total_amount",
        "dates": date_axis,
        "totals": totals.round(2).tolist(),
        "cumulative_total": float(totals.sum()),
        "avg_daily_total": float(totals.mean()) if len(totals) else 0.0,
        "fallback_used": False,
        "model_ready": True,
        "source_pairs_count": len(valid_forecasts),
        "note": "Aggregated from pair-level model forecasts weighted by historical unit price.",
    }


def build_total_forecast(
    app: Any,
    parsed_data: Dict[str, pd.DataFrame],
    version_id: str,
    horizon: int = 14,
    model_type: str = "auto",
    top_n_pairs: int = 20,
) -> Dict[str, Any]:
    """Build total amount forecast response payload."""
    model_type = (model_type or "auto").lower()

    model_payload = None
    if model_type in {"auto", "lightgbm", "model"}:
        model_payload = _model_based_total_forecast(app, horizon=horizon, top_n_pairs=top_n_pairs)

    if model_payload is None:
        fallback_payload = _naive_weekday_forecast(parsed_data, horizon=horizon)
        payload = fallback_payload
    else:
        payload = model_payload

    payload.update(
        {
            "version": version_id,
            "horizon": horizon,
            "metric": "total_amount",
            "model_type": model_type,
        }
    )
    return payload
