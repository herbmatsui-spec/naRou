"""
Elona Roguelike - Input Action System (Step 6.1)
コマンドパターンによる入力アクションの抽象化
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class InputAction(Protocol):
    """入力アクションのプロトコル"""

    def execute(self, engine: Any, event: Any) -> bool:
        """アクションを実行。消費された場合Trueを返す"""
        ...

    def can_execute(self, engine: Any) -> bool:
        """現在の状態で実行可能か判定"""
        ...


@dataclass
class KeyBinding:
    """キーバインド定義"""

    key: int  # tcod.event.KeySym
    action: InputAction
    modifiers: int = 0  # tcod.event.Modifier
    description: str = ""


class ActionRegistry:
    """アクションレジストリ：ステートごとのキーバインドを管理"""

    def __init__(self):
        self._bindings: dict[str, list[KeyBinding]] = {}
        self._global_bindings: list[KeyBinding] = []

    def register(self, state: str, binding: KeyBinding) -> None:
        """ステート固有のキーバインドを登録"""
        if state not in self._bindings:
            self._bindings[state] = []
        self._bindings[state].append(binding)

    def register_global(self, binding: KeyBinding) -> None:
        """全ステート共通のキーバインドを登録"""
        self._global_bindings.append(binding)

    def get_bindings(self, state: str) -> list[KeyBinding]:
        """指定ステートのキーバインドを取得（グローバル含む）"""
        return self._bindings.get(state, []) + self._global_bindings

    def clear_state(self, state: str) -> None:
        """ステートのバインディングをクリア"""
        if state in self._bindings:
            self._bindings[state].clear()


# ============================================================
# 具体的なアクションクラス (Step 6.2)
# ============================================================

import tcod.event

from constants import GameState
from save_system import SaveSystem
from sound_manager import SoundManager


class MovementAction:
    """移動アクション"""

    def __init__(self, dx: int, dy: int):
        self.dx = dx
        self.dy = dy

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        if engine.player_act(self.dx, self.dy):
            engine.advance_world()
        return True


class OpenContextMenuAction:
    """コンテキストメニューを開く"""

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        engine.open_context_menu()
        return True


class LookModeAction:
    """調査モードに入る"""

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        engine.game_state = "look"
        engine.look_cursor.x = engine.player.x
        engine.look_cursor.y = engine.player.y
        engine.log(
            "【調査モード】矢印キーで対象を選択 (Esc/Enter:閉じる)", (255, 255, 120)
        )
        return True


class PickupAction:
    """足元のアイテムを拾う"""

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        for itm in list(engine.items_on_ground):
            if itm.x == engine.player.x and itm.y == engine.player.y:
                ok, msg = engine.inventory.add_item(itm)
                engine.log(msg, (255, 255, 200))
                SoundManager.play_se("get_item")
                if ok:
                    engine.items_on_ground.remove(itm)
                break
        else:
            engine.log("足元には何もない。")
        return True


class HelpAction:
    """ヘルプ画面を開く"""

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        engine.game_state = "help"
        engine.help_tab = 0
        return True


class InventoryAction:
    """インベントリを開く（プレイヤー/ペット切り替え対応）"""

    def __init__(self, target: str = "player"):
        self.target = target

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        engine.game_state = "inventory"
        engine.inventory_target = self.target
        engine.inventory_cursor = 0
        return True


class StatusAction:
    """ステータス画面を開く"""

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        engine.game_state = "status"
        return True


class JournalAction:
    """ジャーナルを開く"""

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        engine.open_journal()
        return True


class SkillTreeAction:
    """スキルツリー画面を開く"""

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        engine.game_state = "skill_tree"
        return True


class JobAction:
    """ジョブ画面を開く（Shift+Jでジョブ、Jでジャーナル）"""

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        # Shift修飾子の判定は呼び出し元で行う
        if hasattr(event, "mod") and event.mod & tcod.event.Modifier.SHIFT:
            engine.game_state = "jobs"
        else:
            engine.open_journal()
        return True


class GuildAction:
    """ギルド画面を開く"""

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        engine.game_state = "guild"
        return True


class CastFireballAction:
    """ファイアボール詠唱"""

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        engine.cast_fireball()
        return True


class MineWallAction:
    """壁採掘"""

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        engine.mine_wall()
        return True


class PlayMusicAction:
    """音楽再生"""

    def can_execute(self, engine: Any) -> bool:
        return True  # どの状態でも可

    def execute(self, engine: Any, event: Any) -> bool:
        engine.play_music()
        return True


class PrayAction:
    """祈り"""

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        engine.pray()
        return True


class OfferAltarAction:
    """祭壇への捧げ物"""

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        engine.offer_altar()
        return True


class TalkAction:
    """会話"""

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        engine.talk_to_neighbor()
        return True


class HarvestAction:
    """採取"""

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        engine.harvest_resource()
        return True


class WishRodAction:
    """願いの杖使用"""

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        engine.use_wish_rod()
        return True


class DescendStairsAction:
    """階段を下りる"""

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        engine.descend_stairs()
        return True


class SaveAction:
    """セーブ"""

    def can_execute(self, engine: Any) -> bool:
        return True  # どの状態でも可

    def execute(self, engine: Any, event: Any) -> bool:
        msg = SaveSystem.save(engine)
        engine.log(msg, (100, 255, 150))
        return True


class LoadAction:
    """ロード"""

    def can_execute(self, engine: Any) -> bool:
        return True  # どの状態でも可

    def execute(self, engine: Any, event: Any) -> bool:
        loaded_engine, msg = SaveSystem.load()
        if loaded_engine is not None:
            engine.__dict__.update(loaded_engine.__dict__)
        engine.log(msg, (100, 200, 255))
        return True


class DebugAction:
    """デバッグコンソールを開く"""

    def can_execute(self, engine: Any) -> bool:
        return True

    def execute(self, engine: Any, event: Any) -> bool:
        engine.game_state = "debug"
        engine.debug_input = ""
        return True


class WaitAction:
    """待機 (1ターン経過) - スケジューラ再評価トリガー (Phase 3 Step 11)"""

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        engine.log("待機した。", (200, 200, 200))
        engine.advance_world()
        return True


class SleepAction:
    """睡眠 (HP/MP全快 + 長時間経過) - スケジューラ再評価トリガー (Phase 3 Step 11)"""

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        logs = engine.survival.sleep(engine.player)
        for l in logs:
            engine.log(l, (150, 150, 255))
        # 睡眠は複数ターン経過させる (例: 8時間 = 数百ターン相当)
        for _ in range(20):
            engine.advance_world()
        return True


class ActionScan:
    """《解析》アクション (Step 14, 20, 22)"""

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False

        current_world = getattr(
            getattr(engine, "game_state_data", None), "current_world", "main"
        )
        if current_world != "skill_eater" and not getattr(
            engine, "devour_debug_enabled", False
        ):
            engine.log(
                "《解析》はAの世界（スキル喰い）でのみ使用可能です。",
                (180, 180, 180),
            )
            return True

        if hasattr(engine, "execute_scan"):
            return engine.execute_scan()

        engine.log("【解析スキャン】周囲の生体構造をスキャン中...", (100, 255, 100))
        combat_sys = (
            engine.kernel.get_system("skill_eater_combat_system")
            if hasattr(engine, "kernel") and engine.kernel.has_system("skill_eater_combat_system")
            else None
        )
        if combat_sys:
            # Find nearest monster
            from core_framework import Point
            nearest = None
            min_dist = 999.0
            player_pos = Point(engine.player.x, engine.player.y)
            for entity in engine.entity_manager.get_living_entities():
                if entity != engine.player and not getattr(entity, "is_pet", False):
                    p = Point(entity.x, entity.y)
                    dist = ((p.x - player_pos.x) ** 2 + (p.y - player_pos.y) ** 2) ** 0.5
                    if dist < min_dist:
                        min_dist = dist
                        nearest = entity

            if nearest:
                from skill_eater_system import CharacterState
                analyzer = CharacterState(
                    id="player", name=engine.player.name, hp=engine.player.hp, max_hp=engine.player.max_hp,
                    mp=engine.player.mp, max_mp=engine.player.max_mp, atk=10, defense=5, intelligence=10, speed=100,
                    analysis_level=getattr(engine.player, "analysis_level", 1)
                )
                target_state = CharacterState(
                    id=str(getattr(nearest, "id", "enemy")), name=nearest.name, hp=nearest.hp, max_hp=nearest.max_hp,
                    mp=10, max_mp=10, atk=5, defense=2, intelligence=5, speed=80
                )
                res = combat_sys.analyze_target(analyzer, target_state)
                engine.log(f"【解析結果】対象: {res.target_name} (捕食成功率: {int(res.devour_success_rate * 100)}%)", (100, 255, 200))
                for sk in res.revealed_skills:
                    engine.log(f" - スキル: [{sk.tier}] {sk.name}", (255, 215, 0))
            else:
                engine.log("周囲に解析可能な対象が見つかりません。", (200, 200, 200))
        return True


class ActionDevour:
    """《喰らい》アクション (Step 13, 19, 22, 23)"""

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False

        current_world = getattr(
            getattr(engine, "game_state_data", None), "current_world", "main"
        )
        if current_world != "skill_eater" and not getattr(
            engine, "devour_debug_enabled", False
        ):
            engine.log(
                "《喰らい》はAの世界（スキル喰い）でのみ使用可能です。",
                (180, 180, 180),
            )
            return True

        if hasattr(engine, "execute_devour"):
            return engine.execute_devour()

        engine.log("【捕食コマンド】《喰らい》を発動！", (255, 100, 100))
        return True


class ActionSynthesisMenu:
    """スキル合成メニュー (Step 15, 21)"""

    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play" or (
            hasattr(engine, "current_state")
            and engine.current_state == GameState.EXPLORING
        )

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False

        current_world = getattr(
            getattr(engine, "game_state_data", None), "current_world", "main"
        )
        if current_world != "skill_eater" and not getattr(
            engine, "devour_debug_enabled", False
        ):
            engine.log(
                "《スキル合成》はAの世界（スキル喰い）でのみ使用可能です。",
                (180, 180, 180),
            )
            return True

        if hasattr(engine, "execute_synthesis"):
            return engine.execute_synthesis()

        engine.log("【キメラ合成炉】スキル合成メニューを展開します。", (200, 150, 255))
        return True


class QuitAction:
    """終了"""

    def can_execute(self, engine: Any) -> bool:
        return True

    def execute(self, engine: Any, event: Any) -> bool:
        print("Auto-saving before quit...")
        SaveSystem.save(engine)
        import sys

        sys.exit()
        return True

class WaitAction:
    """待機アクション (Step 20)"""
    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play"

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        if hasattr(engine, "player_act"):
            engine.player_act(0, 0)
        if hasattr(engine, "advance_world"):
            engine.advance_world()
        return True

class ActionDevour:
    """喰らい（Devour）アクション (Step 21)"""
    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play"

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        engine.log("【Devour】対象を喰らう準備をした！", (255, 100, 100))
        return True

class ActionScan:
    """解析（Scan）アクション (Step 22)"""
    def can_execute(self, engine: Any) -> bool:
        return engine.game_state == "play"

    def execute(self, engine: Any, event: Any) -> bool:
        if not self.can_execute(engine):
            return False
        engine.log("【Scan】対象の構造解析を開始！", (100, 255, 100))
        return True
