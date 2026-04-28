"""
Feature Engineering - 特徴生成エンジン
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class FeatureEngine:
    """特徴生成エンジン"""
    
    def __init__(self, parsed_data: Dict[str, pd.DataFrame]):
        self.parsed_data = parsed_data
        self.features_df = None
        
    def generate_forecast_features(self) -> pd.DataFrame:
        """予測用特徴を生成"""
        logger.info("Generating forecasting features")

        # transaction_items is the only hard requirement. Missing transaction sheet will degrade gracefully.
        if 'transaction_items' not in self.parsed_data:
            raise ValueError("transaction_items が必要です")

        items_df = self.parsed_data['transaction_items'].copy()
        trans_df = self.parsed_data.get('transaction')
        if trans_df is None:
            trans_df = pd.DataFrame()
            logger.warning("transaction sheet is missing; running degraded forecast feature generation")
        else:
            trans_df = trans_df.copy()

        # 型異常対策: 数量・金額・価格系が datetime64 に誤変換されている場合を数値へ戻す
        def _coerce_numeric(df_local, cols):
            for c in cols:
                if c in df_local.columns and pd.api.types.is_datetime64_any_dtype(df_local[c]):
                    try:
                        df_local[c] = pd.to_numeric(df_local[c].view('int64'), errors='coerce')
                    except Exception:
                        pass
        numeric_cols_candidates = [
            'quantity','unit_price','unit_price_jpy','discount_price_jpy','original_price_jpy',
            'line_total','line_total_jpy','total_amount','total_amount_jpy'
        ]
        _coerce_numeric(items_df, numeric_cols_candidates)
        _coerce_numeric(trans_df, numeric_cols_candidates)
        
        # Transaction と結合
        if 'transaction_id' in items_df.columns and 'transaction_id' in trans_df.columns:
            df = items_df.merge(trans_df, on='transaction_id', how='left', suffixes=('', '_trans'))
        else:
            df = items_df.copy()
        
        # Product 情報を結合
        if 'product' in self.parsed_data:
            product_df = self.parsed_data['product']
            if 'product_id' in df.columns and 'product_id' in product_df.columns:
                df = df.merge(product_df, on='product_id', how='left', suffixes=('', '_prod'))
        
        # Store 情報を結合
        if 'store' in self.parsed_data and 'store_id' in df.columns:
            store_df = self.parsed_data['store']
            if 'store_id' in store_df.columns:
                df = df.merge(store_df, on='store_id', how='left', suffixes=('', '_store'))
        
        # 日付列を特定
        date_col = self._find_date_column(df)
        if date_col:
            df['date'] = pd.to_datetime(df[date_col], errors='coerce')
        else:
            logger.warning("日付列が見つかりません")
            df['date'] = pd.Timestamp.now()
        
        # 時間特徴
        df = self._add_time_features(df)
        
        # 集計特徴（product × store × date）
        agg_df = self._aggregate_sales(df)
        
        # ラグ特徴
        agg_df = self._add_lag_features(agg_df)
        
        # ローリング統計
        agg_df = self._add_rolling_features(agg_df)
        
        # 価格特徴
        agg_df = self._add_price_features(agg_df, df)
        
        # プロモーション特徴
        if 'promotion' in self.parsed_data:
            agg_df = self._add_promotion_features(agg_df)
        
        # 天気特徴
        if 'weather' in self.parsed_data:
            agg_df = self._add_weather_features(agg_df)
        
        # 祝日特徴
        if 'holiday' in self.parsed_data:
            agg_df = self._add_holiday_features(agg_df)
        
        # 在庫特徴
        if 'inventory' in self.parsed_data:
            agg_df = self._add_inventory_features(agg_df)
        
        self.features_df = agg_df
        logger.info(f"Generated features: {len(agg_df)} rows, {len(agg_df.columns)} columns")
        
        return agg_df
    
    def _find_date_column(self, df: pd.DataFrame) -> Optional[str]:
        """日付列を探す"""
        date_candidates = [
            'transaction_date',
            'date',
            'order_date',
            'sale_date',
            'transaction_datetime',
            'transaction_timestamp',
            'event_timestamp',
            'last_purchase_date',
        ]
        for col in date_candidates:
            if col in df.columns:
                return col
        
        # datetime型の列を探す
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                return col
        
        return None
    
    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """時間特徴を追加"""
        if 'date' not in df.columns:
            return df
        
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['day'] = df['date'].dt.day
        df['dayofweek'] = df['date'].dt.dayofweek
        df['dayofyear'] = df['date'].dt.dayofyear
        df['week'] = df['date'].dt.isocalendar().week
        df['quarter'] = df['date'].dt.quarter
        df['is_weekend'] = (df['dayofweek'] >= 5).astype(int)
        df['is_month_start'] = df['date'].dt.is_month_start.astype(int)
        df['is_month_end'] = df['date'].dt.is_month_end.astype(int)
        
        return df
    
    def _aggregate_sales(self, df: pd.DataFrame) -> pd.DataFrame:
        """売上を集計（product × store × date）"""
        group_cols = []
        
        if 'product_id' in df.columns:
            group_cols.append('product_id')
        if 'store_id' in df.columns:
            group_cols.append('store_id')
        if 'date' in df.columns:
            group_cols.append('date')
        
        if not group_cols:
            raise ValueError("集計用のキー列が見つかりません")
        
        # 数量と金額を集計
        agg_dict = {}
        
        if 'quantity' in df.columns:
            agg_dict['quantity'] = 'sum'
        elif 'purchase_count' in df.columns:
            agg_dict['purchase_count'] = 'sum'
        
        if 'line_total' in df.columns:
            agg_dict['line_total'] = 'sum'
        elif 'line_total_jpy' in df.columns:
            agg_dict['line_total_jpy'] = 'sum'
        elif 'total_amount' in df.columns:
            agg_dict['total_amount'] = 'sum'
        elif 'total_amount_jpy' in df.columns:
            agg_dict['total_amount_jpy'] = 'sum'
        
        if 'unit_price' in df.columns:
            agg_dict['unit_price'] = 'mean'
        elif 'unit_price_jpy' in df.columns:
            agg_dict['unit_price_jpy'] = 'mean'
        elif 'retail_price_jpy' in df.columns:
            agg_dict['retail_price_jpy'] = 'mean'

        if not agg_dict:
            # Last fallback: keep at least one row per group so downstream steps can still run.
            df['_fallback_counter'] = 1
            agg_dict['_fallback_counter'] = 'sum'
        
        agg_df = df.groupby(group_cols).agg(agg_dict).reset_index()
        
        # カラム名を統一
        if 'line_total' in agg_df.columns:
            agg_df.rename(columns={'line_total': 'sales_amount'}, inplace=True)
        elif 'line_total_jpy' in agg_df.columns:
            agg_df.rename(columns={'line_total_jpy': 'sales_amount'}, inplace=True)
        elif 'total_amount' in agg_df.columns:
            agg_df.rename(columns={'total_amount': 'sales_amount'}, inplace=True)
        elif 'total_amount_jpy' in agg_df.columns:
            agg_df.rename(columns={'total_amount_jpy': 'sales_amount'}, inplace=True)
        
        if 'quantity' in agg_df.columns:
            agg_df.rename(columns={'quantity': 'sales_quantity'}, inplace=True)
        elif 'purchase_count' in agg_df.columns:
            agg_df.rename(columns={'purchase_count': 'sales_quantity'}, inplace=True)
        else:
            agg_df['sales_quantity'] = 1  # デフォルト
        
        # 時間特徴を再度追加
        if 'date' in agg_df.columns:
            agg_df = self._add_time_features(agg_df)
        
        return agg_df
    
    def _add_lag_features(self, df: pd.DataFrame, lags: List[int] = [1, 7, 14, 28]) -> pd.DataFrame:
        """ラグ特徴を追加"""
        if 'sales_quantity' not in df.columns or 'date' not in df.columns:
            return df
        
        # ソート
        sort_cols = ['product_id', 'store_id', 'date'] if 'product_id' in df.columns and 'store_id' in df.columns else ['date']
        df = df.sort_values(sort_cols)
        
        group_cols = ['product_id', 'store_id'] if 'product_id' in df.columns and 'store_id' in df.columns else []
        
        if group_cols:
            for lag in lags:
                df[f'lag_{lag}'] = df.groupby(group_cols)['sales_quantity'].shift(lag)
        else:
            for lag in lags:
                df[f'lag_{lag}'] = df['sales_quantity'].shift(lag)
        
        return df
    
    def _add_rolling_features(self, df: pd.DataFrame, windows: List[int] = [7, 14, 28]) -> pd.DataFrame:
        """ローリング統計特徴を追加"""
        if 'sales_quantity' not in df.columns:
            return df
        
        group_cols = ['product_id', 'store_id'] if 'product_id' in df.columns and 'store_id' in df.columns else []
        
        if group_cols:
            for window in windows:
                df[f'rolling_mean_{window}'] = df.groupby(group_cols)['sales_quantity'].transform(
                    lambda x: x.rolling(window=window, min_periods=1).mean()
                )
                df[f'rolling_std_{window}'] = df.groupby(group_cols)['sales_quantity'].transform(
                    lambda x: x.rolling(window=window, min_periods=1).std()
                )
                df[f'rolling_max_{window}'] = df.groupby(group_cols)['sales_quantity'].transform(
                    lambda x: x.rolling(window=window, min_periods=1).max()
                )
        
        return df
    
    def _add_price_features(self, agg_df: pd.DataFrame, detail_df: pd.DataFrame) -> pd.DataFrame:
        """価格関連特徴を追加"""
        price_cols = ['unit_price', 'unit_price_jpy', 'retail_price_jpy', 'discount_price_jpy', 'original_price_jpy']
        
        available_price_cols = [col for col in price_cols if col in detail_df.columns]
        
        if not available_price_cols:
            return agg_df
        
        # 価格統計を集計
        group_cols = [col for col in ['product_id', 'store_id', 'date'] if col in detail_df.columns]
        if 'date' not in group_cols:
            return agg_df
        if not all(col in agg_df.columns for col in group_cols):
            return agg_df
        
        if group_cols:
            price_stats = detail_df.groupby(group_cols).agg({
                col: ['mean', 'min', 'max'] for col in available_price_cols if col in detail_df.columns
            }).reset_index()
            
            # カラム名をフラット化
            price_stats.columns = ['_'.join(col).strip('_') if col[1] else col[0] for col in price_stats.columns]
            
            # マージ
            agg_df = agg_df.merge(price_stats, on=group_cols, how='left')
        
        return agg_df
    
    def _add_promotion_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """プロモーション特徴を追加"""
        promo_df = self.parsed_data['promotion']
        
        if 'date' not in df.columns:
            return df
        
        # 日付範囲でプロモーションを特定
        df['promotion_active'] = 0
        
        if 'start_date' in promo_df.columns and 'end_date' in promo_df.columns:
            for _, promo in promo_df.iterrows():
                start = pd.to_datetime(promo['start_date'])
                end = pd.to_datetime(promo['end_date'])
                mask = (df['date'] >= start) & (df['date'] <= end)
                df.loc[mask, 'promotion_active'] = 1
        
        return df
    
    def _add_weather_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """天気特徴を追加"""
        weather_df = self.parsed_data['weather']
        
        if 'date' not in df.columns or 'date' not in weather_df.columns:
            return df
        
        weather_df['date'] = pd.to_datetime(weather_df['date'], errors='coerce')
        
        # 都道府県または店舗位置でマージ
        merge_keys = ['date']
        if 'prefecture' in df.columns and 'prefecture' in weather_df.columns:
            merge_keys.append('prefecture')
        
        weather_features = weather_df[merge_keys + ['temperature_celsius', 'precipitation_mm', 'humidity_percent']].copy() if all(c in weather_df.columns for c in ['temperature_celsius', 'precipitation_mm']) else weather_df
        
        df = df.merge(weather_features, on=merge_keys, how='left')
        
        return df
    
    def _add_holiday_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """祝日特徴を追加"""
        holiday_df = self.parsed_data['holiday']

        holiday_date_col = 'date' if 'date' in holiday_df.columns else 'holiday_date' if 'holiday_date' in holiday_df.columns else None
        if 'date' not in df.columns or holiday_date_col is None:
            return df

        holiday_df['date'] = pd.to_datetime(holiday_df[holiday_date_col], errors='coerce')
        holiday_df['is_holiday'] = 1
        
        df = df.merge(holiday_df[['date', 'is_holiday']], on='date', how='left')
        df['is_holiday'] = df['is_holiday'].fillna(0).astype(int)
        
        return df
    
    def _add_inventory_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """在庫特徴を追加"""
        inv_df = self.parsed_data['inventory']
        
        # 最新の在庫情報を取得
        if 'product_id' in df.columns and 'product_id' in inv_df.columns:
            merge_cols = ['product_id']
            if 'store_id' in df.columns and 'store_id' in inv_df.columns:
                merge_cols.append('store_id')

            value_cols = [col for col in ['stock_quantity', 'reorder_point', 'max_stock_level'] if col in inv_df.columns]
            if not value_cols:
                return df

            inv_features = inv_df.groupby(merge_cols).agg({col: 'last' for col in value_cols}).reset_index()
            
            df = df.merge(inv_features, on=merge_cols, how='left')
        
        return df


class RecommendationFeatureEngine:
    """推薦用特徴生成"""
    
    def __init__(self, parsed_data: Dict[str, pd.DataFrame]):
        self.parsed_data = parsed_data
    
    def generate_user_item_matrix(self) -> Tuple[pd.DataFrame, Dict]:
        """User-Item 相互作用行列を生成"""
        logger.info("Generating user-item interaction matrix")
        
        # Transaction Items から顧客-商品の購買履歴を抽出
        if 'transaction_items' not in self.parsed_data or 'transaction' not in self.parsed_data:
            raise ValueError("transaction_items と transaction が必要です")
        
        items_df = self.parsed_data['transaction_items']
        trans_df = self.parsed_data['transaction']
        
        # 結合
        if 'transaction_id' in items_df.columns and 'transaction_id' in trans_df.columns:
            df = items_df.merge(trans_df[['transaction_id', 'customer_id']], on='transaction_id', how='left')
        else:
            raise ValueError("transaction_id が見つかりません")

        if 'quantity' not in df.columns:
            # Degrade gracefully: use transaction count when quantity is missing.
            df['quantity'] = 1
        
        # 顧客×商品の購買回数を集計
        if 'customer_id' not in df.columns or 'product_id' not in df.columns:
            raise ValueError("customer_id または product_id が見つかりません")
        
        interaction_df = df.groupby(['customer_id', 'product_id']).agg({
            'quantity': 'sum',
            'transaction_id': 'count'
        }).reset_index()
        
        interaction_df.rename(columns={'transaction_id': 'purchase_count'}, inplace=True)

        # 安全策: quantity / purchase_count が datetime64 の場合は数値に戻す
        for c in ['quantity','purchase_count']:
            if c in interaction_df.columns and pd.api.types.is_datetime64_any_dtype(interaction_df[c]):
                try:
                    interaction_df[c] = pd.to_numeric(interaction_df[c].view('int64'), errors='coerce')
                except Exception:
                    pass
        
        # スパース行列に変換するための情報
        matrix_info = {
            'n_users': interaction_df['customer_id'].nunique(),
            'n_items': interaction_df['product_id'].nunique(),
            'n_interactions': len(interaction_df)
        }
        
        logger.info(f"Matrix: {matrix_info['n_users']} users × {matrix_info['n_items']} items, {matrix_info['n_interactions']} interactions")
        
        return interaction_df, matrix_info
    
    def generate_product_features(self) -> pd.DataFrame:
        """商品特徴を生成（コンテンツベース推薦用）"""
        if 'product' not in self.parsed_data:
            raise ValueError("product テーブルが必要です")
        
        product_df = self.parsed_data['product'].copy()
        
        # カテゴリ特徴
        category_cols = [col for col in product_df.columns if 'category' in col.lower()]
        
        # 価格帯
        if 'retail_price_jpy' in product_df.columns:
            product_df['price_range'] = pd.cut(
                product_df['retail_price_jpy'],
                bins=[0, 500, 1000, 2000, 5000, float('inf')],
                labels=['very_cheap', 'cheap', 'medium', 'expensive', 'very_expensive']
            )
        
        return product_df
