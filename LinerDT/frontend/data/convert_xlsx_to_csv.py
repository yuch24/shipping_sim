"""
将 data 目录下的 .xlsx 文件转换为 .csv 文件，保存于同目录。
用法: python convert_xlsx_to_csv.py
"""

import os
import sys
import pandas as pd

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
XLSX_FILES = ["订单OD对需求.xlsx", "港口费用表.xlsx"]

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

for filename in XLSX_FILES:
    xlsx_path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(xlsx_path):
        print(f"SKIP: {filename} not found")
        continue

    df = pd.read_excel(xlsx_path)
    csv_path = os.path.join(DATA_DIR, filename.replace(".xlsx", ".csv"))
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(
        f"OK: {filename} -> {os.path.basename(csv_path)} ({len(df)} rows x {len(df.columns)} cols)"
    )
    print(f"    columns: {list(df.columns)}")

print("Done.")
