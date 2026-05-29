"""
merge_prices.py
data/daily/ の日次CSVを年別に結合し、週次ファイルも生成する
"""

import time
from datetime import datetime
from pathlib import Path

import pandas as pd

# ── 設定 ──────────────────────────────────────────────────
DAILY_DIR      = Path(__file__).parent / "data" / "daily"
MERGED_DIR     = Path(__file__).parent / "data" / "merged"
SETTLEMENT_DIR = Path(__file__).parent / "data" / "settlement"

INPUT_COLS = [
    "SC", "名称", "市場", "業種", "日付", "株価", "前日比",
    "前日比（％）", "前日終値", "始値", "高値", "安値",
    "出来高", "売買代金（千円）", "時価総額（百万円）",
    "値幅下限", "値幅上限",
]

DEDUP_KEYS = ["SC", "日付"]

NUM_COLS = [
    "株価", "前日比", "前日比（％）", "前日終値", "始値", "高値", "安値",
    "出来高", "売買代金（千円）", "時価総額（百万円）", "値幅下限", "値幅上限",
]
# ──────────────────────────────────────────────────────────


def load_daily_files(daily_dir: Path) -> pd.DataFrame:
    """data/daily/ の全CSVを読み込んで1つの DataFrame にまとめる"""
    files = sorted(daily_dir.glob("japan-all-stock-prices_*.csv"))
    if not files:
        return pd.DataFrame(columns=INPUT_COLS)

    frames = []
    for f in files:
        try:
            df = pd.read_csv(f, encoding="shift-jis", dtype=str, header=0)
            # 列名の空白を除去し、定義名に揃える
            df.columns = [c.strip() for c in df.columns]
            if list(df.columns) != INPUT_COLS and len(df.columns) == len(INPUT_COLS):
                df.columns = INPUT_COLS
            frames.append(df)
        except Exception as e:
            print(f"  警告: {f.name} の読み込みに失敗 ({e})")

    if not frames:
        return pd.DataFrame(columns=INPUT_COLS)

    return pd.concat(frames, ignore_index=True)


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """日付・数値列を適切な型に変換する"""
    df = df.copy()
    df["日付"] = pd.to_datetime(df["日付"], errors="coerce")
    for col in NUM_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False),
                errors="coerce",
            )
    return df


def load_existing_merged(path: Path) -> pd.DataFrame:
    """既存の結合済みCSV を読み込む（なければ空 DataFrame）"""
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, encoding="utf-8", dtype=str)
    except Exception:
        return pd.DataFrame()


def build_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """
    日次 DataFrame から週次 DataFrame を生成する。
    週の基準: 月曜始まり（ISO 週）
    """
    df = df.copy().sort_values(["SC", "日付"])
    df["_week"] = df["日付"].dt.to_period("W")

    grp = df.groupby(["SC", "_week"], sort=True)

    weekly = pd.DataFrame({
        "名称":              grp["名称"].first(),
        "市場":              grp["市場"].first(),
        "業種":              grp["業種"].first(),
        "日付":              grp["日付"].last(),          # 週最終営業日
        "株価":              grp["株価"].last(),           # 週末終値
        "前日比":            None,
        "前日比（％）":       None,
        "前日終値":          None,
        "始値":              grp["始値"].first(),          # 週初め始値
        "高値":              grp["高値"].max(),
        "安値":              grp["安値"].min(),
        "出来高":            grp["出来高"].sum(),
        "売買代金（千円）":   grp["売買代金（千円）"].sum(),
        "時価総額（百万円）":  grp["時価総額（百万円）"].last(),
        "値幅下限":          grp["値幅下限"].last(),
        "値幅上限":          grp["値幅上限"].last(),
    }).reset_index()

    weekly = weekly.drop(columns=["_week"])

    cols = ["SC", "名称", "市場", "業種", "日付", "株価", "前日比", "前日比（％）",
            "前日終値", "始値", "高値", "安値", "出来高", "売買代金（千円）",
            "時価総額（百万円）", "値幅下限", "値幅上限"]
    return weekly[cols]


