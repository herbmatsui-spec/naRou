import subprocess
import sys
import os

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
  Elona Clone 統合システム - ヘルプ
========================================
このシステムは、Elonaクローンと関連ツールを起動するためのメニューです。

1. Elona クローン（ゲーム本編）を起動
   - ローグライクゲーム「Elona」のクローン版を起動します。
   - ダンジョン探索、クエスト達成、キャラ育成などを楽しめます。
   - ゲーム内で [?] または [h] キーを押すと詳細なヘルプを参照できます。

2. 経済シミュレーションを実行 (economy_sim.py)
   - Elonaの経済システムをシミュレートするスクリプトを実行します。
   - 価格変動、取引、インフレなどの経済現象を観察できます。

3. ワークフローを実行 (orchestrator.py)
   - 複数のタスクを自動的に実行するオーケストレーターを起動します。
   - 設定されたワークフローに従って、さまざまなユーティリティを順次実行します。

0. 終了
   - システムを終了します。

その他の操作:
- メニュー表示中に '?' または 'help' と入力するとこのヘルプを表示します。
- 数字以外の入力はエラーとなります。

初心者へのアドバイス:
まずは「1. Elona クローン（ゲーム本編）を起動」を選んでゲームを始めてみてください。
ゲーム開始直後は画面左下に操作ガイドが表示されるので、それに従ってください。
さらに詳細なヘルプが必要な場合は、ゲーム内で [?] キーを押してください。
========================================
"""
    print(help_text)

def main():
    while True:
        print("========================================")
        print("  Elona Clone 統合システムメニュー")
        print("========================================")
        print("1. Elona クローン（ゲーム本編）を起動")
        print("2. 経済シミュレーションを実行 (economy_sim.py)")
        print("3. ワークフローを実行 (orchestrator.py)")
        print("4. バトルバランス自動検証を実行 (tests/balance_simulator.py)")
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
            run_script("economy_sim.py")
        elif choice == '3':
            run_script("orchestrator.py")
        elif choice == '4':
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