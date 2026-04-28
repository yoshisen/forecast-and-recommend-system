"""Tabular upload parser for CSV and ZIP files."""
from __future__ import annotations

from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional
import io
import logging
import zipfile

import pandas as pd
from pandas.errors import EmptyDataError, ParserError

from app.core.excel_parser import FieldStandardizer, SheetMapper, TypeInferrer


logger = logging.getLogger(__name__)


class TabularUploadParser:
    """Parse CSV/ZIP uploads into the same structure as ExcelParser."""

    CSV_ENCODINGS = ("utf-8-sig", "utf-8", "cp932", "shift_jis")
    DEFAULT_SHEET_SUGGESTIONS = ("transaction_items", "transaction", "product")

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.sheet_mapper = SheetMapper()
        self.field_standardizer = FieldStandardizer()
        self.type_inferrer = TypeInferrer()

        self.parsed_data: dict[str, pd.DataFrame] = {}
        self.sheet_mapping: dict[str, str] = {}
        self.field_mappings: dict[str, dict[str, str]] = {}
        self.parse_report: dict[str, Any] = {}
        self.skipped_files: list[str] = []
        self.skipped_file_hints: dict[str, list[str]] = {}

    def parse(self) -> dict[str, Any]:
        logger.info("Parsing tabular file: %s", self.file_path)

        try:
            file_ext = self.file_path.suffix.lower()
            if file_ext == ".csv":
                self._parse_single_csv()
            elif file_ext == ".zip":
                self._parse_zip_csv()
            else:
                raise ValueError(f"Unsupported tabular extension: {file_ext}")

            if not self.parsed_data:
                raise ValueError("No recognized CSV sheets were found in the uploaded file")

            self._generate_parse_report()
            return {
                "success": True,
                "parsed_data": self.parsed_data,
                "sheet_mapping": self.sheet_mapping,
                "field_mappings": self.field_mappings,
                "report": self.parse_report,
            }

        except (
            ValueError,
            RuntimeError,
            TypeError,
            AttributeError,
            OSError,
            zipfile.BadZipFile,
            EmptyDataError,
            ParserError,
            UnicodeDecodeError,
        ) as e:
            logger.error("Error parsing tabular file: %s", str(e), exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "report": {},
            }

    def _read_csv_bytes(self, raw_bytes: bytes) -> pd.DataFrame:
        last_error: Exception | None = None
        for encoding in self.CSV_ENCODINGS:
            try:
                return pd.read_csv(
                    io.BytesIO(raw_bytes),
                    encoding=encoding,
                    sep=None,
                    engine="python",
                )
            except (UnicodeDecodeError, ParserError, EmptyDataError, ValueError, TypeError) as e:  # pragma: no cover - fallback chain
                last_error = e

        raise ValueError(f"CSV parsing failed for supported encodings: {last_error}")

    def _identify_sheet_from_name(self, file_name: str) -> Optional[str]:
        stem = Path(file_name).stem

        exact = self.sheet_mapper.identify_sheet(stem)
        if exact:
            return exact

        normalized_stem = self.sheet_mapper.normalize_sheet_name(stem)
        best_match: tuple[int, int, str] | None = None
        for standard_name, aliases in self.sheet_mapper.SHEET_MAPPINGS.items():
            candidates = [standard_name, *aliases]
            for alias in candidates:
                normalized_alias = self.sheet_mapper.normalize_sheet_name(alias)
                rank = 0
                if normalized_stem == normalized_alias:
                    rank = 4
                elif normalized_stem.startswith(normalized_alias) or normalized_stem.endswith(normalized_alias):
                    rank = 3
                elif normalized_alias in normalized_stem:
                    rank = 2

                if rank == 0:
                    continue

                score = (rank, len(normalized_alias), standard_name)
                if best_match is None or score > best_match:
                    best_match = score

        if best_match is not None:
            return best_match[2]

        return None

    def _suggest_sheet_names(self, file_name: str, limit: int = 3) -> list[str]:
        stem = Path(file_name).stem
        normalized_stem = self.sheet_mapper.normalize_sheet_name(stem)
        if not normalized_stem:
            return [
                sheet_name
                for sheet_name in self.DEFAULT_SHEET_SUGGESTIONS
                if sheet_name in self.sheet_mapper.SHEET_MAPPINGS
            ][:limit]

        score_by_sheet: dict[str, float] = {}
        for standard_name, aliases in self.sheet_mapper.SHEET_MAPPINGS.items():
            candidates = [standard_name, *aliases]
            best_score = 0.0
            for alias in candidates:
                normalized_alias = self.sheet_mapper.normalize_sheet_name(alias)
                score = SequenceMatcher(None, normalized_stem, normalized_alias).ratio()
                if normalized_stem.startswith(normalized_alias) or normalized_stem.endswith(normalized_alias):
                    score += 0.35
                elif normalized_alias in normalized_stem:
                    score += 0.2
                best_score = max(best_score, score)

            if best_score >= 0.35:
                score_by_sheet[standard_name] = best_score

        ranked = sorted(score_by_sheet.items(), key=lambda x: (-x[1], x[0]))
        suggestions = [sheet_name for sheet_name, _ in ranked[:limit]]
        if suggestions:
            return suggestions

        fallback = [
            sheet_name
            for sheet_name in self.DEFAULT_SHEET_SUGGESTIONS
            if sheet_name in self.sheet_mapper.SHEET_MAPPINGS
        ]
        return fallback[:limit]

    def _parse_single_csv(self):
        standard_name = self._identify_sheet_from_name(self.file_path.name)
        if standard_name is None:
            suggestions = self._suggest_sheet_names(self.file_path.name)
            raise ValueError(
                f"CSVファイル名から標準シートを識別できません: {self.file_path.name}. "
                f"候補: {', '.join(suggestions)}. "
                f"推奨形式: <sheet_name>.csv"
            )

        raw = self.file_path.read_bytes()
        df = self._read_csv_bytes(raw)
        self._ingest_dataframe(df, source_name=self.file_path.name, standard_name=standard_name)

    def _parse_zip_csv(self):
        with zipfile.ZipFile(self.file_path, "r") as archive:
            csv_files = [
                name
                for name in archive.namelist()
                if not name.endswith("/") and Path(name).suffix.lower() == ".csv"
            ]

            if not csv_files:
                raise ValueError("No CSV files found in uploaded ZIP")

            for csv_name in csv_files:
                standard_name = self._identify_sheet_from_name(csv_name)
                if standard_name is None:
                    self.skipped_files.append(csv_name)
                    self.skipped_file_hints[csv_name] = self._suggest_sheet_names(csv_name)
                    logger.warning("Unknown CSV in ZIP, skipped: %s", csv_name)
                    continue

                raw = archive.read(csv_name)
                df = self._read_csv_bytes(raw)
                self._ingest_dataframe(df, source_name=csv_name, standard_name=standard_name)

    def _ingest_dataframe(self, df: pd.DataFrame, source_name: str, standard_name: str):
        df = df.dropna(how="all", axis=0)
        df = df.dropna(how="all", axis=1)

        if df.empty:
            self.skipped_files.append(source_name)
            logger.warning("CSV source is empty after cleaning, skipped: %s", source_name)
            return

        field_mapping: dict[str, str] = {}
        new_columns: list[str] = []
        for col in df.columns:
            standard_field = self.field_standardizer.standardize_field(str(col))
            field_mapping[str(col)] = standard_field
            new_columns.append(standard_field)

        df.columns = new_columns
        df = self._infer_and_convert_types(df)

        if standard_name in self.parsed_data:
            self.parsed_data[standard_name] = pd.concat(
                [self.parsed_data[standard_name], df],
                ignore_index=True,
                sort=False,
            )
        else:
            self.parsed_data[standard_name] = df

        self.sheet_mapping[source_name] = standard_name
        self.field_mappings.setdefault(standard_name, {}).update(field_mapping)

        logger.info(
            "Parsed CSV source '%s' as '%s': %s rows, %s columns",
            source_name,
            standard_name,
            len(df),
            len(df.columns),
        )

    def _infer_and_convert_types(self, df: pd.DataFrame) -> pd.DataFrame:
        date_name_keywords = ("date", "time", "day", "timestamp")
        numeric_preferred = {
            "quantity",
            "sales_quantity",
            "purchase_count",
            "line_total",
            "line_total_jpy",
            "unit_price",
            "unit_price_jpy",
            "discount_price_jpy",
            "original_price_jpy",
            "total_amount",
            "total_amount_jpy",
            "tax_amount_jpy",
            "discount_amount_jpy",
            "retail_price_jpy",
            "cost_price_jpy",
            "item_margin_jpy",
            "stock_quantity",
            "reorder_point",
            "max_stock_level",
            "weight_g",
            "average_foot_traffic",
            "store_size_sqm",
            "household_size",
            "shelf_life_days",
            "days_on_shelf",
            "age",
            "avg_basket_size",
            "avg_transaction_value_jpy",
            "purchase_frequency",
            "days_since_last_purchase",
            "promotion_response_rate",
            "churn_risk_score",
            "support",
            "confidence",
            "lift",
            "co_purchase_count_30d",
            "waon_points_used",
            "waon_points_earned",
        }

        for col in df.columns:
            series = df[col]
            col_lower = col.lower()

            if any(keyword in col_lower for keyword in date_name_keywords):
                is_date, date_format = self.type_inferrer.infer_date_column(series)
                if is_date:
                    try:
                        df[col] = pd.to_datetime(series, format=date_format, errors="coerce")
                        continue
                    except (ValueError, TypeError):
                        pass

            if col_lower in numeric_preferred or self.type_inferrer.infer_numeric_column(series):
                try:
                    df[col] = pd.to_numeric(series, errors="coerce")
                    continue
                except (ValueError, TypeError):
                    pass

            if self.type_inferrer.infer_categorical_column(series):
                try:
                    df[col] = series.astype("category")
                except (ValueError, TypeError):
                    pass

        for col in df.columns:
            if col.lower() in numeric_preferred and pd.api.types.is_datetime64_any_dtype(df[col]):
                try:
                    df[col] = pd.to_numeric(df[col].view("int64"), errors="coerce")
                except (ValueError, TypeError, OverflowError, AttributeError):
                    pass

        return df

    def _generate_parse_report(self):
        source_format = self.file_path.suffix.lower().replace(".", "")
        self.parse_report = {
            "file_name": self.file_path.name,
            "source_format": source_format,
            "file_size_mb": round(self.file_path.stat().st_size / (1024 * 1024), 2),
            "parse_timestamp": datetime.now().isoformat(),
            "total_sheets": len(self.parsed_data),
            "identified_sheets": sorted(self.parsed_data.keys()),
            "sheet_details": {},
            "skipped_files": self.skipped_files,
            "skipped_file_hints": self.skipped_file_hints,
        }

        for standard_name, df in self.parsed_data.items():
            self.parse_report["sheet_details"][standard_name] = {
                "rows": len(df),
                "columns": len(df.columns),
                "fields": list(df.columns),
                "memory_mb": round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2),
            }
