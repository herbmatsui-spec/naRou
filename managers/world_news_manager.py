"""WorldNewsManager: periodic world/title/job/guild updates per turn.

Extracted from Engine.advance_world (game.py).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game import Engine


class WorldNewsManager:
    """Drives periodic per-turn progression checks and notifications."""

    def advance(self, engine: "Engine") -> None:
        from constants import WORLD_NEWS_INTERVAL

        # 世界のニュース・噂の動的生成 (Step 8.1)
        if engine.turns % WORLD_NEWS_INTERVAL == 0 and hasattr(engine, "world_state_manager"):
            engine.world_state_manager.generate_world_news(engine)

        # === 称号システム: 定期チェック（10ターンごと） ===
        if engine.player and hasattr(engine.player, "total_turns"):
            engine.player.total_turns += 1
            from constants import TITLE_CHECK_INTERVAL

            if engine.player.total_turns % TITLE_CHECK_INTERVAL == 0:
                from title_system import MANAGER

                MANAGER.check_all_titles(engine.player)

        # === ジョブ経験値加算 & レベルアップ (Step 51) ===
        if engine.player:
            from constants import JOB_EXP_PER_TURN, JOB_LEVEL_UP_THRESHOLD

            engine.player.job_exp += JOB_EXP_PER_TURN
            if engine.player.job_exp >= JOB_LEVEL_UP_THRESHOLD:
                engine.player.job_exp -= 100
                engine.player.job_level += 1
                engine.log(
                    f"★職業【{engine.player.job}】の熟練度が上がり、Job Lv.{engine.player.job_level} に到達！",
                    (255, 220, 100),
                )

        # === スキルツリー定期チェック (Step 27) ===
        from constants import SKILL_POINTS_NOTIFICATION_THRESHOLD, SKILL_TREE_CHECK_INTERVAL

        if (
            engine.turns % SKILL_TREE_CHECK_INTERVAL == 0
            and engine.player.skill_points >= SKILL_POINTS_NOTIFICATION_THRESHOLD
        ):
            avail = engine.skill_tree_manager.get_available_skills(engine.player)
            if avail:
                engine.log(
                    "スキルポイントが利用可能です！ Sキーでスキルツリーを開いて習得できます。",
                    (255, 255, 0),
                )

        # === ギルドクエスト日次リセット (Step 41) ===
        from constants import GUILD_QUEST_RESET_INTERVAL

        if (
            engine.turns % GUILD_QUEST_RESET_INTERVAL == 0
            and engine.player
            and hasattr(engine.player, "guild_quest_progress")
        ):
            engine.log("【ギルド】日次ギルド依頼が更新・リセットされました。", (180, 220, 255))
