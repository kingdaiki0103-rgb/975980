# CrowdWorks Short Video Job Watcher

クラウドワークスに掲載されたショート動画編集系の新着案件を検出し、Discord Webhook に埋め込みメッセージで通知する最小構成です。

初期版では AI 判定や複雑な本文解析は行わず、次の条件を優先します。

- 対象キーワードを含む
- 動画編集系の文言を含む
- 表示金額が 3,000 円以上
- SQLite に未通知として保存されていない

## 重要: 利用規約と robots.txt

実行前に、必ず現在のクラウドワークス利用規約と robots.txt を確認してください。

- 利用規約: https://crowdworks.jp/pages/agreement
- robots.txt: https://crowdworks.jp/robots.txt

この実装は、実行時に robots.txt を確認し、対象 URL の取得が許可されない場合は停止します。robots.txt が取得できない場合も、初期設定では停止します。

クラウドワークス側で自動取得が禁止されている、または運用上問題があると判断される場合は、このスクレイピング方式を使わず、次の代替案を使ってください。

- クラウドワークス公式メール通知を Gmail / Outlook で受信し、メール内容を Discord へ転送する
- ユーザー自身が開いている検索画面をブラウザ拡張機能で定期確認する
- クラウドワークスが提供する許可済み通知機能、RSS、公式 API がある場合はそれを利用する

## ファイル構成

```text
.
├── main.py                         # 実行入口
├── scraper.py                      # クラウドワークス公開ページ取得・HTML解析
├── filters.py                      # キーワード・金額条件による判定
├── notifier.py                     # Discord Webhook 通知
├── storage.py                      # SQLite による重複通知防止
├── requirements.txt
├── .env.example
├── .github/workflows/crowdworks-watch.yml
└── tests/
```

## Discord Webhook の作成方法

1. Discord で通知したいサーバーを開きます。
2. 通知したいチャンネルの歯車アイコンを押します。
3. `連携サービス` または `Integrations` を開きます。
4. `Webhook` を選び、`新しい Webhook` を作成します。
5. Webhook 名と投稿先チャンネルを確認します。
6. `Webhook URL をコピー` を押します。
7. コピーした URL は外部に公開しないでください。

## ローカルで動かす

Python 3.11 以上を推奨します。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` を開き、`DISCORD_WEBHOOK_URL` に Discord の Webhook URL を設定します。

まずは通知せずに確認したい場合:

```bash
DRY_RUN=true python main.py
```

実際に通知する場合:

```bash
python main.py
```

SQLite の通知履歴は初期設定で `data/notified_jobs.sqlite` に保存されます。同じ案件 ID または URL は 2 回通知されません。

## GitHub Actions で 5 分ごとに実行する

`.github/workflows/crowdworks-watch.yml` は `*/5 * * * *` で設定済みです。

GitHub Actions に Webhook URL を登録します。

1. GitHub リポジトリを開きます。
2. `Settings` を開きます。
3. `Secrets and variables` → `Actions` を開きます。
4. `New repository secret` を押します。
5. Name に `DISCORD_WEBHOOK_URL` を入力します。
6. Secret に Discord Webhook URL を貼り付けます。
7. 保存します。

Actions では SQLite の `data/` を GitHub Actions cache に保存して、過去通知済み案件を復元します。

注意点:

- GitHub Actions の schedule は最低 5 分間隔です。
- 実際の起動は GitHub 側の混雑で数分以上遅れることがあります。
- cache は簡易的な状態保存です。厳密な永続化が必要なら外部 DB を使ってください。

## 即時性が不足する場合の構成

5〜10分以内の通知をより安定させたい場合は、GitHub Actions より常時実行の環境が向いています。

- Render Worker: 無料枠やスリープ条件に注意。常時 worker で `python main.py` を 5 分ごとに実行。
- Railway: cron / worker 構成で運用しやすい。SQLite より Postgres 推奨。
- Google Cloud Run Jobs + Cloud Scheduler: 5 分ごとの定期実行に向く。状態保存は Cloud SQL / Firestore / Cloud Storage 推奨。
- VPS / 自宅サーバー: cron で `*/5 * * * * cd /path && .venv/bin/python main.py`。

## 検索 URL の調整

初期設定では対象キーワードごとにクラウドワークス公開検索 URL を生成します。検索画面の URL が変わった場合やカテゴリで絞りたい場合は、`.env` の `CROWDWORKS_SEARCH_URLS` にカンマ区切りで指定してください。

```env
CROWDWORKS_SEARCH_URLS=https://crowdworks.jp/public/jobs/search?search%5Bkeywords%5D=TikTok%E7%B7%A8%E9%9B%86&order=new
```

## 対象キーワード

- ショート動画
- ショート動画編集
- TikTok
- TikTok編集
- リール動画
- Instagramリール
- YouTube Shorts
- 縦型動画
- SNS動画編集

## テスト

```bash
pytest
```

テストは実サイトへアクセスしません。HTML 解析、フィルタ、Discord payload、SQLite 重複防止を確認します。

## セキュリティ

- Discord Webhook URL は `.env` または GitHub Secrets から読み込みます。
- `.env` と `data/` は `.gitignore` 済みです。
- ログイン情報をソースコードに書かないでください。
- ログインが必要なページ、アクセス制御されたページ、robots.txt で禁止されたページは取得しないでください。
