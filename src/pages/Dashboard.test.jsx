import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { message } from "antd";

import Dashboard from "./Dashboard";

const {
  getDataSummary,
  getDataFieldReadiness,
  trainForecastModel,
  trainRecommender,
  trainClassificationModel,
  trainAssociationModel,
  trainClusteringModel,
  trainTimeSeriesModel,
  navigateMock,
  clipboardWriteMock,
} = vi.hoisted(() => ({
  getDataSummary: vi.fn(),
  getDataFieldReadiness: vi.fn(),
  trainForecastModel: vi.fn(),
  trainRecommender: vi.fn(),
  trainClassificationModel: vi.fn(),
  trainAssociationModel: vi.fn(),
  trainClusteringModel: vi.fn(),
  trainTimeSeriesModel: vi.fn(),
  navigateMock: vi.fn(),
  clipboardWriteMock: vi.fn(),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock("../services/api", () => ({
  getDataSummary,
  getDataFieldReadiness,
  trainForecastModel,
  trainRecommender,
  trainClassificationModel,
  trainAssociationModel,
  trainClusteringModel,
  trainTimeSeriesModel,
}));

vi.mock("../components/ForecastMetricsViz", () => ({
  default: () => <div data-testid="forecast-metrics-viz" />,
}));

vi.mock("../components/RecommenderMatrixViz", () => ({
  default: () => <div data-testid="recommender-matrix-viz" />,
}));

class MockWebSocket {
  static instances = [];

  constructor(url) {
    this.url = url;
    this.onmessage = null;
    this.onclose = null;
    MockWebSocket.instances.push(this);
  }

  close = vi.fn();
}

const createSummaryData = (training = { forecast: "completed", forecast_progress: 100 }) => ({
  version: "v_test_001",
  uploaded_at: "2026-01-01T00:00:00",
  filename: "seed.xlsx",
  overall_summary: {
    total_sheets: 3,
    total_rows: 120,
    total_fields: 45,
  },
  sheet_summaries: {
    product: { rows: 20, columns: 5 },
    transaction: { rows: 60, columns: 6 },
  },
  training,
  task_readiness: {
    forecast: { can_train: true },
    recommend: { can_train: false, reason: "missing_required_sheets: customer" },
    classification: { can_train: false, reason: "missing_required_sheets: customer" },
    association: { can_train: false, reason: "missing_required_sheets: product" },
    clustering: { can_train: false, reason: "missing_required_sheets: customer" },
    prophet: { can_train: false, reason: "missing_required_sheets: product" },
  },
});

describe("Dashboard ページ", () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    global.WebSocket = MockWebSocket;

    getDataSummary.mockReset();
    getDataFieldReadiness.mockReset();
    navigateMock.mockReset();
    clipboardWriteMock.mockReset();
    trainForecastModel.mockReset();
    trainRecommender.mockReset();
    trainClassificationModel.mockReset();
    trainAssociationModel.mockReset();
    trainClusteringModel.mockReset();
    trainTimeSeriesModel.mockReset();

    Object.defineProperty(window.navigator, "clipboard", {
      value: {
        writeText: clipboardWriteMock,
      },
      configurable: true,
    });

    getDataSummary.mockResolvedValue({
      success: true,
      data: createSummaryData(),
    });
    getDataFieldReadiness.mockResolvedValue({
      success: true,
      data: {
        field_readiness: {
          tasks: {
            forecast: {
              can_train_with_fields: true,
              reason: "ok",
              missing_required_fields_by_sheet: {},
            },
            recommend: {
              can_train_with_fields: false,
              reason: "missing_required_fields",
              reason_code: "missing_required_fields",
              reason_ja: "必須フィールド不足（テスト表示）",
              missing_required_sheets: [],
              missing_required_fields_by_sheet: {
                transaction_items: ["product_id"],
              },
              missing_required_field_hints: {
                transaction_items: [
                  {
                    field: "product_id",
                    aliases: ["productid", "product_id", "prod_id", "item_id", "sku_id"],
                  },
                ],
              },
            },
          },
        },
      },
    });
    trainForecastModel.mockResolvedValue({ success: true, data: {} });
  });

  it("サマリーを読み込み主要項目を表示する", async () => {
    render(<Dashboard />);

    await waitFor(() => {
      expect(getDataSummary).toHaveBeenCalledTimes(1);
    });

    expect(await screen.findByText("seed.xlsx")).toBeInTheDocument();
    expect(screen.getByText("v_test_001")).toBeInTheDocument();
    expect(screen.getByText("総シート数")).toBeInTheDocument();
    expect(screen.getByText(/フィールド診断サマリー/)).toBeInTheDocument();
    expect(screen.getByText("現在、以下のタスクで必須フィールドが不足しています")).toBeInTheDocument();
    expect(screen.getByText("必須フィールド不足（テスト表示）")).toBeInTheDocument();
    expect(screen.getByText(/transaction_items\[product_id\]/)).toBeInTheDocument();
    expect(screen.getByText(/認識可能な別名ヒント/)).toBeInTheDocument();
    expect(screen.getByText(/sku_id/)).toBeInTheDocument();
  });

  it("フィールド診断サマリーから規約ページへ遷移する", async () => {
    render(<Dashboard />);

    const schemaButton = await screen.findByRole("button", { name: "フィールド規約を見る" });
    fireEvent.click(schemaButton);

    expect(navigateMock).toHaveBeenCalledWith("/upload-schema");
  });

  it("ブロック中タスク行からタスク指定付き規約ページへ遷移する", async () => {
    render(<Dashboard />);

    const rowLinkButton = await screen.findByRole("button", { name: "このタスクの規約を見る" });
    fireEvent.click(rowLinkButton);

    expect(navigateMock).toHaveBeenCalledWith("/upload-schema?task=recommend");
  });

  it("ブロック中タスクの不足項目をクリップボードへコピーする", async () => {
    clipboardWriteMock.mockResolvedValue(undefined);
    render(<Dashboard />);

    const copyButton = await screen.findByRole("button", { name: "不足項目をコピー" });
    fireEvent.click(copyButton);

    await waitFor(() => {
      expect(clipboardWriteMock).toHaveBeenCalledTimes(1);
    });
    expect(clipboardWriteMock.mock.calls[0][0]).toContain("タスク: recommend");
    expect(clipboardWriteMock.mock.calls[0][0]).toContain("不足必須フィールド: transaction_items[product_id]");
  });

  it("再学習ボタン押下で forecast 学習を実行する", async () => {
    render(<Dashboard />);

    const retrainButton = await screen.findByRole("button", { name: "再学習" });
    fireEvent.click(retrainButton);

    await waitFor(() => {
      expect(trainForecastModel).toHaveBeenCalledTimes(1);
    });
  });

  it("学習中に WebSocket が切断されたらポーリング通知を表示する", async () => {
    getDataSummary.mockResolvedValue({
      success: true,
      data: createSummaryData({ forecast: "running", forecast_progress: 35 }),
    });

    render(<Dashboard />);

    await screen.findByText("seed.xlsx");

    const ws = MockWebSocket.instances[0];
    await act(async () => {
      ws.onclose?.();
    });

    expect(
      await screen.findByText(/WebSocket 切断時はポーリングで状態を同期します/)
    ).toBeInTheDocument();
  });

  it("未アップロード時の 404 ではエラートーストを出さず空状態を表示する", async () => {
    const errorSpy = vi.spyOn(message, "error").mockImplementation(() => {});
    getDataSummary.mockRejectedValueOnce({
      response: {
        status: 404,
      },
      message: "Request failed with status code 404",
    });

    render(<Dashboard />);

    expect(await screen.findByText("データがありません")).toBeInTheDocument();
    expect(screen.getByText("先にExcelファイルをアップロードしてください")).toBeInTheDocument();
    expect(errorSpy).not.toHaveBeenCalled();

    errorSpy.mockRestore();
  });
});