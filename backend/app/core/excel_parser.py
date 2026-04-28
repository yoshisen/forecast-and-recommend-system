"""
Excel Parser - Sheet識別、フィールド標準化、型推論
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import re
from datetime import datetime
import logging

from app.core.upload_schema_catalog import SHEET_ALIAS_CATALOG, build_parser_field_mappings

logger = logging.getLogger(__name__)


class SheetMapper:
    """Sheet名を標準名にマッピング"""

    SHEET_MAPPINGS = SHEET_ALIAS_CATALOG
    
    @classmethod
    def normalize_sheet_name(cls, sheet_name: str) -> str:
        """シート名を標準化"""
        # 空白、下線、ハイフンを削除して小文字化
        normalized = re.sub(r'[\s_-]', '', sheet_name.lower())
        return normalized
    
    @classmethod
    def identify_sheet(cls, sheet_name: str) -> Optional[str]:
        """シート名から標準名を識別"""
        normalized = cls.normalize_sheet_name(sheet_name)
        
        for standard_name, aliases in cls.SHEET_MAPPINGS.items():
            if normalized in [cls.normalize_sheet_name(alias) for alias in aliases]:
                return standard_name
        
        return None


class FieldStandardizer:
    """フィールド名の標準化"""

    # Shared alias catalog keeps parser and upload-guide page aligned.
    FIELD_MAPPINGS = build_parser_field_mappings()
    
    @classmethod
    def normalize_field_name(cls, field_name: str) -> str:
        """フィールド名を標準化"""
        # 空白、ハイフンを下線に変換、小文字化
        normalized = field_name.strip().lower()
        normalized = re.sub(r'[\s-]', '_', normalized)
        # 複数の下線を1つに
        normalized = re.sub(r'_+', '_', normalized)
        # 前後の下線を削除
        normalized = normalized.strip('_')
        return normalized
    
    @classmethod
    def standardize_field(cls, field_name: str) -> str:
        """フィールド名を標準名に変換（可能な場合）"""
        normalized = cls.normalize_field_name(field_name)
        
        for standard_name, aliases in cls.FIELD_MAPPINGS.items():
            if normalized in [cls.normalize_field_name(alias) for alias in aliases]:
                return standard_name
        
        return normalized  # マッピング見つからない場合は正規化名を返す


class TypeInferrer:
    """データ型の推論"""
    
    @staticmethod
    def infer_date_column(series: pd.Series) -> Tuple[bool, Optional[str]]:
        """日付列を推論"""
        # 既にdatetime型の場合
        if pd.api.types.is_datetime64_any_dtype(series):
            return True, None
        
        # サンプルを取得
        sample = series.dropna().head(100)
        if len(sample) == 0:
            return False, None
        
        # 複数の日付フォーマットを試す
        date_formats = [
            '%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y',
            '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S',
            '%d-%m-%Y', '%d.%m.%Y'
        ]
        
        for fmt in date_formats:
            try:
                pd.to_datetime(sample, format=fmt, errors='raise')
                return True, fmt
            except:
                continue
        
        # フォーマット指定なしで試す
        try:
            pd.to_datetime(sample, errors='raise')
            return True, None
        except:
            return False, None
    
    @staticmethod
    def infer_numeric_column(series: pd.Series) -> bool:
        """数値列を推論"""
        if pd.api.types.is_numeric_dtype(series):
            return True
        
        # 文字列から数値変換を試す
        sample = series.dropna().head(100)
        if len(sample) == 0:
            return False
        
        try:
            pd.to_numeric(sample, errors='raise')
            return True
        except:
            return False
    
    @staticmethod
    def infer_categorical_column(series: pd.Series, threshold: float = 0.05) -> bool:
        """カテゴリ列を推論（ユニーク率が低い場合）"""
        if len(series) == 0:
            return False
        
        unique_ratio = series.nunique() / len(series)
        return unique_ratio < threshold


class ExcelParser:
    """Excel解析のメインクラス"""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.sheet_mapper = SheetMapper()
        self.field_standardizer = FieldStandardizer()
        self.type_inferrer = TypeInferrer()
        
        self.parsed_data: Dict[str, pd.DataFrame] = {}
        self.sheet_mapping: Dict[str, str] = {}  # original_name -> standard_name
        self.field_mappings: Dict[str, Dict[str, str]] = {}  # sheet -> {original: standard}
        self.parse_report: Dict[str, Any] = {}
    
    def parse(self) -> Dict[str, Any]:
        """Excel全体を解析"""
        logger.info(f"Parsing Excel file: {self.file_path}")
        
        try:
            # Excelファイルを読み込む
            excel_file = pd.ExcelFile(self.file_path)
            sheet_names = excel_file.sheet_names
            
            logger.info(f"Found {len(sheet_names)} sheets: {sheet_names}")
            
            # 各シートを処理
            for sheet_name in sheet_names:
                self._parse_sheet(excel_file, sheet_name)
            
            # 解析報告を生成
            self._generate_parse_report()
            
            return {
                'success': True,
                'parsed_data': self.parsed_data,
                'sheet_mapping': self.sheet_mapping,
                'field_mappings': self.field_mappings,
                'report': self.parse_report
            }
            
        except Exception as e:
            logger.error(f"Error parsing Excel: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'report': {}
            }
    
    def _parse_sheet(self, excel_file: pd.ExcelFile, sheet_name: str):
        """単一シートを解析"""
        # シート名を識別
        standard_name = self.sheet_mapper.identify_sheet(sheet_name)
        
        if standard_name is None:
            logger.warning(f"Unknown sheet: {sheet_name}, skipping")
            return
        
        logger.info(f"Parsing sheet '{sheet_name}' as '{standard_name}'")
        
        # データを読み込む
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        
        # 空行・空列を削除
        df = df.dropna(how='all', axis=0)
        df = df.dropna(how='all', axis=1)
        
        if df.empty:
            logger.warning(f"Sheet '{sheet_name}' is empty after cleaning")
            return
        
        # フィールド名を標準化
        field_mapping = {}
        new_columns = []
        for col in df.columns:
            standard_field = self.field_standardizer.standardize_field(str(col))
            field_mapping[col] = standard_field
            new_columns.append(standard_field)
        
        df.columns = new_columns
        
        # 型推論と変換
        df = self._infer_and_convert_types(df)
        
        # 保存
        self.parsed_data[standard_name] = df
        self.sheet_mapping[sheet_name] = standard_name
        self.field_mappings[standard_name] = field_mapping
        
        logger.info(f"Successfully parsed sheet '{sheet_name}': {len(df)} rows, {len(df.columns)} columns")
    
    def _infer_and_convert_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """型推論と変換"""
        # 日付としてのみ扱う候補名（列名判定優先）
        date_name_keywords = ("date", "time", "day", "timestamp")
        # 強制的に数値扱いしたい列（数量・金額系）
        numeric_preferred = {
            'quantity','sales_quantity','purchase_count','line_total','line_total_jpy',
            'unit_price','unit_price_jpy','discount_price_jpy','original_price_jpy',
            'total_amount','total_amount_jpy','tax_amount_jpy','discount_amount_jpy',
            'retail_price_jpy','cost_price_jpy','item_margin_jpy',
            'stock_quantity','reorder_point','max_stock_level',
            'weight_g','average_foot_traffic','store_size_sqm',
            'household_size','shelf_life_days','days_on_shelf','age',
            'avg_basket_size','avg_transaction_value_jpy','purchase_frequency',
            'days_since_last_purchase','promotion_response_rate','churn_risk_score',
            'support','confidence','lift','co_purchase_count_30d',
            'waon_points_used','waon_points_earned'
        }
        for col in df.columns:
            series = df[col]
            col_lower = col.lower()

            # 1. 列名に日付/時間キーワードが含まれる場合のみ日付推論
            if any(k in col_lower for k in date_name_keywords):
                is_date, date_format = self.type_inferrer.infer_date_column(series)
                if is_date:
                    try:
                        df[col] = pd.to_datetime(series, format=date_format, errors='coerce')
                        logger.debug(f"Converted '{col}' to datetime (name matched)")
                        continue
                    except Exception:
                        pass

            # 2. それ以外はまず数値推論
            if col_lower in numeric_preferred or self.type_inferrer.infer_numeric_column(series):
                try:
                    df[col] = pd.to_numeric(series, errors='coerce')
                    logger.debug(f"Converted '{col}' to numeric")
                    continue
                except Exception:
                    pass

            # 3. 最後にカテゴリ推論
            if self.type_inferrer.infer_categorical_column(series):
                try:
                    df[col] = series.astype('category')
                    logger.debug(f"Converted '{col}' to category")
                except Exception:
                    pass

        # 安全策: datetime になってしまった数量系を再度数値へ（pandas2.0 の sum() 対策）
        for col in df.columns:
            if col.lower() in numeric_preferred and pd.api.types.is_datetime64_any_dtype(df[col]):
                try:
                    df[col] = pd.to_numeric(df[col].view('int64'), errors='coerce')
                    logger.debug(f"Forced datetime column '{col}' back to numeric")
                except Exception:
                    pass
        return df
    
    def _generate_parse_report(self):
        """解析報告を生成"""
        self.parse_report = {
            'file_name': self.file_path.name,
            'file_size_mb': round(self.file_path.stat().st_size / (1024 * 1024), 2),
            'parse_timestamp': datetime.now().isoformat(),
            'total_sheets': len(self.sheet_mapping),
            'identified_sheets': list(self.parsed_data.keys()),
            'sheet_details': {}
        }
        
        for standard_name, df in self.parsed_data.items():
            self.parse_report['sheet_details'][standard_name] = {
                'rows': len(df),
                'columns': len(df.columns),
                'fields': list(df.columns),
                'memory_mb': round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2)
            }
