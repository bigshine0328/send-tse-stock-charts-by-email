#!/usr/bin/env python3
"""
お気に入り銘柄 株価チャート自動配信スクリプト (delivery.py)
--------------------------------------------------
- 東証休業日（土日・祝日）の判定と自動スキップ (JST厳密判定)
- Supabaseからのユーザー別お気に入り銘柄（最大30件）取得
- yfinance による株価四本値・出来高データの取得
- japanize-matplotlib + mplfinance による日本式ローソク足チャート画像生成
- Resend API (CIDインライン添付) を利用したマルチデバイス・Gmail Web対応レスポンシブHTMLメール送信
"""

import argparse
import base64
import datetime
import io
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import jpholiday
import japanize_matplotlib  # 日本語フォントを自動ロード
import matplotlib
matplotlib.use('Agg')  # ヘッドレステンプレート
import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
import requests
import yfinance as yf  # 株価データ取得ライブラリ
from supabase import create_client, Client

# JST (日本標準時) タイムゾーンの定義
JST = datetime.timezone(datetime.timedelta(hours=9))

# --- CLI Arguments ---
parser = argparse.ArgumentParser(description="株価チャートメール自動配信バッチ")
parser.add_argument("--type", choices=["daily", "weekly"], default="daily", help="配信種別 (daily: 日足, weekly: 週足)")
args = parser.parse_args()

DELIVERY_TYPE = args.type

# --- Environment Variables ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("[ERROR] SUPABASE_URL または SUPABASE_SERVICE_ROLE_KEY が設定されていません。")
    sys.exit(1)

if not RESEND_API_KEY:
    print("[ERROR] RESEND_API_KEY が設定されていません。")
    sys.exit(1)

# Initialize Supabase Admin Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def is_trading_day(today: datetime.date) -> bool:
    """東証取引日判定 (土日・祝日の場合は False)"""
    # 0 = 月曜, 4 = 金曜, 5 = 土曜, 6 = 日曜
    if today.weekday() in (5, 6):
        return False
    if jpholiday.is_holiday(today):
        return False
    return True


def fetch_all_user_favorites():
    """
    全ユーザーのお気に入り銘柄情報を取得
    Return format: { user_id: { 'email': str, 'favorites': [ { 'ticker': str, 'stock_name': str } ] } }
    """
    try:
        users_resp = supabase.auth.admin.list_users()
        users_list = users_resp if isinstance(users_resp, list) else getattr(users_resp, 'users', [])
    except Exception as e:
        print(f"[ERROR] Failed to list users from Supabase Auth: {e}")
        users_list = []

    user_email_map = {}
    for u in users_list:
        uid = getattr(u, 'id', None) or u.get('id')
        email = getattr(u, 'email', None) or u.get('email')
        if uid and email:
            user_email_map[uid] = email

    res = supabase.table("user_favorites").select("*").execute()
    favorites_rows = res.data if res.data else []

    user_data = {}
    for row in favorites_rows:
        uid = row["user_id"]
        email = user_email_map.get(uid, f"user_{uid[:8]}@example.com")
        if uid not in user_data:
            user_data[uid] = {
                "email": email,
                "favorites": []
            }
        user_data[uid]["favorites"].append({
            "ticker": row["ticker"],
            "stock_name": row.get("stock_name", f"東証 {row['ticker']}")
        })

    return user_data