def load_splits() -> pd.DataFrame:
    """splits.csv を読み込む（なければ空 DataFrame）

    異常な ratio（実際の株式分割ではない合併・組織再編等）を除外する。
    有効範囲: 0.1 ≤ ratio ≤ 20（1:10分割〜10:1併合まで）
    """
    path = SETTLEMENT_DIR / "splits.csv"
    if not path.exists():
        return pd.DataFrame(columns=["SC", "date", "ratio"])
    try:
        df = pd.read_csv(path, encoding="utf-8", dtype={"SC": str})
        df["SC"]    = df["SC"].str.zfill(4)
        df["ratio"] = pd.to_numeric(df["ratio"], errors="coerce")
        before = len(df)
        df = df[(df["ratio"] >= 0.1) & (df["ratio"] <= 20)].reset_index(drop=True)
        filtered = before - len(df)
        print(f"splits.csv 読み込み: {len(df)} 件（異常ratio除外: {filtered} 件）")
        return df
    except Exception as e:
        print(f"[警告] splits.csv 読み込み失敗: {e}")
        return pd.DataFrame(columns=["SC", "date", "ratio"])


def apply_splits(df_sc: pd.DataFrame, splits_df: pd.DataFrame, sc: str) -> pd.DataFrame:
    """
    yfinanceの調整済みデータ（分割後価格）に統一する。
    KABU+の未調整データ（分割前価格）を分割比率で割って補正する。

    splits_df の date 列は 'YYYY/MM/DD' 文字列。
    df_sc の '日付' 列は datetime 型。
    KABU+ データ開始日（2025/05/01）以降の分割のみ対象。
    """
    sc_splits = splits_df[
        (splits_df["SC"] == sc) &
        (splits_df["date"] >= "2025/05/01")
    ].sort_values("date")

    if sc_splits.empty:
        return df_sc

    for _, split in sc_splits.iterrows():
        # YYYY/MM/DD → pd.Timestamp に変換して datetime 列と比較
        split_ts = pd.Timestamp(split["date"].replace("/", "-"))
        ratio    = split["ratio"]

        # 補正対象: KABU+ 生データ取得開始日(2025/05/01) 〜 分割日の前日
        # Jan〜Apr のデータは KABU+ が自動で調整済みのため対象外
        # May 1〜(分割日-1) のデータのみ未調整なので ÷ratio で補正
        kabu_raw_start = pd.Timestamp("2025-05-01")
        mask = (df_sc["日付"] >= kabu_raw_start) & (df_sc["日付"] < split_ts)
        if mask.sum() == 0:
            continue

        for col in ["株価", "始値", "高値", "安値", "前日終値"]:
            if col in df_sc.columns:
                df_sc.loc[mask, col] = df_sc.loc[mask, col] / ratio

        # 出来高は逆に ratio 倍
        if "出来高" in df_sc.columns:
            df_sc.loc[mask, "出来高"] = df_sc.loc[mask, "出来高"] * ratio

        print(f"  補正: SC{sc} {split['date']} ÷{ratio} ({mask.sum()}行)")

    return df_sc


def save_csv(df: pd.DataFrame, path: Path):
    """DataFrame を UTF-8 CSV として保存（ファイルロック時は最大3回リトライ）"""
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            df.to_csv(path, index=False, encoding="utf-8")
            return
        except PermissionError:
            if attempt < 2:
                print(f"  ファイルがロックされています。10秒後にリトライ... ({attempt + 1}/3)")
                time.sleep(10)
            else:
                print(f"  エラー: {path.name} への書き込み権限がありません")
                print(f"  Excel やブラウザでファイルを開いていたら閉じてください")
                raise


