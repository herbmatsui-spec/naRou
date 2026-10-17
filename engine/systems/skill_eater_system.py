"""
Skill Eater System - Handles scan/devour/synthesis/world transition extracted from Engine.
"""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

from constants import ENERGY_THRESHOLD

if TYPE_CHECKING:
    from ecs.entity import Entity
    from game import Engine

logger = logging.getLogger(__name__)


def _declared_skill_ids(entity: Entity) -> list[str]:
    """Entity が宣言しているスキル id を、並び順どおりに返す。

    `Entity.skills` は未設定の個体に対してプレイヤーの既定 17 種を生成し、触れた時点で
    `_skills` にまで書き込む property なので、判定には生値を使う。
    data_manager.create_monster は id 文字列のリスト、プレイヤーは Skill 辞書を保持する。
    """
    declared = getattr(entity, "_skills", None)
    if declared is None:
        return []
    if isinstance(declared, dict):
        return [str(key) for key in declared]
    return [str(s) for s in declared]


def _character_state_from_entity(entity: Entity, analysis_level: int = 1):
    """Entity が保持する実データから、喰らい判定用の `CharacterState` を構成する。"""
    from skill_eater_system import CharacterState

    attributes = entity.attributes
    return CharacterState(
        id=str(getattr(entity, "id", entity.name)),
        name=entity.name,
        hp=entity.hp,
        max_hp=entity.max_hp,
        mp=entity.mp,
        max_mp=entity.max_mp,
        atk=attributes.strength,
        defense=attributes.endurance,
        intelligence=attributes.perception,
        speed=entity.speed,
        analysis_level=analysis_level,
        # 奪取率は target.status_effects も読む（Paralyzed / Sleep で +0.20）。
        # Entity には宣言フィールドがないため動的属性として付き、実データだけを写す。
        status_effects=list(getattr(entity, "status_effects", None) or []),
    )


