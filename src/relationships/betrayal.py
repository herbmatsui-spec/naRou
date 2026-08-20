"""
NPC Relationship Simulation - Betrayal and Conflict Mechanics
Step 11: Betrayal and conflict mechanics
"""

from __future__ import annotations

import random
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .engine import RelationshipManager
from .models import FactionAffiliation, InteractionType, RelationshipType


class BetrayalType(Enum):
    """裏切りのタイプ"""

    INFORMATION_LEAK = "information_leak"  # 情報漏洩
    ASSET_THEFT = "asset_theft"  # 資産奪取
    BACKSTAB = "backstab"  # 背後からの攻撃
    FALSE_ALLIANCE = "false_alliance"  # 偽りの同盟
    ABANDONMENT = "abandonment"  # 見捨て
    SABOTAGE = "sabotage"  # 妨害工作
    DEFECTION = "defection"  # 寝返り


class ConflictState(Enum):
    """対立状態"""

    PEACEFUL = "peaceful"  # 平和
    TENSE = "tense"  # 緊張
    HOSTILE = "hostile"  # 敵対
    OPEN_CONFLICT = "open_conflict"  # 正面衝突
    WAR = "war"  # 戦争
    RECONCILED = "reconciled"  # 和解済み


@dataclass
class BetrayalRecord:
    """裏切り記録"""

    betrayer_id: str
    victim_id: str
    betrayal_type: BetrayalType
    timestamp: float
    severity: int  # 1〜10
    evidence_available: bool
    witnesses: list[str] = field(default_factory=list)
    resolved: bool = False
    consequences: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConflictRecord:
    """対立記録"""

    party_a: str
    party_b: str
    state: ConflictState
    intensity: int  # 0〜100
    triggers: list[str] = field(default_factory=list)
    escalation_history: list[dict[str, Any]] = field(default_factory=list)
    last_escalation: float | None = None
    reconciliation_attempts: int = 0


