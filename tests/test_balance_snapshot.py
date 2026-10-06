"""Balance snapshots.

Numbers the redesign will move on purpose. Each one is pinned here so that a
change is a *deliberate diff* against this file rather than a surprise three
phases later. Step 22 updates the exp row when the curve is designed; every
other update must say in the commit why the number changed.
"""

from __future__ import annotations

import random
import statistics

import yaml

from ecs.entity import Entity
from map_engine import GameMap

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((REPO_ROOT / "config.yaml").read_text(encoding="utf-8"))
MONSTERS = yaml.safe_load((REPO_ROOT / "data" / "monsters.yaml").read_text(encoding="utf-8"))


def _player_entity() -> Entity:
    """Build the player exactly as core/world_state_manager.py:33-40 does.

    The `god_id = "jure"` line matters: calculate_max_hp grants +10 for it
    (ecs/entity.py:1157), so a player built without it is not the shipping one.
    """
    cfg = CONFIG["player"]
    entity = Entity(
        x=cfg["start_x"],
        y=cfg["start_y"],
        char=cfg["char"],
        color=tuple(cfg["color"]),
        name=cfg["name"],
        is_player=True,
        speed=cfg["speed"],
        attributes=cfg["attributes"],
    )
    entity.god_id = "jure"  # packages/character/package.py:11
    entity.recalculate_stats()
    return entity


def test_starting_max_hp_is_55():
    """endurance*2 + strength + level*5 + jure bonus = 13*2 + 14 + 5 + 10."""
    assert _player_entity().max_hp == 55


def test_starting_kit_is_seven_items():
    """packages/gameplay/package.py:8-33 returns 7 items."""
    from packages.gameplay.package import _create_starter_items

    class _Kernel:
        def get_system(self, name, default=None):
            return default

        def has_system(self, name):
            return False

    kit = _create_starter_items(_Kernel())
    assert len(kit) == 7


def test_monster_hp_span():
    """The deepest monster has 22x the HP of the shallowest — see Step 33."""
    hp = sorted(body["max_hp"] for body in MONSTERS.values())
    assert hp[0] == 10
    assert hp[-1] == 220


def test_exp_next_is_flat_100():
    """RECORDS A DEFECT, not an endorsement.

    `exp_next` is a hardcoded constant that is never scaled by level, which is
    why level 50 (the reincarnation gate) arrives at ~6.6 floors. Step 22
    replaces this test with the designed curve.
    """
    entity = _player_entity()
    assert entity.exp_next == 100
    assert entity.exp_next == _player_entity().exp_next


def test_monsters_per_floor_is_about_6_7():
    """0.6 spawn chance per room x ~11 rooms, measured over 60 generated floors."""
    rng = random.Random(20261004)
    random.seed(20261004)
    counts: list[int] = []
    for _ in range(60):
        game_map = GameMap(80, 50)
        game_map.generate_dungeon()
        # rooms[0] is the start room and never spawns monsters (package.py:58)
        counts.append(round(0.6 * max(0, len(game_map.rooms) - 1)))
    mean = statistics.mean(counts)
    assert 5.5 <= mean <= 8.0, f"monsters per floor drifted to {mean:.2f}"
