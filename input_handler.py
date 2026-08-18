"""
Input Handling System Module
Translates tcod keyboard and window events into discrete game actions.

Step 6 refactor: input is now routed through an ActionRegistry of InputAction
objects (command pattern). The registry is tried first; any key not bound to a
registered action falls back to the original handler (_handle_keydown_legacy).
"""

from __future__ import annotations
from typing import TYPE_CHECKING
import sys
import tcod
import tcod.event

from constants import ENERGY_THRESHOLD, COLOR_PET_PINK
from item_system import CAT_FOOD, CAT_POTION, CAT_WEAPON
from core_framework import Point
from sound_manager import SoundManager
from save_system import SaveSystem
from ui_fx_systems import HelpSystem
from render_system import RenderSystem
from input_actions import (
    ActionRegistry,
    KeyBinding,
    MovementAction,
    OpenContextMenuAction,
    LookModeAction,
    PickupAction,
    HelpAction,
    InventoryAction,
    StatusAction,
    JournalAction,
    SkillTreeAction,
    JobAction,
    GuildAction,
    CastFireballAction,
    MineWallAction,
    PlayMusicAction,
    PrayAction,
    OfferAltarAction,
    TalkAction,
    HarvestAction,
    WishRodAction,
    DescendStairsAction,
    SaveAction,
    LoadAction,
    DebugAction,
    WaitAction,
    SleepAction,
)

if TYPE_CHECKING:
    from game import Engine


