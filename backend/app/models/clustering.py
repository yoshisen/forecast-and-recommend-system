"""Customer clustering model (KMeans + PCA)."""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


class CustomerClusterer:
    """Customer segmentation based on purchase behavior."""

    def __init__(self, n_clusters: int = 4, random_state: int = 42):
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.kmeans: KMeans | None = None
        self.pca: PCA | None = None
        self.feature_columns: List[str] = []
        self.customer_segments: pd.DataFrame | None = None
        self.cluster_profiles: pd.DataFrame | None = None
        self.summary: Dict[str, Any] = {}

    @staticmethod
    def _pick_amount_column(df: pd.DataFrame) -> str:
        for col in ["line_total", "line_total_jpy", "total_amount", "total_amount_jpy"]:
            if col in df.columns:
                return col
        if "quantity" in df.columns:
            return "quantity"
        raise ValueError("no usable amount column found")

    @staticmethod
    def _fill_missing_values(df: pd.DataFrame) -> pd.DataFrame:
        filled = df.copy()
        for col in filled.columns:
            series = filled[col]
            if pd.api.types.is_numeric_dtype(series):
                filled[col] = series.fillna(0)
            elif isinstance(series.dtype, pd.CategoricalDtype):
                if "unknown" not in series.cat.categories:
                    series = series.cat.add_categories(["unknown"])
                filled[col] = series.fillna("unknown")
            else:
                filled[col] = series.fillna("unknown")
        return filled

    def _build_customer_features(self, parsed_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        if "transaction_items" not in parsed_data or "transaction" not in parsed_data:
            raise ValueError("transaction_items and transaction sheets are required for clustering")

        items_df = parsed_data["transaction_items"].copy()
        trans_df = parsed_data["transaction"].copy()

        if not {"transaction_id", "customer_id"}.issubset(trans_df.columns):
            raise ValueError("transaction sheet must contain transaction_id and customer_id")

        merge_cols = ["transaction_id", "customer_id"]
        for col in ["transaction_date", "store_id", "total_amount", "total_amount_jpy"]:
            if col in trans_df.columns:
                merge_cols.append(col)

        df = items_df.merge(trans_df[merge_cols], on="transaction_id", how="left")
        df = df.dropna(subset=["customer_id"]).copy()

        amount_col = self._pick_amount_column(df)
        if "quantity" not in df.columns:
            df["quantity"] = 1

        if "transaction_date" in df.columns:
            df["_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
        else:
            df["_date"] = pd.Timestamp.now()

        base = (
            df.groupby("customer_id")
            .agg(
                transaction_count=("transaction_id", "nunique"),
                total_amount=(amount_col, "sum"),
                total_quantity=("quantity", "sum"),
                active_days=("_date", lambda s: pd.Series(s).dt.floor("D").nunique()),
                last_seen=("_date", "max"),
            )
            .reset_index()
        )

        snapshot = base["last_seen"].max()
        base["recency_days"] = (snapshot - base["last_seen"]).dt.days.fillna(0)
        base["avg_ticket"] = base["total_amount"] / base["transaction_count"].replace(0, np.nan)
        base["avg_ticket"] = base["avg_ticket"].fillna(0)

        # Add category spend profile when available
        if "product" in parsed_data and "product_id" in df.columns and "product_id" in parsed_data["product"].columns:
            prod_df = parsed_data["product"].copy()
            if "category_level1" in prod_df.columns:
                df = df.merge(prod_df[["product_id", "category_level1"]], on="product_id", how="left")
                pivot = (
                    df.pivot_table(
                        index="customer_id",
                        columns="category_level1",
                        values=amount_col,
                        aggfunc="sum",
                        fill_value=0,
                    )
                    .add_prefix("cat_")
                    .reset_index()
                )
                base = base.merge(pivot, on="customer_id", how="left")

        # Add demographics when available
        if "customer" in parsed_data and "customer_id" in parsed_data["customer"].columns:
            customer_df = parsed_data["customer"].copy()
            cols = ["customer_id"]
            for col in ["age", "gender"]:
                if col in customer_df.columns:
                    cols.append(col)
            if len(cols) > 1:
                base = base.merge(customer_df[cols], on="customer_id", how="left")

        base = base.drop(columns=["last_seen"], errors="ignore")
        return self._fill_missing_values(base)

    def fit(self, parsed_data: Dict[str, pd.DataFrame], n_clusters: int | None = None) -> Dict[str, Any]:
        customer_features = self._build_customer_features(parsed_data)
        if len(customer_features) < 4:
            raise ValueError("not enough customers for clustering")

        clusters = int(n_clusters or self.n_clusters)
        clusters = max(2, min(clusters, len(customer_features) - 1))

        x_raw = customer_features.drop(columns=["customer_id"], errors="ignore")
        x_encoded = pd.get_dummies(x_raw, dummy_na=True)
        self.feature_columns = x_encoded.columns.tolist()

        x_scaled = self.scaler.fit_transform(x_encoded)

        self.kmeans = KMeans(n_clusters=clusters, random_state=self.random_state, n_init=10)
        labels = self.kmeans.fit_predict(x_scaled)

        self.pca = PCA(n_components=2, random_state=self.random_state)
        x_pca = self.pca.fit_transform(x_scaled)

        seg_df = customer_features[["customer_id"]].copy()
        seg_df["cluster"] = labels
        seg_df["pca_x"] = x_pca[:, 0]
        seg_df["pca_y"] = x_pca[:, 1]

        numeric = customer_features.drop(columns=["customer_id"], errors="ignore")
        numeric = numeric.select_dtypes(include=[np.number]).copy()
        profile_df = pd.concat([seg_df[["cluster"]], numeric], axis=1).groupby("cluster").mean().reset_index()

        silhouette = float(silhouette_score(x_scaled, labels)) if clusters > 1 else 0.0

        self.customer_segments = seg_df
        self.cluster_profiles = profile_df
        self.summary = {
            "n_customers": int(len(seg_df)),
            "n_clusters": int(clusters),
            "silhouette": silhouette,
            "inertia": float(self.kmeans.inertia_),
        }
        return self.summary

    def get_segments(self) -> List[Dict[str, Any]]:
        if self.customer_segments is None:
            raise ValueError("clusterer is not trained")

        counts = self.customer_segments["cluster"].value_counts().sort_index().to_dict()
        profiles = []
        if self.cluster_profiles is not None:
            profiles = self.cluster_profiles.to_dict(orient="records")

        result = []
        for profile in profiles:
            cluster_id = int(profile["cluster"])
            result.append(
                {
                    "cluster": cluster_id,
                    "count": int(counts.get(cluster_id, 0)),
                    "profile": profile,
                }
            )
        return result

    def get_points(self, limit: int = 2000) -> List[Dict[str, Any]]:
        if self.customer_segments is None:
            raise ValueError("clusterer is not trained")
        return self.customer_segments.head(limit).to_dict(orient="records")

    def get_customer_cluster(self, customer_id: str) -> Dict[str, Any]:
        if self.customer_segments is None:
            raise ValueError("clusterer is not trained")

        row = self.customer_segments[self.customer_segments["customer_id"].astype(str) == str(customer_id)]
        if row.empty:
            raise ValueError(f"customer_id not found: {customer_id}")

        cluster_id = int(row.iloc[0]["cluster"])
        profile = None
        if self.cluster_profiles is not None:
            p = self.cluster_profiles[self.cluster_profiles["cluster"] == cluster_id]
            if not p.empty:
                profile = p.iloc[0].to_dict()

        return {
            "customer_id": str(customer_id),
            "cluster": cluster_id,
            "pca_x": float(row.iloc[0]["pca_x"]),
            "pca_y": float(row.iloc[0]["pca_y"]),
            "profile": profile,
        }
