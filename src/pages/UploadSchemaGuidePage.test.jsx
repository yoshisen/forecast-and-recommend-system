import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import UploadSchemaGuidePage from "./UploadSchemaGuidePage";

const { getUploadSchemaGuide, getDataFieldReadiness } = vi.hoisted(() => ({
  getUploadSchemaGuide: vi.fn(),
  getDataFieldReadiness: vi.fn(),
}));

vi.mock("../services/api", () => ({
  getUploadSchemaGuide,
  getDataFieldReadiness,
}));

const renderPage = (route = "/upload-schema") => {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <UploadSchemaGuidePage />
    </MemoryRouter>
  );
};

describe("UploadSchemaGuidePage ページ", () => {
  beforeEach(() => {
    getUploadSchemaGuide.mockReset();
    getDataFieldReadiness.mockReset();
  });

  it("バックエンド返却値からフィールド規約を表示する", async () => {
    getUploadSchemaGuide.mockResolvedValue({
      success: true,
      data: {
        naming_rules: {
          style: "snake_case",
          amount_suffix: "*_jpy",
        },
        sheets: [
          {
            sheet: "transaction_items",
            aliases: ["transaction_items", "order_items"],
            description: "Order line items",
            minimum_fields: ["transaction_id", "product_id"],
            recommended_fields: ["quantity", "line_total_jpy"],
            optional_fields: ["promotion_id"],
          },
        ],
        task_requirements: {
          forecast: {
            required_sheets: ["transaction_items", "transaction", "product"],
            usefulness: "critical",
          },
          recommend: {
            required_sheets: ["transaction_items", "transaction", "customer", "product"],
            usefulness: "critical",
          },
        },
        field_catalog: [
          {
            field: "forecast_only_field",
            aliases: ["forecast_only_field", "forecast_alias"],
            utility: "critical",
            used_by: ["forecast"],
            granularity: ["transaction", "transaction_items"],
          },
          {
            field: "recommend_only_field",
            aliases: ["recommend_only_field", "recommend_alias"],
            utility: "high",
            used_by: ["recommend"],
            granularity: ["transaction_items"],
          },
        ],
        degrade_policy: [
          {
            condition: "Missing optional fields",
            behavior: "Skip optional joins",
          },
        ],
        notes: ["Users can upload fewer columns."],
      },
    });

    getDataFieldReadiness.mockResolvedValue({
      success: true,
      data: {
        field_readiness: {
          tasks: {
            forecast: {
              can_train_with_fields: false,
              reason: "missing_required_fields",
              reason_code: "missing_required_fields",
              reason_ja: "必須フィールド不足（規約ページ表示）",
              missing_required_sheets: [],
              missing_required_fields_by_sheet: {
                transaction: ["transaction_date"],
              },
            },
          },
        },
      },
    });

    renderPage("/upload-schema?task=recommend");

    expect(await screen.findByText("Excelアップロード項目規約ガイド")).toBeInTheDocument();
    expect(screen.getByText("Sheet: transaction_items")).toBeInTheDocument();
    expect(screen.getByText("フィールド説明（日本語・サンプル）")).toBeInTheDocument();
    expect(screen.getByText("取引ID")).toBeInTheDocument();
    expect(screen.getAllByText("transaction_id: T202501010001").length).toBeGreaterThan(0);
    expect(screen.getAllByText("recommend_only_field").length).toBeGreaterThan(0);
    expect(screen.queryByText("forecast_only_field")).not.toBeInTheDocument();
    expect(screen.getByText("現在表示中: 1 件")).toBeInTheDocument();
    expect(screen.getAllByText("critical").length).toBeGreaterThan(0);
    expect(screen.getByText("現在アップロード済みデータのフィールド診断")).toBeInTheDocument();
  });

  it("utility クエリで有用度フィルタを適用する", async () => {
    getUploadSchemaGuide.mockResolvedValue({
      success: true,
      data: {
        naming_rules: {
          style: "snake_case",
        },
        sheets: [],
        task_requirements: {
          forecast: {
            required_sheets: ["transaction_items"],
            usefulness: "critical",
          },
          recommend: {
            required_sheets: ["transaction_items"],
            usefulness: "critical",
          },
        },
        field_catalog: [
          {
            field: "critical_field",
            aliases: ["critical_field"],
            utility: "critical",
            used_by: ["forecast"],
            granularity: ["transaction_items"],
          },
          {
            field: "high_field",
            aliases: ["high_field"],
            utility: "high",
            used_by: ["recommend"],
            granularity: ["transaction_items"],
          },
        ],
        degrade_policy: [],
        notes: [],
      },
    });

    getDataFieldReadiness.mockResolvedValue({
      success: true,
      data: {
        field_readiness: {
          tasks: {},
        },
      },
    });

    renderPage("/upload-schema?utility=critical");

    expect(await screen.findByText("Excelアップロード項目規約ガイド")).toBeInTheDocument();
    expect(screen.getAllByText("critical_field").length).toBeGreaterThan(0);
    expect(screen.queryByText("high_field")).not.toBeInTheDocument();
    expect(screen.getByText("現在表示中: 1 件")).toBeInTheDocument();
  });

  it("エンドポイント失敗時にエラー表示へ遷移する", async () => {
    getUploadSchemaGuide.mockRejectedValue(new Error("network failed"));

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("フィールド規約の読み込みに失敗しました")).toBeInTheDocument();
    });
  });
});
