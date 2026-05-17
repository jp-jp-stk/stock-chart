"""
merge_history.py
yfinance 過去データと KABU+ データを統合し、全年次ファイルの週次データを生成する

Step1: 上場廃止銘柄の除外
Step2: 2025年データの補完（yfinance 1〜4月 + KABU+ 5月〜）
Step3: 全年次ファイルの週次データ生成
"""

import time
from pathlib import Path

import pandas as pd

# ── 設定 ──────────────────────────────────────────────
STOCK_LIST  = Path(__file__).parent / "data" / "stock_list.csv"
MERGED_DIR  = Path(__file__).parent / "data" / "merged"

KABU_COLS = [
    "SC", "名称", "市場", "業種", "日付", "株価", "前日比",
    "前日比（％）", "前日終値", "始値", "高値", "安値",
    "出来高", "売買代金（千円）", "時価総額（百万円）", "値幅下限", "値幅上限",
]

NUM_COLS = ["株価", "前日比", "前日比（％）", "前日終値", "始値", "高値", "安値", "出来高"]
# ──────────────────────────────────────────────────────


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["日付"] = pd.to_datetime(df["日付"], errors="coerce")
    for col in NUM_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False),
                errors="coerce",
            )
    return df


def save_csv(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str, encoding="utf-8")
    except Exception:
        return pd.DataFrame()


def build_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """日次 DataFrame から週次 DataFrame を生成する（merge_prices.py と同ロジック）"""
    df = df.copy().sort_values(["SC", "日付"])
    df["_week"] = df["日付"].dt.to_period("W")

    grp = df.groupby(["SC", "_week"], sort=True)

    weekly = pd.DataFrame({
        "名称":              grp["名称"].first(),
        "市場":              grp["市場"].first(),
        "業種":              grp["業種"].first(),
        "日付":              grp["日付"].last(),
        "株価":              grp["株価"].last(),
        "前日比":            None,
        "前日比（％）":       None,
        "前日終値":          None,
        "始値":              grp["始値"].first(),
        "高値":              grp["高値"].max(),
        "安値":              grp["安値"].min(),
        "出来高":            grp["出来高"].sum(),
        "売買代金（千円）":   grp["売買代金（千円）"].last() if "売買代金（千円）" in df.columns else "-",
        "時価総額（百万円）":  grp["時価総額（百万円）"].last() if "時価総額（百万円）" in df.columns else "-",
        "値幅下限":          grp["値幅下限"].last() if "値幅下限" in df.columns else "-",
        "値幅上限":          grp["値幅上限"].last() if "値幅上限" in df.columns else "-",
    }).reset_index().drop(columns=["_week"])

    cols = ["SC"] + [c for c in KABU_COLS if c != "SC"]
    return weekly[[c for c in cols if c in weekly.columns]]


# ══════════════════════════════════════════════════════
#  Step 1: 上場廃止銘柄の除外
# ══════════════════════════════════════════════════════
def step1_remove_delisted():
    print("\n【Step1】上場廃止銘柄の除外")

    if not STOCK_LIST.exists():
        print("  stock_list.csv が見つかりません。スキップします。")
        return

    active_sc = set(
        pd.read_csv(STOCK_LIST, dtype=str)["コード"]
        .astype(str).str.strip().str.zfill(4)
    )
    print(f"  現在上場中: {len(active_sc):,}銘柄")

    total_removed = 0
    for year in range(2015, 2026):
        path = MERGED_DIR / f"prices_{year}.csv"
        if not path.exists():
            continue
        df = load_csv(path)
        if df.empty:
            continue
        before = len(df)
        df = df[df["SC"].astype(str).str.zfill(4).isin(active_sc)]
        removed = before - len(df)
        if removed:
            save_csv(df, path)
            print(f"  prices_{year}.csv: {removed:,}行削除")
            total_removed += removed

    print(f"  合計: {total_removed:,}行削除完了")


