"""Association rule mining model for basket analysis."""
from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules


class AssociationRuleMiner:
    """Apriori + association rules for cross-sell recommendations."""

    def __init__(self):
        self.frequent_itemsets: pd.DataFrame | None = None
        self.rules_df: pd.DataFrame | None = None
        self.fallback_pairs: pd.DataFrame | None = None
        self.summary: Dict[str, Any] = {}

    @staticmethod
    def _build_basket(parsed_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        if "transaction_items" not in parsed_data:
            raise ValueError("transaction_items sheet is required")

        items_df = parsed_data["transaction_items"].copy()
        if not {"transaction_id", "product_id"}.issubset(items_df.columns):
            raise ValueError("transaction_items must contain transaction_id and product_id")

        basket = (
            items_df[["transaction_id", "product_id"]]
            .dropna()
            .drop_duplicates()
            .assign(value=1)
            .pivot_table(index="transaction_id", columns="product_id", values="value", fill_value=0)
        )
        basket = basket > 0

        if basket.shape[0] < 5 or basket.shape[1] < 2:
            raise ValueError("not enough transactions or products for association mining")

        return basket

    @staticmethod
    def _build_external_fallback(parsed_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        if "product_association" not in parsed_data:
            return pd.DataFrame()

        assoc_df = parsed_data["product_association"].copy()
        required_cols = {"product_id_a", "product_id_b"}
        if not required_cols.issubset(assoc_df.columns):
            return pd.DataFrame()

        assoc_df["product_id_a"] = assoc_df["product_id_a"].astype(str)
        assoc_df["product_id_b"] = assoc_df["product_id_b"].astype(str)

        for metric_col in ["support", "confidence", "lift"]:
            if metric_col in assoc_df.columns:
                assoc_df[metric_col] = pd.to_numeric(assoc_df[metric_col], errors="coerce")
            else:
                assoc_df[metric_col] = 0.0

        base = assoc_df[["product_id_a", "product_id_b", "support", "confidence", "lift"]].dropna(
            subset=["product_id_a", "product_id_b"]
        )
        swapped = base.rename(columns={"product_id_a": "product_id_b", "product_id_b": "product_id_a"})
        out = pd.concat([base, swapped], ignore_index=True)
        out = out[out["product_id_a"] != out["product_id_b"]]
        if out.empty:
            return out

        out = out.sort_values(["lift", "confidence", "support"], ascending=False)
        out = out.drop_duplicates(subset=["product_id_a", "product_id_b"], keep="first")
        return out.reset_index(drop=True)

    @staticmethod
    def _build_cooccurrence_fallback(basket: pd.DataFrame, min_support: float) -> pd.DataFrame:
        binary = basket.astype(int)
        n_transactions = int(binary.shape[0])
        if n_transactions == 0:
            return pd.DataFrame()

        item_counts = binary.sum(axis=0)
        co_matrix = binary.T.dot(binary)
        products = list(binary.columns)

        # Keep fallback broad enough so sparse products still get candidates.
        min_pair_count = max(3, int(n_transactions * 0.00025))
        rows: List[Dict[str, Any]] = []

        for i, product_a in enumerate(products):
            count_a = float(item_counts[product_a])
            if count_a <= 0:
                continue
            for j in range(i + 1, len(products)):
                product_b = products[j]
                count_b = float(item_counts[product_b])
                if count_b <= 0:
                    continue

                pair_count = float(co_matrix.iat[i, j])
                if pair_count < min_pair_count:
                    continue

                support = pair_count / n_transactions
                conf_ab = pair_count / count_a
                conf_ba = pair_count / count_b
                lift_ab = conf_ab / (count_b / n_transactions) if count_b > 0 else 0.0
                lift_ba = conf_ba / (count_a / n_transactions) if count_a > 0 else 0.0

                rows.append(
                    {
                        "product_id_a": str(product_a),
                        "product_id_b": str(product_b),
                        "support": float(support),
                        "confidence": float(conf_ab),
                        "lift": float(lift_ab),
                    }
                )
                rows.append(
                    {
                        "product_id_a": str(product_b),
                        "product_id_b": str(product_a),
                        "support": float(support),
                        "confidence": float(conf_ba),
                        "lift": float(lift_ba),
                    }
                )

        if not rows:
            return pd.DataFrame()

        out = pd.DataFrame(rows)
        out = out.sort_values(["lift", "confidence", "support"], ascending=False)
        out = out.drop_duplicates(subset=["product_id_a", "product_id_b"], keep="first")
        return out.reset_index(drop=True)

    def fit(
        self,
        parsed_data: Dict[str, pd.DataFrame],
        min_support: float = 0.01,
        min_confidence: float = 0.12,
        min_lift: float = 1.0,
        max_len: int = 3,
    ) -> Dict[str, Any]:
        basket = self._build_basket(parsed_data)
        cooccurrence_fallback = self._build_cooccurrence_fallback(basket, min_support=min_support)
        external_fallback = self._build_external_fallback(parsed_data)

        fallback_frames = [df for df in [cooccurrence_fallback, external_fallback] if not df.empty]
        if fallback_frames:
            fallback_pairs = pd.concat(fallback_frames, ignore_index=True)
            fallback_pairs = fallback_pairs.sort_values(["lift", "confidence", "support"], ascending=False)
            fallback_pairs = fallback_pairs.drop_duplicates(subset=["product_id_a", "product_id_b"], keep="first")
            self.fallback_pairs = fallback_pairs.reset_index(drop=True)
        else:
            self.fallback_pairs = pd.DataFrame()

        frequent_itemsets = apriori(
            basket,
            min_support=min_support,
            use_colnames=True,
            max_len=max_len,
        )

        if frequent_itemsets.empty:
            self.frequent_itemsets = frequent_itemsets
            self.rules_df = pd.DataFrame()
            self.summary = {
                "n_transactions": int(basket.shape[0]),
                "n_products": int(basket.shape[1]),
                "n_itemsets": 0,
                "n_rules": 0,
                "n_fallback_pairs": int(len(self.fallback_pairs)),
                "min_support": float(min_support),
                "min_confidence": float(min_confidence),
                "min_lift": float(min_lift),
            }
            return self.summary

        rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=min_confidence)
        if not rules.empty:
            rules = rules[rules["lift"] >= min_lift].copy()
            rules = rules.sort_values(["lift", "confidence", "support"], ascending=False)

        self.frequent_itemsets = frequent_itemsets
        self.rules_df = rules
        self.summary = {
            "n_transactions": int(basket.shape[0]),
            "n_products": int(basket.shape[1]),
            "n_itemsets": int(len(frequent_itemsets)),
            "n_rules": int(len(rules)),
            "n_fallback_pairs": int(len(self.fallback_pairs)),
            "min_support": float(min_support),
            "min_confidence": float(min_confidence),
            "min_lift": float(min_lift),
        }
        return self.summary

    @staticmethod
    def _rule_to_dict(row: pd.Series) -> Dict[str, Any]:
        return {
            "antecedents": sorted(list(row["antecedents"])),
            "consequents": sorted(list(row["consequents"])),
            "support": float(row["support"]),
            "confidence": float(row["confidence"]),
            "lift": float(row["lift"]),
            "leverage": float(row.get("leverage", 0.0)),
            "conviction": float(row.get("conviction", 0.0)) if pd.notna(row.get("conviction", 0.0)) else 0.0,
        }

    def list_rules(self, top_k: int = 50) -> List[Dict[str, Any]]:
        if self.rules_df is None or self.rules_df.empty:
            return []
        return [self._rule_to_dict(row) for _, row in self.rules_df.head(top_k).iterrows()]

    def recommend(self, product_id: str, top_k: int = 10) -> List[Dict[str, Any]]:
        product_id = str(product_id)

        candidates: Dict[str, Dict[str, Any]] = {}

        def _upsert_candidate(pid: str, confidence: float, lift: float, support: float):
            if not pid or pid == product_id:
                return
            candidate = {
                "product_id": str(pid),
                "confidence": float(confidence),
                "lift": float(lift),
                "support": float(support),
            }
            prev = candidates.get(str(pid))
            if prev is None:
                candidates[str(pid)] = candidate
                return
            prev_rank = (float(prev["lift"]), float(prev["confidence"]), float(prev["support"]))
            now_rank = (candidate["lift"], candidate["confidence"], candidate["support"])
            if now_rank > prev_rank:
                candidates[str(pid)] = candidate

        if self.rules_df is not None and not self.rules_df.empty:
            matched_forward = self.rules_df[self.rules_df["antecedents"].apply(lambda s: product_id in set(s))]
            for _, row in matched_forward.iterrows():
                for c in row["consequents"]:
                    _upsert_candidate(str(c), float(row["confidence"]), float(row["lift"]), float(row["support"]))

            matched_reverse = self.rules_df[self.rules_df["consequents"].apply(lambda s: product_id in set(s))]
            for _, row in matched_reverse.iterrows():
                consequent_support = float(row.get("consequent support", 0.0) or 0.0)
                reverse_confidence = float(row["support"]) / consequent_support if consequent_support > 0 else float(
                    row["confidence"]
                )
                for a in row["antecedents"]:
                    _upsert_candidate(str(a), reverse_confidence, float(row["lift"]), float(row["support"]))

        if (len(candidates) < top_k) and (self.fallback_pairs is not None) and (not self.fallback_pairs.empty):
            fallback = self.fallback_pairs[self.fallback_pairs["product_id_a"] == product_id]
            for _, row in fallback.head(max(top_k * 3, 30)).iterrows():
                _upsert_candidate(
                    str(row["product_id_b"]),
                    float(row.get("confidence", 0.0)),
                    float(row.get("lift", 0.0)),
                    float(row.get("support", 0.0)),
                )

        ordered = sorted(candidates.values(), key=lambda x: (x["lift"], x["confidence"], x["support"]), reverse=True)
        return ordered[:top_k]
