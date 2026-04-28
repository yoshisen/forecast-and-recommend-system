# デプロイと起動ガイド（現行構成, 2026-04）

このドキュメントは、現在のリポジトリでそのまま実行できる起動手順と運用上の注意点をまとめたものです。

## 1. 現在の標準エントリ

- バックエンドの主エントリ: `backend/app/main.py`
- 推奨バックエンド起動コマンド: `python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- フロントエンド: Vite (`npm run dev`)

補足:
- `backend/main.py` は過去の実験用エントリ（`/analyze`）であり、通常の運用フローでは使用しません。

## 2. 起動前の準備

### 2.1 前提環境

- Python 3.11+
- Node.js 18+

### 2.2 依存関係のインストール

```powershell
# backend
cd backend
python -m venv dataanalysisproject
.\dataanalysisproject\Scripts\Activate.ps1
pip install -r requirements.txt

# frontend
cd ..
npm install
```

注意:
- ルートの `start.ps1` / `start.bat` はサービス起動専用です。依存関係の自動インストールは行いません。

## 3. Windows ローカル起動

### 3.1 ワンクリック起動（推奨）

プロジェクトルートで実行:

```powershell
.\start.ps1
```

または:

```bat
start.bat
```

### 3.2 バックエンドのみ起動

```powershell
cd backend
.\start_backend.ps1
```

### 3.3 手動起動（最も安定）

バックエンド:

```powershell
cd backend
.\dataanalysisproject\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

フロントエンド（別ターミナル）:

```powershell
cd <プロジェクトルート>
npm run dev
```

## 4. 起動後の確認

- API ドキュメント: `http://localhost:8000/api/docs`
- ヘルスチェック: `http://localhost:8000/api/health`
- フロントエンド: `http://localhost:5173`

最小確認フロー:

1. Upload 画面でファイルをアップロード（`.xlsx` / `.xls` / `.csv` / `.zip`、複数 CSV の同時選択可）
2. Dashboard へ遷移し、学習ステータスを確認
3. Forecast / Recommend で 1 回ずつ推論を実行
4. CSV/ZIP 利用時は warning の内容（フィールド不足・ファイル名候補）を確認

## 5. 設定と環境変数

バックエンド設定ファイル: `backend/app/config.py`

主要設定:

- アップロード最大サイズ: `MAX_UPLOAD_SIZE = 100MB`
- 許可拡張子: `ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".zip"}`
- CORS 既定値: `http://localhost:5173`, `http://localhost:3000`
- 既定予測期間: `FORECAST_HORIZON = 14`
- 解析後ファイル削除: `DELETE_AFTER_PARSE = False`

`.env` に同名キーを定義することで上書きできます。

## 6. 本番運用の現状と推奨

### 6.1 リポジトリ現状

現時点で同梱されていないもの:

- Dockerfile
- docker-compose.yml
- systemd / NSSM のサービス定義

本番デプロイ時は、対象環境に合わせて上記を追加してください。

### 6.2 最小本番起動（非コンテナ）

```powershell
cd backend
.\dataanalysisproject\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

フロントエンドビルド:

```powershell
cd <プロジェクトルート>
npm run build
npm run preview
```

その後、Nginx / IIS などで `/api` をバックエンドへリバースプロキシしてください。

## 7. よくある問題と対処

### 7.1 `ModuleNotFoundError: No module named app`

原因:
- `backend` 以外のディレクトリで起動している。

対処:

```powershell
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7.2 仮想環境の有効化に失敗する

原因:
- ルートの `.venv` を前提にしているが、このプロジェクトは固定していない。

対処:
- `backend/dataanalysisproject` を使うか、任意の環境を用意して `backend/requirements.txt` をインストールする。

### 7.3 アップロードで「未対応フォーマット」エラー

確認:
- 拡張子が `.xlsx` / `.xls` / `.csv` / `.zip` のいずれかであること。

### 7.4 CSV/ZIP は成功したが一部データが認識されない

原因:
- CSV ファイル名が標準 Sheet 名にマッピングされていない。

対処:

- 標準名で命名する（例: `transaction_items.csv`, `transaction.csv`, `product.csv`）
- 複数 CSV を同時アップロードする場合は、少なくとも `transaction_items.csv`, `transaction.csv`, `product.csv`, `customer.csv` を同時選択
- upload 応答の `warnings` で `zip_skipped_files` と `suggested_sheet_names_by_file` を確認

### 7.5 学習が `skipped` になる / モデル未学習エラーが出る

原因:
- 必須 Sheet もしくは必須フィールドが不足している。

対処:

```text
GET /api/v1/data/readiness
GET /api/v1/data/field-readiness
```

`reason_code` / `reason_ja` を確認し、データを補完後に再学習してください。

### 7.6 TimeSeries 関連 API が失敗する

確認:
- 環境に `prophet` がインストールされているかを確認。

補足:
- 未インストールの場合、一部テストは条件付きでスキップされ、学習 API は失敗する可能性があります。

### 7.7 フロントエンドで CORS エラー

確認:
- `backend/app/config.py` の `ALLOWED_ORIGINS` にフロントエンド URL が含まれているか。
