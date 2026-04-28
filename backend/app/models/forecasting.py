"""
Forecasting Models - 販売予測モデル
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
import lightgbm as lgb
import logging
import pickle
from pathlib import Path

try:
    from xgboost import XGBRegressor  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional runtime dependency guard
    XGBRegressor = None

try:
    from statsmodels.tsa.statespace.sarimax import SARIMAX  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional runtime dependency guard
    SARIMAX = None

logger = logging.getLogger(__name__)


class BaselineForecaster:
    """ベースライン予測モデル（移動平均）"""
    
    def __init__(self, window: int = 7):
        self.window = window
        self.history = {}
    
    def fit(self, df: pd.DataFrame, target_col: str = 'sales_quantity'):
        """学習"""
        if 'product_id' in df.columns and 'store_id' in df.columns:
            for (product_id, store_id), group in df.groupby(['product_id', 'store_id']):
                key = (product_id, store_id)
                self.history[key] = group[target_col].tail(self.window).mean()
        else:
            self.history['global'] = df[target_col].tail(self.window).mean()
        
        return self
    
    def predict(self, product_id: Optional[str] = None, store_id: Optional[str] = None, 
                horizon: int = 14) -> np.ndarray:
        """予測"""
        key = (product_id, store_id) if product_id and store_id else 'global'
        
        if key in self.history:
            prediction = self.history[key]
        elif 'global' in self.history:
            prediction = self.history['global']
        else:
            prediction = 0
        
        return np.array([prediction] * horizon)


class LightGBMForecaster:
    """LightGBM 予測モデル"""
    
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {
            'objective': 'regression',
            'metric': 'rmse',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1
        }
        self.model = None
        self.feature_names = None
        self.feature_importance = None
    
    def prepare_features(self, df: pd.DataFrame, target_col: str = 'sales_quantity') -> Tuple[pd.DataFrame, pd.Series]:
        """特徴量を準備"""
        # 除外するカラム
        exclude_cols = [target_col, 'date', 'product_id', 'store_id', 'customer_id', 
                       'transaction_id', 'product_name', 'store_name']
        
        # 数値型と整数型のカラムのみ使用
        feature_cols = []
        for col in df.columns:
            if col not in exclude_cols:
                if pd.api.types.is_numeric_dtype(df[col]):
                    feature_cols.append(col)
        
        X = df[feature_cols].fillna(0)
        y = df[target_col].fillna(0)
        
        self.feature_names = feature_cols
        
        return X, y
    
    def fit(self, df: pd.DataFrame, target_col: str = 'sales_quantity', 
            test_size: float = 0.2, n_estimators: int = 100):
        """学習"""
        logger.info("Training LightGBM model")
        
        X, y = self.prepare_features(df, target_col)
        
        # 時系列なので順序を保持して分割
        split_idx = int(len(X) * (1 - test_size))
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        
        # データセット作成
        train_data = lgb.Dataset(X_train, label=y_train)
        valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)
        
        # 学習
        self.model = lgb.train(
            self.params,
            train_data,
            num_boost_round=n_estimators,
            valid_sets=[valid_data],
            callbacks=[lgb.early_stopping(stopping_rounds=10), lgb.log_evaluation(period=0)]
        )
        
        # 特徴重要度
        self.feature_importance = dict(zip(self.feature_names, self.model.feature_importance()))
        
        # 評価
        y_pred = self.model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        
        # MAPEは0除算を避ける
        mask = y_test > 0
        if mask.sum() > 0:
            mape = mean_absolute_percentage_error(y_test[mask], y_pred[mask])
        else:
            mape = 0
        
        metrics = {
            'mae': mae,
            'rmse': rmse,
            'mape': mape
        }
        
        logger.info("Model metrics: MAE=%.2f, RMSE=%.2f, MAPE=%.2f%%", mae, rmse, mape * 100)
        
        return metrics
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """予測"""
        if self.model is None:
            raise ValueError("モデルが学習されていません")
        
        # 特徴量を揃える
        X_aligned = X[self.feature_names].fillna(0)
        
        return self.model.predict(X_aligned)
    
    def save(self, path: Path):
        """モデル保存"""
        with open(path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'feature_names': self.feature_names,
                'feature_importance': self.feature_importance,
                'params': self.params
            }, f)
        logger.info("Model saved to %s", path)
    
    def load(self, path: Path):
        """モデル読み込み"""
        with open(path, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.feature_names = data['feature_names']
            self.feature_importance = data['feature_importance']
            self.params = data['params']
        logger.info("Model loaded from %s", path)


class ForecastingPipeline:
    """予測パイプライン（階層化戦略）"""
    
    def __init__(self, features_df: pd.DataFrame):
        self.features_df = features_df
        self.baseline_model = BaselineForecaster()
        self.lgbm_model = LightGBMForecaster()
        self.xgb_model = None
        self.xgb_feature_names: List[str] = []
        self.xgb_metrics: Dict[str, float] = {}
        self.metrics = {}

    @staticmethod
    def _latest_anchor_date(df: pd.DataFrame) -> pd.Timestamp:
        if 'date' not in df.columns or df.empty:
            return pd.Timestamp.now().floor('D')

        parsed = pd.to_datetime(df['date'], errors='coerce').dropna()
        if parsed.empty:
            return pd.Timestamp.now().floor('D')

        return parsed.max().floor('D')

    def _build_recursive_feature_row(
        self,
        base_row: pd.DataFrame,
        future_date: pd.Timestamp,
        history_values: List[float],
    ) -> pd.DataFrame:
        row = base_row.copy()

        if 'date' in row.columns:
            row.loc[:, 'date'] = future_date

        date_features = {
            'year': future_date.year,
            'month': future_date.month,
            'day': future_date.day,
            'dayofweek': future_date.dayofweek,
            'dayofyear': future_date.dayofyear,
            'week': int(future_date.isocalendar().week),
            'quarter': future_date.quarter,
            'is_weekend': int(future_date.dayofweek >= 5),
            'is_month_start': int(future_date.is_month_start),
            'is_month_end': int(future_date.is_month_end),
        }
        for col, value in date_features.items():
            if col in row.columns:
                row.loc[:, col] = value

        for lag in [1, 7, 14, 28]:
            col = f'lag_{lag}'
            if col not in row.columns:
                continue

            if len(history_values) >= lag:
                lag_value = history_values[-lag]
            elif history_values:
                lag_value = history_values[-1]
            else:
                lag_value = 0.0
            row.loc[:, col] = float(lag_value)

        for window in [7, 14, 28]:
            if history_values:
                recent = np.array(history_values[-window:], dtype=float)
            else:
                recent = np.array([0.0], dtype=float)

            mean_col = f'rolling_mean_{window}'
            std_col = f'rolling_std_{window}'
            max_col = f'rolling_max_{window}'

            if mean_col in row.columns:
                row.loc[:, mean_col] = float(recent.mean())
            if std_col in row.columns:
                row.loc[:, std_col] = float(recent.std(ddof=0))
            if max_col in row.columns:
                row.loc[:, max_col] = float(recent.max())

        if 'promotion_active' in row.columns:
            row.loc[:, 'promotion_active'] = 0

        if 'is_holiday' in row.columns and 'is_weekend' in row.columns:
            row.loc[:, 'is_holiday'] = int(row['is_weekend'].iloc[0])

        return row

    def _extract_pair_df(self, product_id: str, store_id: str) -> Tuple[pd.DataFrame, pd.Timestamp]:
        if 'product_id' in self.features_df.columns and 'store_id' in self.features_df.columns:
            pair_df = self.features_df[
                (self.features_df['product_id'] == product_id) &
                (self.features_df['store_id'] == store_id)
            ].copy()
        else:
            pair_df = self.features_df.copy()

        anchor_date = self._latest_anchor_date(self.features_df)
        if pair_df.empty:
            return pair_df, anchor_date

        if 'date' in pair_df.columns:
            pair_df = pair_df.copy()
            pair_df['_date_sort'] = pd.to_datetime(pair_df['date'], errors='coerce')
            pair_df = pair_df.sort_values('_date_sort').drop(columns=['_date_sort'])
            anchor_date = self._latest_anchor_date(pair_df)

        return pair_df, anchor_date

    def _extract_history_values(self, pair_df: pd.DataFrame, latest_data: pd.DataFrame) -> List[float]:
        history_col = 'sales_quantity' if 'sales_quantity' in pair_df.columns else None
        if history_col is None and 'quantity' in pair_df.columns:
            history_col = 'quantity'
        if history_col is None and 'sales_amount' in pair_df.columns:
            history_col = 'sales_amount'

        if history_col is not None:
            history_values = pd.to_numeric(pair_df[history_col], errors='coerce').dropna().astype(float).tolist()
        else:
            history_values = []

        if not history_values:
            fallback_value = float(
                pd.to_numeric(latest_data.get('sales_quantity', pd.Series([0])), errors='coerce').fillna(0).iloc[0]
            )
            history_values = [fallback_value]

        return history_values

    def _predict_with_xgboost(self, row: pd.DataFrame) -> float:
        if self.xgb_model is None or not self.xgb_feature_names:
            raise ValueError("xgboost model is not trained")

        aligned = row.reindex(columns=self.xgb_feature_names, fill_value=0)
        aligned = aligned.apply(pd.to_numeric, errors='coerce').fillna(0)
        return float(self.xgb_model.predict(aligned)[0])

    def _recursive_forecast(
        self,
        latest_data: pd.DataFrame,
        history_values: List[float],
        anchor_date: pd.Timestamp,
        horizon: int,
        algorithm: str,
    ) -> np.ndarray:
        predictions = []
        current_row = latest_data.copy()

        for idx in range(horizon):
            future_date = anchor_date + pd.Timedelta(days=idx + 1)
            current_row = self._build_recursive_feature_row(current_row, future_date, history_values)

            if algorithm == 'xgboost':
                pred = self._predict_with_xgboost(current_row)
            else:
                pred = float(self.lgbm_model.predict(current_row)[0])

            pred = max(0.0, pred)
            predictions.append(pred)
            history_values.append(pred)

        return np.asarray(predictions, dtype=float)

    def _forecast_with_sarima(self, pair_df: pd.DataFrame, horizon: int) -> np.ndarray:
        if SARIMAX is None:
            raise ValueError("SARIMA を使用するには statsmodels のインストールが必要です")

        history_col = 'sales_quantity' if 'sales_quantity' in pair_df.columns else None
        if history_col is None and 'quantity' in pair_df.columns:
            history_col = 'quantity'
        if history_col is None and 'sales_amount' in pair_df.columns:
            history_col = 'sales_amount'

        if history_col is None:
            raise ValueError("SARIMA 用の時系列列が見つかりません")

        series = pd.to_numeric(pair_df[history_col], errors='coerce').dropna().astype(float)
        if len(series) < 10:
            raise ValueError("SARIMA に必要な履歴データが不足しています")

        if len(series) >= 21:
            model = SARIMAX(
                series,
                order=(1, 1, 1),
                seasonal_order=(1, 1, 1, 7),
                enforce_stationarity=False,
                enforce_invertibility=False,
            )
        else:
            model = SARIMAX(
                series,
                order=(1, 1, 1),
                enforce_stationarity=False,
                enforce_invertibility=False,
            )

        fitted = model.fit(disp=False)
        predictions = np.asarray(fitted.forecast(steps=horizon), dtype=float)

        fallback_value = float(series.iloc[-1]) if len(series) else 0.0
        predictions = np.nan_to_num(predictions, nan=fallback_value, posinf=fallback_value, neginf=0.0)
        predictions = np.clip(predictions, 0.0, None)
        return predictions
    
    def train(self, target_col: str = 'sales_quantity'):
        """学習"""
        logger.info("Training forecasting pipeline")
        
        # データを準備
        df = self.features_df.copy()
        
        # 欠損値を含む行を削除
        df = df.dropna(subset=[target_col])
        
        if len(df) < 100:
            logger.warning("データ量が少ない: %s行", len(df))
        
        # ベースラインモデル
        self.baseline_model.fit(df, target_col)
        
        # LightGBMモデル
        self.metrics = self.lgbm_model.fit(df, target_col)

        # XGBoostモデル（任意）
        self.xgb_model = None
        self.xgb_feature_names = []
        self.xgb_metrics = {}

        if XGBRegressor is not None:
            X, y = self.lgbm_model.prepare_features(df, target_col)
            if not X.empty and X.shape[1] > 0 and len(X) > 12:
                split_idx = int(len(X) * 0.8)
                split_idx = max(1, min(split_idx, len(X) - 1))

                X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
                y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

                self.xgb_model = XGBRegressor(
                    objective='reg:squarederror',
                    n_estimators=220,
                    max_depth=6,
                    learning_rate=0.05,
                    subsample=0.85,
                    colsample_bytree=0.85,
                    random_state=42,
                )
                self.xgb_model.fit(X_train, y_train, verbose=False)
                self.xgb_feature_names = list(X.columns)

                xgb_pred = self.xgb_model.predict(X_test)
                xgb_mae = mean_absolute_error(y_test, xgb_pred)
                xgb_rmse = np.sqrt(mean_squared_error(y_test, xgb_pred))

                mask = y_test > 0
                if mask.sum() > 0:
                    xgb_mape = mean_absolute_percentage_error(y_test[mask], xgb_pred[mask])
                else:
                    xgb_mape = 0.0

                self.xgb_metrics = {
                    'mae': float(xgb_mae),
                    'rmse': float(xgb_rmse),
                    'mape': float(xgb_mape),
                }
                self.metrics['xgboost_metrics'] = self.xgb_metrics
            else:
                logger.warning("XGBoost training skipped due to insufficient feature rows")
        else:
            logger.warning("xgboost is unavailable; xgboost forecast will fallback to baseline")
        
        logger.info("Training completed")
        
        return self.metrics
    
    def forecast(
        self,
        product_id: str,
        store_id: str,
        horizon: int = 14,
        use_baseline: bool = False,
        algorithm: str = 'lightgbm',
    ) -> Dict[str, Any]:
        """予測実行"""
        requested_algorithm = (algorithm or 'lightgbm').lower().strip()
        if use_baseline:
            requested_algorithm = 'baseline'

        allowed_algorithms = {'lightgbm', 'xgboost', 'sarima', 'baseline'}
        if requested_algorithm not in allowed_algorithms:
            raise ValueError(f"unsupported forecast algorithm: {requested_algorithm}")

        pair_df, anchor_date = self._extract_pair_df(product_id, store_id)

        def _baseline_prediction(method_name: str) -> Tuple[np.ndarray, str, str]:
            preds = self.baseline_model.predict(product_id, store_id, horizon)
            return np.asarray(preds, dtype=float), method_name, 'baseline'

        if requested_algorithm == 'baseline':
            predictions, method, effective_algorithm = _baseline_prediction('baseline')
        elif pair_df.empty:
            if requested_algorithm == 'xgboost':
                predictions, method, effective_algorithm = _baseline_prediction('xgboost_baseline_fallback')
            elif requested_algorithm == 'sarima':
                predictions, method, effective_algorithm = _baseline_prediction('sarima_baseline_fallback')
            else:
                predictions, method, effective_algorithm = _baseline_prediction('baseline_fallback')
        elif requested_algorithm == 'sarima':
            try:
                predictions = self._forecast_with_sarima(pair_df, horizon)
                method = 'sarima'
                effective_algorithm = 'sarima'
            except (ValueError, RuntimeError, TypeError, np.linalg.LinAlgError) as e:
                logger.warning("SARIMA forecast failed; fallback to baseline: %s", str(e))
                predictions, method, effective_algorithm = _baseline_prediction('sarima_fallback_baseline')
        else:
            latest_data = pair_df.tail(1).copy()
            history_values = self._extract_history_values(pair_df, latest_data)

            if requested_algorithm == 'xgboost':
                if self.xgb_model is None:
                    predictions, method, effective_algorithm = _baseline_prediction('xgboost_model_unavailable_baseline')
                else:
                    predictions = self._recursive_forecast(
                        latest_data=latest_data,
                        history_values=history_values,
                        anchor_date=anchor_date,
                        horizon=horizon,
                        algorithm='xgboost',
                    )
                    method = 'xgboost_recursive'
                    effective_algorithm = 'xgboost'
            else:
                predictions = self._recursive_forecast(
                    latest_data=latest_data,
                    history_values=history_values,
                    anchor_date=anchor_date,
                    horizon=horizon,
                    algorithm='lightgbm',
                )
                method = 'lightgbm_recursive'
                effective_algorithm = 'lightgbm'

        predictions = np.asarray(predictions, dtype=float)
        
        # 日付範囲を生成
        forecast_dates = pd.date_range(start=anchor_date + pd.Timedelta(days=1), periods=horizon)
        
        return {
            'product_id': product_id,
            'store_id': store_id,
            'requested_algorithm': requested_algorithm,
            'algorithm': effective_algorithm,
            'method': method,
            'horizon': horizon,
            'predictions': predictions.tolist(),
            'dates': [d.strftime('%Y-%m-%d') for d in forecast_dates],
            'total_forecast': float(predictions.sum()),
            'avg_daily_forecast': float(predictions.mean())
        }
    
    def batch_forecast(self, pairs: List[Tuple[str, str]], horizon: int = 14) -> List[Dict]:
        """バッチ予測"""
        results = []
        for product_id, store_id in pairs:
            try:
                result = self.forecast(product_id, store_id, horizon)
                results.append(result)
            except (ValueError, RuntimeError, TypeError, KeyError) as e:
                logger.error("Error forecasting %s, %s: %s", product_id, store_id, str(e))
                results.append({
                    'product_id': product_id,
                    'store_id': store_id,
                    'error': str(e)
                })
        
        return results
    
    def save(self, model_dir: Path):
        """モデル保存"""
        model_dir.mkdir(parents=True, exist_ok=True)
        self.lgbm_model.save(model_dir / 'lgbm_model.pkl')
        
        # メタデータ
        with open(model_dir / 'metadata.pkl', 'wb') as f:
            pickle.dump({
                'metrics': self.metrics,
                'feature_names': self.lgbm_model.feature_names
            }, f)
    
    def load(self, model_dir: Path):
        """モデル読み込み"""
        self.lgbm_model.load(model_dir / 'lgbm_model.pkl')
        
        with open(model_dir / 'metadata.pkl', 'rb') as f:
            data = pickle.load(f)
            self.metrics = data['metrics']
