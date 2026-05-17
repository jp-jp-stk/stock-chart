"""
create_weekly_merged.py
年別週次ファイルを3つの期間別ファイルに集約する
"""

import time
from pathlib import Path

import pandas as pd

MERGED_DIR = Path(__file__).parent / "data" / "merged"

GROUPS = [
    ("prices_weekly_2015_2020.csv", list(range(2015, 2021))),
    ("prices_weekly_2021_2025.csv", list(range(2021, 2026))),
    ("prices_weekly_2026.csv",      [2026]),
]


def main():
    start = time.time()
    print("処理開始")

    for out_name, years in GROUPS:
        frames = []
        for year in years:
            path = MERGED_DIR / f"prices_{year}_weekly.csv"
            if not path.exists():
                print(f"  スキップ（ファイルなし）: {path.name}")
                continue
            df = pd.read_csv(path, dtype=str, encoding="utf-8")
            print(f"  読込：{path.name}（{len(df):,}行）")
            frames.append(df)

        if not frames:
            print(f"  スキップ（対象ファイルなし）: {out_name}")
            continue

        merged = pd.concat(frames, ignore_index=True)

        # 日付を datetime に変換してソート・重複排除
        merged["_dt"] = pd.to_datetime(merged["日付"], errors="coerce")
        before = len(merged)
        merged = merged.drop_duplicates(subset=["SC", "日付"], keep="last")
        merged = merged.sort_values(["_dt", "SC"]).drop(columns=["_dt"])
        merged = merged.reset_index(drop=True)
        dupes = before - len(merged)

        out_path = MERGED_DIR / out_name
        merged.to_csv(out_path, index=False, encoding="utf-8")

        dup_msg = f"  重複除去: {dupes:,}行" if dupes else ""
        print(f"  出力：{out_name}（{len(merged):,}行）{dup_msg}")

    elapsed = time.time() - start
    print(f"処理完了：所要時間 {elapsed:.1f}秒")


if __name__ == "__main__":
    main()
