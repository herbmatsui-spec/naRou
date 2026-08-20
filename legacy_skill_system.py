"""
レガシースキルシステム
"""

import os
from dataclasses import dataclass
from typing import Any

import yaml


@dataclass
class LegacySkillData:
    """レガシースキルデータクラス"""

    id: str
    min_reincarnation: int
    name: str = ""
    description: str = ""
    effect_type: str = ""
    effect_value: Any = None
    unlock_condition: Any = None


class LegacySkillRegistry:
    """レガシースキルレジストリ（シングルトン的）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data: dict[str, LegacySkillData] = {}
        return cls._instance

    def load(self, path: str = "data/legacy_skills.yaml") -> None:
        """YAMLファイルからレガシースキルデータを読み込み"""
        self._data.clear()
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    raw = yaml.safe_load(f)
                if raw and "legacy_skills" in raw:
                    for sid, sdata in raw["legacy_skills"].items():
                        self._data[sid] = LegacySkillData(
                            id=sid,
                            min_reincarnation=sdata.get("min_reincarnation", 1),
                            name=sdata.get("name", sid),
                            description=sdata.get("description", ""),
                            effect_type=sdata.get("effect_type", ""),
                            effect_value=sdata.get("effect_value", 0),
                            unlock_condition=sdata.get("unlock_condition"),
                        )
            except Exception:
                pass

        if not self._data:
            default_data = LegacySkillData(
                id="soul_memory",
                min_reincarnation=1,
                name="魂の記憶",
                description="デフォルトレガシースキル",
                effect_type="skill_exp_boost",
                effect_value=0.15,
                unlock_condition={"reincarnation_count": 1},
            )
            self._data["soul_memory"] = default_data

    def all(self) -> dict[str, LegacySkillData]:
        """全レガシースキルデータを取得"""
        return self._data.copy()

    def get(self, skill_id: str) -> LegacySkillData | None:
        """特定のレガシースキルデータを取得"""
        return self._data.get(skill_id)


# グローバルレジストリインスタンス
REGISTRY = LegacySkillRegistry()


class LegacySkillManager:
    """レガシースキル管理クラス"""

    def __init__(self, registry: LegacySkillRegistry | None = None):
        self.registry = registry or REGISTRY

    def apply_legacy_effects(
        self, player: Any, effect_type: str = "skill_exp_boost", base_val: float = 100.0
    ) -> float:
        """レガシースキルの効果を適用"""
        bonus_mult = 0.0
        for skill_data in self.registry.all().values():
            if skill_data.effect_type == effect_type:
                reinc = getattr(player, "reincarnation_count", 0)
                if reinc >= skill_data.min_reincarnation:
                    bonus_mult += float(skill_data.effect_value)
        return round(base_val * (1.0 + bonus_mult), 4)

    def check_unlocks(self, player: Any) -> list[str]:
        """新規レガシースキルのアンロックをチェック"""
        newly_unlocked = []
        reinc = getattr(player, "reincarnation_count", 0)
        for skill_data in self.registry.all().values():
            if skill_data.id not in getattr(player, "legacy_skills", []):
                if reinc >= skill_data.min_reincarnation:
                    newly_unlocked.append(skill_data.id)
        return newly_unlocked
