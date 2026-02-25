#!/usr/bin/env python3
"""pieces.tsv のチェックツール
- 文字数超過チェック
- リンク切れチェック
- 最新ツイートチェック（24時間以上ツイートがなければメール通知）
"""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate


TSV_PATH = os.path.join(os.path.dirname(__file__), "../twitter_bot/pieces.tsv")
FROM_ADDRESS = os.getenv('EMAIL_ADDRESS')
TO_ADDRESS = FROM_ADDRESS
FROM_PASSWORD = os.getenv('EMAIL_PASSWORD')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')


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


def check_latest_tweet():
    """Botワークフローの最終成功実行が24時間以上前ならメール通知"""
    api_url = "https://api.github.com/repos/PoloLavapies/twitter_bot/actions/workflows/twitter_bot.yml/runs?status=success&per_page=1"
    try:
        req = urllib.request.Request(
            api_url,
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        runs = data.get("workflow_runs", [])

        run_time = datetime.fromisoformat(runs[0]["updated_at"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        hours = (now - run_time).total_seconds() / 3600

        if hours >= 24:
            send_email(
                "【Bot監視】24時間以上ツイートなし",
                f"Botのワークフローが {hours:.1f} 時間実行されていません。\nBotが停止している可能性があります。",
            )
        else:
            print(f"bot の最終実行は {hours:.1f} 時間前でした。")
    except Exception as e:
        send_email(
            "【Bot監視】チェックエラー",
            f"ワークフロー実行チェック中にエラーが発生しました。\n{e}",
        )


# 140 だが、厳しめに設定
def check_length(rows, threshold=135):
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
            f"以下が文字数上限（{threshold}文字）を超えています。\n\n{lines}",
        )
    else:
        print(f"文字数上限 ({threshold}文字を超えるツイートはありませんでした。")


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
    dead_links = []
    for i, (composer, title, desc, url) in enumerate(rows):

        print(f"\r{i + 1}/{len(rows)} 件チェック中...", end="", flush=True)
        if is_link_dead(url):
            dead_links.append((composer, title, url))

    if dead_links:
        lines = "\n".join(f"{composer} {title}\n  {url}" for composer, title, url in dead_links)
        send_email(
            "【Bot監視】リンク切れ",
            f"以下のURLがリンク切れです。\n\n{lines}",
        )
    else:
        print("リンクが切れている動画はありませんでした。")


def main():
    rows = load_tsv()
    check_latest_tweet()
    check_length(rows)
    check_links(rows)


if __name__ == "__main__":
    main()
