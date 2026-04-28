"""
Data Management API Router
"""
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Request, Query
from pathlib import Path
import logging
import math
from datetime import datetime
import shutil
from typing import Optional
import zipfile

from app.config import settings
from app.core.excel_parser import ExcelParser
from app.core.tabular_parser import TabularUploadParser
from app.core.quality import DataQualityChecker, DataValidator
from app.core.training_events import (
    run_forecast_training,
    run_recommend_training,
    run_classification_training,
    run_association_training,
    run_clustering_training,
    run_prophet_training,
)
from app.core.task_registry import build_task_readiness, build_initial_training_state
from app.core.total_forecast import build_total_forecast
from app.core.upload_schema_catalog import build_upload_schema_payload, build_field_readiness_from_parsed_data

logger = logging.getLogger(__name__)

router = APIRouter()

# Global state will be accessed via request.app.state


def _resolve_version_or_404(request: Request, version: Optional[str]) -> str:
    version_id = version or request.app.state.current_version
    if not version_id or version_id not in request.app.state.data_versions:
        raise HTTPException(
            status_code=404,
            detail="データが見つかりません。先にファイルをアップロードしてください"
        )
    return version_id


def _unique_head(series, limit: int = 20):
    return [str(v) for v in series.dropna().astype(str).drop_duplicates().head(limit).tolist()]


def _build_samples(parsed_data: dict):
    transaction_df = parsed_data.get('transaction')
    item_df = parsed_data.get('transaction_items')
    customer_df = parsed_data.get('customer')
    product_df = parsed_data.get('product')
    store_df = parsed_data.get('store')

    product_ids = []
    if product_df is not None and 'product_id' in product_df.columns:
        product_ids.extend(_unique_head(product_df['product_id']))
    if item_df is not None and 'product_id' in item_df.columns:
        for pid in _unique_head(item_df['product_id']):
            if pid not in product_ids:
                product_ids.append(pid)

    customer_ids = []
    if customer_df is not None and 'customer_id' in customer_df.columns:
        customer_ids.extend(_unique_head(customer_df['customer_id']))
    if transaction_df is not None and 'customer_id' in transaction_df.columns:
        for cid in _unique_head(transaction_df['customer_id']):
            if cid not in customer_ids:
                customer_ids.append(cid)

    store_ids = []
    if store_df is not None and 'store_id' in store_df.columns:
        store_ids.extend(_unique_head(store_df['store_id']))
    if transaction_df is not None and 'store_id' in transaction_df.columns:
        for sid in _unique_head(transaction_df['store_id']):
            if sid not in store_ids:
                store_ids.append(sid)

    top_pairs = []
    if item_df is not None and transaction_df is not None and 'transaction_id' in item_df.columns and 'transaction_id' in transaction_df.columns:
        merged = item_df[['transaction_id', 'product_id']].merge(
            transaction_df[['transaction_id', 'store_id']], on='transaction_id', how='left'
        )
        if 'product_id' in merged.columns and 'store_id' in merged.columns:
            pair_counts = (
                merged.dropna(subset=['product_id', 'store_id'])
                .groupby(['product_id', 'store_id'])
                .size()
                .sort_values(ascending=False)
                .head(20)
                .reset_index(name='count')
            )
            top_pairs = [
                {
                    'product_id': str(row['product_id']),
                    'store_id': str(row['store_id']),
                    'count': int(row['count'])
                }
                for _, row in pair_counts.iterrows()
            ]

    return {
        'product_ids': product_ids[:20],
        'customer_ids': customer_ids[:20],
        'store_ids': store_ids[:20],
        'top_pairs': top_pairs,
    }


def _extract_reason_code(reason: Optional[str]) -> Optional[str]:
    if not reason:
        return None

    if reason.startswith('missing_required_sheets:'):
        return 'missing_required_sheets'
    if reason.startswith('missing_required_fields:'):
        return 'missing_required_fields'
    return reason


def _reason_to_japanese(reason: Optional[str]) -> Optional[str]:
    if not reason:
        return None

    if reason == 'ok':
        return '問題ありません'
    if reason == 'missing_required_sheets':
        return '必須シート不足'
    if reason.startswith('missing_required_sheets:'):
        value = reason.replace('missing_required_sheets:', '').strip()
        return f'必須シート不足: {value}' if value else '必須シート不足'

    if reason == 'missing_required_fields':
        return '必須フィールド不足'
    if reason.startswith('missing_required_fields:'):
        value = reason.replace('missing_required_fields:', '').strip()
        return f'必須フィールド不足: {value}' if value else '必須フィールド不足'

    if reason == 'task_not_implemented_yet':
        return 'このタスクは未実装です'
    if reason == 'not_trainable':
        return '現在は学習できません'
    return reason


