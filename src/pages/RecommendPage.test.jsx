import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import RecommendPage from "./RecommendPage";

const { getRecommendations, getPopularRecommendations } = vi.hoisted(() => ({
  getRecommendations: vi.fn(),
  getPopularRecommendations: vi.fn(),
}));

vi.mock("../services/api", () => ({
  getRecommendations,
  getPopularRecommendations,
}));

const renderPage = (entry = "/recommend") => {
  return render(
    <MemoryRouter
      initialEntries={[entry]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/recommend" element={<RecommendPage />} />
      </Routes>
    </MemoryRouter>
  );
};

describe("RecommendPage", () => {
  beforeEach(() => {
    getRecommendations.mockReset();
    getPopularRecommendations.mockReset();

    getRecommendations.mockResolvedValue({
      success: true,
      data: {
        customer_id: "C000001",
        recommendations: [
          {
            product_id: "P000001",
            product_name: "Milk",
            category: "Dairy",
            price: 120,
            score: 0.91,
          },
        ],
        method: "hybrid",
      },
    });

    getPopularRecommendations.mockResolvedValue({
      success: true,
      data: {
        recommendations: [
          {
            product_id: "P000002",
            product_name: "Bread",
            category: "Bakery",
            price: 180,
            score: 0.83,
          },
        ],
      },
    });
  });

  it("auto-submits when customer_id is present in query params", async () => {
    renderPage("/recommend?customer_id=C000001&top_k=5");

    await waitFor(() => {
      expect(getRecommendations).toHaveBeenCalledWith("C000001", 5);
    });
  });

  it("submits manual recommendation form", async () => {
    renderPage();

    fireEvent.change(screen.getByPlaceholderText("例: C000001"), {
      target: { value: "C999999" },
    });

    fireEvent.click(screen.getByRole("button", { name: /推薦取得/ }));

    await waitFor(() => {
      expect(getRecommendations).toHaveBeenCalledWith("C999999", 10);
    });
  });

  it("loads popular recommendations when popular button is clicked", async () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: /人気商品表示/ }));

    await waitFor(() => {
      expect(getPopularRecommendations).toHaveBeenCalledWith(10);
    });

    expect(await screen.findByText("P000002")).toBeInTheDocument();
  });
});