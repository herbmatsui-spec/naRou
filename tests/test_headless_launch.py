"""Step 70: ヘッドレス環境でのワンタッチ起動がテキストモードを選ぶことを確認する。

このテストは出荷経路の要であり、`tests/test_entrypoint.py` と同じく実際の起動を
観測する。以前は 10 秒のタイムアウトでゲームの初期化に贴近していたため負荷時に
不安定だった。タイムアウト_detection の抖动は「起動に失敗した」ような表示になるが、
実際には起動が遅かっただけだった。
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

# run_text_mode が出す操作ガイド。テキストモードが実際に一周的唯一な目印になる。
# 描画は ANSI カラーエスケープ入りなので、比較前に除去する。
_TEXT_MODE_GUIDE = "q:終了"
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def test_headless_launches_text_mode() -> None:
    """DISPLAY を unset にして run.py を実行し、テキストモードのゲームループに入れる。"""
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    env["NAROU_FORCE_TEXT"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "run.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    try:
        # NAROU_FORCE_TEXT があると run.py は統合メニューを飛ばしてテキストモードへ入る
        stdout, _ = proc.communicate(input="q\n", timeout=120)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, _ = proc.communicate()
        raise AssertionError("ヘッドレス起動がタイムアウトしました") from None

    rendered = _ANSI.sub("", stdout)
    assert proc.returncode == 0, f"プロセスが異常終了しました (rc={proc.returncode})"
    assert _TEXT_MODE_GUIDE in rendered, "run.py からテキストモードのゲームループ。入っていない"


if __name__ == "__main__":
    test_headless_launches_text_mode()
    print("Headless launch test passed")