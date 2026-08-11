# 東証お気に入り銘柄 株価チャート自動配信システム

東証（東京証券取引所）上場銘柄の日足・週足ローソク足チャートを、ログインアカウントごとに最大30銘柄まで登録し、スマートフォンに最適化されたメールで取引日17:00（日足）および土曜日09:00（週足）に自動受信できる完全無料システムです。

---

## 🛠️ システム構成・主要機能

- **WEBフロントエンド**: GitHub Pages（静的WEB・レスポンシブデザイン・ダークモード調）
- **データベース & 認証**: Supabase Free Tier（ユーザー認証 & 最大30銘柄登録管理）
- **バックエンド自動処理**: GitHub Actions + Python (`yfinance` + `mplfinance` + `jpholiday`)
- **メール送信**: Resend API（スマホ最適化レスポンシブHTMLメール）
- **カラー設定**: 日本標準ローソク足（陽線＝赤、陰線＝緑）

---

## 🚀 初回セットアップガイド

### 1. Supabase データベースの設定

1. [Supabase](https://supabase.com/) にて無料プロジェクトを作成します。
2. 左メニューの **SQL Editor** を開き、リポジトリ内の [`schema.sql`](file:///c:/Users/Daiki%20Maeda/Antigravity/お気に入り銘柄配信/schema.sql) の内容をコピー＆ペーストして実行（Run）します。
3. **Authentication** > **Users** から、利用するユーザー（最大5名分）のメールアドレスおよび初期パスワードを事前に登録（発行）します。
4. **Project Settings** > **API** から以下を控えます：
   - `Project URL`
   - `anon key` (公開用キー)
   - `service_role key` (管理者用シークレットキー)

### 2. GitHub Pages でのWEB公開

1. 本リポジトリを GitHub のリポジトリにプッシュします。
2. リポジトリの **Settings** > **Pages** を開きます。
3. Source を `Deploy from a branch` に設定し、`main` ブランチの `/ (root)` を選択して保存します。
4. 公開されたURLにアクセスし、画面右上の歯車アイコン（設定）から `Project URL` および `anon key` を入力・保存します（`config.js` に直書きすることも可能です）。

### 3. GitHub Repository Secrets の設定

リポジトリの **Settings** > **Secrets and variables** > **Actions** にて以下の Secrets を登録します：

| Secret名 | 設定内容 |
| :--- | :--- |
| `SUPABASE_URL` | Supabaseの Project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabaseの `service_role` キー（全データ参照用） |
| `RESEND_API_KEY` | [Resend](https://resend.com/) で取得したAPIキー (`re_...`) |
| `RESEND_FROM_EMAIL` | 送信元メールアドレス（例: `onboarding@resend.dev` または独自ドメインアドレス） |

---

## ⏰ 自動配信スケジュール

| 配信種別 | トリガー日時 (JST) | 内容 |
| :--- | :--- | :--- |
| **日足チャートメール** | **平日 (月〜金) 17:00頃** | 直近 **50営業日** のローソク足、移動平均線 (5/25/75日)、出来高<br>※祝日・東証休業日は自動判定で送信スキップ |
| **週足チャートメール** | **毎週土曜日 09:00頃** | 直近 **52週分** のローソク足、移動平均線 (13/26週)、出来高 |

---

## 🧪 手動テストの実行方法

GitHub リポジトリの **Actions** タブから `Daily Chart Delivery` または `Weekly Chart Delivery` を選択し、**Run workflow** ボタンを押すことで、指定時刻を待たずにテスト配信メールを即時送信できます。
