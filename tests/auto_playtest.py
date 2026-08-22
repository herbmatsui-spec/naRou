from __future__ import annotations

import argparse
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
import os
from pathlib import Path
import random
import sys
import time
from typing import Any

# Add project directories to sys.path
NAROU_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = NAROU_DIR.parent

for p in [str(NAROU_DIR), str(PROJECT_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.chdir(PROJECT_ROOT)

from naRou.constants import MAP_HEIGHT, MAP_WIDTH, TILE_STAIRS_DOWN
from naRou.core_framework import AStar, Point
from naRou.entity import Entity
from naRou.game import Engine
from naRou.item_system import Item


@dataclass
class TurnLog:
    turn: int
    timestamp: str
    player_hp: int
    player_max_hp: int
    player_mp: int
    player_max_mp: int
    player_level: int
    player_exp: int
    player_exp_next: int
    dungeon_level: int
    player_x: int
    player_y: int
    status_effects: list[str]
    gold: int
    food: int
    action: str
    action_result: str


@dataclass
class CombatLog:
    turn: int
    timestamp: str
    enemy_name: str
    enemy_type: str
    player_dmg_dealt: int
    player_dmg_taken: int
    enemy_hp_before: int
    enemy_hp_after: int
    player_hp_before: int
    player_hp_after: int
    turns_elapsed: int
    result: str
    is_critical: bool = False


@dataclass
class ItemLog:
    turn: int
    timestamp: str
    item_name: str
    item_type: str
    action: str
    quantity: int
    source: str


@dataclass
class SkillLog:
    turn: int
    timestamp: str
    skill_id: str
    skill_name: str
    exp_gained: int
    new_level: int
    job_id: str | None = None
    job_level: int = 0


@dataclass
class PetLog:
    turn: int
    timestamp: str
    pet_hp: int
    pet_max_hp: int
    bond: int
    action: str
    target: str | None = None


@dataclass
class DeathLog:
    timestamp: str
    cause: str
    turn: int
    dungeon_level: int
    player_level: int
    total_turns: int
    inventory: list[str]
    gold: int
    skills: list[str]
    last_damage_taken: int = 0


@dataclass
class PlaythroughLog:
    seed: int
    strategy: str
    status: str = "IN_PROGRESS"  # "CLEARED", "DIED", "STALLED", "TIMEOUT"
    start_time: str = ""
    end_time: str | None = None
    total_turns: int = 0
    max_dungeon_level: int = 1
    final_level: int = 1
    final_exp: int = 0
    final_gold: int = 0
    survived: bool = True
    cleared: bool = False
    death_log: DeathLog | None = None
    turn_logs: list[TurnLog] = field(default_factory=list)
    combat_logs: list[CombatLog] = field(default_factory=list)
    item_logs: list[ItemLog] = field(default_factory=list)
    skill_logs: list[SkillLog] = field(default_factory=list)
    pet_logs: list[PetLog] = field(default_factory=list)
    enemy_kill_counts: dict[str, int] = field(default_factory=dict)
    damage_by_enemy_type: dict[str, int] = field(default_factory=dict)
    damage_dealt_by_enemy: dict[str, int] = field(default_factory=dict)
    item_drop_stats: dict[str, int] = field(default_factory=dict)
    stairs_found_turn: int = 0
    steps_to_stairs: int = 0


@dataclass
class SummaryStats:
    total_runs: int = 0
    cleared_runs: int = 0
    survived_runs: int = 0
    death_runs: int = 0
    stalled_runs: int = 0
    timeout_runs: int = 0
    clear_rate: float = 0.0
    win_rate: float = 0.0
    avg_survival_turns: float = 0.0
    avg_dungeon_level: float = 0.0
    avg_final_level: float = 0.0
    one_shot_deaths: int = 0
    early_deaths: int = 0
    exp_shortage_runs: int = 0
    enemy_kill_totals: dict[str, int] = field(default_factory=dict)
    damage_taken_by_enemy: dict[str, int] = field(default_factory=dict)
    damage_dealt_to_enemy: dict[str, int] = field(default_factory=dict)
    item_drop_stats: dict[str, int] = field(default_factory=dict)
    balance_issues: list[str] = field(default_factory=list)


class LogCollector:
    def __init__(self, playthrough: PlaythroughLog, record_turn_details: bool = False):
        self.playthrough = playthrough
        self.record_turn_details = record_turn_details
        self.turn_counter = 0
        self.last_stairs_turn = 0
        self.steps_since_stairs = 0
        self.known_items_count: dict[str, int] = {}
        self.known_skills: dict[str, int] = {}

    def log_turn(self, engine: Engine, action: str, result: str):
        self.turn_counter += 1
        player = engine.player

        if self.record_turn_details:
            status_effects = [str(e) for e in getattr(player, "status_effects", [])]
            log = TurnLog(
                turn=self.turn_counter,
                timestamp=datetime.now().isoformat(),
                player_hp=player.hp,
                player_max_hp=player.max_hp,
                player_mp=player.mp,
                player_max_mp=player.max_mp,
                player_level=player.level,
                player_exp=player.exp,
                player_exp_next=getattr(player, "exp_next", 0),
                dungeon_level=engine.dungeon_level,
                player_x=player.x,
                player_y=player.y,
                status_effects=status_effects,
                gold=getattr(engine.survival, "gold", 0),
                food=getattr(engine.survival, "hunger", 0),
                action=action,
                action_result=result,
            )
            self.playthrough.turn_logs.append(log)

    def log_combat(
        self,
        enemy_name: str,
        enemy_type: str,
        player_dmg: int,
        enemy_dmg: int,
        enemy_hp_before: int,
        enemy_hp_after: int,
        player_hp_before: int,
        player_hp_after: int,
        result: str,
        is_critical: bool = False,
    ):
        log = CombatLog(
            turn=self.turn_counter,
            timestamp=datetime.now().isoformat(),
            enemy_name=enemy_name,
            enemy_type=enemy_type,
            player_dmg_dealt=player_dmg,
            player_dmg_taken=enemy_dmg,
            enemy_hp_before=enemy_hp_before,
            enemy_hp_after=enemy_hp_after,
            player_hp_before=player_hp_before,
            player_hp_after=player_hp_after,
            turns_elapsed=1,
            result=result,
            is_critical=is_critical,
        )
        self.playthrough.combat_logs.append(log)

        enemy_key = enemy_name.lower().replace(" ", "_")
        if result == "win":
            self.playthrough.enemy_kill_counts[enemy_key] = (
                self.playthrough.enemy_kill_counts.get(enemy_key, 0) + 1
            )
        if player_dmg > 0:
            self.playthrough.damage_dealt_by_enemy[enemy_key] = (
                self.playthrough.damage_dealt_by_enemy.get(enemy_key, 0) + player_dmg
            )
        if enemy_dmg > 0:
            self.playthrough.damage_by_enemy_type[enemy_key] = (
                self.playthrough.damage_by_enemy_type.get(enemy_key, 0) + enemy_dmg
            )

    def log_item(self, item: Item | str, action: str, source: str, quantity: int = 1):
        item_name = item.name if isinstance(item, Item) else str(item)
        item_type = getattr(item, "item_type", "item") if isinstance(item, Item) else "item"

        log = ItemLog(
            turn=self.turn_counter,
            timestamp=datetime.now().isoformat(),
            item_name=item_name,
            item_type=item_type,
            action=action,
            quantity=quantity,
            source=source,
        )
        self.playthrough.item_logs.append(log)

        if action in ("pickup", "drop", "obtain"):
            self.playthrough.item_drop_stats[item_name] = (
                self.playthrough.item_drop_stats.get(item_name, 0) + quantity
            )

    def log_skill(
        self,
        skill_id: str,
        skill_name: str,
        exp_gained: int,
        new_level: int,
        job_id: str | None = None,
        job_level: int = 0,
    ):
        log = SkillLog(
            turn=self.turn_counter,
            timestamp=datetime.now().isoformat(),
            skill_id=skill_id,
            skill_name=skill_name,
            exp_gained=exp_gained,
            new_level=new_level,
            job_id=job_id,
            job_level=job_level,
        )
        self.playthrough.skill_logs.append(log)

    def log_pet(self, engine: Engine, action: str, target: str | None = None):
        pet = getattr(engine, "pet", None)
        bond = getattr(pet, "bond", 0) if pet else 0
        log = PetLog(
            turn=self.turn_counter,
            timestamp=datetime.now().isoformat(),
            pet_hp=getattr(pet, "hp", 0) if pet else 0,
            pet_max_hp=getattr(pet, "max_hp", 0) if pet else 0,
            bond=bond,
            action=action,
            target=target,
        )
        self.playthrough.pet_logs.append(log)

    def log_death(self, engine: Engine, cause: str, last_damage: int = 0):
        player = engine.player
        inventory_names = [item.name for item in engine.inventory.items]
        skills_dict = getattr(player, "skills", {})
        skill_names = list(skills_dict.keys()) if isinstance(skills_dict, dict) else []
        log = DeathLog(
            timestamp=datetime.now().isoformat(),
            cause=cause,
            turn=self.turn_counter,
            dungeon_level=engine.dungeon_level,
            player_level=player.level,
            total_turns=self.turn_counter,
            inventory=inventory_names,
            gold=getattr(engine.survival, "gold", 0),
            skills=skill_names,
            last_damage_taken=last_damage,
        )
        self.playthrough.death_log = log
        self.playthrough.survived = False
        self.playthrough.status = "DIED" if cause != "stalled" else "STALLED"

    def check_stairs(self, engine: Engine):
        if (
            engine.player.x < len(engine.game_map.tiles)
            and engine.player.y < len(engine.game_map.tiles[0])
            and engine.game_map.tiles[engine.player.x][engine.player.y] == TILE_STAIRS_DOWN
        ):
            if self.playthrough.stairs_found_turn == 0:
                self.playthrough.stairs_found_turn = self.turn_counter
            self.playthrough.steps_to_stairs = self.turn_counter - self.last_stairs_turn
            self.last_stairs_turn = self.turn_counter

    def capture_turn_delta(
        self,
        engine: Engine,
        prev_player_hp: int,
        prev_player_max_hp: int,
        prev_target: Entity | None = None,
        target_hp_before: int = 0,
    ):
        player = engine.player
        curr_hp = player.hp
        damage_taken = max(0, prev_player_hp - curr_hp)

        # 敵への攻撃・被ダメージの記録
        if prev_target is not None:
            curr_target_hp = max(0, prev_target.hp)
            dmg_dealt = max(0, target_hp_before - curr_target_hp)
            res = "win" if curr_target_hp <= 0 else "ongoing"
            self.log_combat(
                enemy_name=prev_target.name,
                enemy_type=getattr(prev_target, "char", "enemy"),
                player_dmg=dmg_dealt,
                enemy_dmg=damage_taken,
                enemy_hp_before=target_hp_before,
                enemy_hp_after=curr_target_hp,
                player_hp_before=prev_player_hp,
                player_hp_after=curr_hp,
                result=res,
            )
        elif damage_taken > 0:
            # 近隣の敵からダメージを受けたと推定
            enemies = [
                e
                for e in engine.entity_manager.get_living_entities()
                if e not in (player, getattr(engine, "pet", None))
            ]
            nearest_enemy = None
            min_dist = 999
            for e in enemies:
                d = max(abs(e.x - player.x), abs(e.y - player.y))
                if d < min_dist:
                    min_dist = d
                    nearest_enemy = e

            enemy_name = nearest_enemy.name if (nearest_enemy and min_dist <= 2) else "environmental/trap"
            enemy_type = getattr(nearest_enemy, "char", "?") if nearest_enemy else "trap"
            self.log_combat(
                enemy_name=enemy_name,
                enemy_type=enemy_type,
                player_dmg=0,
                enemy_dmg=damage_taken,
                enemy_hp_before=getattr(nearest_enemy, "hp", 0) if nearest_enemy else 0,
                enemy_hp_after=getattr(nearest_enemy, "hp", 0) if nearest_enemy else 0,
                player_hp_before=prev_player_hp,
                player_hp_after=curr_hp,
                result="ongoing",
            )

        # 死亡チェック
        if curr_hp <= 0 and self.playthrough.death_log is None:
            self.log_death(engine, "hp_depleted", last_damage=damage_taken)


class AutoPlayer:
    STRATEGIES = {
        "melee": {"focus": "melee", "spell_chance": 0.05, "explore_chance": 0.7},
        "mage": {"focus": "magic", "spell_chance": 0.7, "explore_chance": 0.5},
        "hybrid": {"focus": "balanced", "spell_chance": 0.3, "explore_chance": 0.6},
        "tank": {"focus": "defense", "spell_chance": 0.05, "explore_chance": 0.5},
        "speed": {"focus": "evasion", "spell_chance": 0.2, "explore_chance": 0.8},
    }

    def __init__(
        self,
        engine: Engine,
        strategy: str = "hybrid",
        seed: int | None = None,
        record_turn_details: bool = False,
    ):
        self.engine = engine
        self.strategy_name = strategy
        self.strategy = self.STRATEGIES.get(strategy, self.STRATEGIES["hybrid"])
        self.rng = random.Random(seed)
        self.turn_count = 0
        self.max_turns = 10000
        self.max_dungeon_level = 50
        self.consecutive_waits = 0
        self.pos_history: deque[tuple[int, int]] = deque(maxlen=30)
        self.stalled_counter = 0

        self.playthrough_log = PlaythroughLog(
            seed=seed or int(time.time() * 1000) % 1000000,
            strategy=strategy,
            start_time=datetime.now().isoformat(),
        )
        self.collector = LogCollector(self.playthrough_log, record_turn_details=record_turn_details)

    def get_valid_moves(self) -> list[tuple[int, int]]:
        moves = []
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
            nx, ny = self.engine.player.x + dx, self.engine.player.y + dy
            if self.engine.game_map.is_walkable(nx, ny):
                moves.append((dx, dy))
        return moves

    def get_enemies_in_range(self, range_: int = 1) -> list[Entity]:
        enemies = []
        for ent in self.engine.entity_manager.get_living_entities():
            if ent in (self.engine.player, getattr(self.engine, "pet", None)):
                continue
            if getattr(ent, "faction", "") == "player":
                continue
            dist = max(abs(ent.x - self.engine.player.x), abs(ent.y - self.engine.player.y))
            if dist <= range_:
                enemies.append(ent)
        return enemies

    def get_nearest_enemy(self, max_range: int = 8) -> Entity | None:
        nearest = None
        min_dist = max_range + 1
        for ent in self.engine.entity_manager.get_living_entities():
            if ent in (self.engine.player, getattr(self.engine, "pet", None)):
                continue
            if getattr(ent, "faction", "") == "player":
                continue
            dist = max(abs(ent.x - self.engine.player.x), abs(ent.y - self.engine.player.y))
            if dist < min_dist and self.engine.has_los(
                Point(self.engine.player.x, self.engine.player.y), Point(ent.x, ent.y)
            ):
                min_dist = dist
                nearest = ent
        return nearest

    def find_path_to(self, target_x: int, target_y: int) -> list[tuple[int, int]] | None:
        blocked = self.engine.get_blocked_positions()
        distance = max(abs(target_x - self.engine.player.x), abs(target_y - self.engine.player.y))
        max_depth = max(40, distance + 10)
        path = AStar.get_path(
            Point(self.engine.player.x, self.engine.player.y),
            Point(target_x, target_y),
            lambda x, y: self.engine.is_tile_free(x, y, blocked),
            max_depth=max_depth,
        )
        if path and len(path) > 1:
            return [(path[1].x - self.engine.player.x, path[1].y - self.engine.player.y)]
        return None

    def find_stairs(self) -> tuple[int, int] | None:
        """探索済み（発見済み）の階段座標を返す（チート防止）"""
        stairs_pos = getattr(self.engine.game_map, "stairs_down_pos", None)
        if stairs_pos:
            sx, sy = stairs_pos
            if (
                sx < len(self.engine.game_map.explored)
                and sy < len(self.engine.game_map.explored[0])
                and self.engine.game_map.explored[sx][sy]
            ):
                return stairs_pos
        return None

    def find_unexplored(self) -> tuple[int, int] | None:
        """探索済み領域に隣接する未探索の歩行可能タイルを探す"""
        player_pos = Point(self.engine.player.x, self.engine.player.y)
        best = None
        best_dist = 999

        tiles = self.engine.game_map.tiles
        explored = self.engine.game_map.explored

        # 走査範囲を安全に取得
        max_x = min(MAP_WIDTH, len(tiles), len(explored))
        max_y = min(MAP_HEIGHT, len(tiles[0]), len(explored[0]))

        for x in range(1, max_x - 1):
            for y in range(1, max_y - 1):
                if explored[x][y] and self.engine.game_map.is_walkable(x, y):
                    # 隣接マスに未探索があるか
                    has_unexplored_neighbor = any(
                        not explored[x + dx][y + dy]
                        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]
                        if 0 <= x + dx < max_x and 0 <= y + dy < max_y
                    )
                    if has_unexplored_neighbor:
                        dist = player_pos.chebyshev_distance(Point(x, y))
                        if dist < best_dist:
                            best_dist = dist
                            best = (x, y)
                            if dist <= 2:
                                return best
        return best

    def decide_action(self) -> tuple[str, tuple[int, int] | None, Entity | None]:
        player = self.engine.player
        valid_moves = self.get_valid_moves()
        enemies_adjacent = self.get_enemies_in_range(1)
        enemies_near = self.get_enemies_in_range(5)

        on_stairs = (
            player.x < len(self.engine.game_map.tiles)
            and player.y < len(self.engine.game_map.tiles[0])
            and self.engine.game_map.tiles[player.x][player.y] == TILE_STAIRS_DOWN
        )

        hp_ratio = player.hp / player.max_hp if player.max_hp > 0 else 0

        # 階段上にいる場合
        if on_stairs:
            if self.engine.dungeon_level >= self.max_dungeon_level:
                return "wait", None, None
            return "descend", None, None

        # 緊急時（HP 30%未満）
        if hp_ratio < 0.3:
            if getattr(player, "piety", 0) >= 20 and self.rng.random() < 0.6:
                return "pray", None, None
            # 敵から離れる安全な移動
            for dx, dy in valid_moves:
                nx, ny = player.x + dx, player.y + dy
                safe = all(
                    max(abs(ent.x - nx), abs(ent.y - ny)) >= 2 for ent in enemies_near
                )
                if safe and not self.engine.get_entity_at(nx, ny):
                    return "move", (dx, dy), None

        # 隣接敵がいる場合（近接攻撃または緊急祈り）
        if enemies_adjacent:
            target = enemies_adjacent[0]
            dx = target.x - player.x
            dy = target.y - player.y

            if (
                self.strategy["focus"] == "magic"
                and player.mp >= 10
                and self.rng.random() < self.strategy["spell_chance"]
            ):
                return "cast_fireball", None, target

            return "attack", (dx, dy), target

        # 遠距離敵への魔法詠唱
        if enemies_near and self.strategy["focus"] == "magic" and player.mp >= 10:
            if self.rng.random() < self.strategy["spell_chance"]:
                return "cast_fireball", None, enemies_near[0]

        # 視界内の敵へ接近
        nearest = self.get_nearest_enemy(8)
        if nearest and self.rng.random() < self.strategy["explore_chance"]:
            path = self.find_path_to(nearest.x, nearest.y)
            if path:
                return "move", path[0], None

        # 発見済み階段への移動
        stairs_pos = self.find_stairs()
        if stairs_pos:
            path = self.find_path_to(stairs_pos[0], stairs_pos[1])
            if path:
                return "move", path[0], None

        # 未探索エリアへの移動
        unexplored = self.find_unexplored()
        if unexplored:
            path = self.find_path_to(unexplored[0], unexplored[1])
            if path:
                return "move", path[0], None

        # 有効な移動
        if valid_moves:
            open_moves = [
                (dx, dy)
                for dx, dy in valid_moves
                if not self.engine.get_entity_at(player.x + dx, player.y + dy)
            ]
            if open_moves:
                return "move", self.rng.choice(open_moves), None
            return "move", self.rng.choice(valid_moves), None

        return "wait", None, None

    def execute_action(
        self, action: str, params: tuple[int, int] | None, target: Entity | None
    ) -> str:
        player = self.engine.player
        result = "ok"

        prev_hp = player.hp
        prev_max_hp = player.max_hp
        target_hp_before = target.hp if target else 0

        try:
            if action in ("move", "attack") and params:
                dx, dy = params
                if self.engine.player_act(dx, dy):
                    self.engine.advance_world()
                    result = "acted"
                else:
                    result = "blocked"
                self.collector.check_stairs(self.engine)

            elif action == "cast_fireball":
                if player.mp >= 10:
                    self.engine.cast_fireball()
                    result = "cast"
                else:
                    result = "no_mp"
                    self.engine.advance_world()

            elif action == "pray":
                self.engine.pray()
                self.engine.advance_world()
                result = "prayed"

            elif action == "descend":
                self.engine.descend_stairs()
                result = "descended"

            elif action == "wait":
                self.engine.log("待機した。", (200, 200, 200))
                self.engine.advance_world()
                result = "waited"
                self.consecutive_waits += 1

            else:
                self.engine.advance_world()
                result = "unknown"

        except Exception as e:
            result = f"error: {e}"

        # ターン後の差分（被ダメージ、戦闘ログ）をキャプチャ
        self.collector.capture_turn_delta(
            self.engine,
            prev_player_hp=prev_hp,
            prev_player_max_hp=prev_max_hp,
            prev_target=target,
            target_hp_before=target_hp_before,
        )

        return result

    def check_death(self) -> bool:
        if self.engine.player.hp <= 0:
            if self.playthrough_log.death_log is None:
                self.collector.log_death(self.engine, "hp_depleted")
            return True
        return False

    def update_and_check_stalled(self) -> bool:
        pos = (self.engine.player.x, self.engine.player.y)
        self.pos_history.append(pos)

        if len(self.pos_history) >= 20:
            unique_positions = len(set(self.pos_history))
            if unique_positions <= 2:
                self.stalled_counter += 1
                if self.stalled_counter >= 30:
                    return True
            else:
                self.stalled_counter = 0
        return False

    def run(self, max_turns: int = 5000, max_dungeon_level: int = 20) -> PlaythroughLog:
        self.max_turns = max_turns
        self.max_dungeon_level = max_dungeon_level

        while self.turn_count < self.max_turns and self.engine.dungeon_level < self.max_dungeon_level:
            self.turn_count += 1

            if self.check_death():
                break

            if self.update_and_check_stalled():
                self.collector.log_death(self.engine, "stalled")
                break

            action, params, target = self.decide_action()
            result = self.execute_action(action, params, target)

            self.collector.log_turn(self.engine, action, result)

            self.playthrough_log.max_dungeon_level = max(
                self.playthrough_log.max_dungeon_level, self.engine.dungeon_level
            )

        self.playthrough_log.end_time = datetime.now().isoformat()
        self.playthrough_log.total_turns = self.turn_count
        self.playthrough_log.final_level = self.engine.player.level
        self.playthrough_log.final_exp = self.engine.player.exp
        self.playthrough_log.final_gold = getattr(self.engine.survival, "gold", 0)

        # 最終状態の確定
        if self.engine.dungeon_level >= self.max_dungeon_level:
            self.playthrough_log.status = "CLEARED"
            self.playthrough_log.survived = True
            self.playthrough_log.cleared = True
        elif self.engine.player.hp <= 0:
            self.playthrough_log.status = "DIED"
            self.playthrough_log.survived = False
            self.playthrough_log.cleared = False
        elif self.playthrough_log.status == "STALLED":
            self.playthrough_log.survived = False
            self.playthrough_log.cleared = False
        else:
            self.playthrough_log.status = "TIMEOUT"
            self.playthrough_log.survived = True
            self.playthrough_log.cleared = False

        return self.playthrough_log


class PlayTestRunner:
    def __init__(
        self,
        num_runs: int = 10,
        max_turns: int = 5000,
        max_dungeon_level: int = 20,
        strategies: list[str] | None = None,
        output_dir: str = "playtest_logs",
        save_turn_logs: bool = False,
    ):
        self.num_runs = num_runs
        self.max_turns = max_turns
        self.max_dungeon_level = max_dungeon_level
        self.strategies = strategies or ["melee", "mage", "hybrid", "tank", "speed"]
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.save_turn_logs = save_turn_logs
        self.all_logs: list[PlaythroughLog] = []

    def run_single(self, strategy: str, seed: int | None = None) -> PlaythroughLog:
        print(f"  Running {strategy} (seed: {seed or 'random'})...")
        engine = Engine()
        player = AutoPlayer(
            engine,
            strategy,
            seed,
            record_turn_details=self.save_turn_logs,
        )
        log = player.run(self.max_turns, self.max_dungeon_level)
        return log

    def run_all(self) -> list[PlaythroughLog]:
        print(f"Starting {self.num_runs} playthroughs...")
        print(f"Strategies: {self.strategies}")
        print(f"Max turns: {self.max_turns}, Max dungeon level: {self.max_dungeon_level}")

        for i in range(self.num_runs):
            strategy = self.strategies[i % len(self.strategies)]
            seed = int(time.time() * 1000) % 1000000 + i
            try:
                log = self.run_single(strategy, seed)
                self.all_logs.append(log)
                print(
                    f"  Run {i+1}/{self.num_runs}: [{log.status}] - "
                    f"Turns: {log.total_turns}, Depth: {log.max_dungeon_level}, Level: {log.final_level}, Gold: {log.final_gold}"
                )
            except Exception as e:
                print(f"  Run {i+1}/{self.num_runs}: ERROR - {e}")
                import traceback
                traceback.print_exc()

        return self.all_logs

    def save_logs(self, timestamp: str | None = None) -> tuple[str, str]:
        ts = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")

        log_file = self.output_dir / f"playtest_{ts}.json"
        summary_file = self.output_dir / f"summary_{ts}.json"

        serializable_logs = []
        for log in self.all_logs:
            d = asdict(log)
            if not self.save_turn_logs:
                d.pop("turn_logs", None)
            serializable_logs.append(d)

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(serializable_logs, f, ensure_ascii=False, indent=2)

        summary = self.generate_summary()
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(asdict(summary), f, ensure_ascii=False, indent=2)

        print(f"\nLogs saved to: {log_file}")
        print(f"Summary saved to: {summary_file}")
        return str(log_file), str(summary_file)

    def generate_summary(self) -> SummaryStats:
        if not self.all_logs:
            return SummaryStats()

        stats = SummaryStats()
        stats.total_runs = len(self.all_logs)

        survival_turns = []
        dungeon_levels = []
        final_levels = []
        total_kills: dict[str, int] = {}
        total_damage_taken: dict[str, int] = {}
        total_damage_dealt: dict[str, int] = {}
        item_drops: dict[str, int] = {}

        for log in self.all_logs:
            if log.status == "CLEARED":
                stats.cleared_runs += 1
                stats.survived_runs += 1
            elif log.status == "TIMEOUT":
                stats.timeout_runs += 1
                stats.survived_runs += 1
            elif log.status == "STALLED":
                stats.stalled_runs += 1
                stats.death_runs += 1
            elif log.status == "DIED":
                stats.death_runs += 1
                if log.death_log:
                    if log.death_log.turn < 10:
                        stats.early_deaths += 1
                    if log.death_log.last_damage_taken >= 30:
                        stats.one_shot_deaths += 1

            survival_turns.append(log.total_turns)
            dungeon_levels.append(log.max_dungeon_level)
            final_levels.append(log.final_level)

            for enemy, count in log.enemy_kill_counts.items():
                total_kills[enemy] = total_kills.get(enemy, 0) + count

            for enemy, dmg in log.damage_by_enemy_type.items():
                total_damage_taken[enemy] = total_damage_taken.get(enemy, 0) + dmg

            for enemy, dmg in log.damage_dealt_by_enemy.items():
                total_damage_dealt[enemy] = total_damage_dealt.get(enemy, 0) + dmg

            for item, count in log.item_drop_stats.items():
                item_drops[item] = item_drops.get(item, 0) + count

            if log.final_level < 3 and log.total_turns > 1000:
                stats.exp_shortage_runs += 1

        stats.avg_survival_turns = sum(survival_turns) / len(survival_turns)
        stats.avg_dungeon_level = sum(dungeon_levels) / len(dungeon_levels)
        stats.avg_final_level = sum(final_levels) / len(final_levels)
        stats.clear_rate = stats.cleared_runs / stats.total_runs if stats.total_runs > 0 else 0.0
        stats.win_rate = stats.survived_runs / stats.total_runs if stats.total_runs > 0 else 0.0
        stats.enemy_kill_totals = total_kills
        stats.damage_taken_by_enemy = total_damage_taken
        stats.damage_dealt_to_enemy = total_damage_dealt
        stats.item_drop_stats = item_drops

        if stats.early_deaths > stats.total_runs * 0.2:
            stats.balance_issues.append(
                f"High early death rate (<10 turns): {stats.early_deaths}/{stats.total_runs}"
            )

        if stats.one_shot_deaths > stats.total_runs * 0.15:
            stats.balance_issues.append(
                f"High burst/one-shot deaths: {stats.one_shot_deaths}/{stats.total_runs}"
            )

        if stats.stalled_runs > stats.total_runs * 0.1:
            stats.balance_issues.append(
                f"Stalled runs detected: {stats.stalled_runs}/{stats.total_runs}"
            )

        if stats.exp_shortage_runs > stats.total_runs * 0.3:
            stats.balance_issues.append(
                f"Experience shortage in {stats.exp_shortage_runs}/{stats.total_runs} runs"
            )

        avg_dmg_per_enemy = {k: v / stats.total_runs for k, v in total_damage_taken.items()}
        for enemy, avg_dmg in avg_dmg_per_enemy.items():
            if avg_dmg > 50:
                stats.balance_issues.append(f"High avg damage from {enemy}: {avg_dmg:.1f}")

        return stats

    def print_summary(self, summary: SummaryStats):
        print("\n" + "=" * 60)
        print("PLAYTEST SUMMARY")
        print("=" * 60)
        print(f"Total runs:          {summary.total_runs}")
        print(f"Cleared (Goal):      {summary.cleared_runs} ({summary.clear_rate*100:.1f}%)")
        print(f"Survived (All):      {summary.survived_runs} ({summary.win_rate*100:.1f}%)")
        print(f"Died:                {summary.death_runs}")
        print(f"  - Early deaths:    {summary.early_deaths}")
        print(f"  - High burst deaths: {summary.one_shot_deaths}")
        print(f"Stalled runs:        {summary.stalled_runs}")
        print(f"Timeout runs:        {summary.timeout_runs}")
        print(f"Exp shortage runs:   {summary.exp_shortage_runs}")
        print(f"Avg survival turns:  {summary.avg_survival_turns:.1f}")
        print(f"Avg dungeon level:   {summary.avg_dungeon_level:.1f}")
        print(f"Avg final level:     {summary.avg_final_level:.1f}")

        print("\nTop Enemy Kills:")
        for enemy, count in sorted(summary.enemy_kill_totals.items(), key=lambda x: -x[1])[:10]:
            print(f"  {enemy}: {count}")

        print("\nTop Damage Taken by Enemy/Source:")
        for enemy, dmg in sorted(summary.damage_taken_by_enemy.items(), key=lambda x: -x[1])[:10]:
            print(f"  {enemy}: {dmg}")

        print("\nTop Damage Dealt to Enemy:")
        for enemy, dmg in sorted(summary.damage_dealt_to_enemy.items(), key=lambda x: -x[1])[:10]:
            print(f"  {enemy}: {dmg}")

        if summary.item_drop_stats:
            print("\nItem Drops/Obtains:")
            for item, count in sorted(summary.item_drop_stats.items(), key=lambda x: -x[1])[:10]:
                print(f"  {item}: {count}")

        if summary.balance_issues:
            print("\n[!] BALANCE ISSUES DETECTED:")
            for issue in summary.balance_issues:
                print(f"  - {issue}")
        else:
            print("\n[OK] No major balance issues detected")


def main():
    parser = argparse.ArgumentParser(description="naRou: Masterpiece Edition Auto Playtest")
    parser.add_argument("-n", "--runs", type=int, default=10, help="Number of playthroughs")
    parser.add_argument("-t", "--max-turns", type=int, default=5000, help="Max turns per run")
    parser.add_argument("-d", "--max-depth", type=int, default=20, help="Max dungeon level")
    parser.add_argument("-s", "--strategies", nargs="+", default=None, help="Strategies to test")
    parser.add_argument("-o", "--output", default="playtest_logs", help="Output directory")
    parser.add_argument(
        "--save-turn-logs",
        action="store_true",
        help="Record and save detailed turn-by-turn logs to JSON",
    )
    args = parser.parse_args()

    runner = PlayTestRunner(
        num_runs=args.runs,
        max_turns=args.max_turns,
        max_dungeon_level=args.max_depth,
        strategies=args.strategies,
        output_dir=args.output,
        save_turn_logs=args.save_turn_logs,
    )

    runner.run_all()
    summary = runner.generate_summary()
    runner.print_summary(summary)
    runner.save_logs()


if __name__ == "__main__":
    main()