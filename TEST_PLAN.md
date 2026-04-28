# テスト計画（システム全体版・追加モジュール対応）

本ドキュメントは、現行リポジトリの実装に合わせた実行可能なテスト活動を定義します。

## 1. 現在のテスト状況と戦略

- バックエンドは `pytest + pytest-cov + pytest-asyncio + httpx` を導入済みで、ヘルスチェック、タスク登録、モジュール異常系、学習エンドポイント行列、主要成功パスをカバー。
- フロントエンドは `vitest + testing-library + jsdom` を導入済みで、Upload/Dashboard/Forecast/Recommend/Classification/Association/Clustering/TimeSeries の主要画面をカバー。
- E2E は Playwright（Chromium）を導入済みで、アップロード->分析->予測->推薦の主経路と、未学習時エラー表示の経路をカバー。
- 運用方針は「自動回帰中心 + 手動探索補完」。自動化で安定性を担保し、手動で複雑な UI/相互作用を確認する。

## 2. テスト範囲（今回リライト後の対象）

### 2.1 バックエンド

- データ/バージョン: upload, parse, quality report, readiness, samples, version list, total forecast。
- 学習/推論:
  - Forecast
  - Recommend
  - Classification
  - Association
  - Clustering
  - TimeSeries（Prophet）
- 学習状態: `pending/running/completed/failed/skipped`、進捗率、エラートレース。
- リアルタイム状態: WebSocket `/api/v1/ws/training` とフロントのポーリングフォールバック。

### 2.2 フロントエンド画面

- Home
- Upload
- Dashboard
- Forecast
- Recommend
- Classification
- Association
- Clustering
- TimeSeries

## 3. 環境準備

### 3.1 サービス起動

推奨（ルートでワンクリック）:

```powershell
.\start.ps1
```

個別起動:

```powershell
# Terminal A
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal B
cd ..
npm run dev
```

### 3.2 ヘルスチェック

```powershell
Invoke-RestMethod http://localhost:8000/api/health
Invoke-RestMethod http://localhost:8000/api/v1/versions
Invoke-RestMethod http://localhost:8000/api/v1/data/summary
```

期待値:
- いずれも JSON を返す。
- `/api/health` は `status=healthy`。
- そのほかは妥当な `success` または説明可能なエラーを返す。

### 3.3 テストデータ生成

小規模（通常回帰向け）:

```powershell
python generate_supermarket_data_small.py data/uploaded/small_test.xlsx
```

大規模（性能回帰向け）:

```powershell
python generate_supermarket_data.py data/uploaded/large_test.xlsx
```

## 4. 学習可能性チェック（必須）

アップロード後は必ず readiness を確認し、データ不足をシステム障害と誤判定しない。

```powershell
Invoke-RestMethod "http://localhost:8000/api/v1/data/readiness"
```

タスクごとの必須 Sheet（task_registry 準拠）:

- forecast: `transaction_items + transaction + product`
- recommend: `transaction_items + transaction + customer + product`
- classification: `transaction_items + transaction + customer`
- association: `transaction_items + transaction + product`
- clustering: `transaction_items + transaction + customer`
- prophet: `transaction_items + transaction + product`

`can_train=false` の場合は「前提不足（想定動作）」として扱い、失敗扱いにしない。

## 5. 全体スモークテスト（現行版で毎回実施）

### 5.1 アップロードと解析

手順:

1. Upload 画面で `small_test.xlsx` をアップロード
2. 進捗が 100% になるまで確認
3. parse/quality/validation の返却内容を確認

期待値:

- `success=true` を返す
- `version` と `available_sheets` を表示
- Dashboard へ自動遷移

### 5.2 Dashboard 状態確認

手順:
- Dashboard を開いて 1〜3 分監視

期待値:

- Sheet 数、総レコード数、version を表示
- 各タスクに状態ラベルと進捗バーを表示
- タスク状態が条件に応じて `pending/running/completed/skipped/failed` に遷移
- 失敗時はエラー内容とトレースを確認可能

### 5.3 自動学習と手動再学習

手順:

1. アップロード後の自動学習進行を確認
2. 任意タスクで「学習開始/再学習」を実行

期待値:

