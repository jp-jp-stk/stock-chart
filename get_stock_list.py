"""
get_stock_list.py
JPXから上場銘柄リストを取得し data/stock_list.csv に保存する
"""

import sys
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests

URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
SAVE_PATH = Path(__file__).parent / "data" / "stock_list.csv"


def find_col(df: pd.DataFrame, *patterns: str) -> str | None:
    """列名に patterns のいずれかを含む列名を返す"""
    for pat in patterns:
        for col in df.columns:
            if pat in str(col):
                return col
    return None


def main():
    print("JPXから上場銘柄リストをダウンロード中...")
    try:
        resp = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
    except Exception as e:
        print(f"ダウンロードエラー: {e}")
        sys.exit(1)

    try:
        df = pd.read_excel(BytesIO(resp.content), dtype=str, engine="xlrd")
    except Exception:
        # .xls が取れなかった場合は openpyxl で再試行
        df = pd.read_excel(BytesIO(resp.content), dtype=str, engine="openpyxl")

    print(f"  取得列: {list(df.columns)}")

    col_code   = find_col(df, "コード", "Code", "code")
    col_name   = find_col(df, "銘柄名", "銘柄", "Name")
    col_market = find_col(df, "市場", "Market")
    col_ind17  = find_col(df, "17業種区分", "17業種", "業種")

    missing = [k for k, v in {"コード": col_code, "銘柄名": col_name,
                               "市場": col_market, "17業種区分": col_ind17}.items() if v is None]
    if missing:
        print(f"エラー: 以下の列が見つかりません: {missing}")
        print(f"  利用可能な列: {list(df.columns)}")
        sys.exit(1)

    out = pd.DataFrame({
        "コード":       df[col_code].astype(str).str.strip().str.zfill(4),
        "銘柄名":       df[col_name].astype(str).str.strip(),
        "市場・商品区分": df[col_market].astype(str).str.strip(),
        "17業種区分":   df[col_ind17].astype(str).str.strip(),
    })

    # 4桁数字コードのみ残す
    out = out[out["コード"].str.match(r"^\d{4}$")].reset_index(drop=True)

    SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(SAVE_PATH, index=False, encoding="utf-8")

    print(f"上場銘柄リスト取得完了：{len(out):,}銘柄")
    print(f"保存先: {SAVE_PATH}")


if __name__ == "__main__":
    main()
