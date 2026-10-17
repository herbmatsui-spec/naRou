"""Tests for HuskComponent"""

import pytest
from naRou.ecs.components.components import HuskComponent


def test_husk_component_to_from_dict():
    """HuskComponentのto_dictとfrom_dictの往復でデータが保存される"""
    # 元のコンポーネントを作成
    original = HuskComponent(
        husk_id="test_husk_001",
        source_monster="slime",
        tier=2,
        decay=10,
        corruption=5,
        slots=3,
        injected_skills=["fire_bolt", "heal"],
        injected_codes=["synergy_fire_heal"]
    )

    # dictに変換
    data = original.to_dict()

    # dictから復元
    restored = HuskComponent.from_dict(data)

    # ソースモンスターが保存されていることを確認
    assert restored.source_monster == "slime"
    # 他のフィールドも保存されていることを確認
    assert restored.husk_id == "test_husk_001"
    assert restored.tier == 2
    assert restored.decay == 10
    assert restored.corruption == 5
    assert restored.slots == 3
    assert restored.injected_skills == ["fire_bolt", "heal"]
    assert restored.injected_codes == ["synergy_fire_heal"]

    # 空のコンポーネントでもデフォルト値で正常に動作することを確認
    empty = HuskComponent(husk_id="", source_monster="")
    data_empty = empty.to_dict()
    restored_empty = HuskComponent.from_dict(data_empty)
    assert restored_empty.source_monster == ""
    assert restored_empty.husk_id == ""
    assert restored_empty.tier == 1  # デフォルト
    assert restored_empty.decay == 0
    assert restored_empty.max_decay == 100
    assert restored_empty.corruption == 0
    assert restored_empty.slots == 1
    assert restored_empty.injected_skills == []
    assert restored_empty.injected_codes == []
