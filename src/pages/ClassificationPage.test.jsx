import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { message } from "antd";

import ClassificationPage from "./ClassificationPage";

const {
  trainClassificationModel,
  predictCustomerClass,
  getClassificationThresholdScan,
  tuneClassificationThreshold,
} = vi.hoisted(() => ({
  trainClassificationModel: vi.fn(),
  predictCustomerClass: vi.fn(),
  getClassificationThresholdScan: vi.fn(),
  tuneClassificationThreshold: vi.fn(),
}));

vi.mock("../services/api", () => ({
  trainClassificationModel,
  predictCustomerClass,
  getClassificationThresholdScan,
  tuneClassificationThreshold,
}));

const renderPage = (entry = "/classification") => {
  return render(
    <MemoryRouter
      initialEntries={[entry]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/classification" element={<ClassificationPage />} />
      </Routes>
    </MemoryRouter>
  );
};

describe("ClassificationPage", () => {
  beforeEach(() => {
    trainClassificationModel.mockReset();
    predictCustomerClass.mockReset();
    getClassificationThresholdScan.mockReset();
    tuneClassificationThreshold.mockReset();

    trainClassificationModel.mockResolvedValue({
      success: true,
      data: {
        metrics: {
          precision: 0.81,
          recall: 0.72,
          f1: 0.76,
          roc_auc: 0.84,
        },
      },
    });

    predictCustomerClass.mockResolvedValue({
      success: true,
      data: {
        prediction: 1,
        probability: 0.92,
        threshold: 0.42,
      },
    });

    getClassificationThresholdScan.mockResolvedValue({
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
    });

    tuneClassificationThreshold.mockResolvedValue({
      success: true,
      data: { threshold: 0.6 },
    });
  });

  it("trains model and renders metric stats", async () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "分類モデルを学習" }));

    await waitFor(() => {
      expect(trainClassificationModel).toHaveBeenCalledTimes(1);
    });

    expect(await screen.findByText("ROC-AUC")).toBeInTheDocument();
  });

  it("submits prediction using query param defaults", async () => {
    renderPage("/classification?customer_id=C000321&threshold=0.42");

    fireEvent.click(screen.getByRole("button", { name: /予\s*測/ }));

    await waitFor(() => {
      expect(predictCustomerClass).toHaveBeenCalledWith("C000321", 0.42);
    });
  });

  it("runs threshold scan and renders best threshold tag", async () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "しきい値をスキャン" }));

    await waitFor(() => {
      expect(getClassificationThresholdScan).toHaveBeenCalledWith(0.05);
    });

    expect(await screen.findByText(/Best F1 Threshold: 0.4/)).toBeInTheDocument();
  });

  it("shows error message when prediction request fails", async () => {
    const errorSpy = vi.spyOn(message, "error").mockImplementation(() => {});
    predictCustomerClass.mockRejectedValueOnce(new Error("predict failed"));

    renderPage("/classification?customer_id=C000321&threshold=0.42");
    fireEvent.click(screen.getByRole("button", { name: /予\s*測/ }));

    await waitFor(() => {
      expect(errorSpy).toHaveBeenCalled();
    });
    expect(errorSpy.mock.calls.at(-1)?.[0]).toContain("予測に失敗しました");

    errorSpy.mockRestore();
  });
});