def _build_reason_meta(reason: Optional[str]) -> dict[str, Optional[str]]:
    code = _extract_reason_code(reason)
    return {
        'reason_code': code,
        'reason': reason,
        'reason_ja': _reason_to_japanese(reason),
    }


def _sanitize_json_value(value):
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, dict):
        return {k: _sanitize_json_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_json_value(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_json_value(v) for v in value)
    return value


def _collect_upload_files(file: Optional[UploadFile], files: Optional[list[UploadFile]]) -> list[UploadFile]:
    upload_files: list[UploadFile] = []
    if files:
        upload_files.extend([item for item in files if item and item.filename])
    if file and file.filename:
        upload_files.append(file)
    return upload_files


def _sanitize_upload_name(file_name: str, fallback: str) -> str:
    base_name = Path(file_name).name.strip()
    return base_name or fallback


async def _save_upload_payload(upload_files: list[UploadFile], version_id: str) -> tuple[Path, str, str]:
    if len(upload_files) == 1:
        item = upload_files[0]
        file_ext = Path(item.filename).suffix.lower()
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不正なファイル形式: {file_ext}. 許可: {settings.ALLOWED_EXTENSIONS}"
            )

        original_name = _sanitize_upload_name(item.filename, "upload_file")
        upload_path = settings.UPLOAD_DIR / f"{version_id}_{original_name}"
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(item.file, buffer)

        return upload_path, file_ext, original_name

    invalid_exts = sorted({
        Path(item.filename).suffix.lower()
        for item in upload_files
        if Path(item.filename).suffix.lower() != '.csv'
    })
    if invalid_exts:
        raise HTTPException(
            status_code=400,
            detail=f"複数同時アップロードは CSV のみ対応です。検出: {invalid_exts}"
        )

    upload_path = settings.UPLOAD_DIR / f"{version_id}_multi_csv_bundle.zip"
    used_names: set[str] = set()
    with zipfile.ZipFile(upload_path, mode='w', compression=zipfile.ZIP_DEFLATED) as archive:
        for index, item in enumerate(upload_files, start=1):
            safe_name = _sanitize_upload_name(item.filename, f"upload_{index}.csv")
            if Path(safe_name).suffix.lower() != '.csv':
                safe_name = f"{Path(safe_name).stem}.csv"

            candidate = safe_name
            duplicate_index = 1
            while candidate in used_names:
                candidate = f"{Path(safe_name).stem}_{duplicate_index}.csv"
                duplicate_index += 1
            used_names.add(candidate)

            archive.writestr(candidate, await item.read())

    display_name = f"multi_csv_upload_{len(upload_files)}_files.zip"
    return upload_path, '.zip', display_name


