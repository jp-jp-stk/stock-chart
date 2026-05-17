"""
download_history.py
yfinance で全上場銘柄の過去データを取得し KABU+形式の年次 CSV に保存する

取得期間  : 2015-01-01 〜 2025-04-30
出力      : data/merged/prices_2015.csv 〜 prices_2024.csv
            data/merged/prices_2025_yf.csv  (2025年1〜4月分、merge_history.py 用)
エラーログ: data/download_errors.log
"""

import logging
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf

# ── 設定 ──────────────────────────────────────────────
STOCK_LIST = Path(__file__).parent / "data" / "stock_list.csv"
MERGED_DIR  = Path(__file__).parent / "data" / "merged"
ERROR_LOG   = Path(__file__).parent / "data" / "download_errors.log"

START_DATE  = "2015-01-01"
END_DATE    = "2025-05-01"   # yfinance end は exclusive
WAIT_SEC    = 0.5

KABU_COLS = [
    "SC", "名称", "市場", "業種", "日付", "株価", "前日比",
    "前日比（％）", "前日終値", "始値", "高値", "安値",
    "出来高", "売買代金（千円）", "時価総額（百万円）", "値幅下限", "値幅上限",
]
# ──────────────────────────────────────────────────────


def to_kabu_df(sc: str, name: str, market: str, industry: str,
               hist: pd.DataFrame) -> pd.DataFrame:
    """yfinance DataFrame → KABU+形式 DataFrame"""
    h = hist.copy()
    h.index = pd.to_datetime(h.index)
    # タイムゾーン除去
    if h.index.tz is not None:
        h.index = h.index.tz_localize(None)

    h = h.sort_index()

    # カラム名の正規化（MultiIndex になる場合がある）
    if isinstance(h.columns, pd.MultiIndex):
        h.columns = h.columns.get_level_values(0)

    required = {"Open", "High", "Low", "Close", "Volume"}
    if not required.issubset(set(h.columns)):
        return pd.DataFrame(columns=KABU_COLS)

    h["SC"]     = sc
    h["名称"]   = name
    h["市場"]   = market
    h["業種"]   = industry
    h["日付"]   = h.index.strftime("%Y/%m/%d")
    h["株価"]   = h["Close"].round(2)
    h["前日終値"] = h["Close"].shift(1).round(2)
    h["前日比"]  = (h["Close"] - h["Close"].shift(1)).round(2)
    h["前日比（％）"] = (h["前日比"] / h["Close"].shift(1) * 100).round(2)
    h["始値"]   = h["Open"].round(2)
    h["高値"]   = h["High"].round(2)
    h["安値"]   = h["Low"].round(2)
    h["出来高"] = h["Volume"].fillna(0).astype(int)
    h["売買代金（千円）"]   = "-"
    h["時価総額（百万円）"] = "-"
    h["値幅下限"] = "-"
    h["値幅上限"] = "-"

    return h[KABU_COLS].dropna(subset=["株価"])


def append_to_year_file(rows: pd.DataFrame, year: int, existing_keys: set) -> int:
    """年次ファイルに差分追記し、追加行数を返す"""
    path = MERGED_DIR / (f"prices_{year}_yf.csv" if year == 2025 else f"prices_{year}.csv")
    new = rows[
        ~rows.apply(lambda r: (str(r["SC"]), str(r["日付"])) in existing_keys, axis=1)
    ]
    if new.empty:
        return 0

    write_header = not path.exists()
    new.to_csv(path, mode="a", header=write_header, index=False, encoding="utf-8")
    return len(new)


def load_existing_keys(year: int) -> set:
    """既存ファイルの (SC, 日付) キーセットを返す"""
    path = MERGED_DIR / (f"prices_{year}_yf.csv" if year == 2025 else f"prices_{year}.csv")
    if not path.exists():
        return set()
    try:
        df = pd.read_csv(path, usecols=["SC", "日付"], dtype=str)
        return set(zip(df["SC"].astype(str), df["日付"].astype(str)))
    except Exception:
        return set()


def get_already_done() -> set:
    """すでにダウンロード済みの SC セットを返す（全年ファイルを横断）"""
    done = set()
    for year in range(2015, 2026):
        path = MERGED_DIR / (f"prices_{year}_yf.csv" if year == 2025 else f"prices_{year}.csv")
        if path.exists():
            try:
                df = pd.read_csv(path, usecols=["SC"], dtype=str)
                done.update(df["SC"].dropna().astype(str).unique())
            except Exception:
                pass
    return done


