"""Proposal 6-9 (Pet): equipment, training, guild, legacy/reincarnation.

Consolidated managers for the pet contract/evolution/fusion proposal.
"""

from __future__ import annotations

import logging
from typing import Any

from constants import (
    PERSONALITY_AGGRESSIVE,
    PERSONALITY_BRAVE,
    PERSONALITY_CALM,
    PERSONALITY_COWARDLY,
    PERSONALITY_GLUTTONOUS,
)

logger = logging.getLogger(__name__)


def _load_yaml(path: str) -> dict:
    from data_validation import load_yaml_validated

    try:
        return load_yaml_validated(path)
    except FileNotFoundError:
        logger.warning(f"File not found: {path}")
        return {}
    except Exception as e:
        logger.error(f"Failed to load {path}: {e}")
        return {}


# ============================================================
# 提案6: Pet equipment / gear
# ============================================================


class PetEquipmentManager:
    def __init__(self, path: str = "data/pet_equipment.yaml"):
        self._items: dict[str, dict] = {}
        self.load(path)

    def load(self, path: str = "data/pet_equipment.yaml") -> None:
        data = _load_yaml(path)
        self._items.clear()
        for slot, items in data.get("pet_equipment", {}).items():
            for it in items:
                self._items[it["id"]] = {**it, "slot": slot}
        logger.info(f"Loaded {len(self._items)} pet equipment items")

    def get(self, item_id: str) -> dict | None:
        return self._items.get(item_id)

    def can_equip(self, pet, item_id: str) -> bool:
        it = self._items.get(item_id)
        if it is None:
            return False
        return getattr(pet, "bond", 0) >= it.get("required_bond", 0) and getattr(
            pet, "level", 1
        ) >= it.get("required_level", 1)

    def equip(self, pet, slot: str, item_id: str) -> bool:
        if not self.can_equip(pet, item_id):
            return False
        if not hasattr(pet, "equipment"):
            pet.equipment = {}
        pet.equipment[slot] = item_id
        return True

    def aggregate_bonuses(self, pet) -> dict[str, int]:
        out: dict[str, int] = {}
        for item_id in getattr(pet, "equipment", {}).values():
            it = self._items.get(item_id)
            if it is None:
                continue
            for eff in it.get("effects", []):
                if eff.get("type") == "stat_bonus":
                    for k, v in eff.get("value", {}).items():
                        out[k] = out.get(k, 0) + int(v)
        return out


# ============================================================
# 提案7: Pet training & loyalty
# ============================================================


class PetTrainingManager:
    def __init__(self, path: str = "data/pet_training.yaml"):
        self._courses: dict[str, dict] = {}
        self.load(path)

    def load(self, path: str = "data/pet_training.yaml") -> None:
        data = _load_yaml(path)
        self._courses.clear()
        for c in data.get("pet_training", {}).get("courses", []):
            self._courses[c["id"]] = c
        logger.info(f"Loaded {len(self._courses)} pet training courses")

    def can_enroll(self, pet, course_id: str, facilities: list[str]) -> bool:
        c = self._courses.get(course_id)
        if c is None:
            return False
        if getattr(pet, "bond", 0) < c.get("required_bond", 0):
            return False
        if getattr(pet, "level", 1) < c.get("required_level", 1):
            return False
        return all(f in facilities for f in c.get("facilities", []))

    def complete(self, pet, course_id: str) -> bool:
        c = self._courses.get(course_id)
        if c is None:
            return False
        if not hasattr(pet, "completed_pet_training"):
            pet.completed_pet_training = []
        if course_id not in pet.completed_pet_training:
            pet.completed_pet_training.append(course_id)
        return True


# ============================================================
# 提案8: Pet guild / fellowship
# ============================================================


class PetGuildManager:
    def __init__(self, path: str = "data/pet_guilds.yaml"):
        self._guilds: dict[str, dict] = {}
        self.load(path)

    def load(self, path: str = "data/pet_guilds.yaml") -> None:
        data = _load_yaml(path)
        self._guilds = data.get("pet_guilds", {})
        logger.info(f"Loaded {len(self._guilds)} pet guilds")

    def guild_level(self, guild_id: str, total_bond: int) -> int:
        g = self._guilds.get(guild_id)
        if not g:
            return 0
        reqs = g.get("guild_level_requirements", {})
        lvl = 1
        for l, needed in reqs.items():
            if total_bond >= int(needed):
                lvl = max(lvl, int(l))
        return lvl

    def active_buffs(self, guild_id: str, total_bond: int) -> list[dict]:
        g = self._guilds.get(guild_id)
        if not g:
            return []
        lvl = self.guild_level(guild_id, total_bond)
        buffs = []
        for buf in g.get("guild_buffers", []):
            if lvl >= int(buf.get("threshold", 0)):
                buffs.extend(buf.get("effects", []))
        return buffs


