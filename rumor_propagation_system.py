"""
Rumor Propagation System Module (偏執的クエストシステム / 設計書 Phase 2 Step 6)
噂伝播エンジン：距離減衰・親密度・派閥フィルタによる情報拡散。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from entity import Entity
    from game import Engine
    from world_map_manager import WorldMapManager


class RumorType(Enum):
    """噂の種類"""

    QUEST_SUCCESS = auto()  # クエスト成功
    QUEST_FAILURE = auto()  # クエスト失敗
    PLAYER_ACTION = auto()  # プレイヤーの特定行動（殺人・窃盗・英雄的行為等）
    FACTION_MOVE = auto()  # 派閥の動き（領土拡大・同盟・抗争）
    WORLD_EVENT = auto()  # ワールドイベント（祭り・蝕・流星群）
    NPC_SECRET = auto()  # NPCの秘密・弱点
    TREASURE_LOCATION = auto()  # 財宝・ダンジョン情報
    MARKET_PRICE = auto()  # 物価変動情報


@dataclass
class Rumor:
    """噂エントリ"""

    rumor_id: str
    rumor_type: RumorType
    content: dict[str, Any]  # 噂の具体的内容
    origin_npc_id: str  # 発信元 NPC
    origin_location: tuple[int, int]  # 発生座標
    timestamp: float
    base_credibility: float = 1.0  # 基本信憑性（0-1）
    tags: set[str] = field(default_factory=set)
    # 伝播状態
    known_by: set[str] = field(default_factory=set)  # 知っている NPC ID 集合
    propagation_count: int = 0  # 伝播回数

    def credibility_for(self, listener: Entity, engine: Engine) -> float:
        """特定リスナーに対する実効信憑性を計算"""
        # 基本信憑性
        cred = self.base_credibility
        # 発信元との関係性で補正
        rel_mgr = (
            engine.relationship_manager
            if hasattr(engine, "relationship_manager")
            else None
        )
        if rel_mgr:
            rel_level = rel_mgr.get_relationship_level(listener, self.origin_npc_id)
            # 関係レベル: 0=他人, 1=知り合い, 2=友人, 3=親友
            cred *= 0.5 + rel_level * 0.15  # 0.5-0.95
        # 同派閥なら信憑性アップ
        # 派閥システムとの連携は実装時に
        return min(1.0, max(0.0, cred))


@dataclass
class RumorPropagationConfig:
    """伝播設定"""

    max_distance: float = 50.0  # 最大伝播距離（タイル）
    base_decay_per_tile: float = 0.02  # タイルごとの減衰
    intimacy_bonus: float = 0.1  # 親密度ボーナス（関係レベル×）
    faction_same_bonus: float = 0.2  # 同派閥ボーナス
    faction_rival_penalty: float = 0.3  # 敵対派閥ペナルティ
    max_propagation_hops: int = 5  # 最大伝播ホップ数
    min_credibility_to_spread: float = 0.2  # これ未満なら伝播しない
    rumor_lifetime: float = 86400.0  # 噂の寿命（秒、24時間）


class RumorEngine:
    """噂伝播エンジン"""

    def __init__(
        self,
        engine: Engine,
        config: RumorPropagationConfig | None = None,
        world_map: WorldMapManager | None = None,
    ):
        self.engine = engine
        self.config = config or RumorPropagationConfig()
        self.world_map = world_map
        self._rumors: dict[str, Rumor] = {}
        self._npc_locations: dict[str, tuple[int, int]] = {}  # NPC ID -> (x, y)
        self._npc_factions: dict[str, str] = {}  # NPC ID -> faction_id

    def register_npc(
        self, npc: Entity, location: tuple[int, int], faction_id: str | None = None
    ) -> None:
        """NPC を伝播ネットワークに登録"""
        self._npc_locations[npc.name] = location
        if faction_id:
            self._npc_factions[npc.name] = faction_id

    def unregister_npc(self, npc_id: str) -> None:
        self._npc_locations.pop(npc_id, None)
        self._npc_factions.pop(npc_id, None)

    def create_rumor(
        self,
        rumor_type: RumorType,
        content: dict[str, Any],
        origin_npc: Entity,
        origin_location: tuple[int, int],
        base_credibility: float = 1.0,
        tags: set[str] | None = None,
    ) -> Rumor:
        """新しい噂を生成・登録"""
        rumor_id = f"{rumor_type.name.lower()}_{origin_npc.name}_{int(time.time() * 1000) % 1000000}"
        rumor = Rumor(
            rumor_id=rumor_id,
            rumor_type=rumor_type,
            content=content,
            origin_npc_id=origin_npc.name,
            origin_location=origin_location,
            timestamp=time.time(),
            base_credibility=base_credibility,
            tags=tags or set(),
        )
        rumor.known_by.add(origin_npc.name)
        self._rumors[rumor_id] = rumor
        # 発信元の記憶にも記録
        from npc_memory_system import (
            GLOBAL_MEMORY_REGISTRY,
            MemoryImportance,
        )

        mgr = GLOBAL_MEMORY_REGISTRY.get(origin_npc)
        mgr.record_reputation_event(
            subject_id=origin_npc.name,
            event_type=f"rumor_created:{rumor_type.name}",
            delta=1,
            source="self",
            importance=MemoryImportance.NOTABLE,
        )
        return rumor

    def _distance(self, loc1: tuple[int, int], loc2: tuple[int, int]) -> float:
        """距離計算（ワールドマップがあれば経路距離、なければチェビシェフ距離）"""
        if self.world_map:
            # TODO: WorldMapManager に経路探索があれば使用
            pass
        return max(abs(loc1[0] - loc2[0]), abs(loc1[1] - loc2[1]))

    def _relationship_level(self, npc1_id: str, npc2_id: str) -> int:
        """2 NPC 間の関係レベル取得（0-3）"""
        rel_mgr = getattr(self.engine, "relationship_manager", None)
        if rel_mgr:
            # npc1 が npc2 をどう見ているか
            npc1 = self._find_entity(npc1_id)
            if npc1:
                return rel_mgr.get_relationship_level(npc1, npc2_id)
        return 0

    def _faction_relation(self, npc1_id: str, npc2_id: str) -> float:
        """派閥関係係数（同盟=+1, 中立=0, 敵対=-1）"""
        f1 = self._npc_factions.get(npc1_id)
        f2 = self._npc_factions.get(npc2_id)
        if not f1 or not f2:
            return 0.0
        if f1 == f2:
            return 1.0
        fw_mgr = getattr(self.engine, "faction_war_manager", None)
        if fw_mgr and fw_mgr.check_war_conditions(f1, f2):
            return -1.0
        # 同盟チェック
        from faction_war_system import REGISTRY as FW_REG

        fw_data1 = FW_REG.get(f1)
        if fw_data1 and f2 in fw_data1.allied_factions:
            return 1.0
        return 0.0

    def _find_entity(self, npc_id: str) -> Entity | None:
        """エンジンから NPC を検索"""
        if hasattr(self.engine, "entity_manager"):
            for e in self.engine.entity_manager.get_all_entities():
                if e.name == npc_id:
                    return e
        return None

    def propagate_step(self, current_time: float | None = None) -> int:
        """伝播ステップ実行（1ターン/1フレームごとに呼ぶ）。新規伝播数を返す。"""
        current_time = current_time or time.time()
        new_spreads = 0

        # 期限切れ噂を削除
        expired = [
            rid
            for rid, r in self._rumors.items()
            if current_time - r.timestamp > self.config.rumor_lifetime
        ]
        for rid in expired:
            del self._rumors[rid]

        # 伝播処理
        for rumor in list(self._rumors.values()):
            if rumor.propagation_count >= self.config.max_propagation_hops:
                continue

            origin_loc = self._npc_locations.get(rumor.origin_npc_id)
            if not origin_loc:
                continue

            # 既知者から未知者へ伝播
            for knower_id in list(rumor.known_by):
                knower_loc = self._npc_locations.get(knower_id)
                if not knower_loc:
                    continue

                # 周囲の NPC を候補に
                for listener_id, listener_loc in self._npc_locations.items():
                    if listener_id in rumor.known_by:
                        continue

                    # 距離チェック
                    dist = self._distance(knower_loc, listener_loc)
                    if dist > self.config.max_distance:
                        continue

                    # 伝播確率計算
                    prob = self._calculate_spread_probability(
                        rumor, knower_id, listener_id, dist
                    )
                    if prob <= self.config.min_credibility_to_spread:
                        continue

                    if random.random() < prob:
                        rumor.known_by.add(listener_id)
                        rumor.propagation_count += 1
                        new_spreads += 1

                        # 受信者の記憶に記録
                        listener = self._find_entity(listener_id)
                        if listener:
                            from npc_memory_system import (
                                GLOBAL_MEMORY_REGISTRY,
                                MemoryImportance,
                            )

                            mgr = GLOBAL_MEMORY_REGISTRY.get(listener)
                            mgr.record_reputation_event(
                                subject_id=rumor.origin_npc_id,
                                event_type=f"rumor:{rumor.rumor_type.name}",
                                delta=int(rumor.base_credibility * 10),
                                source=knower_id,
                                importance=MemoryImportance.NOTABLE,
                            )
        return new_spreads

    def _calculate_spread_probability(
        self,
        rumor: Rumor,
        from_id: str,
        to_id: str,
        distance: float,
    ) -> float:
        """伝播確率計算"""
        prob = rumor.base_credibility

        # 距離減衰
        prob *= max(0.0, 1.0 - distance * self.config.base_decay_per_tile)

        # 親密度ボーナス（from -> to の関係）
        rel = self._relationship_level(from_id, to_id)
        prob += rel * self.config.intimacy_bonus

        # 派閥関係
        fac_rel = self._faction_relation(from_id, to_id)
        if fac_rel > 0:
            prob += self.config.faction_same_bonus
        elif fac_rel < 0:
            prob -= self.config.faction_rival_penalty

        # ホップ数ペナルティ
        prob *= max(0.3, 1.0 - rumor.propagation_count * 0.15)

        return min(1.0, max(0.0, prob))

    def get_rumors_known_by(self, npc_id: str) -> list[Rumor]:
        """特定 NPC が知っている噂一覧"""
        return [r for r in self._rumors.values() if npc_id in r.known_by]

    def get_rumors_about(self, subject_id: str) -> list[Rumor]:
        """特定対象に関する噂一覧"""
        results = []
        for r in self._rumors.values():
            # content に subject_id が含まれるか、origin が対象
            if r.origin_npc_id == subject_id or subject_id in str(r.content):
                results.append(r)
        return results

    def query_rumors(
        self,
        npc_id: str,
        rumor_type: RumorType | None = None,
        min_credibility: float = 0.0,
    ) -> list[Rumor]:
        """NPC が知る噂をフィルタ"""
        results = self.get_rumors_known_by(npc_id)
        if rumor_type:
            results = [r for r in results if r.rumor_type == rumor_type]
        if min_credibility > 0:
            npc = self._find_entity(npc_id)
            results = [
                r
                for r in results
                if r.credibility_for(npc, self.engine) >= min_credibility
            ]
        return results

    def inject_rumor_for_quest(
        self,
        quest_id: str,
        success: bool,
        origin_npc: Entity,
        location: tuple[int, int],
    ) -> Rumor:
        """クエスト結果から噂を自動生成（Phase 3 連携用）"""
        rtype = RumorType.QUEST_SUCCESS if success else RumorType.QUEST_FAILURE
        return self.create_rumor(
            rumor_type=rtype,
            content={"quest_id": quest_id, "success": success},
            origin_npc=origin_npc,
            origin_location=location,
            base_credibility=0.8 if success else 0.6,
            tags={"quest", quest_id},
        )

    def get_active_rumor_count(self) -> int:
        return len(self._rumors)


import time  # Rumor.timestamp 用

__all__ = [
    "Rumor",
    "RumorEngine",
    "RumorPropagationConfig",
    "RumorType",
]
