"""AIロール網羅テスト (Phase 2 Step 54)"""

from __future__ import annotations

import os
import sys

import pytest
import yaml

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from constants import (  # noqa: E402
    AI_ROLE_BRUTE,
    AI_ROLE_FLANKER,
    AI_ROLE_KITER,
)
from data_manager import DataManager  # noqa: E402

MONSTERS_YAML = os.path.join(_ROOT, "data", "monsters.yaml")
VALID_ROLES = {AI_ROLE_BRUTE, AI_ROLE_KITER, AI_ROLE_FLANKER, "caster", "boss"}


def test_every_monster_declares_ai_role():
    """Step 54.3: 名前部分一致フォールバックに依存しないモンスターは ai_role を明示宣言する

    例外: novice_wizard は既存回帰テスト (test_name_substring_fallback_still_applies)
    がフォールバック経路の検証体として保持しているため、明示宣言を禁止されている。
    """
    FALLBACK_SPECIMENS = {"novice_wizard"}

    with open(MONSTERS_YAML, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    missing = [
        mid for mid, entry in data.items()
        if not entry.get("ai_role") and mid not in FALLBACK_SPECIMENS
    ]
    assert not missing, f"ai_role を宣言していないモンスター: {missing}"

    invalid = {
        mid: entry["ai_role"]
        for mid, entry in data.items()
        if entry.get("ai_role") is not None and entry.get("ai_role") not in VALID_ROLES
    }
    assert not invalid, f"無効な ai_role 宣言: {invalid}"


def test_declared_ai_role_flows_into_entity():
    """Step 54.1: 宣言された ai_role が create_monster 経由で Entity へ流れる"""
    with open(MONSTERS_YAML, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    dm = DataManager()
    for monster_id, entry in data.items():
        declared_role = entry.get("ai_role")
        if not declared_role:
            continue
        mob = dm.create_monster(monster_id)
        assert mob.ai_role == declared_role, (
            f"{monster_id}: 宣言 {declared_role} が Entity に流れていない (実体 {mob.ai_role})"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
