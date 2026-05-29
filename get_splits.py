import yfinance as yf
import pandas as pd
from pathlib import Path
import time

SETTLEMENT_DIR = Path(r'C:\Users\jnpei\Documents\stock-chart\data\settlement')
PRICES_DIR     = Path(r'C:\Users\jnpei\Documents\stock-chart\data\merged')
OUTPUT_FILE    = SETTLEMENT_DIR / 'splits.csv'

def get_all_splits():
    # 銘柄リストをprices_2026.csvから取得
    df = pd.read_csv(PRICES_DIR / 'prices_2026.csv', encoding='utf-8', low_memory=False)
    sc_list = df['SC'].astype(str).str.zfill(4).unique().tolist()
    # 数字4桁のみ（指数・ETF等を除外）
    sc_list = [sc for sc in sc_list if sc.isdigit() and int(sc) >= 1000]
    print(f'対象銘柄数: {len(sc_list)}')

    records = []
    errors  = []

    for i, sc in enumerate(sc_list):
        try:
            ticker = yf.Ticker(f'{sc}.T')
            splits = ticker.splits
            if len(splits) > 0:
                for date, ratio in splits.items():
                    records.append({
                        'SC':    sc,
                        'date':  date.strftime('%Y/%m/%d'),
                        'ratio': float(ratio)
                    })
                print(f'  [{i+1}/{len(sc_list)}] {sc}: {len(splits)}件')
        except Exception as e:
            errors.append(sc)

        # レート制限対策
        time.sleep(0.3)
        if i % 50 == 49:
            time.sleep(2)

    # CSV出力
    df_out = pd.DataFrame(records)
    if not df_out.empty:
        df_out = df_out.sort_values(['SC', 'date']).reset_index(drop=True)
        df_out.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
        print(f'\nsplits.csv に {len(df_out)} 件出力しました')

        # SC5535の確認
        sc5535 = df_out[df_out['SC'] == '5535']
        print(f'\nSC5535の分割履歴:')
        print(sc5535.to_string() if not sc5535.empty else '  データなし')
    else:
        print('分割データなし')

    if errors:
        print(f'\nエラー銘柄数: {len(errors)}件')

if __name__ == '__main__':
    get_all_splits()
