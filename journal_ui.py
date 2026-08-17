"""
Journal UI System Module
Handles the rendering and interaction of the Adventurer's Journal.
"""

from __future__ import annotations
from typing import Tuple, Optional, Any, List
import tcod

class JournalUI:
    """冒険日誌UI管理クラス (設計書 3.2)"""
    
    def __init__(self):
        self.is_open = False
        self.selected_index = 0
        self.window_width = 60
        self.window_height = 20
        self.header_color = (255, 215, 50)
        self.text_color = (230, 230, 230)
        self.highlight_color = (255, 255, 0)
        self.completed_color = (100, 255, 100)

    def toggle(self) -> None:
        """日誌の開閉を切り替える"""
        self.is_open = not self.is_open
        if self.is_open:
            self.selected_index = 0

    def handle_input(self, key: Any) -> bool:
        """日誌内での入力処理。Trueを返すとイベントを消費したことを示す"""
        if not self.is_open:
            return False

        # tcodのキー判定 (簡易的な実装)
        # 実際には engine.input_handler 等で処理される
        if key == "UP":
            self.selected_index = max(0, self.selected_index - 1)
            return True
        elif key == "DOWN":
            self.selected_index += 1
            return True
        elif key == "ESC" or key == "ENTER":
            self.is_open = False
            return True
        
        return False

    def render(self, console: tcod.console.Console, engine: Any) -> None:
        """日誌画面の描画 (設計書 3.2)"""
        if not self.is_open:
            return

        # 画面中央に配置
        screen_w = console.width_px / 8 # 概算
        screen_h = console.height_px / 8
        start_x = int((console.width - self.window_width) // 2)
        start_y = int((console.height - self.window_height) // 2)

        # ウィンドウ枠の描画
        for x in range(start_x, start_x + self.window_width):
            console.print(x, start_y, "═", fg=self.header_color)
            console.print(x, start_y + self.window_height - 1, "═", fg=self.header_color)
        for y in range(start_y, start_y + self.window_height):
            console.print(start_x, y, "║", fg=self.header_color)
            console.print(start_x + self.window_width - 1, y, "║", fg=self.header_color)

        # ヘッダー: ワールドフェーズの表示
        from world_state_system import WorldStateManager, REGISTRY
        ws_manager = WorldStateManager(REGISTRY)
        phase = ws_manager.get_phase().name
        
        # フェーズに応じた装飾
        phase_decor = {
            "PROLOGUE": "📜",
            "AWAKENING": "🌅",
            "ASCENSION": "✨",
            "DIVINITY": "👑"
        }.get(phase, "📖")
        
        header_text = f" {phase_decor} 冒険日誌: {phase} {phase_decor} "
        console.print(start_x + (self.window_width - len(header_text)) // 2, start_y, header_text, fg=self.header_color)

        # クエストデータの取得
        mqs = engine.main_quest_system
        active_quest = None
        if mqs.active_quest_id:
            active_quest = mqs.quests.get(mqs.active_quest_id)

        # メインコンテンツの描画
        current_y = start_y + 2
        
        if active_quest:
            console.print(start_x + 2, current_y, "【現在の目標】", fg=self.highlight_color)
            current_y += 1
            console.print(start_x + 2, current_y, active_quest.title, fg=self.text_color)
            current_y += 1
            console.print(start_x + 2, current_y, active_quest.description, fg=self.text_color)
            current_y += 2
            
            # 達成条件のチェックリスト
            console.print(start_x + 2, current_y, "達成条件:", fg=self.text_color)
            current_y += 1
            for obj in active_quest.objectives:
                mark = "✓" if obj.is_completed else "○"
                color = self.completed_color if obj.is_completed else self.text_color
                console.print(start_x + 4, current_y, f"{mark} {obj.description} ({obj.current_count}/{obj.required_count})", fg=color)
                current_y += 1
        else:
            console.print(start_x + 2, current_y, "現在アクティブなクエストはありません。", fg=self.text_color)
            current_y += 1

        # 完了済みクエストの表示
        current_y += 2
        console.print(start_x + 2, current_y, "【完了した記録】", fg=self.highlight_color)
        current_y += 1
        
        completed_quests = [q for q in mqs.quests.values() if q.status == 1] # QuestStatus.COMPLETED = 1 (approx)
        # 正確には Enum を使うべきだが、ここでは簡易的に
        from main_quest_system import QuestStatus
        completed_quests = [q for q in mqs.quests.values() if q.status == QuestStatus.COMPLETED]

        for i, q in enumerate(completed_quests):
            if current_y >= start_y + self.window_height - 2:
                break
            
            color = self.highlight_color if i == self.selected_index else self.text_color
            console.print(start_x + 4, current_y, f"✓ {q.title}", fg=color)
            current_y += 1

        console.print(start_x + 2, start_y + self.window_height - 2, " (ESCで閉じる)", fg=self.text_color)
