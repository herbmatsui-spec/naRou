"""
System Initializer Module
Encapsulates UI managers, background web server, and visual FX system instantiation from game.py Engine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ui_fx_systems import ContextMenu, LookCursor, NotificationManager, TutorialManager
from web_server import start_web_server

if TYPE_CHECKING:
    from game import Engine


class SystemInitializer:
    """Handles instantiation and lifecycle setup for auxiliary subsystems like UI tools, tutorials, and Web server."""

    @staticmethod
    def initialize_ui_and_services(
        engine: Engine,
    ) -> tuple[LookCursor, ContextMenu, TutorialManager, NotificationManager, any]:
        """Instantiate UI tools, notification managers, and background web server."""
        look_cursor = LookCursor(
            engine.game_state_data.player.x, engine.game_state_data.player.y
        )
        context_menu = ContextMenu()
        tutorial_manager = TutorialManager()
        notification_manager = NotificationManager()
        web_server = start_web_server(engine, port=8080)

        return (
            look_cursor,
            context_menu,
            tutorial_manager,
            notification_manager,
            web_server,
        )
