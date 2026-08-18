"""
NPC Relationship Simulation - Relationship Decay and Memory System
Step 12: Relationship decay and memory system
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
import time
import math
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

from .models import RelationshipType, InteractionType
from .engine import RelationshipManager


class MemoryType(Enum):
    """記憶のタイプ"""
    POSITIVE_EVENT = "positive_event"      # 良い出来事
    NEGATIVE_EVENT = "negative_event"      # 悪い出来事
    MILESTONE = "milestone"               # 節目の出来事
    TRAUMA = "trauma"                     # トラウマ
    NOSTALGIA = "nostalgia"               # 郷愁（過去の良い思い出）
    ROUTINE = "routine"                   # 日常的な出来事


class MemoryImportance(Enum):
    """記憶の重要度"""
    TRIVIAL = 1      # 取るに足らない
    MINOR = 2        # 軽微
    MODERATE = 3     # 中程度
    SIGNIFICANT = 4  # 重要
    MAJOR = 5        # 重大
    LIFE_CHANGING = 6  # 人生を変える


@dataclass
class MemoryFragment:
    """記憶の断片"""
    memory_id: str
    character_id: str  # 記憶を持つキャラクター
    other_id: Optional[str]  # 関連する他キャラクター（オプション）
    memory_type: MemoryType
    importance: MemoryImportance
    description: str
    timestamp: float
    emotional_intensity: float = 0.5  # 0.0〜1.0
    associated_relationship: Optional[RelationshipType] = None
    decay_rate: float = 0.0001  # 記憶の薄れ率
    last_recalled: float = field(default_factory=time.time)
    recall_count: int = 0
    linked_memories: List[str] = field(default_factory=list)
    
    def get_effective_intensity(self, current_time: Optional[float] = None) -> float:
        """現在の感情強度を取得（時間経過で減衰）"""
        if current_time is None:
            current_time = time.time()
        
        elapsed = current_time - self.timestamp
        # 指数関数的減衰
        decay = math.exp(-self.decay_rate * elapsed / 86400)  # 日単位
        # ノスタルジア効果：古い良い記憶は理想化される
        if self.memory_type == MemoryType.NOSTALGIA or self.memory_type == MemoryType.POSITIVE_EVENT:
            # 古いほど強くなる（一定の期間まで）
            nostalgia_factor = min(1.5, 1.0 + (elapsed / (365 * 86400)) * 0.3)  # 1年で最大1.5倍
            return min(1.0, self.emotional_intensity * decay * nostalgia_factor)
        
        # トラウマは薄れにくい
        if self.memory_type == MemoryType.TRAUMA:
            decay = math.exp(-self.decay_rate * 0.3 * elapsed / 86400)
        
        return max(0.0, min(1.0, self.emotional_intensity * decay))
    
    def recall(self) -> None:
        """記憶を呼び起こす"""
        self.last_recalled = time.time()
        self.recall_count += 1
        # 呼び起こすことで記憶が強化される
        self.emotional_intensity = min(1.0, self.emotional_intensity * 1.05)
    
    def should_fade(self, current_time: Optional[float] = None) -> bool:
        """記憶が薄れるべきかチェック"""
        if current_time is None:
            current_time = time.time()
        
        # 重要な記憶は永続的
        if self.importance >= MemoryImportance.MAJOR:
            return False
        
        intensity = self.get_effective_intensity(current_time)
        return intensity < 0.05


class MemorySystem:
    """
    記憶システム
    関係変化から記憶を形成し、長期的影響を管理
    """
    
    def __init__(self, relationship_manager: RelationshipManager):
        self.rm = relationship_manager
        self.graph = relationship_manager.graph
        
        # 記憶ストレージ
        self.memories: Dict[str, MemoryFragment] = {}
        self.memories_by_character: Dict[str, List[str]] = defaultdict(list)
        
        # 設定
        self._config = self._load_memory_config()
        
        # 統計
        self._stats = {
            'total_memories': 0,
            'memories_recalled': 0,
            'memories_faded': 0
        }
        
        # 記憶IDカウンター
        self._memory_counter = 0
    
    def _load_memory_config(self) -> Dict[str, Any]:
        """記憶設定をロード"""
        return {
            'memory_threshold': 10,          # 記憶として保存する関係変化の最小量
            'nostalgia_start_years': 2.0,    # ノスタルジアが始まる年数
            'trauma_decay_multiplier': 0.3,  # トラウマの減衰倍率
            'max_memories_per_character': 100,
            'auto_recall_chance': 0.1,       # 関連イベント時の自動回想確率
            'memory_influence_on_relationship': 0.05  # 記憶が関係に与える影響係数
        }
    
    def create_memory(self, character_id: str, memory_type: MemoryType,
                    description: str, importance: MemoryImportance,
                    other_id: Optional[str] = None,
                    associated_relationship: Optional[RelationshipType] = None,
                    emotional_intensity: float = 0.5,
                    timestamp: Optional[float] = None) -> MemoryFragment:
        """記憶を作成"""
        if timestamp is None:
            timestamp = time.time()
        
        self._memory_counter += 1
        memory_id = f"mem_{self._memory_counter}_{int(timestamp)}"
        
        memory = MemoryFragment(
            memory_id=memory_id,
            character_id=character_id,
            other_id=other_id,
            memory_type=memory_type,
            importance=importance,
            description=description,
            timestamp=timestamp,
            emotional_intensity=emotional_intensity,
            associated_relationship=associated_relationship
        )
        
        self.memories[memory_id] = memory
        self.memories_by_character[character_id].append(memory_id)
        
        # 最大記憶数を超えた場合は古いものを削除
        if len(self.memories_by_character[character_id]) > self._config['max_memories_per_character']:
            oldest_id = self.memories_by_character[character_id][0]
            del self.memories[oldest_id]
            self.memories_by_character[character_id].remove(oldest_id)
        
        self._stats['total_memories'] += 1
        
        return memory
    
    def record_relationship_event(self, character_id: str, other_id: str,
                                relationship_type: RelationshipType,
                                change_amount: int,
                                context: Optional[Dict[str, Any]] = None) -> Optional[MemoryFragment]:
        """関係イベントから記憶を記録"""
        if abs(change_amount) < self._config['memory_threshold']:
            return None
        
        context = context or {}
        
        # 記憶タイプと重要度を決定
        if change_amount > 0:
            memory_type = MemoryType.POSITIVE_EVENT
            importance = self._calculate_importance(change_amount, context)
        else:
            memory_type = MemoryType.NEGATIVE_EVENT
            importance = self._calculate_importance(abs(change_amount), context)
            # 深刻なネガティブイベントはトラウマの可能性
            if abs(change_amount) >= 40:
                memory_type = MemoryType.TRAUMA
        
        # 記憶の説明を生成
        description = self._generate_memory_description(
            character_id, other_id, relationship_type, change_amount, memory_type
        )
        
        # 感情的強度
        emotional_intensity = min(1.0, abs(change_amount) / 50.0)
        
        # 記憶を作成
        memory = self.create_memory(
            character_id=character_id,
            memory_type=memory_type,
            description=description,
            importance=importance,
            other_id=other_id,
            associated_relationship=relationship_type,
            emotional_intensity=emotional_intensity
        )
        
        # 他キャラクターの記憶にもリンク
        if other_id and other_id in self.graph.nodes:
            linked_memory = self.create_memory(
                character_id=other_id,
                memory_type=memory_type,
                description=f"{self._get_name(character_id)}との出来事: {description}",
                importance=importance,
                other_id=character_id,
                associated_relationship=relationship_type,
                emotional_intensity=emotional_intensity * 0.8  # 少し弱く
            )
            memory.linked_memories.append(linked_memory.memory_id)
        
        return memory
    
    def _calculate_importance(self, change_amount: int, context: Dict[str, Any]) -> MemoryImportance:
        """関係変化量とコンテキストから重要度を計算"""
        abs_change = abs(change_amount)
        
        # 基本的な重要度（変化量ベース）
        if abs_change >= 40:
            base_importance = MemoryImportance.LIFE_CHANGING
        elif abs_change >= 30:
            base_importance = MemoryImportance.MAJOR
        elif abs_change >= 20:
            base_importance = MemoryImportance.SIGNIFICANT
        elif abs_change >= 15:
            base_importance = MemoryImportance.MODERATE
        elif abs_change >= 10:
            base_importance = MemoryImportance.MINOR
        else:
            base_importance = MemoryImportance.TRIVIAL
        
        # コンテキストによる調整
        if context.get('is_crisis', False):
            # 危機的な状況は重要度アップ
            base_importance = MemoryImportance(min(6, base_importance.value + 1))
        
        if context.get('witnesses_present', False):
            # 目撃者がいる場合も重要度アップ
            base_importance = MemoryImportance(min(6, base_importance.value + 1))
        
        return base_importance
    
    def _generate_memory_description(self, character_id: str, other_id: str,
                                   relationship_type: RelationshipType,
                                   change_amount: int, memory_type: MemoryType) -> str:
        """記憶の説明を生成"""
        name = self._get_name(other_id) if other_id else "誰か"
        rel_name = {
            RelationshipType.FAVORABILITY: "好感度",
            RelationshipType.ROMANCE: "恋愛",
            RelationshipType.MENTORSHIP: "師弟",
            RelationshipType.BETRAYAL: "信頼",
            RelationshipType.ENMITY: "敵対",
            RelationshipType.FRIENDSHIP: "友情",
            RelationshipType.FAMILY: "家族",
            RelationshipType.RIVALRY: "競争",
            RelationshipType.BUSINESS: "取引",
            RelationshipType.FACTION: "派閥"
        }.get(relationship_type, "関係")
        
        if memory_type == MemoryType.POSITIVE_EVENT:
            return f"{name}との{rel_name}関係が深まった（+{change_amount}）"
        elif memory_type == MemoryType.NEGATIVE_EVENT:
            return f"{name}との{rel_name}関係が悪化した（{change_amount}）"
        elif memory_type == MemoryType.TRAUMA:
            return f"{name}からの裏切りによる深い傷（{change_amount}）"
        elif memory_type == MemoryType.MILESTONE:
            return f"{name}との重要な節目（+{change_amount}）"
        else:
            return f"{name}との{rel_name}関係の変化（{change_amount}）"
    
    def recall_memory(self, memory_id: str) -> Optional[MemoryFragment]:
        """記憶を呼び起こす"""
        memory = self.memories.get(memory_id)
        if not memory:
            return None
        
        memory.recall()
        self._stats['memories_recalled'] += 1
        
        # リンクされた記憶も呼び起こす
        for linked_id in memory.linked_memories:
            linked = self.memories.get(linked_id)
            if linked:
                linked.recall()
        
        return memory
    
    def get_memories_for_character(self, character_id: str, 
                                 memory_type: Optional[MemoryType] = None,
                                 limit: int = 10) -> List[MemoryFragment]:
        """キャラクターの記憶を取得"""
        memory_ids = self.memories_by_character.get(character_id, [])
        memories = []
        
        for mid in memory_ids:
            memory = self.memories.get(mid)
            if memory and (memory_type is None or memory.memory_type == memory_type):
                memories.append(memory)
        
        # 感情強度でソート（強い順）
        current_time = time.time()
        memories.sort(key=lambda m: m.get_effective_intensity(current_time), reverse=True)
        
        return memories[:limit]
    
    def apply_memory_influence(self, character_id: str, other_id: str) -> Dict[str, int]:
        """記憶の影響を関係に適用"""
        character_memories = self.get_memories_for_character(character_id, limit=20)
        
        influence: Dict[str, int] = defaultdict(int)
        
        for memory in character_memories:
            if memory.other_id != other_id:
                continue
            
            if memory.associated_relationship is None:
                continue
            
            # 記憶の感情強度に基づいて影響を計算
            intensity = memory.get_effective_intensity()
            effect = int(intensity * self._config['memory_influence_on_relationship'] * 
                       (1 if memory.memory_type in [MemoryType.POSITIVE_EVENT, MemoryType.NOSTALGIA, MemoryType.MILESTONE] else -1) * 10)
            
            influence[memory.associated_relationship.value] += effect
        
        # 影響を適用（小さな変更として）
        for rel_type_str, amount in influence.items():
            if amount == 0:
                continue
            rel_type = RelationshipType(rel_type_str)
            self.rm.modify_relationship(character_id, other_id, InteractionType.TALK, amount)
        
        return dict(influence)
    
    def decay_memories(self, current_time: Optional[float] = None) -> int:
        """薄れるべき記憶を処理"""
        if current_time is None:
            current_time = time.time()
        
        faded_count = 0
        memories_to_remove = []
        
        for memory_id, memory in self.memories.items():
            if memory.should_fade(current_time):
                memories_to_remove.append(memory_id)
        
        for memory_id in memories_to_remove:
            memory = self.memories[memory_id]
            # キャラクターの記憶リストから削除
            if memory.character_id in self.memories_by_character:
                if memory_id in self.memories_by_character[memory.character_id]:
                    self.memories_by_character[memory.character_id].remove(memory_id)
            del self.memories[memory_id]
            faded_count += 1
        
        self._stats['memories_faded'] += faded_count
        
        return faded_count
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """記憶統計を取得"""
        type_distribution: Dict[str, int] = defaultdict(int)
        for memory in self.memories.values():
            type_distribution[memory.memory_type.value] += 1
        
        return {
            **self._stats,
            'active_memories': len(self.memories),
            'type_distribution': dict(type_distribution)
        }
    
    def _get_name(self, character_id: str) -> str:
        """キャラクター名を取得"""
        node = self.graph.get_node(character_id)
        return node.name if node else character_id
    
    def serialize(self) -> Dict[str, Any]:
        """記憶をシリアライズ"""
        return {
            'memories': {
                mid: {
                    'memory_id': m.memory_id,
                    'character_id': m.character_id,
                    'other_id': m.other_id,
                    'memory_type': m.memory_type.value,
                    'importance': m.importance.value,
                    'description': m.description,
                    'timestamp': m.timestamp,
                    'emotional_intensity': m.emotional_intensity,
                    'associated_relationship': m.associated_relationship.value if m.associated_relationship else None,
                    'decay_rate': m.decay_rate,
                    'last_recalled': m.last_recalled,
                    'recall_count': m.recall_count,
                    'linked_memories': m.linked_memories
                }
                for mid, m in self.memories.items()
            },
            'stats': self._stats,
            'memory_counter': self._memory_counter
        }
    
    def deserialize(self, data: Dict[str, Any]) -> None:
        """記憶をデシリアライズ"""
        self.memories.clear()
        self.memories_by_character.clear()
        self._stats = data.get('stats', self._stats)
        self._memory_counter = data.get('memory_counter', 0)
        
        for mid, m_data in data.get('memories', {}).items():
            memory = MemoryFragment(
                memory_id=m_data['memory_id'],
                character_id=m_data['character_id'],
                other_id=m_data.get('other_id'),
                memory_type=MemoryType(m_data['memory_type']),
                importance=MemoryImportance(m_data['importance']),
                description=m_data['description'],
                timestamp=m_data['timestamp'],
                emotional_intensity=m_data.get('emotional_intensity', 0.5),
                associated_relationship=RelationshipType(m_data['associated_relationship']) if m_data.get('associated_relationship') else None,
                decay_rate=m_data.get('decay_rate', 0.0001),
                last_recalled=m_data.get('last_recalled', m_data['timestamp']),
                recall_count=m_data.get('recall_count', 0),
                linked_memories=m_data.get('linked_memories', [])
            )
            self.memories[mid] = memory
            self.memories_by_character[memory.character_id].append(mid)


class RelationshipDecaySystem:
    """
    関係減衰システム
    時間経過による関係の自然な減衰を管理
    """
    
    def __init__(self, relationship_manager: RelationshipManager, memory_system: Optional[MemorySystem] = None):
        self.rm = relationship_manager
        self.graph = relationship_manager.graph
        self.memory_system = memory_system
        
        # 減衰設定
        self._config = {
            'min_decay_interval': 3600,  # 1時間
            'max_decay_per_cycle': 5,    # 1サイクルあたりの最大減衰量
            'positive_relationship_bias': 0.8,  # ポジティブな関係は減衰しにくい
            'negative_relationship_persistence': 1.2,  # ネガティブな関係は持続
            'memory_reinforcement_rate': 0.1  # 記憶による減衰軽減率
        }
        
        self._last_decay_time: float = time.time()
        self._decay_history: deque = deque(maxlen=100)
    
    def apply_decay(self, current_time: Optional[float] = None) -> Dict[str, int]:
        """時間経過による減衰を適用"""
        if current_time is None:
            current_time = time.time()
        
        # 前回の減衰から十分な時間が経過したかチェック
        time_since_last = current_time - self._last_decay_time
        if time_since_last < self._config['min_decay_interval']:
            return {}
        
        self._last_decay_time = current_time
        
        total_changes = defaultdict(int)
        
        # すべてのエッジに減衰を適用
        for edge in self.graph.edges.values():
            change = self._calculate_decay_change(edge, time_since_last, current_time)
            
            if change != 0:
                edge.level = max(-100, min(100, edge.level + change))
                edge.last_interaction = edge.last_interaction  # 更新しない（減衰はインタラクションではない）
                
                total_changes[f"{edge.source_id}->{edge.target_id}:{edge.relationship_type.value}"] += change
                
                # 記憶システムに通知（大きな減衰の場合）
                if self.memory_system and abs(change) >= 5:
                    self.memory_system.record_relationship_event(
                        edge.source_id, edge.target_id, edge.relationship_type, change,
                        context={'is_decay': True}
                    )
        
        # 減衰履歴を記録
        self._decay_history.append({
            'timestamp': current_time,
            'time_since_last': time_since_last,
            'total_edges_affected': len(total_changes)
        })
        
        return dict(total_changes)
    
    def _calculate_decay_change(self, edge: Any, time_elapsed: float, 
                              current_time: float) -> int:
        """個別エッジの減衰量を計算"""
        # 日単位の経過時間
        days_elapsed = time_elapsed / 86400
        
        # 基本減衰率（エッジごとの個別設定 + システム設定）
        base_decay_rate = edge.decay_rate
        
        # 関係の符号による調整
        if edge.level > 0:
            # ポジティブな関係は減衰しにくい
            effective_rate = base_decay_rate * self._config['positive_relationship_bias']
        elif edge.level < 0:
            # ネガティブな関係は持続（減衰しにくい）
            effective_rate = base_decay_rate * self._config['negative_relationship_persistence']
        else:
            effective_rate = base_decay_rate
        
        # 減衰量を計算
        decay_amount = int(edge.level * effective_rate * days_elapsed)
        
        # 最大減衰量でクリップ
        decay_amount = max(-self._config['max_decay_per_cycle'], 
                          min(self._config['max_decay_per_cycle'], decay_amount))
        
        # 記憶による減衰軽減
        if self.memory_system:
            memories = self.memory_system.get_memories_for_character(edge.source_id, limit=5)
            reinforcement = sum(m.get_effective_intensity(current_time) for m in memories 
                              if m.other_id == edge.target_id)
            if reinforcement > 0:
                decay_amount = int(decay_amount * (1 - self._config['memory_reinforcement_rate'] * min(1.0, reinforcement)))
        
        return -decay_amount  # 減衰は負の方向
    
    def get_decay_statistics(self) -> Dict[str, Any]:
        """減衰統計を取得"""
        return {
            'last_decay_time': self._last_decay_time,
            'decay_cycles': len(self._decay_history),
            'total_changes_recorded': sum(
                abs(change) for record in self._decay_history
                for change in [record.get('total_edges_affected', 0)]
            )
        }