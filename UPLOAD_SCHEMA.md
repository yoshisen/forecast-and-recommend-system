# Excel アップロード規約と特徴量命名ブループリント

本ドキュメントは「先にデータ規約を固定し、後からコードを段階的に整合させる」ための運用基準です。

適用範囲:

- 現在稼働している処理系（Parser + FeatureEngine + Models + APIs）
- 次フェーズで追加する拡張特徴量（多粒度・多テーマ）

---

## 0. バージョン方針（重要）

- v1: 現行互換レイヤー（今の実装で確実に動くことを優先）
- v2: 拡張計画レイヤー（先に Excel 側へ列を追加し、後でコード側が順次消費）

要点:
- まずはアップロードデータを前方互換にする
- 次に parser / feature_engine / model を段階的に追従させる

---

## 1. 命名規約（固定）

### 1.1 列名フォーマット

- すべて小文字の snake_case を使用
- 空白、ハイフン、camelCase は使用しない
- ID 列は `_id` サフィックスで統一

### 1.2 時間系フィールド

- 日付: `*_date`（例: `transaction_date`）
- 時刻: `*_time`（例: `transaction_time`）
- タイムスタンプ: `*_timestamp`（例: `event_timestamp`）

### 1.3 金額・数量・率

- 日本円金額は `*_jpy` で統一（例: `total_amount_jpy`）
- 数量は `quantity`、単価は `unit_price_jpy` を推奨
- 率は `*_rate`（0-1）または `*_pct`（0-100）を採用し、意味を明記

### 1.4 真偽値・ウィンドウ

- 真偽値は `is_*` または `*_flag`
- ローリング窓は `*_7d`, `*_14d`, `*_30d`, `*_90d`

### 1.5 粒度

- 各ファクト表は粒度主キーを明確化
- 同一テーマの異なる粒度特徴量は、粒度を明示するサフィックスか別表で管理

---

## 2. 標準 Sheet 名と認識ルール

Parser はシート名を「小文字化 + 空白/アンダースコア/ハイフン除去」で正規化してから別名照合します。
未認識 Sheet は現時点でスキップされます。

### 2.1 現在認識される標準 Sheet

| 標準 Sheet | 主な別名例 | 説明 |
|---|---|---|
| transaction | transaction, transactions, orders, order, 取引 | 受注ヘッダ |
| transaction_items | transaction_items, order_items, transaction_details, 取引明細 | 受注明細（最重要ファクト） |
| product | product, products, item, sku, 商品 | 商品ディメンション |
| customer | customer, customers, user, member, 顧客 | 顧客ディメンション |
| store | store, stores, shop, location, 店舗 | 店舗ディメンション |
| promotion | promotion, promotions, campaign | 施策ディメンション |
| inventory | inventory, stock, stocklevel, 在庫 | 在庫スナップショット |
| weather | weather, climate, 天気 | 日次天候 |
| holiday | holiday, holidays, festival, 祝日 | 日次休日 |
| customer_behavior | customer_behavior, userbehavior, 顧客行動 | 顧客行動拡張 |
| product_association | product_association, association, 商品関連 | 商品関連拡張 |
| review | review, reviews, feedback, rating, レビュー | レビュー拡張 |

### 2.2 v2 で追加予定の標準 Sheet

現状 parser が未対応でも、将来拡張の対象として以下を予約:

- product_store_daily_features
- customer_daily_features
- customer_monthly_features
- product_daily_features
- store_daily_features

---

## 3. 現行コードで動かすための最小要件（v1 必須）

### 3.1 解析最低要件

- `transaction_items`
- `product`

### 3.2 タスク別の最低学習要件（task_registry 準拠）

| タスク | 必須 Sheet |
|---|---|
| forecast | transaction_items + transaction + product |
| recommend | transaction_items + transaction + customer + product |
| classification | transaction_items + transaction + customer |
| association | transaction_items + transaction + product |
| clustering | transaction_items + transaction + customer |
| prophet(timeseries) | transaction_items + transaction + product |

### 3.3 タスク別の推奨最小列（現行実装準拠）

1. Forecast
- transaction_items: `transaction_id`, `product_id`, `quantity`
- transaction: `transaction_id`, `transaction_date`, `store_id`
- 任意金額列: `line_total`, `line_total_jpy`, `total_amount`, `total_amount_jpy`

2. Recommend
- transaction_items: `transaction_id`, `product_id`, `quantity`（または購買回数へ集約可能）
- transaction: `transaction_id`, `customer_id`
- product: `product_id`（推奨: `category_level1`, `retail_price_jpy`）

3. Classification
- transaction_items: `transaction_id`, `product_id`, `quantity`, 任意金額列
- transaction: `transaction_id`, `customer_id`, `transaction_date`
- customer: `customer_id`（推奨: `age`, `gender`, `registration_date`）

