"""
Missed Opportunity System (偏執的クエストシステム / 設計書 Phase 9 Step 35)
未完了時の機会喪失記録・NPC会話/エンディング反映。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from entity import Entity  # For type hinting


@dataclass
class MissedOpportunity:
    """機会喪失の記録"""

    opportunity_id: str
    quest_id: str  # 関連するクエストID
    reason: str  # 喪失理由（例: "time_limit", "event_end", "player_death"）
    timestamp: float  # 発生タイムスタンプ
    penalty: dict[str, Any] = field(
        default_factory=dict
    )  # 喪失によるペナルティ（例: 評判低下, アイテム喪失）


class MissedOpportunitySystem:
    """機会喪失を記録・管理するシステム"""

    def __init__(self):
        self._missed_opportunities: list[MissedOpportunity] = []
        self._opportunity_templates: dict[str, dict[str, Any]] = {}  # 機会のテンプレート

    def record_missed_opportunity(
        self,
        opportunity_id: str,
        quest_id: str,
        reason: str,
        timestamp: float | None = None,
        penalty: dict[str, Any] | None = None,
    ) -> None:
        """機会喪失を記録"""
        from time import time

        if timestamp is None:
            timestamp = time()
        opportunity = MissedOpportunity(
            opportunity_id=opportunity_id,
            quest_id=quest_id,
            reason=reason,
            timestamp=timestamp,
            penalty=penalty or {},
        )
        self._missed_opportunities.append(opportunity)

    def get_missed_opportunities(self, quest_id: str | None = None) -> list[MissedOpportunity]:
        """指定したクエストIDに関連する機会喪失を取得（指定がない場合は全て）"""
        if quest_id is None:
            return self._missed_opportunities
        return [opp for opp in self._missed_opportunities if opp.quest_id == quest_id]

    def clear_missed_opportunities(self, quest_id: str | None = None) -> None:
        """機会喪失の記録をクリア（指定がない場合は全て）"""
        if quest_id is None:
            self._missed_opportunities.clear()
        else:
            self._missed_opportunities = [
                opp for opp in self._missed_opportunities if opp.quest_id != quest_id
            ]

    def get_npc_dialogue_modifier(self, entity: Entity) -> str | None:
        """NPC会話に機会喪失を反映する修正テキストを取得"""
        # 簡易実装：プレイヤーが関与した機会喪失がある場合、特別な会話を返す
        # 実際には、エンティティとの関係や過去のイベントに基づいて会話を変える
        # ここでは、プレイヤーが機会喪失を持っているかどうかで会話を変える
        # エンティティがプレイヤーであると仮定
        if hasattr(entity, "missed_opportunities"):
            missed_count = len(getattr(entity, "missed_opportunities", []))
            if missed_count > 0:
                return "…最近、君の行動には少し不安があるようだね。"
        return None

    def get_ending_modifier(self, entity: Entity) -> dict[str, Any]:
        """エンディングに機会喪失を反映する修正を取得"""
        # 簡易実装：機会喪失の数に基づいてエンディングスコアを調整
        if hasattr(entity, "missed_opportunities"):
            missed_count = len(getattr(entity, "missed_opportunities", []))
            # エンディングスコアにマイナス修正を適用
            return {
                "ending_score_modifier": -missed_count * 5,  # 1機会喪失あたり5点減点
                "ending_note": f"機会喪失が{missed_count}回あったため、エンディングに影響がある。",
            }
        return {}


# グローバルインスタンス
MISSED_OPPORTUNITY_SYSTEM = MissedOpportunitySystem()


def record_missed_opportunity(
    opportunity_id: str,
    quest_id: str,
    reason: str,
    timestamp: float | None = None,
    penalty: dict[str, Any] | None = None,
) -> None:
    """機会喪失を記録するヘルパー関数"""
    MISSED_OPPORTUNITY_SYSTEM.record_missed_opportunity(
        opportunity_id, quest_id, reason, timestamp, penalty
    )


def get_missed_opportunities(quest_id: str | None = None) -> list[MissedOpportunity]:
    """機会喪失を取得するヘルパー関数"""
    return MISSED_OPPORTUNITY_SYSTEM.get_missed_opportunities(quest_id)


def clear_missed_opportunities(quest_id: str | None = None) -> None:
    """機会喪失の記録をクリアするヘルパー関数"""
    MISSED_OPPORTUNITY_SYSTEM.clear_missed_opportunities(quest_id)


def get_npc_dialogue_modifier(entity: Entity) -> str | None:
    """NPC会話に機会喪失を反映する修正テキストを取得するヘルパー関数"""
    return MISSED_OPPORTUNITY_SYSTEM.get_npc_dialogue_modifier(entity)


def get_ending_modifier(entity: Entity) -> dict[str, Any]:
    """エンディングに機会喪失を反映する修正を取得するヘルパー関数"""
    return MISSED_OPPORTUNITY_SYSTEM.get_ending_modifier(entity)


__all__ = [
    "MISSED_OPPORTUNITY_SYSTEM",
    "MissedOpportunity",
    "MissedOpportunitySystem",
    "clear_missed_opportunities",
    "get_ending_modifier",
    "get_missed_opportunities",
    "get_npc_dialogue_modifier",
    "record_missed_opportunity",
]