@router.post("/upload")
async def upload_excel(
    request: Request,
    file: UploadFile | None = File(default=None),
    files: list[UploadFile] | None = File(default=None),
    background_tasks: BackgroundTasks = None
):
    """
    データファイルをアップロードして解析
    
    Returns:
        - success: bool
        - version: str - データバージョンID
        - parse_report: dict - 解析報告
        - quality_report: dict - 質量報告
        - warnings: list - 警告リスト
    """
    upload_files = _collect_upload_files(file, files)
    if not upload_files:
        raise HTTPException(status_code=400, detail="アップロードするファイルが指定されていません")

    logger.info("Receiving file upload: %s", ', '.join(item.filename for item in upload_files))

    version_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    upload_path = None
    
    try:
        upload_path, file_ext, original_filename = await _save_upload_payload(upload_files, version_id)
        
        logger.info("File saved to: %s", upload_path)
        
        # ファイル解析
        if file_ext in {'.xlsx', '.xls'}:
            parser = ExcelParser(upload_path)
        else:
            parser = TabularUploadParser(upload_path)
        parse_result = parser.parse()
        
        if not parse_result['success']:
            raise HTTPException(
                status_code=400,
                detail=f"ファイル解析エラー: {parse_result.get('error', 'Unknown error')}"
            )
        
        parsed_data = parse_result['parsed_data']
        parse_report = _sanitize_json_value(parse_result['report'])
        
        # データ質量チェック
        quality_checker = DataQualityChecker(parsed_data)
        quality_report = _sanitize_json_value(quality_checker.generate_report())
        
        # データ検証
        validation_result = _sanitize_json_value(DataValidator.validate_relationships(parsed_data))
        
        available_sheets = sorted(list(parsed_data.keys()))
        task_readiness = build_task_readiness(available_sheets)
        field_readiness = build_field_readiness_from_parsed_data(parsed_data)
        training_status = build_initial_training_state(task_readiness)

        # Field-level minimum checks can disable task training even when required sheets exist.
        for task_name, task_info in field_readiness.get('tasks', {}).items():
            if training_status.get(task_name) == 'pending' and not task_info.get('can_train_with_fields', True):
                training_status[task_name] = 'skipped'
                training_status[f'{task_name}_reason'] = task_info.get('reason')
                training_status[f'{task_name}_reason_code'] = task_info.get('reason_code')
                training_status[f'{task_name}_reason_ja'] = task_info.get('reason_ja')
                training_status[f'{task_name}_finished_at'] = datetime.now().isoformat()

        # グローバル状態に保存
        request.app.state.data_versions[version_id] = {
            'parsed_data': parsed_data,
            'parse_report': parse_report,
            'quality_report': quality_report,
            'validation_result': validation_result,
            'uploaded_at': datetime.now().isoformat(),
            'filename': original_filename,
            'training': training_status,
            'task_readiness': task_readiness,
            'field_readiness': field_readiness,
        }
        request.app.state.current_version = version_id
        
        logger.info("Successfully processed file, version: %s", version_id)
        
        # 警告リスト生成
        warnings = []
        for task_name, readiness in task_readiness.items():
            if readiness.get('missing_required_sheets'):
                reason = readiness.get('reason')
                warnings.append({
                    'type': 'missing_required_sheet',
                    'task': task_name,
                    'message': f"{task_name} に必要なシートが不足: {', '.join(readiness['missing_required_sheets'])}",
                    'impact': '該当機能はスキップされます',
                    **_build_reason_meta(reason),
                })

        # Missing required fields for a task (sheet exists but required columns are missing)
        for task_name, info in field_readiness.get('tasks', {}).items():
            missing_by_sheet = info.get('missing_required_fields_by_sheet', {})
            if not missing_by_sheet:
                continue

            detail_parts = []
            for sheet_name, missing_fields in missing_by_sheet.items():
                detail_parts.append(f"{sheet_name}[{', '.join(missing_fields)}]")

            reason_meta = _build_reason_meta(info.get('reason'))
            # field_readiness で生成済みの日本語理由がある場合は優先して採用する
            if info.get('reason_ja'):
                reason_meta['reason_ja'] = info.get('reason_ja')
            if info.get('reason_code'):
                reason_meta['reason_code'] = info.get('reason_code')

            warnings.append({
                'type': 'missing_required_field',
                'task': task_name,
                'message': f"{task_name} に必要な列が不足: {'; '.join(detail_parts)}",
                'impact': '該当機能の自動訓練はスキップされます（他機能は継続）',
                **reason_meta,
            })
        
        # オプションシート不足
        optional_sheets = {
            'promotion': 'プロモーション分析機能',
            'inventory': '在庫最適化機能',
            'weather': '天気影響分析',
            'customer_behavior': '高度な顧客分析',
            'product_association': '拡張アソシエーション分析',
            'review': 'レビュー特徴分析',
        }
        for sheet, feature in optional_sheets.items():
            if sheet not in available_sheets:
                warnings.append({
                    'type': 'missing_optional_sheet',
                    'message': f"{sheet} シートがありません",
                    'impact': f"{feature}が利用できません",
                    'reason_code': 'missing_optional_sheet',
                    'reason': f'missing_optional_sheet: {sheet}',
                    'reason_ja': f'任意シート不足: {sheet}',
                })

        if file_ext in {'.csv', '.zip'}:
            missing_required_sheets_all = sorted({
                sheet
                for readiness in task_readiness.values()
                for sheet in readiness.get('missing_required_sheets', [])
            })
            if missing_required_sheets_all:
                detail = ', '.join(missing_required_sheets_all)
                warnings.append({
                    'type': 'tabular_missing_core_sheets',
                    'message': f"CSV/ZIP 取り込みで主要シートが不足: {detail}",
                    'impact': 'CSVファイル名を標準シート名に合わせて追加してください（例: transaction_items.csv, transaction.csv, product.csv）',
                    'reason_code': 'missing_required_sheets',
                    'reason': f'missing_required_sheets: {detail}',
                    'reason_ja': f'必須シート不足: {detail}',
                })

            if file_ext == '.zip':
                skipped_files = parse_report.get('skipped_files') or []
                if skipped_files:
                    preview = ', '.join(skipped_files[:6])
                    if len(skipped_files) > 6:
                        preview = f"{preview} ほか {len(skipped_files) - 6} 件"

                    skipped_hints = parse_report.get('skipped_file_hints') or {}
                    hint_rows = []
                    hinted_files: dict[str, list[str]] = {}
                    for file_name in skipped_files[:3]:
                        suggestions = skipped_hints.get(file_name) or []
                        if suggestions:
                            hinted_files[file_name] = suggestions
                            hint_rows.append(f"{file_name} -> {', '.join(suggestions)}")

                    hint_text = '; '.join(hint_rows)
                    impact_text = 'ファイル名に標準シート名を含めると取り込みできます（例: transaction_items.csv）'
                    if hint_text:
                        impact_text = f"{impact_text} 候補: {hint_text}"

                    warnings.append({
                        'type': 'zip_skipped_files',
                        'message': f"ZIP 内で未認識の CSV をスキップ: {preview}",
                        'impact': impact_text,
                        'suggested_sheet_names_by_file': hinted_files,
                        'reason_code': 'unknown_sheet_name',
                        'reason': 'unknown_sheet_name',
                        'reason_ja': '未認識シート名',
                    })
        
        scheduled_tasks = []
        auto_train_dispatch = {
            'forecast': run_forecast_training,
            'recommend': run_recommend_training,
            'classification': run_classification_training,
            'association': run_association_training,
            'clustering': run_clustering_training,
            'prophet': run_prophet_training,
        }
        if background_tasks:
            for task_name, train_fn in auto_train_dispatch.items():
                if task_readiness.get(task_name, {}).get('can_train'):
                    if not field_readiness.get('tasks', {}).get(task_name, {}).get('can_train_with_fields', True):
                        continue
                    background_tasks.add_task(train_fn, request.app, version_id)
                    scheduled_tasks.append(task_name)

        # 処理後ファイル削除（オプション）
        if settings.DELETE_AFTER_PARSE and background_tasks and upload_path is not None:
            background_tasks.add_task(upload_path.unlink, missing_ok=True)
        
        return _sanitize_json_value({
            'success': True,
            'version': version_id,
            'parse_report': parse_report,
            'quality_report': quality_report,
            'validation_result': validation_result,
            'warnings': warnings,
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'filename': original_filename,
                'available_sheets': available_sheets
            },
            'parsed_data_summary': {
                'total_sheets': len(parsed_data),
                'sheet_names': list(parsed_data.keys())
            },
            'task_readiness': task_readiness,
            'field_readiness': field_readiness,
            'task_field_readiness': field_readiness.get('tasks', {}),
            'auto_training': {
                task_name: {
                    'status': 'scheduled' if task_name in scheduled_tasks else training_status[task_name],
                    'reason': training_status.get(f'{task_name}_reason'),
                    'reason_code': training_status.get(f'{task_name}_reason_code') or _extract_reason_code(training_status.get(f'{task_name}_reason')),
                    'reason_ja': training_status.get(f'{task_name}_reason_ja') or _reason_to_japanese(training_status.get(f'{task_name}_reason')),
                }
                for task_name in task_readiness.keys()
            }
        })
    
    except HTTPException:
        if upload_path and upload_path.exists():
            upload_path.unlink()
        raise
    except Exception as e:
        logger.error("Error processing file: %s", str(e), exc_info=True)
        
        # エラー時はファイル削除
        if upload_path and upload_path.exists():
            upload_path.unlink()
        
        raise HTTPException(
            status_code=500,
            detail=f"ファイル処理エラー: {str(e)}"
        ) from e


