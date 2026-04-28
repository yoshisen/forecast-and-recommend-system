# 小売分析・MLプラットフォーム（現行実装, 2026-04）

本リポジトリは、フロントエンドとバックエンドを統合した実行可能な分析基盤です。
現在の主フローは次の通りです。

データアップロード（.xlsx/.xls/.csv/.zip） -> 自動解析と品質チェック -> フィールド適合性チェック -> 自動/手動学習（6タスク） -> Dashboard/Homeで状態確認 -> 各ページ/APIで推論

## 1. 現在実装済みの機能

- アップロードと解析
  - `.xlsx` / `.xls` / `.csv` / `.zip` に対応
  - 複数 `.csv` の同時アップロードに対応
  - CSV は「1ファイル = 1 Sheet」として解析
  - ZIP は複数 CSV を一括取込し、未認識ファイルには候補 Sheet 名を返却
- データガバナンス
  - 列名正規化、型推定、関連整合チェック
  - 品質レポート（欠損・重複・範囲など）
  - タスク別フィールド readiness（`reason_code` / `reason_ja`）
- 学習と推論
  - Forecast
  - Recommend
  - Classification
  - Association
  - Clustering
  - TimeSeries (Prophet)
- 学習状態管理
  - アップロード後の自動学習スケジューリング
  - 手動再学習
  - WebSocket: `/api/v1/ws/training`
- フロントエンド画面（ルーティング接続済み）
  - Home
  - Upload
  - Upload Schema Guide
  - Dashboard
  - Forecast
  - Recommend
  - Classification
  - Association
  - Clustering
  - TimeSeries

## 2. 現時点の制約と注意点

- バージョン情報とモデル状態はプロセスメモリ保持のため、再起動で消失します。
- 認証・認可は未実装です。
- Dockerfile / docker-compose / systemd / NSSM は同梱していません。
- `backend/main.py` は過去の実験用エントリで、主系では利用しません。
- TimeSeries は `prophet` に依存し、未導入環境では関連テストが条件付きスキップされます。
- `start.ps1` / `start.bat` は依存インストールを行いません（起動のみ）。

## 3. Windows での起動

### 3.1 前提

- Python 3.11+
- Node.js 18+

初回は依存をインストールしてください。

```powershell
# backend
cd backend
python -m venv dataanalysisproject
.\dataanalysisproject\Scripts\Activate.ps1
pip install -r requirements.txt

# frontend（プロジェクトルート）
cd ..
npm install
```

### 3.2 ワンクリック起動（ルート）

```powershell
.\start.ps1
```

または

```bat
start.bat
```

### 3.3 バックエンドのみ起動

```powershell
cd backend
.\start_backend.ps1
```

### 3.4 手動起動（推奨）

```powershell
# Terminal A: backend
cd backend
.\dataanalysisproject\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal B: frontend
cd ..
npm run dev
```

### 3.5 アクセス先

- フロントエンド: `http://localhost:5173`
- Swagger: `http://localhost:8000/api/docs`
- ヘルスチェック: `http://localhost:8000/api/health`

## 4. API 一覧（現行ルーティング）

プレフィックス: `/api/v1`

### 4.1 Data / Upload

- `POST /upload`
- `GET /data/summary`
- `GET /data/quality`
- `GET /data/readiness`
- `GET /data/upload-schema`
- `GET /data/field-readiness`
- `GET /data/samples`
- `GET /data/forecast-total`
- `GET /versions`

### 4.2 Forecast

- `GET /forecast`
- `POST /forecast/batch`
- `POST /forecast/train`

### 4.3 Recommend

- `GET /recommend`
- `GET /recommend/popular`
- `POST /recommend/train`

### 4.4 Classification

- `POST /classification/train`
- `GET /classification/predict`
- `POST /classification/predict/features`
- `GET /classification/threshold-scan`
- `POST /classification/tune-threshold`

### 4.5 Association

- `POST /association/train`
- `GET /association/rules`
- `GET /association/recommendations`

### 4.6 Clustering

- `POST /clustering/train`
- `GET /clustering/segments`
- `GET /clustering/points`
- `GET /clustering/customer/{customer_id}`

### 4.7 TimeSeries

- `POST /timeseries/train`
- `GET /timeseries/forecast`

共通:

- `GET /`
- `GET /api/health`
- `WS /api/v1/ws/training`

## 5. アップロードと学習の重要制約

- 対応形式: `.xlsx` / `.xls` / `.csv` / `.zip`
- 複数 `.csv` を同時アップロード可能（同一リクエスト内で統合解析）
- CSV ファイル名は標準 Sheet 名を含めることを推奨（例: `transaction_items.csv`）
- ZIP の未認識ファイルは warning に以下を返却
  - `zip_skipped_files`
  - `suggested_sheet_names_by_file`

主要機能を一度に検証する推奨セット:

- `transaction_items.csv`
- `transaction.csv`
- `product.csv`
- `customer.csv`

タスク別の最低 Sheet 要件:

- forecast: `transaction_items + transaction + product`
- recommend: `transaction_items + transaction + customer + product`
- classification: `transaction_items + transaction + customer`
- association: `transaction_items + transaction + product`
- clustering: `transaction_items + transaction + customer`
- prophet(timeseries): `transaction_items + transaction + product`

## 6. テストと回帰

### 6.1 バックエンド

```powershell
cd backend
pytest
```

`backend/tests/` には以下を含むテストが実装済みです。

- モジュールの成功/失敗パス
- upload warning 契約
- train エンドポイント行列
- CSV/ZIP アップロード回帰
- 全体 CSV データセットの統合テスト

### 6.2 フロントエンド

```powershell
npm run test
```

Upload/Dashboard/Forecast/Recommend/Classification/Association/Clustering/TimeSeries の主要経路をカバーします。

### 6.3 E2E

```powershell
npm run e2e
```

初回はブラウザをインストールしてください。

```powershell
npm run e2e:install
```

### 6.4 フィクスチャ生成

`backend/tests/fixtures/schema_v2_full/generate_schema_v2_csv.py` は、既定で 12 CSV・各 20000 行を生成し、高負荷回帰に利用できます。

## 7. ディレクトリ構成（抜粋）

```text
dataAnalysisProject/
├─ backend/
│  ├─ app/
│  │  ├─ api/v1/            # data / forecast / recommend / classification / association / clustering / timeseries
│  │  ├─ core/              # parser / quality / feature_engine / training_events / task_registry
│  │  ├─ models/            # forecasting / recommendation / classification / clustering / association / timeseries
│  │  ├─ schemas/
│  │  └─ main.py            # 主 FastAPI エントリ
│  ├─ tests/
│  ├─ main.py               # 実験用旧エントリ（/analyze）
│  └─ requirements.txt
├─ src/
│  ├─ pages/                # Home / Upload / Dashboard / Forecast / Recommend / Classification / Association / Clustering / TimeSeries
│  ├─ components/
│  └─ services/api.js
├─ e2e/
├─ DEPLOY.md
├─ UPLOAD_SCHEMA.md
└─ TEST_PLAN.md
```

## 8. ドキュメント索引

- `DEPLOY.md`: デプロイと起動
- `UPLOAD_SCHEMA.md`: アップロードスキーマ規約と拡張方針
- `TEST_PLAN.md`: テスト計画と回帰指針

## 9. ライセンス

Apache-2.0
