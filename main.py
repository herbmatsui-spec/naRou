import subprocess
import sys
import os

from pathlib import Path
try:
    import pydantic
except ImportError:
    _stubs = Path(__file__).resolve().parent / "stubs"
    if str(_stubs) not in sys.path:
        sys.path.insert(0, str(_stubs))


def run_script(script_name):
    if os.path.exists(script_name):
        print(f"\n--- {script_name} を実行しています ---")
        subprocess.run([sys.executable, script_name])
        print(f"--- {script_name} の実行が完了しました ---\n")
    else:
        print(f"\nエラー: {script_name} が見つかりません。")

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
    while True:
        print("========================================")
        print("  naRou: Masterpiece Edition 統合システムメニュー")
        print("========================================")
        print("1. naRou: Masterpiece Edition（ゲーム本編）を起動")
        print("2. バトルバランス自動検証を実行 (tests/balance_simulator.py)")
        print("0. 終了")
        print("========================================")
        
        choice = input("実行したいメニューの番号を入力してください (? または help でヘルプ表示): ")
        
        if choice == '1':
            print("\nゲーム本編を起動します...\n")
            try:
                import game
                game.main()
            except ImportError:
                print("エラー: game.py が見つからないか、エラーがあります。")
            except Exception as e:
                from exceptions import ElonaError
                print(f"\n【重大なエラーが発生しました】: {e}")
                err = ElonaError(str(e)) if not isinstance(e, ElonaError) else e
                log_file = err.log_to_file()
                print(f"詳細ログを保存しました: {log_file}\n")
        elif choice == '2':
            run_script("tests/balance_simulator.py")
        elif choice == '0':
            print("システムを終了します。")
            break
        elif choice.lower() in ['?', 'help']:
            show_help()
        else:
            print("無効な入力です。正しい番号を入力してください。\n")

if __name__ == "__main__":
    main()