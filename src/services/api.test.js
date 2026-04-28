import { beforeEach, describe, expect, it, vi } from "vitest";

const { mockApiGet, mockApiPost, mockAxiosGet, mockAxiosPost } = vi.hoisted(() => ({
  mockApiGet: vi.fn(),
  mockApiPost: vi.fn(),
  mockAxiosGet: vi.fn(),
  mockAxiosPost: vi.fn(),
}));

vi.mock("axios", () => {
  return {
    default: {
      create: vi.fn(() => ({
        get: mockApiGet,
        post: mockApiPost,
      })),
      get: mockAxiosGet,
      post: mockAxiosPost,
    },
  };
});

import {
  getDataFieldReadiness,
  getForecast,
  getUploadSchemaGuide,
  getTaskReadiness,
  getTimeSeriesForecast,
  trainClusteringModel,
  uploadExcel,
} from "./api";


describe("API service parameter mapping", () => {
  beforeEach(() => {
    mockApiGet.mockReset();
    mockApiPost.mockReset();
    mockAxiosGet.mockReset();
    mockAxiosPost.mockReset();

    mockApiGet.mockResolvedValue({ data: { success: true } });
    mockApiPost.mockResolvedValue({ data: { success: true } });
    mockAxiosGet.mockResolvedValue({ data: { success: true } });
    mockAxiosPost.mockResolvedValue({ data: { success: true } });
  });

  it("maps forecast params correctly", async () => {
    await getForecast("P000001", "S000001", 7, true, "v1", "xgboost");

    expect(mockApiGet).toHaveBeenCalledWith("/forecast", {
      params: {
        product_id: "P000001",
        store_id: "S000001",
        horizon: 7,
        use_baseline: true,
        algorithm: "xgboost",
        version: "v1",
      },
    });
  });

  it("maps clustering train params correctly", async () => {
    await trainClusteringModel(6, "v2");

    expect(mockApiPost).toHaveBeenCalledWith("/clustering/train", null, {
      params: {
        n_clusters: 6,
        version: "v2",
      },
    });
  });

  it("maps timeseries forecast params correctly", async () => {
    await getTimeSeriesForecast(30, "v3");

    expect(mockApiGet).toHaveBeenCalledWith("/timeseries/forecast", {
      params: {
        horizon: 30,
        version: "v3",
      },
    });
  });

  it("maps readiness query params correctly", async () => {
    await getTaskReadiness("v4");

    expect(mockApiGet).toHaveBeenCalledWith("/data/readiness", {
      params: {
        version: "v4",
      },
    });
  });

  it("calls upload schema guide endpoint", async () => {
    await getUploadSchemaGuide();

    expect(mockApiGet).toHaveBeenCalledWith("/data/upload-schema");
  });

  it("maps field readiness query params correctly", async () => {
    await getDataFieldReadiness("v5");

    expect(mockApiGet).toHaveBeenCalledWith("/data/field-readiness", {
      params: {
        version: "v5",
      },
    });
  });

  it("uses multipart upload for excel", async () => {
    const file = new File(["dummy"], "test.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });

    await uploadExcel(file);

    expect(mockAxiosPost).toHaveBeenCalledTimes(1);
    const [url, formData, config] = mockAxiosPost.mock.calls[0];

    expect(url).toContain("/upload");
    expect(formData).toBeInstanceOf(FormData);
    expect(formData.get("file")).toBe(file);
    expect(config.headers["Content-Type"]).toBe("multipart/form-data");
    expect(config.timeout).toBe(120000);
  });

  it("uses multipart upload for multiple csv files", async () => {
    const fileA = new File(["a"], "transaction_items.csv", { type: "text/csv" });
    const fileB = new File(["b"], "transaction.csv", { type: "text/csv" });

    await uploadExcel([fileA, fileB]);

    expect(mockAxiosPost).toHaveBeenCalledTimes(1);
    const [url, formData, config] = mockAxiosPost.mock.calls[0];

    expect(url).toContain("/upload");
    expect(formData).toBeInstanceOf(FormData);
    expect(formData.get("file")).toBeNull();
    expect(formData.getAll("files")).toEqual([fileA, fileB]);
    expect(config.headers["Content-Type"]).toBe("multipart/form-data");
  });
});