4. Association
- transaction_items: `transaction_id`, `product_id`

5. Clustering
- transaction_items: `transaction_id`, `product_id`, `quantity`, 任意金額列
- transaction: `transaction_id`, `customer_id`, `transaction_date`
- customer: `customer_id`（推奨: `age`, `gender`）

6. Prophet TimeSeries
- transaction_items: `transaction_id` + 任意金額列
- transaction: `transaction_id`, `transaction_date`

注記:
- readiness のゲート条件とモデル内部依存が完全一致しない場合があります。
- 実務上は「まず readiness を満たす -> 次にモデル必要列を補完」の順で対応してください。

---

## 4. 標準フィールド辞書（拡張版, v2 目標）

### 4.1 transaction（粒度 = transaction_id）

主キー:
- `transaction_id`（PK）, `customer_id`（FK）, `store_id`（FK）

推奨列:

- `transaction_date`, `transaction_time`
- `total_amount_jpy`, `discount_amount_jpy`, `tax_amount_jpy`
- `payment_method`, `cashier_id`, `receipt_number`
- `coupon_id`, `waon_points_used`, `waon_points_earned`
- `channel`（offline/online/omni）
- `basket_size_items`

### 4.2 transaction_items（粒度 = transaction_item_id）

主キー:
- `transaction_item_id`（PK）, `transaction_id`（FK）, `product_id`（FK）

推奨列:

- `quantity`
- `unit_price_jpy`, `original_price_jpy`, `discount_price_jpy`
- `line_total_jpy`
- `promotion_id`, `return_flag`
- `product_barcode`
- `tax_rate`, `tax_included_flag`
- `item_margin_jpy`

### 4.3 product（粒度 = product_id）

主キー:
- `product_id`（PK）

推奨列:

- `product_name`, `brand`
- `category_level1`, `category_level2`, `category_level3`
- `retail_price_jpy`, `cost_price_jpy`
- `unit_of_measure`, `package_size`, `weight_g`
- `supplier_id`
- `shelf_life_days`, `perishable_flag`, `seasonal_flag`
- `organic_flag`, `private_label_flag`
- `launch_date`

### 4.4 customer（粒度 = customer_id）

主キー:
- `customer_id`（PK）

推奨列:

- `registration_date`, `birth_date`, `age`, `gender`
- `income_level`, `education_level`, `occupation`
- `marital_status`, `household_size`, `has_children`, `children_age_range`
- `prefecture`, `city`, `postcode`
- `loyalty_tier`, `total_lifetime_value_jpy`
- `preferred_store_id`, `waon_card_number`

### 4.5 store（粒度 = store_id）

主キー:
- `store_id`（PK）

推奨列:

- `store_name`, `store_type`
- `prefecture`, `city`, `postcode`
- `latitude`, `longitude`
- `store_size_sqm`, `parking_spaces`
- `location_type`, `opening_date`, `opening_hours`
- `average_foot_traffic`

### 4.6 promotion（粒度 = promotion_id）

主キー:
- `promotion_id`（PK）

推奨列:

- `promotion_name`, `promotion_type`
- `start_date`, `end_date`
- `discount_rate`
- `min_purchase_amount_jpy`, `max_discount_jpy`
- `target_category_level1`, `target_store_id`

### 4.7 inventory（粒度 = product_id + store_id + snapshot_date）

主キー候補:
- `inventory_id` または (`product_id`, `store_id`, `snapshot_date`)

推奨列:

- `product_id`, `store_id`
- `stock_quantity`, `reorder_point`, `max_stock_level`
- `last_restock_date`, `expiry_date`
- `shelf_location`, `days_on_shelf`
- `stockout_flag`, `inventory_turnover_30d`

### 4.8 weather（粒度 = prefecture + date）

主キー:
- `prefecture + date`

推奨列:

- `temperature_celsius`, `humidity_percent`, `precipitation_mm`
- `weather_condition`
- `wind_speed_mps`, `pressure_hpa`

### 4.9 holiday（粒度 = date）

主キー:
- `date`

推奨列:

- `holiday_name`, `holiday_type`
- `is_long_weekend`
- `holiday_weight`（業務定義）

### 4.10 customer_behavior（粒度 = customer_id + snapshot_date）

主キー候補:
- `customer_id + snapshot_date`

推奨列:

- `avg_basket_size`
- `avg_transaction_value_jpy`
- `purchase_frequency`
- `last_purchase_date`, `days_since_last_purchase`
- `preferred_categories`
- `price_sensitivity`
- `promotion_response_rate`
- `channel_preference`
- `churn_risk_score`

### 4.11 product_association（粒度 = product_id_a + product_id_b + snapshot_date）

推奨列:

