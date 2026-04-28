import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { message } from "antd";

import AssociationPage from "./AssociationPage";

const {
  trainAssociationModel,
  getAssociationRules,
  getAssociationRecommendations,
} = vi.hoisted(() => ({
  trainAssociationModel: vi.fn(),
  getAssociationRules: vi.fn(),
  getAssociationRecommendations: vi.fn(),
}));

vi.mock("../services/api", () => ({
  trainAssociationModel,
  getAssociationRules,
  getAssociationRecommendations,
}));

const renderPage = (entry = "/association") => {
  return render(
    <MemoryRouter
      initialEntries={[entry]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/association" element={<AssociationPage />} />
      </Routes>
    </MemoryRouter>
  );
};

describe("AssociationPage", () => {
  beforeEach(() => {
    trainAssociationModel.mockReset();
    getAssociationRules.mockReset();
    getAssociationRecommendations.mockReset();

    trainAssociationModel.mockResolvedValue({
      success: true,
      data: {
        summary: {
          n_transactions: 100,
          n_products: 20,
          n_rules: 1,
          n_itemsets: 5,
        },
      },
    });

    getAssociationRules.mockResolvedValue({
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
    });

    getAssociationRecommendations.mockResolvedValue({
      success: true,
      data: {
        product_id: "P000010",
        count: 2,
        recommendations: [
          {
            product_id: "P000020",
            confidence: 0.51,
            lift: 1.6,
            support: 0.09,
          },
          {
            product_id: "P000030",
            confidence: 0.28,
            lift: 0.9,
            support: 0.05,
          },
        ],
      },
    });
  });

  it("trains and loads association rules", async () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "ルールを学習して読み込む" }));

    await waitFor(() => {
      expect(trainAssociationModel).toHaveBeenCalledTimes(1);
      expect(getAssociationRules).toHaveBeenCalledWith(100);
    });

    expect(await screen.findByText(/ルール数: 1/)).toBeInTheDocument();
  });

  it("submits cross-sell recommendation query", async () => {
    renderPage();

    fireEvent.change(screen.getByPlaceholderText("例: P00001"), {
      target: { value: "P000010" },
    });
    fireEvent.click(screen.getByRole("button", { name: "推薦を取得" }));

    await waitFor(() => {
      expect(getAssociationRecommendations).toHaveBeenCalledWith("P000010", 10);
    });

    expect(await screen.findByText("商品ID: P000010")).toBeInTheDocument();
  });

  it("shows error message when recommendation query fails", async () => {
    const errorSpy = vi.spyOn(message, "error").mockImplementation(() => {});
    getAssociationRecommendations.mockRejectedValueOnce(new Error("recommend failed"));

    renderPage();
    fireEvent.change(screen.getByPlaceholderText("例: P00001"), {
      target: { value: "P000010" },
    });
    fireEvent.click(screen.getByRole("button", { name: "推薦を取得" }));

    await waitFor(() => {
      expect(errorSpy).toHaveBeenCalled();
    });
    expect(errorSpy.mock.calls.at(-1)?.[0]).toContain("推薦取得に失敗しました");

    errorSpy.mockRestore();
  });

  it("filters recommendations by minimum confidence and minimum lift", async () => {
    renderPage();

    fireEvent.change(screen.getByPlaceholderText("例: P00001"), {
      target: { value: "P000010" },
    });
    fireEvent.click(screen.getByRole("button", { name: "推薦を取得" }));

    expect(await screen.findByText("商品ID: P000010")).toBeInTheDocument();
    expect(screen.getByText(/表示件数: 2/)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("min-confidence"), {
      target: { value: "0.5" },
    });

    await waitFor(() => {
      expect(screen.getByText(/表示件数: 1/)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("min-lift"), {
      target: { value: "2" },
    });

    await waitFor(() => {
      expect(screen.getByText("フィルタ条件に一致する推薦がありません")).toBeInTheDocument();
    });
  });
});