- 状態が再度 `running` に入る
- 最終的に `completed` もしくは明確な失敗理由を返す

### 5.4 Forecast（画面 + API）

手順:

1. `/api/v1/data/samples` から `product_id/store_id` を取得
2. Forecast 画面で 14 日予測を実行
3. API 実行

```powershell
Invoke-RestMethod "http://localhost:8000/api/v1/forecast?product_id=<PID>&store_id=<SID>&horizon=14"
```

期待値:

- 予測結果、トレンド可視化、明細が表示される
- `horizon` 1〜90 が有効
- 未学習時は明確なエラーを返し、画面はクラッシュしない

### 5.5 Recommend（画面 + API）

手順:

1. `customer_id` で個別推薦を実行
2. 人気推薦に切替
3. API 実行

```powershell
Invoke-RestMethod "http://localhost:8000/api/v1/recommend?customer_id=<CID>&top_k=10"
Invoke-RestMethod "http://localhost:8000/api/v1/recommend/popular?top_k=10"
```

期待値:

- 推薦リスト（商品情報 + スコア）を返す
- `top_k` 1〜50 が有効
- 未学習時は解釈可能なエラーを返す

### 5.6 Classification（重点）

手順:

1. 画面で分類モデル学習を実行
2. customer_id で予測
3. 閾値スキャンと閾値更新を実行

推奨 API:

```powershell
Invoke-RestMethod -Method Post "http://localhost:8000/api/v1/classification/train"
Invoke-RestMethod "http://localhost:8000/api/v1/classification/predict?customer_id=<CID>&threshold=0.5"
Invoke-RestMethod "http://localhost:8000/api/v1/classification/threshold-scan?step=0.05"
Invoke-RestMethod -Method Post "http://localhost:8000/api/v1/classification/tune-threshold?threshold=0.6"
```

期待値:

- precision/recall/f1 などの学習指標を返す
- 予測結果と閾値スキャン結果が描画される
- パラメータ不正時は明確なバリデーションエラー

### 5.7 Association（重点）

手順:

1. 「学習して関連ルールを読み込む」を実行
2. product_id でクロスセル推薦を照会

推奨 API:

```powershell
Invoke-RestMethod -Method Post "http://localhost:8000/api/v1/association/train"
Invoke-RestMethod "http://localhost:8000/api/v1/association/rules?top_k=100"
Invoke-RestMethod "http://localhost:8000/api/v1/association/recommendations?product_id=<PID>&top_k=10"
```

期待値:

- support/confidence/lift を含むルールを返す
- クロスセル結果を返す
- 未学習時エラーが明確

### 5.8 Clustering（重点）

手順:

1. n_clusters=4 で学習
2. segments、points（PCA）、customer cluster を確認

推奨 API:

```powershell
Invoke-RestMethod -Method Post "http://localhost:8000/api/v1/clustering/train?n_clusters=4"
Invoke-RestMethod "http://localhost:8000/api/v1/clustering/segments"
Invoke-RestMethod "http://localhost:8000/api/v1/clustering/points?limit=2000"
Invoke-RestMethod "http://localhost:8000/api/v1/clustering/customer/<CID>"
```

期待値:

- 顧客数、クラスタ数、シルエット係数などを返す
- 散布図とセグメント表が表示される
- customer 照会で所属クラスタを返す

### 5.9 TimeSeries / Prophet（重点）

手順:

1. Prophet 学習を実行
2. 未来 horizon 予測を実行し区間を確認

推奨 API:

```powershell
Invoke-RestMethod -Method Post "http://localhost:8000/api/v1/timeseries/train"
Invoke-RestMethod "http://localhost:8000/api/v1/timeseries/forecast?horizon=14"
```

期待値:

- `yhat`, `upper/lower`, `trend` を返す
- `horizon` 1〜90 が有効
- 未学習時エラーが明確

### 5.10 複数バージョン回帰

手順:

1. `small` と `large` を連続アップロード
2. `/api/v1/versions` で一覧確認
3. `version` 指定で summary/forecast/recommend を照会

期待値:

- 複数バージョンが見える
- バージョン指定時の挙動が説明可能
- 現行バージョン切替時にフロントがクラッシュしない

