import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import TimeSeriesPage from "./TimeSeriesPage";

const { getForecast, trainTimeSeriesModel, getTimeSeriesForecast } = vi.hoisted(() => ({
  getForecast: vi.fn(),
  trainTimeSeriesModel: vi.fn(),
  getTimeSeriesForecast: vi.fn(),
}));

vi.mock("../services/api", () => ({
  getForecast,
  trainTimeSeriesModel,
  getTimeSeriesForecast,
}));

vi.mock("recharts", () => {
  const Wrapper = ({ children }) => <div>{children}</div>;
  return {
    ResponsiveContainer: Wrapper,
    LineChart: Wrapper,
    Line: () => <div />,
    CartesianGrid: () => <div />,
    Tooltip: () => <div />,
    XAxis: () => <div />,
    YAxis: () => <div />,
    Legend: () => <div />,
  };
});

describe("TimeSeriesPage", () => {
  const renderPage = (entry = "/timeseries") => {
    return render(
      <MemoryRouter
        initialEntries={[entry]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/timeseries" element={<TimeSeriesPage />} />
        </Routes>
      </MemoryRouter>
    );
  };

  beforeEach(() => {
    getForecast.mockReset();
    trainTimeSeriesModel.mockReset();
    getTimeSeriesForecast.mockReset();

    getForecast.mockResolvedValue({
      success: true,
      data: {
        product_id: "P000001",
        store_id: "LUMI0001",
        method: "mock-model",
        horizon: 7,
        predictions: [10, 11, 12],
        dates: ["2026-01-01", "2026-01-02", "2026-01-03"],
        total_forecast: 33,
        avg_daily_forecast: 11,
      },
    });

    trainTimeSeriesModel.mockResolvedValue({
      success: true,
      data: {
        summary: {
          n_points: 180,
          start_date: "2025-01-01",
          end_date: "2025-12-31",
          method: "prophet",
        },
      },
    });

    getTimeSeriesForecast.mockResolvedValue({
      success: true,
      data: {
        dates: ["2026-01-01", "2026-01-02"],
        yhat: [100, 105],
        yhat_upper: [120, 126],
        yhat_lower: [90, 95],
        trend: [98, 102],
      },
    });
  });

  it("defaults to prophet mode and runs forecast", async () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Prophet で予測" }));

    await waitFor(() => {
      expect(trainTimeSeriesModel).toHaveBeenCalledTimes(1);
      expect(getTimeSeriesForecast).toHaveBeenCalledWith(14);
    });

    expect(await screen.findByText(/予測結果（Prophet）/)).toBeInTheDocument();
  });

  it("can switch to sales algorithm from merged page", async () => {
    renderPage("/timeseries?product_id=P000001&store_id=LUMI0001&horizon=7");

    fireEvent.click(screen.getByRole("button", { name: "LightGBM" }));
    fireEvent.click(screen.getByRole("button", { name: "LightGBM で予測" }));

    await waitFor(() => {
      expect(getForecast).toHaveBeenCalledWith("P000001", "LUMI0001", 7, false, null, "lightgbm");
    });

    expect(await screen.findByText(/予測結果（LightGBM）/)).toBeInTheDocument();
  });
});