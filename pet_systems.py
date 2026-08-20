"""Proposal 6-9 (Pet): equipment, training, guild, legacy/reincarnation.

Consolidated managers for the pet contract/evolution/fusion proposal.
"""

import logging
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def _load_yaml(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
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
