"""
NPC Relationship Simulation - Main Quest System Integration
Step 16: Integration with main quest system
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

from .models import RelationshipType, InteractionType
from .engine import RelationshipManager
from .branching import BranchingScenarioGenerator, GeneratedScenario


class QuestRelationRequirement(Enum):
    """クエストの関係要件タイプ"""
    MIN_LEVEL = "min_level"               # 最小関係レベル
    EXACT_LEVEL = "exact_level"          # 指定レベル
    MAX_LEVEL = "max_level"              # 最大関係レベル
    RELATIONSHIP_TYPE = "relationship_type"  # 特定の関係タイプが必要
    NO_CONFLICT = "no_conflict"          # 対立がないこと
    ROMANCE_ACTIVE = "romance_active"    # 恋愛関係が活性
    MENTORSHIP_ACTIVE = "mentorship_active"  # 師弟関係が活性


@dataclass
class QuestRelationshipGate:
    """クエストの関係ゲート（前提条件）"""
    quest_id: str
    requirements: List[Dict[str, Any]] = field(default_factory=list)
    failure_consequences: Dict[str, Any] = field(default_factory=dict)
    success_bonus: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QuestRewardRelationship:
    """クエスト報酬としての関係変化"""
    quest_id: str
    target_character: str
    relationship_type: RelationshipType
    delta: int
    reason: str = ""


class QuestRelationshipIntegration:
    """
    メインクエストシステムとの統合
    クエスト進行が関係に与える影響、関係ベースのクエスト条件、
    クエスト報酬としての関係変化を管理
    """
    
    def __init__(self, relationship_manager: RelationshipManager, 
                 branching_generator: Optional[BranchingScenarioGenerator] = None):
        self.rm = relationship_manager
        self.graph = relationship_manager.graph
        self.branching = branching_generator or BranchingScenarioGenerator(relationship_manager)
        
        # クエスト関係ゲート
        self.quest_gates: Dict[str, QuestRelationshipGate] = {}
        
        # クエスト報酬関係変化
        self.quest_rewards: Dict[str, List[QuestRewardRelationship]] = defaultdict(list)
        
        # クエスト特有のNPC
        self.quest_npcs: Dict[str, List[str]] = defaultdict(list)
        
        # イベントハンドラー
        self._event_handlers: Dict[str, List[Callable[..., Any]]] = defaultdict(list)
        
        # 統計
        self._stats = {
            'quests_affected_by_relationships': 0,
            'relationship_based_quest_unlocks': 0,
            'relationship_failures': 0
        }
    
    def register_quest_relationship_gate(self, quest_id: str,
                                      requirements: List[Dict[str, Any]],
                                      success_bonus: Optional[Dict[str, Any]] = None,
                                      failure_consequences: Optional[Dict[str, Any]] = None) -> QuestRelationshipGate:
        """クエストの関係ゲートを登録"""
        gate = QuestRelationshipGate(
            quest_id=quest_id,
            requirements=requirements,
            success_bonus=success_bonus or {},
            failure_consequences=failure_consequences or {}
        )
        self.quest_gates[quest_id] = gate
        return gate
    
    def register_quest_reward_relationship(self, quest_id: str, target_character: str,
                                       relationship_type: RelationshipType, delta: int,
                                       reason: str = "") -> QuestRewardRelationship:
        """クエスト報酬としての関係変化を登録"""
        reward = QuestRewardRelationship(
            quest_id=quest_id,
            target_character=target_character,
            relationship_type=relationship_type,
            delta=delta,
            reason=reason
        )
        self.quest_rewards[quest_id].append(reward)
        return reward
    
    def register_quest_npc(self, quest_id: str, npc_id: str) -> None:
        """クエストに関連するNPCを登録"""
        self.quest_npcs[quest_id].append(npc_id)
    
    def check_quest_availability(self, quest_id: str, player_id: str = "player") -> Dict[str, Any]:
        """クエストの利用可能性を関係ベースでチェック"""
        gate = self.quest_gates.get(quest_id)
        if not gate:
            return {"available": True, "reason": "no_gates"}
        
        unmet_requirements = []
        
        for req in gate.requirements:
            requirement_type = req.get('type')
            target_id = req.get('target_id')
            
            if requirement_type == QuestRelationRequirement.MIN_LEVEL.value:
                rel_type = RelationshipType(req.get('relationship_type', 'favorability'))
                min_level = req.get('level', 0)
                actual_level = self.rm.get_relationship_level(player_id, target_id, rel_type)
                if actual_level < min_level:
                    unmet_requirements.append({
                        'requirement': requirement_type,
                        'target': target_id,
                        'required': min_level,
                        'actual': actual_level
                    })
            
            elif requirement_type == QuestRelationRequirement.MAX_LEVEL.value:
                rel_type = RelationshipType(req.get('relationship_type', 'favorability'))
                max_level = req.get('level', 100)
                actual_level = self.rm.get_relationship_level(player_id, target_id, rel_type)
                if actual_level > max_level:
                    unmet_requirements.append({
                        'requirement': requirement_type,
                        'target': target_id,
                        'required': max_level,
                        'actual': actual_level
                    })
            
            elif requirement_type == QuestRelationRequirement.NO_CONFLICT.value:
                # 敵対関係がないことを確認
                enmity_level = self.rm.get_relationship_level(player_id, target_id, RelationshipType.ENMITY)
                if enmity_level > 0:
                    unmet_requirements.append({
                        'requirement': requirement_type,
                        'target': target_id,
                        'enmity_level': enmity_level
                    })
            
            elif requirement_type == QuestRelationRequirement.ROMANCE_ACTIVE.value:
                romance_level = self.rm.get_relationship_level(player_id, target_id, RelationshipType.ROMANCE)
                if romance_level < 20:
                    unmet_requirements.append({
                        'requirement': requirement_type,
                        'target': target_id,
                        'romance_level': romance_level
                    })
            
            elif requirement_type == QuestRelationRequirement.MENTORSHIP_ACTIVE.value:
                mentorship_level = self.rm.get_relationship_level(player_id, target_id, RelationshipType.MENTORSHIP)
                if mentorship_level < 20:
                    unmet_requirements.append({
                        'requirement': requirement_type,
                        'target': target_id,
                        'mentorship_level': mentorship_level
                    })
        
        available = len(unmet_requirements) == 0
        
        if available:
            self._stats['relationship_based_quest_unlocks'] += 1
        
        return {
            "available": available,
            "unmet_requirements": unmet_requirements,
            "reason": "ok" if available else "requirements_not_met"
        }
    
    def apply_quest_completion_effects(self, quest_id: str, player_id: str = "player",
                                    success: bool = True) -> Dict[str, Any]:
        """クエスト完了時の関係効果を適用"""
        results = {}
        
        # 報酬としての関係変化を適用
        rewards = self.quest_rewards.get(quest_id, [])
        for reward in rewards:
            if success:
                delta = reward.delta
            else:
                # 失敗時は半減または逆効果
                delta = -reward.delta // 2 if reward.delta > 0 else reward.delta
            
            self.rm.modify_relationship(
                player_id, reward.target_character,
                InteractionType.QUEST_COOPERATION if success else InteractionType.QUEST_CONFLICT,
                delta
            )
            results[reward.target_character] = {
                'relationship_type': reward.relationship_type.value,
                'delta': delta,
                'reason': reward.reason
            }
        
        # 成功ボーナス（ゲートにある場合）
        gate = self.quest_gates.get(quest_id)
        if gate and success and gate.success_bonus:
            bonus_targets = gate.success_bonus.get('relationship_bonuses', [])
            for bonus in bonus_targets:
                target = bonus.get('target_id')
                rel_type = RelationshipType(bonus.get('relationship_type', 'favorability'))
                delta = bonus.get('delta', 0)
                if target and delta != 0:
                    self.rm.modify_relationship(player_id, target, InteractionType.QUEST_COOPERATION, delta)
                    results[target] = results.get(target, {})
                    results[target].update({
                        'bonus_delta': delta,
                        'bonus_type': rel_type.value
                    })
        
        # 失敗時の帰結
        if not success and gate and gate.failure_consequences:
            fail_consequences = gate.failure_consequences.get('relationship_penalties', [])
            for penalty in fail_consequences:
                target = penalty.get('target_id')
                rel_type = RelationshipType(penalty.get('relationship_type', 'favorability'))
                delta = penalty.get('delta', 0)
                if target and delta != 0:
                    self.rm.modify_relationship(player_id, target, InteractionType.QUEST_CONFLICT, delta)
                    results[target] = results.get(target, {})
                    results[target].update({
                        'penalty_delta': delta,
                        'penalty_type': rel_type.value
                    })
                    self._stats['relationship_failures'] += 1
        
        # クエストNPCへの影響（共闘の絆）
        if success:
            npcs = self.quest_npcs.get(quest_id, [])
            for npc in npcs:
                if npc != player_id:
                    self.rm.modify_relationship(player_id, npc, InteractionType.QUEST_COOPERATION, 10)
                    results[npc] = results.get(npc, {})
                    results[npc].update({'quest_bond': 10})
        
        return results
    
    def generate_relationship_quest(self, player_id: str = "player",
                                 character_id: Optional[str] = None) -> Optional[GeneratedScenario]:
        """関係ベースのクエストを生成"""
        # 分岐シナリオ生成器を使用
        scenarios = self.branching.check_for_scenarios(player_id)
        
        # 関係ベースのクエストシナリオを抽出
        relationship_quests = [
            s for s in scenarios 
            if s.trigger_type.value in [
                'relationship_threshold', 'relationship_conflict', 
                'triangular_relationship', 'faction_tension'
            ]
        ]
        
        if not relationship_quests:
            return None
        
        # 最も影響が大きいシナリオを選択
        best_scenario = max(
            relationship_quests,
            key=lambda s: len(s.involved_characters) + len(s.branches) * 2
        )
        
        self._stats['quests_affected_by_relationships'] += 1
        
        return best_scenario
    
    def get_quest_relationship_status(self, quest_id: str, player_id: str = "player") -> Dict[str, Any]:
        """クエストの関係ステータスを取得"""
        gate = self.quest_gates.get(quest_id)
        if not gate:
            return {"has_gates": False}
        
        availability = self.check_quest_availability(quest_id, player_id)
        
        # 関連NPCの関係状態を取得
        npc_status = {}
        for npc_id in self.quest_npcs.get(quest_id, []):
            npc_status[npc_id] = self.rm.get_all_relationships(npc_id)
        
        return {
            "has_gates": True,
            "available": availability['available'],
            "unmet_requirements": availability['unmet_requirements'],
            "npc_status": npc_status
        }
    
    def integrate_with_main_quest_system(self, main_quest_system: Any) -> None:
        """メインクエストシステムとの統合フック"""
        # メインクエストシステムのクエスト完了時に呼び出されるフック
        if hasattr(main_quest_system, 'add_completion_callback'):
            main_quest_system.add_completion_callback(self._on_quest_completed)
    
    def _on_quest_completed(self, quest_id: str, player: Any, engine: Any = None) -> List[str]:
        """クエスト完了時のコールバック"""
        results = self.apply_quest_completion_effects(quest_id)
        
        logs = []
        for target, changes in results.items():
            if 'delta' in changes:
                logs.append(f"【関係変化】{target}との{changes['relationship_type']}関係が{changes['delta']:+d}されました")
            if 'bonus_delta' in changes:
                logs.append(f"【ボーナス関係】{target}との{changes['bonus_type']}関係が{changes['bonus_delta']:+d}されました")
            if 'penalty_delta' in changes:
                logs.append(f"【ペナルティ関係】{target}との{changes['penalty_type']}関係が{changes['penalty_delta']:+d}されました")
            if 'quest_bond' in changes:
                logs.append(f"【共闘の絆】{target}との絆が{changes['quest_bond']:+d}されました")
        
        # クエスト完了によるシナリオ生成チェック
        scenarios = self.branching.check_for_scenarios(getattr(player, 'id', 'player'))
        for scenario in scenarios:
            logs.append(f"【新規シナリオ】{scenario.title}が発生しました！")
        
        return logs
    
    def register_event_handler(self, event_type: str, handler: Callable[..., Any]) -> None:
        """イベントハンドラーを登録"""
        self._event_handlers[event_type].append(handler)
    
    def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """イベントを発行"""
        for handler in self._event_handlers.get(event_type, []):
            try:
                handler(event_type, data)
            except Exception as e:
                print(f"Error in quest integration event handler: {e}")
    
    def get_integration_statistics(self) -> Dict[str, Any]:
        """統合統計を取得"""
        return {
            **self._stats,
            'registered_gates': len(self.quest_gates),
            'registered_rewards': sum(len(rewards) for rewards in self.quest_rewards.values()),
            'registered_npcs': sum(len(npcs) for npcs in self.quest_npcs.values())
        }
    
    def serialize(self) -> Dict[str, Any]:
        """統合状態をシリアライズ"""
        return {
            'quest_gates': {
                qid: {
                    'quest_id': gate.quest_id,
                    'requirements': gate.requirements,
                    'success_bonus': gate.success_bonus,
                    'failure_consequences': gate.failure_consequences
                }
                for qid, gate in self.quest_gates.items()
            },
            'quest_rewards': {
                qid: [
                    {
                        'quest_id': r.quest_id,
                        'target_character': r.target_character,
                        'relationship_type': r.relationship_type.value,
                        'delta': r.delta,
                        'reason': r.reason
                    }
                    for r in rewards
                ]
                for qid, rewards in self.quest_rewards.items()
            },
            'quest_npcs': dict(self.quest_npcs),
            'stats': self._stats
        }
    
    def deserialize(self, data: Dict[str, Any]) -> None:
        """統合状態をデシリアライズ"""
        self.quest_gates.clear()
        self.quest_rewards.clear()
        self.quest_npcs.clear()
        
        for qid, gate_data in data.get('quest_gates', {}).items():
            self.quest_gates[qid] = QuestRelationshipGate(
                quest_id=gate_data['quest_id'],
                requirements=gate_data['requirements'],
                success_bonus=gate_data.get('success_bonus', {}),
                failure_consequences=gate_data.get('failure_consequences', {})
            )
        
        for qid, rewards_data in data.get('quest_rewards', {}).items():
            for r_data in rewards_data:
                self.quest_rewards[qid].append(QuestRewardRelationship(
                    quest_id=r_data['quest_id'],
                    target_character=r_data['target_character'],
                    relationship_type=RelationshipType(r_data['relationship_type']),
                    delta=r_data['delta'],
                    reason=r_data.get('reason', '')
                ))
        
        self.quest_npcs = defaultdict(list, data.get('quest_npcs', {}))
        self._stats = data.get('stats', self._stats)