def generate_chart_image(ticker_code: str, stock_name: str, delivery_type: str):
    """
    yfinanceからデータ取得し、mplfinanceでローソク足チャート画像(PNG base64)および株価サマリーを生成
    """
    clean_code = ticker_code.replace(".T", "").strip()
    yf_symbol = f"{clean_code}.T"

    try:
        ticker = yf.Ticker(yf_symbol)
        if delivery_type == "daily":
            # 直近50営業日程度
            df = ticker.history(period="3mo", interval="1d")
            df = df.tail(50)
            mav_tuple = (5, 25, 75)
            chart_title = f"{stock_name} ({clean_code}) 日足 50営業日"
        else:
            # 直近52週分 (約1年)
            df = ticker.history(period="2y", interval="1wk")
            df = df.tail(52)
            mav_tuple = (13, 26)
            chart_title = f"{stock_name} ({clean_code}) 週足 52週"

        if df.empty or len(df) < 5:
            return {
                "ticker": clean_code,
                "stock_name": stock_name,
                "success": False,
                "error_msg": "株価データが存在しないか取得できませんでした。"
            }

        # 最新株価情報の計算
        latest_row = df.iloc[-1]
        prev_row = df.iloc[-2] if len(df) > 1 else latest_row
        close_price = latest_row["Close"]
        prev_close = prev_row["Close"]
        diff = close_price - prev_close
        diff_pct = (diff / prev_close) * 100 if prev_close != 0 else 0

        # 日本式ローソク足カラー (陽線: 赤 #e53935, 陰線: 緑 #43a047)
        mc = mpf.make_marketcolors(
            up='#e53935',
            down='#43a047',
            edge='inherit',
            wick='inherit',
            volume='inherit'
        )
        s = mpf.make_mpf_style(
            marketcolors=mc,
            gridstyle=':',
            y_on_right=False
        )

        buf = io.BytesIO()
        mpf.plot(
            df,
            type='candle',
            style=s,
            volume=True,
            mav=mav_tuple,
            title=chart_title,
            figratio=(16, 9),
            figscale=1.1,
            savefig=dict(fname=buf, format='png', dpi=120, bbox_inches='tight')
        )
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')

        return {
            "ticker": clean_code,
            "stock_name": stock_name,
            "success": True,
            "close_price": f"{close_price:,.1f}",
            "diff": f"{diff:+,.1f}",
            "diff_pct": f"{diff_pct:+.2f}%",
            "is_positive": diff >= 0,
            "img_base64": img_base64
        }

    except Exception as e:
        print(f"[WARN] Failed to fetch/generate chart for {clean_code}: {e}")
        return {
            "ticker": clean_code,
            "stock_name": stock_name,
            "success": False,
            "error_msg": f"データ取得処理エラー: {str(e)}"
        }
    finally:
        # 例外発生時も確実にmatplotlibメモリを解放
        plt.close('all')


def build_responsive_email_html(chart_results, delivery_type: str, user_email: str):
    """
    スマホ最適化レスポンシブHTMLメールおよびResend CID添付構造の組み立て
    Returns: (html_content: str, attachments_list: list)
    """
    title_text = "日足チャート" if delivery_type == "daily" else "週足チャート"
    now_jst = datetime.datetime.now(JST)
    date_str = now_jst.strftime("%Y年%m月%d日")

    cards_html = ""
    attachments = []

    for item in chart_results:
        ticker = item["ticker"]
        name = item["stock_name"]

        if not item["success"]:
            cards_html += f"""
            <div style="background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 16px; margin-bottom: 20px; color: #f8fafc;">
                <div style="font-weight: bold; font-size: 16px; margin-bottom: 8px;">{name} ({ticker})</div>
                <div style="background-color: #451a1a; color: #fca5a5; padding: 12px; border-radius: 8px; font-size: 14px;">
                    ⚠️ {item['error_msg']}
                </div>
            </div>
            """
            continue

        cid_name = f"chart_{ticker}"
        price = item["close_price"]
        diff = item["diff"]
        diff_pct = item["diff_pct"]
        price_color = "#ef4444" if item["is_positive"] else "#10b981"
        sign = "▲" if item["is_positive"] else "▼"

        # Resend CID インライン添付構造
        attachments.append({
            "filename": f"{ticker}.png",
            "content": item["img_base64"],
            "content_id": cid_name,
            "disposition": "inline"
        })

        cards_html += f"""
        <div style="background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 16px; margin-bottom: 20px; color: #f8fafc;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #334155; padding-bottom: 8px;">
                <div>
                    <span style="background-color: #3b82f6; color: #ffffff; font-weight: bold; padding: 2px 8px; border-radius: 4px; font-size: 14px; margin-right: 8px;">{ticker}</span>
                    <span style="font-size: 16px; font-weight: bold;">{name}</span>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 18px; font-weight: bold;">{price} 円</div>
                    <div style="font-size: 13px; font-weight: bold; color: {price_color};">{sign} {diff} ({diff_pct})</div>
                </div>
            </div>
            <div style="text-align: center;">
                <img src="cid:{cid_name}" alt="{name} チャート" style="width: 100%; max-width: 100%; height: auto; border-radius: 8px; display: block;" />
            </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="light">
    <title>【お気に入り銘柄】{title_text}配信 ({date_str})</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0f172a; font-family: 'Helvetica Neue', Arial, 'Hiragino Kaku Gothic ProN', 'ヒラギノ角ゴ ProN W3', sans-serif; color: #f8fafc;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px 12px;">
        <div style="text-align: center; margin-bottom: 24px; background: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #334155;">
            <h1 style="font-size: 20px; margin: 0 0 8px 0; color: #60a5fa;">📈 お気に入り銘柄 {title_text}レポート</h1>
            <p style="font-size: 13px; color: #94a3b8; margin: 0;">配信日時: {date_str} | 受信アドレス: {user_email}</p>
        </div>

        {cards_html}

        <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #334155; font-size: 12px; color: #64748b;">
            <p>※ 本メールは「東証お気に入り銘柄 チャート配信システム」から自動送信されています。</p>
            <p>※ 株価データ参照元: Yahoo! Finance (yfinance)</p>
        </div>
    </div>
</body>
</html>
"""
    return html, attachments


