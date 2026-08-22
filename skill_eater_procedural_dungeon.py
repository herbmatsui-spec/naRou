"""
skill_eater_procedural_dungeon.py
Aの世界（スキル喰い） プロシージャルダンジョン生成・探索ログ・ミニマップシステム
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum

from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_exploration_system import DungeonRoom, ExplorationResult
from skill_eater_presentation_system import (
    SkillEaterPresentationSystem,
)
from skill_eater_system import CharacterState


class RoomType(Enum):
    CORRIDOR = "corridor"
    GUARD_ROOM = "guard_room"
    STORAGE = "storage"
    SERVER_ROOM = "server_room"
    EXPERIMENT_CHAMBER = "experiment_chamber"
    SAFE_ZONE = "safe_zone"
    TRAP_CORRIDOR = "trap_corridor"
    BOSS_ROOM = "boss_room"
    SECRET_ROOM = "secret_room"
    SHOP_ROOM = "shop_room"


class DungeonTheme(Enum):
    INDUSTRIAL_RUINS = "industrial_ruins"
    NEON_SEWERS = "neon_sewers"
    MIDAS_LABS = "midas_labs"
    BABEL_CORE = "babel_core"


@dataclass
class RoomTemplate:
    room_type: RoomType
    name: str
    description: str
    base_enemy_count: tuple[int, int] = (0, 0)
    treasure_chance: float = 0.0
    trap_chance: float = 0.0
    min_size: int = 1
    max_size: int = 1
    required_depth: int = 1
    weight: float = 1.0
    special_tags: list[str] = field(default_factory=list)


ROOM_TEMPLATES: dict[RoomType, RoomTemplate] = {
    RoomType.CORRIDOR: RoomTemplate(
        room_type=RoomType.CORRIDOR,
        name="通路",
        description="薄暗い通路が続く。足音が反響する。",
        base_enemy_count=(0, 1),
        treasure_chance=0.05,
        trap_chance=0.1,
        weight=2.0,
        special_tags=["transit"],
    ),
    RoomType.GUARD_ROOM: RoomTemplate(
        room_type=RoomType.GUARD_ROOM,
        name="警備室",
        description="防犯カメラと武装警備員が待機している。",
        base_enemy_count=(2, 4),
        treasure_chance=0.2,
        trap_chance=0.15,
        weight=1.2,
        special_tags=["combat"],
    ),
    RoomType.STORAGE: RoomTemplate(
        room_type=RoomType.STORAGE,
        name="物資倉庫",
        description="段ボールとコンテナが積み上げられている。",
        base_enemy_count=(0, 2),
        treasure_chance=0.5,
        trap_chance=0.1,
        weight=1.0,
        special_tags=["loot"],
    ),
    RoomType.SERVER_ROOM: RoomTemplate(
        room_type=RoomType.SERVER_ROOM,
        name="サーバー室",
        description="冷却音が鳴り響くサーバーラックが並ぶ。データが眠る。",
        base_enemy_count=(1, 3),
        treasure_chance=0.3,
        trap_chance=0.25,
        weight=0.8,
        special_tags=["tech", "hackable"],
    ),
    RoomType.EXPERIMENT_CHAMBER: RoomTemplate(
        room_type=RoomType.EXPERIMENT_CHAMBER,
        name="実験室",
        description="怪しげな薬品と実験台。人体実験の跡が残る。",
        base_enemy_count=(1, 3),
        treasure_chance=0.4,
        trap_chance=0.3,
        required_depth=3,
        weight=0.6,
        special_tags=["bio", "toxic"],
    ),
    RoomType.SAFE_ZONE: RoomTemplate(
        room_type=RoomType.SAFE_ZONE,
        name="安全区画",
        description="一時的に安息できる区画。簡易ベッドと水がある。",
        base_enemy_count=(0, 0),
        treasure_chance=0.1,
        trap_chance=0.0,
        weight=0.5,
        special_tags=["rest", "heal"],
    ),
    RoomType.TRAP_CORRIDOR: RoomTemplate(
        room_type=RoomType.TRAP_CORRIDOR,
        name="トラップ通路",
        description="床に不自然な継ぎ目。踏み込めば作動する。",
        base_enemy_count=(0, 1),
        treasure_chance=0.1,
        trap_chance=0.8,
        weight=0.7,
        special_tags=["trap_heavy"],
    ),
    RoomType.BOSS_ROOM: RoomTemplate(
        room_type=RoomType.BOSS_ROOM,
        name="ボスの間",
        description="重厚な扉の奥に、この区画の主が待ち構えている。",
        base_enemy_count=(1, 1),
        treasure_chance=1.0,
        trap_chance=0.2,
        required_depth=1,
        weight=0.0,
        special_tags=["boss", "unique"],
    ),
    RoomType.SECRET_ROOM: RoomTemplate(
        room_type=RoomType.SECRET_ROOM,
        name="秘密の部屋",
        description="隠された空間。貴重な何かが眠っているはずだ。",
        base_enemy_count=(0, 2),
        treasure_chance=0.8,
        trap_chance=0.3,
        required_depth=2,
        weight=0.0,
        special_tags=["secret", "rare_loot"],
    ),
    RoomType.SHOP_ROOM: RoomTemplate(
        room_type=RoomType.SHOP_ROOM,
        name="闇商人の店",
        description="フードを被った商人が怪しげな品を並べている。",
        base_enemy_count=(0, 0),
        treasure_chance=0.0,
        trap_chance=0.0,
        required_depth=2,
        weight=0.3,
        special_tags=["shop", "npc"],
    ),
}

THEME_ROOM_WEIGHTS: dict[DungeonTheme, dict[RoomType, float]] = {
    DungeonTheme.INDUSTRIAL_RUINS: {
        RoomType.CORRIDOR: 2.0,
        RoomType.GUARD_ROOM: 1.5,
        RoomType.STORAGE: 1.2,
        RoomType.SERVER_ROOM: 0.5,
        RoomType.EXPERIMENT_CHAMBER: 0.3,
        RoomType.SAFE_ZONE: 0.5,
        RoomType.TRAP_CORRIDOR: 0.8,
        RoomType.SHOP_ROOM: 0.2,
    },
    DungeonTheme.NEON_SEWERS: {
        RoomType.CORRIDOR: 1.5,
        RoomType.GUARD_ROOM: 1.0,
        RoomType.STORAGE: 0.8,
        RoomType.SERVER_ROOM: 0.6,
        RoomType.EXPERIMENT_CHAMBER: 0.7,
        RoomType.SAFE_ZONE: 0.6,
        RoomType.TRAP_CORRIDOR: 1.2,
        RoomType.SHOP_ROOM: 0.4,
    },
    DungeonTheme.MIDAS_LABS: {
        RoomType.CORRIDOR: 1.0,
        RoomType.GUARD_ROOM: 1.8,
        RoomType.STORAGE: 0.5,
        RoomType.SERVER_ROOM: 1.5,
        RoomType.EXPERIMENT_CHAMBER: 1.2,
        RoomType.SAFE_ZONE: 0.3,
        RoomType.TRAP_CORRIDOR: 0.6,
        RoomType.SHOP_ROOM: 0.1,
    },
    DungeonTheme.BABEL_CORE: {
        RoomType.CORRIDOR: 0.8,
        RoomType.GUARD_ROOM: 1.2,
        RoomType.STORAGE: 0.3,
        RoomType.SERVER_ROOM: 1.0,
        RoomType.EXPERIMENT_CHAMBER: 1.5,
        RoomType.SAFE_ZONE: 0.2,
        RoomType.TRAP_CORRIDOR: 1.0,
        RoomType.SHOP_ROOM: 0.0,
    },
}


@dataclass
class ProceduralDungeonConfig:
    min_rooms: int = 8
    max_rooms: int = 15
    loop_chance: float = 0.15
    secret_room_chance: float = 0.1
    boss_room_guaranteed: bool = True
    safe_zone_count: tuple[int, int] = (1, 2)


@dataclass
class DungeonNode:
    node_id: str
    room: DungeonRoom
    room_type: RoomType
    connections: list[str] = field(default_factory=list)
    x: int = 0
    y: int = 0
    is_discovered: bool = False
    is_cleared: bool = False
    is_secret: bool = False
    secret_unlocked: bool = False


@dataclass
class DungeonFloor:
    floor_id: str
    depth: int
    theme: DungeonTheme
    rooms: dict[str, DungeonNode] = field(default_factory=dict)
    connections: dict[str, list[str]] = field(default_factory=dict)
    entrance_id: str = ""
    exit_id: str = ""
    boss_room_id: str = ""
    discovered_rooms: set[str] = field(default_factory=set)
    cleared_rooms: set[str] = field(default_factory=set)


@dataclass
class ExplorationLogEntry:
    timestamp: float
    floor_id: str
    room_id: str
    action: str
    discovered_items: list[str] = field(default_factory=list)
    encountered_enemies: list[str] = field(default_factory=list)
    traps_triggered: list[str] = field(default_factory=list)
    damage_taken: int = 0
    duration_seconds: float = 0.0


class SkillEaterProceduralDungeon:
    def __init__(
        self,
        audio: SkillEaterAudioSystem | None = None,
        presentation: SkillEaterPresentationSystem | None = None,
    ):
        self.audio = audio or SkillEaterAudioSystem.get_instance()
        self.presentation = presentation or SkillEaterPresentationSystem.get_instance()
        self.floors: dict[str, DungeonFloor] = {}
        self.current_floor_id: str = ""
        self.current_room_id: str = ""
        self.exploration_log: list[ExplorationLogEntry] = []
        self.config = ProceduralDungeonConfig()
        self._rng = random.Random()

    def set_seed(self, seed: int) -> None:
        self._rng.seed(seed)
        random.seed(seed)

    def _select_theme_by_depth(self, depth: int) -> DungeonTheme:
        if depth <= 5:
            return DungeonTheme.INDUSTRIAL_RUINS
        elif depth <= 10:
            return DungeonTheme.NEON_SEWERS
        elif depth <= 15:
            return DungeonTheme.MIDAS_LABS
        else:
            return DungeonTheme.BABEL_CORE

    def generate_floor(
        self, depth: int, theme: DungeonTheme | None = None, seed: int | None = None
    ) -> DungeonFloor:
        if seed is not None:
            self.set_seed(seed)

        if theme is None:
            theme = self._select_theme_by_depth(depth)

        room_count = self._rng.randint(self.config.min_rooms, self.config.max_rooms)

        available_types = [
            rt for rt, tpl in ROOM_TEMPLATES.items()
            if tpl.required_depth <= depth and tpl.weight > 0
        ]
        weights = [THEME_ROOM_WEIGHTS[theme].get(rt, ROOM_TEMPLATES[rt].weight) for rt in available_types]

        selected_types = self._rng.choices(available_types, weights=weights, k=room_count)

        if self.config.boss_room_guaranteed:
            selected_types[-1] = RoomType.BOSS_ROOM

        safe_zone_needed = self._rng.randint(*self.config.safe_zone_count)
        safe_indices = self._rng.sample(range(room_count - 1), min(safe_zone_needed, room_count - 1))
        for idx in safe_indices:
            if selected_types[idx] not in (RoomType.BOSS_ROOM, RoomType.SECRET_ROOM):
                selected_types[idx] = RoomType.SAFE_ZONE

        nodes: dict[str, DungeonNode] = {}
        for i, rtype in enumerate(selected_types):
            node_id = f"floor_{depth}_room_{i}"
            template = ROOM_TEMPLATES[rtype]
            room = DungeonRoom(
                room_id=node_id,
                name=f"{template.name} {i+1}",
                description=template.description,
                has_treasure=False,
                has_trap=False,
                enemies=[],
            )
            node = DungeonNode(
                node_id=node_id,
                room=room,
                room_type=rtype,
            )
            nodes[node_id] = node

        connections = self._generate_mst_connections(list(nodes.keys()))
        node_ids = list(nodes.keys())
        for u, neighbors in connections.items():
            nodes[u].connections.extend(neighbors)
        self._add_loops(connections, nodes, node_ids)

        entrance_id = min(nodes.keys(), key=lambda k: len(connections.get(k, [])))
        farthest = self._find_farthest_node(entrance_id, connections)
        exit_id = farthest

        boss_node_id = f"floor_{depth}_room_{room_count - 1}"
        if RoomType.BOSS_ROOM in [n.room_type for n in nodes.values()]:
            for nid, node in nodes.items():
                if node.room_type == RoomType.BOSS_ROOM:
                    boss_node_id = nid
                    break

        if self._rng.random() < self.config.secret_room_chance:
            secret_id = f"floor_{depth}_secret_0"
            secret_template = ROOM_TEMPLATES[RoomType.SECRET_ROOM]
            secret_room = DungeonRoom(
                room_id=secret_id,
                name=secret_template.name,
                description=secret_template.description,
                has_treasure=True,
                has_trap=True,
                enemies=[],
            )
            secret_node = DungeonNode(
                node_id=secret_id,
                room=secret_room,
                room_type=RoomType.SECRET_ROOM,
                is_secret=True,
            )
            nodes[secret_id] = secret_node
            parent = self._rng.choice(list(nodes.keys()))
            if parent != secret_id:
                connections.setdefault(parent, []).append(secret_id)
                connections.setdefault(secret_id, []).append(parent)
                nodes[parent].connections.append(secret_id)
                secret_node.connections.append(parent)

        self._assign_coordinates(nodes, connections)

        floor = DungeonFloor(
            floor_id=f"floor_{depth}",
            depth=depth,
            theme=theme,
            rooms=nodes,
            connections=connections,
            entrance_id=entrance_id,
            exit_id=exit_id,
            boss_room_id=boss_node_id,
        )

        self._populate_floor_content(floor)
        self.floors[floor.floor_id] = floor

        if not self.current_floor_id:
            self.current_floor_id = floor.floor_id
            self.current_room_id = floor.entrance_id
            floor.discovered_rooms.add(floor.entrance_id)
            nodes[floor.entrance_id].is_discovered = True

        self._play_floor_generated_audio(floor)

        return floor

    def _generate_mst_connections(self, node_ids: list[str]) -> dict[str, list[str]]:
        connections: dict[str, list[str]] = {nid: [] for nid in node_ids}
        if not node_ids:
            return connections

        visited = {node_ids[0]}
        remaining = set(node_ids[1:])

        while remaining:
            u = self._rng.choice(list(visited))
            v = self._rng.choice(list(remaining))
            connections[u].append(v)
            connections[v].append(u)
            visited.add(v)
            remaining.remove(v)

        return connections

    def _add_loops(
        self, connections: dict[str, list[str]], nodes: dict[str, DungeonNode], node_ids: list[str]
    ) -> None:
        loop_count = int(len(node_ids) * self.config.loop_chance)
        all_pairs = [
            (a, b) for a in node_ids for b in node_ids
            if a < b and b not in connections.get(a, [])
        ]
        self._rng.shuffle(all_pairs)
        for a, b in all_pairs[:loop_count]:
            connections[a].append(b)
            connections[b].append(a)
            nodes[a].connections.append(b)
            nodes[b].connections.append(a)

    def _find_farthest_node(self, start: str, connections: dict[str, list[str]]) -> str:
        from collections import deque
        queue = deque([(start, 0)])
        visited = {start}
        farthest = start
        max_dist = 0

        while queue:
            node, dist = queue.popleft()
            if dist > max_dist:
                max_dist = dist
                farthest = node
            for neighbor in connections.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, dist + 1))
        return farthest

    def _assign_coordinates(
        self, nodes: dict[str, DungeonNode], connections: dict[str, list[str]]
    ) -> None:
        from collections import deque
        if not nodes:
            return

        start = next(iter(nodes))
        nodes[start].x = 0
        nodes[start].y = 0
        queue = deque([start])
        visited = {start}
        level_nodes: dict[int, list[str]] = {0: [start]}

        while queue:
            current = queue.popleft()
            cx, cy = nodes[current].x, nodes[current].y
            neighbors = connections.get(current, [])
            for i, neighbor in enumerate(neighbors):
                if neighbor not in visited:
                    visited.add(neighbor)
                    nodes[neighbor].x = cx + 100
                    nodes[neighbor].y = cy + (i - len(neighbors) / 2) * 80
                    level = nodes[current].x // 100 + 1
                    level_nodes.setdefault(level, []).append(neighbor)
                    queue.append(neighbor)

    def _populate_floor_content(self, floor: DungeonFloor) -> None:
        for node in floor.rooms.values():
            template = ROOM_TEMPLATES[node.room_type]
            self._populate_room_content(node, template, floor.depth, floor.theme)

    def _populate_room_content(
        self, node: DungeonNode, template: RoomTemplate, depth: int, theme: DungeonTheme
    ) -> None:
        min_enemies, max_enemies = template.base_enemy_count
        enemy_count = self._rng.randint(min_enemies, max_enemies)

        if enemy_count > 0 and node.room_type != RoomType.SAFE_ZONE:
            node.room.enemies = self._generate_enemies(enemy_count, depth, theme, node.room_type)

        if self._rng.random() < template.treasure_chance:
            node.room.has_treasure = True

        if self._rng.random() < template.trap_chance:
            node.room.has_trap = True

        if node.room_type == RoomType.SERVER_ROOM:
            node.room.description += " データ端子が露出している。"
        elif node.room_type == RoomType.EXPERIMENT_CHAMBER:
            node.room.description += " 異臭が漂う。"

    def _generate_enemies(
        self, count: int, depth: int, theme: DungeonTheme, room_type: RoomType
    ) -> list[CharacterState]:
        enemies = []
        for i in range(count):
            enemy = CharacterState(
                id=f"enemy_{theme.value}_{depth}_{i}",
                name=self._get_enemy_name(theme, room_type),
                hp=50 + depth * 10,
                max_hp=50 + depth * 10,
                mp=20,
                max_mp=20,
                atk=10 + depth * 2,
                defense=5 + depth,
                intelligence=5,
                speed=10,
            )
            enemies.append(enemy)
        return enemies

    def _get_enemy_name(self, theme: DungeonTheme, room_type: RoomType) -> str:
        names = {
            DungeonTheme.INDUSTRIAL_RUINS: ["廃棄ロボット", "変異ラット", "スクラップゴーレム"],
            DungeonTheme.NEON_SEWERS: ["下水ギャング", "ネオンムカデ", "汚染水スライム"],
            DungeonTheme.MIDAS_LABS: ["実験体", "警備ドローン", "サイバー強化兵"],
            DungeonTheme.BABEL_CORE: ["エリートガード", "概念兵器", "管理者アバター"],
        }
        return self._rng.choice(names.get(theme, ["敵"]))

    def _play_floor_generated_audio(self, floor: DungeonFloor) -> None:
        self.audio.play_sound("map_reveal_ping.ogg")
        self.presentation.add_event(
            emote_file="emote_map.png",
            audio_file="map_reveal_ping.ogg",
            message=f"第{floor.depth}層 [{floor.theme.value}] を生成しました",
        )

    def get_current_floor(self) -> DungeonFloor | None:
        return self.floors.get(self.current_floor_id)

    def get_current_room(self) -> DungeonNode | None:
        floor = self.get_current_floor()
        if floor:
            return floor.rooms.get(self.current_room_id)
        return None

    def add_log_entry(
        self,
        floor_id: str,
        room_id: str,
        action: str,
        discovered_items: list[str] | None = None,
        encountered_enemies: list[str] | None = None,
        traps_triggered: list[str] | None = None,
        damage_taken: int = 0,
        duration_seconds: float = 0.0,
    ) -> ExplorationLogEntry:
        entry = ExplorationLogEntry(
            timestamp=time.time(),
            floor_id=floor_id,
            room_id=room_id,
            action=action,
            discovered_items=discovered_items or [],
            encountered_enemies=encountered_enemies or [],
            traps_triggered=traps_triggered or [],
            damage_taken=damage_taken,
            duration_seconds=duration_seconds,
        )
        self.exploration_log.append(entry)
        return entry

    def log_room_discovery(self, floor_id: str, room_id: str) -> None:
        floor = self.floors.get(floor_id)
        if floor and room_id not in floor.discovered_rooms:
            floor.discovered_rooms.add(room_id)
            node = floor.rooms.get(room_id)
            if node:
                node.is_discovered = True
            self._play_discovery_audio()

    def log_room_cleared(self, floor_id: str, room_id: str) -> None:
        floor = self.floors.get(floor_id)
        if floor:
            floor.cleared_rooms.add(room_id)
            node = floor.rooms.get(room_id)
            if node:
                node.is_cleared = True

    def _play_discovery_audio(self) -> None:
        self.audio.play_sound("scanner_beep.ogg")
        self.presentation.add_event(
            emote_file="emote_radar.png",
            audio_file="scanner_beep.ogg",
            message="新区画発見",
        )

    def log_combat_encounter(
        self, floor_id: str, room_id: str, enemy_ids: list[str], result: str
    ) -> None:
        self.add_log_entry(
            floor_id=floor_id,
            room_id=room_id,
            action=f"COMBAT_{result}",
            encountered_enemies=enemy_ids,
        )

    def log_treasure_found(
        self, floor_id: str, room_id: str, items: list[str]
    ) -> None:
        self.add_log_entry(
            floor_id=floor_id,
            room_id=room_id,
            action="LOOT",
            discovered_items=items,
        )

    def log_trap_triggered(
        self, floor_id: str, room_id: str, trap_type: str, damage: int
    ) -> None:
        self.add_log_entry(
            floor_id=floor_id,
            room_id=room_id,
            action="TRAP",
            traps_triggered=[trap_type],
            damage_taken=damage,
        )

    def log_secret_found(self, floor_id: str, room_id: str) -> None:
        self.add_log_entry(
            floor_id=floor_id,
            room_id=room_id,
            action="SECRET_FOUND",
        )
        self.audio.play_sound("secret_revealed.ogg")
        self.presentation.add_event(
            emote_file="emote_eye.png",
            audio_file="secret_revealed.ogg",
            message="隠し部屋を発見！",
        )

    @property
    def exploration_progress(self) -> float:
        total = sum(len(f.rooms) for f in self.floors.values())
        discovered = sum(len(f.discovered_rooms) for f in self.floors.values())
        return discovered / max(1, total)

    def get_floor_progress(self, floor_id: str) -> float:
        floor = self.floors.get(floor_id)
        if not floor:
            return 0.0
        total = len(floor.rooms)
        discovered = len(floor.discovered_rooms)
        return discovered / max(1, total)

    def get_logs_by_floor(self, floor_id: str) -> list[ExplorationLogEntry]:
        return [e for e in self.exploration_log if e.floor_id == floor_id]

    def get_logs_by_action(self, action: str) -> list[ExplorationLogEntry]:
        return [e for e in self.exploration_log if e.action == action]

    def export_logs_json(self) -> list[dict]:
        return [
            {
                "timestamp": e.timestamp,
                "floor_id": e.floor_id,
                "room_id": e.room_id,
                "action": e.action,
                "discovered_items": e.discovered_items,
                "encountered_enemies": e.encountered_enemies,
                "traps_triggered": e.traps_triggered,
                "damage_taken": e.damage_taken,
                "duration_seconds": e.duration_seconds,
            }
            for e in self.exploration_log
        ]

    def get_minimap_data(self, floor_id: str | None = None) -> dict:
        target_floor_id = floor_id or self.current_floor_id
        floor = self.floors.get(target_floor_id)
        if not floor:
            return {}

        nodes_data = []
        for node in floor.rooms.values():
            nodes_data.append({
                "id": node.node_id,
                "x": node.x,
                "y": node.y,
                "type": node.room_type.value,
                "name": node.room.name,
                "discovered": node.is_discovered,
                "cleared": node.is_cleared,
                "is_secret": node.is_secret,
                "is_current": node.node_id == self.current_room_id,
                "has_treasure": node.room.has_treasure,
                "has_trap": node.room.has_trap,
                "enemy_count": len(node.room.enemies),
            })

        connections_data = []
        for from_id, to_ids in floor.connections.items():
            for to_id in to_ids:
                if from_id < to_id:
                    from_node = floor.rooms.get(from_id)
                    to_node = floor.rooms.get(to_id)
                    discovered = (
                        from_node and from_node.is_discovered
                        and to_node and to_node.is_discovered
                    )
                    connections_data.append({
                        "from": from_id,
                        "to": to_id,
                        "discovered": discovered,
                    })

        return {
            "floor_id": floor.floor_id,
            "depth": floor.depth,
            "theme": floor.theme.value,
            "nodes": nodes_data,
            "connections": connections_data,
            "current_room": self.current_room_id,
            "entrance_id": floor.entrance_id,
            "exit_id": floor.exit_id,
            "boss_room_id": floor.boss_room_id,
            "discovered": list(floor.discovered_rooms),
            "cleared": list(floor.cleared_rooms),
            "progress": self.get_floor_progress(target_floor_id),
        }

    def _check_progress_milestones(self, floor_id: str) -> None:
        progress = self.get_floor_progress(floor_id)
        milestones = [0.25, 0.5, 0.75, 1.0]
        for m in milestones:
            if progress >= m:
                attr = f"_milestone_{int(m * 100)}_reached"
                if not getattr(self, attr, False):
                    setattr(self, attr, True)
                    self._play_milestone_audio(m)

    def _play_milestone_audio(self, progress: float) -> None:
        self.audio.play_sound("map_reveal_ping.ogg")
        emote_map = {
            0.25: "emote_star.png",
            0.5: "emote_stars.png",
            0.75: "emote_exclamation.png",
            1.0: "emote_crown.png",
        }
        self.presentation.add_event(
            emote_file=emote_map.get(progress, "emote_star.png"),
            audio_file="map_reveal_ping.ogg",
            message=f"探索進行度 {int(progress * 100)}% 到達",
        )

    def get_connected_rooms(self, room_id: str | None = None) -> list[DungeonNode]:
        target_id = room_id or self.current_room_id
        floor = self.get_current_floor()
        if not floor:
            return []
        node = floor.rooms.get(target_id)
        if not node:
            return []
        connected = []
        for conn_id in node.connections:
            conn_node = floor.rooms.get(conn_id)
            if conn_node:
                connected.append(conn_node)
        return connected

    def find_path(self, from_id: str, to_id: str, floor_id: str | None = None) -> list[str]:
        target_floor_id = floor_id or self.current_floor_id
        floor = self.floors.get(target_floor_id)
        if not floor:
            return []

        from collections import deque
        queue = deque([(from_id, [from_id])])
        visited = {from_id}

        while queue:
            current, path = queue.popleft()
            if current == to_id:
                return path
            for neighbor in floor.connections.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return []

    def auto_explore(self, target_room_id: str | None = None) -> list[ExplorationResult]:
        results = []
        floor = self.get_current_floor()
        if not floor:
            return results

        if target_room_id is None:
            undiscovered = [nid for nid in floor.rooms if nid not in floor.discovered_rooms]
            if not undiscovered:
                return results
            target_room_id = undiscovered[0]

        path = self.find_path(self.current_room_id, target_room_id)
        if not path or len(path) < 2:
            return results

        for next_room_id in path[1:]:
            result = self.move_to_room_procedural(next_room_id)
            results.append(result)
            if result.action_type == "MOVE_ROOM":
                self._check_progress_milestones(self.current_floor_id)
        return results

    def move_to_room_procedural(self, target_room_id: str) -> ExplorationResult:
        floor = self.get_current_floor()
        if not floor or target_room_id not in floor.rooms:
            return ExplorationResult(
                action_type="MOVE_ROOM",
                message="行き先が存在しません。",
                current_room_id=self.current_room_id,
                played_sounds=[],
                presentation_events=[],
            )

        target_node = floor.rooms[target_room_id]
        current_node = floor.rooms.get(self.current_room_id)

        if target_room_id not in (current_node.connections if current_node else []):
            return ExplorationResult(
                action_type="MOVE_ROOM",
                message="直接移動できません。経路を確認してください。",
                current_room_id=self.current_room_id,
                played_sounds=[],
                presentation_events=[],
            )

        sounds = []
        events = []

        for _ in range(3):
            s = f"footstep0{self._rng.randint(0, 9)}.ogg"
            self.audio.play_sound(s)
            sounds.append(s)

        emote = "emote_exclamation.png" if target_node.room_type == RoomType.BOSS_ROOM else "emote_dots2.png"
        evt_enter = self.presentation.add_event(
            emote_file=emote,
            audio_file="doorOpen_1.ogg",
            message=f"{target_node.room.name} へ移動",
        )
        sounds.append("doorOpen_1.ogg")
        events.append(evt_enter)

        self.current_room_id = target_room_id
        self.log_room_discovery(self.current_floor_id, target_room_id)

        room = target_node.room
        self._check_progress_milestones(self.current_floor_id)

        return ExplorationResult(
            action_type="MOVE_ROOM",
            message=f"【エリア進入】{room.name} に到達した。（{room.description}）",
            current_room_id=self.current_room_id,
            played_sounds=sounds,
            presentation_events=events,
        )

    def descend_stairs(self) -> ExplorationResult:
        floor = self.get_current_floor()
        if not floor:
            return ExplorationResult(
                action_type="DESCEND",
                message="現在のフロアが存在しません。",
                current_room_id=self.current_room_id,
                played_sounds=[],
                presentation_events=[],
            )

        if self.current_room_id != floor.exit_id and self.current_room_id != floor.boss_room_id:
            return ExplorationResult(
                action_type="DESCEND",
                message="出口またはボス部屋でのみ階層移動可能です。",
                current_room_id=self.current_room_id,
                played_sounds=[],
                presentation_events=[],
            )

        next_depth = floor.depth + 1
        next_floor_id = f"floor_{next_depth}"

        if next_floor_id not in self.floors:
            self.generate_floor(next_depth)

        self.current_floor_id = next_floor_id
        next_floor = self.floors[next_floor_id]
        self.current_room_id = next_floor.entrance_id
        next_floor.discovered_rooms.add(next_floor.entrance_id)
        next_floor.rooms[next_floor.entrance_id].is_discovered = True

        sounds = ["stair_creak.ogg", "footstep01.ogg", "footstep02.ogg"]
        for s in sounds:
            self.audio.play_sound(s)

        evt = self.presentation.add_event(
            emote_file="emote_arrow_down.png",
            audio_file="stair_creak.ogg",
            message=f"第{next_depth}層へ降下",
        )

        self.log_room_discovery(self.current_floor_id, self.current_room_id)
        self._check_progress_milestones(self.current_floor_id)

        return ExplorationResult(
            action_type="DESCEND",
            message=f"階段を降り、第{next_depth}層 [{next_floor.theme.value}] に到達した。",
            current_room_id=self.current_room_id,
            played_sounds=sounds,
            presentation_events=[evt],
        )

    def ascend_stairs(self) -> ExplorationResult:
        floor = self.get_current_floor()
        if not floor or floor.depth <= 1:
            return ExplorationResult(
                action_type="ASCEND",
                message="これ以上上に行けません。",
                current_room_id=self.current_room_id,
                played_sounds=[],
                presentation_events=[],
            )

        if self.current_room_id != floor.entrance_id:
            return ExplorationResult(
                action_type="ASCEND",
                message="入口でのみ上層へ戻れます。",
                current_room_id=self.current_room_id,
                played_sounds=[],
                presentation_events=[],
            )

        prev_depth = floor.depth - 1
        prev_floor_id = f"floor_{prev_depth}"

        self.current_floor_id = prev_floor_id
        prev_floor = self.floors[prev_floor_id]
        self.current_room_id = prev_floor.exit_id

        sounds = ["stair_creak.ogg", "footstep01.ogg", "footstep02.ogg"]
        for s in sounds:
            self.audio.play_sound(s)

        evt = self.presentation.add_event(
            emote_file="emote_arrow_up.png",
            audio_file="stair_creak.ogg",
            message=f"第{prev_depth}層へ上昇",
        )

        return ExplorationResult(
            action_type="ASCEND",
            message=f"階段を上り、第{prev_depth}層 [{prev_floor.theme.value}] に戻った。",
            current_room_id=self.current_room_id,
            played_sounds=sounds,
            presentation_events=[evt],
        )

    def use_elevator(self, target_depth: int) -> ExplorationResult:
        if target_depth < 1 or target_depth > max(f.depth for f in self.floors.values()):
            return ExplorationResult(
                action_type="ELEVATOR",
                message="その階層は存在しません。",
                current_room_id=self.current_room_id,
                played_sounds=[],
                presentation_events=[],
            )

        target_floor_id = f"floor_{target_depth}"
        if target_floor_id not in self.floors:
            self.generate_floor(target_depth)

        self.current_floor_id = target_floor_id
        target_floor = self.floors[target_floor_id]
        self.current_room_id = target_floor.entrance_id
        target_floor.discovered_rooms.add(target_floor.entrance_id)
        target_floor.rooms[target_floor.entrance_id].is_discovered = True

        sounds = ["elevator_hum.ogg", "floor_transition_woosh.ogg"]
        for s in sounds:
            self.audio.play_sound(s)

        evt = self.presentation.add_event(
            emote_file="emote_arrow_down.png" if target_depth > self.get_current_floor().depth else "emote_arrow_up.png",
            audio_file="elevator_hum.ogg",
            message=f"エレベーターで第{target_depth}層へ移動",
        )

        self.log_room_discovery(self.current_floor_id, self.current_room_id)

        return ExplorationResult(
            action_type="ELEVATOR",
            message=f"エレベーターで第{target_depth}層 [{target_floor.theme.value}] へ移動した。",
            current_room_id=self.current_room_id,
            played_sounds=sounds,
            presentation_events=[evt],
        )

    def to_dict(self) -> dict:
        return {
            "floors": {
                fid: {
                    "floor_id": f.floor_id,
                    "depth": f.depth,
                    "theme": f.theme.value,
                    "entrance_id": f.entrance_id,
                    "exit_id": f.exit_id,
                    "boss_room_id": f.boss_room_id,
                    "discovered_rooms": list(f.discovered_rooms),
                    "cleared_rooms": list(f.cleared_rooms),
                    "rooms": {
                        nid: {
                            "node_id": n.node_id,
                            "room_type": n.room_type.value,
                            "connections": n.connections,
                            "x": n.x,
                            "y": n.y,
                            "is_discovered": n.is_discovered,
                            "is_cleared": n.is_cleared,
                            "is_secret": n.is_secret,
                            "secret_unlocked": n.secret_unlocked,
                            "room": {
                                "room_id": n.room.room_id,
                                "name": n.room.name,
                                "description": n.room.description,
                                "has_treasure": n.room.has_treasure,
                                "has_trap": n.room.has_trap,
                            },
                        }
                        for nid, n in f.rooms.items()
                    },
                    "connections": f.connections,
                }
                for fid, f in self.floors.items()
            },
            "current_floor_id": self.current_floor_id,
            "current_room_id": self.current_room_id,
            "exploration_log": self.export_logs_json(),
            "config": {
                "min_rooms": self.config.min_rooms,
                "max_rooms": self.config.max_rooms,
                "loop_chance": self.config.loop_chance,
                "secret_room_chance": self.config.secret_room_chance,
                "boss_room_guaranteed": self.config.boss_room_guaranteed,
                "safe_zone_count": self.config.safe_zone_count,
            },
        }

    @classmethod
    def from_dict(cls, data: dict, audio: SkillEaterAudioSystem | None = None, presentation: SkillEaterPresentationSystem | None = None) -> "SkillEaterProceduralDungeon":
        instance = cls(audio=audio, presentation=presentation)
        instance.current_floor_id = data.get("current_floor_id", "")
        instance.current_room_id = data.get("current_room_id", "")
        instance.config = ProceduralDungeonConfig(**data.get("config", {}))

        for fid, fdata in data.get("floors", {}).items():
            floor = DungeonFloor(
                floor_id=fdata["floor_id"],
                depth=fdata["depth"],
                theme=DungeonTheme(fdata["theme"]),
                entrance_id=fdata["entrance_id"],
                exit_id=fdata["exit_id"],
                boss_room_id=fdata["boss_room_id"],
                discovered_rooms=set(fdata.get("discovered_rooms", [])),
                cleared_rooms=set(fdata.get("cleared_rooms", [])),
                connections=fdata.get("connections", {}),
            )
            for nid, ndata in fdata.get("rooms", {}).items():
                room = DungeonRoom(
                    room_id=ndata["room"]["room_id"],
                    name=ndata["room"]["name"],
                    description=ndata["room"]["description"],
                    has_treasure=ndata["room"]["has_treasure"],
                    has_trap=ndata["room"]["has_trap"],
                )
                node = DungeonNode(
                    node_id=ndata["node_id"],
                    room=room,
                    room_type=RoomType(ndata["room_type"]),
                    connections=ndata.get("connections", []),
                    x=ndata.get("x", 0),
                    y=ndata.get("y", 0),
                    is_discovered=ndata.get("is_discovered", False),
                    is_cleared=ndata.get("is_cleared", False),
                    is_secret=ndata.get("is_secret", False),
                    secret_unlocked=ndata.get("secret_unlocked", False),
                )
                floor.rooms[nid] = node
            instance.floors[fid] = floor

        instance.exploration_log = [
            ExplorationLogEntry(**e) for e in data.get("exploration_log", [])
        ]
        return instance

    def explore_command(self, action: str, param: str | None = None) -> ExplorationResult:
        if action == "move" and param:
            return self.move_to_room_procedural(param)
        elif action == "descend":
            return self.descend_stairs()
        elif action == "ascend":
            return self.ascend_stairs()
        elif action == "elevator" and param:
            return self.use_elevator(int(param))
        elif action == "auto":
            results = self.auto_explore(param)
            return results[-1] if results else ExplorationResult(
                action_type="AUTO", message="探索対象がありません。",
                current_room_id=self.current_room_id, played_sounds=[], presentation_events=[]
            )
        elif action == "map":
            return ExplorationResult(
                action_type="MAP", message="ミニマップ表示",
                current_room_id=self.current_room_id, played_sounds=["map_reveal_ping.ogg"], presentation_events=[]
            )
        elif action == "log":
            return ExplorationResult(
                action_type="LOG", message=f"探索ログ: {len(self.exploration_log)}件",
                current_room_id=self.current_room_id, played_sounds=[], presentation_events=[]
            )
        return ExplorationResult(
            action_type="UNKNOWN", message=f"不明なコマンド: {action}",
            current_room_id=self.current_room_id, played_sounds=[], presentation_events=[]
        )
