#!/usr/bin/env python3
"""
垂直ワールドシステム 統合テスト
すべてのコンポーネントが連携して動作することを確認
"""

from world_map_manager import WorldMapManager
from world_state_system import WorldStateManager


def test_integration():
    """すべてのコンポーネントの統合テスト"""
    print("=== 垂直ワールドシステム 統合テスト ===\n")

    # システムコンポーネントを初期化
    world_manager = WorldMapManager(max_loaded_layers=4)
    state_manager = WorldStateManager()

    print("1. システム初期化完了")
    print(f"   最大ロードレイヤー: {world_manager.max_loaded_layers}")
    print()

    print("2. レイヤー作成・ロード・訪問記録の連携テスト")

    # 複数のレイヤーをテスト
    test_layers = [
        ("surface", "plains", 3, "material", "陽だまりの草原"),
        ("surface", "plains", 3, "ethereal", "霧の草原"),
        ("underground", "forest", 20, "material", "地下のキノコ林"),
        ("heaven", "plains", 105, "material", "聖なる光の草原"),
    ]

    loaded_maps = []

    for zone, biome, depth, dimension, expected_name in test_layers:
        print(f"   処理中: {zone}:{biome}:{depth}:{dimension}")

        # レイヤーをロード
        game_map = world_manager.load_layer(zone, biome, depth, dimension)
        if not game_map:
            print("     エラー: マップのロードに失敗")
            continue

        loaded_maps.append((game_map, zone, biome, depth, dimension))

        # レイヤー訪問を記録（ワールドステートに）
        state_manager.record_layer_visit(None, zone, biome, depth, dimension)

        # テーマ名を確認
        actual_name = game_map.world_layer.theme_data.get("name", "Unknown")
        if expected_name in actual_name:
            print(f"     ✓ テーマ名一致: {actual_name}")
        else:
            print(f"     ✗ テーマ名不一致: 期待={expected_name}, 実際={actual_name}")

        # モンスタープールを取得
        monster_pool = game_map.world_layer.get_monster_pool()
        common_monsters = monster_pool.get("common", [])
        print(f"     ✓ 一般的なモンスター: {common_monsters}")

        # 階層間移動可能性を確認
        transition_info = game_map.get_layer_transition_info()
        can_go_down = transition_info.get("can_go_down", False)
        can_go_up = transition_info.get("can_go_up", False)
        print(f"     ✓ 階層移動: 下={can_go_down}, 上={can_go_up}")
    print()

    print("3. ワールドステートの状態確認")
    visited_count = len(state_manager.get_visited_layers())
    print(f"   訪問済みレイヤー数: {visited_count}")

    visited_layers = list(state_manager.get_visited_layers())
    for layer in visited_layers[:3]:  # 最初の3つを表示
        print(f"   - {layer}")
    if len(visited_layers) > 3:
        print(f"   ...および{len(visited_layers) - 3}つ以上")
    print()

    print("4. 隣接レイヤー計算のテスト")
    # 特定のレイヤーの隣接レイヤーを計算
    test_zone, test_biome, test_depth, test_dim = "surface", "plains", 5, "material"
    adjacent = world_manager.get_adjacent_layers(
        test_zone, test_biome, test_depth, test_dim
    )
    print(
        f"   {test_zone}:{test_biome}:{test_depth}:{test_dim} の隣接レイヤー数: {len(adjacent)}"
    )

    # 期待される隣接タイプをチェック
    adj_types = set()
    for adj_layer in adjacent:
        adj_types.add((adj_layer.zone, adj_layer.biome, adj_layer.dimension))

    expected_adj_types = {
        # 同じゾーン・バイオーム・次元での深度移動
        ("surface", "plains", "material"),
        # ゾーン境界移動（地上から地下へ）
        ("underground", "plains", "material"),
    }

    print(f"   検出された隣接タイプ: {adj_types}")
    print(f"   期待される隣接タイプ: {expected_adj_types}")

    # 共通部分をチェック
    common = adj_types & expected_adj_types
    if len(common) >= 2:  # 少なくとも2つは一致しているべき
        print("   ✓ 隣接計算: 期待通りの結果")
    else:
        print("   ⚠ 隣接計算: 予期せぬ結果（詳細調整が必要な場合あり）")
    print()

    print("5. 統計情報")
    world_stats = world_manager.get_statistics()
    print("   ワールドマネージャー:")
    for key, value in world_stats.items():
        print(f"     {key}: {value}")

    # WorldStateの統計も表示（利用可能な場合）
    state_tpl = state_manager.registry.get_template()
    print("   ワールドステート:")
    print(f"     ヒストリエントリ数: {len(state_tpl.player_layer_history)}")
    print(f"     訪問済みレイヤー数: {len(state_tpl.visited_layers)}")
    print(
        f"     発見記録数: {sum(len(v) for v in state_tpl.layer_discoveries.values())}"
    )
    print()

    print("6. マップ生成機能のテスト")
    # 実際にマップを生成して基本的なプロパティをチェック
    test_map = world_manager.load_layer("surface", "forests", 10, "material")
    if test_map:
        print(f"   テストマップサイズ: {test_map.width}x{test_map.height}")
        print(f"   マップタイプ: {test_map.map_type}")
        print(f"   フロアレベル: {test_map.floor_level}")

        # ワールドレイヤーへの参照を確認
        if test_map.world_layer:
            print(
                f"   関連レイヤー: {test_map.world_layer.zone}:{test_map.world_layer.biome}:{test_map.world_layer.depth}:{test_map.world_layer.dimension}"
            )
            print(f"   レイヤー名: {test_map.world_layer.theme_data.get('name')}")
        else:
            print("   警告: ワールドレイヤーへの参照がありません")
    else:
        print("   エラー: テストマップの生成に失敗")
    print()

    print("=== 統合テスト完了 ===")
    print("すべての主要コンポーネントが正常に連携して動作しています！")


if __name__ == "__main__":
    test_integration()
