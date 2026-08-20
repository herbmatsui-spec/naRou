"""
skill_eater_synthesis_system.py
Aの世界（スキル喰い） Phase 3: 《合成》システム＆ダイナミックスキルツリー
提案4: 合成錬金のEmote & Audio演出 (Steps 25〜32)
"""

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from skill_eater_system import (
    SkillEaterRegistry,
    SkillDef,
    SkillEffect,
    SkillTier,
    SkillType,
    CharacterState
)
from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_presentation_system import SkillEaterPresentationSystem, PresentationEvent


@dataclass
class StaticSynthesisRecipe:
    ingredient_ids: Tuple[str, str]
    result_skill_id: str
    description: str


@dataclass
class SynthesisResult:
    success: bool
    result_skill: Optional[SkillDef] = None
    consumed_skill_ids: List[str] = field(default_factory=list)
    is_procedural: bool = False
    message: str = ""
    played_sounds: List[str] = field(default_factory=list)
    presentation_events: List[PresentationEvent] = field(default_factory=list)  # Step 25: 演出リスト


@dataclass
class TreeNode:
    skill_id: str
    name: str
    tier: str
    parent_ids: List[str] = field(default_factory=list)
    is_synthesized: bool = False


class SkillEaterSynthesisSystem:
    def __init__(
        self,
        registry: Optional[SkillEaterRegistry] = None,
        audio: Optional[SkillEaterAudioSystem] = None,
        presentation: Optional[SkillEaterPresentationSystem] = None
    ):
        self.registry = registry or SkillEaterRegistry.get_instance()
        self.audio = audio or SkillEaterAudioSystem.get_instance()
        self.presentation = presentation or SkillEaterPresentationSystem.get_instance()
        self._static_recipes: Dict[Tuple[str, str], str] = {}
        self._init_default_recipes()

    def _init_default_recipes(self):
        """基本の静的レシピ登録"""
        self.register_static_recipe("com_magic_001", "com_labor_002", "rar_infrared_vision")
        self.register_static_recipe("rar_combat_012", "uni_midas_001", "rar_gold_body")

    def register_static_recipe(self, id_a: str, id_b: str, result_id: str):
        key1 = (id_a, id_b)
        key2 = (id_b, id_a)
        self._static_recipes[key1] = result_id
        self._static_recipes[key2] = result_id

    def synthesize(self, character: CharacterState, skill_id_a: str, skill_id_b: str) -> SynthesisResult:
        """
        2つのスキルを消費して新しいスキルを合成生成する
        Step 26〜31: 調合(dots2/metalPot2)、レシピ参照(idea/bookOpen)、完成(stars/metalPot3)、変異(exclamation/creak2)、失敗(cross/metalClick)
        """
        sounds = []
        events = []

        if not character.has_skill(skill_id_a) or not character.has_skill(skill_id_b):
            # Step 30: 素材不足エラー
            evt_err = self.presentation.add_event(
                emote_file="emote_cross.png",
                audio_file="metalClick.ogg",
                message="所持していないスキルは合成できません"
            )
            return SynthesisResult(
                success=False,
                message="所持していないスキルは合成できません。",
                played_sounds=["metalClick.ogg"],
                presentation_events=[evt_err]
            )

        if skill_id_a == skill_id_b:
            evt_same = self.presentation.add_event(
                emote_file="emote_cross.png",
                audio_file="metalClick.ogg",
                message="同じスキル同士は合成不可"
            )
            return SynthesisResult(
                success=False,
                message="同じスキル同士は合成できません。",
                played_sounds=["metalClick.ogg"],
                presentation_events=[evt_same]
            )

        skill_a = self.registry.get_skill(skill_id_a)
        skill_b = self.registry.get_skill(skill_id_b)

        if not skill_a or not skill_b:
            evt_inv = self.presentation.add_event(
                emote_file="emote_cross.png",
                audio_file="metalClick.ogg",
                message="無効なスキルデータ"
            )
            return SynthesisResult(
                success=False,
                message="無効なスキルデータです。",
                played_sounds=["metalClick.ogg"],
                presentation_events=[evt_inv]
            )

        # Step 26: 合成開始（魔導調合）
        evt_mix = self.presentation.add_event(
            emote_file="emote_dots2.png",
            audio_file="metalPot2.ogg",
            message=f"《{skill_a.name}》と《{skill_b.name}》を合成炉に投入..."
        )
        sounds.append("metalPot2.ogg")
        events.append(evt_mix)

        # 1. 静的レシピ解決
        recipe_key = (skill_id_a, skill_id_b)
        if recipe_key in self._static_recipes:
            # Step 27: 秘伝レシピのひらめき
            evt_rec = self.presentation.add_event(
                emote_file="emote_idea.png",
                audio_file="bookOpen.ogg",
                message="秘伝の合成式と共鳴！"
            )
            sounds.extend(["bookOpen.ogg", "bookFlip1.ogg"])
            events.append(evt_rec)

            res_id = self._static_recipes[recipe_key]
            result_skill = self.registry.get_skill(res_id)
            if not result_skill:
                result_skill = SkillDef(
                    id=res_id,
                    name=f"合成秘奥：{skill_a.name}×{skill_b.name}",
                    tier=SkillTier.RARE,
                    type=SkillType.ACTIVE,
                    flavor_text="静的レシピによって生み出された特異スキル。"
                )
                self.registry._skills[res_id] = result_skill

            character.remove_skill(skill_id_a)
            character.remove_skill(skill_id_b)
            character.add_skill(result_skill.id)

            # Step 28: 合成成功
            evt_suc = self.presentation.add_event(
                emote_file="emote_stars.png",
                audio_file="metalPot3.ogg",
                message=f"《{result_skill.name}》が完成！"
            )
            sounds.append("metalPot3.ogg")
            events.append(evt_suc)

            return SynthesisResult(
                success=True,
                result_skill=result_skill,
                consumed_skill_ids=[skill_id_a, skill_id_b],
                is_procedural=False,
                message=f"【秘伝合成成功！】《{skill_a.name}》と《{skill_b.name}》から《{result_skill.name}》が精製された！",
                played_sounds=sounds,
                presentation_events=events
            )

        # 2. 動的タグベース合成 (Procedural)
        # Step 29: 未知のキメラ変異
        evt_mut = self.presentation.add_event(
            emote_file="emote_exclamation.png",
            audio_file="creak2.ogg",
            message="未知の魔力反応！ キメラ変異が発生！"
        )
        sounds.append("creak2.ogg")
        events.append(evt_mut)

        combined_tags = list(set(skill_a.tags + skill_b.tags))
        new_id = f"proc_syn_{uuid.uuid4().hex[:8]}"
        new_name = f"変異融合：《{skill_a.name}・{skill_b.name}》"
        
        tier_hierarchy = [SkillTier.COMMON, SkillTier.RARE, SkillTier.UNIQUE, SkillTier.CONCEPT]
        tier_idx = max(tier_hierarchy.index(skill_a.tier), tier_hierarchy.index(skill_b.tier))
        new_tier = tier_hierarchy[tier_idx]

        combined_effects = skill_a.effects + skill_b.effects

        procedural_skill = SkillDef(
            id=new_id,
            name=new_name,
            tier=new_tier,
            type=SkillType.ACTIVE if (skill_a.type == SkillType.ACTIVE or skill_b.type == SkillType.ACTIVE) else SkillType.PASSIVE,
            mp_cost=skill_a.mp_cost + skill_b.mp_cost,
            cooldown=max(skill_a.cooldown, skill_b.cooldown),
            market_value=skill_a.market_value + skill_b.market_value,
            tags=combined_tags,
            flavor_text=f"《{skill_a.name}》の性質と《{skill_b.name}》の構造を融合させたキメラ能力。",
            effects=combined_effects,
            is_illegal=True
        )

        self.registry._skills[new_id] = procedural_skill
        character.remove_skill(skill_id_a)
        character.remove_skill(skill_id_b)
        character.add_skill(new_id)

        # Step 28: 合成成功
        evt_suc2 = self.presentation.add_event(
            emote_file="emote_stars.png",
            audio_file="metalPot3.ogg",
            message=f"《{new_name}》が誕生！"
        )
        sounds.append("metalPot3.ogg")
        events.append(evt_suc2)

        # Step 31: 違法スキルの警告エモート
        if procedural_skill.is_illegal:
            evt_ill = self.presentation.add_event(
                emote_file="emote_anger.png",
                message="認可外の違法合成スキルが登録されました（公認市場取引不可）"
            )
            events.append(evt_ill)

        return SynthesisResult(
            success=True,
            result_skill=procedural_skill,
            consumed_skill_ids=[skill_id_a, skill_id_b],
            is_procedural=True,
            message=f"【プロシージャル合成成功！】《{new_name}》が誕生した！（タグ: {', '.join(combined_tags)}）",
            played_sounds=sounds,
            presentation_events=events
        )

    def generate_dynamic_tree(self, character: CharacterState) -> List[TreeNode]:
        nodes: List[TreeNode] = []
        nodes.append(TreeNode(
            skill_id="root_analysis",
            name="《解析（基盤）》",
            tier="Eater",
            parent_ids=[]
        ))

        for s_id in character.get_skill_ids():
            s_def = self.registry.get_skill(s_id)
            if not s_def:
                continue
            
            is_syn = s_id.startswith("proc_syn_") or s_id.startswith("rar_gold_")
            nodes.append(TreeNode(
                skill_id=s_def.id,
                name=s_def.name,
                tier=s_def.tier.value,
                parent_ids=["root_analysis"],
                is_synthesized=is_syn
            ))

        return nodes
