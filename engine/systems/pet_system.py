"""
Pet System - Handles pet facilities, music, prayer, altar, and wish items extracted from Engine.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from advanced_systems import WishParser
from constants import COLOR_GOLD_YELLOW, ENERGY_THRESHOLD
from run_summary import CAUSE_SELF
from sound_manager import SoundManager

if TYPE_CHECKING:
    from game import Engine


class PetSystemHandler:
    """Handles pet evolution/fusion facilities, music, prayer, altar, and wishes."""

    def __init__(self, engine: "Engine"):
        self.engine = engine

    def use_pet_evolution_stone(self) -> None:
        """特別アイテムによるペット進化トリガー (Step 46)"""
        engine = self.engine
        if not engine.pet or engine.pet.hp <= 0:
            engine.log("進化させられるペットがいません。")
            return
        p_type = getattr(engine.pet, "pet_type", "puppy")
        evos = engine.pet_evolution_manager.get_available_evolutions(
            p_type, engine.pet.pet_ai, engine.pet
        )
        if evos:
            target_evo = evos[0]
            ok = engine.pet_evolution_manager.apply_evolution(engine.pet.pet_ai, target_evo, engine.pet)
            if ok:
                engine.log(
                    f"★進化の秘石が輝き、【{engine.pet.name}】へと劇的進化した！",
                    (255, 215, 0),
                )
                SoundManager.play_se("level_up")
        else:
            engine.log("ペットの絆度またはレベルが進化条件に達していません。")

    def use_alchemy_lab(self) -> None:
        """アルケミーラボでのペット融合施設利用トリガー (Steps 67, 68)"""
        engine = self.engine
        # プレイヤーのペットと従えているペット群
        pets = [engine.pet] + getattr(engine.player, "pets", [])
        if len(pets) < 2:
            engine.log("融合には2体以上のペットが必要です。")
            return

        res_id = engine.pet_fusion_manager.can_fuse(pets[:2], engine.player)
        if not res_id:
            engine.log("融合条件（種族・絆度・レベル等）を満たしていません。")
            return

        p1_name, p2_name = pets[0].name, pets[1].name
        fused = engine.pet_fusion_manager.execute_fusion(pets[:2], engine.player, res_id)
        if fused:
            engine.pet = fused
            from ui_fx_systems import play_pet_fusion_fx

            play_pet_fusion_fx(engine, p1_name, p2_name, fused.name)

    def play_music(self) -> None:
        """演奏 - 視界内のNPCのみおひねり (ステップ52)"""
        engine = self.engine
        perf_lv = engine.player.skills.get("performance")
        lv = perf_lv.level if perf_lv else 1
        lv += engine.player.attributes.charisma // 3
        engine.player.gain_skill_exp("performance", 35)
        total_tips = 0
        for e in engine.entity_manager.get_living_entities():
            if e not in (engine.player, engine.pet) and e.hp > 0:
                success_rate = min(95, max(10, lv * 8 + engine.player.attributes.charisma))
                if random.randint(1, 100) <= success_rate:
                    tip = random.randint(5, 10 + lv * 3)
                    total_tips += tip
                    engine.log(f"{e.name}が拍手を送った！ (+{tip}G)", (255, 220, 100))
                else:
                    engine.log(
                        f"{e.name}は不満げに石を投げた！(演奏失敗 -1 HP)",
                        (200, 100, 100),
                    )
                    engine.player.hp -= 1
                    engine._record_harm_cause(CAUSE_SELF)
        if total_tips > 0:
            engine.survival.gold += total_tips
            engine.log(f"★演奏の報酬合計: {total_tips}G！", COLOR_GOLD_YELLOW)
        engine.player.energy -= ENERGY_THRESHOLD
        engine.advance_world()

    def pray(self) -> None:
        engine = self.engine
        success, msg = engine.player.pray_to_god()
        engine.log(msg, (255, 215, 0) if success else (200, 200, 200))
        if success:
            engine.player.energy -= ENERGY_THRESHOLD
            engine.advance_world()

    def offer_altar(self) -> None:
        engine = self.engine
        if (engine.player.x, engine.player.y) != engine.altar_pos:
            engine.log("祭壇の上に立っていない。")
            return
        for itm in list(engine.inventory.items):
            if any(kw in itm.name for kw in ["肉", "鉱石", "パン", "ハーブ"]):
                engine.inventory.remove_item(itm, count=1)
                engine.player.piety += 30
                engine.log(f"{itm.name} を捧げた！ 信仰度: {engine.player.piety}", (255, 215, 0))
                engine.player.energy -= ENERGY_THRESHOLD
                engine.advance_world()
                return
        engine.log("捧げる供物がない（肉・鉱石・パン・ハーブなど）。")

    def use_wish_rod(self) -> None:
        engine = self.engine
        for itm in engine.inventory.items:
            if "願いの杖" in itm.name:
                engine.game_state = "wish"
                engine.wish_input = ""
                engine.log(
                    "★願いの杖を振った！ 何を望む？（テキストを入力してEnter）",
                    (100, 255, 255),
                )
                return
        engine.log("願いの杖を持っていない。")

    def confirm_wish(self) -> None:
        engine = self.engine
        result = WishParser.parse(engine.wish_input, engine.player, engine.inventory, engine.survival)
        engine.log(f"★願い「{engine.wish_input}」: {result}", (100, 255, 255))
        engine.game_state = "play"
        engine.wish_input = ""
