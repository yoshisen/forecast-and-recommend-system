"""Customer classification model pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split


try:
    from xgboost import XGBClassifier  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional import fallback
    XGBClassifier = None


@dataclass
class ClassificationTrainResult:
    metrics: Dict[str, Any]
    dataset_info: Dict[str, Any]


class CustomerClassifier:
    """Binary classifier on customer-level retail behavior."""

    def __init__(self, random_state: int = 42, default_threshold: float = 0.5):
        self.random_state = random_state
        self.default_threshold = default_threshold
        self.model: Any = None
        self.feature_columns: list[str] = []
        self.dropped_feature_columns: list[str] = []
        self.customer_features: pd.DataFrame | None = None
        self.label_source: str = "unknown"
        self.eval_cache: Dict[str, np.ndarray] = {}

    @staticmethod
    def _pick_amount_column(df: pd.DataFrame) -> Optional[str]:
        for col in ["line_total", "line_total_jpy", "total_amount", "total_amount_jpy"]:
            if col in df.columns:
                return col
        if {"quantity", "unit_price", "unit_price_jpy"}.intersection(df.columns) and "quantity" in df.columns:
            price_col = "unit_price" if "unit_price" in df.columns else "unit_price_jpy"
            df["_calc_amount"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0) * pd.to_numeric(
                df[price_col], errors="coerce"
            ).fillna(0)
            return "_calc_amount"
        return None

    @staticmethod
    def _pick_date_column(df: pd.DataFrame) -> Optional[str]:
        for col in ["transaction_date", "date", "order_date"]:
            if col in df.columns:
                return col
        return None

    @staticmethod
    def _fill_missing_values(df: pd.DataFrame) -> pd.DataFrame:
        filled = df.copy()
        for col in filled.columns:
            series = filled[col]
            if pd.api.types.is_numeric_dtype(series):
                filled[col] = series.fillna(0)
            elif pd.api.types.is_datetime64_any_dtype(series):
                parsed = pd.to_datetime(series, errors="coerce")
                unix_seconds = (parsed.astype("int64", copy=False) // 10**9).where(parsed.notna(), 0)
                filled[col] = unix_seconds.astype(float)
            elif isinstance(series.dtype, pd.CategoricalDtype):
                if "unknown" not in series.cat.categories:
                    series = series.cat.add_categories(["unknown"])
                filled[col] = series.fillna("unknown")
            else:
                filled[col] = series.fillna("unknown")
        return filled

    def _build_customer_table(self, parsed_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        if "transaction_items" not in parsed_data or "transaction" not in parsed_data:
            raise ValueError("transaction_items and transaction sheets are required for classification")

        items_df = parsed_data["transaction_items"].copy()
        trans_df = parsed_data["transaction"].copy()

        required_cols = ["transaction_id", "customer_id"]
        if not all(col in trans_df.columns for col in required_cols):
            raise ValueError("transaction sheet must contain transaction_id and customer_id")

        merge_cols = ["transaction_id", "customer_id"]
        for extra_col in ["transaction_date", "store_id", "total_amount", "total_amount_jpy"]:
            if extra_col in trans_df.columns:
                merge_cols.append(extra_col)

        merged = items_df.merge(trans_df[merge_cols], on="transaction_id", how="left")
        merged = merged.dropna(subset=["customer_id"]).copy()

        amount_col = self._pick_amount_column(merged)
        if amount_col is None:
            merged["_fallback_amount"] = pd.to_numeric(merged.get("quantity", 1), errors="coerce").fillna(0)
            amount_col = "_fallback_amount"

        if "quantity" not in merged.columns:
            merged["quantity"] = 1

        date_col = self._pick_date_column(merged)
        if date_col:
            merged["_date"] = pd.to_datetime(merged[date_col], errors="coerce")
        else:
            merged["_date"] = pd.Timestamp.now()

        customer_agg = (
            merged.groupby("customer_id", dropna=False)
            .agg(
                transaction_count=("transaction_id", "nunique"),
                total_amount=(amount_col, "sum"),
                total_quantity=("quantity", "sum"),
                active_days=("_date", lambda s: pd.Series(s).dt.floor("D").nunique()),
                last_seen=("_date", "max"),
            )
            .reset_index()
        )

        snapshot = customer_agg["last_seen"].max()
        customer_agg["recency_days"] = (snapshot - customer_agg["last_seen"]).dt.days.fillna(0)
        customer_agg["avg_ticket"] = customer_agg["total_amount"] / customer_agg["transaction_count"].replace(0, np.nan)
        customer_agg["avg_ticket"] = customer_agg["avg_ticket"].fillna(0)

        # Optional product diversity
        if "product_id" in merged.columns:
            diversity = merged.groupby("customer_id")["product_id"].nunique().rename("product_diversity")
            customer_agg = customer_agg.merge(diversity, on="customer_id", how="left")
            customer_agg["product_diversity"] = customer_agg["product_diversity"].fillna(0)

        # Merge customer profile columns when available
        if "customer" in parsed_data and "customer_id" in parsed_data["customer"].columns:
            customer_profile = parsed_data["customer"].copy()
            profile_cols = ["customer_id"]
            for col in ["age", "gender", "registration_date"]:
                if col in customer_profile.columns:
                    profile_cols.append(col)
            if len(profile_cols) > 1:
                customer_agg = customer_agg.merge(customer_profile[profile_cols], on="customer_id", how="left")

        # Build target label
        explicit_labels = ["label", "target", "is_positive", "conversion_label", "subscribed", "y", "class"]
        label_col = next((col for col in customer_agg.columns if col in explicit_labels), None)
        if label_col:
            y = pd.to_numeric(customer_agg[label_col], errors="coerce")
            y = y.fillna(0).astype(int)
            self.label_source = f"explicit:{label_col}"
        else:
            threshold = customer_agg["total_amount"].quantile(0.75)
            y = (customer_agg["total_amount"] >= threshold).astype(int)
            self.label_source = "derived:high_spender_top_25pct"

        customer_agg["label"] = y
        customer_agg = customer_agg.drop(columns=["last_seen"], errors="ignore")

        return customer_agg

    def _encode_features(self, df: pd.DataFrame) -> pd.DataFrame:
        encoded = pd.get_dummies(df, dummy_na=True)
        if self.feature_columns:
            encoded = encoded.reindex(columns=self.feature_columns, fill_value=0)
        return encoded

    def _drop_leaky_features(self, feature_df: pd.DataFrame) -> pd.DataFrame:
        self.dropped_feature_columns = []
        if self.label_source != "derived:high_spender_top_25pct":
            return feature_df

        # 派生ラベルと同義になりやすい列を除外して、過剰に高い指標を抑制する。
        drop_candidates = ["total_amount", "avg_ticket"]
        to_drop = [col for col in drop_candidates if col in feature_df.columns]
        if not to_drop:
            return feature_df

        self.dropped_feature_columns = to_drop
        return feature_df.drop(columns=to_drop, errors="ignore")

    def train(self, parsed_data: Dict[str, pd.DataFrame]) -> ClassificationTrainResult:
        dataset = self._build_customer_table(parsed_data)
        if dataset["label"].nunique() < 2:
            raise ValueError("classification label has only one class")

        feature_df = dataset.drop(columns=["label", "customer_id"], errors="ignore")
        feature_df = self._drop_leaky_features(feature_df)
        feature_df = self._fill_missing_values(feature_df)

        encoded = pd.get_dummies(feature_df, dummy_na=True)
        self.feature_columns = encoded.columns.tolist()

        y = dataset["label"].astype(int).values
        customer_ids = dataset["customer_id"].astype(str).values

        x_train, x_test, y_train, y_test, _id_train, id_test = train_test_split(
            encoded,
            y,
            customer_ids,
            test_size=0.3,
            random_state=self.random_state,
            stratify=y,
        )

        if XGBClassifier is not None:
            model = XGBClassifier(
                n_estimators=250,
                max_depth=4,
                learning_rate=0.06,
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=self.random_state,
                eval_metric="logloss",
            )
            model_name = "xgboost"
        else:
            model = RandomForestClassifier(
                n_estimators=300,
                random_state=self.random_state,
                class_weight="balanced",
            )
            model_name = "random_forest_fallback"

        model.fit(x_train, y_train)
        y_proba = model.predict_proba(x_test)[:, 1]
        y_pred = (y_proba >= self.default_threshold).astype(int)

        metrics = {
            "precision": float(precision_score(y_test, y_pred, zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, zero_division=0)),
            "f1": float(f1_score(y_test, y_pred, zero_division=0)),
            "roc_auc": float(roc_auc_score(y_test, y_proba)),
            "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
            "default_threshold": float(self.default_threshold),
            "model": model_name,
        }

        self.model = model
        self.customer_features = dataset.drop(columns=["label"], errors="ignore").copy()
        self.eval_cache = {
            "y_test": y_test,
            "y_proba": y_proba,
            "customer_ids": np.array(id_test),
        }

        dataset_info = {
            "n_customers": int(len(dataset)),
            "positive_ratio": float(dataset["label"].mean()),
            "label_source": self.label_source,
            "n_features": int(encoded.shape[1]),
            "dropped_feature_columns": self.dropped_feature_columns,
            "label_is_derived": bool(self.label_source.startswith("derived:")),
        }

        return ClassificationTrainResult(metrics=metrics, dataset_info=dataset_info)

    def _predict_from_features(self, features_df: pd.DataFrame, threshold: Optional[float] = None) -> np.ndarray:
        if self.model is None:
            raise ValueError("classifier is not trained")

        threshold = float(self.default_threshold if threshold is None else threshold)
        encoded = self._encode_features(self._fill_missing_values(features_df))
        proba = self.model.predict_proba(encoded)[:, 1]
        pred = (proba >= threshold).astype(int)
        return np.vstack([proba, pred]).T

    def predict_customer(self, customer_id: str, threshold: Optional[float] = None) -> Dict[str, Any]:
        if self.customer_features is None:
            raise ValueError("customer feature table is unavailable")

        row = self.customer_features[self.customer_features["customer_id"].astype(str) == str(customer_id)]
        if row.empty:
            raise ValueError(f"customer_id not found: {customer_id}")

        feature_df = row.drop(columns=["customer_id"], errors="ignore")
        out = self._predict_from_features(feature_df, threshold=threshold)[0]
        used_threshold = float(self.default_threshold if threshold is None else threshold)

        return {
            "customer_id": str(customer_id),
            "probability": float(out[0]),
            "prediction": int(out[1]),
            "threshold": used_threshold,
            "label_source": self.label_source,
        }

    def predict_with_features(self, features: Dict[str, Any], threshold: Optional[float] = None) -> Dict[str, Any]:
        feature_df = pd.DataFrame([features])
        out = self._predict_from_features(feature_df, threshold=threshold)[0]
        used_threshold = float(self.default_threshold if threshold is None else threshold)
        return {
            "probability": float(out[0]),
            "prediction": int(out[1]),
            "threshold": used_threshold,
        }

    def scan_thresholds(self, step: float = 0.05) -> Dict[str, Any]:
        if not self.eval_cache:
            raise ValueError("evaluation cache is unavailable")

        y_test = self.eval_cache["y_test"]
        y_proba = self.eval_cache["y_proba"]

        thresholds = np.arange(0.05, 0.951, step)
        rows = []
        for th in thresholds:
            y_pred = (y_proba >= th).astype(int)
            rows.append(
                {
                    "threshold": float(np.round(th, 4)),
                    "precision": float(precision_score(y_test, y_pred, zero_division=0)),
                    "recall": float(recall_score(y_test, y_pred, zero_division=0)),
                    "f1": float(f1_score(y_test, y_pred, zero_division=0)),
                    "positive_predictions": int(y_pred.sum()),
                }
            )

        best = max(rows, key=lambda x: x["f1"]) if rows else None
        return {
            "rows": rows,
            "best_by_f1": best,
            "current_threshold": float(self.default_threshold),
        }

    def set_threshold(self, threshold: float):
        if threshold <= 0 or threshold >= 1:
            raise ValueError("threshold must be between 0 and 1")
        self.default_threshold = float(threshold)
