from __future__ import annotations

import logging
logger = logging.getLogger(__name__)
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

if importlib.util.find_spec("pydantic") is None:
    _stubs = Path(__file__).resolve().parent / "stubs"
    if str(_stubs) not in sys.path:
        sys.path.insert(0, str(_stubs))


def run_script(script_name):
    if os.path.exists(script_name):
        print(f"\n--- {script_name} を実行しています ---")
        subprocess.run([sys.executable, script_name], check=False)
        print(f"--- {script_name} の実行が完了しました ---\n")
    else:
        print(f"\nエラー: {script_name} が見つかりません。")


def prompt_accessibility():
    """Step 35/36: 色覚対応と難易度を選択し、config に永続化する。"""
    try:
        from config import configure, get_config
    except Exception:
        # TODO: handle exception properly

        logger.exception("Unhandled exception")
        return

    print("\n--- アクセシビリティ設定（Enter で現在値を維持）---")
    cv_current = get_config("accessibility.color_vision") or "none"
    diff_current = get_config("game.difficulty") or "normal"

    print(f"色覚対応 [1]none [2]deutan [3]protan [4]tritan  (現在: {cv_current})")
    cv = input("選択> ").strip()
    cv_map = {"1": "none", "2": "deutan", "3": "protan", "4": "tritan"}
    if cv in cv_map:
        configure("accessibility.color_vision", cv_map[cv])

    print(f"難易度 [1]easy [2]normal [3]hard  (現在: {diff_current})")
    df = input("選択> ").strip()
    df_map = {"1": "easy", "2": "normal", "3": "hard"}
    if df in df_map:
        configure("game.difficulty", df_map[df])
    print("設定を保存しました。\n")


def start_web_backend(open_browser: bool = False, port: int = 8080):
    """Step 50/51: Web サーバーを別スレッドで起動し、必要ならブラウザを開く。"""
    try:
        import game
        import web_server

        eng = game.Engine()
        srv = web_server.start_web_server(eng, port=port)
        if srv and open_browser:
            web_server.launch_browser(f"http://localhost:{port}")
        return srv
    except Exception as exc:  # noqa: BLE001 - バックエンド起動失敗は致命的ではない
        print(f"Web バックエンド起動に失敗しました: {exc}")
        logger.exception("Unhandled exception")
        return None


def show_help():
    help_text = """
========================================
  naRou: Masterpiece Edition 統合システム - ヘルプ
========================================
このシステムは、naRou: Masterpiece Editionと関連ツールを起動するためのメニューです。

1. naRou: Masterpiece Edition（ゲーム本編）を起動
   - ローグライクゲーム「naRou: Masterpiece Edition」を起動します。
   - ダンジョン探索、クエスト達成、キャラ育成などを楽しめます。
   - ゲーム内で [?] または [h] キーを押すと詳細なヘルプを参照できます。

 2. バトルバランス自動検証を実行 (tests/balance_simulator.py)
     - 戦闘バランスを自動検証し、HTML/JSON レポートを出力します。

  0. 終了
    - システムを終了します。

その他の操作:
- メニュー表示中に '?' または 'help' と入力するとこのヘルプを表示します。
- 数字以外の入力はエラーとなります。

初心者へのアドバイス:
まずは「1. naRou: Masterpiece Edition（ゲーム本編）を起動」を選んでゲームを始めてみてください。
ゲーム開始直後は画面左下に操作ガイドが表示されるので、それに従ってください。
さらに詳細なヘルプが必要な場合は、ゲーム内で [?] キーを押してください。
========================================
"""
    print(help_text)


def main():
    # 環境変数でテキストモードを強制（run.py などから利用）
    import os
    if os.environ.get("NAROU_FORCE_TEXT") == "1":
        print("NAROU_FORCE_TEXT が設定されているため、テキストモードを起動します。")
        try:
            import main_text
            main_text.main()
        except ImportError:
            print("エラー: main_text.py が見つかりません。")
        return

    while True:
        print("========================================")
        print("  naRou: Masterpiece Edition 統合システムメニュー")
        print("========================================")
        print("1. naRou: Masterpiece Edition（ゲーム本編）を起動")
        print("2. バトルバランス自動検証を実行 (tests/balance_simulator.py)")
        print("3. テキストモードで起動（GPU/SDL 不要）")
        print("0. 終了")
        print("========================================")

        choice = input(
            "実行したいメニューの番号を入力してください (? または help でヘルプ表示): "
        )

        if choice == "1":
            print("\nゲーム本編を起動します...\n")
            prompt_accessibility()
            # Step 50/51: --open 指定時は Web サーバーを裏で起動しブラウザを開く
            if "--open" in sys.argv:
                start_web_backend(open_browser=True)
            try:
                import game

                game.main()
            except ImportError:
                print("エラー: game.py が見つからないか、エラーがあります。")
            except Exception as e:  # noqa: BLE001
                logger.exception("Unhandled exception")
                from exceptions import ElonaError

                print(f"\n【重大なエラーが発生しました】: {e}")
                err = ElonaError(str(e)) if not isinstance(e, ElonaError) else e
                log_file = err.log_to_file()
                print(f"詳細ログを保存しました: {log_file}\n")
        elif choice == "3":
            print("\nテキストモードを起動します...\n")
            prompt_accessibility()
            try:
                import main_text

                main_text.main()
            except ImportError:
                print("エラー: main_text.py が見つからないか、エラーがあります。")
            except KeyboardInterrupt:
                print("\nテキストモードを終了しました。")
        elif choice == "2":
            run_script("tests/balance_simulator.py")
        elif choice == "0":
            print("システムを終了します。")
            break
        elif choice.lower() in ["?", "help"]:
            show_help()
        else:
            print("無効な入力です。正しい番号を入力してください。\n")


if __name__ == "__main__":
    main()