class SkillEaterSystemHandler:
    """Handles Skill Eater actions: scan, devour, synthesis, dispatch, world switch."""

    def __init__(self, engine: "Engine"):
        self.engine = engine

    def execute_scan(self) -> bool:
        """周囲の対象をスキャン・解析する (Step 14, 20, 38, 39)"""
        engine = self.engine
        combat_sys = engine.skill_eater_combat_system
        if not combat_sys:
            engine.log("解析システムが見つかりません。", (255, 100, 100))
            return False

        nearest = None
        min_dist = 999.0
        for entity in engine.entity_manager.get_living_entities():
            if entity != engine.player and not getattr(entity, "is_pet", False):
                dist = ((entity.x - engine.player.x) ** 2 + (entity.y - engine.player.y) ** 2) ** 0.5
                if dist < min_dist:
                    min_dist = dist
                    nearest = entity

        if not nearest:
            engine.log("周囲に解析可能な対象が見つかりません。", (200, 200, 200))
            return True

        from skill_eater_system import CharacterState

        analyzer = CharacterState(
            id="player",
            name=engine.player.name,
            hp=engine.player.hp,
            max_hp=engine.player.max_hp,
            mp=engine.player.mp,
            max_mp=engine.player.max_mp,
            atk=15,
            defense=10,
            intelligence=15,
            speed=100,
            analysis_level=getattr(engine.player, "analysis_level", 1),
        )
        target_state = CharacterState(
            id=str(getattr(nearest, "id", "enemy")),
            name=nearest.name,
            hp=nearest.hp,
            max_hp=nearest.max_hp,
            mp=10,
            max_mp=10,
            atk=getattr(nearest, "atk", 10),
            defense=getattr(nearest, "defense", 5),
            intelligence=5,
            speed=getattr(nearest, "speed", 80),
        )
        res = combat_sys.analyze_target(analyzer, target_state)
        engine.last_scan_result = res
        engine.log(
            f"【深度解析】{res.target_name} (HP: {int(res.target_hp_ratio * 100)}% / 喰らい成功率: {int(res.devour_success_rate * 100)}%)",
            (100, 255, 200),
        )
        for sk in res.revealed_skills:
            engine.log(f" - [{sk.tier}] {sk.name} (タグ: {', '.join(sk.tags)})", (255, 215, 0))
        return True

    def execute_devour(self) -> bool:
        """隣接する敵からスキルを強奪する《喰らい》 (Steps 25-36)"""
        engine = self.engine
        combat_sys = engine.skill_eater_combat_system
        if not combat_sys:
            engine.log("喰らいシステムが見つかりません。", (255, 100, 100))
            return False

        target = None
        for entity in engine.entity_manager.get_living_entities():
            if entity != engine.player and not getattr(entity, "is_pet", False):
                dist = ((entity.x - engine.player.x) ** 2 + (entity.y - engine.player.y) ** 2) ** 0.5
                if dist <= 1.5:
                    target = entity
                    break

        if not target:
            engine.log(
                "隣接する捕食対象がいません。（敵に隣接して発動してください）", (200, 200, 200)
            )
            return True

        from skill_eater_system import SkillEaterRegistry

        analyzer = _character_state_from_entity(
            engine.player,
            analysis_level=getattr(engine.player, "analysis_level", 1),
        )
        target_state = _character_state_from_entity(target)
        declared_ids = _declared_skill_ids(target)
        for skill_id in declared_ids:
            # 敵が宣言するスキルはすべて奪取候補として積む（実際に奪われるのは先頭の1つ）。
            # メモリ容量で落とすのは敵の貧弱さではない
            target_state.add_skill(skill_id, ignore_capacity=True)

        rate = combat_sys.calculate_devour_rate(analyzer, target_state)
        roll = random.random()
        # 複数保有時は宣言順の先頭。抽選は行わない
        stolen_id = next(iter(target_state.skills), None)

        if stolen_id is None:
            engine.log(f"{target.name} の身体には、喰うべきスキルが棲んでいない。", (200, 200, 200))
        elif roll <= rate:
            target_state.remove_skill(stolen_id)
            reg = SkillEaterRegistry.get_instance()
            sk_def = reg.get_skill(stolen_id)
            sk_name = sk_def.name if sk_def else stolen_id

            if "skills" not in engine.game_state_data.world_a_data:
                engine.game_state_data.world_a_data["skills"] = []
            engine.game_state_data.world_a_data["skills"].append(stolen_id)

            self._register_devoured_skill(stolen_id, sk_def)

            engine.log(
                f"【捕食成功！】{target.name} から 《{sk_name}》 を喰らい尽くした！",
                (255, 100, 255),
            )
            if hasattr(engine, "sound_manager") and engine.sound_manager:
                engine.sound_manager.play_se("eat")

            target.hp = max(1, target.hp - 15)
            if target_state.is_husk or len(target_state.skills) == 0:
                target.is_husk = True
                engine.log(
                    f"{target.name} はスキルを奪われ、抜け殻（Husk）と化した！", (180, 180, 180)
                )
        else:
            backlash = random.randint(3, 8)
            engine.player.hp -= backlash
            engine.log(
                f"【捕食失敗】拒絶反応！ 胃袋から激痛が走る！（-{backlash} HP）", (255, 80, 80)
            )
            if hasattr(engine, "screen_shake") and engine.screen_shake:
                engine.screen_shake.trigger(intensity=1.5, duration=4)

        engine.player.energy -= ENERGY_THRESHOLD
        engine.advance_world()
        return True

    def _register_devoured_skill(self, skill_id: str, sk_def) -> None:
        """奪ったスキルを唱えられるスキル (`player.skills`) へ登録する。

        `world_a_data["skills"]` は HUD と fusion 炉の記録であり、別枠の配列なので残す。
        定義が引けなかった場合は、黙って捨てずに理由をログと画面に残す。
        """
        from ecs.entity import Skill

        engine = self.engine
        skills = engine.player.skills
        if skill_id in skills:
            return

        if sk_def is None:
            logger.warning("Devoured skill %r could not be registered: no definition found", skill_id)
            engine.log(f"【記録のみ】《{skill_id}》の定義が見つからないため、唱えられるスキルには登録できない", (255, 160, 80))
            return

        skills[skill_id] = Skill(sk_def.name, level=1)

    def execute_synthesis(self, skill_a: str | None = None, skill_b: str | None = None) -> bool:
        """スキル合成を実行する (Steps 43-47)"""
        engine = self.engine
        synth_sys = engine.skill_eater_synthesis_system
        if not synth_sys:
            engine.log("合成システムが見つかりません。", (255, 100, 100))
            return False

        if "skills" not in engine.game_state_data.world_a_data:
            engine.game_state_data.world_a_data["skills"] = []

        skills = engine.game_state_data.world_a_data["skills"]
        if len(skills) < 2:
            engine.log(
                f"【キメラ合成炉】合成には少なくとも2つのスキルが必要です。（現在所持: {len(skills)}個）",
                (200, 200, 200),
            )
            return True

        id_a = skill_a or skills[0]
        id_b = skill_b or skills[1]

        from skill_eater_system import CharacterState

        char_state = CharacterState(
            id="player",
            name=engine.player.name,
            hp=engine.player.hp,
            max_hp=engine.player.max_hp,
            mp=engine.player.mp,
            max_mp=engine.player.max_mp,
            atk=15,
            defense=10,
            intelligence=15,
            speed=100,
        )
        for s in skills:
            char_state.add_skill(s)

        res = synth_sys.synthesize(char_state, id_a, id_b)
        if res.success and res.result_skill:
            if id_a in skills:
                skills.remove(id_a)
            if id_b in skills:
                skills.remove(id_b)
            skills.append(res.result_skill.id)
            engine.log(
                f"【合成成功！】《{res.result_skill.name}》[{res.result_skill.tier.value}] が誕生した！",
                (255, 215, 0),
            )
            if hasattr(engine, "sound_manager") and engine.sound_manager:
                engine.sound_manager.play_se("cast")
        else:
            engine.log("【合成失敗】魔力が反発し、合成に失敗した...", (255, 100, 100))
        return True

    def execute_pet_dispatch(
        self, mission_name: str, duration_turns: int = 10, reward_gold: int = 500
    ) -> bool:
        """ペットをスラム街の探索・調達任務に派遣する (Step 54-56)"""
        engine = self.engine
        if "pet_dispatches" not in engine.game_state_data.world_a_data:
            engine.game_state_data.world_a_data["pet_dispatches"] = []

        engine.game_state_data.world_a_data["pet_dispatches"].append(
            {
                "mission_name": mission_name,
                "remaining_turns": duration_turns,
                "reward_gold": reward_gold,
            }
        )
        engine.log(
            f"【ペット派遣】『{mission_name}』へ派遣を開始しました（所要: {duration_turns}ターン）。",
            (100, 255, 200),
        )
        return True

    def execute_base_upgrade(self, facility_id: str, cost_aldo: int = 1000) -> bool:
        """スラム街の拠点を拡張・改修する (Step 54)"""
        engine = self.engine
        if "facilities" not in engine.game_state_data.world_a_data:
            engine.game_state_data.world_a_data["facilities"] = {}

        facs = engine.game_state_data.world_a_data["facilities"]
        current_lv = facs.get(facility_id, 1)
        facs[facility_id] = current_lv + 1
        engine.log(
            f"【拠点改修完了】施設『{facility_id}』が Lv.{facs[facility_id]} にアップグレードされました！",
            (255, 215, 0),
        )
        return True

    def execute_solve_puzzle(self, puzzle_type: str, used_skill_tag: str) -> bool:
        """環境パズルを所持スキルで解除する (Step 57-59)"""
        engine = self.engine
        match = (
            (puzzle_type == "ice_barrier" and "Fire" in used_skill_tag)
            or (puzzle_type == "dark_gate" and "Light" in used_skill_tag)
            or (puzzle_type == "iron_lock" and "Labor" in used_skill_tag)
        )
        if match:
            engine.log(
                f"【ギミック解除！】スキル特性[{used_skill_tag}]により『{puzzle_type}』の封鎖を突破した！",
                (100, 255, 100),
            )
            return True
        else:
            engine.log(
                f"【解除失敗】『{puzzle_type}』に対して[{used_skill_tag}]は効果が薄いようだ...",
                (255, 100, 100),
            )
            return False

    def switch_world(self, world_id: str) -> bool:
        """ワールド間遷移（Aの世界 / 本編ワールドの切り替え） (Step 61-62)"""
        engine = self.engine
        engine.game_state_data.current_world = world_id
        if world_id == "skill_eater":
            engine.log(
                "【次元遷移】Aの世界（スキル喰い）へ転移しました！ 《解析(X)》と《喰らい(V)》が解放されます。",
                (150, 255, 150),
            )
            if hasattr(engine, "sound_manager") and engine.sound_manager:
                engine.sound_manager.play_se("warp")
        else:
            engine.log(f"【次元遷移】ワールド『{world_id}』へ帰還しました。", (180, 200, 255))
        return True

    def execute_epilogue_world_transition(self) -> bool:
        """Aの世界エピローグ＆次元ゲート開放 (Step 69-70)"""
        engine = self.engine
        engine.log(
            "【次元ゲート開放】Aの世界の境界線が溶解し、概念の残滓がプレイヤーに宿る！",
            (255, 215, 0),
        )
        if "meta_artifacts" not in engine.game_state_data.world_a_data:
            engine.game_state_data.world_a_data["meta_artifacts"] = []
        engine.game_state_data.world_a_data["meta_artifacts"].append("concept_eater_mark")
        return self.switch_world("main")
