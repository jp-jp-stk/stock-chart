"""
download_prices.py
KABU+ csvex から日次株価CSV を自動ダウンロードする

使い方:
  python download_prices.py        -> 本日分のみ（通常実行）
  python download_prices.py --all  -> 全期間チェック（初回・過去分取得）
"""

import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

# ── 設定 ──────────────────────────────────────────────────
BASE_URL   = "https://csvex.com/kabu.plus/csv/japan-all-stock-prices/daily/"
START_DATE = date(2025, 5, 1)
SAVE_DIR   = Path(__file__).parent / "data" / "daily"
CONFIG     = Path(__file__).parent / "config.txt"
INTERVAL   = 1.0   # ダウンロード間の待機秒数
TIMEOUT    = 30    # 接続タイムアウト秒数
# ──────────────────────────────────────────────────────────


def load_config() -> tuple[str, str]:
    """config.txt から KABU_ID・KABU_PASSWORD を読み込んで返す"""
    if not CONFIG.exists():
        print("エラー: config.txtが見つかりません。")
        print("config.txtをスクリプトと同じフォルダに作成してください。")
        sys.exit(1)

    cfg = {}
    for line in CONFIG.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        cfg[key.strip()] = val.strip()

    uid = cfg.get("KABU_ID", "")
    pwd = cfg.get("KABU_PASSWORD", "")

    if not uid or not pwd:
        print("エラー: config.txtにKABU_IDとKABU_PASSWORDを設定してください。")
        sys.exit(1)

    return uid, pwd


def date_range(start: date, end: date):
    """start から end まで 1 日ずつ yield する（土日含む）"""
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def build_filename(d: date) -> str:
    return f"japan-all-stock-prices_{d.strftime('%Y%m%d')}.csv"


def verify_auth(session: requests.Session, auth: HTTPBasicAuth) -> bool:
    """先頭ファイルで認証テストを行う"""
    test_file = build_filename(START_DATE)
    url = BASE_URL + test_file
    try:
        resp = session.head(url, auth=auth, timeout=TIMEOUT)
        if resp.status_code == 401:
            return False
        return True
    except requests.RequestException:
        return True   # ネットワーク系エラーは認証とは別問題なので続行


def download_file(session: requests.Session, url: str, dest: Path,
                  auth: HTTPBasicAuth) -> str:
    """
    1 ファイルをダウンロードして dest に保存する。
    戻り値: 'ok' | 'skip_404' | 'error:<msg>'
    """
    try:
        resp = session.get(url, auth=auth, timeout=TIMEOUT)
        if resp.status_code == 404:
            return "skip_404"
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        return "ok"
    except requests.RequestException as e:
        return f"error:{e}"


def run_today(session: requests.Session, auth: HTTPBasicAuth):
    """本日分（1ファイル）のみダウンロードする"""
    today = date.today()
    filename = build_filename(today)
    dest = SAVE_DIR / filename

    print(f"対象: {filename}")

    if dest.exists():
        print("本日分は取得済みです。")
        return

    print(f"ダウンロード中 ... ", end="", flush=True)
    result = download_file(session, BASE_URL + filename, dest, auth)

    if result == "ok":
        print("完了")
    elif result == "skip_404":
        print("スキップ（ファイルなし・休場日の可能性）")
    else:
        msg = result.replace("error:", "")
        print(f"失敗 ({msg})")


def run_all(session: requests.Session, auth: HTTPBasicAuth):
    """全期間（START_DATE〜本日）を差分チェックしてダウンロードする"""
    today = date.today()
    all_dates = list(date_range(START_DATE, today))
    existing = {p.name for p in SAVE_DIR.glob("*.csv")}
    targets = [d for d in all_dates if build_filename(d) not in existing]
    skip_count = len(all_dates) - len(targets)

    print(f"対象ファイル数       : {len(all_dates)} 件")
    print(f"取得済みスキップ     : {skip_count} 件")
    print(f"新規ダウンロード対象 : {len(targets)} 件\n")

    if not targets:
        print("新規ダウンロード対象がありません。")
        return

    start_time = time.time()
    done_count = 0
    fail_log = []

    for d in targets:
        filename = build_filename(d)
        dest = SAVE_DIR / filename

        print(f"  ダウンロード中: {filename} ... ", end="", flush=True)
        result = download_file(session, BASE_URL + filename, dest, auth)

        if result == "ok":
            print("完了")
            done_count += 1
        elif result == "skip_404":
            print("スキップ（ファイルなし）")
        else:
            msg = result.replace("error:", "")
            print(f"失敗 ({msg})")
            fail_log.append((filename, msg))

        time.sleep(INTERVAL)

    elapsed = time.time() - start_time
    print(f"\n完了: {done_count} 件ダウンロード（所要時間: {elapsed:.1f} 秒）")

    if fail_log:
        print(f"\n失敗ファイル ({len(fail_log)} 件):")
        for fname, reason in fail_log:
            print(f"  {fname}: {reason}")


def main():
    all_mode = "--all" in sys.argv

    print("=" * 50)
    print("  株価CSV 自動ダウンロード", "（全期間モード）" if all_mode else "（本日分）")
    print("=" * 50)

    username, password = load_config()
    auth = HTTPBasicAuth(username, password)

    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    print("\n認証を確認中...")
    session = requests.Session()
    if not verify_auth(session, auth):
        print("エラー: 認証に失敗しました。config.txtのID・パスワードを確認してください。")
        sys.exit(1)
    print("認証OK\n")

    if all_mode:
        run_all(session, auth)
    else:
        run_today(session, auth)


if __name__ == "__main__":
    main()
