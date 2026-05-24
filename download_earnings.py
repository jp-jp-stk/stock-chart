# download_earnings.py
# JPXの決算発表予定日ページからxlsxを自動ダウンロードし、
# earnings.csv を最新化するスクリプト。
#
# タスクスケジューラ設定:
#   実行ファイル: python
#   引数:         C:\Users\jnpei\Documents\stock-chart\download_earnings.py
#   実行タイミング: 毎週月曜日 8:00 (決算シーズン中は毎営業日に変更推奨)

import requests
from bs4 import BeautifulSoup
from pathlib import Path
import subprocess
import logging
import sys
from datetime import datetime

# ---- 設定 ----------------------------------------------------------------
BASE_URL       = 'https://www.jpx.co.jp'
TARGET_URL     = BASE_URL + '/listing/event-schedules/financial-announcement/index.html'
SETTLEMENT_DIR = Path(r'C:\Users\jnpei\Documents\stock-chart\data\settlement')
SCRIPT_DIR     = Path(r'C:\Users\jnpei\Documents\stock-chart')
LOG_FILE       = SCRIPT_DIR / 'download_earnings.log'

# JPXは単純なUser-Agentで403を返すため、ブラウザに近いヘッダーを使用
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept':          'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer':         BASE_URL + '/',
}

TIMEOUT = 30  # 秒
# -------------------------------------------------------------------------

# ---- ログ設定 ------------------------------------------------------------
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8',
)
# コンソールにも出力
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter('%(asctime)s %(message)s', datefmt='%H:%M:%S'))
logging.getLogger().addHandler(console)
# -------------------------------------------------------------------------


def fetch_xlsx_links() -> list[str]:
    """JPXページからxlsxリンクを取得する。"""
    logging.info(f'JPXページ取得中: {TARGET_URL}')
    try:
        resp = requests.get(TARGET_URL, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error(f'ページ取得失敗: {e}')
        raise

    soup  = BeautifulSoup(resp.content, 'html.parser')
    links = [
        a['href'] for a in soup.find_all('a', href=True)
        if a['href'].endswith('.xlsx')
    ]

    if not links:
        logging.warning('JPXページの構造が変わった可能性があります（xlsxリンクが0件）')
    else:
        logging.info(f'  xlsxリンク検出: {len(links)} 件')

    return links


def download_files(links: list[str]) -> int:
    """xlsx を settlement/ フォルダへダウンロードする。
    Returns: ダウンロードした件数"""
    SETTLEMENT_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = 0

    for link in links:
        # 絶対URLに変換
        url      = link if link.startswith('http') else BASE_URL + link
        filename = Path(link).name
        savepath = SETTLEMENT_DIR / filename

        logging.info(f'  ダウンロード中: {filename}')
        try:
            dl_headers = {**HEADERS, 'Referer': TARGET_URL}
            r = requests.get(url, headers=dl_headers, timeout=TIMEOUT)
            r.raise_for_status()
        except requests.RequestException as e:
            logging.error(f'  ダウンロード失敗 ({filename}): {e}')
            continue

        savepath.write_bytes(r.content)
        logging.info(f'  保存完了: {savepath}')
        downloaded += 1

    return downloaded


def run_convert() -> None:
    """convert_earnings.py を実行して earnings.csv を最新化する。"""
    convert_script = SCRIPT_DIR / 'convert_earnings.py'
    logging.info(f'convert_earnings.py を実行中...')
    try:
        result = subprocess.run(
            [sys.executable, str(convert_script)],
            capture_output=True,
            check=True,
        )
        # Windows環境ではcp932、それ以外はutf-8でデコード
        for enc in ('utf-8', 'cp932', 'latin-1'):
            try:
                stdout_text = result.stdout.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            stdout_text = result.stdout.decode('utf-8', errors='replace')

        for line in stdout_text.splitlines():
            logging.info(f'  [convert] {line}')
        logging.info('earnings.csv を更新しました')
    except subprocess.CalledProcessError as e:
        logging.error(f'convert_earnings.py 実行失敗: {e.stderr}')
        raise


def main() -> None:
    logging.info('=' * 60)
    logging.info('download_earnings.py 開始')

    try:
        links      = fetch_xlsx_links()
        downloaded = download_files(links)
        logging.info(f'ダウンロード完了: {downloaded} / {len(links)} 件')

        run_convert()

    except Exception as e:
        logging.error(f'処理中断: {e}')
        sys.exit(1)

    logging.info('download_earnings.py 正常終了')
    logging.info('=' * 60)


if __name__ == '__main__':
    main()
