"""
NPC Memory System Module (偏執的クエストシステム / 設計書 Phase 2 Step 5)
NPC の記憶ストア：クエスト結果・目撃・タイムスタンプを管理。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ecs.entity import Entity


class MemoryType(Enum):
    """記憶の種類"""

    QUEST_RESULT = auto()  # クエスト結果（成功/失敗/詳細）
    WITNESS = auto()  # 目撃情報（プレイヤーの行動を目撃）
    REPUTATION_EVENT = auto()  # 評判イベント（噂・伝聞）
    PERSONAL_INTERACTION = auto()  # 個人的交流（会話・贈り物・裏切り等）
    WORLD_EVENT = auto()  # ワールドイベント参加・観測


class MemoryImportance(Enum):
    """記憶の重要度（減衰・想起優先度に影響）"""

    TRIVIAL = 1  # 些細（すぐに薄れる）
    NOTABLE = 2  # 注目（通常減衰）
    SIGNIFICANT = 3  # 重要（減衰遅い）
    CRITICAL = 4  # 重大（ほぼ減衰しない・トラウマ級）
    ETERNAL = 5  # 永続（減衰しない・血の絆・師弟等）


# =============================================================================
# プレイヤー行動 → 態度影響定義 (R4-C カルマフックの行動名と整合, T43 案A)
# =============================================================================

# 態度値のクランプ範囲
ATTITUDE_MIN = -100
ATTITUDE_MAX = 100
# 態度 0 における好感度の基準値
AFFECTION_BASE = 50
# プレイヤーの行動を目撃できる距離 (チェビシェフ距離)
WITNESS_RADIUS = 6

# 未知の行動に適用される中立定義 (記憶には残るが態度は動かない)
_NEUTRAL_IMPACT: dict[str, Any] = {"attitude": 0, "importance": MemoryImportance.NOTABLE}

# action → 1 回あたりの態度変化量と記憶重要度
PLAYER_ACTION_IMPACTS: dict[str, dict[str, Any]] = {
    "relief_wounded": {"attitude": 15, "importance": MemoryImportance.SIGNIFICANT},
    "spare_enemy": {"attitude": 10, "importance": MemoryImportance.NOTABLE},
    "help_innocent": {"attitude": 15, "importance": MemoryImportance.SIGNIFICANT},
    "donate_to_temple": {"attitude": 5, "importance": MemoryImportance.NOTABLE},
    "trade": {"attitude": 3, "importance": MemoryImportance.NOTABLE},
    "talk": {"attitude": 1, "importance": MemoryImportance.TRIVIAL},
    "defeat_monster": {"attitude": 2, "importance": MemoryImportance.NOTABLE},
    "attack": {"attitude": -15, "importance": MemoryImportance.SIGNIFICANT},
    "attack_innocent": {"attitude": -20, "importance": MemoryImportance.CRITICAL},
    "steal": {"attitude": -10, "importance": MemoryImportance.SIGNIFICANT},
    "murder_innocent": {"attitude": -30, "importance": MemoryImportance.CRITICAL},
    "attack_gwen": {"attitude": -25, "importance": MemoryImportance.CRITICAL},
    "good_deed": {"attitude": 10, "importance": MemoryImportance.SIGNIFICANT},
    "evil_deed": {"attitude": -20, "importance": MemoryImportance.CRITICAL},
}

# 会話表示用の行動ラベル (名詞句)
ACTION_LABELS: dict[str, str] = {
    "relief_wounded": "看病",
    "spare_enemy": "見逃し",
    "help_innocent": "人助け",
    "donate_to_temple": "神殿への寄付",
    "trade": "取引",
    "talk": "世間話",
    "defeat_monster": "魔物退治",
    "attack": "襲撃",
    "attack_innocent": "無辜の民への暴行",
    "steal": "盗み",
    "murder_innocent": "殺人",
    "attack_gwen": "グウェンへの暴行",
    "good_deed": "善行",
    "evil_deed": "悪事",
}


def get_player_action_impact(action: str) -> dict[str, Any]:
    """行動の態度影響定義を返す (未知の行動は中立・通常重要度)"""
    return dict(PLAYER_ACTION_IMPACTS.get(action, _NEUTRAL_IMPACT))


def attitude_disposition(attitude: int) -> str:
    """態度値から NPC の態度ラベルを返す"""
    if attitude >= 50:
        return "信頼"
    if attitude >= 20:
        return "友好的"
    if attitude > -20:
        return "中立"
    if attitude > -50:
        return "警戒"
    return "敵対的"


@dataclass
class MemoryEntry:
    """単一記憶エントリ"""

    memory_type: MemoryType
    content: dict[str, Any]  # 記憶の詳細データ
    importance: MemoryImportance = MemoryImportance.NOTABLE
    timestamp: float = field(default_factory=time.time)
    source_npc_id: str | None = None  # 直接体験なら None、伝聞なら発信者
    tags: list[str] = field(default_factory=list)  # 検索用タグ
    decay_rate: float = 0.0  # カスタム減衰率（0=デフォルト使用）

    def age(self, current_time: float | None = None) -> float:
        """経過時間（秒）を返す"""
        return (current_time or time.time()) - self.timestamp

    def current_strength(
        self, current_time: float | None = None, base_decay: float = 0.0001
    ) -> float:
        """現在の記憶強度（0.0-1.0）を返す。重要度で減衰調整。"""
        elapsed = self.age(current_time)
        effective_decay = self.decay_rate or (base_decay / max(1, self.importance.value))
        return max(0.0, 1.0 - elapsed * effective_decay)


class NPCMemoryManager:
    """NPC 単位の記憶管理"""

    def __init__(self, npc: Entity):
        self.npc = npc
        self._memories: list[MemoryEntry] = []

    def add_memory(
        self,
        memory_type: MemoryType,
        content: dict[str, Any],
        importance: MemoryImportance = MemoryImportance.NOTABLE,
        source_npc_id: str | None = None,
        tags: list[str] | None = None,
        decay_rate: float = 0.0,
        timestamp: float | None = None,
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
        details: dict[str, Any] | None = None,
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
        target_id: str | None = None,
        location: tuple[int, int] | None = None,
        importance: MemoryImportance = MemoryImportance.NOTABLE,
        timestamp: float | None = None,
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
            timestamp=timestamp,
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
        details: dict[str, Any] | None = None,
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

    def record_player_action(
        self,
        action: str,
        player_id: str = "player",
        amount: int = 1,
        timestamp: float | None = None,
        details: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """プレイヤーの重要行動を記憶へ登録する (態度変化の素)

        行動は PLAYER_ACTION_IMPACTS に基づき態度変化量付きで記録される。
        未知の行動も中立の記憶として残る (態度は動かない)。
        """
        impact = get_player_action_impact(action)
        return self.add_memory(
            memory_type=MemoryType.PERSONAL_INTERACTION,
            content={
                "action": action,
                "actor_id": player_id,
                "amount": amount,
                "delta_attitude": impact["attitude"] * amount,
                "details": details or {},
            },
            importance=impact["importance"],
            # player_action:<id> はアクター別の精密検索用タグ
            tags=["player_action", f"player_action:{player_id}", player_id, action],
            timestamp=timestamp,
        )

    def get_attitude_towards(
        self, actor_id: str = "player", current_time: float | None = None
    ) -> int:
        """記憶から対象アクターへの態度値 (-100..100) を集計する

        直接体験 (個人的交流) を最重視し、目撃・伝聞 (噂) は係数 0.5 で
        減衰して合算する。減衰した記憶の影響も半減する (記憶が消えれば
        態度への影響も消える)。
        """
        total = 0.0
        for mem in self.query(current_time=current_time):
            content = mem.content
            delta: float | None = None
            if (
                mem.memory_type == MemoryType.PERSONAL_INTERACTION
                and content.get("actor_id") == actor_id
            ):
                delta = float(content.get("delta_attitude", 0))
            elif (
                mem.memory_type == MemoryType.WITNESS
                and content.get("actor_id") == actor_id
            ):
                delta = get_player_action_impact(content.get("action", ""))["attitude"] * 0.5
            elif (
                mem.memory_type == MemoryType.REPUTATION_EVENT
                and content.get("subject_id") == actor_id
            ):
                delta = float(content.get("delta", 0)) * 0.5
            if delta is None:
                continue
            strength = mem.current_strength(current_time)
            total += delta * (0.5 + 0.5 * strength)
        # round にすることで記録直後の僅かな時間経過でも意図した値を保つ
        return round(max(float(ATTITUDE_MIN), min(float(ATTITUDE_MAX), total)))

    def sync_attitude_effects(
        self, actor_id: str = "player", current_time: float | None = None
    ) -> int:
        """態度値を NPC の好感度 (affection) へ反映し、適用後の好感度を返す"""
        attitude = self.get_attitude_towards(actor_id, current_time)
        affection = max(0, min(100, AFFECTION_BASE + attitude // 2))
        try:
            self.npc.affection = affection
        except Exception:
            # AffectionComponent 未装着の Entity は getter が例外を出すため無視する
            pass
        return affection

    def query(
        self,
        memory_type: MemoryType | None = None,
        tags: list[str] | None = None,
        min_strength: float = 0.0,
        current_time: float | None = None,
        limit: int = 50,
    ) -> list[MemoryEntry]:
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

    def get_quest_memory(self, quest_id: str) -> MemoryEntry | None:
        """特定クエストの最新記憶を取得"""
        matches = self.query(memory_type=MemoryType.QUEST_RESULT, tags=[quest_id], limit=1)
        return matches[0] if matches else None

    def get_witness_of(self, actor_id: str, action: str | None = None) -> list[MemoryEntry]:
        """特定アクターの目撃記憶を取得"""
        tags = ["witness", actor_id]
        if action:
            tags.append(action)
        return self.query(memory_type=MemoryType.WITNESS, tags=tags)

    def get_reputation_towards(self, subject_id: str) -> list[MemoryEntry]:
        """特定対象への評判記憶を取得"""
        return self.query(memory_type=MemoryType.REPUTATION_EVENT, tags=[subject_id])

    def decay_and_cleanup(
        self, current_time: float | None = None, min_strength: float = 0.01
    ) -> int:
        """減衰処理と弱い記憶の削除。削除数を返す。"""
        original = len(self._memories)
        self._memories = [
            m for m in self._memories if m.current_strength(current_time) >= min_strength
        ]
        return original - len(self._memories)

    def get_summary(self, current_time: float | None = None) -> dict[str, Any]:
        """記憶サマリ（デバッグ・UI用）"""
        by_type: dict[str, int] = {}
        for m in self._memories:
            by_type[m.memory_type.name] = by_type.get(m.memory_type.name, 0) + 1
        return {
            "total": len(self._memories),
            "by_type": by_type,
            "avg_strength": sum(m.current_strength(current_time) for m in self._memories)
            / max(1, len(self._memories)),
        }


class GlobalMemoryRegistry:
    """全NPCの記憶を管理するレジストリ（ゲームエンジン保持用）"""

    def __init__(self):
        self._managers: dict[str, NPCMemoryManager] = {}

    def get(self, npc: Entity) -> NPCMemoryManager:
        """NPC の記憶マネージャを取得（遅延生成）"""
        nid = npc.name  # 識別子として名前を使用（必要なら UUID 等に変更）
        if nid not in self._managers:
            self._managers[nid] = NPCMemoryManager(npc)
        return self._managers[nid]

    def get_by_id(self, npc_id: str) -> NPCMemoryManager | None:
        return self._managers.get(npc_id)

    def record_player_action(
        self,
        npc: Entity,
        action: str,
        player_id: str = "player",
        amount: int = 1,
        timestamp: float | None = None,
    ) -> MemoryEntry:
        """対象 NPC の記憶へプレイヤー行動を登録する"""
        return self.get(npc).record_player_action(
            action, player_id=player_id, amount=amount, timestamp=timestamp
        )

    def get_attitude(
        self, npc_id: str, actor_id: str = "player", current_time: float | None = None
    ) -> int | None:
        """登録済み NPC の対象アクターへの態度値を取得する (未登録なら None)"""
        mgr = self._managers.get(npc_id)
        if mgr is None:
            return None
        return mgr.get_attitude_towards(actor_id, current_time)

    def all_managers(self) -> dict[str, NPCMemoryManager]:
        return dict(self._managers)

    def global_decay(self, current_time: float | None = None, min_strength: float = 0.01) -> int:
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


# =============================================================================
# 統合フック: プレイヤー行動 → 記憶 → 態度 → 噂 (T43 案A)
# =============================================================================


def _record_witness_memories(
    engine: Any,
    target: Entity,
    action: str,
    player_id: str,
    timestamp: float | None,
) -> list[Entity]:
    """行動を目撃できる範囲の生存 NPC に目撃記憶を登録し、目撃者を返す"""
    em = getattr(engine, "entity_manager", None) if engine is not None else None
    if em is None:
        return []
    try:
        candidates = em.get_living_entities()
        tx, ty = getattr(target, "x", None), getattr(target, "y", None)
        if not isinstance(tx, (int, float)) or not isinstance(ty, (int, float)):
            return []
        player = getattr(engine, "player", None)
        target_id = getattr(target, "name", None)
        witnesses: list[Entity] = []
        for e in candidates:
            if e is target or e is player:
                continue
            ex, ey = getattr(e, "x", None), getattr(e, "y", None)
            if not isinstance(ex, (int, float)) or not isinstance(ey, (int, float)):
                continue
            if max(abs(ex - tx), abs(ey - ty)) > WITNESS_RADIUS:
                continue
            mgr = GLOBAL_MEMORY_REGISTRY.get(e)
            mgr.record_witness(
                player_id,
                action,
                target_id=target_id,
                location=(tx, ty),
                timestamp=timestamp,
            )
            mgr.sync_attitude_effects(player_id, timestamp)
            witnesses.append(e)
        return witnesses
    except Exception:
        # 生存 NPC 一覧を取得できない環境では目撃記録を諦める
        return []


def _inject_action_rumor(
    engine: Any,
    target: Entity,
    action: str,
    player_id: str,
    amount: int,
    witness: Entity | None,
) -> Any | None:
    """重要な行動を目撃者の噂として伝播ネットワークへ注入する (失敗時は None)"""
    try:
        from rumor_propagation_system import RumorEngine

        rumor_engine = getattr(engine, "rumor_engine", None) if engine is not None else None
        if rumor_engine is None:
            rumor_engine = RumorEngine(engine)
            try:
                engine.rumor_engine = rumor_engine
            except Exception:
                pass
        origin = witness if witness is not None else target
        location = (
            getattr(origin, "x", 0) if isinstance(getattr(origin, "x", 0), (int, float)) else 0,
            getattr(origin, "y", 0) if isinstance(getattr(origin, "y", 0), (int, float)) else 0,
        )
        return rumor_engine.inject_player_action_rumor(
            action,
            actor_id=player_id,
            origin_npc=origin,
            origin_location=location,
            amount=amount,
        )
    except Exception:
        return None


def notify_player_action(
    engine: Any,
    target: Entity,
    action: str,
    player: Any = None,
    amount: int = 1,
    spread: bool = True,
    timestamp: float | None = None,
) -> dict[str, Any]:
    """プレイヤーの重要行動を NPC の記憶・態度・噂へ反映する統合フック

    1. 対象 NPC の記憶へ行動を登録する
    2. 記憶から態度値を再計算し、好感度 (affection) へ反映する
    3. 周囲の生存 NPC に目撃記憶を登録し、各自の態度へ反映する
    4. 重要度が高い行動は目撃者の噂として伝播ネットワークへ注入し、
       以後の伝播ステップで NPC 間へ拡散する

    戻り値: {"attitude": 態度値, "affection": 好感度, "witnesses": 目撃者
    リスト, "rumor": 生成された噂 or None} の辞書
    """
    player_id = getattr(player, "name", "player") if player is not None else "player"
    mgr = GLOBAL_MEMORY_REGISTRY.get(target)
    mgr.record_player_action(action, player_id=player_id, amount=amount, timestamp=timestamp)
    attitude = mgr.get_attitude_towards(player_id, timestamp)
    affection = mgr.sync_attitude_effects(player_id, timestamp)
    witnesses = _record_witness_memories(engine, target, action, player_id, timestamp)

    rumor = None
    if spread and get_player_action_impact(action)["importance"].value >= MemoryImportance.SIGNIFICANT.value:
        rumor = _inject_action_rumor(
            engine, target, action, player_id, amount, witnesses[0] if witnesses else None
        )
    return {"attitude": attitude, "affection": affection, "witnesses": witnesses, "rumor": rumor}


def build_memory_dialogue_line(
    npc: Entity, player_id: str = "player", current_time: float | None = None
) -> str | None:
    """NPC のプレイヤーに関する記憶から会話用の一言を生成する (記憶が無ければ None)

    dialogue_system から参照される。記憶を持つ NPC しかプレイヤーの
    過去の行動に言及できない (情報非対称の表現)。
    """
    npc_id = getattr(npc, "name", None)
    if not npc_id:
        return None
    mgr = GLOBAL_MEMORY_REGISTRY.get_by_id(npc_id)
    if mgr is None:
        return None
    memories = mgr.query(
        tags=[f"player_action:{player_id}"], current_time=current_time, limit=1
    )
    if not memories:
        return None
    memory = memories[0]
    action = memory.content.get("action", "")
    label = ACTION_LABELS.get(action, action or "何か")
    if memory.memory_type == MemoryType.PERSONAL_INTERACTION:
        positive = memory.content.get("delta_attitude", 0) >= 0
    else:
        # 目撃など: 行動の影響定義から極性を判断する
        positive = get_player_action_impact(action)["attitude"] >= 0
    attitude = mgr.get_attitude_towards(player_id, current_time)
    if positive:
        if attitude >= 50:
            return f"「この前の{label}、覚えているよ。本当に助かった。感謝している。」"
        return f"「そういえば、{label}の時のことも覚えているよ。悪くない奴だ。」"
    if attitude <= -50:
        return f"「……お前の{label}をこの目で見た。近づくな。」"
    return f"「お前の{label}はもう忘れない。信用できんよ。」"


__all__ = [
    "ACTION_LABELS",
    "AFFECTION_BASE",
    "ATTITUDE_MAX",
    "ATTITUDE_MIN",
    "GLOBAL_MEMORY_REGISTRY",
    "GlobalMemoryRegistry",
    "MemoryEntry",
    "MemoryImportance",
    "MemoryType",
    "NPCMemoryManager",
    "PLAYER_ACTION_IMPACTS",
    "WITNESS_RADIUS",
    "attitude_disposition",
    "build_memory_dialogue_line",
    "get_player_action_impact",
    "notify_player_action",
]
