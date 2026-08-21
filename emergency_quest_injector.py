"""
Emergency Quest Injector Module (偏執的クエストシステム / 設計書 Phase 9 Step 33)
緊急クエスト自動注入（イベント発生中のみ有効）。
"""

from __future__ import annotations

from procedural_quest_generator import ProceduralQuestGenerator
from world_event_hooks import monitor_world_event
from world_event_system import WorldEventType


class EmergencyQuestInjector:
    """ワールドイベント発生中に緊急クエストを依頼ボードに注入"""

    def __init__(self, quest_generator: ProceduralQuestGenerator | None = None):
        from procedural_quest_generator import PROCEDURAL_QUEST_GENERATOR

        self.quest_generator = quest_generator or PROCEDURAL_QUEST_GENERATOR
        self._active = False
        self._emergency_quests: List[GeneratedQuest] = []
        self._register_handlers()

    def _register_handlers(self) -> None:
        """ワールドイベントのハンドラーを登録"""
        monitor_world_event(WorldEventType.WAR, self._on_event_start)
        monitor_world_event(WorldEventType.PLAGUE, self._on_event_start)
        monitor_world_event(WorldEventType.COMET, self._on_event_start)
        monitor_world_event(WorldEventType.INHERITANCE, self._on_event_start)
        # 終了ハンドラーはここでは簡易的に、イベントが非アクティブになったらクエストを削除する
        # 実際には、ワールドイベントシステムがイベントの終了を通知する仕組みが必要
        # ここでは、更新時にチェックする

    def _on_event_start(self, event: WorldEvent) -> None:
        """イベント開始時に緊急クエストを生成"""
        self._generate_emergency_quests()
        self._active = True

    def _generate_emergency_quests(self) -> None:
        """緊急クエストを生成"""
        # 簡易実装：イベントタイプに基づいてクエストを生成
        # 実際には、ワールドイベントの詳細に基づいてクエストを生成する
        from world_event_system import WORLD_EVENT_SYSTEM

        active_event = None
        for event in WORLD_EVENT_SYSTEM.active_events.values():
            if event.is_active:
                active_event = event
                break
        if active_event is None:
            return

        # 緊急クエストを1つ生成（簡易実装）
        # 実際には、複数のクエストを生成するか、イベントの規模に基づいて数を決定する
        quest = self.quest_generator.generate_board_quest()
        if quest is not None:
            # クエストを緊急クエストとしてマークする
            quest.title = f"[緊急] {quest.title}"
            quest.desc = f"[緊急] {quest.desc}"
            # 報酬を増やす（簡易実装）
            if hasattr(quest, "reward") and isinstance(quest.reward, dict):
                quest.reward["gold"] = int(quest.reward.get("gold", 0) * 2)
                quest.reward["exp"] = int(quest.reward.get("exp", 0) * 2)
            self._emergency_quests.append(quest)

    def update(self) -> None:
        """更新：イベントが終了したら緊急クエストをクリア"""
        from world_event_system import WORLD_EVENT_SYSTEM

        any_active = any(
            event.is_active for event in WORLD_EVENT_SYSTEM.active_events.values()
        )
        if not any_active and self._active:
            # イベントが終了したら緊急クエストをクリア
            self._emergency_quests.clear()
            self._active = False

    def inject_emergency_quests(
        self, board_quests: List[GeneratedQuest]
    ) -> List[GeneratedQuest]:
        """依頼ボードのクエストリストに緊急クエストを注入"""
        if not self._active:
            return board_quests
        # 緊急クエストをボードクエストのリストに追加する
        # ただし、ボードの最大数を超えないようにする
        cfg = self.quest_generator.registry.board_config()
        max_active = int(cfg.get("max_active", 8))
        current_count = len(board_quests)
        available_slots = max_active - current_count
        if available_slots > 0:
            # 緊急クエストから利用可能なスロット数だけ追加
            to_add = self._emergency_quests[:available_slots]
            board_quests.extend(to_add)
        return board_quests


# グローバルインスタンス
EMERGENCY_QUEST_INJECTOR = EmergencyQuestInjector()


def inject_emergency_quests(board_quests: List[GeneratedQuest]) -> List[GeneratedQuest]:
    """依頼ボードのクエストリストに緊急クエストを注入するヘルパー関数"""
    return EMERGENCY_QUEST_INJECTOR.inject_emergency_quests(board_quests)


def update_emergency_quest_injector() -> None:
    """緊急クエストインジェクターを更新するヘルパー関数"""
    EMERGENCY_QUEST_INJECTOR.update()


__all__ = [
    "EMERGENCY_QUEST_INJECTOR",
    "EmergencyQuestInjector",
    "inject_emergency_quests",
    "update_emergency_quest_injector",
]