- `product_id_a`, `product_id_b`
- `support`, `confidence`, `lift`
- `co_purchase_count_30d`

### 4.12 review（粒度 = review_id）

推奨列:

- `review_id`, `product_id`, `customer_id`
- `review_date`, `rating_score`
- `sentiment_score`
- `review_channel`

---

## 5. 多粒度特徴量レイヤー（重点）

目的:
- 同一テーマを複数粒度で保持し、「1列ですべてを表す」設計を避ける。

### 5.1 推奨粒度レイヤー

1. イベント粒度（L0）
- テーブル: `transaction_items`
- キー: `transaction_item_id`

2. 受注粒度（L1）
- テーブル: `transaction`
- キー: `transaction_id`

3. 商品×店舗×日粒度（L2）
- テーブル: `product_store_daily_features`
- キー: `product_id + store_id + date`

4. 顧客×日粒度（L2.5）
- テーブル: `customer_daily_features`
- キー: `customer_id + date`

5. 顧客×月粒度（L3）
- テーブル: `customer_monthly_features`
- キー: `customer_id + month`

6. 商品×日粒度（L3）
- テーブル: `product_daily_features`
- キー: `product_id + date`

### 5.2 粒度別の代表列

1. product_store_daily_features
- `sales_quantity`
- `sales_amount_jpy`
- `avg_selling_price_jpy`
- `promo_item_share`
- `stockout_flag`
- `lag_1`, `lag_7`, `lag_14`, `lag_28`
- `rolling_mean_7`, `rolling_std_7`, `rolling_mean_30`
- `is_holiday`, `is_weekend`
- `temperature_celsius`, `precipitation_mm`

2. customer_daily_features
- `customer_order_count`
- `customer_amount_jpy`
- `customer_distinct_products`
- `customer_discount_share`
- `customer_recency_days`

3. customer_monthly_features
- `monthly_amount_jpy`
- `monthly_order_count`
- `monthly_visit_days`
- `monthly_category_diversity`
- `monthly_return_rate`
- `churn_risk_score`

4. product_daily_features
- `product_sales_quantity`
- `product_sales_amount_jpy`
- `product_avg_price_jpy`
- `product_discount_rate`
- `product_return_rate`
- `product_store_coverage`

---

## 6. 同一テーマを粒度別に命名する例

テーマ: 価格・割引

1. 明細粒度
- `unit_price_jpy`
- `discount_price_jpy`
- `line_total_jpy`

2. 受注粒度
- `total_amount_jpy`
- `discount_amount_jpy`
- `discount_rate`

3. 商品×店舗×日粒度
- `avg_selling_price_jpy`
- `promo_discount_rate_7d`
- `price_volatility_30d`

4. 顧客×月粒度
- `customer_avg_ticket_30d`
- `customer_discount_share_30d`

同様に、需要・販促反応・在庫リスク・再購買傾向も粒度別で管理してください。

---

## 7. 別名とフィールドマッピング拡張（コード整合向け）

Parser の `FIELD_MAPPINGS` へ段階的に追加推奨:

- `total_amount_jpy -> total_amount`
- `line_total_jpy -> line_total`
- `retail_price_jpy -> retail_price`
- `cost_price_jpy -> cost_price`
- `discount_amount_jpy -> discount_amount`
- `avg_transaction_value_jpy -> avg_transaction_value`
- `transaction_datetime -> transaction_timestamp`

汎用別名ファミリー推奨:

- `*_amt`, `*_amount`, `*_amount_jpy`
- `*_qty`, `quantity`, `units`
- `txn_id`, `order_id -> transaction_id`
- `sku_id`, `item_id -> product_id`

---

## 8. 推奨アップロード構成

### 8.1 Bronze（最小運用）

- `transaction_items`, `transaction`, `product`, `customer`

### 8.2 Silver（実運用推奨）

- Bronze + `store`, `promotion`, `holiday`, `weather`, `inventory`

### 8.3 Gold（拡張フル）

- Silver + `customer_behavior`, `review`, `product_association`
- さらに多粒度特徴量表（`product_store_daily_features` など）

---

## 9. 現行バックエンド契約との整合（2026-04）

この節は、現在実装済みの API 契約を前後工程の基準として示します。

### 9.1 アップロード応答（POST /api/v1/upload）

既存の `parse_report` / `quality_report` / `task_readiness` に加えて、次を返却:

- `field_readiness`（summary + sheets + tasks）
- `task_field_readiness`（`field_readiness.tasks` のフラット表示）
- `warnings` に `missing_required_field` が含まれる場合あり
- CSV 名未一致時、エラーまたは warning に候補 Sheet 名を付与
- ZIP 警告 `zip_skipped_files` に `suggested_sheet_names_by_file` を付与
- `warnings` / `auto_training` に `reason_code`, `reason_ja` を付与

サンプル:

