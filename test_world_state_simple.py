#!/usr/bin/env python3
"""
ワールドステートの簡単なテスト
"""

from world_state_system import WorldStateManager


def test_world_state_basic():
    """ワールドステートの基本機能をテスト"""
    print("=== ワールドステート基本テスト ===")

    ws_manager = WorldStateManager()

    # 初期状態をチェック
    print(f"初期訪問済みレイヤー数: {len(ws_manager.get_visited_layers())}")
    print(
        f"初期ヒストリ数: {len(ws_manager.registry.get_template().player_layer_history)}"
    )

    # レイヤー訪問を記録
    print("\nレイヤー訪問を記録中...")
    ws_manager.record_layer_visit(None, "test", "zone", 1, "material")

    # すぐにチェック
    print(f"記録後訪問済みレイヤー数: {len(ws_manager.get_visited_layers())}")
    print(
        f"記録後ヒストリ数: {len(ws_manager.registry.get_template().player_layer_history)}"
    )

    # テンプレートを直接取得して中身をチェック
    tpl = ws_manager.registry.get_template()
    print(f"直接テンプレート取得 - 訪問済みレイヤー: {tpl.visited_layers}")
    print(f"直接テンプレート取得 - ヒストリ: {len(tpl.player_layer_history)}件")
    if tpl.player_layer_history:
        print(f"  最初のエントリ: {tpl.player_layer_history[0]}")

    print("\n=== テスト完了 ===")


if __name__ == "__main__":
    test_world_state_basic()