class BetrayalConflictSystem:
    """
    裏切りと対立メカニズム
    裏切りイベント、復讐システム、和解の可能性を管理
    """

    def __init__(self, relationship_manager: RelationshipManager):
        self.rm = relationship_manager
        self.graph = relationship_manager.graph

        # 裏切り記録のストレージ
        self.betrayal_records: list[BetrayalRecord] = []
        self.betrayal_by_victim: dict[str, list[BetrayalRecord]] = defaultdict(list)

        # 対立記録のストレージ
        self.conflict_records: dict[tuple[str, str], ConflictRecord] = {}

        # 復讐システム
        self.revenge_queue: list[dict[str, Any]] = []
        self.revenge_cooldowns: dict[str, float] = {}

        # 設定
        self._config = self._load_betrayal_config()

        # イベントハンドラー
        self._event_handlers: dict[str, list[Callable[..., Any]]] = defaultdict(list)

        # 統計
        self._stats = {
            "total_betrayals": 0,
            "successful_reconciliations": 0,
            "revenge_acts": 0,
            "wars_started": 0,
        }

    def _load_betrayal_config(self) -> dict[str, Any]:
        """裏切り・対立設定をロード"""
        return {
            "betrayal_severity_weights": {
                BetrayalType.INFORMATION_LEAK: 3,
                BetrayalType.ASSET_THEFT: 5,
                BetrayalType.BACKSTAB: 8,
                BetrayalType.FALSE_ALLIANCE: 6,
                BetrayalType.ABANDONMENT: 4,
                BetrayalType.SABOTAGE: 7,
                BetrayalType.DEFECTION: 9,
            },
            "revenge_threshold": 50,  # 復讐を考慮する関係悪化レベル
            "revenge_cooldown": 86400,  # 復讐のクールダウン（秒）
            "reconciliation_base_chance": 0.3,
            "trust_recovery_rate": 0.01,
            "conflict_decay": 0.0005,
            "witness_impact_multiplier": 1.5,
        }

    def commit_betrayal(
        self,
        betrayer_id: str,
        victim_id: str,
        betrayal_type: BetrayalType,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """裏切りを実行"""
        context = context or {}

        # 裏切りの深刻度を計算
        base_severity = self._config["betrayal_severity_weights"].get(betrayal_type, 5)

        # 証拠と目撃者の影響
        evidence = context.get("evidence_available", random.random() < 0.5)
        witnesses = context.get("witnesses", [])
        witness_multiplier = 1.0 + (len(witnesses) * 0.1)

        severity = int(base_severity * witness_multiplier)

        # 影響量を計算（関係悪化）
        impact = -severity * 5  # 各severityポイントで-5

        # 関係タイプに応じて影響を適用
        betrayal_impact = {}

        # 裏切り関係のレベルを大幅に下げる
        self.rm.modify_relationship(
            betrayer_id, victim_id, InteractionType.BETRAYAL, impact
        )
        betrayal_impact["betrayal_level"] = self.rm.get_relationship_level(
            betrayer_id, victim_id, RelationshipType.BETRAYAL
        )

        # 好感度も低下
        self.rm.modify_relationship(
            betrayer_id, victim_id, InteractionType.BETRAYAL, impact // 2
        )
        betrayal_impact["favorability"] = self.rm.get_relationship_level(
            betrayer_id, victim_id, RelationshipType.FAVORABILITY
        )

        # 敵対関係を強化
        self.rm.modify_relationship(
            betrayer_id, victim_id, InteractionType.COMBAT_ENEMY, impact // 3
        )

        # 記録を作成
        record = BetrayalRecord(
            betrayer_id=betrayer_id,
            victim_id=victim_id,
            betrayal_type=betrayal_type,
            timestamp=time.time(),
            severity=severity,
            evidence_available=evidence,
            witnesses=witnesses,
            consequences=betrayal_impact,
        )
        self.betrayal_records.append(record)
        self.betrayal_by_victim[victim_id].append(record)

        self._stats["total_betrayals"] += 1

        # 対立状態を更新
        self._update_conflict_state(
            betrayer_id, victim_id, ConflictState.HOSTILE, "betrayal"
        )

        # 復讐の可能性をチェック
        revenge_triggered = self._check_revenge_trigger(
            victim_id, betrayer_id, severity
        )

        # イベント発行
        self._emit_event("betrayal_committed", record)

        return {
            "success": True,
            "betrayal_record": record,
            "impact": betrayal_impact,
            "revenge_triggered": revenge_triggered,
            "conflict_state": self.get_conflict_state(betrayer_id, victim_id),
        }

    def _check_revenge_trigger(
        self, victim_id: str, betrayer_id: str, severity: int
    ) -> bool:
        """復讐トリガーをチェック"""
        # 深刻な裏切りで、クールダウン中でない場合
        current_time = time.time()
        if victim_id in self.revenge_cooldowns and (
            current_time - self.revenge_cooldowns[victim_id]
            < self._config["revenge_cooldown"]
        ):
            return False

        # 復讐の深刻度しきい値
        if severity >= 6:
            self.revenge_queue.append(
                {
                    "avenger_id": victim_id,
                    "target_id": betrayer_id,
                    "intensity": severity,
                    "timestamp": current_time,
                }
            )
            self.revenge_cooldowns[victim_id] = current_time
            return True

        return False

    def execute_revenge(
        self, avenger_id: str, target_id: str, method: str = "direct"
    ) -> dict[str, Any]:
        """復讐を実行"""
        # 復讐キューから該当エントリーを検索
        revenge_entry = None
        for entry in self.revenge_queue:
            if entry["avenger_id"] == avenger_id and entry["target_id"] == target_id:
                revenge_entry = entry
                break

        if not revenge_entry:
            return {"success": False, "reason": "no_revenge_plan"}

        intensity = revenge_entry["intensity"]

        # 復讐の影響（裏切りより少し軽い）
        impact = -intensity * 3

        # 相互の関係をさらに悪化
        self.rm.modify_relationship(
            avenger_id, target_id, InteractionType.COMBAT_ENEMY, impact
        )
        self.rm.modify_relationship(
            target_id, avenger_id, InteractionType.COMBAT_ENEMY, impact // 2
        )

        # 対立状態をエスカレート
        self._update_conflict_state(
            avenger_id, target_id, ConflictState.OPEN_CONFLICT, "revenge"
        )

        # 復讐キューから削除
        self.revenge_queue.remove(revenge_entry)
        self._stats["revenge_acts"] += 1

        # イベント発行
        self._emit_event(
            "revenge_executed",
            {
                "avenger_id": avenger_id,
                "target_id": target_id,
                "method": method,
                "intensity": intensity,
                "timestamp": time.time(),
            },
        )

        return {
            "success": True,
            "impact": impact,
            "conflict_state": self.get_conflict_state(avenger_id, target_id),
        }

    def attempt_reconciliation(
        self,
        party_a: str,
        party_b: str,
        mediator_id: str | None = None,
        sincerity: float = 0.5,
    ) -> dict[str, Any]:
        """和解を試みる"""
        # 対立状態を確認
        conflict = self.get_conflict_record(party_a, party_b)
        if not conflict:
            return {"success": False, "reason": "no_conflict"}

        if conflict.state == ConflictState.RECONCILED:
            return {"success": False, "reason": "already_reconciled"}

        # 和解の成功確率を計算
        base_chance = self._config["reconciliation_base_chance"]

        # 仲介者の影響
        mediator_bonus = 0.2 if mediator_id else 0.0

        # 真摯さの影響
        sincerity_bonus = (sincerity - 0.5) * 0.4

        # 対立の激しさによるペナルティ
        intensity_penalty = conflict.intensity / 200.0  # 0-0.5

        # 過去の和解試行回数によるペナルティ
        attempt_penalty = conflict.reconciliation_attempts * 0.05

        success_chance = (
            base_chance
            + mediator_bonus
            + sincerity_bonus
            - intensity_penalty
            - attempt_penalty
        )
        success_chance = max(0.05, min(0.95, success_chance))

        conflict.reconciliation_attempts += 1

        success = random.random() < success_chance

        if success:
            # 関係を改善
            improvement = int(conflict.intensity * 0.4)
            self.rm.modify_relationship(
                party_a, party_b, InteractionType.EMOTIONAL_SUPPORT, improvement
            )
            self.rm.modify_relationship(
                party_a, party_b, InteractionType.EMOTIONAL_SUPPORT, improvement // 2
            )

            # 対立状態を和解済みに
            self._update_conflict_state(
                party_a, party_b, ConflictState.RECONCILED, "reconciliation"
            )

            self._stats["successful_reconciliations"] += 1

            # イベント発行
            self._emit_event(
                "reconciliation_success",
                {
                    "party_a": party_a,
                    "party_b": party_b,
                    "mediator_id": mediator_id,
                    "timestamp": time.time(),
                },
            )

            return {
                "success": True,
                "improvement": improvement,
                "conflict_state": self.get_conflict_state(party_a, party_b),
            }
        else:
            # 和解失敗：関係はさらに悪化する可能性
            if random.random() < 0.3:
                self.rm.modify_relationship(
                    party_a, party_b, InteractionType.ARGUMENT, -10
                )
                self._update_conflict_state(
                    party_a, party_b, ConflictState.HOSTILE, "failed_reconciliation"
                )

            # イベント発行
            self._emit_event(
                "reconciliation_failed",
                {
                    "party_a": party_a,
                    "party_b": party_b,
                    "mediator_id": mediator_id,
                    "timestamp": time.time(),
                },
            )

            return {
                "success": False,
                "reason": "reconciliation_rejected",
                "conflict_state": self.get_conflict_state(party_a, party_b),
            }

    def _update_conflict_state(
        self, party_a: str, party_b: str, new_state: ConflictState, trigger: str
    ) -> ConflictRecord:
        """対立状態を更新"""
        key = tuple(sorted([party_a, party_b]))

        if key not in self.conflict_records:
            record = ConflictRecord(
                party_a=party_a,
                party_b=party_b,
                state=ConflictState.PEACEFUL,
                intensity=0,
            )
            self.conflict_records[key] = record

        record = self.conflict_records[key]

        # 状態が変わる場合のみ記録
        if record.state != new_state:
            old_state = record.state
            record.state = new_state

            # エスカレーション
            escalation = {
                "from": old_state.value,
                "to": new_state.value,
                "trigger": trigger,
                "timestamp": time.time(),
            }
            record.escalation_history.append(escalation)
            record.last_escalation = time.time()

            # 強度を更新
            intensity_delta = self._calculate_intensity_delta(new_state)
            record.intensity = max(0, min(100, record.intensity + intensity_delta))

            # 戦争開始の記録
            if new_state == ConflictState.WAR:
                self._stats["wars_started"] += 1

        return record

    def _calculate_intensity_delta(self, state: ConflictState) -> int:
        """対立状態から強度の変化量を計算"""
        deltas = {
            ConflictState.PEACEFUL: -10,
            ConflictState.TENSE: 10,
            ConflictState.HOSTILE: 20,
            ConflictState.OPEN_CONFLICT: 30,
            ConflictState.WAR: 40,
            ConflictState.RECONCILED: -30,
        }
        return deltas.get(state, 0)

    def get_conflict_state(self, party_a: str, party_b: str) -> str | None:
        """対立状態を取得"""
        record = self.get_conflict_record(party_a, party_b)
        return record.state.value if record else None

    def get_conflict_record(self, party_a: str, party_b: str) -> ConflictRecord | None:
        """対立記録を取得"""
        key = tuple(sorted([party_a, party_b]))
        return self.conflict_records.get(key)

    def get_betrayals_against(self, victim_id: str) -> list[BetrayalRecord]:
        """特定のキャラクターに対する裏切り記録を取得"""
        return self.betrayal_by_victim.get(victim_id, [])

    def calculate_trust_recovery(
        self, party_a: str, party_b: str, days_passed: float = 1.0
    ) -> int:
        """信頼の回復を計算・適用"""
        record = self.get_conflict_record(party_a, party_b)
        if not record:
            return 0

        # 和解済みの場合のみ回復
        if record.state != ConflictState.RECONCILED:
            return 0

        recovery = int(self._config["trust_recovery_rate"] * days_passed * 100)
        if recovery > 0:
            self.rm.modify_relationship(
                party_a, party_b, InteractionType.EMOTIONAL_SUPPORT, recovery
            )
            self.rm.modify_relationship(
                party_a, party_b, InteractionType.EMOTIONAL_SUPPORT, recovery
            )

            # 強度を減少
            record.intensity = max(0, record.intensity - recovery)

            # 完全に平和になったら記録を更新
            if record.intensity <= 10:
                record.state = ConflictState.PEACEFUL
                record.intensity = 0

        return recovery

    def spread_rumor(
        self,
        source_id: str,
        target_id: str,
        rumor_type: str = "betrayal",
        credibility: float = 0.5,
    ) -> dict[str, Any]:
        """噂を広める（評判への影響）"""
        # 噂の影響を計算
        impact = int(credibility * 15)

        # ターゲットの評判を低下（FactionAffiliationを使用）
        target_node = self.graph.get_node(target_id)
        if not target_node:
            return {"success": False, "reason": "target_not_found"}

        # 噂を広める側の派閥所属を考慮
        spread_effect = self._calculate_rumor_spread(source_id, target_id, rumor_type)

        affected = []
        for other_id in self.graph.nodes:
            if other_id in [source_id, target_id]:
                continue

            edge = self.graph.get_edge(
                other_id, target_id, RelationshipType.FAVORABILITY
            )
            if edge:
                edge.add_modifier(
                    self.rm._create_modifier(
                        InteractionType.BETRAYAL, -impact * spread_effect
                    )
                )
                affected.append(other_id)

        return {
            "success": True,
            "affected_count": len(affected),
            "impact_per_person": -impact * spread_effect,
        }

    def _calculate_rumor_spread(
        self, source_id: str, target_id: str, rumor_type: str
    ) -> float:
        """噂の拡散効果を計算"""
        # 基本係数
        multiplier = 1.0

        # 噂のタイプによる調整
        type_multipliers = {
            "betrayal": 1.5,
            "scandal": 1.2,
            "achievement": 0.8,
            "death": 2.0,
        }
        multiplier *= type_multipliers.get(rumor_type, 1.0)

        # ソースの影響力（派閥所属による）
        source_node = self.graph.get_node(source_id)
        if source_node:
            for affiliation in source_node.faction_affiliations.values():
                if affiliation in [FactionAffiliation.LEADER, FactionAffiliation.ELDER]:
                    multiplier *= 1.3

        return multiplier

    def register_event_handler(
        self, event_type: str, handler: Callable[..., Any]
    ) -> None:
        """イベントハンドラーを登録"""
        self._event_handlers[event_type].append(handler)

    def _emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        """イベントを発行"""
        for handler in self._event_handlers.get(event_type, []):
            try:
                handler(event_type, data)
            except Exception as e:
                print(f"Error in betrayal event handler: {e}")

    def get_betrayal_statistics(self) -> dict[str, Any]:
        """裏切り・対立統計を取得"""
        return {
            **self._stats,
            "active_conflicts": len(
                [
                    r
                    for r in self.conflict_records.values()
                    if r.state not in [ConflictState.PEACEFUL, ConflictState.RECONCILED]
                ]
            ),
            "pending_revenge": len(self.revenge_queue),
            "total_betrayal_records": len(self.betrayal_records),
        }

    def serialize(self) -> dict[str, Any]:
        """状態をシリアライズ"""
        return {
            "betrayal_records": [
                {
                    "betrayer_id": r.betrayer_id,
                    "victim_id": r.victim_id,
                    "betrayal_type": r.betrayal_type.value,
                    "timestamp": r.timestamp,
                    "severity": r.severity,
                    "evidence_available": r.evidence_available,
                    "witnesses": r.witnesses,
                    "resolved": r.resolved,
                    "consequences": r.consequences,
                }
                for r in self.betrayal_records
            ],
            "conflict_records": {
                f"{a}_{b}": {
                    "party_a": r.party_a,
                    "party_b": r.party_b,
                    "state": r.state.value,
                    "intensity": r.intensity,
                    "triggers": r.triggers,
                    "escalation_history": r.escalation_history,
                    "reconciliation_attempts": r.reconciliation_attempts,
                }
                for (a, b), r in self.conflict_records.items()
            },
            "revenge_queue": self.revenge_queue,
            "stats": self._stats,
        }

    def deserialize(self, data: dict[str, Any]) -> None:
        """状態をデシリアライズ"""
        self.betrayal_records.clear()
        self.betrayal_by_victim.clear()

        for r_data in data.get("betrayal_records", []):
            record = BetrayalRecord(
                betrayer_id=r_data["betrayer_id"],
                victim_id=r_data["victim_id"],
                betrayal_type=BetrayalType(r_data["betrayal_type"]),
                timestamp=r_data["timestamp"],
                severity=r_data["severity"],
                evidence_available=r_data["evidence_available"],
                witnesses=r_data.get("witnesses", []),
                resolved=r_data.get("resolved", False),
                consequences=r_data.get("consequences", {}),
            )
            self.betrayal_records.append(record)
            self.betrayal_by_victim[record.victim_id].append(record)

        self.conflict_records.clear()
        for r_data in data.get("conflict_records", {}).values():
            record = ConflictRecord(
                party_a=r_data["party_a"],
                party_b=r_data["party_b"],
                state=ConflictState(r_data["state"]),
                intensity=r_data["intensity"],
                triggers=r_data.get("triggers", []),
                escalation_history=r_data.get("escalation_history", []),
                reconciliation_attempts=r_data.get("reconciliation_attempts", 0),
            )
            self.conflict_records[tuple(sorted([record.party_a, record.party_b]))] = (
                record
            )

        self.revenge_queue = data.get("revenge_queue", [])
        self._stats = data.get("stats", self._stats)
