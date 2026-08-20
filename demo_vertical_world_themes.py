#!/usr/bin/env python3
"""
Vertical World System テーマデモ
実際のYAMLテーマデータを使用したデモ
"""
from __future__ import annotations

from world_layer import WorldLayer
from world_map_manager import WorldMapManager


def demo_themed_content():
    """実際のテーマデータを使用したデモ"""
    print("=== Vertical World System テーマデモ ===\n")

    # 実際にYAMLファイルに追加したテーマをテスト
    print("1. 地表草原・浅層・物質次元のテーマ")
    surface_plains_shallow = WorldLayer("surface", "plains", 3, "material")
    print(f"   テーマID: {surface_plains_shallow.theme_data.get('theme_id')}")
    print(f"   名前: {surface_plains_shallow.theme_data.get('name')}")
    print(f"   難易度: {surface_plains_shallow.theme_data.get('difficulty_modifier')}")
    print(f"   基本レイアウト: {surface_plains_shallow.theme_data.get('base_layout')}")
    print(
        f"   一般的なモンスター: {surface_plains_shallow.theme_data.get('enemy_pools', {}).get('common', [])}"
    )
    print(
        f"   固有ボス: {surface_plains_shallow.theme_data.get('enemy_pools', {}).get('unique_boss')}"
    )
    print(
        f"   環境ハザード: {surface_plains_shallow.theme_data.get('environmental_hazards', [])}"
    )
    print(
        f"   特殊ルーム: {surface_plains_shallow.theme_data.get('special_rooms', [])}"
    )
    print(
        f"   ストーリーフック: {surface_plains_shallow.theme_data.get('story_hooks', [])}"
    )
    print(
        f"   一般的な資源: {surface_plains_shallow.theme_data.get('resources', {}).get('common', [])}"
    )
    print()

    print("2. 地表草原・浅層・精神次元のテーマ")
    surface_plains_shallow_ethereal = WorldLayer("surface", "plains", 3, "ethereal")
    print(f"   テーマID: {surface_plains_shallow_ethereal.theme_data.get('theme_id')}")
    print(f"   名前: {surface_plains_shallow_ethereal.theme_data.get('name')}")
    print(
        f"   難易度: {surface_plains_shallow_ethereal.theme_data.get('difficulty_modifier')}"
    )
    print(
        f"   一般的なモンスター: {surface_plains_shallow_ethereal.theme_data.get('enemy_pools', {}).get('common', [])}"
    )
    print(
        f"   固有ボス: {surface_plains_shallow_ethereal.theme_data.get('enemy_pools', {}).get('unique_boss')}"
    )
    print(
        f"   環境ハザード: {surface_plains_shallow_ethereal.theme_data.get('environmental_hazards', [])}"
    )
    print()

    print("3. 地下キノコ林・浅層・物質次元のテーマ")
    underground_forest_shallow = WorldLayer("underground", "forest", 15, "material")
    print(f"   テーマID: {underground_forest_shallow.theme_data.get('theme_id')}")
    print(f"   名前: {underground_forest_shallow.theme_data.get('name')}")
    print(
        f"   難易度: {underground_forest_shallow.theme_data.get('difficulty_modifier')}"
    )
    print(
        f"   一般的なモンスター: {underground_forest_shallow.theme_data.get('enemy_pools', {}).get('common', [])}"
    )
    print(
        f"   固有ボス: {underground_forest_shallow.theme_data.get('enemy_pools', {}).get('unique_boss')}"
    )
    print()

    print("4. 天界草原・中層・物質次元のテーマ")
    heaven_plains_mid = WorldLayer("heaven", "plains", 105, "material")
    print(f"   テーマID: {heaven_plains_mid.theme_data.get('theme_id')}")
    print(f"   名前: {heaven_plains_mid.theme_data.get('name')}")
    print(f"   難易度: {heaven_plains_mid.theme_data.get('difficulty_modifier')}")
    print(
        f"   一般的なモンスター: {heaven_plains_mid.theme_data.get('enemy_pools', {}).get('common', [])}"
    )
    print(
        f"   固有ボス: {heaven_plains_mid.theme_data.get('enemy_pools', {}).get('unique_boss')}"
    )
    print(
        f"   環境ハザード: {heaven_plains_mid.theme_data.get('environmental_hazards', [])}"
    )
    print()

    # WorldMapManagerで実際にマップを生成してみる
    print("5. WorldMapManagerを使用したマップ生成テスト")
    world_manager = WorldMapManager()

    # 異なるテーマでマップを生成
    themes_to_test = [
        ("surface", "plains", 3, "material"),
        ("surface", "plains", 3, "ethereal"),
        ("underground", "forest", 15, "material"),
        ("heaven", "plains", 105, "material"),
    ]

    for zone, biome, depth, dimension in themes_to_test:
        print(f"   生成中: {zone}:{biome}:{depth}:{dimension}")
        game_map = world_manager.load_layer(zone, biome, depth, dimension)
        if game_map and game_map.world_layer:
            theme_name = game_map.world_layer.theme_data.get("name", "Unknown")
            difficulty = game_map.world_layer.theme_data.get("difficulty_modifier", 1.0)
            print(f"     成功: {theme_name} (難易度: {difficulty})")
        else:
            print("     失敗: マップの生成に失敗しました")
    print()

    print("6. 統計情報")
    stats = world_manager.get_statistics()
    print(f"   ロード済みレイヤー: {stats['loaded_layers']}")
    print(f"   総レイヤー数: {stats['total_layers']}")
    print(f"   ロード回数: {stats['layer_load_count']}")
    print()

    print("=== テーマデモ完了 ===")


if __name__ == "__main__":
    demo_themed_content()
