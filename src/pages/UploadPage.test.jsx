import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import UploadPage from "./UploadPage";

const { uploadExcel, navigateMock, clipboardWriteMock } = vi.hoisted(() => ({
  uploadExcel: vi.fn(),
  navigateMock: vi.fn(),
  clipboardWriteMock: vi.fn(),
}));

vi.mock("../services/api", () => ({
  uploadExcel,
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

const triggerFileUpload = (container, filename = "small_test.xlsx") => {
  const fileInput = container.querySelector('input[type="file"]');
  expect(fileInput).toBeTruthy();

  const file = new File(["dummy"], filename, {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });

  fireEvent.change(fileInput, {
    target: { files: [file] },
  });
};

const triggerMultiFileUpload = (container, filenames = ["transaction_items.csv", "transaction.csv"]) => {
  const fileInput = container.querySelector('input[type="file"]');
  expect(fileInput).toBeTruthy();

  const files = filenames.map(
    (name) =>
      new File(["dummy"], name, {
        type: "text/csv",
      })
  );

  fireEvent.change(fileInput, {
    target: { files },
  });
};

describe("UploadPage ページ", () => {
  beforeEach(() => {
    uploadExcel.mockReset();
    navigateMock.mockReset();
    clipboardWriteMock.mockReset();

    Object.defineProperty(window.navigator, "clipboard", {
      value: {
        writeText: clipboardWriteMock,
      },
      configurable: true,
    });
  });

  it("アップロード成功時に onUploadSuccess を呼び出し dashboard へ遷移する", async () => {
    uploadExcel.mockResolvedValue({
      success: true,
      version: "v_upload_1",
      parse_report: { ok: true },
      quality_report: { ok: true },
      validation_result: { ok: true },
      warnings: [],
      metadata: {
        filename: "small_test.xlsx",
        timestamp: "2026-01-01T00:00:00",
        available_sheets: ["product", "transaction"],
      },
    });

    const onUploadSuccess = vi.fn();
    const { container } = render(<UploadPage onUploadSuccess={onUploadSuccess} />);

    triggerFileUpload(container);

    await waitFor(() => {
      expect(uploadExcel).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(onUploadSuccess).toHaveBeenCalledWith("v_upload_1");
    });
    await waitFor(
      () => {
        expect(navigateMock).toHaveBeenCalledWith("/dashboard");
      },
      { timeout: 2000 }
    );
  });

  it("アップロード失敗時にエラー UI を表示する", async () => {
    uploadExcel.mockRejectedValue(new Error("upload failed"));
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    const { container } = render(<UploadPage />);
    triggerFileUpload(container);

    expect(await screen.findByText("アップロードに失敗しました")).toBeInTheDocument();
    expect(navigateMock).not.toHaveBeenCalled();

    consoleErrorSpy.mockRestore();
  });

  it("タスク別フィールド診断テーブルに不足項目を表示する", async () => {
    uploadExcel.mockResolvedValue({
      success: true,
      version: "v_upload_2",
      parse_report: { ok: true },
      quality_report: { ok: true },
      validation_result: { ok: true },
      warnings: [],
      metadata: {
        filename: "small_test.xlsx",
        timestamp: "2026-01-01T00:00:00",
        available_sheets: ["transaction_items", "product"],
      },
      task_field_readiness: {
        forecast: {
          can_train_with_fields: false,
          reason: "missing_required_fields",
          reason_code: "missing_required_fields",
          reason_ja: "必須フィールド不足（アップロード表示）",
          missing_required_sheets: ["transaction"],
          missing_required_fields_by_sheet: {
            transaction: ["transaction_date", "store_id"],
            transaction_items: ["transaction_id"],
          },
        },
      },
    });

    const { container } = render(<UploadPage />);
    triggerFileUpload(container);

    expect(await screen.findByText("フィールド診断（タスク別）")).toBeInTheDocument();
    const rowCell = await screen.findByText("forecast");
    const row = rowCell.closest("tr");

    expect(row).toBeTruthy();
    expect(row).toHaveTextContent("必須フィールド不足（アップロード表示）");
    expect(row).toHaveTextContent("transaction");
    expect(row).toHaveTextContent(
      "transaction[transaction_date, store_id]; transaction_items[transaction_id]"
    );
  });

  it("不足項目コピーボタンでクリップボードへ内容を出力する", async () => {
    clipboardWriteMock.mockResolvedValue(undefined);
    uploadExcel.mockResolvedValue({
      success: true,
      version: "v_upload_3",
      parse_report: { ok: true },
      quality_report: { ok: true },
      validation_result: { ok: true },
      warnings: [],
      metadata: {
        filename: "small_test.xlsx",
        timestamp: "2026-01-01T00:00:00",
        available_sheets: ["transaction_items", "product"],
      },
      task_field_readiness: {
        recommend: {
          can_train_with_fields: false,
          reason: "missing_required_fields",
          reason_code: "missing_required_fields",
          reason_ja: "必須フィールド不足（コピー表示）",
          missing_required_sheets: ["customer"],
          missing_required_fields_by_sheet: {
            transaction: ["customer_id"],
          },
          missing_required_field_hints: {
            transaction: [
              {
                field: "customer_id",
                aliases: ["customerid", "customer_id", "cust_id"],
              },
            ],
          },
        },
      },
    });

    const { container } = render(<UploadPage />);
    triggerFileUpload(container);

    const copyButton = await screen.findByRole("button", { name: "不足項目をコピー" });
    fireEvent.click(copyButton);

    await waitFor(() => {
      expect(clipboardWriteMock).toHaveBeenCalledTimes(1);
    });
    expect(clipboardWriteMock.mock.calls[0][0]).toContain("タスク: recommend");
    expect(clipboardWriteMock.mock.calls[0][0]).toContain("理由: 必須フィールド不足（コピー表示）");
    expect(clipboardWriteMock.mock.calls[0][0]).toContain("不足必須フィールド: transaction[customer_id]");
  });

  it("ZIP未認識CSV警告で候補シート名リストを表示する", async () => {
    uploadExcel.mockResolvedValue({
      success: true,
      version: "v_upload_4",
      parse_report: { ok: true },
      quality_report: { ok: true },
      validation_result: { ok: true },
      warnings: [
        {
          type: "zip_skipped_files",
          message: "ZIP 内で未認識の CSV をスキップ: unknown_sheet.csv",
          impact: "ファイル名に標準シート名を含めると取り込みできます（例: transaction_items.csv）",
          suggested_sheet_names_by_file: {
            "unknown_sheet.csv": ["transaction_items", "transaction", "product"],
          },
        },
      ],
      metadata: {
        filename: "bundle.zip",
        timestamp: "2026-01-01T00:00:00",
        available_sheets: ["transaction_items", "product"],
      },
    });

    const { container } = render(<UploadPage />);
    triggerFileUpload(container, "bundle.zip");

    expect(await screen.findByText("ZIP 内で未認識の CSV をスキップ: unknown_sheet.csv")).toBeInTheDocument();
    expect(await screen.findByText("候補シート名:")).toBeInTheDocument();
    expect(await screen.findByText("unknown_sheet.csv: transaction_items, transaction, product")).toBeInTheDocument();
  });

  it("複数CSV選択時に1回のアップロード要求として送信する", async () => {
    uploadExcel.mockResolvedValue({
      success: true,
      version: "v_upload_5",
      parse_report: { ok: true, source_format: "zip" },
      quality_report: { ok: true },
      validation_result: { ok: true },
      warnings: [],
      metadata: {
        filename: "multi_csv_upload_2_files.zip",
        timestamp: "2026-01-01T00:00:00",
        available_sheets: ["transaction_items", "transaction", "product", "customer"],
      },
    });

    const { container } = render(<UploadPage />);
    triggerMultiFileUpload(container);

    await waitFor(() => {
      expect(uploadExcel).toHaveBeenCalledTimes(1);
    });

    const firstArg = uploadExcel.mock.calls[0][0];
    expect(Array.isArray(firstArg)).toBe(true);
    expect(firstArg).toHaveLength(2);
  });
});