def download_one(sc: str, name: str, market: str, industry: str,
                 year_keys: dict) -> tuple[int, str | None]:
    """1銘柄ダウンロード → 年次ファイルに追記。(追加行数, エラーメッセージ|None) を返す"""
    ticker = f"{sc}.T"
    try:
        hist = yf.download(ticker, start=START_DATE, end=END_DATE,
                           auto_adjust=True, progress=False,
                           actions=False, threads=False)
        if hist is None or hist.empty:
            return 0, "データなし"

        df = to_kabu_df(sc, name, market, industry, hist)
        if df.empty:
            return 0, "変換後データなし"

        total_added = 0
        for year, grp in df.groupby(df["日付"].str[:4].astype(int)):
            if year < 2015 or year > 2025:
                continue
            added = append_to_year_file(grp, year, year_keys.get(year, set()))
            # 追記したキーを即座に更新して次回重複を防ぐ
            for _, row in grp.iterrows():
                year_keys.setdefault(year, set()).add((str(row["SC"]), str(row["日付"])))
            total_added += added

        return total_added, None

    except Exception as e:
        return 0, str(e)


def main(test_sc: str | None = None):
    start_time = time.time()

    if not STOCK_LIST.exists():
        print(f"エラー: {STOCK_LIST} が見つかりません。先に get_stock_list.py を実行してください。")
        return

    stocks = pd.read_csv(STOCK_LIST, dtype=str)
    stocks["コード"] = stocks["コード"].str.strip().str.zfill(4)

    if test_sc:
        stocks = stocks[stocks["コード"] == test_sc].reset_index(drop=True)
        if stocks.empty:
            print(f"エラー: {test_sc} が銘柄リストに見つかりません")
            return

    MERGED_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(filename=ERROR_LOG, level=logging.ERROR,
                        format="%(asctime)s %(message)s", filemode="a")

    already_done = get_already_done() if not test_sc else set()

    targets = stocks[~stocks["コード"].isin(already_done)].reset_index(drop=True)
    total   = len(stocks)
    skip    = total - len(targets)

    print(f"全{total:,}銘柄の取得を開始します")
    if skip:
        print(f"  取得済みスキップ: {skip:,}銘柄")
    print(f"  新規取得対象: {len(targets):,}銘柄")
    print(f"  期間: {START_DATE} 〜 2025-04-30\n")

    # 既存キー（年別）を事前ロード
    year_keys: dict[int, set] = {y: load_existing_keys(y) for y in range(2015, 2026)}

    done_cnt = 0
    fail_cnt = 0

    for idx, row in targets.iterrows():
        sc       = str(row["コード"]).zfill(4)
        name     = str(row.get("銘柄名", ""))
        market   = str(row.get("市場・商品区分", ""))
        industry = str(row.get("17業種区分", ""))

        num = idx + 1 - skip
        print(f"  [{num:>5}/{len(targets):>5}] {sc}.T {name[:20]} ...", end=" ", flush=True)

        added, err = download_one(sc, name, market, industry, year_keys)

        if err:
            print(f"スキップ ({err})")
            logging.error(f"{sc} {name}: {err}")
            fail_cnt += 1
        else:
            print(f"完了 (+{added:,}行)")
            done_cnt += 1

        time.sleep(WAIT_SEC)

    elapsed = time.time() - start_time
    mins, secs = divmod(int(elapsed), 60)
    print(f"\n完了: {done_cnt:,}銘柄取得完了・{fail_cnt:,}銘柄失敗")
    print(f"所要時間: {mins}分{secs:02d}秒")
    if fail_cnt:
        print(f"エラーログ: {ERROR_LOG}")


def test_single(sc: str = "8306"):
    """指定銘柄1社だけで動作確認"""
    print(f"=== テスト実行: {sc} ===\n")
    main(test_sc=sc)

    # 結果確認
    for year in range(2015, 2026):
        path = MERGED_DIR / (f"prices_{year}_yf.csv" if year == 2025 else f"prices_{year}.csv")
        if path.exists():
            df = pd.read_csv(path, dtype=str)
            sc_rows = df[df["SC"] == sc]
            if not sc_rows.empty:
                print(f"\n  prices_{year}: {len(sc_rows):,}行")
                if year == 2015:
                    print(f"  先頭5行:\n{sc_rows.head().to_string(index=False)}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        sc = sys.argv[2] if len(sys.argv) > 2 else "8306"
        test_single(sc)
    else:
        main()
