"""
UI System - Handles journal, context menu, tutorials, archaeology interpretation, and reincarnation extracted from Engine.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

from constants import COLOR_GOLD_YELLOW, ENERGY_THRESHOLD, TILE_FLOOR, TILE_WALL
from item_system import Item

if TYPE_CHECKING:
    from game import Engine


class UISystemHandler:
    """Handles journal/context menu, tutorials, mining, archaeology, and reincarnation."""

    def __init__(self, engine: "Engine"):
        self.engine = engine

    def open_journal(self) -> None:
        """冒険日誌を開く"""
        engine = self.engine
        engine.journal_ui.toggle()
        if engine.journal_ui.visible:
            engine.game_state = "journal"
        else:
            engine.game_state = "play"

    def open_context_menu(self) -> None:
        """Spaceキーによる文脈アクション候補の動的生成 (ContextMenuBuilder に委譲)"""
        engine = self.engine
        from managers.context_menu_builder import ContextMenuBuilder

        actions = ContextMenuBuilder().build_actions(engine)
        if actions:
            engine.context_menu.set_actions(actions)
            engine.game_state = "context"
        else:
            self.log("周囲にアクション可能な対象がない。")

    def log(
        self,
        text: str,
        color: tuple[int, int, int] = (230, 230, 230),
        level: str = "INFO",
    ) -> None:
        engine = self.engine
        engine.msg_log.add(text, color, level=level)

    def check_tutorial_triggers(self, trigger_condition: str) -> Any | None:
        """チュートリアルの発動条件を検知し、未完了なら通知・ポップアップ設定 (Step 1.2)"""
        engine = self.engine
        if not hasattr(engine, "tutorial_manager") or not engine.player:
            return None
        guide = engine.tutorial_manager.check_triggers(
            trigger_condition, engine.player.completed_tutorials
        )
        if guide:
            engine.player.completed_tutorials.add(guide.id)
            engine.player.pending_tutorial_popup = guide.to_dict()
            # ログにも案内表示
            self.log(
                f"📖【ガイド】{guide.title}: {guide.message}",
                (100, 255, 200),
                level="SUCCESS",
            )
            # 画面上部ポップアップ通知キューにも登録
            if hasattr(engine, "notification_manager"):
                engine.notification_manager.notify(
                    title=f"📖 ガイド: {guide.title}",
                    message=guide.message,
                    category="tutorial",
                    color=(100, 255, 200),
                    duration=40,
                )
            return guide
        return None

    def help_friend(self) -> None:
        """フレンド救援処理 (Step 57)"""
        engine = self.engine
        if not engine.player:
            return
        engine.player.friend_helps += 1
        engine.player.social_points += 10
        self.log(
            f"★フレンドを救援した！ (救援回数: {engine.player.friend_helps})",
            (100, 255, 200),
        )
        if hasattr(engine, "achievement_manager"):
            engine.achievement_manager.check_all_achievements(engine.player, engine)

    def mine_wall(self) -> None:
        engine = self.engine
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = engine.player.x + dx, engine.player.y + dy
            if engine.game_map.is_in_bounds(nx, ny) and engine.game_map.tiles[nx][ny] == TILE_WALL:
                engine.game_map.tiles[nx][ny] = TILE_FLOOR
                engine.player.gain_skill_exp("mining", 25)
                roll = random.random()
                if roll < 0.25:
                    ore = Item(
                        "鉄鉱石",
                        "ore",
                        "🪨",
                        (160, 160, 160),
                        nx,
                        ny,
                        base_weight=1.5,
                        base_value=50,
                    )
                    engine.entity_manager.add_item(ore)
                    self.log("壁を掘り崩した！ 鉄鉱石を発見！", (200, 200, 255))
                elif roll < 0.40:
                    g = random.randint(50, 200)
                    engine.survival.gold += g
                    self.log(f"壁から金貨が飛び散った！ (+{g}G)", COLOR_GOLD_YELLOW)
                else:
                    self.log("壁を掘り崩した。", (180, 180, 180))
                engine.player.energy -= ENERGY_THRESHOLD
                engine.advance_world()
                return
        self.log("近くに掘れる壁がない。")

    def excavate(self) -> None:
        """考古学メタゲーム: 現在の深度で遺跡を発掘する (Steps 25, 26)"""
        engine = self.engine
        mgr = getattr(engine, "archaeology_manager", None)
        if mgr is None:
            self.log("考古学システムが利用できない。")
            return
        depth = getattr(engine, "dungeon_level", 1)
        site_id = mgr.registry.pick_site_for_excavation(depth)
        if not site_id:
            self.log(f"地下{depth}階には発掘できる遺跡がない。", (180, 180, 180))
            return
        if site_id not in engine.player.archaeology.excavated_sites:
            engine.player.archaeology.excavated_sites.append(site_id)
        frag_id, key_id = mgr.resolve_excavation(site_id)
        if frag_id:
            mgr.collect_fragment(engine.player, frag_id, engine)
        if key_id:
            mgr.acquire_key(engine.player, key_id, engine)
        # 入手直後に解読を試みる（鍵があれば解読される）
        if frag_id:
            mgr.decode_fragment(engine.player, frag_id, engine)
        engine.player.energy -= ENERGY_THRESHOLD
        engine.advance_world()

    # ---- 改善②: 解釈選択プロンプト（ジャーナル内インタラクティブ） ----
    def _arch_interpret_groups(self) -> list[dict[str, Any]]:
        """到達真理ごとに候補エンディングをグループ化"""
        engine = self.engine
        mgr = getattr(engine, "archaeology_manager", None)
        if mgr is None:
            return []
        groups: dict[str, dict[str, Any]] = {}
        for tid, eid in mgr.suggest_endings(engine.player):
            g = groups.setdefault(tid, {"tid": tid, "name": "", "endings": []})
            g["endings"].append(eid)
        # 名称付与
        for tid, g in groups.items():
            t = mgr.registry.get_truth(tid)
            g["name"] = t.get("name", tid) if t else tid
        return list(groups.values())

    def open_interpret_prompt(self) -> None:
        """ジャーナル内で解釈プロンプトを開始（[e]）"""
        engine = self.engine
        groups = self._arch_interpret_groups()
        if not groups:
            self.log("まだ真理に到達していないので、解釈を記録できない。", (200, 160, 120))
            return
        engine.arch_interpret_active = True
        engine.arch_interpret_groups_cache = groups
        engine.arch_interpret_truth_idx = 0
        engine.arch_interpret_ending_idx = 0
        self.log(
            "💭 解釈プロンプト: ↑↓で真理、←→でエンディング、Enterで決定、Escで取消。",
            (220, 200, 255),
        )

    def interpret_move_truth(self, delta: int) -> None:
        engine = self.engine
        if not getattr(engine, "arch_interpret_active", False):
            return
        n = len(engine.arch_interpret_groups_cache)
        engine.arch_interpret_truth_idx = (engine.arch_interpret_truth_idx + delta) % max(n, 1)
        engine.arch_interpret_ending_idx = 0

    def interpret_move(self, delta: int) -> None:
        engine = self.engine
        if not getattr(engine, "arch_interpret_active", False):
            return
        g = engine.arch_interpret_groups_cache[engine.arch_interpret_truth_idx]
        n = len(g["endings"])
        engine.arch_interpret_ending_idx = (engine.arch_interpret_ending_idx + delta) % max(n, 1)

    def confirm_interpret(self) -> None:
        engine = self.engine
        if not getattr(engine, "arch_interpret_active", False):
            return
        g = engine.arch_interpret_groups_cache[engine.arch_interpret_truth_idx]
        eid = g["endings"][engine.arch_interpret_ending_idx]
        mgr = engine.archaeology_manager
        mgr.interpret_truth(engine.player, g["tid"], eid, engine=engine)
        engine.arch_interpret_active = False

    def cancel_interpret(self) -> None:
        engine = self.engine
        engine.arch_interpret_active = False

    def check_reincarnation_option(self) -> bool:
        """転生オプション表示・判定 (Steps 29, 30)"""
        # TODO: Reincarnation option
        engine = self.engine
        if hasattr(engine, "reincarnation_manager"):
            can_reinc = engine.reincarnation_manager.can_reincarnate(engine.player)
            if can_reinc:
                self.check_tutorial_triggers("reincarnate_ready")
            return can_reinc
        return False

    def reincarnate(self) -> None:
        """転生処理 (Steps 27, 28, 60, 61, 71)"""
        engine = self.engine
        if not engine.player:
            return
        if hasattr(engine, "reincarnation_manager"):
            engine.reincarnation_manager.reincarnate(engine.player, engine)
        else:
            engine.player.reincarnation_count += 1
            engine.player.total_level_earned += engine.player.level
            engine.player.level = 1
            engine.player.exp = 0
            self.log(
                f"★転生を実行した！ (転生回数: {engine.player.reincarnation_count}, 累計レベル: {engine.player.total_level_earned})",
                (255, 215, 0),
            )
        self.check_tutorial_triggers("reincarnate_ready")
