"""
NPC Relationship Simulation - Event-Driven Relationship Updates
Step 6: Event-driven relationship updates
"""

from __future__ import annotations

import logging
logger = logging.getLogger(__name__)
import time
from collections import defaultdict
from collections.abc import Callable
from enum import Enum
from typing import Any

from core_framework import EventBus

from .dynamics import DynamicRelationshipSystem
from .engine import RelationshipManager
from .models import InteractionType


class GameEventType(Enum):
    """ゲーム内イベントタイプ（関係システムとマッピング）"""

    # 会話関連
    PLAYER_TALK_NPC = "player_talk_npc"
    NPC_TALK_PLAYER = "npc_talk_player"
    NPC_TALK_NPC = "npc_talk_npc"

    # アイテム関連
    PLAYER_GIVE_ITEM_NPC = "player_give_item_npc"
    NPC_GIVE_ITEM_PLAYER = "npc_give_item_player"
    PLAYER_STEAL_FROM_NPC = "player_steal_from_npc"
    NPC_STEAL_FROM_PLAYER = "npc_steal_from_player"

    # クエスト関連
    QUEST_ACCEPTED = "quest_accepted"
    QUEST_COMPLETED = "quest_completed"
    QUEST_FAILED = "quest_failed"
    QUEST_SHARED_COMPLETION = "quest_shared_completion"  # 多プレイヤークエスト

    # 戦闘関連
    COMBAT_ALLIED = "combat_allied"
    COMBAT_ENEMY = "combat_enemy"
    PLAYER_RESCUED_NPC = "player_rescued_npc"
    NPC_RESCUED_PLAYER = "npc_rescued_player"
    PLAYER_RESCUED_BY_NPC = "player_rescued_by_npc"

    # 社会的関連
    PLAYER_CONFESSED_TO_NPC = "player_confessed_to_npc"
    NPC_CONFESSED_TO_PLAYER = "npc_confessed_to_player"
    PLAYER_ARGUED_WITH_NPC = "player_argued_with_npc"
    NPC_ARGUED_WITH_PLAYER = "npc_argued_with_player"

    # 知識・スキル関連
    KNOWLEDGE_SHARED = "knowledge_shared"
    SKILL_TAUGHT = "skill_taught"
    MENTORSHIP_ESTABLISHED = "mentorship_established"

    # 取引関連
    TRADE_COMPLETED = "trade_completed"
    TRADE_FAILED = "trade_failed"
    CREDIT_EXTENDED = "credit_extended"
    DEFAULT_ON_DEBT = "default_on_debt"

    # 家族・派閥関連
    FAMILY_EVENT = "family_event"
    FACTION_JOINED = "faction_joined"
    FACTION_LEFT = "faction_left"
    FACTION_CONFLICT = "faction_conflict"

    # 特殊イベント
    BETRAYAL_DISCOVERED = "betrayal_discovered"
    RECONCILIATION_ATTEMPTED = "reconciliation_attempted"
    CELEBRATION_SHARED = "celebration_shared"
    GRIEF_SHARED = "grief_shared"