def send_email_via_resend(to_email: str, subject: str, html_content: str, attachments: list):
    """Resend API を使用したCID添付インラインメール送信"""
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "from": RESEND_FROM_EMAIL,
        "to": [to_email],
        "subject": subject,
        "html": html_content
    }

    if attachments:
        payload["attachments"] = attachments

    resp = requests.post(url, json=payload, headers=headers)
    if resp.status_code in (200, 201):
        print(f"[SUCCESS] Email sent successfully to {to_email}")
        return True
    else:
        print(f"[ERROR] Failed to send email to {to_email}: Status {resp.status_code}, Response: {resp.text}")
        return False


def main():
    now_jst = datetime.datetime.now(JST)
    today = now_jst.date()
    print(f"=== 株価チャート自動配信バッチ開始 (Type: {DELIVERY_TYPE}, JST Date: {today}) ===")

    # 休業日チェック (日足バッチのみ)
    if DELIVERY_TYPE == "daily" and not is_trading_day(today):
        print(f"[INFO] 本日 ({today}) は東証休業日（土日・祝日）のため、メール配信をスキップします。")
        sys.exit(0)

    # ユーザー・お気に入りデータ取得
    user_data = fetch_all_user_favorites()
    if not user_data:
        print("[INFO] 登録ユーザーまたはお気に入り銘柄が存在しません。処理を終了します。")
        sys.exit(0)

    print(f"[INFO] 対象ユーザー数: {len(user_data)} 名")

    # ユーザーごとにチャート生成 & メール送信
    for uid, uinfo in user_data.items():
        email = uinfo["email"]
        favs = uinfo["favorites"]
        print(f"\n--- ユーザー処理中: {email} (銘柄数: {len(favs)}) ---")

        if not favs:
            print(f"[INFO] {email} はお気に入り銘柄が0件のためスキップします。")
            continue

        # チャート並列生成
        chart_results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_stock = {
                executor.submit(generate_chart_image, item["ticker"], item["stock_name"], DELIVERY_TYPE): item
                for item in favs
            }
            for future in as_completed(future_to_stock):
                res = future.result()
                chart_results.append(res)

        # 順序を元の登録順にソート
        ticker_order = {item["ticker"].replace(".T", ""): i for i, item in enumerate(favs)}
        chart_results.sort(key=lambda x: ticker_order.get(x["ticker"], 999))

        # メール組み立て & 送信
        title_type = "日足チャート" if DELIVERY_TYPE == "daily" else "週足チャート"
        subject = f"【株価チャート】お気に入り銘柄 {title_type}配信 ({today.strftime('%Y/%m/%d')})"
        html_body, attachments = build_responsive_email_html(chart_results, DELIVERY_TYPE, email)

        send_email_via_resend(email, subject, html_body, attachments)

    print("\n=== バッチ処理が正常に完了しました ===")


if __name__ == "__main__":
    main()
