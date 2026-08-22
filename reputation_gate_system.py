"""
Reputation Gate System Module (偏執的クエストシステム / 設計書 Phase 2 Step 7)
評判閾値によるクエスト解放・敵対トリガー。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from entity import Entity
    from game import Engine


class GateAction(Enum):
    """ゲート通過時のアクション"""

    UNLOCK_QUEST = auto()  # クエスト解放
    LOCK_QUEST = auto()  # クエストロック
    TRIGGER_HOSTILE = auto()  # 敵対化
    REMOVE_HOSTILE = auto()  # 敵対解除
    UNLOCK_SHOP = auto()  # 店解放
    UNLOCK_DIALOGUE = auto()  # 会話解放
    GRANT_BUFF = auto()  # バフ付与
    APPLY_DEBUFF = auto()  # デバフ付与
    CUSTOM = auto()  # カスタムコールバック


class ReputationSource(Enum):
    """評判ソース"""

    DIRECT = "direct"  # 直接交流
    RUMOR = "rumor"  # 噂伝播
    FACTION = "faction"  # 派閥影響
    QUEST = "quest"  # クエスト結果
    WORLD_EVENT = "world_event"  # ワールドイベント


@dataclass
class ReputationThreshold:
    """評判閾値定義"""

    threshold: int  # 必要評判値（-100 to 100）
    action: GateAction
    target_id: str  # 対象（クエストID、NPC ID、ショップID等）
    params: dict[str, Any] = field(default_factory=dict)  # アクション固有パラメータ
    description: str = ""  # 説明（UI表示用）
    one_time: bool = True  # 一度だけ発火
    comparison: str = "auto"  # "gte" (以上), "lte" (以下), "auto" (threshold>=0ならgte, <0ならlte)

    def _get_comparison(self) -> str:
        if self.comparison != "auto":
            return self.comparison
        return "lte" if self.threshold < 0 else "gte"

    def check(self, reputation: int) -> bool:
        """評判値が閾値を満たすか判定"""
        cmp = self._get_comparison()
        if cmp == "gte":
            return reputation >= self.threshold
        return reputation <= self.threshold


@dataclass
class FactionReputationGate:
    """派閥評判ゲート（派閥単位）"""

    faction_id: str
    thresholds: list[ReputationThreshold] = field(default_factory=list)
    # 派閥内での相対評判計算用
    base_reputation: int = 0


@dataclass
class NPCReputationGate:
    """個別NPC評判ゲート"""

    npc_id: str
    thresholds: list[ReputationThreshold] = field(default_factory=list)
    base_reputation: int = 0


class ReputationGate:
    """評判ゲートシステム：閾値監視・アクション実行"""

    def __init__(self, engine: Engine):
        self.engine = engine
        self._npc_gates: dict[str, NPCReputationGate] = {}
        self._faction_gates: dict[str, FactionReputationGate] = {}
        self._custom_actions: dict[str, Callable] = {}
        self._fired_gates: set[str] = set()  # 発火済みゲートID（one_time用）

    def register_npc_gate(
        self,
        npc_id: str,
        thresholds: list[ReputationThreshold],
        base_reputation: int = 0,
    ) -> NPCReputationGate:
        """NPC 個別ゲート登録"""
        gate = NPCReputationGate(
            npc_id=npc_id, thresholds=thresholds, base_reputation=base_reputation
        )
        self._npc_gates[npc_id] = gate
        return gate

    def register_faction_gate(
        self,
        faction_id: str,
        thresholds: list[ReputationThreshold],
        base_reputation: int = 0,
    ) -> FactionReputationGate:
        """派閥ゲート登録"""
        gate = FactionReputationGate(
            faction_id=faction_id,
            thresholds=thresholds,
            base_reputation=base_reputation,
        )
        self._faction_gates[faction_id] = gate
        return gate

    def register_custom_action(self, name: str, func: Callable) -> None:
        """カスタムアクション登録"""
        self._custom_actions[name] = func

    def get_npc_reputation(self, player: Entity, npc_id: str) -> int:
        """プレイヤーから見た NPC への評判取得（関係システム連携）"""
        # 直接 character_relationships から trust 取得（最優先）
        rel = player.character_relationships.get(npc_id, {})
        trust = rel.get("trust", 0)
        base = self._npc_gates.get(npc_id, NPCReputationGate(npc_id)).base_reputation
        return base + trust

    def get_faction_reputation(self, player: Entity, faction_id: str) -> int:
        """プレイヤーの派閥評判取得"""
        # GuildFactionComponent 経由
        rep = player.faction_reputation.get(faction_id, 0)
        # 派閥影響力も加味（派閥マネージャー経由）
        base = self._faction_gates.get(
            faction_id, FactionReputationGate(faction_id)
        ).base_reputation
        fw_mgr = getattr(self.engine, "faction_war_manager", None)
        if fw_mgr and hasattr(fw_mgr, "registry"):
            faction_data = fw_mgr.registry.get(faction_id)
            if faction_data:
                # 派閥影響力 0-100 を -50 to 50 にマッピングして加算
                base += faction_data.influence - 50
        return base + rep

    def evaluate_npc_gates(self, player: Entity, npc_id: str) -> list[ReputationThreshold]:
        """NPC ゲート評価・未発火閾値を返す（発火は別メソッド）"""
        gate = self._npc_gates.get(npc_id)
        if not gate:
            return []
        rep = self.get_npc_reputation(player, npc_id)
        return self._check_thresholds(gate, rep, f"npc:{npc_id}")

    def evaluate_faction_gates(self, player: Entity, faction_id: str) -> list[ReputationThreshold]:
        """派閥ゲート評価"""
        gate = self._faction_gates.get(faction_id)
        if not gate:
            return []
        rep = self.get_faction_reputation(player, faction_id)
        return self._check_thresholds(gate, rep, f"faction:{faction_id}")

    def _check_thresholds(
        self,
        gate: Any,
        reputation: int,
        gate_key: str,
    ) -> list[ReputationThreshold]:
        """閾値チェック（未発火のみ）"""
        results = []
        for thresh in gate.thresholds:
            gate_id = f"{gate_key}:{thresh.threshold}:{thresh.action.name}:{thresh.target_id}"
            if gate_id in self._fired_gates:
                continue
            # 閾値判定
            if thresh.check(reputation):
                results.append(thresh)
        return results

    def fire_gate(self, threshold: ReputationThreshold, gate_key: str, player: Entity) -> bool:
        """ゲートアクション実行"""
        gate_id = f"{gate_key}:{threshold.threshold}:{threshold.action.name}:{threshold.target_id}"
        if gate_id in self._fired_gates:
            return False

        success = self._execute_action(threshold, player)
        if success and threshold.one_time:
            self._fired_gates.add(gate_id)
        return success

    def _execute_action(self, threshold: ReputationThreshold, player: Entity) -> bool:
        """アクション実行ディスパッチ"""
        action = threshold.action
        target = threshold.target_id
        params = threshold.params

        try:
            if action == GateAction.UNLOCK_QUEST:
                return self._unlock_quest(target, player, params)
            elif action == GateAction.LOCK_QUEST:
                return self._lock_quest(target, player, params)
            elif action == GateAction.TRIGGER_HOSTILE:
                return self._trigger_hostile(target, player, params)
            elif action == GateAction.REMOVE_HOSTILE:
                return self._remove_hostile(target, player, params)
            elif action == GateAction.UNLOCK_SHOP:
                return self._unlock_shop(target, player, params)
            elif action == GateAction.UNLOCK_DIALOGUE:
                return self._unlock_dialogue(target, player, params)
            elif action == GateAction.GRANT_BUFF:
                return self._grant_buff(target, player, params)
            elif action == GateAction.APPLY_DEBUFF:
                return self._apply_debuff(target, player, params)
            elif action == GateAction.CUSTOM:
                return self._custom_action(target, player, params)
        except Exception:
            logger.exception("Unhandled exception")
            # Log failure and return False
            return False

    def _unlock_quest(self, quest_id: str, player: Entity, params: dict) -> bool:
        mqs = getattr(self.engine, "main_quest_system", None)
        if mqs and quest_id in mqs.quests:
            mqs.quests[quest_id].status = mqs.quests[quest_id].status.__class__.AVAILABLE
            return True
        return False

    def _lock_quest(self, quest_id: str, player: Entity, params: dict) -> bool:
        mqs = getattr(self.engine, "main_quest_system", None)
        if mqs and quest_id in mqs.quests:
            mqs.quests[quest_id].status = mqs.quests[quest_id].status.__class__.LOCKED
            return True
        return False

    def _trigger_hostile(self, npc_id: str, player: Entity, params: dict) -> bool:
        # NPC を敵対状態に（AI システム連携）
        for e in self.engine.entity_manager.get_all_entities():
            if e.name == npc_id:
                e.is_hostile = True
                # 関係性も悪化
                rel_mgr = getattr(self.engine, "relationship_manager", None)
                if rel_mgr:
                    rel_mgr.update_relationship(player, npc_id, "betray", -50, -50)
                return True
        return False

    def _remove_hostile(self, npc_id: str, player: Entity, params: dict) -> bool:
        for e in self.engine.entity_manager.get_all_entities():
            if e.name == npc_id:
                e.is_hostile = False
                return True
        return False

    def _unlock_shop(self, shop_id: str, player: Entity, params: dict) -> bool:
        # ショップシステム連携（実装時に）
        return True

    def _unlock_dialogue(self, dialogue_id: str, player: Entity, params: dict) -> bool:
        # 会話システム連携（story_choices 等）
        return True

    def _grant_buff(self, buff_id: str, player: Entity, params: dict) -> bool:
        # TODO: 難易度プリセットの補正値を適用
        # バフシステム連携
        return True

    def _apply_debuff(self, debuff_id: str, player: Entity, params: dict) -> bool:
        return True

    def _custom_action(self, name: str, player: Entity, params: dict) -> bool:
        func = self._custom_actions.get(name)
        if func:
            return func(self.engine, player, params)
        return False

    def check_all_gates(self, player: Entity) -> list[str]:
        """全ゲート一括チェック・発火。発火したゲートIDリストを返す。"""
        fired = []
        # NPC ゲート
        for npc_id in self._npc_gates:
            for thresh in self.evaluate_npc_gates(player, npc_id):
                if self.fire_gate(thresh, f"npc:{npc_id}", player):
                    fired.append(f"npc:{npc_id}:{thresh.action.name}:{thresh.target_id}")
        # 派閥ゲート
        for fac_id in self._faction_gates:
            for thresh in self.evaluate_faction_gates(player, fac_id):
                if self.fire_gate(thresh, f"faction:{fac_id}", player):
                    fired.append(f"faction:{fac_id}:{thresh.action.name}:{thresh.target_id}")
        return fired


# 便利関数：YAML から閾値リストを構築
def create_thresholds_from_yaml(
    data: list[dict[str, Any]],
) -> list[ReputationThreshold]:
    """YAML データから ReputationThreshold リストを生成"""
    result = []
    for d in data:
        result.append(
            ReputationThreshold(
                threshold=d["threshold"],
                action=GateAction[d["action"]],
                target_id=d["target_id"],
                params=d.get("params", {}),
                description=d.get("description", ""),
                one_time=d.get("one_time", True),
            )
        )
    return result


__all__ = [
    "FactionReputationGate",
    "GateAction",
    "NPCReputationGate",
    "ReputationGate",
    "ReputationSource",
    "ReputationThreshold",
    "create_thresholds_from_yaml",
]
