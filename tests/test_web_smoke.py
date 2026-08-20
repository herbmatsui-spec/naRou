"""Step 67: Web サーバー スモークテスト。"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def test_web_server_smoke() -> None:
    """サーバーを起動して / にアクセスし、200 OK を確認する。"""
    # サーバーをバックグラウンドで起動
    proc = subprocess.Popen(
        [sys.executable, "web_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        # サーバー起動待ち（最大5秒）
        for _ in range(50):  # 0.1秒 x 50 = 5秒
            try:
                with urllib.request.urlopen(
                    "http://127.0.0.1:8080/health", timeout=1
                ) as resp:
                    if resp.status == 200:
                        break
            except urllib.error.URLError:
                time.sleep(0.1)
        else:
            raise RuntimeError("サーバーが起動しませんでした")

        # / にアクセス
        with urllib.request.urlopen("http://127.0.0.1:8080/", timeout=5) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            html = resp.read().decode("utf-8")
            assert "<html" in html.lower(), "HTML が返されていません"

    finally:
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    test_web_server_smoke()
    print("Web smoke test passed")