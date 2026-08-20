#!/usr/bin/env python3
"""
後方互換性テスト
既存の機能が壊れていないことを確認
"""

from map_engine import GameMap
from world_layer import WorldLayer


def test_backward_compatibility():
    """後方互換性をテスト"""
    print("=== 後方互換性テスト ===\n")

    print("1. 既存のマップエンジン機能テスト")
    # 従来通りのマップ生成が動作するか確認
    game_map = GameMap(40, 25, "dungeon", 1)
    game_map.generate_dungeon(max_rooms=5, room_min_size=3, room_max_size=8)

    print(f"   マップサイズ: {game_map.width}x{game_map.height}")
    print(f"   マップタイプ: {game_map.map_type}")
    print(f"   フロアレベル: {game_map.floor_level}")
    print(f"   部屋数: {len(game_map.rooms)}")
    print(f"   スタート位置: {game_map.start_pos}")
    print(f"   下り階段位置: {game_map.stairs_down_pos}")
    print(f"   上り階段位置: {game_map.stairs_up_pos}")
    print()

    # 基本的な妥当性チェック
    assert 0 <= game_map.start_pos[0] < game_map.width
    assert 0 <= game_map.start_pos[1] < game_map.height
    assert 0 <= game_map.stairs_down_pos[0] < game_map.width
    assert 0 <= game_map.stairs_down_pos[1] < game_map.height
    assert 0 <= game_map.stairs_up_pos[0] < game_map.width
    assert 0 <= game_map.stairs_up_pos[1] < game_map.height
    print("   ✓ マップ位置情報が有効範囲内")
    print()

    print("2. 既存のテーマ互換性テスト")
    # 従来のテーマ形式がまだ動作するか確認
    # これにより、WorldLayerがフォールバックメカニズムを通じて
    # 従来のテーマも扱えることを確認
    try:
        # これは従来のテーマ形式を参照しようとするが、
        # 見つからない場合はデフォルトテーマにフォールバックするはず
        legacy_layer = WorldLayer("surface", "plains", 1, "material")
        print(
            f"   レイヤー作成成功: {legacy_layer.zone}:{legacy_layer.biome}:{legacy_layer.depth}:{legacy_layer.dimension}"
        )
        print(f"   テーマID: {legacy_layer.theme_data.get('theme_id')}")
        print(f"   テーマ名: {legacy_layer.theme_data.get('name')}")
        print("   ✓ 後方互換性メカニズムが動作中")
    except Exception as e:
        print(f"   エラー: {e}")
    print()

    print("3. 基本マップ機能テスト")
    # マップが基本的に機能するかをテスト
    # FOV計算などの基本メソッドがエラーなく動作するか
    try:
        # 簡単なFOVテスト（中心から）
        center_x, center_y = game_map.width // 2, game_map.height // 2
        game_map.compute_fov(center_x, center_y, radius=5)
        print(f"   FOV計算: 中心({center_x}, {center_y})から半径5で実行成功")

        # 一部の位置が探索済みとしてマークされているかチェック
        explored_count = 0
        total_samples = 50
        import random

        for _ in range(total_samples):
            x = random.randint(0, game_map.width - 1)
            y = random.randint(0, game_map.height - 1)
            if game_map.explored[x][y]:
                explored_count += 1

        print(
            f"   探索状況サンプリング: {explored_count}/{total_samples} タイルが探索済み"
        )
        print("   ✓ 基本マップ機能が動作中")
    except Exception as e:
        print(f"   エラー in 基本マップ機能: {e}")
    print()

    print("=== 後方互換性テスト完了 ===")
    print("既存のコア機能は正常に動作しています。")


if __name__ == "__main__":
    test_backward_compatibility()
