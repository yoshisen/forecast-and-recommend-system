const fs = require("node:fs/promises");
const { test, expect } = require("@playwright/test");

async function mockHappyApiRoutes(page) {
  await page.route("**/api/v1/upload", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        version: "v_e2e_001",
        parse_report: { sheets: 6 },
        quality_report: { score: 0.95 },
        validation_result: { ok: true },
        warnings: [],
        metadata: {
          filename: "small_test.xlsx",
          timestamp: "2026-01-01T00:00:00",
          available_sheets: [
            "product",
            "transaction",
            "transaction_items",
            "customer",
            "store",
            "promotion",
          ],
        },
      }),
    });
  });

  await page.route("**/api/v1/data/summary**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          version: "v_e2e_001",
          uploaded_at: "2026-01-01T00:00:00",
          filename: "small_test.xlsx",
          overall_summary: {
            total_sheets: 6,
            total_rows: 1200,
            total_fields: 45,
          },
          sheet_summaries: {
            product: { rows: 80, columns: 10 },
            transaction: { rows: 1200, columns: 8 },
          },
          training: {
            forecast: "completed",
            recommend: "completed",
            classification: "completed",
            association: "completed",
            clustering: "completed",
            prophet: "completed",
          },
          task_readiness: {
            forecast: { can_train: true },
            recommend: { can_train: true },
            classification: { can_train: true },
            association: { can_train: true },
            clustering: { can_train: true },
            prophet: { can_train: true },
          },
        },
      }),
    });
  });

  await page.route("**/api/v1/forecast**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          product_id: "P000001",
          store_id: "LUMI0001",
          method: "mock-model",
          horizon: 7,
          predictions: [10, 11, 12, 13, 14, 15, 16],
          dates: [
            "2026-01-01",
            "2026-01-02",
            "2026-01-03",
            "2026-01-04",
            "2026-01-05",
            "2026-01-06",
            "2026-01-07",
          ],
          total_forecast: 91,
          avg_daily_forecast: 13,
        },
      }),
    });
  });

  await page.route("**/api/v1/recommend?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          customer_id: "C000001",
          recommendations: [
            {
              product_id: "P000011",
              product_name: "Milk",
              category: "Dairy",
              price: 120,
              score: 0.91,
            },
          ],
          method: "hybrid",
        },
      }),
    });
  });

  await page.route("**/api/v1/recommend/popular**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          recommendations: [
            {
              product_id: "P000022",
              product_name: "Bread",
              category: "Bakery",
              price: 200,
              score: 0.85,
            },
          ],
        },
      }),
    });
  });
}

