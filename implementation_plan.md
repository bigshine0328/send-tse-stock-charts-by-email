# 【改定版 実装計画書】お気に入り銘柄 株価チャート自動配信システム

ご回答いただいた決定事項（**Resend API送信、日本式ローソク足カラー、japanize-matplotlib文字化け対策、Supabase Service Role一括取得**）を統合した最終確定版の実装計画書です。

---

## 1. 実装コンポーネントおよびファイル構成

```
お気に入り銘柄配信/
├── index.html                  # [NEW] スマホ最適化WEB管理画面
├── style.css                   # [NEW] レスポンシブCSS（ダークモード調デザイン）
├── app.js                      # [NEW] Supabase Auth & お気に入り30件管理ロジック
├── config.js                   # [NEW] Supabase接続設定用JS
├── schema.sql                  # [NEW] Supabase DBスキーマ（ユーザー・お気に入り・30件制限トリガー）
├── requirements.txt            # [NEW] Python依存パッケージ（yfinance, resend, japanize-matplotlib等）
├── README.md                   # [NEW] デプロイ・設定ガイド
├── .github/
│   └── workflows/
│       ├── daily_delivery.yml  # [NEW] 取引日17:00 JST 実行ワークフロー
│       └── weekly_delivery.yml # [NEW] 土曜09:00 JST 実行ワークフロー
└── scripts/
    └── delivery.py             # [NEW] 株価取得・チャート生成・Resend送信処理コアスクリプト
```

---

## 2. 詳細実装仕様

### 2.1 WEBフロントエンド (GitHub Pages)
- **`index.html` & `style.css`**:
  - スマホ（375px〜430px）およびPC表示に対応したレスポンシブデザイン。
  - ログイン画面 / 登録済み銘柄（最大30件）メーターおよびプログレスバー / ワンタップ削除リスト。
- **`app.js`**:
  - Supabase Authによるログイン管理。
  - 東証銘柄コード（4桁数字）のフロントエンドバリデーション。
  - 30銘柄上限時の追加防止・警告アラート。

### 2.2 バックエンド処理スクリプト (`scripts/delivery.py`)
1. **データ取得ロジック**:
   - `SUPABASE_SERVICE_ROLE_KEY` を使用して、全登録ユーザー（最大5名）とそのお気に入り銘柄リスト（最大30銘柄/人）を取得。
2. **東証営業日判定 (`jpholiday`)**:
   - 日足配信時、当日の日本祝日および東証休業日（土日・年末年始等）を自動判定。休業日の場合はログを出力して正常終了。
3. **株価データ取得 & ローソク足チャート描画**:
   - `japanize-matplotlib` を読み込み、日本語銘柄名の文字化けを防止。
   - **日本式ローソク足カラー**設定：陽線＝赤（`#e53935`）、陰線＝緑（`#43a047`）。
   - **日足**：直近50営業日＋移動平均線（5日/25日/75日）＋出来高。
   - **週足**：直近52週分＋移動平均線（13週/26週）＋出来高。
   - `ThreadPoolExecutor` による並列処理で生成時間を短縮。
   - **エラーハンドリング**：データ取得失敗銘柄はバッチを止めず「⚠️ 株価データ取得失敗」の警告カードに置き換え。
4. **Resend API によるスマホ最適化メール送信**:
   - `resend` Python SDK / REST API を利用。
   - メール本文内に各銘柄のインライン画像（`cid:` または Base64 / Resend Attachment）と終値・前日比サマリーカードを埋め込んだレスポンシブHTML（`color-scheme: light`）を出力。
   - 各ユーザーの指定メールアドレス宛に個別送信。

### 2.3 自動化ワークフロー (GitHub Actions)
- **`daily_delivery.yml`**:
  - スケジュール: `cron: '0 8 * * 1-5'` (日本時間 平日17:00 JST)
  - 引数: `--type daily`
- **`weekly_delivery.yml`**:
  - スケジュール: `cron: '0 0 * * 6'` (日本時間 土曜日 09:00 JST)
  - 引数: `--type weekly`
- **GitHub Secrets設定**:
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `RESEND_API_KEY`
  - `RESEND_FROM_EMAIL` (例: `onboarding@resend.dev` または 独自ドメイン送信アドレス)

---

## 3. テスト・検証計画

1. **DB & 認証テスト**:
   - `schema.sql` 適用後の30銘柄上限トリガー動作の検証。
   - 事前発行アカウントでのログイン・ログアウト疎通。
2. **スクリプト単体テスト (`delivery.py`)**:
   - 日足50営業日 / 週足52週分のローソク足チャート生成の確認（日本語銘柄名の文字化けなし）。
   - 一部の無効なコード（例: `0000`）が含まれていても正常にフォールバック処理が行われることの検証。
3. **メール受信テスト (Resend)**:
   - スマホ実機（iOS / Android）の標準メールアプリにて、インラインチャート画像が縦スクロールで綺麗に表示されることの確認。
4. **GitHub Actions ワークフローテスト**:
   - `workflow_dispatch`（手動実行トリガー）による日足・週足バッチの完走テスト。
