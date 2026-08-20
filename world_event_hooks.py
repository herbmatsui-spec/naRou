"""
World Event Hooks Module (偏執的クエストシステム / 設計書 Phase 9 Step 32)
ワールドイベント監視バス（戦争/疫病/彗星/継承）。
"""

from __future__ import annotations

from collections.abc import Callable

from world_event_system import WorldEvent, WorldEventSystem, WorldEventType


class EventMonitor:
    """ワールドイベントを監視し、イベント発生・終了時にハンドラーを呼び出す"""

    def __init__(self, event_system: WorldEventSystem | None = None):
        from world_event_system import WORLD_EVENT_SYSTEM

        self.event_system = event_system or WORLD_EVENT_SYSTEM
        self._handlers: dict[WorldEventType, list[Callable[[WorldEvent], None]]] = {
            event_type: [] for event_type in WorldEventType
        }
        self._active_events: dict[WorldEventType, WorldEvent] = {}

    def register_handler(
        self, event_type: WorldEventType, handler: Callable[[WorldEvent], None]
    ) -> None:
        """特定のイベントタイプにハンドラーを登録"""
        if event_type in self._handlers:
            self._handlers[event_type].append(handler)

    def unregister_handler(
        self, event_type: WorldEventType, handler: Callable[[WorldEvent], None]
    ) -> None:
        """ハンドラーの登録を解除"""
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    def update(self) -> None:
        """イベント状態を更新し、変更があればハンドラーを呼び出す"""
        current_events = self.event_system.active_events
        # 新しく開始されたイベントをチェック
        for event_type, event in current_events.items():
            if event.is_active and (
                event_type not in self._active_events
                or not self._active_events[event_type].is_active
            ):
                # イベントが開始された
                self._active_events[event_type] = event
                self._trigger_handlers(event_type, event)
        # 終了したイベントをチェック
        for event_type, event in list(self._active_events.items()):
            if not event.is_active:
                # イベントが終了した
                del self._active_events[event_type]
                # 終了ハンドラーがある場合はここで呼び出す（簡易実装では開始ハンドラーのみ）
                # ここでは終了ハンドラーは別途実装するか、開始ハンドラーに渡すイベントに終了フラグを追加する
                pass

    def _trigger_handlers(self, event_type: WorldEventType, event: WorldEvent) -> None:
        """登録されたハンドラーを呼び出す"""
        for handler in self._handlers.get(event_type, []):
            try:
                handler(event)
            except Exception as e:
                # エラーはログに記録するが、監視を停止しない
                print(f"[EventMonitor Error] Handler for {event_type} failed: {e}")


# グローバルインスタンス
EVENT_MONITOR = EventMonitor()


def monitor_world_event(
    event_type: WorldEventType, handler: Callable[[WorldEvent], None]
) -> None:
    """ワールドイベントのハンドラーを登録するヘルパー関数"""
    EVENT_MONITOR.register_handler(event_type, handler)


def update_world_event_monitor() -> None:
    """ワールドイベント監視を更新するヘルパー関数"""
    EVENT_MONITOR.update()


__all__ = [
    "EventMonitor",
    "EVENT_MONITOR",
    "monitor_world_event",
    "update_world_event_monitor",
]
