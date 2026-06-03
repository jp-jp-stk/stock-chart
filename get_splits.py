"""
get_splits.py
yfinance から株式分割データを取得して splits.csv に保存する。

初回実行 : 全期間取得（遅いが一度だけ）
2回目以降: 最終更新日の30日前以降のみチェック（高速）
"""

import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

SETTLEMENT_DIR   = Path(r'C:\Users\jnpei\Documents\stock-chart\data\settlement')
PRICES_DIR       = Path(r'C:\Users\jnpei\Documents\stock-chart\data\merged')
OUTPUT_FILE      = SETTLEMENT_DIR / 'splits.csv'
LAST_UPDATE_FILE = SETTLEMENT_DIR / 'splits_last_update.txt'

LOOKBACK_DAYS = 30   # 最終更新日から何日前までさかのぼるか
SLEEP_EACH    = 0.3  # 銘柄ごとの待機秒数
SLEEP_BATCH   = 2.0  # 50銘柄ごとの追加待機秒数


# ── ヘルパー ────────────────────────────────────────

def load_last_update() -> date | None:
    """splits_last_update.txt から最終更新日を読み込む"""
    if not LAST_UPDATE_FILE.exists():
        return None
    try:
        return date.fromisoformat(LAST_UPDATE_FILE.read_text(encoding='utf-8').strip())
    except Exception:
        return None


def save_last_update(d: date) -> None:
    LAST_UPDATE_FILE.write_text(d.isoformat(), encoding='utf-8')


def load_existing_splits() -> pd.DataFrame:
    """既存の splits.csv を読み込む（なければ空 DataFrame）"""
    if not OUTPUT_FILE.exists():
        return pd.DataFrame(columns=['SC', 'date', 'ratio'])
    try:
        return pd.read_csv(OUTPUT_FILE, encoding='utf-8', dtype={'SC': str})
    except Exception:
        return pd.DataFrame(columns=['SC', 'date', 'ratio'])


def get_sc_list() -> list[str]:
    """prices_2026.csv（なければ prices_2025.csv）から銘柄コードリストを取得"""
    for year in (2026, 2025):
        p = PRICES_DIR / f'prices_{year}.csv'
        if p.exists():
            df = pd.read_csv(p, encoding='utf-8', low_memory=False)
            sc_list = df['SC'].astype(str).str.zfill(4).unique().tolist()
            return [sc for sc in sc_list if sc.isdigit() and int(sc) >= 1000]
    return []


# ── メイン処理 ──────────────────────────────────────

def fetch_splits(sc_list: list[str], start_date: date | None) -> list[dict]:
    """
    sc_list の各銘柄について yfinance から分割データを取得する。
    start_date が指定されている場合はその日以降のみ返す。
    """
    records = []
    errors  = []
    total   = len(sc_list)

    for i, sc in enumerate(sc_list):
        try:
            ticker = yf.Ticker(f'{sc}.T')

            if start_date is not None:
                # 差分チェック：start_date 以降のみ取得
                hist = ticker.history(
                    start=start_date.strftime('%Y-%m-%d'),
                    auto_adjust=False,
                    actions=True,
                )
                splits = hist['Stock Splits'] if 'Stock Splits' in hist.columns else pd.Series(dtype=float)
                splits = splits[splits > 0]
            else:
                # 初回：全期間取得
                splits = ticker.splits

            if len(splits) > 0:
                for dt, ratio in splits.items():
                    records.append({
                        'SC':    sc,
                        'date':  dt.strftime('%Y/%m/%d'),
                        'ratio': float(ratio),
                    })
                print(f'  [{i+1}/{total}] {sc}: {len(splits)}件')

        except Exception as e:
            errors.append((sc, str(e)))

        time.sleep(SLEEP_EACH)
        if i % 50 == 49:
            time.sleep(SLEEP_BATCH)

    if errors:
        print(f'\nエラー銘柄数: {len(errors)} 件')
        for sc, msg in errors[:5]:
            print(f'  {sc}: {msg}')
        if len(errors) > 5:
            print(f'  ...他 {len(errors)-5} 件')

    return records


def main():
    today       = date.today()
    last_update = load_last_update()

    if last_update is None:
        start_date = None
        print('=' * 50)
        print('  初回実行：全期間の分割データを取得します')
        print('=' * 50)
    else:
        start_date = last_update - timedelta(days=LOOKBACK_DAYS)
        print('=' * 50)
        print(f'  差分チェック（前回: {last_update} → {start_date} 以降）')
        print('=' * 50)

    sc_list = get_sc_list()
    if not sc_list:
        print('銘柄リストが取得できませんでした')
        return
    print(f'対象銘柄数: {len(sc_list)}\n')

    # 分割データ取得
    new_records = fetch_splits(sc_list, start_date)

    # 既存データとマージ
    existing = load_existing_splits()

    if new_records:
        new_df = pd.DataFrame(new_records)
        merged = pd.concat([existing, new_df], ignore_index=True)
        merged = merged.drop_duplicates(subset=['SC', 'date'], keep='last')
        merged = merged.sort_values(['SC', 'date']).reset_index(drop=True)
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        merged.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
        added = len(merged) - len(existing)
        print(f'\nsplits.csv 更新: 合計 {len(merged)} 件（新規 +{added} 件）')
    else:
        print('\n新規分割データなし → splits.csv の更新をスキップ')

    # 最終更新日を記録
    save_last_update(today)
    print(f'最終更新日を記録: {today}  ({LAST_UPDATE_FILE.name})')

    # 動作確認用：SC5803 の分割履歴を表示
    check_df = load_existing_splits()
    sc5803 = check_df[check_df['SC'] == '5803']
    print(f'\nSC5803 の分割履歴:')
    print(sc5803.to_string() if not sc5803.empty else '  データなし')


if __name__ == '__main__':
    main()
