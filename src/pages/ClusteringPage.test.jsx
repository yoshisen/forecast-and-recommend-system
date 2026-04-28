import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { message } from "antd";

import ClusteringPage from "./ClusteringPage";

const {
  trainClusteringModel,
  getClusterSegments,
  getClusterPoints,
  getCustomerCluster,
} = vi.hoisted(() => ({
  trainClusteringModel: vi.fn(),
  getClusterSegments: vi.fn(),
  getClusterPoints: vi.fn(),
  getCustomerCluster: vi.fn(),
}));

vi.mock("../services/api", () => ({
  trainClusteringModel,
  getClusterSegments,
  getClusterPoints,
  getCustomerCluster,
}));

vi.mock("recharts", () => {
  const Wrapper = ({ children }) => <div>{children}</div>;
  return {
    ResponsiveContainer: Wrapper,
    ScatterChart: Wrapper,
    Scatter: () => <div />,
    CartesianGrid: () => <div />,
    Tooltip: () => <div />,
    XAxis: () => <div />,
    YAxis: () => <div />,
    Legend: () => <div />,
  };
});

const renderPage = (entry = "/clustering") => {
  return render(
    <MemoryRouter
      initialEntries={[entry]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/clustering" element={<ClusteringPage />} />
      </Routes>
    </MemoryRouter>
  );
};

describe("ClusteringPage", () => {
  beforeEach(() => {
    trainClusteringModel.mockReset();
    getClusterSegments.mockReset();
    getClusterPoints.mockReset();
    getCustomerCluster.mockReset();

    trainClusteringModel.mockResolvedValue({
      success: true,
      data: {
        summary: {
          n_customers: 10,
          n_clusters: 2,
          silhouette: 0.56,
          inertia: 124.5,
        },
      },
    });

    getClusterSegments.mockResolvedValue({
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
    });

    getClusterPoints.mockResolvedValue({
      success: true,
      data: {
        points: [
          { customer_id: "C000001", cluster: 0, pca_x: 0.2, pca_y: 0.4 },
          { customer_id: "C000002", cluster: 1, pca_x: -0.1, pca_y: 0.7 },
        ],
      },
    });

    getCustomerCluster.mockResolvedValue({
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
    });
  });

  it("trains clustering model and loads cluster assets", async () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "クラスタリングを学習" }));

    await waitFor(() => {
      expect(trainClusteringModel).toHaveBeenCalledWith(4);
      expect(getClusterSegments).toHaveBeenCalledTimes(1);
      expect(getClusterPoints).toHaveBeenCalledWith(2000);
    });
  });

  it("queries customer cluster assignment", async () => {
    renderPage("/clustering?customer_id=C000001");

    fireEvent.click(screen.getByRole("button", { name: "顧客クラスタを照会" }));

    await waitFor(() => {
      expect(getCustomerCluster).toHaveBeenCalledWith("C000001");
    });

    expect(await screen.findByText("クラスタ: 1")).toBeInTheDocument();
  });

  it("shows error message when customer cluster query fails", async () => {
    const errorSpy = vi.spyOn(message, "error").mockImplementation(() => {});
    getCustomerCluster.mockRejectedValueOnce(new Error("query failed"));

    renderPage("/clustering?customer_id=C000001");
    fireEvent.click(screen.getByRole("button", { name: "顧客クラスタを照会" }));

    await waitFor(() => {
      expect(errorSpy).toHaveBeenCalled();
    });
    expect(errorSpy.mock.calls.at(-1)?.[0]).toContain("照会に失敗しました");

    errorSpy.mockRestore();
  });
});