# ══════════════════════════════════════════════════════
#  Step 2: 2025年データの補完
# ══════════════════════════════════════════════════════
def step2_merge_2025():
    print("\n【Step2】2025年データの補完（yfinance 1〜4月 + KABU+ 5月〜）")

    kabu_path = MERGED_DIR / "prices_2025.csv"
    yf_path   = MERGED_DIR / "prices_2025_yf.csv"

    kabu = load_csv(kabu_path)
    yf   = load_csv(yf_path)

    if yf.empty and kabu.empty:
        print("  prices_2025.csv も prices_2025_yf.csv も存在しません。スキップします。")
        return

    if yf.empty:
        print("  prices_2025_yf.csv が存在しないため、KABU+データのみ使用します。")
        merged = coerce_types(kabu)
    elif kabu.empty:
        print("  prices_2025.csv が存在しないため、yfinanceデータのみ使用します。")
        merged = coerce_types(yf)
    else:
        # yfinance から 2025-01-01 〜 2025-04-30 のみ抽出
        yf_df = coerce_types(yf)
        cutoff = pd.Timestamp("2025-05-01")
        yf_jan_apr = yf_df[yf_df["日付"] < cutoff].copy()

        # KABU+ は 2025-05-01 以降をそのまま使用
        kabu_df = coerce_types(kabu)

        merged = pd.concat([yf_jan_apr, kabu_df], ignore_index=True)
        merged = merged.drop_duplicates(subset=["SC", "日付"], keep="last")

        print(f"  yfinance (1〜4月): {len(yf_jan_apr):,}行")
        print(f"  KABU+ (5月〜):    {len(kabu_df):,}行")

    merged = merged.sort_values(["日付", "SC"]).reset_index(drop=True)

    # 保存
    out = merged.copy()
    out["日付"] = out["日付"].dt.strftime("%Y/%m/%d")
    # 数値列の文字列化（"-" をそのまま保持）
    for col in ["売買代金（千円）", "時価総額（百万円）", "値幅下限", "値幅上限"]:
        if col in out.columns:
            out[col] = out[col].fillna("-").astype(str).replace("nan", "-")

    save_csv(out, kabu_path)
    print(f"  prices_2025.csv 更新完了: {len(out):,}行")


# ══════════════════════════════════════════════════════
#  Step 3: 全年次ファイルの週次データ生成
# ══════════════════════════════════════════════════════
def step3_generate_weekly():
    print("\n【Step3】週次データ生成")

    generated = 0
    for year in range(2015, 2026):
        path = MERGED_DIR / f"prices_{year}.csv"
        if not path.exists():
            continue

        df = load_csv(path)
        if df.empty:
            continue

        df = coerce_types(df)
        df = df.dropna(subset=["SC", "日付"])
        df["SC"] = df["SC"].astype(str).str.strip()

        # 数値列の欠損を補完（"-" → NaN にして集計）
        for col in ["売買代金（千円）", "時価総額（百万円）", "値幅下限", "値幅上限"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).replace("-", ""), errors="coerce")

        weekly = build_weekly(df)

        # 保存フォーマット整形
        weekly_out = weekly.copy()
        weekly_out["日付"] = weekly_out["日付"].dt.strftime("%Y/%m/%d")
        for col in ["前日比", "前日比（％）", "前日終値"]:
            if col in weekly_out.columns:
                weekly_out[col] = ""
        for col in ["売買代金（千円）", "時価総額（百万円）", "値幅下限", "値幅上限"]:
            if col in weekly_out.columns:
                weekly_out[col] = weekly_out[col].fillna("-").astype(str).replace("nan", "-")

        weekly_path = MERGED_DIR / f"prices_{year}_weekly.csv"
        save_csv(weekly_out, weekly_path)
        print(f"  prices_{year}_weekly.csv: {len(weekly_out):,}行")
        generated += 1

    print(f"  週次データ生成完了: {generated}年分")


# ══════════════════════════════════════════════════════
#  main
# ══════════════════════════════════════════════════════
def main():
    start_time = time.time()
    print("=" * 50)
    print("  merge_history.py 開始")
    print("=" * 50)

    step1_remove_delisted()
    step2_merge_2025()
    step3_generate_weekly()

    elapsed = time.time() - start_time
    print(f"\n全処理完了: 所要時間 {elapsed:.1f}秒")


if __name__ == "__main__":
    main()
