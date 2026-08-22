"""
AI Spatial Safety & Threat Grid Evaluation System
Calculates threat heatmaps, mobility scores, and potential field navigation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from naRou.ai_blackboard import AIBlackboard
    from naRou.entity import Entity


class ThreatTable:
    """Calculates danger threat scores for entities."""

    BASE_THREATS = {
        "ドラゴン": 90,
        "魔王": 100,
        "ワイバーン": 70,
        "ゴーレム": 60,
        "ガーゴイル": 50,
        "ヒドラ": 65,
        "ドレイク": 60,
        "スケルトン": 35,
        "オーク": 30,
        "野盗": 25,
        "ウルフ": 20,
        "ゴブリン": 15,
        "コウモリ": 10,
        "スライム": 10,
    }

    @classmethod
    def get_entity_threat_level(cls, entity: Entity) -> float:
        """Compute numerical threat level based on name keywords and stats."""
        name = getattr(entity, "name", "")
        base = 20.0
        for kw, val in cls.BASE_THREATS.items():
            if kw in name:
                base = float(val)
                break

        hp = getattr(entity, "hp", 20)
        power = getattr(entity, "power", 5)
        threat = base + (power * 2.0) + (hp * 0.5)
        return threat


class PotentialFieldNavigator:
    """Calculates attractive forces to goals and repulsive forces from threats."""

    @staticmethod
    def compute_potential(
        pos: tuple[int, int],
        goal_pos: tuple[int, int] | None,
        danger_map: dict[tuple[int, int], float],
        mobility_map: dict[tuple[int, int], float],
        fog_map: dict[tuple[int, int], float],
    ) -> float:
        """Compute combined potential value (lower is more attractive/safe)."""
        px, py = pos

        # Attractive potential to goal
        att_force = 0.0
        if goal_pos:
            gx, gy = goal_pos
            dist = max(abs(px - gx), abs(py - gy))
            att_force = dist * 8.0

        # Repulsive forces from danger, fog, and low mobility
        danger_rep = danger_map.get(pos, 0.0)
        fog_rep = fog_map.get(pos, 0.0)
        mobility_bonus = mobility_map.get(pos, 0.0)

        # Combined potential score
        potential = att_force + (danger_rep * 1.5) + (fog_rep * 0.5) - mobility_bonus
        return potential


class SafetyGridEvaluator:
    """Evaluates safety, danger, and tactical value of tiles in local neighborhood."""

    def __init__(self, blackboard: AIBlackboard, radius: int = 7):
        self.bb = blackboard
        self.radius = radius

    def get_local_bounds(self) -> tuple[int, int, int, int]:
        """Return (min_x, max_x, min_y, max_y) bounding box for safety evaluation."""
        player = self.bb.engine.player
        game_map = self.bb.engine.game_map
        max_w = len(game_map.tiles)
        max_h = len(game_map.tiles[0])

        min_x = max(0, player.x - self.radius)
        max_x = min(max_w - 1, player.x + self.radius)
        min_y = max(0, player.y - self.radius)
        max_h_val = min(max_h - 1, player.y + self.radius)

        return (min_x, max_x, min_y, max_h_val)

    def compute_danger_map(self) -> dict[tuple[int, int], float]:
        """Generate a heatmap mapping (x, y) coordinates to cumulative danger values."""
        engine = self.bb.engine
        player = engine.player
        danger_map: dict[tuple[int, int], float] = {}

        min_x, max_x, min_y, max_y = self.get_local_bounds()

        # Iterate all living hostiles
        for ent in engine.entity_manager.get_living_entities():
            if ent in (player, getattr(engine, "pet", None)):
                continue
            if getattr(ent, "faction", "") == "player":
                continue

            threat = ThreatTable.get_entity_threat_level(ent)

            # Apply danger radius around enemy
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    tx, ty = ent.x + dx, ent.y + dy
                    if min_x <= tx <= max_x and min_y <= ty <= max_y:
                        if not engine.game_map.is_walkable(tx, ty):
                            continue
                        chebyshev_dist = max(abs(dx), abs(dy))
                        if chebyshev_dist == 0:
                            danger_map[(tx, ty)] = danger_map.get((tx, ty), 0.0) + threat * 2.0
                        elif chebyshev_dist == 1:
                            danger_map[(tx, ty)] = danger_map.get((tx, ty), 0.0) + threat * 1.5
                        elif chebyshev_dist == 2:
                            danger_map[(tx, ty)] = danger_map.get((tx, ty), 0.0) + threat * 0.8
                        else:
                            danger_map[(tx, ty)] = danger_map.get((tx, ty), 0.0) + threat * 0.3

        # Add trap danger
        for tx, ty in self.bb.known_traps:
            if min_x <= tx <= max_x and min_y <= ty <= max_y:
                danger_map[(tx, ty)] = danger_map.get((tx, ty), 0.0) + 50.0

        return danger_map

    def compute_mobility_scores(self) -> dict[tuple[int, int], float]:
        """Compute branching mobility scores (number of open neighbor tiles) for local area."""
        engine = self.bb.engine
        game_map = engine.game_map
        min_x, max_x, min_y, max_y = self.get_local_bounds()
        mobility_map: dict[tuple[int, int], float] = {}

        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                if not game_map.is_walkable(x, y):
                    continue

                open_neighbors = 0
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < len(game_map.tiles) and 0 <= ny < len(game_map.tiles[0]):
                        if game_map.is_walkable(nx, ny):
                            open_neighbors += 1

                score = open_neighbors * 5.0
                if open_neighbors <= 2:
                    score -= 30.0
                elif open_neighbors >= 6:
                    score += 15.0

                mobility_map[(x, y)] = score

        return mobility_map

    def compute_fog_penalties(self) -> dict[tuple[int, int], float]:
        """Compute uncertainty penalties for tiles bordering unexplored fog of war."""
        game_map = self.bb.engine.game_map
        min_x, max_x, min_y, max_y = self.get_local_bounds()
        fog_map: dict[tuple[int, int], float] = {}

        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                if not game_map.explored[x][y] or not game_map.is_walkable(x, y):
                    continue

                unexplored_adjacent = sum(
                    1 for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]
                    if 0 <= x + dx < len(game_map.tiles) and 0 <= y + dy < len(game_map.tiles[0])
                    and not game_map.explored[x + dx][y + dy]
                )
                if unexplored_adjacent > 0:
                    fog_map[(x, y)] = unexplored_adjacent * 8.0

        return fog_map

    def find_best_safe_step(self, goal_pos: tuple[int, int] | None = None) -> tuple[int, int] | None:
        """Find the neighbor step with the lowest combined potential value."""
        engine = self.bb.engine
        player = engine.player
        game_map = engine.game_map

        danger_map = self.compute_danger_map()
        mobility_map = self.compute_mobility_scores()
        fog_map = self.compute_fog_penalties()

        best_move = None
        best_pot = 999999.0

        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
            nx, ny = player.x + dx, player.y + dy
            if not game_map.is_walkable(nx, ny) or engine.get_entity_at(nx, ny):
                continue

            pot = PotentialFieldNavigator.compute_potential(
                (nx, ny), goal_pos, danger_map, mobility_map, fog_map
            )
            if pot < best_pot:
                best_pot = pot
                best_move = (dx, dy)

        return best_move

    def find_tactical_retreat_step(self) -> tuple[int, int] | None:
        """Find the best tactical retreat step maximizing distance from hostiles and open mobility."""
        engine = self.bb.engine
        player = engine.player
        game_map = engine.game_map

        danger_map = self.compute_danger_map()
        mobility_map = self.compute_mobility_scores()

        best_move = None
        best_score = -999999.0

        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
            nx, ny = player.x + dx, player.y + dy
            if not game_map.is_walkable(nx, ny) or engine.get_entity_at(nx, ny):
                continue

            danger = danger_map.get((nx, ny), 0.0)
            mobility = mobility_map.get((nx, ny), 0.0)

            # Score: High mobility bonus minus heavy danger penalty
            score = (mobility * 2.0) - (danger * 3.0)
            if score > best_score:
                best_score = score
                best_move = (dx, dy)

        return best_move
