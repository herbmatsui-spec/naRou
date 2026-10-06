"""バランス計測器。

実ゲームと同じ戦闘ループ (``player_act`` / ``advance_world``) を回して測る。
判定基準は ``data/balance_standards.yaml`` に置き、コードには閾値を埋めない。
"""

from __future__ import annotations

import copy
import json
import math
import os
import random
import sys
from collections import deque
from typing import Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ecs.entity import Attributes

# 実ゲームのレベルアップ規則 (ecs/entity.py gain_exp) が触る能力値。
ATTRIBUTE_KEYS = (
    "strength",
    "endurance",
    "dexterity",
    "perception",
    "learning",
    "will",
    "magic",
    "charisma",
)

# 生成済みエンジンと計測用の戦闘タイル。Engine() の生成は 2 秒程度かかり、
# 試行ごとに生成すると計測時間が桁で増えるためプロセス内で 1 つだけ共有する。
_WORLD: dict[str, Any] = {}

# 計測用の世界 (ダンジョン生成) を固定するシード。レポートの再生成が同じ数値になるようにする。
WORLD_SEED = 20261004

# 経済計測 (1 フロアの獲得ゴールド) の乱数。階と GOLD を初期状態へ戻しても、
# 戦闘ロールの順番で値が微妙に揺れると「同じ計測なのに数値が違う」ことになるので固定する。
ECONOMY_SEED = WORLD_SEED + 1


def acquire_world() -> tuple[Any, tuple[int, int]]:
    """実エンジンと計測用の戦闘タイルを返す (初回の呼び出しで生成)。"""
    if "engine" not in _WORLD:
        from game import Engine

        # ダンジョンは乱数生成なので、生成時の乱数を固定してレポートを再現可能にする。
        # 呼び出し元の乱数状態は復元するので、戦闘ロールは呼び出し側の seed のまま。
        caller_state = random.getstate()
        random.seed(WORLD_SEED)
        try:
            engine = Engine()
        finally:
            random.setstate(caller_state)

        altar = getattr(engine, "altar_pos", None)
        altar = tuple(altar) if altar else None
        # 祭壇タイルは player_act が ``GodInfo`` を import できず例外を投げる
        # (packages/gameplay/package.py) ため、計測は祭壇から離れたタイルで行う。
        arena, best_distance = None, -1
        for x in range(engine.game_map.width):
            for y in range(engine.game_map.height):
                if not engine.game_map.is_walkable(x, y):
                    continue
                distance = 10**6 if altar is None else max(abs(x - altar[0]), abs(y - altar[1]))
                if distance > best_distance:
                    arena, best_distance = (x, y), distance
        _WORLD["engine"] = engine
        _WORLD["arena"] = arena
        _WORLD["altar"] = altar
        _WORLD["base_attributes"] = {
            name: getattr(engine.player.attributes, name) for name in ATTRIBUTE_KEYS
        }
        # 経済計測 (1 フロアの獲得ゴールド) は実ダンジョン1階を実際にクリアして測る。
        # 戦闘試行はエンティティを潰し、EXP も積むので、階と仲間の状態をここで撮っておき
        # 毎回復元する。復元しないと 2 回目以降の計測は前の計測の結果によって値が変わる。
        _WORLD["floor_start"] = tuple(engine.game_map.start_pos)
        _WORLD["floor_monsters"] = [
            copy.deepcopy(e) for e in engine.entity_manager.get_living_entities() if _is_hostile(e)
        ]
        _WORLD["floor_items"] = list(engine.entity_manager.items_on_ground)
        _WORLD["floor_quests"] = copy.deepcopy(engine.quests)
        _WORLD["floor_player"] = copy.deepcopy(engine.player)
        _WORLD["floor_pet"] = copy.deepcopy(engine.pet)
    return _WORLD["engine"], _WORLD["arena"]


def _is_hostile(entity: Any) -> bool:
    """その階でプレイヤーが倒すべき身 (モンスター faction) かどうか。"""
    return getattr(entity, "faction", "") == "monster"


class BattleScenario:
    """自動戦闘シナリオ定義クラス (Step 36, 37)"""

    def __init__(
        self,
        name: str,
        player_level: int,
        monster_type: str,
        trials: int = 100,
        expected_win_rate: float = 0.5,
    ):
        self.name = name
        self.player_level = player_level
        self.monster_type = monster_type
        self.trials = trials
        self.expected_win_rate = expected_win_rate

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BattleScenario:
        return cls(
            name=data.get("name", "Scenario"),
            player_level=data.get("player_level", 1),
            monster_type=data.get("monster_type", "slime"),
            trials=data.get("trials", 100),
            expected_win_rate=data.get("expected_win_rate", 0.5),
        )


