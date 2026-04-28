"""
Data Quality Checker - データ質量分析と報告生成
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DataQualityChecker:
    """データ質量チェッカー"""
    
    def __init__(self, parsed_data: Dict[str, pd.DataFrame], config: Optional[Dict] = None):
        self.parsed_data = parsed_data
        self.config = config or {
            'missing_rate_warning': 0.30,
            'missing_rate_critical': 0.60,
            'outlier_std_threshold': 3.0
        }
        
        self.quality_report: Dict[str, Any] = {}
    
    def generate_report(self) -> Dict[str, Any]:
        """質量報告を生成"""
        logger.info("Generating data quality report")
        
        self.quality_report = {
            'timestamp': datetime.now().isoformat(),
            'overall_summary': self._generate_overall_summary(),
            'sheet_reports': {},
            'issues': [],
            'recommendations': []
        }
        
        # 各シートの質量分析
        for sheet_name, df in self.parsed_data.items():
            self.quality_report['sheet_reports'][sheet_name] = self._analyze_sheet(sheet_name, df)
        
        # 全体的な問題と推奨事項
        self._generate_issues_and_recommendations()
        
        return self.quality_report
    
    def _generate_overall_summary(self) -> Dict[str, Any]:
        """全体サマリー"""
        total_rows = sum(len(df) for df in self.parsed_data.values())
        total_fields = sum(len(df.columns) for df in self.parsed_data.values())
        
        return {
            'total_sheets': len(self.parsed_data),
            'total_rows': total_rows,
            'total_fields': total_fields,
            'sheets_available': list(self.parsed_data.keys())
        }
    
    def _analyze_sheet(self, sheet_name: str, df: pd.DataFrame) -> Dict[str, Any]:
        """シート単位の分析"""
        report = {
            'row_count': len(df),
            'column_count': len(df.columns),
            'field_analysis': {},
            'data_range': {},
            'duplicates': {},
            'anomalies': {}
        }
        
        # フィールド分析
        for col in df.columns:
            report['field_analysis'][col] = self._analyze_field(df[col])
        
        # データ範囲（日付列がある場合）
        date_cols = df.select_dtypes(include=['datetime64']).columns
        if len(date_cols) > 0:
            for col in date_cols:
                report['data_range'][col] = {
                    'min': df[col].min().isoformat() if pd.notna(df[col].min()) else None,
                    'max': df[col].max().isoformat() if pd.notna(df[col].max()) else None,
                    'span_days': (df[col].max() - df[col].min()).days if pd.notna(df[col].max()) and pd.notna(df[col].min()) else None
                }
        
        # 重複チェック（主キー候補）
        report['duplicates'] = self._check_duplicates(df, sheet_name)
        
        # 異常値検出（数値列）
        report['anomalies'] = self._detect_anomalies(df)
        
        return report
    
    def _analyze_field(self, series: pd.Series) -> Dict[str, Any]:
        """フィールド単位の分析"""
        total = len(series)
        missing = series.isna().sum()
        missing_rate = missing / total if total > 0 else 0
        
        analysis = {
            'dtype': str(series.dtype),
            'total_count': total,
            'missing_count': int(missing),
            'missing_rate': round(missing_rate, 4),
            'non_null_count': int(total - missing),
            'unique_count': int(series.nunique()),
            'unique_rate': round(series.nunique() / total, 4) if total > 0 else 0
        }
        
        # 数値列の統計
        if pd.api.types.is_numeric_dtype(series):
            analysis['statistics'] = {
                'mean': float(series.mean()) if not series.isna().all() else None,
                'median': float(series.median()) if not series.isna().all() else None,
                'std': float(series.std()) if not series.isna().all() else None,
                'min': float(series.min()) if not series.isna().all() else None,
                'max': float(series.max()) if not series.isna().all() else None,
                'negative_count': int((series < 0).sum()),
                'zero_count': int((series == 0).sum())
            }
        
        # カテゴリ列のトップ値
        elif series.dtype == 'category' or series.dtype == 'object':
            value_counts = series.value_counts().head(10)
            analysis['top_values'] = {
                str(k): int(v) for k, v in value_counts.items()
            }
        
        # 質量レベル
        if missing_rate >= self.config['missing_rate_critical']:
            analysis['quality_level'] = 'critical'
        elif missing_rate >= self.config['missing_rate_warning']:
            analysis['quality_level'] = 'warning'
        else:
            analysis['quality_level'] = 'good'
        
        return analysis
    
    def _check_duplicates(self, df: pd.DataFrame, sheet_name: str) -> Dict[str, Any]:
        """重複チェック"""
        result = {
            'total_duplicates': 0,
            'duplicate_rate': 0.0,
            'key_candidates': {}
        }
        
        # 全行の重複
        duplicates = df.duplicated()
        result['total_duplicates'] = int(duplicates.sum())
        result['duplicate_rate'] = round(duplicates.sum() / len(df), 4) if len(df) > 0 else 0
        
        # ID列候補のチェック
        id_candidates = [col for col in df.columns if 'id' in col.lower()]
        
        for col in id_candidates:
            duplicates_in_col = df[col].duplicated()
            if duplicates_in_col.sum() > 0:
                result['key_candidates'][col] = {
                    'duplicates': int(duplicates_in_col.sum()),
                    'is_unique': False
                }
            else:
                result['key_candidates'][col] = {
                    'duplicates': 0,
                    'is_unique': True
                }
        
        return result
    
    def _detect_anomalies(self, df: pd.DataFrame) -> Dict[str, Any]:
        """異常値検出"""
        anomalies = {}
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) == 0:
                continue
            
            # IQR方式
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = ((series < lower_bound) | (series > upper_bound)).sum()
            
            # Z-score方式
            if series.std() > 0:
                z_scores = np.abs((series - series.mean()) / series.std())
                z_outliers = (z_scores > self.config['outlier_std_threshold']).sum()
            else:
                z_outliers = 0
            
            if outliers > 0 or z_outliers > 0:
                anomalies[col] = {
                    'iqr_outliers': int(outliers),
                    'iqr_outlier_rate': round(outliers / len(series), 4),
                    'z_outliers': int(z_outliers),
                    'z_outlier_rate': round(z_outliers / len(series), 4),
                    'bounds': {
                        'lower': float(lower_bound),
                        'upper': float(upper_bound)
                    }
                }
        
        return anomalies
    
    def _generate_issues_and_recommendations(self):
        """問題点と推奨事項を生成"""
        issues = []
        recommendations = []
        
        # 必須シートのチェック
        required_sheets = ['transaction_items', 'product']
        missing_sheets = [s for s in required_sheets if s not in self.parsed_data]
        
        if missing_sheets:
            issues.append({
                'severity': 'critical',
                'category': 'missing_data',
                'message': f"必須シート不足: {', '.join(missing_sheets)}",
                'affected_sheets': missing_sheets
            })
            recommendations.append({
                'category': 'data_completeness',
                'message': f"{', '.join(missing_sheets)} シートを追加してください"
            })
        
        # 欠損率の高いフィールド
        for sheet_name, sheet_report in self.quality_report['sheet_reports'].items():
            for field, field_info in sheet_report['field_analysis'].items():
                if field_info['quality_level'] == 'critical':
                    issues.append({
                        'severity': 'warning',
                        'category': 'high_missing_rate',
                        'message': f"{sheet_name}.{field}: 欠損率 {field_info['missing_rate']:.1%}",
                        'sheet': sheet_name,
                        'field': field,
                        'missing_rate': field_info['missing_rate']
                    })
                    recommendations.append({
                        'category': 'data_quality',
                        'message': f"{sheet_name}.{field} の欠損データを確認・補完するか、除外を検討してください"
                    })
        
        # 重複主キー
        for sheet_name, sheet_report in self.quality_report['sheet_reports'].items():
            for key_col, key_info in sheet_report['duplicates'].get('key_candidates', {}).items():
                if not key_info['is_unique'] and key_info['duplicates'] > 0:
                    issues.append({
                        'severity': 'warning',
                        'category': 'duplicate_keys',
                        'message': f"{sheet_name}.{key_col}: {key_info['duplicates']} 件の重複",
                        'sheet': sheet_name,
                        'field': key_col,
                        'duplicates': key_info['duplicates']
                    })
        
        # 異常値
        for sheet_name, sheet_report in self.quality_report['sheet_reports'].items():
            for field, anomaly_info in sheet_report['anomalies'].items():
                if anomaly_info['iqr_outlier_rate'] > 0.05:  # 5%以上
                    issues.append({
                        'severity': 'info',
                        'category': 'anomalies',
                        'message': f"{sheet_name}.{field}: 異常値 {anomaly_info['iqr_outlier_rate']:.1%}",
                        'sheet': sheet_name,
                        'field': field,
                        'outlier_rate': anomaly_info['iqr_outlier_rate']
                    })
        
        self.quality_report['issues'] = issues
        self.quality_report['recommendations'] = recommendations


class DataValidator:
    """データバリデーション"""
    
    @staticmethod
    def validate_required_fields(df: pd.DataFrame, required_fields: List[str]) -> Dict[str, Any]:
        """必須フィールドの検証"""
        missing_fields = [f for f in required_fields if f not in df.columns]
        
        return {
            'is_valid': len(missing_fields) == 0,
            'missing_fields': missing_fields
        }
    
    @staticmethod
    def validate_date_range(df: pd.DataFrame, date_col: str, min_days: int = 90) -> Dict[str, Any]:
        """日付範囲の検証"""
        if date_col not in df.columns:
            return {'is_valid': False, 'error': f"列 '{date_col}' が見つかりません"}
        
        date_series = pd.to_datetime(df[date_col], errors='coerce')
        date_series = date_series.dropna()
        
        if len(date_series) == 0:
            return {'is_valid': False, 'error': '有効な日付がありません'}
        
        date_range = (date_series.max() - date_series.min()).days
        
        return {
            'is_valid': date_range >= min_days,
            'date_range_days': date_range,
            'min_required_days': min_days,
            'start_date': date_series.min().isoformat(),
            'end_date': date_series.max().isoformat()
        }
    
    @staticmethod
    def validate_relationships(parsed_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """テーブル間の関係性を検証"""
        validation_results = {
            'is_valid': True,
            'checks': []
        }
        
        # Transaction Items -> Product
        if 'transaction_items' in parsed_data and 'product' in parsed_data:
            items_df = parsed_data['transaction_items']
            product_df = parsed_data['product']
            
            if 'product_id' in items_df.columns and 'product_id' in product_df.columns:
                items_products = set(items_df['product_id'].unique())
                master_products = set(product_df['product_id'].unique())
                missing_products = items_products - master_products
                
                validation_results['checks'].append({
                    'relationship': 'transaction_items -> product',
                    'is_valid': len(missing_products) == 0,
                    'missing_count': len(missing_products),
                    'message': f"{len(missing_products)} 件の商品IDが商品マスタに存在しません" if missing_products else "OK"
                })
                
                if len(missing_products) > 0:
                    validation_results['is_valid'] = False
        
        # Transaction Items -> Customer
        if 'transaction' in parsed_data and 'customer' in parsed_data:
            trans_df = parsed_data['transaction']
            customer_df = parsed_data['customer']
            
            if 'customer_id' in trans_df.columns and 'customer_id' in customer_df.columns:
                trans_customers = set(trans_df['customer_id'].unique())
                master_customers = set(customer_df['customer_id'].unique())
                missing_customers = trans_customers - master_customers
                
                validation_results['checks'].append({
                    'relationship': 'transaction -> customer',
                    'is_valid': len(missing_customers) == 0,
                    'missing_count': len(missing_customers),
                    'message': f"{len(missing_customers)} 件の顧客IDが顧客マスタに存在しません" if missing_customers else "OK"
                })
        
        return validation_results
