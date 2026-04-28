from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_XLSX = BASE_DIR / "schema_v2_full_upload.xlsx"
SHEET_NAMES = [
    "transaction",
    "transaction_items",
    "product",
    "customer",
    "store",
    "promotion",
    "inventory",
    "weather",
    "holiday",
    "customer_behavior",
    "product_association",
    "review",
]


def main():
    with pd.ExcelWriter(OUTPUT_XLSX, engine="openpyxl") as writer:
        for sheet_name in SHEET_NAMES:
            csv_path = BASE_DIR / f"{sheet_name}.csv"
            df = pd.read_csv(csv_path)
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"added: {sheet_name} ({len(df)} rows)")
    print(f"created: {OUTPUT_XLSX}")


if __name__ == "__main__":
    main()