class EventToInteractionMapper:
    """ゲームイベントを関係インタラクションタイプにマッピングするクラス"""

    # イベントタイプとインタラクションタイプのマッピング
    EVENT_INTERACTION_MAP = {
        GameEventType.PLAYER_TALK_NPC: InteractionType.TALK,
        GameEventType.NPC_TALK_PLAYER: InteractionType.TALK,
        GameEventType.NPC_TALK_NPC: InteractionType.TALK,
        GameEventType.PLAYER_GIVE_ITEM_NPC: InteractionType.GIFT,
        GameEventType.NPC_GIVE_ITEM_PLAYER: InteractionType.GIFT,
        GameEventType.PLAYER_STEAL_FROM_NPC: InteractionType.BETRAYAL,
        GameEventType.NPC_STEAL_FROM_PLAYER: InteractionType.BETRAYAL,
        GameEventType.QUEST_COMPLETED: InteractionType.QUEST_COOPERATION,
        GameEventType.QUEST_FAILED: InteractionType.QUEST_CONFLICT,
        GameEventType.QUEST_SHARED_COMPLETION: InteractionType.QUEST_COOPERATION,
        GameEventType.COMBAT_ALLIED: InteractionType.COMBAT_ALLY,
        GameEventType.COMBAT_ENEMY: InteractionType.COMBAT_ENEMY,
        GameEventType.PLAYER_RESCUED_NPC: InteractionType.RESCUE,
        GameEventType.NPC_RESCUED_PLAYER: InteractionType.RESCUE,
        GameEventType.PLAYER_RESCUED_BY_NPC: InteractionType.RESCUE,
        GameEventType.PLAYER_CONFESSED_TO_NPC: InteractionType.CONFESSION,
        GameEventType.NPC_CONFESSED_TO_PLAYER: InteractionType.CONFESSION,
        GameEventType.PLAYER_ARGUED_WITH_NPC: InteractionType.ARGUMENT,
        GameEventType.NPC_ARGUED_WITH_PLAYER: InteractionType.ARGUMENT,
        GameEventType.KNOWLEDGE_SHARED: InteractionType.KNOWLEDGE_SHARE,
        GameEventType.SKILL_TAUGHT: InteractionType.KNOWLEDGE_SHARE,
        GameEventType.MENTORSHIP_ESTABLISHED: InteractionType.KNOWLEDGE_SHARE,
        GameEventType.TRADE_COMPLETED: InteractionType.TRADE,
        GameEventType.TRADE_FAILED: InteractionType.TRADE,  # 失敗でも取引試行として扱う
        GameEventType.CREDIT_EXTENDED: InteractionType.TRADE,
        GameEventType.DEFAULT_ON_DEBT: InteractionType.BETRAYAL,
    }

    # イベントタイプとベース変更量のマッピング
    EVENT_BASE_AMOUNT_MAP = {
        GameEventType.PLAYER_TALK_NPC: 2,
        GameEventType.NPC_TALK_PLAYER: 2,
        GameEventType.NPC_TALK_NPC: 1,
        GameEventType.PLAYER_GIVE_ITEM_NPC: 10,
        GameEventType.NPC_GIVE_ITEM_PLAYER: 10,
        GameEventType.PLAYER_STEAL_FROM_NPC: -15,
        GameEventType.NPC_STEAL_FROM_PLAYER: -15,
        GameEventType.QUEST_COMPLETED: 15,
        GameEventType.QUEST_FAILED: -5,
        GameEventType.QUEST_SHARED_COMPLETION: 20,
        GameEventType.COMBAT_ALLIED: 8,
        GameEventType.COMBAT_ENEMY: -10,
        GameEventType.PLAYER_RESCUED_NPC: 25,
        GameEventType.NPC_RESCUED_PLAYER: 25,
        GameEventType.PLAYER_RESCUED_BY_NPC: 20,
        GameEventType.PLAYER_CONFESSED_TO_NPC: 18,
        GameEventType.NPC_CONFESSED_TO_PLAYER: 18,
        GameEventType.PLAYER_ARGUED_WITH_NPC: -12,
        GameEventType.NPC_ARGUED_WITH_PLAYER: -12,
        GameEventType.KNOWLEDGE_SHARED: 12,
        GameEventType.SKILL_TAUGHT: 15,
        GameEventType.MENTORSHIP_ESTABLISHED: 20,
        GameEventType.TRADE_COMPLETED: 8,
        GameEventType.TRADE_FAILED: -3,
        GameEventType.CREDIT_EXTENDED: 10,
        GameEventType.DEFAULT_ON_DEBT: -20,
    }

    @classmethod
    def get_interaction_type(cls, event_type: GameEventType) -> InteractionType | None:
        """イベントタイプからインタラクションタイプを取得"""
        return cls.EVENT_INTERACTION_MAP.get(event_type)

    @classmethod
    def get_base_amount(cls, event_type: GameEventType) -> int:
        """イベントタイプからベース変更量を取得"""
        return cls.EVENT_BASE_AMOUNT_MAP.get(event_type, 0)


