#!/usr/bin/env python3
"""run.py - naRou ワンタッチ起動スクリプト（Step 69）。

環境を判定し、テキストモードまたは Web モードを自動選択して起動する。
- ヘッドレス環境 (DISPLAY 未設定) ではテキストモードを強制
- それ以外は通常起動（SDL が使えればグラフィカルモード、使えなければ Web サーバー待機）
"""
from __future__ import annotations

import os
import subprocess
import sys


def main() -> None:
    # ヘッドレス判定: DISPLAY が unset かつ Linux らしき環境
    if not os.environ.get("DISPLAY") and sys.platform.startswith("linux"):
        os.environ["NAROU_FORCE_TEXT"] = "1"
        print("[run.py] ヘッドレス環境を検出 → テキストモードを強制します")
    else:
        print("[run.py] グラフィカル環境または macOS/Windows → 通常起動を試みます")

    # メインスクリプトを起動
    try:
        subprocess.run([sys.executable, "main.py"], check=False)
    except KeyboardInterrupt:
        print("\n[run.py] 中断されました")

if __name__ == "__main__":
    main()