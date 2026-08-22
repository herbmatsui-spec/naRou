"""
UI Event Panel Module
Provides data for displaying event information in the UI.
"""

from __future__ import annotations

from typing import Any

from entity import Entity  # For type hinting
from ranking_manager import RANKING_MANAGER
from time_system import TimePhase, get_world_clock
from title_manager import TITLE_MANAGER
from world_event_system import EVENT_SCHEDULER


def get_current_event_info(current_turn: int) -> dict[str, Any]:
    """
    現在のアクティブイベント情報を取得する。
    :param current_turn: 現在のターン数
    :return: イベント情報の辞書
    """
    event_data = EVENT_SCHEDULER.get_current_seasonal_event(current_turn)
    if not event_data:
        return {"active": False}

    # イベントの残りターンを計算（簡易実装）
    remaining_turns = 0
    if hasattr(event_data, "end_turn") and event_data.end_turn is not None:
        remaining_turns = max(0, event_data.end_turn - current_turn)
    elif hasattr(event_data, "duration"):
        # ダURATIONから推定（実際には開始ターンが必要）
        remaining_turns = event_data.duration  # プレースホルダー

    return {
        "active": True,
        "id": event_data.id,
        "name": event_data.name,
        "description": event_data.description,
        "remaining_turns": remaining_turns,
        "quarter": getattr(event_data, "quarter", None),
        "effects": event_data.effects,
    }


def get_event_ranking(event_id: str, top_n: int = 10) -> list:
    """
    指定されたイベントのランキングを取得する。
    :param event_id: イベントID
    :param top_n: 上位何位を取得するか
    :return: ランキングリスト [(player_id, score), ...]
    """
    return RANKING_MANAGER.get_ranking(event_id)[:top_n]


def get_player_event_score(event_id: str, player_id: str) -> int:
    """
    プレイヤーの指定イベントにおけるスコアを取得する。
    :param event_id: イベントID
    :param player_id: プレイヤーID
    :return: スコア
    """
    return RANKING_MANAGER.get_player_score(event_id, player_id)


def get_player_event_titles(player: Entity, event_data: Any) -> list:
    """
    プレイヤーが獲得したイベント固有の称号を取得する。
    :param player: プレイヤーエンティティ
    :param event_data: WorldEventDataオブジェクト
    :return: 称号リスト
    """
    # ここでは簡易的に、プレイヤーの統計がないため空リストを返す
    # 実際には、プレイヤーのイベント統計を渡す必要がある
    return TITLE_MANAGER.get_player_titles(player)


# --- NPCスケジュール表示 (Step 21) ---
def get_active_npcs(player: Entity | None = None) -> list[dict]:
    """現在出現中のNPC一覧取得"""
    clock = get_world_clock()
    return clock.get_active_npc_details(player)


def get_active_npc_names(player: Entity | None = None) -> list[str]:
    """現在出現中のNPC名一覧取得 (簡易表示用)"""
    npcs = get_active_npcs(player)
    return [f"{npc['name']}({npc['location']})" for npc in npcs]


def get_merchant_location(npc_id: str) -> str:
    """移動商人の現在地取得"""
    clock = get_world_clock()
    return clock.get_merchant_location(npc_id)


def get_current_phase_info() -> dict:
    """現在の時間帯情報取得 (UI表示用)"""
    clock = get_world_clock()
    phase = clock.current_phase
    return {
        "phase": phase.name,
        "display_name": phase.display_name,
        "short_name": phase.short_name,
        "hour": clock.hour,
        "minute": clock.minute,
        "time_string": clock.to_string(),
        "hours_until_next": phase.hours_until_next(clock.hour),
    }


# --- 施設稼働表示 (Step 37) ---
def get_facility_efficiency(facility_id: str) -> float:
    """施設効率取得 (UI表示用)"""
    clock = get_world_clock()
    return clock.get_facility_efficiency(facility_id)


def get_facility_status(facility_id: str) -> dict:
    """施設ステータス取得 (UI表示用)"""
    clock = get_world_clock()
    efficiency = clock.get_facility_efficiency(facility_id)
    is_active = clock.is_facility_active(facility_id)
    registry = clock.facility_registry
    facility = registry.get_facility(facility_id)

    if not facility:
        return {"active": False, "efficiency": 0.0, "name": facility_id}

    # 次フェーズでの効率予測
    next_phase = TimePhase.from_hour((clock.hour + 1) % 24)
    next_efficiency = registry.get_efficiency(facility_id, next_phase)

    return {
        "facility_id": facility_id,
        "name": facility.name,
        "type": facility.facility_type.value,
        "active": is_active,
        "efficiency": efficiency,
        "efficiency_percent": int(efficiency * 100),
        "next_efficiency": next_efficiency,
        "next_efficiency_percent": int(next_efficiency * 100),
        "is_24h": facility.is_24h,
    }


def get_all_facility_statuses() -> list[dict]:
    """全施設ステータス取得"""
    clock = get_world_clock()
    return [
        get_facility_status(f.facility_id) for f in clock.facility_registry.get_all_facilities()
    ]


# --- プレイヤー行動表示 (Step 48) ---
def get_available_actions(player: Entity) -> list[dict]:
    """実行可能な行動一覧取得"""
    clock = get_world_clock()
    try:
        from naRou.player_actions import ActionType
    except ImportError:
        from player_actions import ActionType
    actions = []

    for at in ActionType:
        can, msg = clock.can_perform_action(at.value, player)
        cost = clock.action_manager.get_cost(at)
        if cost:
            # 実際の消費時間計算
            actual_hours = cost.base_hours
            if at == ActionType.CRAFT:
                efficiency = clock.get_facility_efficiency("workshop")
                if efficiency > 0:
                    actual_hours = cost.base_hours / efficiency

            actions.append(
                {
                    "action_type": at.value,
                    "display_name": _get_action_display_name(at),
                    "can_perform": can,
                    "message": msg if not can else "実行可能",
                    "base_hours": cost.base_hours,
                    "actual_hours": actual_hours,
                    "stamina_cost": cost.stamina_cost,
                    "mp_cost": cost.mp_cost,
                }
            )
    return actions


def _get_action_display_name(action_type) -> str:
    """行動表示名取得"""
    names = {
        "explore": "探索",
        "craft": "クラフト",
        "sleep": "睡眠",
        "wait": "待機",
        "travel": "移動",
        "train": "訓練",
        "shop": "買い物",
        "talk": "会話",
    }
    return names.get(action_type.value, action_type.value)


def get_action_cost_preview(action_type: str, player: Entity) -> dict:
    """行動コストプレビュー取得"""
    clock = get_world_clock()
    try:
        from naRou.player_actions import ActionType
    except ImportError:
        from player_actions import ActionType
    try:
        at = ActionType(action_type)
    except ValueError:
        return {"error": "不明な行動"}

    cost = clock.action_manager.get_cost(at)
    if not cost:
        return {"error": "コスト未定義"}

    actual_hours = cost.base_hours
    if at == ActionType.CRAFT:
        efficiency = clock.get_facility_efficiency("workshop")
        if efficiency > 0:
            actual_hours = cost.base_hours / efficiency

    can, msg = clock.can_perform_action(at.value, player)

    return {
        "action_type": at.value,
        "display_name": _get_action_display_name(at),
        "base_hours": cost.base_hours,
        "actual_hours": actual_hours,
        "stamina_cost": cost.stamina_cost,
        "mp_cost": cost.mp_cost,
        "can_perform": can,
        "message": msg,
    }
