#!/usr/bin/env python3
"""
Vertical World System デモスクリプト
基本的な機能を示すシンプルな例
"""

from world_layer import WorldLayer
from world_map_manager import WorldMapManager


def demo_basic_functionality():
    """基本的な機能のデモ"""
    print("=== Vertical World System デモ ===\n")

    # 1. WorldLayerの作成とテスト
    print("1. WorldLayerの作成")
    layer = WorldLayer("underground", "forest", 25, "material")
    print(
        f"   作成されたレイヤー: {layer.zone} {layer.biome} 深度{layer.depth} {layer.dimension}"
    )
    print(f"   テーマID: {layer.theme_data.get('theme_id', 'N/A')}")
    print(f"   レイヤー名: {layer.theme_data.get('name', 'N/A')}")
    print(f"   難易度修正子: {layer.theme_data.get('difficulty_modifier', 'N/A')}")
    print()

    # 2. モンスタープールの取得
    print("2. モンスタープールの取得")
    monster_pool = layer.get_monster_pool()
    print(f"   一般的なモンスター: {monster_pool.get('common', [])}")
    print(f"    uncommonなモンスター: {monster_pool.get('uncommon', [])}")
    print(f"   稀なモンスター: {monster_pool.get('rare', [])}")
    print(f"   固有ボス: {layer.get_unique_boss()}")
    print()

    # 3. 資源の取得
    print("3. 資源の取得")
    resources = layer.get_resources()
    print(f"   一般的な資源: {resources.get('common', [])}")
    print(f"    uncommonな資源: {resources.get('uncommon', [])}")
    print(f"   稀な資源: {resources.get('rare', [])}")
    print()

    # 4. WorldMapManagerのテスト
    print("4. WorldMapManagerのテスト")
    world_manager = WorldMapManager(max_loaded_layers=3)

    # レイヤーの取得または作成
    test_layer = world_manager.get_or_create_layer("surface", "plains", 5, "material")
    print(
        f"   取得/作成されたレイヤー: {test_layer.zone}:{test_layer.biome}:{test_layer.depth}:{test_layer.dimension}"
    )

    # レイヤーのロード
    game_map = world_manager.load_layer("surface", "plains", 5, "material")
    if game_map:
        print(f"   ロードされたマップサイズ: {game_map.width}x{game_map.height}")
        print(f"   マップタイプ: {game_map.map_type}")
        print(f"   フロアレベル: {game_map.floor_level}")
        if game_map.world_layer:
            print(
                f"   マップに関連付けられたレイヤー: {game_map.world_layer.zone}:{game_map.world_layer.biome}:{game_map.world_layer.depth}:{game_map.world_layer.dimension}"
            )
    print()

    # 5. 隣接レイヤーの取得
    print("5. 隣接レイヤーの取得")
    adjacent_layers = world_manager.get_adjacent_layers(
        "surface", "plains", 5, "material"
    )
    print(f"   隣接レイヤー数: {len(adjacent_layers)}")
    for i, adj_layer in enumerate(adjacent_layers[:3]):  # 最初の3つだけ表示
        print(
            f"   隣接レイヤー{i + 1}: {adj_layer.zone}:{adj_layer.biome}:{adj_layer.depth}:{adj_layer.dimension}"
        )
    if len(adjacent_layers) > 3:
        print(f"   ...および{len(adjacent_layers) - 3}つ以上のその他のレイヤー")
    print()

    # 6. 統計情報
    print("6. 統計情報")
    stats = world_manager.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    print("=== デモ完了 ===")


if __name__ == "__main__":
    demo_basic_functionality()