# ============================================================
# 提案9: Pet legacy / reincarnation
# ============================================================


class PetLegacyManager:
    def __init__(self, path: str = "data/pet_legacy.yaml"):
        self._transfers: list[dict] = []
        self._points_cfg: dict[str, Any] = {}
        self.load(path)

    def load(self, path: str = "data/pet_legacy.yaml") -> None:
        data = _load_yaml(path)
        self._transfers = data.get("pet_legacy", {}).get("legacy_transfer", [])
        self._points_cfg = data.get("pet_legacy", {}).get("legacy_points", {})
        logger.info(f"Loaded {len(self._transfers)} pet legacy transfers")

    def compute_legacy_points(
        self, level: int, max_bond: int, evolved_pets: int, legendary_pets: int
    ) -> int:
        cfg = self._points_cfg
        pts = int(cfg.get("base", 0))
        pts += (level // 10) * int(cfg.get("per_10_levels", 0))
        if max_bond >= 1000:
            pts += int(cfg.get("per_max_bond_1000", 0))
        pts += evolved_pets * int(cfg.get("per_evolved_pet", 0))
        pts += legendary_pets * int(cfg.get("per_legendary_pet", 0))
        return pts

    def available_transfers(self, flags: dict[str, bool]) -> list[dict]:
        out = []
        for t in self._transfers:
            if flags.get(t.get("condition"), False):
                out.append(t)
        return out

    def apply_transfer(self, pet, transfer: dict) -> bool:
        if not hasattr(pet, "pet_legacy_flags"):
            pet.pet_legacy_flags = {}
        pet.pet_legacy_flags[transfer["type"]] = True
        return True


# ============================================================
# Phase 3 (ECS Refactoring): Pet Bond System
# ============================================================


class PetBondSystem:
    """ペットの絆値操作と契約更新を担うECSシステムクラス (Steps 40-45)"""

    @classmethod
    def increase_bond(cls, pet_ai, amount: int, reason: str = "") -> int:
        from pet_contract_system import REGISTRY as CONTRACT_REG
        from pet_contract_system import PetContractManager

        try:
            CONTRACT_REG.load()
            mgr = PetContractManager(CONTRACT_REG)
            new_val = mgr.update_bond(pet_ai, amount)
            logger.debug(
                "Pet bond increased by %d (reason: %s), current: %d", amount, reason, new_val
            )
            return new_val
        except Exception as e:
            logger.warning("Failed to update bond via PetBondSystem: %s", e)
            pet_ai.bond = getattr(pet_ai, "bond", 0) + amount
            return pet_ai.bond


# ============================================================
# T30 案B: Pet growth curve (EXP / level / status / evolution hook)
# ============================================================


class PetGrowthSystem:
    """ペットの成長曲線・レベルアップ成長・進化条件検知を担うシステム (T30 案B)

    プレイヤー (balance_standards.yaml の指数曲線) と異なり、ペットは
    標準JRPG式の多項式曲線 level^2 + level*10 で成長要求が段階的に増える。
    レベルアップ時のステータス成長 (HP/攻撃/速度) は性格で差別化する。
    """

    # 性格別のレベルアップ成長量 {hp, attack(筋力), speed}
    _GROWTH_PROFILES: dict[str, dict[str, int]] = {
        PERSONALITY_BRAVE: {"hp": 6, "attack": 3, "speed": 1},
        PERSONALITY_AGGRESSIVE: {"hp": 4, "attack": 4, "speed": 1},
        PERSONALITY_CALM: {"hp": 5, "attack": 2, "speed": 2},
        PERSONALITY_COWARDLY: {"hp": 3, "attack": 1, "speed": 4},
        PERSONALITY_GLUTTONOUS: {"hp": 8, "attack": 1, "speed": 1},
    }
    _DEFAULT_GROWTH: dict[str, int] = {"hp": 5, "attack": 2, "speed": 1}

    @staticmethod
    def exp_required(level: int) -> int:
        """レベル level から level+1 へ到達するために必要な経験値 (標準JRPG式)"""
        level = max(1, int(level))
        return level * level + level * 10

    @classmethod
    def get_growth_profile(cls, pet: Any) -> dict[str, int]:
        """ペットの性格に応じたレベルアップ成長量を返す (未付与ならデフォルト)"""
        personality = getattr(pet, "personality", None)
        return dict(cls._GROWTH_PROFILES.get(personality, cls._DEFAULT_GROWTH))

    @classmethod
    def apply_level_growth(cls, pet: Any) -> list[str]:
        """レベル 1 上昇分のステータス成長 (HP/攻撃/速度) を性格差別化込みで適用する

        レベルアップ時は HP 全回復する (標準JRPG挙動)。筋力は _base_attributes
        側にも反映し、recalculate_stats() によるベース値復元で成長が消えないようにする。
        """
        growth = cls.get_growth_profile(pet)
        hp_gain = growth["hp"]
        atk_gain = growth["attack"]
        spd_gain = growth["speed"]

        pet.max_hp = int(getattr(pet, "max_hp", 10)) + hp_gain
        pet.hp = pet.max_hp

        attributes = getattr(pet, "attributes", None)
        if attributes is not None and hasattr(attributes, "strength"):
            attributes.strength += atk_gain
            base_attrs = getattr(pet, "_base_attributes", None)
            if base_attrs is not None and hasattr(base_attrs, "strength"):
                base_attrs.strength += atk_gain

        pet.speed = int(getattr(pet, "speed", 70)) + spd_gain

        return [
            f"{getattr(pet, 'name', 'ペット')}はレベル {int(getattr(pet, 'level', 1))} に上がった！ "
            f"(HP+{hp_gain} 攻撃+{atk_gain} 速度+{spd_gain}, 全回復)"
        ]

    @classmethod
    def gain_exp(cls, pet: Any, amount: int) -> list[str]:
        """ペットに経験値を与え、成長曲線に沿ってレベルアップさせる (T30 案B)

        Entity.gain_exp (is_pet ブランチ) から委譲される。戻り値はログメッセージ。
        """
        pet.exp = max(0, int(getattr(pet, "exp", 0)) + int(amount))

        logs: list[str] = []
        while pet.exp >= cls.exp_required(pet.level):
            pet.exp -= cls.exp_required(pet.level)
            pet.level = int(getattr(pet, "level", 1)) + 1
            logs.extend(cls.apply_level_growth(pet))
        return logs

    @classmethod
    def set_level_with_growth(cls, pet: Any, target_level: int) -> None:
        """現在レベルから target_level まで成長を適用しながら一括で到達させる (融合継承用)"""
        target = max(1, int(target_level))
        while int(getattr(pet, "level", 1)) < target:
            pet.level = int(getattr(pet, "level", 1)) + 1
            cls.apply_level_growth(pet)
        pet.exp = 0

    @classmethod
    def check_and_apply_evolution(cls, engine: Any) -> bool:
        """進化条件の達成を検知して進化を適用し、演出を発火する (T30 案B)

        条件判定 (requirements: level/bond) は既存 PetEvolutionManager の
        get_available_evolutions に委譲する。発火時は進化ログ + 浮遊テキスト +
        レベルアップ SE を出す。進化管理システムが不在な環境では何もしない。
        """
        pet = getattr(engine, "pet", None)
        if pet is None or getattr(pet, "hp", 0) <= 0:
            return False

        try:
            evo_mgr = engine.pet_evolution_manager
        except Exception:
            return False
        if evo_mgr is None:
            return False

        try:
            p_type = getattr(pet, "pet_type", "puppy")
            available = evo_mgr.get_available_evolutions(p_type, pet.pet_ai, pet)
        except Exception:
            logger.warning("ペット進化条件の判定に失敗", exc_info=True)
            return False
        if not available:
            return False

        target = available[0]
        try:
            ok = evo_mgr.apply_evolution(pet.pet_ai, target, pet)
        except Exception:
            logger.warning("ペット進化の適用に失敗", exc_info=True)
            return False
        if not ok:
            return False

        # 進化イベント演出: ログ + 浮遊テキスト + レベルアップ SE
        engine.log(
            f"★{getattr(pet, 'name', 'ペット')} は進化条件を満たし、【{target.name}】へ進化した！",
            (255, 215, 0),
        )
        fx_manager = getattr(engine, "fx_manager", None)
        floating_texts = getattr(engine, "floating_texts", None)
        if fx_manager is not None and floating_texts is not None and hasattr(
            fx_manager, "FloatingText"
        ):
            floating_texts.append(
                fx_manager.FloatingText("進化！", pet.x, pet.y - 0.3, (255, 215, 0))
            )
        try:
            from sound_manager import SoundManager

            SoundManager.play_se("level_up")
        except Exception:
            logger.debug("進化 SE の再生に失敗", exc_info=True)
        return True