class BalanceChecker:
    """YAML基準値に基づくバランス整合性検証クラス (Step 44-47)"""

    def __init__(self, standards_path: str = "data/balance_standards.yaml"):
        import yaml

        self.standards_path = standards_path
        self.standards = {}
        if os.path.exists(standards_path):
            with open(standards_path, encoding="utf-8") as f:
                self.standards = yaml.safe_load(f) or {}

    @property
    def judgement(self) -> dict[str, Any]:
        """判定基準 (勝率の許容範囲・ダメージ比下限など)。"""
        return self.standards.get("judgement") or {}

    @property
    def max_turns(self) -> int:
        """膠着とみなすターン上限。"""
        return int((self.standards.get("simulation") or {}).get("max_turns", 100))

    @property
    def economy_floor_run(self) -> dict[str, Any]:
        """経済計測の実行条件 (どのレベルのプレイヤーを何ターンまで回すか)。"""
        return (self.standards.get("simulation") or {}).get("economy_floor_run") or {}

    def check_standards(self, observations: dict[str, Any] | None = None) -> dict[str, Any]:
        """実測値を ``data/balance_standards.yaml`` の基準値と照合する。

        ``observations`` は ``{"levels": {レベル: {"hp": ..., "attack": ...}},"economy": {"gold_per_dungeon_floor": ...}}``
        の形。実測値が無い項目は「確認できていない」ので PASS にはしない。
        """
        issues: list[dict[str, Any]] = []
        standards = self.standards.get("standards") or {}
        observed_levels = self._normalize_levels(observations)
        for level, limits in sorted((standards.get("levels") or {}).items()):
            measured = observed_levels.get(int(level))
            if not measured:
                issues.append(
                    {
                        "standard": f"standards.levels.{level}",
                        "level": int(level),
                        "message": f"Lv{level} の実測値が計測されていない (基準は確認できない)",
                    }
                )
                continue
            for field, lower, upper in (
                ("hp", "min_hp", "max_hp"),
                ("attack", "min_attack", "max_attack"),
            ):
                value = measured.get(field)
                if value is None:
                    continue
                for key in (lower, upper):
                    limit = limits.get(key)
                    if limit is None:
                        continue
                    violated = value < limit if key == lower else value > limit
                    if violated:
                        issues.append(
                            {
                                "standard": f"standards.levels.{level}.{key}",
                                "level": int(level),
                                "field": field,
                                "value": value,
                                "limit": limit,
                                "message": (
                                    f"Lv{level} の {field} が実測 {value} で、"
                                    f"基準 {key}={limit} を外れている"
                                ),
                            }
                        )

        economy = self.standards.get("economy") or {}
        max_gold = economy.get("max_gold_per_dungeon_floor")
        gold = ((observations or {}).get("economy") or {}).get("gold_per_dungeon_floor")
        if max_gold is not None and gold is None:
            issues.append(
                {
                    "standard": "economy.max_gold_per_dungeon_floor",
                    "message": (
                        "1 ダンジョンフロアあたりの獲得ゴールドが計測されていない "
                        "(基準は確認できない)"
                    ),
                }
            )
        elif max_gold is not None and gold > max_gold:
            issues.append(
                {
                    "standard": "economy.max_gold_per_dungeon_floor",
                    "field": "gold_per_dungeon_floor",
                    "value": gold,
                    "limit": max_gold,
                    "message": (
                        f"1 ダンジョンフロアあたりの획取ゴールドが実測 {gold} で、"
                        f"基準 {max_gold} を超えている"
                    ),
                }
            )

        return {
            "status": "PASS" if not issues else "FAIL",
            "issues": issues,
            "standards_loaded": bool(self.standards),
        }

    @staticmethod
    def _normalize_levels(observations: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
        """``{"levels": {...}}`` と ``{レベル: {...}}`` の両方を受け取る。"""
        if not isinstance(observations, dict):
            return {}
        raw = observations.get("levels", observations)
        if not isinstance(raw, dict):
            return {}
        return {int(level): stats for level, stats in raw.items() if isinstance(stats, dict)}


class BalanceSimulator:
    """実ゲームの戦闘ループをそのまま回して測るバランス計測器。"""

    # 実攻撃のたびに config.yaml を読み直すため 1 試行は実測 0.1〜0.5 秒かかる。
    # レポート既定の試行回数はこの実測時間に合わせて抑える (判定基準は YAML 側)。
    SCENARIO_TRIALS = 30

    def __init__(self):
        self.report = {}
        self.checker = BalanceChecker()

    # --- 実戦ループ -----------------------------------------------------

    def _reset_player(self, player_level: int, position: tuple[int, int]) -> Any:
        """指定レベルのプレイヤーを計測用の初期状態へ戻す。

        実ゲームと同じレベルアップ規則 (1レベルにつき 8 能力値からランダムに 2 つを +1)。
        """
        engine, _ = acquire_world()
        player = engine.player

        attributes = dict(_WORLD["base_attributes"])
        for _ in range(max(0, player_level - 1)):
            for name in random.sample(ATTRIBUTE_KEYS, 2):
                attributes[name] += 1
        if getattr(player, "_base_attributes", None) is not None:
            player._base_attributes = Attributes(**attributes)
        for name, value in attributes.items():
            setattr(player.attributes, name, value)
        player.level = player_level
        player.recalculate_stats()

        player.x, player.y = position
        player.hp = player.max_hp
        player.mp = player.max_mp
        player.energy = 0
        return player

    def _prepare_trial(self, player_level: int) -> tuple[Any, Any]:
        """1 試行の開始時に世界を初期状態へ戻し、指定レベルのプレイヤーを用意する。"""
        engine, arena = acquire_world()
        player = self._reset_player(player_level, arena)
        # 計測対象の戦闘 1 体を置く。マップ・AI・進行系は実物のまま使う。
        engine.entity_manager.entities = [player]
        engine.entity_manager.items_on_ground.clear()
        engine.turns = 0
        return engine, player

    def _spawn_monster(self, engine: Any, monster_type: str) -> Any | None:
        """データ定義からモンスターを生成する (階層補正はプレイヤーLvに合わせる)。"""
        player = engine.player
        altar = _WORLD.get("altar")
        for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            x, y = player.x + dx, player.y + dy
            if altar is not None and (x, y) == altar:
                continue
            if engine.game_map.is_walkable(x, y):
                return engine.data_manager.create_monster(
                    monster_type, x, y, level_scale=player.level
                )
        return None

    def _step_toward(self, engine: Any, monster: Any) -> tuple[int, int]:
        """モンスターへ向かう 1 手。隣接していれば攻撃、それ以外は歩けるタイルを選ぶ。"""
        player = engine.player
        dx = (monster.x > player.x) - (monster.x < player.x)
        dy = (monster.y > player.y) - (monster.y < player.y)
        altar = _WORLD.get("altar")
        for step in ((dx, dy), (dx, 0), (0, dy), (dy, dx), (0, dx), (dy, 0)):
            if step == (0, 0):
                continue
            x, y = player.x + step[0], player.y + step[1]
            if altar is not None and (x, y) == altar:
                continue
            occupant = engine.get_entity_at(x, y)
            if occupant is monster:
                return step
            if occupant is None and engine.game_map.is_walkable(x, y):
                return step
        return (0, 0)

    def _run_trial(self, scenario: BattleScenario) -> dict[str, Any] | None:
        """1 回の遭遇を実エンジンで最後まで回す。"""
        engine, player = self._prepare_trial(scenario.player_level)
        monster = self._spawn_monster(engine, scenario.monster_type)
        if monster is None:
            return None
        engine.entity_manager.add_entity(monster)

        player_hp_start = player.hp
        monster_hp_start = monster.hp
        dealt = taken = regen = 0
        turns = 0
        one_shot = False
        outcome = "timeout"

        while turns < self.checker.max_turns:
            turns += 1

            monster_hp_before = monster.hp
            engine.player_act(*self._step_toward(engine, monster))
            dealt_this_action = max(0, monster_hp_before - monster.hp)
            dealt += dealt_this_action
            if dealt_this_action >= monster_hp_start:
                one_shot = True
            if monster.hp <= 0:
                outcome = "win" if player.hp > 0 else "draw"
                break

            hp_before = player.hp
            # 敵 AI の行動選択と turn ベースの自然回復はここ ([[engine.py:advance_world]]) で起きる。
            engine.advance_world()
            damage = hp_before - player.hp
            if damage > 0:
                taken += damage
                if damage >= player_hp_start:
                    one_shot = True
            else:
                regen += -damage
            if player.hp <= 0:
                outcome = "loss"
                break

        engine.entity_manager.remove_entity(monster)
        return {
            "outcome": outcome,
            "turns": turns,
            "dmg_dealt": dealt,
            "dmg_taken": taken,
            "hp_regen": regen,
            "one_shot": one_shot,
        }

    # --- 判定 -----------------------------------------------------------

    def _judge(self, scenario: BattleScenario, stats: dict[str, Any]) -> tuple[bool, list[str]]:
        """YAML の判定基準で「バランス良好」かを決める。"""
        criteria = self.checker.judgement
        reasons: list[str] = []

        if stats["stalled_rate"] > 0:
            reasons.append(
                f"{stats['stalled_count']} 回の戦闘が {self.checker.max_turns} ターンで終わらなかった"
            )
        if stats["one_shot_rate"] > criteria.get("max_one_shot_rate", 0.1):
            reasons.append(
                f"一撃決着の割合 {stats['one_shot_rate']:.2f} が上限 "
                f"{criteria.get('max_one_shot_rate')} を超えた"
            )
        if stats["damage_taken_ratio"] < criteria.get("min_damage_taken_ratio", 0.1):
            reasons.append(
                f"被与ダメージ比 {stats['damage_taken_ratio']:.2f} が下限 "
                f"{criteria.get('min_damage_taken_ratio')} を下回った"
            )

        expected = scenario.expected_win_rate
        absolute = criteria.get("absolute_victory_win_rate", 1.0)
        if expected is not None:
            if expected < absolute and stats["win_rate"] >= absolute:
                reasons.append(
                    f"期待勝率 {expected} に対し勝率 {stats['win_rate']} (絶対勝利) となった"
                )
            elif abs(stats["win_rate"] - expected) > criteria.get("win_rate_tolerance", 0.3):
                reasons.append(
                    f"勝率 {stats['win_rate']} が期待値 {expected} から許容範囲 "
                    f"{criteria.get('win_rate_tolerance')} を超えた"
                )
        return not reasons, reasons

    def simulate_battle(
        self,
        player_level: int = 1,
        monster_type: str = "slime",
        trials: int = 100,
        expected_win_rate: float | None = None,
    ) -> dict[str, Any]:
        scenario = BattleScenario(
            name=f"lvl{player_level}_vs_{monster_type}",
            player_level=player_level,
            monster_type=monster_type,
            trials=trials,
            expected_win_rate=expected_win_rate,
        )

        results = [self._run_trial(scenario) for _ in range(trials)]
        completed = [r for r in results if r is not None]
        if not completed:
            return {
                "player_level": player_level,
                "monster_type": monster_type,
                "trials": trials,
                "completed_trials": 0,
                "win_rate": 0.0,
                "expected_win_rate": expected_win_rate,
                "win_rate_alert": True,
                "avg_turns": 0.0,
                "std_dev_turns": 0.0,
                "avg_dmg_dealt": 0.0,
                "avg_dmg_taken": 0.0,
                "avg_hp_regen": 0.0,
                "damage_taken_ratio": 0.0,
                "one_shot_count": 0,
                "one_shot_rate": 1.0,
                "stalled_count": 0,
                "stalled_rate": 1.0,
                "is_balanced": False,
                "unbalanced_reasons": ["戦闘を開始できなかった"],
            }

        count = len(completed)
        turns_list = [r["turns"] for r in completed]
        avg_turns = sum(turns_list) / count
        variance = sum((x - avg_turns) ** 2 for x in turns_list) / count
        avg_dealt = sum(r["dmg_dealt"] for r in completed) / count
        avg_taken = sum(r["dmg_taken"] for r in completed) / count
        one_shot_count = sum(1 for r in completed if r["one_shot"])
        stalled_count = sum(1 for r in completed if r["outcome"] == "timeout")
        win_rate = round(sum(1 for r in completed if r["outcome"] == "win") / count, 3)

        stats = {
            "win_rate": win_rate,
            "avg_turns": avg_turns,
            "one_shot_rate": one_shot_count / count,
            "stalled_count": stalled_count,
            "stalled_rate": stalled_count / count,
            # 被与ダメージ比。0 に近いほど相手が何もできない一方的な戦闘。
            "damage_taken_ratio": (avg_taken / avg_dealt) if avg_dealt else float("inf"),
        }
        is_balanced, reasons = self._judge(scenario, stats)

        return {
            "player_level": player_level,
            "monster_type": monster_type,
            "trials": trials,
            "completed_trials": count,
            "win_rate": win_rate,
            "expected_win_rate": expected_win_rate,
            "win_rate_alert": bool(reasons),
            "avg_turns": round(avg_turns, 2),
            "std_dev_turns": round(math.sqrt(variance), 2),
            "avg_dmg_dealt": round(avg_dealt, 2),
            "avg_dmg_taken": round(avg_taken, 2),
            "avg_hp_regen": round(sum(r["hp_regen"] for r in completed) / count, 2),
            "damage_taken_ratio": round(
                stats["damage_taken_ratio"]
                if stats["damage_taken_ratio"] != float("inf")
                else 999.0,
                3,
            ),
            "one_shot_count": one_shot_count,
            "one_shot_rate": round(stats["one_shot_rate"], 3),
            "stalled_count": stalled_count,
            "stalled_rate": round(stats["stalled_rate"], 3),
            "is_balanced": is_balanced,
            "unbalanced_reasons": reasons,
        }

    # --- 経済計測 -------------------------------------------------------

    def _current_gold(self) -> int:
        """エンジン側の所持ゴールド。"""
        engine, _ = acquire_world()
        return int(engine.survival.gold)

    def _restore_floor(self, player_level: int) -> list[Any]:
        """実ダンジョン1階を生成時の状態へ戻し、その階に居るモンスターを返す。"""
        engine, _ = acquire_world()
        monsters = [copy.deepcopy(m) for m in _WORLD["floor_monsters"]]
        self._restore_entity_state(engine.player, _WORLD["floor_player"])
        self._restore_entity_state(engine.pet, _WORLD["floor_pet"])
        engine.entity_manager.entities = [engine.player, engine.pet, *monsters]
        engine.entity_manager.items_on_ground.clear()
        engine.entity_manager.items_on_ground.extend(_WORLD["floor_items"])
        engine.entity_manager.resource_nodes.clear()
        # 依頼の進捗は GOLD の決済 (``managers/combat_manager.py``) に効くので、
        # 毎回の計測を同じ状態から始めるために巻き戻す。
        engine.quests = copy.deepcopy(_WORLD["floor_quests"])
        engine.turns = 0
        self._reset_player(player_level, _WORLD["floor_start"])
        return monsters

    @staticmethod
    def _restore_entity_state(entity: Any, snapshot: Any) -> None:
        """エンティティの中身を生成時の状態へ戻す。

        システム側が握っているオブジェクト参照を維持するため、
        インスタンスを差し替えるのでなく中身だけを書き戻す。
        """
        entity.__dict__.clear()
        entity.__dict__.update(copy.deepcopy(snapshot.__dict__))

    @staticmethod
    def _floor_monsters(engine: Any) -> list[Any]:
        """その階に残っているモンスター (プレイヤーが倒すべき身)。"""
        return [
            e for e in engine.entity_manager.get_living_entities() if _is_hostile(e) and e.hp > 0
        ]

    @staticmethod
    def _approach_path(engine: Any, target: Any) -> list[tuple[int, int]] | None:
        """壁・エンティティ・祭壇を避けて、``target`` のマスまで進む経路を返す。

        経路の最後の 1 手は ``target`` のマスそのものへの踏み込みで、これは攻撃になる。
        到達できないときは ``None``。
        """
        altar = _WORLD.get("altar")
        blocked = engine.entity_manager.get_blocked_positions()
        blocked.discard((target.x, target.y))
        blocked.discard((engine.player.x, engine.player.y))

        start = (engine.player.x, engine.player.y)
        came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        queue = deque([start])
        while queue:
            x, y = queue.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                point = (x + dx, y + dy)
                if point in came_from or point in blocked:
                    continue
                if altar is not None and point == altar:
                    # 祭壇は ``player_act`` が例外を投げるタイル (``acquire_world``)。
                    continue
                if not engine.game_map.is_walkable(*point):
                    continue
                came_from[point] = (x, y)
                queue.append(point)

        goal = (target.x, target.y)
        if goal not in came_from:
            return None
        path: list[tuple[int, int]] = []
        node = goal
        while came_from[node] is not None:
            path.append(node)
            node = came_from[node]
        path.reverse()
        return path

    def _next_floor_target(
        self, engine: Any, monsters: list[Any]
    ) -> tuple[Any | None, list[tuple[int, int]]]:
        """到達可能なうち最も近いモンスターと、そこまでの経路を返す。"""
        player = engine.player
        for monster in sorted(monsters, key=lambda m: abs(m.x - player.x) + abs(m.y - player.y)):
            path = self._approach_path(engine, monster)
            if path:
                return monster, path
        return None, []

    def _clear_dungeon_floor(self, player_level: int, max_turns: int) -> dict[str, Any]:
        """実ダンジョン1階を実エンジンで全撃破する (経済計測のための 1 フロア実走)。

        移動は ``player_act``、敵 AI と turn ベースの自然回復は ``advance_world`` に任せる。
        """
        engine, _ = acquire_world()
        monsters = self._restore_floor(player_level)
        turns = 0
        target: Any = None
        path: list[tuple[int, int]] = []
        died = False

        while turns < max_turns:
            alive = self._floor_monsters(engine)
            if not alive:
                break
            if target is None or target.hp <= 0 or not path:
                target, path = self._next_floor_target(engine, alive)
                if target is None:
                    # ここまで来ると階を全滅させられないので「1 フロア」を測れない。
                    break
            before_pos = (target.x, target.y)
            point = path[0]
            moved = engine.player_act(point[0] - engine.player.x, point[1] - engine.player.y)
            turns += 1
            if moved:
                path.pop(0)
            if target.hp <= 0:
                path = []
                continue
            engine.advance_world()
            turns += 1
            if (target.x, target.y) != before_pos:
                path = []  # 敵が動いたので経路を作り直す
            if engine.player.hp <= 0:
                died = True
                break

        remaining = self._floor_monsters(engine)
        return {
            "turns": turns,
            "died": died,
            "cleared": not died and not remaining,
            # ペットも戦うので、撃破数はプレイヤーの撃破数ではなく階全体の数にする。
            "defeated": len(monsters) - len(remaining),
            "monsters": len(monsters),
        }

    def _measure_gold_per_floor(self) -> dict[str, Any]:
        """「1 ダンジョンフロアあたりの獲得ゴールド」を実測する。

        実ダンジョン1階を全撃破するまでの ``survival.gold`` を測る。
        階・仲間・依頼・GOLD を毎回初期状態へ戻し、乱数も固定するので、
        値は試行回数や計測の順番に依存しない。
        全滅させられなかった (死亡・到達不能) ときは ``gold_per_dungeon_floor`` を
        ``None`` にして理由を残す。値をでっち上げないための措置。
        """
        config = self.checker.economy_floor_run
        player_level = int(config.get("player_level", 1))
        max_turns = int(config.get("max_turns", 2000))

        engine, _ = acquire_world()
        gold_before = self._current_gold()
        caller_state = random.getstate()
        engine.survival.gold = 0
        try:
            random.seed(ECONOMY_SEED)
            run = self._clear_dungeon_floor(player_level, max_turns)
            gold = self._current_gold()
        finally:
            random.setstate(caller_state)
            engine.survival.gold = gold_before

        measurement: dict[str, Any] = {
            "gold_per_dungeon_floor": gold if run["cleared"] else None,
            "dungeon_level": 1,
            "player_level": player_level,
            "defeated": run["defeated"],
            "monsters": run["monsters"],
            "turns": run["turns"],
            "method": "実ダンジョン1階を全撃破するまでの獲得ゴールド",
        }
        if not run["cleared"]:
            measurement["not_measured_because"] = (
                "プレイヤーが倒された" if run["died"] else "1 フロアを全滅させられなかった"
            )
        return measurement

    # --- レポート -------------------------------------------------------

    def _collect_observations(self, economy: dict[str, Any]) -> dict[str, Any]:
        """YAML の基準に照合するための実測値を集める。

        ``economy`` は ``_measure_gold_per_floor`` の戻り値。計測できなかったときは
        ``gold_per_dungeon_floor`` が無いので、基準を確認できていない issues になる。
        """
        engine, _ = acquire_world()
        levels = sorted(
            int(level)
            for level in ((self.checker.standards.get("standards") or {}).get("levels") or {})
        )
        measured: dict[int, dict[str, Any]] = {}
        for level in levels:
            _, player = self._prepare_trial(level)
            measured[level] = {"hp": player.max_hp, "attack": player.attributes.strength}
        observations: dict[str, Any] = {"levels": measured}
        if economy.get("gold_per_dungeon_floor") is not None:
            observations["economy"] = {"gold_per_dungeon_floor": economy["gold_per_dungeon_floor"]}
        return observations

    def generate_html_report(
        self, report_data: dict[str, Any], output_html: str = "balance_report.html"
    ) -> str:
        """シミュレーション結果をHTMLレポートとして出力 (Step 42)"""
        html_lines = [
            "<!DOCTYPE html>",
            "<html lang='ja'>",
            "<head><meta charset='UTF-8'><title>Elona Battle Balance Report</title>",
            "<style>",
            "body { font-family: 'Segoe UI', sans-serif; background: #0f172a; color: #f8fafc; padding: 24px; }",
            "table { width: 100%; border-collapse: collapse; margin-top: 16px; background: #1e293b; border-radius: 8px; overflow: hidden; }",
            "th, td { padding: 12px; border: 1px solid #334155; text-align: left; }",
            "th { background: #3b82f6; color: white; }",
            ".pass { color: #4ade80; font-weight: bold; }",
            ".warn { color: #f87171; font-weight: bold; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>⚔️ Elona Commercial Battle Balance Report: <span class='{'pass' if report_data.get('summary') == 'PASS' else 'warn'}'>{report_data.get('summary')}</span></h1>",
            "<table>",
            "<tr><th>シナリオ</th><th>プレイヤーLv</th><th>対象モンスター</th><th>勝率</th>"
            "<th>期待勝率</th><th>平均ターン</th><th>与/被</th><th>判定理由</th><th>判定</th></tr>",
        ]
        for key, sc in report_data.get("scenarios", {}).items():
            status_cls = "pass" if sc.get("is_balanced") else "warn"
            status_txt = "BALANCED" if sc.get("is_balanced") else "WARNING"
            reasons = " / ".join(sc.get("unbalanced_reasons", []))
            html_lines.append(
                f"<tr><td>{key}</td><td>{sc.get('player_level')}</td><td>{sc.get('monster_type')}</td>"
                f"<td>{sc.get('win_rate')}</td><td>{sc.get('expected_win_rate')}</td>"
                f"<td>{sc.get('avg_turns')}</td><td>{sc.get('damage_taken_ratio')}</td>"
                f"<td>{reasons}</td><td class='{status_cls}'>{status_txt}</td></tr>"
            )

        html_lines.extend(["</table>", "</body>", "</html>"])
        html_str = "\n".join(html_lines)
        with open(output_html, "w", encoding="utf-8") as f:
            f.write(html_str)
        return output_html

    def run_full_validation(self, output_path: str = "balance_report.json") -> dict[str, Any]:
        scenarios = [(1, "slime", 0.95), (3, "goblin", 0.85), (5, "orc", 0.70)]
        results = {}
        all_passed = True
        for lvl, mtype, exp_rate in scenarios:
            key = f"lvl{lvl}_vs_{mtype}"
            res = self.simulate_battle(
                player_level=lvl,
                monster_type=mtype,
                trials=self.SCENARIO_TRIALS,
                expected_win_rate=exp_rate,
            )
            results[key] = res
            if not res["is_balanced"]:
                all_passed = False

        # 経済基準は「1 フロアを実際にクリアして得たゴールド」として実測する。
        # 階と GOLD を初期状態へ戻して測るので、上の試行回数とは独立になる。
        economy = self._measure_gold_per_floor()
        checker_res = self.checker.check_standards(self._collect_observations(economy))

        self.report = {
            "summary": (
                "PASS" if all_passed and checker_res["status"] == "PASS" else "WARNINGS_DETECTED"
            ),
            "judgement_criteria": self.checker.judgement,
            "scenarios": results,
            "economy_measurement": economy,
            "balance_standards": checker_res,
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.report, f, ensure_ascii=False, indent=2)

        # HTML も JSON と同じ出力先に置く (CWD をハードコードしない)。
        self.generate_html_report(self.report, os.path.splitext(output_path)[0] + ".html")
        return self.report


if __name__ == "__main__":
    sim = BalanceSimulator()
    rep = sim.run_full_validation()
    print("Balance validation completed:", rep["summary"])
