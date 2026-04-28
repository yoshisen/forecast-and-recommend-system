import { describe, expect, it } from "vitest";

import { formatReadinessReason } from "./readinessReason";

describe("readinessReason ユーティリティ", () => {
  it("reason_ja がある場合は最優先で返す", () => {
    expect(formatReadinessReason("missing_required_fields", "日本語理由", "missing_required_fields")).toBe("日本語理由");
  });

  it("reason_code から日本語文言を返す", () => {
    expect(formatReadinessReason(null, null, "missing_required_sheets")).toBe("必須シート不足");
    expect(formatReadinessReason(null, null, "missing_required_fields")).toBe("必須フィールド不足");
  });

  it("接頭辞付き reason を日本語へ変換する", () => {
    expect(formatReadinessReason("missing_required_sheets: customer, product")).toBe(
      "必須シート不足: customer, product"
    );
    expect(formatReadinessReason("missing_required_fields: transaction[customer_id]")).toBe(
      "必須フィールド不足: transaction[customer_id]"
    );
  });

  it("未知の reason はそのまま返す", () => {
    expect(formatReadinessReason("custom_reason_code")).toBe("custom_reason_code");
  });
});