@router.get("/data/summary")
async def get_data_summary(request: Request, version: Optional[str] = None):
    """
    データサマリーを取得
    
    Args:
        version: データバージョン（省略時は最新）
    
    Returns:
        データサマリー情報
    """
    version_id = _resolve_version_or_404(request, version)

    version_data = request.app.state.data_versions[version_id]
    quality_report = version_data['quality_report']

    training_info = version_data.get('training', {})
    task_readiness = version_data.get('task_readiness', {})
    summary = {
        'version': version_id,
        'uploaded_at': version_data['uploaded_at'],
        'filename': version_data['filename'],
        'overall_summary': quality_report['overall_summary'],
        'sheet_summaries': {},
        'training': training_info,
        'task_readiness': task_readiness
    }
    for sheet_name, sheet_report in quality_report['sheet_reports'].items():
        summary['sheet_summaries'][sheet_name] = {
            'rows': sheet_report['row_count'],
            'columns': sheet_report['column_count'],
            'data_range': sheet_report.get('data_range', {})
        }

    return {
        'success': True,
        'data': summary,
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'version': version_id
        }
    }


@router.get("/data/quality")
async def get_quality_report(request: Request, version: Optional[str] = None):
    """データ質量報告を取得"""
    version_id = _resolve_version_or_404(request, version)

    version_data = request.app.state.data_versions[version_id]

    return {
        'success': True,
        'data': version_data['quality_report'],
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'version': version_id
        }
    }


