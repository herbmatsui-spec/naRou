"""
NPC Relationship Simulation - World State System Integration
Step 17: Integration with world state system
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .engine import RelationshipManager
from .models import InteractionType, RelationshipType


class WorldPhase(Enum):
    """ワールドフェーズ（world_state_systemから複製）"""

    BEGINNING = "BEGINNING"
    AWAKENING = "AWAKENING"
    EXPLORATION = "EXPLORATION"
    CONFRONTATION = "CONFRONTATION"
    CLIMAX = "CLIMAX"
    EPILOGUE = "EPILOGUE"


class WorldEventImpact(Enum):
    """世界イベントの関係への影響タイプ"""

    UNIFYING = "unifying"  # 団結を促す
    DIVIDING = "dividing"  # 分断を招く
    TRAUMATIC = "traumatic"  # トラウマ的
    CELEBRATORY = "celebratory"  # 祝賀的
    CHAOTIC = "chaotic"  # 混沌的
    CALMING = "calming"  # 鎮静的


@dataclass
class WorldRelationshipTrend:
    """世界レベルの関係トレンド"""

    phase: WorldPhase
    global_favorability_avg: float
    global_conflict_level: float
    dominant_relationship_type: RelationshipType
    faction_tension: dict[str, float] = field(default_factory=dict)


@dataclass
class WorldEventRelationshipEffect:
    """世界イベントの関係効果"""

    event_id: str
    event_type: WorldEventImpact
    affected_relationships: list[tuple[str, str, RelationshipType]]
    delta_range: tuple[int, int]  # 最小・最大変化量
    duration_days: int = 7
    description: str = ""


class WorldStateRelationshipIntegration:
    """
    ワールドステートシステムとの統合
    ワールドフェーズによる関係変化のグローバルトレンド、
    世界イベントによる一斉関係変化、関係のワールドステートへのフィードバック
    """

    def __init__(
        self,
        relationship_manager: RelationshipManager,
        world_state_manager: Any | None = None,
    ):
        self.rm = relationship_manager
        self.graph = relationship_manager.graph
        self.world_state_manager = world_state_manager

        # フェーズごとの関係修飾子
        self._phase_modifiers: dict[WorldPhase, dict[RelationshipType, float]] = (
            self._load_phase_modifiers()
        )

        # 世界イベント効果
        self._active_world_events: dict[str, WorldEventRelationshipEffect] = {}
        self._event_history: list[dict[str, Any]] = []

        # トレンド分析バッファ
        self._trend_history: deque = deque(maxlen=100)

        # 統計
        self._stats = {
            "world_events_triggered": 0,
            "relationship_changes_from_world": 0,
            "phase_transitions": 0,
        }

        # 最後のフェーズ
        self._last_phase: WorldPhase | None = None

    def _load_phase_modifiers(self) -> dict[WorldPhase, dict[RelationshipType, float]]:
        """フェーズごとの関係修飾子をロード"""
        return {
            WorldPhase.BEGINNING: {
                RelationshipType.FAVORABILITY: 1.0,
                RelationshipType.FRIENDSHIP: 1.0,
                RelationshipType.ENMITY: 0.8,
                RelationshipType.ROMANCE: 0.8,
                RelationshipType.MENTORSHIP: 1.0,
            },
            WorldPhase.AWAKENING: {
                RelationshipType.FAVORABILITY: 1.1,
                RelationshipType.FRIENDSHIP: 1.2,
                RelationshipType.ENMITY: 0.9,
                RelationshipType.ROMANCE: 1.0,
                RelationshipType.MENTORSHIP: 1.2,
            },
            WorldPhase.EXPLORATION: {
                RelationshipType.FAVORABILITY: 1.0,
                RelationshipType.FRIENDSHIP: 1.1,
                RelationshipType.ENMITY: 1.0,
                RelationshipType.ROMANCE: 1.1,
                RelationshipType.MENTORSHIP: 1.1,
            },
            WorldPhase.CONFRONTATION: {
                RelationshipType.FAVORABILITY: 0.9,
                RelationshipType.FRIENDSHIP: 0.9,
                RelationshipType.ENMITY: 1.5,
                RelationshipType.ROMANCE: 0.8,
                RelationshipType.MENTORSHIP: 1.0,
            },
            WorldPhase.CLIMAX: {
                RelationshipType.FAVORABILITY: 1.2,
                RelationshipType.FRIENDSHIP: 1.3,
                RelationshipType.ENMITY: 2.0,
                RelationshipType.ROMANCE: 1.2,
                RelationshipType.MENTORSHIP: 1.2,
            },
            WorldPhase.EPILOGUE: {
                RelationshipType.FAVORABILITY: 1.1,
                RelationshipType.FRIENDSHIP: 1.2,
                RelationshipType.ENMITY: 0.5,
                RelationshipType.ROMANCE: 1.3,
                RelationshipType.MENTORSHIP: 1.3,
            },
        }

    def update_for_phase(
        self, phase: WorldPhase, player_id: str = "player"
    ) -> dict[str, Any]:
        """フェーズ変更時に呼び出し、関係に影響を与える"""
        results = {}

        if self._last_phase == phase:
            return results

        # フェーズ遷移の記録
        if self._last_phase is not None:
            self._stats["phase_transitions"] += 1

        self._last_phase = phase

        # フェーズ修飾子を取得
        modifiers = self._phase_modifiers.get(phase, {})

        # プレイヤーのすべての関係に修飾子を適用
        relationships = self.rm.get_all_relationships(player_id)

        for target_id, rel_dict in relationships.items():
            for rel_type in rel_dict:
                if rel_type in modifiers:
                    modifier = modifiers[rel_type]
                    # 修飾子が1.0より大きければポジティブな方向、小さければネガティブな方向
                    if modifier > 1.0:
                        delta = int((modifier - 1.0) * 20)  # 最大+20
                    else:
                        delta = int((modifier - 1.0) * -20)  # 最大-20

                    if delta != 0:
                        self.rm.modify_relationship(
                            player_id,
                            target_id,
                            InteractionType.EMOTIONAL_SUPPORT
                            if delta > 0
                            else InteractionType.ARGUMENT,
                            delta,
                        )
                        results[target_id] = results.get(target_id, {})
                        results[target_id][rel_type.value] = delta

        # ワールドステートマネージャーに通知
        if self.world_state_manager:
            try:
                self.world_state_manager.set_variable(
                    None, "relationship_phase_effects", results
                )
            except Exception:
                # TODO: handle exception properly
                pass

        return results

    def trigger_world_event(
        self,
        event_id: str,
        event_type: WorldEventImpact,
        affected_characters: list[str] | None = None,
        magnitude: int = 10,
        duration_days: int = 7,
        description: str = "",
    ) -> WorldEventRelationshipEffect:
        """世界イベントを発動し、関係に影響"""
        self._stats["world_events_triggered"] += 1

        # 影響を受けるキャラクターペアを決定
        if affected_characters is None:
            # すべてのノード間
            affected_characters = list(self.graph.nodes.keys())

        affected_relationships = []

        # イベントタイプに基づく変化量を計算
        if event_type == WorldEventImpact.UNIFYING:
            delta_range = (magnitude // 2, magnitude)
            rel_types = [
                RelationshipType.FAVORABILITY,
                RelationshipType.FRIENDSHIP,
                RelationshipType.MENTORSHIP,
            ]
        elif event_type == WorldEventImpact.DIVIDING:
            delta_range = (-magnitude, -magnitude // 2)
            rel_types = [RelationshipType.ENMITY, RelationshipType.BETRAYAL]
        elif event_type == WorldEventImpact.TRAUMATIC:
            delta_range = (-magnitude * 2, -magnitude)
            rel_types = [
                RelationshipType.ENMITY,
                RelationshipType.BETRAYAL,
                RelationshipType.FAVORABILITY,
            ]
        elif event_type == WorldEventImpact.CELEBRATORY:
            delta_range = (magnitude, magnitude * 2)
            rel_types = [
                RelationshipType.FAVORABILITY,
                RelationshipType.ROMANCE,
                RelationshipType.FRIENDSHIP,
            ]
        elif event_type == WorldEventImpact.CHAOTIC:
            delta_range = (-magnitude, magnitude)  # ランダムな方向
            rel_types = [
                RelationshipType.ENMITY,
                RelationshipType.BETRAYAL,
                RelationshipType.FAVORABILITY,
                RelationshipType.ROMANCE,
            ]
        else:  # CALMING
            delta_range = (magnitude // 2, magnitude)
            rel_types = [RelationshipType.FAVORABILITY, RelationshipType.FRIENDSHIP]

        # 影響を適用
        import random

        for i in range(len(affected_characters)):
            for j in range(i + 1, len(affected_characters)):
                char_a = affected_characters[i]
                char_b = affected_characters[j]

                # 関係エッジが存在する場合のみ
                edges = self.graph.get_edges_between(char_a, char_b)
                if not edges:
                    continue

                for edge in edges:
                    if edge.relationship_type not in rel_types:
                        continue

                    # 変動量を決定
                    if event_type == WorldEventImpact.CHAOTIC:
                        delta = random.randint(delta_range[0], delta_range[1])
                    else:
                        delta = random.randint(delta_range[0], delta_range[1])

                    self.rm.modify_relationship(
                        char_a, char_b, InteractionType.EMOTIONAL_SUPPORT, delta
                    )
                    affected_relationships.append(
                        (char_a, char_b, edge.relationship_type)
                    )
                    self._stats["relationship_changes_from_world"] += 1

        # エフェクトを記録
        effect = WorldEventRelationshipEffect(
            event_id=event_id,
            event_type=event_type,
            affected_relationships=affected_relationships,
            delta_range=delta_range,
            duration_days=duration_days,
            description=description,
        )
        self._active_world_events[event_id] = effect

        # 履歴に記録
        self._event_history.append(
            {
                "event_id": event_id,
                "event_type": event_type.value,
                "timestamp": time.time(),
                "affected_count": len(affected_relationships),
                "description": description,
            }
        )

        return effect

    def calculate_global_trend(
        self, player_id: str = "player"
    ) -> WorldRelationshipTrend:
        """グローバルな関係トレンドを計算"""
        # プレイヤーの関係から平均を計算
        relationships = self.rm.get_all_relationships(player_id)

        favorability_sum = 0
        favorability_count = 0
        conflict_sum = 0
        conflict_count = 0
        rel_type_counts: dict[RelationshipType, int] = defaultdict(int)

        for rel_dict in relationships.values():
            for rel_type, level in rel_dict.items():
                rel_type_counts[rel_type] += 1
                if rel_type == RelationshipType.FAVORABILITY:
                    favorability_sum += level
                    favorability_count += 1
                elif rel_type == RelationshipType.ENMITY:
                    conflict_sum += abs(level)
                    conflict_count += 1

        global_favorability_avg = (
            favorability_sum / favorability_count if favorability_count > 0 else 0.0
        )
        global_conflict_level = (
            conflict_sum / conflict_count if conflict_count > 0 else 0.0
        )

        # 支配的な関係タイプ
        dominant_relationship_type = RelationshipType.FAVORABILITY
        if rel_type_counts:
            dominant_relationship_type = max(
                rel_type_counts, key=lambda x: rel_type_counts[x]
            )

        # フェーズを取得
        current_phase = WorldPhase.BEGINNING
        if self.world_state_manager:
            try:
                phase_str = self.world_state_manager.get_phase().name
                current_phase = WorldPhase(phase_str)
            except (ValueError, AttributeError):
                pass

        trend = WorldRelationshipTrend(
            phase=current_phase,
            global_favorability_avg=global_favorability_avg,
            global_conflict_level=global_conflict_level,
            dominant_relationship_type=dominant_relationship_type,
        )

        # トレンド履歴に記録
        self._trend_history.append(
            {
                "timestamp": time.time(),
                "phase": current_phase.value,
                "favorability_avg": global_favorability_avg,
                "conflict_level": global_conflict_level,
            }
        )

        return trend

    def predict_world_relationship_future(
        self, days_ahead: int = 30, player_id: str = "player"
    ) -> dict[str, Any]:
        """未来の世界関係状態を予測"""
        current_trend = self.calculate_global_trend(player_id)

        # 現在の減衰率に基づく予測
        predicted_favorability = current_trend.global_favorability_avg * (
            1 - 0.001 * days_ahead
        )
        predicted_conflict = current_trend.global_conflict_level * (
            1 - 0.0005 * days_ahead
        )

        # フェーズによる影響
        future_phase = self._predict_future_phase(days_ahead)
        if future_phase:
            phase_modifiers = self._phase_modifiers.get(future_phase, {})
            if RelationshipType.FAVORABILITY in phase_modifiers:
                predicted_favorability *= phase_modifiers[RelationshipType.FAVORABILITY]

        return {
            "days_ahead": days_ahead,
            "predicted_favorability_avg": round(predicted_favorability, 2),
            "predicted_conflict_level": round(predicted_conflict, 2),
            "predicted_phase": future_phase.value if future_phase else None,
            "current_phase": current_trend.phase.value,
        }

    def _predict_future_phase(self, days_ahead: int) -> WorldPhase | None:
        """未来のフェーズを予測（簡易実装）"""
        if self.world_state_manager:
            try:
                current_phase = self.world_state_manager.get_phase()
                # フェーズの順序を定義
                phase_order = list(WorldPhase)
                current_idx = phase_order.index(WorldPhase(current_phase.name))
                # 日数に基づいてフェーズを進める（30日で1フェーズ）
                steps = days_ahead // 30
                future_idx = min(len(phase_order) - 1, current_idx + steps)
                return phase_order[future_idx]
            except (ValueError, AttributeError):
                pass
        return None

    def apply_faction_influence_to_world(self, faction_system: Any) -> dict[str, Any]:
        """派閥影響を世界状態に適用"""
        if not faction_system:
            return {}

        results = {}

        # 派閥間の対立をワールドステートにフィードバック
        conflicts = faction_system.check_faction_conflicts()
        for conflict in conflicts:
            faction_a = conflict["faction_a"]
            faction_b = conflict["faction_b"]
            severity = conflict["severity"]

            key = f"faction_conflict_{faction_a}_{faction_b}"
            results[key] = {
                "severity": severity,
                "relation_type": conflict["relation_type"],
            }

            if self.world_state_manager:
                try:
                    self.world_state_manager.set_variable(None, key, severity)
                except Exception:
                    # TODO: handle exception properly
                    pass

        return results

    def get_world_state_summary(self, player_id: str = "player") -> dict[str, Any]:
        """世界状態の関係サマリーを取得"""
        trend = self.calculate_global_trend(player_id)

        return {
            "current_phase": trend.phase.value,
            "global_favorability_avg": round(trend.global_favorability_avg, 2),
            "global_conflict_level": round(trend.global_conflict_level, 2),
            "dominant_relationship_type": trend.dominant_relationship_type.value,
            "active_world_events": len(self._active_world_events),
            "total_world_events": len(self._event_history),
            "phase_transitions": self._stats["phase_transitions"],
        }

    def get_integration_statistics(self) -> dict[str, Any]:
        """統合統計を取得"""
        return {
            **self._stats,
            "active_world_events": len(self._active_world_events),
            "trend_history_size": len(self._trend_history),
        }

    def serialize(self) -> dict[str, Any]:
        """統合状態をシリアライズ"""
        return {
            "active_world_events": {
                eid: {
                    "event_id": effect.event_id,
                    "event_type": effect.event_type.value,
                    "affected_relationships": [
                        (a, b, rt.value) for a, b, rt in effect.affected_relationships
                    ],
                    "delta_range": effect.delta_range,
                    "duration_days": effect.duration_days,
                    "description": effect.description,
                }
                for eid, effect in self._active_world_events.items()
            },
            "event_history": self._event_history[-50:],  # 最新50件
            "last_phase": self._last_phase.value if self._last_phase else None,
            "stats": self._stats,
        }

    def deserialize(self, data: dict[str, Any]) -> None:
        """統合状態をデシリアライズ"""
        self._active_world_events.clear()
        self._event_history = data.get("event_history", [])
        self._last_phase = (
            WorldPhase(data["last_phase"]) if data.get("last_phase") else None
        )
        self._stats = data.get("stats", self._stats)

        for eid, effect_data in data.get("active_world_events", {}).items():
            affected = [
                (a, b, RelationshipType(rt))
                for a, b, rt in effect_data["affected_relationships"]
            ]
            self._active_world_events[eid] = WorldEventRelationshipEffect(
                event_id=effect_data["event_id"],
                event_type=WorldEventImpact(effect_data["event_type"]),
                affected_relationships=affected,
                delta_range=tuple(effect_data["delta_range"]),
                duration_days=effect_data["duration_days"],
                description=effect_data.get("description", ""),
            )
