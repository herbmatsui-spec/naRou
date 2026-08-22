"""
Dynamic World State System Module (Steps 47-53)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from entity import Entity


from enum import Enum, auto

from typing_extensions import Self


class WorldPhase(Enum):
    """ワールドの物語進行フェーズ (設計書 2.1)"""

    BEGINNING = auto()  # 導入期
    AWAKENING = auto()  # 目覚め
    EXPLORATION = auto()  # 探索期
    CONFRONTATION = auto()  # 対立期
    CLIMAX = auto()  # 終局
    EPILOGUE = auto()  # 後日談


# Step 48: WorldStateTemplate
@dataclass
class WorldStateTemplate:
    """ワールド状態テンプレートデータ (Step 48)"""

    version: str = "1.0"
    last_updated: str = ""
    current_phase: WorldPhase = WorldPhase.BEGINNING
    persistent_variables: dict[str, Any] = field(default_factory=dict)
    location_states: dict[str, Any] = field(default_factory=dict)
    faction_relations: dict[str, Any] = field(default_factory=dict)
    global_events: list[str] = field(default_factory=list)
    player_legacy: dict[str, Any] = field(default_factory=dict)
    # Vertical World Extension: プレイヤーの層情報
    player_layer_history: list[dict[str, Any]] = field(default_factory=list)
    visited_layers: set[str] = field(default_factory=set)  # ゾーン:バイオーム:深度:次元形式
    layer_discoveries: dict[str, Any] = field(default_factory=dict)


# Step 49, 50: WorldStateRegistry
class WorldStateRegistry:
    """ワールド状態レジストリ (Step 49, 50)"""

    _instance: WorldStateRegistry | None = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._template = None
        return cls._instance

    def load(self, file_path: str = "data/world_state.yaml") -> None:
        """YAMLからワールド状態テンプレートを読み込む (Step 50)"""
        if not os.path.exists(file_path):
            self._template = WorldStateTemplate(version="1.0")
            return

        with open(file_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        t_dict = raw.get("world_state_template", {})

        # フェーズ文字列からEnumへの変換
        phase_str = t_dict.get("current_phase", "BEGINNING")
        try:
            phase = WorldPhase[phase_str]
        except KeyError:
            phase = WorldPhase.BEGINNING

        self._template = WorldStateTemplate(
            version=t_dict.get("version", "1.0"),
            last_updated=t_dict.get("last_updated", ""),
            current_phase=phase,
            persistent_variables=t_dict.get("persistent_variables", {}),
            location_states=t_dict.get("location_states", {}),
            faction_relations=t_dict.get("faction_relations", {}),
            global_events=t_dict.get("global_events", []),
            player_legacy=t_dict.get("player_legacy", {}),
            # Vertical World Extension
            player_layer_history=t_dict.get("player_layer_history", []),
            visited_layers=set(t_dict.get("visited_layers", [])),
            layer_discoveries=t_dict.get("layer_discoveries", {}),
        )

    def get_template(self) -> WorldStateTemplate:
        if self._template is None:
            self.load()
        return self._template or WorldStateTemplate()

    def create_from_template(self) -> dict[str, Any]:
        tpl = self.get_template()
        return dict(tpl.persistent_variables)


REGISTRY = WorldStateRegistry()


# Step 51-53: WorldStateManager
class WorldStateManager:
    """ワールド状態変数管理 (Steps 51-53)"""

    def __init__(self, registry: WorldStateRegistry | None = None):
        self.registry = registry or REGISTRY

    def get_phase(self) -> WorldPhase:
        """現在のワールドフェーズを取得する"""
        return self.registry.get_template().current_phase

    def set_phase(self, phase: WorldPhase, engine: Any | None = None) -> None:
        """ワールドフェーズを更新し、イベントを通知する"""
        old_phase = self.get_phase()
        if old_phase != phase:
            self.registry.get_template().current_phase = phase
            if engine:
                # EventBusを通じてフェーズ変更を通知
                from core_framework import EventBus

                EventBus.publish("WORLD_PHASE_CHANGED", {"old": old_phase, "new": phase})

    def get_variable(self, player: Entity, var_name: str, default: Any = None) -> Any:
        """ワールド変数を取得 (Step 52)"""
        if not player:
            return default
        if var_name in player.story_variables:
            return player.story_variables[var_name]
        tpl = self.registry.get_template()
        return tpl.persistent_variables.get(var_name, default)

    def set_variable(
        self, player: Entity, var_name: str, value: Any, engine: Any | None = None
    ) -> None:
        """ワールド変数を更新 (Step 53)"""
        if not player:
            return
        player.story_variables[var_name] = value

    def generate_world_news(self, engine: Any | None = None) -> list[str]:
        """世界イベントニュースの自動生成 (Step 8.1)"""
        import random

        actors = [
            "冒険者『ロキ』",
            "パルミア王室親衛隊",
            "吟遊詩人のルカ",
            "ヴェルニースの炭鉱夫",
            "魔道士組合の斥候",
        ]
        actions = [
            "地下深層のドラゴンを討伐した！",
            "古代遺跡で伝説の遺物を発見した。",
            "隣国の盗賊団を壊滅させた。",
            "街の復興支援を完了した。",
        ]
        festivals = [
            "パルミアで収穫祭が開催されている。",
            "ポート・カプールで大バザールが開幕した。",
            "ノイエルで聖夜祭の準備が始まった。",
        ]

        news_pool = [
            f"【世界通信】{random.choice(actors)}が{random.choice(actions)}",
            f"【風の噂】{random.choice(festivals)}",
        ]
        chosen = random.sample(news_pool, k=min(len(news_pool), 1))
        if engine and hasattr(engine, "log"):
            for n in chosen:
                engine.log(n, (140, 200, 255), level="INFO")
        return chosen

    def get_action_echo(self, player: Entity, faction_id: str = "adventurer_guild") -> str | None:
        """プレイヤー行動の反響（エコー）ダイアログ (Step 8.2)"""
        if not player:
            return None
        rep = player.faction_reputation.get(faction_id, 0)
        if rep >= 50:
            return "市民「君がギルドで大活躍していると噂で聞いたよ。頼もしいね！」"
        elif rep <= -20:
            return "市民「おい…あいつが噂の危険人物じゃないか？ 近寄らないでおこう…」"
        return "市民「旅の冒険者さん、今日も安全に気をつけてね。」"

    def update_location_state(self, player: Entity, location: str, key: str, value: Any) -> None:
        pass

    def update_faction_relation(self, player: Entity, relation_key: str, delta: int) -> None:
        pass

    # Vertical World Extension Methods
    def record_layer_visit(
        self, player: Entity, zone: str, biome: str, depth: int, dimension: str
    ) -> None:
        """レイヤー訪問を記録する"""
        layer_key = f"{zone}:{biome}:{depth}:{dimension}"
        visit_record = {
            "layer": layer_key,
            "zone": zone,
            "biome": biome,
            "depth": depth,
            "dimension": dimension,
            "timestamp": __import__("time").time(),
            "discoveries": [],  # ここで発見したアイテムやイベントを記録
        }

        tpl = self.registry.get_template()
        tpl.player_layer_history.append(visit_record)
        tpl.visited_layers.add(layer_key)

    def get_visited_layers(self) -> set[str]:
        """訪問済みレイヤーのセットを取得"""
        tpl = self.registry.get_template()
        return tpl.visited_layers.copy()

    def is_layer_visited(self, zone: str, biome: str, depth: int, dimension: str) -> bool:
        """指定されたレイヤーが訪問済みかチェック"""
        layer_key = f"{zone}:{biome}:{depth}:{dimension}"
        return layer_key in self.get_visited_layers()

    def add_layer_discovery(
        self,
        zone: str,
        biome: str,
        depth: int,
        dimension: str,
        discovery_type: str,
        discovery_data: Any,
    ) -> None:
        """レイヤー発見を記録"""
        tpl = self.registry.get_template()
        layer_key = f"{zone}:{biome}:{depth}:{dimension}"

        if layer_key not in tpl.layer_discoveries:
            tpl.layer_discoveries[layer_key] = []

        tpl.layer_discoveries[layer_key].append(
            {
                "type": discovery_type,
                "data": discovery_data,
                "timestamp": __import__("time").time(),
            }
        )

    def get_layer_discoveries(
        self, zone: str, biome: str, depth: int, dimension: str
    ) -> list[dict[str, Any]]:
        """レイヤーの発見を取得"""
        tpl = self.registry.get_template()
        layer_key = f"{zone}:{biome}:{depth}:{dimension}"
        return tpl.layer_discoveries.get(layer_key, [])
