"""Prophet-based total amount forecaster."""
from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd


try:
    from prophet import Prophet  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency
    Prophet = None


class TotalProphetForecaster:
    """Train Prophet on daily total sales amount."""

    def __init__(self):
        self.model: Optional[Any] = None
        self.history_df: pd.DataFrame | None = None

    @staticmethod
    def _pick_amount_column(df: pd.DataFrame) -> Optional[str]:
        for col in ["line_total", "line_total_jpy", "total_amount", "total_amount_jpy"]:
            if col in df.columns:
                return col
        if {"quantity", "unit_price"}.issubset(df.columns):
            df["_calc_amount"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0) * pd.to_numeric(
                df["unit_price"], errors="coerce"
            ).fillna(0)
            return "_calc_amount"
        if {"quantity", "unit_price_jpy"}.issubset(df.columns):
            df["_calc_amount"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0) * pd.to_numeric(
                df["unit_price_jpy"], errors="coerce"
            ).fillna(0)
            return "_calc_amount"
        if "quantity" in df.columns:
            return "quantity"
        return None

    def _build_daily_series(self, parsed_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        if "transaction_items" not in parsed_data:
            raise ValueError("transaction_items sheet is required")

        items_df = parsed_data["transaction_items"].copy()
        if "transaction" in parsed_data and {"transaction_id", "transaction_date"}.issubset(parsed_data["transaction"].columns):
            trans_df = parsed_data["transaction"][["transaction_id", "transaction_date"]].copy()
            items_df = items_df.merge(trans_df, on="transaction_id", how="left")

        date_col = "transaction_date" if "transaction_date" in items_df.columns else "date" if "date" in items_df.columns else None
        if date_col is None:
            raise ValueError("transaction_date/date column is required for time series")

        amount_col = self._pick_amount_column(items_df)
        if amount_col is None:
            raise ValueError("amount column is required for time series")

        items_df["ds"] = pd.to_datetime(items_df[date_col], errors="coerce").dt.floor("D")
        items_df = items_df.dropna(subset=["ds"]).copy()
        items_df[amount_col] = pd.to_numeric(items_df[amount_col], errors="coerce").fillna(0)

        daily = items_df.groupby("ds")[amount_col].sum().reset_index().rename(columns={amount_col: "y"})
        if len(daily) < 14:
            raise ValueError("at least 14 daily points are required for prophet training")

        return daily.sort_values("ds")

    def train(self, parsed_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        if Prophet is None:
            raise ValueError("prophet package is not installed in current environment")

        daily = self._build_daily_series(parsed_data)

        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            seasonality_mode="multiplicative",
        )
        model.fit(daily)

        self.model = model
        self.history_df = daily

        return {
            "n_points": int(len(daily)),
            "start_date": daily["ds"].min().strftime("%Y-%m-%d"),
            "end_date": daily["ds"].max().strftime("%Y-%m-%d"),
            "method": "prophet",
        }

    def forecast(self, horizon: int = 14) -> Dict[str, Any]:
        if self.model is None:
            raise ValueError("prophet model is not trained")

        future = self.model.make_future_dataframe(periods=horizon)
        pred = self.model.predict(future).tail(horizon)

        return {
            "method": "prophet",
            "horizon": int(horizon),
            "dates": pred["ds"].dt.strftime("%Y-%m-%d").tolist(),
            "yhat": pred["yhat"].round(3).tolist(),
            "yhat_lower": pred["yhat_lower"].round(3).tolist(),
            "yhat_upper": pred["yhat_upper"].round(3).tolist(),
            "trend": pred["trend"].round(3).tolist() if "trend" in pred.columns else [],
            "weekly": pred["weekly"].round(3).tolist() if "weekly" in pred.columns else [],
            "yearly": pred["yearly"].round(3).tolist() if "yearly" in pred.columns else [],
        }
