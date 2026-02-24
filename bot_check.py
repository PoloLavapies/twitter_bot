#!/usr/bin/env python3
"""pieces.tsv のチェックツール
- 文字数超過チェック
- リンク切れチェック
- 最新ツイートチェック（24時間以上ツイートがなければメール通知）
"""

import os
import urllib.request
import urllib.error
from datetime import datetime, timezone
import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate

TSV_PATH = os.path.join(os.path.dirname(__file__), "../twitter_bot/pieces.tsv")


def load_tsv():
    """TSVファイルを読み込み、(作曲者, 曲名, 説明, URL) のリストを返す"""
    rows = []
    with open(TSV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            cols = line.split("\t")
            if len(cols) >= 4:
                rows.append((cols[0], cols[1], cols[2], cols[3]))
    return rows


def send_email(title, body):
    """Gmail SMTP でメールを送信"""
    msg = MIMEText(body)
    msg["Subject"] = title
    msg["From"] = FROM_ADDRESS
    msg["To"] = TO_ADDRESS
    msg["Date"] = formatdate()

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(FROM_ADDRESS, FROM_PASSWORD)
        server.sendmail(FROM_ADDRESS, TO_ADDRESS, msg.as_string())


def check_length(rows, threshold=130):
    """文字数が閾値を超える行をメール通知"""
    results = []
    for composer, title, desc, url in rows:
        total_len = len(composer) + len(title) + len(desc) + len(url)
        if total_len > threshold:
            results.append((composer, title, total_len))

    results.sort(key=lambda x: x[2], reverse=True)
    if results:
        lines = "\n".join(f"{composer} {title} {length}文字" for composer, title, length in results)
        send_email(
            "【Bot監視】文字数超過",
            f"以下のエントリが文字数上限（{threshold}文字）を超えています。\n\n{lines}",
        )


def is_link_dead(url):
    """URLがリンク切れかどうかを判定"""
    try:
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, timeout=10) as resp:
            # YouTube の場合、削除された動画でも200を返すことがあるのでGETで確認
            if "youtube" in url or "youtu.be" in url:
                req = urllib.request.Request(url)
                req.add_header("User-Agent", "Mozilla/5.0")
                with urllib.request.urlopen(req, timeout=10) as resp:
                    html = resp.read().decode("utf-8", errors="ignore")
                    # 動画が利用不可の場合のパターン
                    if "Video unavailable" in html or "この動画は再生できません" in html:
                        return True
            return False
    except (urllib.error.HTTPError, urllib.error.URLError):
        return True
    except Exception:
        return True


def check_links(rows):
    """リンク切れをチェックして表示"""
    print("=== リンク切れチェック中 ===")
    dead_links = []
    for i, (composer, title, desc, url) in enumerate(rows):
        # TODO あとで消す
        if i > 10:
            break
        print(f"\r{i + 1}/{len(rows)} 件チェック中...", end="", flush=True)
        if is_link_dead(url):
            dead_links.append((composer, title, url))

    if dead_links:
        print("=== リンク切れ ===")
        for composer, title, url in dead_links:
            print(f"{composer} {title}")
            print(f"  {url}")
    else:
        print("リンク切れはありませんでした")
    print()


FROM_ADDRESS = os.getenv('EMAIL_ADDRESS')
TO_ADDRESS = FROM_ADDRESS
FROM_PASSWORD = os.getenv('EMAIL_PASSWORD')


def check_latest_tweet(username):
    """最新ツイートが24時間以上前ならメール通知"""
    from playwright.sync_api import sync_playwright

    print(f"=== @{username} の最新ツイートをチェック中 ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(f"https://x.com/piano_music_bot", wait_until="networkidle", timeout=30000)
            # ログインウォールが出る場合があるので待機
            page.wait_for_timeout(3000)

            time_el = page.locator("article time").first
            if time_el.count() == 0:
                print("最新ツイートの時刻を取得できませんでした（ログインウォールの可能性）")
                send_email(
                    "【Bot監視】ツイート取得失敗",
                    f"@{username} の最新ツイートを取得できませんでした。\nログインウォール等の可能性があります。",
                )
                return

            dt_str = time_el.get_attribute("datetime")
            tweet_time = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            diff = now - tweet_time
            hours = diff.total_seconds() / 3600

            print(f"最新ツイート: {tweet_time.isoformat()} ({hours:.1f}時間前)")

            if hours >= 24:
                print("24時間以上ツイートがありません。メールで通知します。")
                send_email(
                    "【Bot監視】24時間以上ツイートなし",
                    f"@{username} が {hours:.1f} 時間ツイートしていません。\nBotが停止している可能性があります。",
                )
            else:
                print("正常にツイートされています。")
        except Exception as e:
            print(f"ツイートチェック中にエラー: {e}")
            send_email(
                "【Bot監視】チェックエラー",
                f"@{username} のツイートチェック中にエラーが発生しました。\n{e}",
            )
        finally:
            browser.close()
    print()


def main():
    rows = load_tsv()
    check_length(rows)
    check_links(rows)
    # check_latest_tweet("piano_music_bot")


if __name__ == "__main__":
    main()