class InputHandler:
    """入力制御およびイベントハンドラ"""

    # ActionRegistry インスタンスをクラス変数として保持
    _action_registry = ActionRegistry()
    _actions_registered = False

    # ------------------------------------------------------------------
    # エントリポイント
    # ------------------------------------------------------------------
    @classmethod
    def handle_event(cls, event: tcod.event.Event, engine: Engine) -> None:
        if isinstance(event, tcod.event.Quit):
            print("Auto-saving before quit...")
            SaveSystem.save(engine)
            sys.exit()
        elif isinstance(event, tcod.event.TextInput):
            if engine.game_state == "wish":
                engine.wish_input += event.text
            elif engine.game_state == "debug":
                engine.debug_input += event.text
        elif isinstance(event, tcod.event.KeyDown):
            cls._handle_keydown(event, engine)

    # ------------------------------------------------------------------
    # アクションレジストリ構築 (Step 6.4)
    # ------------------------------------------------------------------
    @classmethod
    def register_default_actions(cls) -> None:
        """プレイ状態の既定キーバインドを ActionRegistry に登録する。"""
        if cls._actions_registered:
            return
        reg = cls._action_registry
        KS = tcod.event.KeySym
        SHIFT = tcod.event.Modifier.SHIFT

        # 移動 (4方向 + viキー)
        move_map = {
            KS.UP: (0, -1),
            KS.K: (0, -1),
            KS.DOWN: (0, 1),
            KS.J: (0, 1),
            KS.LEFT: (-1, 0),
            KS.H: (-1, 0),
            KS.RIGHT: (1, 0),
        }
        for key, (dx, dy) in move_map.items():
            reg.register("play", KeyBinding(key, MovementAction(dx, dy), description="移動"))

        # 基本アクション
        reg.register("play", KeyBinding(KS.SPACE, OpenContextMenuAction(), description="コンテキストメニュー"))
        reg.register("play", KeyBinding(KS.L, LookModeAction(), description="調査モード"))
        reg.register("play", KeyBinding(KS.G, PickupAction(), description="拾う"))
        reg.register("play", KeyBinding(KS.QUESTION, HelpAction(), description="ヘルプ"))
        reg.register("play", KeyBinding(KS.H, HelpAction()))
        reg.register("play", KeyBinding(KS.F1, HelpAction()))
        reg.register("play", KeyBinding(KS.SLASH, HelpAction()))
        reg.register("play", KeyBinding(KS.I, InventoryAction("player"), description="インベントリ"))
        reg.register("play", KeyBinding(KS.P, InventoryAction("pet"), SHIFT, description="ペットインベントリ"))
        reg.register("play", KeyBinding(KS.C, StatusAction(), SHIFT, description="ステータス"))
        reg.register("play", KeyBinding(KS.J, JournalAction(), description="ジャーナル"))
        reg.register("play", KeyBinding(KS.J, JobAction(), SHIFT, description="ジョブ"))
        reg.register("play", KeyBinding(KS.S, SkillTreeAction(), SHIFT, description="スキルツリー"))
        reg.register("play", KeyBinding(KS.K, SkillTreeAction(), SHIFT, description="スキルツリー"))
        reg.register("play", KeyBinding(KS.G, GuildAction(), SHIFT, description="ギルド"))
        reg.register("play", KeyBinding(KS.C, CastFireballAction(), description="ファイアボール"))
        reg.register("play", KeyBinding(KS.B, MineWallAction(), description="壁採掘"))
        reg.register("play", KeyBinding(KS.M, PlayMusicAction(), description="音楽"))
        reg.register("play", KeyBinding(KS.P, PrayAction(), description="祈り"))
        reg.register("play", KeyBinding(KS.O, OfferAltarAction(), description="祭壇捧げ物"))
        reg.register("play", KeyBinding(KS.T, TalkAction(), description="会話"))
        reg.register("play", KeyBinding(KS.Z, HarvestAction(), description="採取"))
        reg.register("play", KeyBinding(KS.W, WishRodAction(), description="願いの杖"))
        reg.register("play", KeyBinding(KS.PERIOD, DescendStairsAction(), SHIFT, description="階段を下りる"))
        reg.register("play", KeyBinding(KS.PERIOD, WaitAction(), description="待機 (1ターン経過)"))
        reg.register("play", KeyBinding(KS.COMMA, SleepAction(), description="睡眠 (HP/MP全快 + 時間経過)"))
        reg.register("play", KeyBinding(KS.S, SaveAction(), description="セーブ"))
        reg.register("play", KeyBinding(KS.R, LoadAction(), description="ロード"))
        reg.register("play", KeyBinding(KS.GRAVE, DebugAction(), description="デバッグ"))

        cls._actions_registered = True

    # ------------------------------------------------------------------
    # キーマッチ判定
    # ------------------------------------------------------------------
    @classmethod
    def _is_key_match(cls, event: tcod.event.KeyDown, binding: KeyBinding) -> bool:
        if event.sym != binding.key:
            return False
        if binding.modifiers == 0:
            return event.mod == 0
        return (event.mod & binding.modifiers) == binding.modifiers

    # ------------------------------------------------------------------
    # レジストリ優先の入力処理 (Step 6.3)
    # ------------------------------------------------------------------
    @classmethod
    def _handle_keydown(cls, event: tcod.event.KeyDown, engine: Engine) -> None:
        """キー入力の処理 - ActionRegistry を優先し、未登録は従来処理へ。"""
        state_name = getattr(engine, "game_state", "play") or "play"

        for binding in cls._action_registry.get_bindings(state_name):
            if cls._is_key_match(event, binding) and binding.action.can_execute(engine):
                binding.action.execute(engine, event)
                return

        # レジストリに該当なし → 従来のハンドラへ委譲
        cls._handle_keydown_legacy(event, engine)

    # ------------------------------------------------------------------
    # 従来の実装 (後方互換・モーダル状態等のフォールバック)
    # ------------------------------------------------------------------
    @classmethod
    def _handle_keydown_legacy(cls, event: tcod.event.KeyDown, engine: Engine) -> None:
        from constants import GameState

        # 会話ウィンドウ (GameState.DIALOGUE)
        if engine.active_dialogue or (hasattr(engine, 'current_state') and engine.current_state == GameState.DIALOGUE):
            if event.sym in (tcod.event.KeySym.SPACE, tcod.event.KeySym.RETURN, tcod.event.KeySym.ESCAPE, tcod.event.KeySym.T):
                engine.active_dialogue = None
                if hasattr(engine, 'change_state'):
                    engine.change_state(GameState.EXPLORING)
            return

        # 一時停止状態 (GameState.PAUSED)
        if hasattr(engine, 'current_state') and engine.current_state == GameState.PAUSED:
            if event.sym in (tcod.event.KeySym.P, tcod.event.KeySym.ESCAPE):
                engine.change_state(GameState.EXPLORING)
                engine.log("ゲームを再開しました。", (100, 255, 100))
            return

        # ジャーナル状態 (改善②: 解釈選択プロンプト)
        if getattr(engine, "game_state", "play") == "journal":
            if getattr(engine, "arch_interpret_active", False):
                if event.sym in (tcod.event.KeySym.UP, tcod.event.KeySym.K):
                    engine.interpret_move_truth(-1)
                elif event.sym in (tcod.event.KeySym.DOWN, tcod.event.KeySym.J):
                    engine.interpret_move_truth(1)
                elif event.sym in (tcod.event.KeySym.LEFT, tcod.event.KeySym.H):
                    engine.interpret_move(-1)
                elif event.sym in (tcod.event.KeySym.RIGHT, tcod.event.KeySym.L):
                    engine.interpret_move(1)
                elif event.sym in (tcod.event.KeySym.RETURN, tcod.event.KeySym.SPACE):
                    engine.confirm_interpret()
                elif event.sym == tcod.event.KeySym.ESCAPE:
                    engine.cancel_interpret()
                return
            else:
                if event.sym == tcod.event.KeySym.E:
                    engine.open_interpret_prompt()
                    return
                if event.sym == tcod.event.KeySym.ESCAPE:
                    engine.open_journal()  # トグルで閉じる
                    return

        # 願い入力
        if engine.game_state == "wish":
            if event.sym == tcod.event.KeySym.RETURN:
                engine.confirm_wish()
            elif event.sym == tcod.event.KeySym.ESCAPE:
                engine.game_state = "play"
                engine.wish_input = ""
            elif event.sym == tcod.event.KeySym.BACKSPACE:
                engine.wish_input = engine.wish_input[:-1]
            return

        # デバッグコンソール
        if engine.game_state == "debug":
            if event.sym == tcod.event.KeySym.RETURN:
                result = engine.debug.process_command(engine.debug_input, engine)
                engine.log(f"[DEBUG] {result}", (0, 255, 100))
                engine.debug_input = ""
            elif event.sym == tcod.event.KeySym.ESCAPE:
                engine.game_state = "play"
                engine.debug_input = ""
            elif event.sym == tcod.event.KeySym.BACKSPACE:
                engine.debug_input = engine.debug_input[:-1]
            return

        # ステータス画面
        if engine.game_state == "status":
            if event.sym in (tcod.event.KeySym.C, tcod.event.KeySym.ESCAPE):
                engine.game_state = "play"
            return

        # スキルツリー画面
        if engine.game_state == "skill_tree":
            if event.sym in (tcod.event.KeySym.S, tcod.event.KeySym.ESCAPE):
                engine.game_state = "play"
            elif tcod.event.KeySym.N1 <= event.sym <= tcod.event.KeySym.N9:
                idx = event.sym - tcod.event.KeySym.N1
                avail = engine.skill_tree_manager.get_available_skills(engine.player)
                if idx < len(avail):
                    target = avail[idx]
                    ok = engine.skill_tree_manager.learn_skill(engine.player, target["tree_id"], target["tier_id"])
                    if ok:
                        engine.log(f"★スキル【{target['tier']}】を習得した！", (100, 255, 100))
                        SoundManager.play_se("level_up")
                    else:
                        engine.log("スキルポイントが足りないか、前提条件を満たしていません。", (255, 100, 100))
            return

        # ジョブ画面
        if engine.game_state == "jobs":
            if event.sym in (tcod.event.KeySym.J, tcod.event.KeySym.ESCAPE):
                engine.game_state = "play"
            elif tcod.event.KeySym.N1 <= event.sym <= tcod.event.KeySym.N9:
                idx = event.sym - tcod.event.KeySym.N1
                avail_jobs = engine.job_manager.get_available_jobs(engine.player)
                if idx < len(avail_jobs):
                    target_job = avail_jobs[idx]
                    ok = engine.job_manager.change_job(engine.player, target_job.id)
                    if ok:
                        engine.log(f"★職業を【{target_job.name}】に転職した！", (255, 215, 0))
                        SoundManager.play_se("level_up")
                    else:
                        engine.log("転職条件を満たしていません。", (255, 100, 100))
            return

        # ギルド画面
        if engine.game_state == "guild":
            if event.sym in (tcod.event.KeySym.G, tcod.event.KeySym.ESCAPE):
                engine.game_state = "play"
            elif tcod.event.KeySym.N1 <= event.sym <= tcod.event.KeySym.N3:
                idx = event.sym - tcod.event.KeySym.N1
                g_keys = list(engine.guild_registry.all().keys())
                if idx < len(g_keys):
                    target_gid = g_keys[idx]
                    ok = engine.guild_manager.join_guild(engine.player, target_gid)
                    if ok:
                        g_info = engine.guild_registry.get(target_gid)
                        engine.log(f"★【{g_info.name if g_info else target_gid}】に加入した！", (100, 255, 200))
                        SoundManager.play_se("level_up")
                    else:
                        engine.log("ギルドに加入できませんでした（既に所属済みなど）。", (255, 100, 100))
            return

        # 称号画面
        if engine.game_state == "titles":
            if event.sym in (tcod.event.KeySym.T, tcod.event.KeySym.ESCAPE, tcod.event.KeySym.RETURN):
                engine.game_state = "play"
            return

        # 実績一覧画面 (Step 72)
        if engine.game_state == "achievements":
            if event.sym in (tcod.event.KeySym.A, tcod.event.KeySym.ESCAPE, tcod.event.KeySym.RETURN):
                engine.game_state = "play"
            return

        # ヘルプガイド画面
        if engine.game_state == "help":
            if event.sym in (tcod.event.KeySym.ESCAPE, tcod.event.KeySym.H, tcod.event.KeySym.QUESTION, tcod.event.KeySym.SLASH):
                engine.game_state = "play"
            elif event.sym in (tcod.event.KeySym.RIGHT, tcod.event.KeySym.TAB):
                engine.help_tab = (engine.help_tab + 1) % len(HelpSystem.SECTIONS)
            elif event.sym == tcod.event.KeySym.LEFT:
                engine.help_tab = (engine.help_tab - 1) % len(HelpSystem.SECTIONS)
            elif event.sym == tcod.event.KeySym.N1:
                engine.help_tab = 0
            elif event.sym == tcod.event.KeySym.N2:
                engine.help_tab = 1
            elif event.sym == tcod.event.KeySym.N3:
                engine.help_tab = 2
            elif event.sym == tcod.event.KeySym.N4:
                engine.help_tab = 3
            return

        # インベントリ
        if engine.game_state == "inventory":
            filtered = RenderSystem.get_tabbed_items(engine)
            is_pet = engine.inventory_target == "pet"
            target_inv = engine.pet_inventory if is_pet else engine.inventory
            other_inv = engine.inventory if is_pet else engine.pet_inventory

            if event.sym in (tcod.event.KeySym.ESCAPE, tcod.event.KeySym.I, tcod.event.KeySym.P):
                engine.game_state = "play"
            elif event.sym == tcod.event.KeySym.LEFT:
                engine.inventory_tab = (engine.inventory_tab - 1) % 5
                engine.inventory_cursor = 0
            elif event.sym == tcod.event.KeySym.RIGHT:
                engine.inventory_tab = (engine.inventory_tab + 1) % 5
                engine.inventory_cursor = 0
            elif event.sym == tcod.event.KeySym.UP:
                engine.inventory_cursor = max(0, engine.inventory_cursor - 1)
            elif event.sym == tcod.event.KeySym.DOWN:
                engine.inventory_cursor = min(len(filtered) - 1, engine.inventory_cursor + 1)
            elif event.sym == tcod.event.KeySym.E:
                if 0 <= engine.inventory_cursor < len(filtered):
                    itm = filtered[engine.inventory_cursor]
                    if itm.category == CAT_FOOD:
                        logs = engine.survival.eat(engine.player, itm) if not is_pet else []
                        for l in logs: engine.log(l, (255, 200, 150))
                        if is_pet:
                            engine.log(f"シエルは{itm.name}をモグモグ食べた。", (255, 200, 150))
                        target_inv.remove_item(itm, count=1)
                    elif itm.category == CAT_POTION:
                        target_ent = engine.pet if is_pet else engine.player
                        target_ent.hp = min(target_ent.max_hp, target_ent.hp + itm.heal_amount)
                        engine.log(f"{target_ent.name}は{itm.name}を飲んだ！ HP+{itm.heal_amount}", (100, 255, 100))
                        target_inv.remove_item(itm, count=1)
                    engine.player.energy -= ENERGY_THRESHOLD
                    engine.advance_world()
                    engine.game_state = "play"
            elif event.sym == tcod.event.KeySym.D:
                if 0 <= engine.inventory_cursor < len(filtered):
                    itm = filtered[engine.inventory_cursor]
                    dropped = target_inv.remove_item(itm, count=1)
                    if dropped:
                        dropped.x, dropped.y = engine.player.x, engine.player.y
                        engine.items_on_ground.append(dropped)
                        engine.log(f"{dropped.name}を足元に置いた。")
            elif event.sym == tcod.event.KeySym.G:
                if 0 <= engine.inventory_cursor < len(filtered):
                    itm = filtered[engine.inventory_cursor]
                    if engine.pet.hp <= 0:
                        engine.log("シエルは倒れている…", (255, 100, 100))
                    else:
                        dist = Point(engine.player.x, engine.player.y).chebyshev_distance(Point(engine.pet.x, engine.pet.y))
                        if dist > 1:
                            engine.log("シエルが遠すぎて渡せない。", (255, 150, 150))
                        else:
                            removed = target_inv.remove_item(itm, count=1)
                            if removed:
                                ok, msg = other_inv.add_item(removed)
                                engine.log(f"{removed.name}を{'シエルに' if not is_pet else '自分に'}渡した。", (200, 255, 200))
                                if not is_pet and hasattr(engine.pet, 'pet_ai'):
                                    new_b = engine.pet.pet_ai.increase_bond(25, "gift")
                                    engine.log(f"シエル「ありがとう、お兄ちゃん！」 (絆度: {new_b})", COLOR_PET_PINK)
            elif event.sym == tcod.event.KeySym.X:
                if 0 <= engine.inventory_cursor < len(filtered):
                    itm = filtered[engine.inventory_cursor]
                    for sl in target_inv.slots:
                        if sl.item is itm:
                            ok, msg = target_inv.unequip(itm)
                            engine.log(msg, (200, 200, 255) if ok else (255, 80, 80))
                            break
                    else:
                        slot_name = "main_hand" if itm.category == CAT_WEAPON else "body"
                        ok, msg = target_inv.equip(itm, slot_name)
                        engine.log(msg, (200, 200, 255) if ok else (255, 80, 80))
            return

        # ルックモード
        if engine.game_state == "look":
            if event.sym in (tcod.event.KeySym.ESCAPE, tcod.event.KeySym.RETURN, tcod.event.KeySym.L):
                engine.game_state = "play"
            elif event.sym in (tcod.event.KeySym.UP, tcod.event.KeySym.K):
                engine.look_cursor.move(0, -1)
            elif event.sym in (tcod.event.KeySym.DOWN, tcod.event.KeySym.J):
                engine.look_cursor.move(0, 1)
            elif event.sym in (tcod.event.KeySym.LEFT, tcod.event.KeySym.H):
                engine.look_cursor.move(-1, 0)
            elif event.sym in (tcod.event.KeySym.RIGHT, tcod.event.KeySym.SEMICOLON):
                engine.look_cursor.move(1, 0)
            return

        # コンテキストメニュー
        if engine.game_state == "context":
            actions = engine.context_menu.actions
            if event.sym in (tcod.event.KeySym.ESCAPE, tcod.event.KeySym.SPACE):
                engine.game_state = "play"
            elif event.sym == tcod.event.KeySym.UP:
                engine.context_menu.selected_index = (engine.context_menu.selected_index - 1) % len(actions)
            elif event.sym == tcod.event.KeySym.DOWN:
                engine.context_menu.selected_index = (engine.context_menu.selected_index + 1) % len(actions)
            elif event.sym in (tcod.event.KeySym.RETURN, tcod.event.KeySym.KP_ENTER) or (tcod.event.KeySym.N1 <= event.sym <= tcod.event.KeySym.N9):
                selected_idx = engine.context_menu.selected_index
                if tcod.event.KeySym.N1 <= event.sym <= tcod.event.KeySym.N9:
                    num = event.sym - tcod.event.KeySym.N1
                    if num < len(actions): selected_idx = num

                if 0 <= selected_idx < len(actions):
                    act = actions[selected_idx]
                    engine.game_state = "play"
                    if act.handler_name == "pickup_item":
                        ok, msg = engine.inventory.add_item(act.payload)
                        engine.log(msg, (255, 255, 200))
                        SoundManager.play_se("get_item")
                        if ok: engine.items_on_ground.remove(act.payload)
                    elif act.handler_name == "eat_ground":
                        logs = engine.survival.eat(engine.player, act.payload)
                        for l in logs: engine.log(l, (255, 200, 150))
                        SoundManager.play_se("heal")
                        engine.items_on_ground.remove(act.payload)
                        engine.advance_world()
                    elif act.handler_name == "talk_target":
                        engine.talk_to_neighbor()
                    elif act.handler_name == "open_pet_inv":
                        engine.game_state = "inventory"
                        engine.inventory_target = "pet"
                        engine.inventory_cursor = 0
                    elif act.handler_name == "pray":
                        engine.pray()
                    elif act.handler_name == "offer_altar":
                        engine.offer_altar()
                    elif act.handler_name == "harvest_resource":
                        engine.harvest_resource()
                    elif act.handler_name == "mine_wall":
                        engine.mine_wall()
            return

        # 通常プレイ状態のキー入力
        dx, dy = 0, 0
        if event.sym in (tcod.event.KeySym.UP,    tcod.event.KeySym.K): dy = -1
        elif event.sym in (tcod.event.KeySym.DOWN,  tcod.event.KeySym.J): dy = 1
        elif event.sym in (tcod.event.KeySym.LEFT,  tcod.event.KeySym.H): dx = -1
        elif event.sym in (tcod.event.KeySym.RIGHT,): dx = 1
        elif event.sym == tcod.event.KeySym.SPACE:
            engine.open_context_menu()
        elif event.sym == tcod.event.KeySym.L:
            engine.game_state = "look"
            engine.look_cursor.x = engine.player.x
            engine.look_cursor.y = engine.player.y
            engine.log("【調査モード】矢印キーで対象を選択 (Esc/Enter:閉じる)", (255, 255, 120))
        elif event.sym == tcod.event.KeySym.G:
            for itm in list(engine.items_on_ground):
                if itm.x == engine.player.x and itm.y == engine.player.y:
                    ok, msg = engine.inventory.add_item(itm)
                    engine.log(msg, (255, 255, 200))
                    SoundManager.play_se("get_item")
                    if ok: engine.items_on_ground.remove(itm)
                    break
            else:
                engine.log("足元には何もない。")
        elif event.sym in (tcod.event.KeySym.QUESTION, tcod.event.KeySym.H, tcod.event.KeySym.F1, tcod.event.KeySym.SLASH):
            engine.game_state = "help"
            engine.help_tab = 0
        elif event.sym == tcod.event.KeySym.I:
            engine.game_state = "inventory"
            engine.inventory_target = "player"
            engine.inventory_cursor = 0
        elif event.sym == tcod.event.KeySym.P and (event.mod & tcod.event.Modifier.SHIFT):
            engine.game_state = "inventory"
            engine.inventory_target = "pet"
            engine.inventory_cursor = 0
        elif event.sym == tcod.event.KeySym.C and (event.mod & tcod.event.Modifier.SHIFT):
            engine.game_state = "status"
        elif event.sym == tcod.event.KeySym.T and (event.mod & tcod.event.Modifier.SHIFT):
            engine.game_state = "titles"
        elif event.sym == tcod.event.KeySym.A and (event.mod & tcod.event.Modifier.SHIFT):
            engine.game_state = "achievements"
        elif event.sym == tcod.event.KeySym.S and (event.mod & tcod.event.Modifier.SHIFT):
            engine.game_state = "skill_tree"
        elif event.sym == tcod.event.KeySym.J:
            if event.mod & tcod.event.Modifier.SHIFT:
                engine.game_state = "jobs"
            else:
                engine.open_journal()
        elif event.sym == tcod.event.KeySym.G and (event.mod & tcod.event.Modifier.SHIFT):
            engine.game_state = "guild"
        elif event.sym == tcod.event.KeySym.K and (event.mod & tcod.event.Modifier.SHIFT):
            engine.game_state = "skill_tree"
        elif event.sym == tcod.event.KeySym.C:
            engine.cast_fireball()
        elif event.sym == tcod.event.KeySym.B:
            engine.mine_wall()
        elif event.sym == tcod.event.KeySym.X:
            engine.excavate()
        elif event.sym == tcod.event.KeySym.M:
            engine.play_music()
        elif event.sym == tcod.event.KeySym.P:
            engine.pray()
        elif event.sym == tcod.event.KeySym.O:
            engine.offer_altar()
        elif event.sym == tcod.event.KeySym.T:
            engine.talk_to_neighbor()
        elif event.sym == tcod.event.KeySym.Z:
            engine.harvest_resource()
        elif event.sym == tcod.event.KeySym.W:
            engine.use_wish_rod()
        elif event.sym == tcod.event.KeySym.PERIOD and (event.mod & tcod.event.Modifier.SHIFT):
            engine.descend_stairs()
        elif event.sym == tcod.event.KeySym.S:
            msg = SaveSystem.save(engine)
            engine.log(msg, (100, 255, 150))
        elif event.sym == tcod.event.KeySym.R:
            loaded_engine, msg = SaveSystem.load()
            if loaded_engine is not None:
                engine.__dict__.update(loaded_engine.__dict__)
            engine.log(msg, (100, 200, 255))
        elif event.sym == tcod.event.KeySym.GRAVE:
            engine.game_state = "debug"
            engine.debug_input = ""
        elif event.sym == tcod.event.KeySym.ESCAPE:
            print("Auto-saving before quit...")
            SaveSystem.save(engine)
            sys.exit()

        if dx != 0 or dy != 0:
            if engine.player_act(dx, dy):
                engine.advance_world()
