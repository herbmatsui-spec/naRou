#!/usr/bin/env python3
"""
World State System 垂直ワールド拡張 デモ
"""

from __future__ import annotations

from world_state_system import WorldStateManager


def demo_world_state_extension():
    """ワールドステートシステムの垂直ワールド拡張をデモ"""
    print("=== World State System 垂直ワールド拡張 デモ ===\n")

    # WorldStateManagerのインスタンスを作成
    ws_manager = WorldStateManager()

    print("1. 初期状態の確認")
    visited_layers = ws_manager.get_visited_layers()
    print(f"   訪問済みレイヤー数: {len(visited_layers)}")
    print()

    print("2. レイヤー訪問の記録")
    # 様々なレイヤーを訪問したと記録
    test_visits = [
        ("surface", "plains", 3, "material"),
        ("surface", "plains", 3, "ethereal"),
        ("underground", "forest", 15, "material"),
        ("underground", "forest", 15, "ethereal"),
        ("heaven", "plains", 105, "material"),
        ("heaven", "plains", 105, "ethereal"),
    ]

    for zone, biome, depth, dimension in test_visits:
        ws_manager.record_layer_visit(None, zone, biome, depth, dimension)
        print(f"   訪問記録: {zone}:{biome}:{depth}:{dimension}")
    print()

    print("3. 訪問済みレイヤーの確認")
    visited_layers = ws_manager.get_visited_layers()
    print(f"   訪問済みレイヤー数: {len(visited_layers)}")
    for layer in sorted(visited_layers)[:5]:  # 最初の5つを表示
        print(f"   - {layer}")
    if len(visited_layers) > 5:
        print(f"   ...および{len(visited_layers) - 5}つ以上のその他のレイヤー")
    print()

    print("4. 特定レイヤーの訪問確認")
    test_checks = [
        ("surface", "plains", 3, "material", True),  # 訪問済み
        ("surface", "plains", 4, "material", False),  # 未訪問
        ("heaven", "plains", 105, "ethereal", True),  # 訪問済み
        ("otherworld", "ruins", 55, "material", False),  # 未訪問
    ]

    for zone, biome, depth, dimension, expected in test_checks:
        result = ws_manager.is_layer_visited(zone, biome, depth, dimension)
        status = "✓" if result == expected else "✗"
        print(f"   {status} {zone}:{biome}:{depth}:{dimension}: {result} (期待: {expected})")
    print()

    print("5. レイヤー発見の記録")
    # 特定のレイヤーで発見したものを記録
    discoveries = [
        ("surface", "plains", 3, "material", "rare_item", "金色の小麦"),
        ("surface", "plains", 3, "material", "event", "迷子の旅行者を助けた"),
        ("underground", "forest", 15, "material", "rare_item", "女王の蜜"),
        ("underground", "forest", 15, "material", "event", "キノコの林の秘密を解明"),
        ("heaven", "plains", 105, "material", "rare_item", "神性の欠片"),
        ("heaven", "plains", 105, "material", "event", "天使のメッセージを受け取った"),
    ]

    for zone, biome, depth, dimension, disc_type, disc_data in discoveries:
        ws_manager.add_layer_discovery(zone, biome, depth, dimension, disc_type, disc_data)
        print(f"   発見記録: {zone}:{biome}:{depth}:{dimension} - {disc_type}: {disc_data}")
    print()

    print("6. レイヤー発見の取得")
    test_discovery_checks = [
        ("surface", "plains", 3, "material"),
        ("underground", "forest", 15, "material"),
        ("heaven", "plains", 105, "material"),
        ("surface", "plains", 4, "material"),  # 発見なしのレイヤー
    ]

    for zone, biome, depth, dimension in test_discovery_checks:
        discoveries = ws_manager.get_layer_discoveries(zone, biome, depth, dimension)
        print(f"   {zone}:{biome}:{depth}:{dimension}: {len(discoveries)}件の発見")
        for disc in discoveries:
            print(f"     - {disc['type']}: {disc['data']}")
    print()

    print("7. プレイヤー層ヒストリの確認")
    # 注意: ここでNoneを渡しているので実際のプレイヤーオブジェクトではない
    # 実際の使用では、プレイヤーオブジェクトを渡す
    tpl = ws_manager.registry.get_template()
    print(f"   ヒストリエントリ数: {len(tpl.player_layer_history)}")
    for i, entry in enumerate(tpl.player_layer_history[:3]):  # 最初の3つを表示
        print(f"   エントリ{i + 1}: {entry['layer']} at {entry['timestamp']}")
    if len(tpl.player_layer_history) > 3:
        print(f"   ...および{len(tpl.player_layer_history) - 3}つ以上のその他のエントリ")
    print()

    print("=== World State System デモ完了 ===")


if __name__ == "__main__":
    demo_world_state_extension()