async function mockAdvancedAnalyticsSuccessApiRoutes(page) {
  await page.route("**/api/v1/classification/train**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          metrics: {
            precision: 0.81,
            recall: 0.72,
            f1: 0.76,
            roc_auc: 0.84,
          },
        },
      }),
    });
  });

  await page.route("**/api/v1/classification/predict**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          prediction: 1,
          probability: 0.92,
          threshold: 0.42,
        },
      }),
    });
  });

  await page.route("**/api/v1/classification/threshold-scan**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          rows: [
            {
              threshold: 0.4,
              precision: 0.8,
              recall: 0.7,
              f1: 0.7467,
              positive_predictions: 11,
            },
          ],
          best_by_f1: {
            threshold: 0.4,
            f1: 0.7467,
          },
        },
      }),
    });
  });

  await page.route("**/api/v1/classification/tune-threshold**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: { threshold: 0.6 },
      }),
    });
  });

  await page.route("**/api/v1/association/train**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          summary: {
            n_transactions: 100,
            n_products: 20,
            n_rules: 1,
            n_itemsets: 5,
          },
        },
      }),
    });
  });

  await page.route("**/api/v1/association/rules**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          rules: [
            {
              antecedents: ["P000001"],
              consequents: ["P000002"],
              support: 0.11,
              confidence: 0.42,
              lift: 1.33,
            },
          ],
          summary: {
            n_transactions: 100,
            n_products: 20,
            n_rules: 1,
            n_itemsets: 5,
          },
        },
      }),
    });
  });

  await page.route("**/api/v1/association/recommendations**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          product_id: "P000010",
          count: 1,
          recommendations: [
            {
              product_id: "P000020",
              confidence: 0.51,
              lift: 1.6,
              support: 0.09,
            },
          ],
        },
      }),
    });
  });

  await page.route("**/api/v1/clustering/train**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          summary: {
            n_customers: 10,
            n_clusters: 2,
            silhouette: 0.56,
            inertia: 124.5,
          },
        },
      }),
    });
  });

  await page.route("**/api/v1/clustering/segments**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          segments: [
            {
              cluster: 0,
              count: 6,
              profile: { transaction_count: 3.2, total_amount: 1500, recency_days: 6 },
            },
            {
              cluster: 1,
              count: 4,
              profile: { transaction_count: 1.8, total_amount: 800, recency_days: 12 },
            },
          ],
          summary: {
            n_customers: 10,
            n_clusters: 2,
            silhouette: 0.56,
            inertia: 124.5,
          },
        },
      }),
    });
  });

  await page.route("**/api/v1/clustering/points**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          points: [
            { customer_id: "C000001", cluster: 0, pca_x: 0.2, pca_y: 0.4 },
            { customer_id: "C000002", cluster: 1, pca_x: -0.1, pca_y: 0.7 },
          ],
        },
      }),
    });
  });

  await page.route("**/api/v1/clustering/customer/**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          customer_id: "C000001",
          cluster: 1,
          pca_x: 0.2,
          pca_y: 0.4,
          profile: {
            avg_ticket: 23.4,
            transaction_count: 3,
          },
        },
      }),
    });
  });

  await page.route("**/api/v1/timeseries/train**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          summary: {
            n_points: 180,
            start_date: "2025-01-01",
            end_date: "2025-12-31",
            method: "prophet",
          },
        },
      }),
    });
  });

  await page.route("**/api/v1/timeseries/forecast**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          dates: ["2026-01-01", "2026-01-02"],
          yhat: [100, 105],
          yhat_upper: [120, 126],
          yhat_lower: [90, 95],
          trend: [98, 102],
        },
      }),
    });
  });
}

async function mockHomeSuccessApiRoutes(page) {
  await page.route("**/api/v1/data/summary**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          version: "v_home_001",
          uploaded_at: "2026-01-01T00:00:00",
          filename: "seed.xlsx",
          overall_summary: {
            total_sheets: 6,
            total_rows: 1200,
            total_fields: 45,
          },
          sheet_summaries: {
            product: { rows: 80, columns: 10 },
            transaction: { rows: 1200, columns: 8 },
          },
          training: {
            forecast: "completed",
            recommend: "completed",
            classification: "completed",
            association: "completed",
            clustering: "completed",
            prophet: "completed",
          },
          task_readiness: {
            forecast: { can_train: true },
            recommend: { can_train: true },
            classification: { can_train: true },
            association: { can_train: true },
            clustering: { can_train: true },
            prophet: { can_train: true },
          },
        },
      }),
    });
  });

  await page.route("**/api/v1/data/samples**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          samples: {
            product_ids: ["P000321"],
            store_ids: ["LUMI0123"],
            customer_ids: ["C000123"],
            top_pairs: [{ product_id: "P000321", store_id: "LUMI0123" }],
          },
        },
      }),
    });
  });

  await page.route("**/api/v1/data/forecast-total**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          dates: ["2026-01-01", "2026-01-02", "2026-01-03"],
          totals: [100, 110, 120],
          cumulative_total: 330,
          avg_daily_total: 110,
          method: "mock-total",
        },
      }),
    });
  });
}