def main():
    start_time = time.time()
    now_str = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    print("=" * 50)
    print(f"  処理開始: {now_str}")
    print("=" * 50)

    MERGED_DIR.mkdir(parents=True, exist_ok=True)

    # 分割データ読み込み
    splits_df  = load_splits()
    split_scs  = set(splits_df["SC"].unique()) if not splits_df.empty else set()

    daily_files = sorted(DAILY_DIR.glob("japan-all-stock-prices_*.csv"))
    print(f"\n読み込みファイル数: {len(daily_files)} 件")

    if not daily_files:
        print("data/daily/ にファイルがありません。処理をスキップします。")
        elapsed = time.time() - start_time
        print(f"\n処理完了: 所要時間 {elapsed:.1f} 秒")
        return

    raw = load_daily_files(DAILY_DIR)
    raw = coerce_types(raw)
    raw = raw.dropna(subset=["SC", "日付"])
    raw["SC"] = raw["SC"].astype(str).str.strip()

    years = sorted(raw["日付"].dt.year.dropna().unique().astype(int))
    total_added = 0
    total_skipped = 0

    for year in years:
        year_df = raw[raw["日付"].dt.year == year].copy()

        merged_path = MERGED_DIR / f"prices_{year}.csv"
        weekly_path = MERGED_DIR / f"prices_{year}_weekly.csv"

        # 差分追記（重複排除）
        existing = load_existing_merged(merged_path)
        if not existing.empty:
            existing = coerce_types(existing)
            existing_keys = set(
                zip(existing["SC"].astype(str),
                    existing["日付"].dt.strftime("%Y-%m-%d"))
            )
            new_rows = year_df[
                ~year_df.apply(
                    lambda r: (str(r["SC"]), r["日付"].strftime("%Y-%m-%d")) in existing_keys,
                    axis=1,
                )
            ]
            skipped = len(year_df) - len(new_rows)
            total_skipped += skipped
            merged = pd.concat([existing, new_rows], ignore_index=True) if not new_rows.empty else existing.copy()
            merged = coerce_types(merged)
            added_count = len(new_rows)
        else:
            merged = year_df.copy()
            added_count = len(year_df)
            skipped = 0

        total_added += added_count

        merged = merged.sort_values(["日付", "SC"]).drop_duplicates(
            subset=DEDUP_KEYS, keep="last"
        )

        # ── 分割補正（splits.csv が存在し、分割がある銘柄のみ処理）──
        affected_scs = split_scs & set(merged["SC"].astype(str).unique())
        if affected_scs:
            print(f"\n  分割補正対象: {len(affected_scs)} 銘柄")
            affected   = merged[merged["SC"].astype(str).isin(affected_scs)].copy()
            unaffected = merged[~merged["SC"].astype(str).isin(affected_scs)]
            corrected  = [
                apply_splits(grp.copy(), splits_df, sc_val)
                for sc_val, grp in affected.groupby("SC")
            ]
            merged = pd.concat(
                [unaffected] + corrected, ignore_index=True
            ).sort_values(["日付", "SC"]).reset_index(drop=True)

        out = merged.copy()
        out["日付"] = out["日付"].dt.strftime("%Y/%m/%d")
        save_csv(out, merged_path)
        print(f"\n出力: {merged_path.name}（{len(out):,} 行）"
              f"  ← 追加 {added_count:,} 行  スキップ {skipped:,} 行")

        # 週次生成
        weekly = build_weekly(merged)
        weekly_out = weekly.copy()
        weekly_out["日付"] = weekly_out["日付"].dt.strftime("%Y/%m/%d")
        for col in ["前日比", "前日比（％）", "前日終値"]:
            weekly_out[col] = ""

        save_csv(weekly_out, weekly_path)
        print(f"出力: {weekly_path.name}（{len(weekly_out):,} 行）")

    elapsed = time.time() - start_time
    print(f"\n追加データ数: {total_added:,} 行（重複スキップ: {total_skipped:,} 行）")
    print(f"処理完了: 所要時間 {elapsed:.1f} 秒")


if __name__ == "__main__":
    main()