```json
{
  "success": true,
  "version": "20260424_102233",
  "task_readiness": {
    "forecast": { "can_train": true, "missing_required_sheets": [] }
  },
  "field_readiness": {
    "summary": {
      "available_sheets": ["transaction", "transaction_items", "product"],
      "sheet_present_count": 3,
      "sheet_expected_count": 12,
      "task_trainable_count": 2,
      "task_total_count": 6
    },
    "tasks": {
      "forecast": {
        "can_train_with_fields": true,
        "missing_required_sheets": [],
        "missing_required_fields_by_sheet": {},
        "reason_code": "ok",
        "reason": null,
        "reason_ja": "問題ありません"
      },
      "recommend": {
        "can_train_with_fields": false,
        "missing_required_sheets": ["customer"],
        "missing_required_fields_by_sheet": {
          "transaction": ["customer_id"]
        },
        "reason_code": "missing_required_sheets",
        "reason": "missing_required_sheets: customer",
        "reason_ja": "必須シート不足: customer"
      }
    }
  }
}
```

### 9.2 readiness（GET /api/v1/data/readiness）

タスク全体の状態確認用。返却には `field_readiness` も含む。

```json
{
  "success": true,
  "data": {
    "version": "20260424_102233",
    "task_readiness": {
      "forecast": { "can_train": true }
    },
    "training": {
      "forecast": "pending"
    },
    "field_readiness": {
      "summary": {
        "task_trainable_count": 2,
        "task_total_count": 6
      },
      "tasks": {
        "forecast": {
          "can_train_with_fields": true,
          "reason_code": "ok",
          "reason": null,
          "reason_ja": "問題ありません"
        }
      }
    }
  }
}
```

### 9.3 field-readiness（GET /api/v1/data/field-readiness）

UploadSchemaGuide と Dashboard の主要データ源。

```json
{
  "success": true,
  "data": {
    "version": "20260424_102233",
    "field_readiness": {
      "summary": {
        "available_sheets": ["transaction", "transaction_items", "product"],
        "sheet_present_count": 3,
        "sheet_expected_count": 12,
        "task_trainable_count": 2,
        "task_total_count": 6
      },
      "tasks": {
        "classification": {
          "missing_required_sheets": ["customer"],
          "missing_required_fields_by_sheet": {
            "transaction": ["customer_id"]
          },
          "can_train_with_fields": false,
          "reason_code": "missing_required_sheets",
          "reason": "missing_required_sheets: customer",
          "reason_ja": "必須シート不足: customer"
        }
      }
    }
  }
}
```

### 9.4 フロントの現行利用箇所

- UploadPage: upload 応答の `task_field_readiness` を表示
- UploadSchemaGuidePage: `/data/upload-schema` と `/data/field-readiness` を併用表示
- Dashboard: `/data/summary` の後に `/data/field-readiness` を取得し、阻害要因を表示

### 9.5 後方互換制約（変更時必須）

削除禁止:
- `field_readiness.tasks.<task>.can_train_with_fields`
- `field_readiness.tasks.<task>.missing_required_fields_by_sheet`
- `task_readiness.<task>.reason`

維持推奨:
- `field_readiness.tasks.<task>.reason_code`
- `field_readiness.tasks.<task>.reason_ja`
- `task_readiness.<task>.reason_code`
- `task_readiness.<task>.reason_ja`
- `auto_training.<task>.reason_code`
- `auto_training.<task>.reason_ja`

新規項目追加は可能ですが、上記互換キーは保持してください。

---

## 10. 次フェーズのコード整合タスク

1. Parser 整合
- Sheet 別名とフィールドマッピングを拡張
- `*_jpy`, `*_rate`, `*_flag` の型規則を強化

2. FeatureEngine 整合
- 多粒度特徴量テーブルを直接消費
- join キー優先順位とフォールバック規則を明文化

3. Model 整合
- forecast/recommend/classification/clustering/prophet の feature contract を明文化
- 欠損特徴量時の段階的劣化戦略を導入

4. Quality/Validation 整合
- 粒度単位の主キー一意性チェックを追加
- テーブル間の時点整合（date アライン）チェックを追加

### 補足 FAQ

Q. アップロード後にタスクが skip される
- A. 必須 Sheet または必須列不足が原因です。第 3 節の最小要件を満たしてください。

Q. 予測や時系列学習が失敗する
- A. `transaction_date` または金額列不足が主因です。`transaction` と `transaction_items` の基礎列を確認してください。

Q. 推薦品質が低い
- A. `customer_id/product_id` だけでは弱いです。商品属性・行動特徴量・販促情報を追加してください。

Q. 似た列名なのに認識されない
- A. 別名辞書に未登録の可能性があります。短期は規約名へリネームし、中期で parser 側へ別名追加してください。
