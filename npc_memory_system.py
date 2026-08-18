"""
NPC Memory System Module (偏執的クエストシステム / 設計書 Phase 2 Step 5)
NPC の記憶ストア：クエスト結果・目撃・タイムスタンプを管理。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from enum import Enum, auto

if TYPE_CHECKING:
    from entity import Entity


class MemoryType(Enum):
    """記憶の種類"""
    QUEST_RESULT = auto()      # クエスト結果（成功/失敗/詳細）
    WITNESS = auto()           # 目撃情報（プレイヤーの行動を目撃）
    REPUTATION_EVENT = auto()  # 評判イベント（噂・伝聞）
    PERSONAL_INTERACTION = auto()  # 個人的交流（会話・贈り物・裏切り等）
    WORLD_EVENT = auto()       # ワールドイベント参加・観測


class MemoryImportance(Enum):
    """記憶の重要度（減衰・想起優先度に影響）"""
    TRIVIAL = 1      # 些細（すぐに薄れる）
    NOTABLE = 2      # 注目（通常減衰）
    SIGNIFICANT = 3  # 重要（減衰遅い）
    CRITICAL = 4     # 重大（ほぼ減衰しない・トラウマ級）
    ETERNAL = 5      # 永続（減衰しない・血の絆・師弟等）


@dataclass
class MemoryEntry:
    """単一記憶エントリ"""
    memory_type: MemoryType
    content: Dict[str, Any]          # 記憶の詳細データ
    importance: MemoryImportance = MemoryImportance.NOTABLE
    timestamp: float = field(default_factory=time.time)
    source_npc_id: Optional[str] = None      # 直接体験なら None、伝聞なら発信者
    tags: List[str] = field(default_factory=list)  # 検索用タグ
    decay_rate: float = 0.0                # カスタム減衰率（0=デフォルト使用）

    def age(self, current_time: Optional[float] = None) -> float:
        """経過時間（秒）を返す"""
        return (current_time or time.time()) - self.timestamp

    def current_strength(self, current_time: Optional[float] = None, base_decay: float = 0.0001) -> float:
        """現在の記憶強度（0.0-1.0）を返す。重要度で減衰調整。"""
        elapsed = self.age(current_time)
        effective_decay = self.decay_rate or (base_decay / max(1, self.importance.value))
        return max(0.0, 1.0 - elapsed * effective_decay)


class NPCMemoryManager:
    """NPC 単位の記憶管理"""

    def __init__(self, npc: "Entity"):
        self.npc = npc
        self._memories: List[MemoryEntry] = []

    def add_memory(
        self,
        memory_type: MemoryType,
        content: Dict[str, Any],
        importance: MemoryImportance = MemoryImportance.NOTABLE,
        source_npc_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        decay_rate: float = 0.0,
        timestamp: Optional[float] = None,
    ) -> MemoryEntry:
        """記憶を追加"""
        entry = MemoryEntry(
            memory_type=memory_type,
            content=content,
            importance=importance,
            source_npc_id=source_npc_id,
            tags=tags or [],
            decay_rate=decay_rate,
        )
        if timestamp is not None:
            entry.timestamp = timestamp
        self._memories.append(entry)
        # 同一タグの古い記憶を統合・圧縮（オプション：実装時に最適化）
        return entry

    def record_quest_result(
        self,
        quest_id: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None,
        importance: MemoryImportance = MemoryImportance.SIGNIFICANT,
    ) -> MemoryEntry:
        """クエスト結果を記録"""
        return self.add_memory(
            memory_type=MemoryType.QUEST_RESULT,
            content={
                "quest_id": quest_id,
                "success": success,
                "details": details or {},
            },
            importance=importance,
            tags=["quest", quest_id, "success" if success else "failure"],
        )

    def record_witness(
        self,
        actor_id: str,
        action: str,
        target_id: Optional[str] = None,
        location: Optional[Tuple[int, int]] = None,
        importance: MemoryImportance = MemoryImportance.NOTABLE,
    ) -> MemoryEntry:
        """目撃情報を記録"""
        return self.add_memory(
            memory_type=MemoryType.WITNESS,
            content={
                "actor_id": actor_id,
                "action": action,
                "target_id": target_id,
                "location": location,
            },
            importance=importance,
            source_npc_id=actor_id,
            tags=["witness", actor_id, action],
        )

    def record_reputation_event(
        self,
        subject_id: str,
        event_type: str,
        delta: int,
        source: str = "rumor",
        importance: MemoryImportance = MemoryImportance.NOTABLE,
    ) -> MemoryEntry:
        """評判変動イベントを記録（噂伝播で受信）"""
        return self.add_memory(
            memory_type=MemoryType.REPUTATION_EVENT,
            content={
                "subject_id": subject_id,
                "event_type": event_type,
                "delta": delta,
                "source": source,
            },
            importance=importance,
            source_npc_id=source if source != "rumor" else None,
            tags=["reputation", subject_id, event_type],
        )

    def record_personal_interaction(
        self,
        action: str,
        delta_trust: int = 0,
        delta_mood: int = 0,
        details: Optional[Dict[str, Any]] = None,
        importance: MemoryImportance = MemoryImportance.NOTABLE,
    ) -> MemoryEntry:
        """個人的交流を記録"""
        return self.add_memory(
            memory_type=MemoryType.PERSONAL_INTERACTION,
            content={
                "action": action,
                "delta_trust": delta_trust,
                "delta_mood": delta_mood,
                "details": details or {},
            },
            importance=importance,
            tags=["interaction", action],
        )

    def query(
        self,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None,
        min_strength: float = 0.0,
        current_time: Optional[float] = None,
        limit: int = 50,
    ) -> List[MemoryEntry]:
        """条件で記憶を検索（強度順）"""
        results = []
        for mem in self._memories:
            if memory_type and mem.memory_type != memory_type:
                continue
            if tags and not any(t in mem.tags for t in tags):
                continue
            strength = mem.current_strength(current_time)
            if strength >= min_strength:
                results.append((strength, mem))
        results.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in results[:limit]]

    def get_quest_memory(self, quest_id: str) -> Optional[MemoryEntry]:
        """特定クエストの最新記憶を取得"""
        matches = self.query(memory_type=MemoryType.QUEST_RESULT, tags=[quest_id], limit=1)
        return matches[0] if matches else None

    def get_witness_of(self, actor_id: str, action: Optional[str] = None) -> List[MemoryEntry]:
        """特定アクターの目撃記憶を取得"""
        tags = ["witness", actor_id]
        if action:
            tags.append(action)
        return self.query(memory_type=MemoryType.WITNESS, tags=tags)

    def get_reputation_towards(self, subject_id: str) -> List[MemoryEntry]:
        """特定対象への評判記憶を取得"""
        return self.query(memory_type=MemoryType.REPUTATION_EVENT, tags=[subject_id])

    def decay_and_cleanup(self, current_time: Optional[float] = None, min_strength: float = 0.01) -> int:
        """減衰処理と弱い記憶の削除。削除数を返す。"""
        original = len(self._memories)
        self._memories = [
            m for m in self._memories
            if m.current_strength(current_time) >= min_strength
        ]
        return original - len(self._memories)

    def get_summary(self, current_time: Optional[float] = None) -> Dict[str, Any]:
        """記憶サマリ（デバッグ・UI用）"""
        by_type: Dict[str, int] = {}
        for m in self._memories:
            by_type[m.memory_type.name] = by_type.get(m.memory_type.name, 0) + 1
        return {
            "total": len(self._memories),
            "by_type": by_type,
            "avg_strength": sum(m.current_strength(current_time) for m in self._memories) / max(1, len(self._memories)),
        }


class GlobalMemoryRegistry:
    """全NPCの記憶を管理するレジストリ（ゲームエンジン保持用）"""

    def __init__(self):
        self._managers: Dict[str, NPCMemoryManager] = {}

    def get(self, npc: "Entity") -> NPCMemoryManager:
        """NPC の記憶マネージャを取得（遅延生成）"""
        nid = npc.name  # 識別子として名前を使用（必要なら UUID 等に変更）
        if nid not in self._managers:
            self._managers[nid] = NPCMemoryManager(npc)
        return self._managers[nid]

    def get_by_id(self, npc_id: str) -> Optional[NPCMemoryManager]:
        return self._managers.get(npc_id)

    def all_managers(self) -> Dict[str, NPCMemoryManager]:
        return dict(self._managers)

    def global_decay(self, current_time: Optional[float] = None, min_strength: float = 0.01) -> int:
        """全NPCの記憶減衰を一括実行"""
        total = 0
        for mgr in self._managers.values():
            total += mgr.decay_and_cleanup(current_time, min_strength)
        return total

    def clear_npc(self, npc_id: str) -> None:
        if npc_id in self._managers:
            del self._managers[npc_id]


# グローバルシングルトン
GLOBAL_MEMORY_REGISTRY = GlobalMemoryRegistry()


__all__ = [
    "MemoryType",
    "MemoryImportance",
    "MemoryEntry",
    "NPCMemoryManager",
    "GlobalMemoryRegistry",
    "GLOBAL_MEMORY_REGISTRY",
]