class RelationshipEventHandler:
    """
    関係システムのイベントハンドラー
    ゲームイベントを監聴し、関係変更に変換する
    """

    def __init__(self, relationship_manager: RelationshipManager):
        self.rm = relationship_manager
        self.dynamic_system = DynamicRelationshipSystem(relationship_manager)
        self.event_bus = EventBus()  # EventBusインスタンスを使用

        # イベントハンドラーの登録
        self._register_event_handlers()

        # カスタムマッピング（特殊ケース用）
        self._custom_event_handlers: dict[GameEventType, list[Callable]] = defaultdict(
            list
        )

        # イベント統計
        self._event_stats: dict[GameEventType, int] = defaultdict(int)
        self._last_event_time: float = 0

    def _register_event_handlers(self) -> None:
        """すべてのゲームイベントタイプのハンドラーを登録"""
        for event_type in GameEventType:
            self.event_bus.subscribe(event_type.value, self._handle_game_event)

    def _handle_game_event(self, event_data: Any) -> None:
        """ゲームイベントを処理"""
        if not isinstance(event_data, dict):
            return

        event_type_str = event_data.get("event_type")
        if not event_type_str:
            return

        try:
            event_type = GameEventType(event_type_str)
        except ValueError:
            # 未知のイベントタイプは無視
            return

        # 統計を更新
        self._event_stats[event_type] += 1
        self._last_event_time = time.time()

        # カスタムハンドラーを優先実行
        if event_type in self._custom_event_handlers:
            for handler in self._custom_event_handlers[event_type]:
                try:
                    handler(event_data)
                except Exception as e:
                    print(f"Error in custom event handler for {event_type}: {e}")
                    logger.exception("Unhandled exception")
            # カスタムハンドラーが処理した場合は標準処理をスキップ
            if self._custom_event_handlers[event_type]:
                return

        # 標準処理を実行
        self._process_standard_event(event_type, event_data)

    def _process_standard_event(
        self, event_type: GameEventType, event_data: dict[str, Any]
    ) -> None:
        """標準的なゲームイベントを処理"""
        # マッピングを取得
        interaction_type = EventToInteractionMapper.get_interaction_type(event_type)
        base_amount = EventToInteractionMapper.get_base_amount(event_type)

        if interaction_type is None or base_amount == 0:
            return  # マッピングがないか、変更量がゼロの場合はスキップ

        # イベントデータから関係当事者を取得
        source_id = event_data.get("source_id")
        target_id = event_data.get("target_id")

        if not source_id or not target_id:
            return  # 必要な情報が不足している場合はスキップ

        # コンテキスト情報を準備
        context = {
            "event_type": event_type.value,
            "timestamp": time.time(),
            "location": event_data.get("location", "unknown"),
            "details": event_data.get("details", {}),
        }

        # 特定のイベントタイプに応じたコンテキスト enrichment
        self._enrich_context(event_type, context, event_data)

        # ダイナミックシステムを使用して関係を変更
        try:
            changes = self.dynamic_system.apply_interaction_with_dynamics(
                source_id, target_id, interaction_type, base_amount, context
            )

            # 変更があった場合はイベントを発行（デバッグや他のシステム用）
            if changes:
                self.event_bus.publish(
                    "RELATIONSHIP_UPDATED",
                    {
                        "source_id": source_id,
                        "target_id": target_id,
                        "changes": changes,
                        "event_type": event_type.value,
                        "timestamp": time.time(),
                    },
                )

        except Exception as e:
            logger.exception("Unhandled exception")
            print(f"Error processing relationship event {event_type}: {e}")

    def _enrich_context(
        self,
        event_type: GameEventType,
        context: dict[str, Any],
        event_data: dict[str, Any],
    ) -> None:
        """イベントタイプに応じてコンテキストを enrichment"""
        # クエスト関連イベント
        if event_type in [
            GameEventType.QUEST_COMPLETED,
            GameEventType.QUEST_FAILED,
            GameEventType.QUEST_SHARED_COMPLETION,
        ]:
            context.update(
                {
                    "quest_id": event_data.get("quest_id"),
                    "quest_difficulty": event_data.get("quest_difficulty", 1.0),
                    "party_size": event_data.get("party_size", 1),
                }
            )

        # 戦闘関連イベント
        elif event_type in [GameEventType.COMBAT_ALLIED, GameEventType.COMBAT_ENEMY]:
            context.update(
                {
                    "combat_duration": event_data.get("combat_duration", 0),
                    "enemy_strength": event_data.get("enemy_strength", 1.0),
                    "allies_count": event_data.get("allies_count", 0),
                    "enemies_count": event_data.get("enemies_count", 0),
                }
            )

        # 会話関連イベント
        elif event_type in [
            GameEventType.PLAYER_TALK_NPC,
            GameEventType.NPC_TALK_PLAYER,
        ]:
            context.update(
                {
                    "conversation_length": event_data.get("conversation_length", 1.0),
                    "topics_discussed": event_data.get("topics_discussed", []),
                    "mood_before": event_data.get("mood_before", "neutral"),
                }
            )

        # アイテム関連イベント
        elif event_type in [
            GameEventType.PLAYER_GIVE_ITEM_NPC,
            GameEventType.NPC_GIVE_ITEM_PLAYER,
        ]:
            context.update(
                {
                    "item_value": event_data.get("item_value", 0),
                    "item_rarity": event_data.get("item_rarity", "common"),
                    "is_heirloom": event_data.get("is_heirloom", False),
                }
            )

        # 社会的関連イベント
        elif event_type in [
            GameEventType.PLAYER_CONFESSED_TO_NPC,
            GameEventType.NPC_CONFESSED_TO_PLAYER,
        ]:
            context.update(
                {
                    "relationship_length": event_data.get("relationship_length", 0.0),
                    "previous_conflicts": event_data.get("previous_conflicts", 0),
                    "is_public": event_data.get("is_public", False),
                }
            )

        elif event_type in [
            GameEventType.PLAYER_ARGUED_WITH_NPC,
            GameEventType.NPC_ARGUED_WITH_PLAYER,
        ]:
            context.update(
                {
                    "argument_topic": event_data.get("argument_topic", "unknown"),
                    "severity": event_data.get("severity", 1.0),
                    "witnesses_present": event_data.get("witnesses_present", 0),
                }
            )

        # 取引関連イベント
        elif event_type in [
            GameEventType.TRADE_COMPLETED,
            GameEventType.TRADE_FAILED,
            GameEventType.CREDIT_EXTENDED,
            GameEventType.DEFAULT_ON_DEBT,
        ]:
            context.update(
                {
                    "trade_value": event_data.get("trade_value", 0),
                    "trade_goods": event_data.get("trade_goods", []),
                    "credit_amount": event_data.get("credit_amount", 0),
                    "repayment_terms": event_data.get("repayment_terms", {}),
                }
            )

        # 家族・派閥関連イベント
        elif event_type == GameEventType.FAMILY_EVENT:
            context.update(
                {
                    "event_subtype": event_data.get("event_subtype", "gathering"),
                    "family_member_type": event_data.get(
                        "family_member_type", "relative"
                    ),
                    "generation_distance": event_data.get("generation_distance", 1),
                }
            )

        elif event_type in [GameEventType.FACTION_JOINED, GameEventType.FACTION_LEFT]:
            context.update(
                {
                    "faction_id": event_data.get("faction_id"),
                    "faction_rank_before": event_data.get("faction_rank_before"),
                    "faction_rank_after": event_data.get("faction_rank_after"),
                }
            )

        # 特殊イベント
        elif event_type == GameEventType.BETRAYAL_DISCOVERED:
            context.update(
                {
                    "betrayal_type": event_data.get("betrayal_type", "unknown"),
                    "damage_amount": event_data.get("damage_amount", 0),
                    "witnesses": event_data.get("witnesses", []),
                    "proof_available": event_data.get("proof_available", False),
                }
            )

        elif event_type == GameEventType.RECONCILIATION_ATTEMPTED:
            context.update(
                {
                    "time_since_betrayal": event_data.get("time_since_betrayal", 0.0),
                    "mediator_present": event_data.get("mediator_present", False),
                    "willingness_level": event_data.get("willingness_level", 0.5),
                }
            )

    def register_custom_event_handler(
        self, event_type: GameEventType, handler: Callable[[dict[str, Any]], None]
    ) -> None:
        """カスタムイベントハンドラーを登録"""
        self._custom_event_handlers[event_type].append(handler)

    def unregister_custom_event_handler(
        self, event_type: GameEventType, handler: Callable[[dict[str, Any]], None]
    ) -> None:
        """カスタムイベントハンドラーの登録を解除"""
        if event_type in self._custom_event_handlers:
            try:
                self._custom_event_handlers[event_type].remove(handler)
            except ValueError:
                pass  # ハンドラーが見つからない場合は無視

    def get_event_statistics(self) -> dict[GameEventType, int]:
        """イベント統計を取得"""
        return dict(self._event_stats)

    def get_last_event_time(self) -> float:
        """最後のイベント時間を取得"""
        return self._last_event_time

    def shutdown(self) -> None:
        """イベントハンドラーの登録を解除（メモリリーク防止）"""
        for event_type in GameEventType:
            self.event_bus.unsubscribe(event_type.value, self._handle_game_event)


# グローバルインスタンス（オプション）
_global_event_handler: RelationshipEventHandler | None = None


def initialize_event_handler(
    relationship_manager: RelationshipManager,
) -> RelationshipEventHandler:
    """グローバルイベントハンドラーを初期化"""
    global _global_event_handler
    _global_event_handler = RelationshipEventHandler(relationship_manager)
    return _global_event_handler


def get_event_handler() -> RelationshipEventHandler | None:
    """グローバルイベントハンドラーを取得"""
    return _global_event_handler


def shutdown_event_handler() -> None:
    """グローバルイベントハンドラーをシャットダウン"""
    global _global_event_handler
    if _global_event_handler:
        _global_event_handler.shutdown()
        _global_event_handler = None