async function mockDashboardTrainFailureApiRoutes(page) {
  await page.route("**/api/v1/data/summary**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          version: "v_dash_001",
          uploaded_at: "2026-01-01T00:00:00",
          filename: "seed.xlsx",
          overall_summary: {
            total_sheets: 6,
            total_rows: 1200,
            total_fields: 45,
          },
          sheet_summaries: {
            product: { rows: 80, columns: 10 },
            transaction: { rows: 1200, columns: 8 },
          },
          training: {
            forecast: "completed",
            recommend: "completed",
            classification: "completed",
            association: "completed",
            clustering: "completed",
            prophet: "completed",
          },
          task_readiness: {
            forecast: { can_train: true },
            recommend: { can_train: true },
            classification: { can_train: true },
            association: { can_train: true },
            clustering: { can_train: true },
            prophet: { can_train: true },
          },
        },
      }),
    });
  });

  await page.route("**/api/v1/forecast/train**", async (route) => {
    await route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ detail: "mock forecast train failure" }),
    });
  });
}

test("happy flow: upload -> dashboard -> forecast -> recommend", async ({ page }, testInfo) => {
  await mockHappyApiRoutes(page);

  await page.goto("/upload");

  const uploadFilePath = testInfo.outputPath("small_test.xlsx");
  await fs.writeFile(uploadFilePath, "mock xlsx content", "utf-8");

  await page.setInputFiles('input[type="file"]', uploadFilePath);

  await expect(page.getByText("解析完了")).toBeVisible();
  await page.waitForURL("**/dashboard");
  await expect(page.getByText("训练任务控制台")).toBeVisible();

  await page.goto("/forecast?product_id=P000001&store_id=LUMI0001&horizon=7");
  await expect(page.getByText("予測結果サマリー")).toBeVisible();
  await expect(page.getByText("P000001")).toBeVisible();

  await page.goto("/recommend?customer_id=C000001&top_k=5");
  await expect(page.getByText("P000011")).toBeVisible();
});

test("failure flow: untrained model errors are shown", async ({ page }) => {
  await page.route("**/api/v1/forecast**", async (route) => {
    await route.fulfill({
      status: 400,
      contentType: "application/json",
      body: JSON.stringify({ detail: "予測モデルが訓練されていません" }),
    });
  });

  await page.route("**/api/v1/recommend?**", async (route) => {
    await route.fulfill({
      status: 400,
      contentType: "application/json",
      body: JSON.stringify({ detail: "推薦モデルが訓練されていません" }),
    });
  });

  await page.goto("/forecast?product_id=P999999&store_id=LUMI0001&horizon=7");
  await expect(page.locator(".ant-message")).toContainText("予測エラー");

  await page.goto("/recommend?customer_id=C999999&top_k=5");
  await expect(page.locator(".ant-message")).toContainText("推薦エラー");
});

test("advanced analytics success flow: classification -> association -> clustering -> timeseries", async ({ page }) => {
  await mockAdvancedAnalyticsSuccessApiRoutes(page);

  await page.goto("/classification?customer_id=C000321&threshold=0.42");
  await page.getByRole("button", { name: "训练分类模型" }).click();
  await expect(page.getByText("ROC-AUC")).toBeVisible();
  await page.getByRole("button", { name: /预\s*测/ }).click();
  await expect(page.getByText("Probability: 0.9200")).toBeVisible();
  await page.getByRole("button", { name: "扫描阈值" }).click();
  await expect(page.getByText(/Best F1 Threshold: 0.4/)).toBeVisible();

  await page.goto("/association?product_id=P000010&top_k=10");
  await page.getByRole("button", { name: "训练并加载关联规则" }).click();
  await expect(page.getByText("Rules: 1")).toBeVisible();
  await page.getByRole("button", { name: "查询推荐" }).click();
  await expect(page.getByText("Product: P000010")).toBeVisible();
  await expect(page.getByText("P000020")).toBeVisible();

  await page.goto("/clustering?customer_id=C000001");
  await page.getByRole("button", { name: "训练聚类模型" }).click();
  await expect(page.getByText("Silhouette")).toBeVisible();
  await page.getByRole("button", { name: "查询客户簇" }).click();
  await expect(page.getByText("Cluster: 1")).toBeVisible();

  await page.goto("/timeseries");
  await page.getByRole("button", { name: "训练 Prophet 模型" }).click();
  await expect(page.getByText("2025-12-31")).toBeVisible();
  await page.getByRole("button", { name: "预测未来区间" }).click();
  await expect(page.getByText("尚无时序预测结果")).toHaveCount(0);
});

