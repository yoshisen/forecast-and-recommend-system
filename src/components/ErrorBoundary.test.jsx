import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import ErrorBoundary from "./ErrorBoundary";

const ThrowOnRender = () => {
  throw new Error("boundary test error");
};

describe("ErrorBoundary", () => {
  it("renders fallback UI and triggers onReset callback", () => {
    const onReset = vi.fn();
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorBoundary onReset={onReset}>
        <ThrowOnRender />
      </ErrorBoundary>
    );

    expect(screen.getByText("表示エラーが発生しました")).toBeInTheDocument();
    expect(screen.getByText("boundary test error")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "再読み込み" }));
    expect(onReset).toHaveBeenCalledTimes(1);

    consoleErrorSpy.mockRestore();
  });
});