@router.get("/data/readiness")
async def get_task_readiness(request: Request, version: Optional[str] = None):
    """Task readiness matrix for current version."""
    version_id = _resolve_version_or_404(request, version)
    version_data = request.app.state.data_versions[version_id]

    return {
        'success': True,
        'data': {
            'version': version_id,
            'task_readiness': version_data.get('task_readiness', {}),
            'training': version_data.get('training', {}),
            'field_readiness': version_data.get('field_readiness', {}),
        },
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'version': version_id
        }
    }


@router.get("/data/upload-schema")
async def get_upload_schema_guide():
    """Return upload field guide used by frontend and user-facing docs page."""
    return {
        'success': True,
        'data': build_upload_schema_payload(),
        'metadata': {
            'timestamp': datetime.now().isoformat(),
        }
    }


@router.get("/data/field-readiness")
async def get_field_readiness(request: Request, version: Optional[str] = None):
    """Return field-level readiness report for current or specific uploaded version."""
    version_id = _resolve_version_or_404(request, version)
    version_data = request.app.state.data_versions[version_id]

    report = version_data.get('field_readiness')
    if report is None:
        report = build_field_readiness_from_parsed_data(version_data.get('parsed_data', {}))

    return {
        'success': True,
        'data': {
            'version': version_id,
            'field_readiness': report,
        },
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'version': version_id,
        }
    }


@router.get("/data/samples")
async def get_data_samples(request: Request, version: Optional[str] = None):
    """Return sample IDs for quick action forms."""
    version_id = _resolve_version_or_404(request, version)
    version_data = request.app.state.data_versions[version_id]

    samples = _build_samples(version_data.get('parsed_data', {}))
    return {
        'success': True,
        'data': {
            'version': version_id,
            'samples': samples,
        },
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'version': version_id,
        }
    }


@router.get("/data/forecast-total")
async def get_total_forecast(
    request: Request,
    horizon: int = Query(14, ge=1, le=90, description="予測期間（日数）"),
    model_type: str = Query("auto", description="auto | model | lightgbm | naive"),
    top_n_pairs: int = Query(20, ge=1, le=100, description="集計に使う上位商品x店舗ペア数"),
    version: Optional[str] = None,
):
    """Aggregate total amount forecast for Home workbench."""
    version_id = _resolve_version_or_404(request, version)
    version_data = request.app.state.data_versions[version_id]

    try:
        payload = build_total_forecast(
            app=request.app,
            parsed_data=version_data['parsed_data'],
            version_id=version_id,
            horizon=horizon,
            model_type=model_type,
            top_n_pairs=top_n_pairs,
        )
        return {
            'success': True,
            'data': payload,
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'version': version_id,
            }
        }
    except Exception as e:
        logger.error("Total forecast error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"総額予測エラー: {str(e)}") from e


@router.get("/versions")
async def list_versions(request: Request):
    """利用可能なデータバージョンのリスト"""
    versions = []
    for version_id, data in request.app.state.data_versions.items():
        versions.append({
            'version': version_id,
            'uploaded_at': data['uploaded_at'],
            'filename': data['filename'],
            'is_current': version_id == request.app.state.current_version
        })

    return {
        'success': True,
        'data': {
            'versions': sorted(versions, key=lambda x: x['uploaded_at'], reverse=True),
            'current_version': request.app.state.current_version
        }
    }