## 6. API パラメータと異常系

### 6.1 境界値

- forecast `horizon`: 1-90
- recommend `top_k`: 1-50
- clustering `n_clusters`: 2-12
- clustering points `limit`: 100-10000
- classification `threshold`: (0,1)
- classification threshold-scan `step`: (0,0.2]

### 6.2 典型的な異常挙動（説明可能であること）

- データなし: 404（無効 version / 未アップロード）
- モデル未学習: 400（当該モデル未存在）
- 不正パラメータ: 422 または明確なパラメータエラー
- 学習失敗: 失敗状態と詳細エラーを返し、黙って失敗しない

## 7. フロント回帰チェックリスト（毎回）

- Upload 成功後に Dashboard へ自動遷移する
- Dashboard で WebSocket 断時にポーリングへフォールバックできる
- Dashboard の失敗タスクでトレースを展開表示できる
- Home の総額予測でモデル種別/horizon 変更が反映される
- Forecast/Recommend の URL パラメータ自動復元と自動実行が機能する
- Classification の予測、閾値スキャン、閾値更新が機能する
- Association のルール表とクロスセル検索が機能する
- Clustering の散布図、分群表、顧客クラスタ照会が機能する
- TimeSeries の学習と予測グラフが機能する
- API エラー時に画面が空白クラッシュせず、エラー表示が出る

## 8. システム障害シナリオ（重点監視）

- 重要 Sheet 不足: タスクが `skipped/failed` になり、理由が明確
- アップロード成功だが一部モデル不可学習: readiness/summary で理由説明
- 学習中に画面リロード: 状態復元して表示可能
- WebSocket 切断: ポーリング継続で状態更新
- 学習ボタン連打: 状態不整合やフロントフリーズが起きない

## 9. 現フェーズの合格基準

以下を満たせば現行版を「利用可能」と判定する。

- 小規模 Excel のアップロードに成功し、parse/quality/validation を取得できる
- Dashboard で 6 タスク（forecast/recommend/classification/association/clustering/prophet）の状態を表示できる
- 少なくとも 4 タスクが小規模データで学習完了し、対応画面で結果を返す
- 主要 API が安定し説明可能
  - `/api/health`
  - `/api/v1/data/summary`
  - `/api/v1/forecast`
  - `/api/v1/recommend`
  - `/api/v1/classification/predict`
  - `/api/v1/association/rules`
  - `/api/v1/clustering/segments`
  - `/api/v1/timeseries/forecast`

## 10. 自動テスト実行ベースライン（現行）

### 10.1 バックエンド

実行:

```powershell
cd backend
pytest
```

現行ベースライン:
- 45 テスト通過（追加モジュールの成功/異常系、学習エンドポイント行列を含む）

### 10.2 フロントエンド

実行:

```powershell
npm run test:run
```

現行ベースライン:
- 29 テスト通過（主要画面、サービス層、エラー表示経路を含む）

### 10.3 E2E

初回準備:

```powershell
npm run e2e:install
```

日常実行:

```powershell
npm run e2e
```

現行ベースライン:
- 7 Playwright シナリオ通過
  - happy flow: upload -> dashboard -> forecast -> recommend
  - failure flow: 未学習時の forecast/recommend エラー表示
  - advanced analytics success: classification -> association -> clustering -> timeseries
  - advanced analytics failure: 上記 4 モジュールのエラー表示経路
  - home success: 概要/総額予測表示 + dashboard への遷移
  - home warning: データ未準備時の Refresh 警告表示
  - dashboard failure: 売上予測再学習失敗の可視化

## 11. 次段階の拡張方針

- バックエンドのコア層単体テストを拡充
  - `excel_parser.py`
  - `quality.py`
  - `feature_engine.py`
  - `training_events.py`
- フロントで Dashboard の「WebSocket切断 + ポーリングフォールバック」の複合ケースを追加
- E2E 追加候補
  - 複数バージョン切替フロー
  - Dashboard リアルタイム更新（WS 切断後のポーリング復旧含む）
  - 大規模データアップロード時の性能ベースライン
- CI 方針
  - PR: バックエンド/フロント単体テスト
  - 夜間: 大規模データを含むフル E2E
