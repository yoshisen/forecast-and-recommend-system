import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import ForecastPage from "./ForecastPage";

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
    XAxis: () => <div />,
    YAxis: () => <div />,
    CartesianGrid: () => <div />,
    Tooltip: () => <div />,
    Legend: () => <div />,
  };
});

const forecastPayload = {
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
};

const prophetTrainPayload = {
  success: true,
  data: {
    summary: {
      method: "prophet",
    },
  },
};

const prophetForecastPayload = {
  success: true,
  data: {
    dates: ["2026-01-01", "2026-01-02", "2026-01-03"],
    yhat: [9, 10, 11],
    yhat_upper: [11, 12, 13],
    yhat_lower: [7, 8, 9],
    trend: [8, 9, 10],
  },
};

const renderPage = (entry = "/forecast") => {
  return render(
    <MemoryRouter
      initialEntries={[entry]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/forecast" element={<ForecastPage />} />
      </Routes>
    </MemoryRouter>
  );
};

describe("ForecastPage", () => {
  beforeEach(() => {
    getForecast.mockReset();
    trainTimeSeriesModel.mockReset();
    getTimeSeriesForecast.mockReset();

    getForecast.mockResolvedValue(forecastPayload);
    trainTimeSeriesModel.mockResolvedValue(prophetTrainPayload);
    getTimeSeriesForecast.mockResolvedValue(prophetForecastPayload);
  });

  it("auto-submits when product_id and store_id are in query params", async () => {
    renderPage("/forecast?product_id=P000001&store_id=LUMI0001&horizon=7");

    await waitFor(() => {
      expect(getForecast).toHaveBeenCalledWith("P000001", "LUMI0001", 7, false, null, "lightgbm");
    });
  });

  it("submits manual form values", async () => {
    renderPage();

    fireEvent.change(screen.getByPlaceholderText("例: P000001"), {
      target: { value: "P999999" },
    });
    fireEvent.change(screen.getByPlaceholderText("例: LUMI0001"), {
      target: { value: "LUMI9999" },
    });

    fireEvent.click(screen.getByRole("button", { name: "LightGBM で予測" }));

    await waitFor(() => {
      expect(getForecast).toHaveBeenCalledWith("P999999", "LUMI9999", 14, false, null, "lightgbm");
    });

    expect(await screen.findByText(/累積予測推移/)).toBeInTheDocument();
  });

  it("runs sarima algorithm when selected", async () => {
    renderPage();

    fireEvent.change(screen.getByPlaceholderText("例: P000001"), {
      target: { value: "P999999" },
    });
    fireEvent.change(screen.getByPlaceholderText("例: LUMI0001"), {
      target: { value: "LUMI9999" },
    });

    fireEvent.click(screen.getByRole("button", { name: "SARIMA" }));
    fireEvent.click(screen.getByRole("button", { name: "SARIMA で予測" }));

    await waitFor(() => {
      expect(getForecast).toHaveBeenCalledWith("P999999", "LUMI9999", 14, false, null, "sarima");
    });
  });

  it("runs xgboost sales algorithm when selected", async () => {
    renderPage();

    fireEvent.change(screen.getByPlaceholderText("例: P000001"), {
      target: { value: "P999999" },
    });
    fireEvent.change(screen.getByPlaceholderText("例: LUMI0001"), {
      target: { value: "LUMI9999" },
    });

    fireEvent.click(screen.getByRole("button", { name: "XGBoost" }));
    fireEvent.click(screen.getByRole("button", { name: "XGBoost で予測" }));

    await waitFor(() => {
      expect(getForecast).toHaveBeenCalledWith("P999999", "LUMI9999", 14, false, null, "xgboost");
    });
  });

  it("runs prophet algorithm from merged page", async () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Prophet" }));
    fireEvent.click(screen.getByRole("button", { name: "Prophet で予測" }));

    await waitFor(() => {
      expect(trainTimeSeriesModel).toHaveBeenCalledTimes(1);
      expect(getTimeSeriesForecast).toHaveBeenCalledWith(14);
    });

    expect(await screen.findByText(/予測結果（Prophet）/)).toBeInTheDocument();
  });
});