test("advanced analytics failure flow: error messages are surfaced", async ({ page }) => {
  await page.route("**/api/v1/classification/predict**", async (route) => {
    await route.fulfill({
      status: 400,
      contentType: "application/json",
      body: JSON.stringify({ detail: "分类模型未训练" }),
    });
  });

  await page.route("**/api/v1/association/recommendations**", async (route) => {
    await route.fulfill({
      status: 400,
      contentType: "application/json",
      body: JSON.stringify({ detail: "关联规则模型未训练" }),
    });
  });

  await page.route("**/api/v1/clustering/customer/**", async (route) => {
    await route.fulfill({
      status: 400,
      contentType: "application/json",
      body: JSON.stringify({ detail: "聚类模型未训练" }),
    });
  });

  await page.route("**/api/v1/timeseries/forecast**", async (route) => {
    await route.fulfill({
      status: 400,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Prophet 模型未训练" }),
    });
  });

  await page.goto("/classification?customer_id=C000321&threshold=0.42");
  await page.getByRole("button", { name: /预\s*测/ }).click();
  await expect(page.locator(".ant-message")).toContainText("预测失败");

  await page.goto("/association?product_id=P000010&top_k=10");
  await page.getByRole("button", { name: "查询推荐" }).click();
  await expect(page.locator(".ant-message")).toContainText("推荐失败");

  await page.goto("/clustering?customer_id=C000001");
  await page.getByRole("button", { name: "查询客户簇" }).click();
  await expect(page.locator(".ant-message")).toContainText("查询失败");

  await page.goto("/timeseries");
  await page.getByRole("button", { name: "预测未来区间" }).click();
  await expect(page.locator(".ant-message")).toContainText("时序预测失败");
});

test("home success flow: summary and quick action navigation work", async ({ page }) => {
  await mockHomeSuccessApiRoutes(page);

  await page.goto("/");

  await expect(page.getByText("AI Excel Analytics Workbench")).toBeVisible();
  await expect(page.getByText("v_home_001")).toBeVisible();
  await expect(page.getByText("Cumulative Total")).toBeVisible();
  await expect(page.getByText("mock-total")).toBeVisible();

  await page.getByRole("button", { name: "Training Monitor" }).click();
  await page.waitForURL("**/dashboard");
  await expect(page.getByText("训练任务控制台")).toBeVisible();
});

test("home warning flow: refresh without data shows warning message", async ({ page }) => {
  await page.route("**/api/v1/data/summary**", async (route) => {
    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "no data" }),
    });
  });

  await page.goto("/");

  await expect(page.getByText("还没有可用数据")).toBeVisible();
  await page.getByRole("button", { name: "Refresh" }).click();
  await expect(page.locator(".ant-message")).toContainText("请先上传数据后再刷新预测");
});

test("dashboard failure flow: retrain failure is surfaced", async ({ page }) => {
  await mockDashboardTrainFailureApiRoutes(page);

  await page.goto("/dashboard");
  await expect(page.getByText("训练任务控制台")).toBeVisible();

  const forecastTaskCard = page.locator(".ant-col").filter({ hasText: "销售预测" }).first();
  await forecastTaskCard.getByRole("button", { name: "重新训练" }).click();

  await expect(page.locator(".ant-message")).toContainText("训练失败");
});