========================================
  StockChart タスクスケジューラ設定手順
========================================

【登録されるタスク】
  ・StockChart_Daily  ── 月〜金 17:15 に株価CSV取得＋マージ
  ・StockChart_Weekly ── 毎週金曜 17:30 に上記＋週次データ生成


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
① PowerShell を「管理者として実行」する方法
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

方法A（スタートメニューから）：
  1. スタートメニューを開く
  2. 「PowerShell」と入力して検索
  3. 「Windows PowerShell」を右クリック
  4. 「管理者として実行」をクリック

方法B（ファイル名を指定して実行）：
  1. Win + R を押す
  2. 「powershell」と入力
  3. Ctrl + Shift + Enter を押す（管理者権限で起動）


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
② setup_scheduler.ps1 の実行コマンド
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

管理者PowerShellで以下を実行：

  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  & "C:\Users\jnpei\Documents\stock-chart\setup_scheduler.ps1"

※ Set-ExecutionPolicy は実行ポリシーを一時的に緩和します。
  現在のPowerShellウィンドウを閉じると元に戻ります。


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
③ 登録確認方法
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【タスクスケジューラGUIで確認】：
  1. Win + R → 「taskschd.msc」と入力 → Enter
  2. 左ペインの「タスクスケジューラライブラリ」をクリック
  3. 「StockChart_Daily」「StockChart_Weekly」が表示されれば登録済み

【PowerShellで確認】：
  Get-ScheduledTask -TaskName "StockChart_*" | Select-Object TaskName, State

  ─ 出力例 ─────────────────────────────
  TaskName           State
  --------           -----
  StockChart_Daily   Ready
  StockChart_Weekly  Ready
  ───────────────────────────────────────


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
④ タスクを削除したい場合
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【PowerShell（管理者）で削除】：
  Unregister-ScheduledTask -TaskName "StockChart_Daily"  -Confirm:$false
  Unregister-ScheduledTask -TaskName "StockChart_Weekly" -Confirm:$false

【GUIで削除】：
  1. タスクスケジューラを開く（taskschd.msc）
  2. 対象タスクを右クリック → 「削除」


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⑤ 注意事項
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【PCがシャットダウン中の場合】
  タスクは実行されません（StartWhenAvailable=無効のため）。
  その日の株価データを取得したい場合は、
  PCを起動してから run_daily.bat をダブルクリックで手動実行してください。

【実行ログの確認】
  data\auto_run_log.txt に各実行の結果が記録されます。
  エラーが発生した場合もログに記録されます。

【config.txt の設定】
  事前に config.txt に KABU_ID と KABU_PASSWORD を設定してください。
  未設定の場合、タスクは起動しますがエラーで終了します。

  config.txt の場所：
  C:\Users\jnpei\Documents\stock-chart\config.txt

  記載例：
  KABU_ID=your_id_here
  KABU_PASSWORD=your_password_here

【実行タイミングの根拠】
  15:30 ─ 東京市場 終値確定
  16:30 ─ KABU+ csvex にCSVアップロード完了（目安）
  17:15 ─ StockChart_Daily 実行（日次）
  17:30 ─ StockChart_Weekly 実行（週次、金曜のみ）

========================================
