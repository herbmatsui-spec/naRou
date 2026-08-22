"""
Meta Progression & Memory System
Provides:
1. Procedural / Dynamic Memory Fragment generation based on player actions and life history
2. Randomized Cycle Modifiers & Legacy causal flags for reincarnation
3. Multi-generation Meta Goals evaluation and permanent bonus aggregation
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
import os
import random
from dataclasses import dataclass, field
from typing import Any

import yaml

from archaeology_system import ArchaeologyRegistry
from components import (
    AchievementComponent,
    ArchaeologyComponent,
    ReincarnationComponent,
    StorytellerComponent,
    TitleComponent,
)


@dataclass
class MemoryFragmentData:
    fragment_id: str
    name: str
    description: str
    generation: int
    category: str  # "combat", "magic", "survival", "exploration", "social"
    buff_traits: dict[str, float] = field(default_factory=dict)
    lore_snippet: str = ""
    unlocked_secrets: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fragment_id": self.fragment_id,
            "name": self.name,
            "description": self.description,
            "generation": self.generation,
            "category": self.category,
            "buff_traits": self.buff_traits.copy(),
            "lore_snippet": self.lore_snippet,
            "unlocked_secrets": list(self.unlocked_secrets),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MemoryFragmentData:
        return cls(
            fragment_id=d.get("fragment_id", "frag_unknown"),
            name=d.get("name", "名もなき記憶"),
            description=d.get("description", ""),
            generation=d.get("generation", 1),
            category=d.get("category", "combat"),
            buff_traits=d.get("buff_traits", {}),
            lore_snippet=d.get("lore_snippet", ""),
            unlocked_secrets=d.get("unlocked_secrets", []),
        )


@dataclass
class CycleModifierData:
    id: str
    name: str
    description: str
    target_goal: str
    reward_meta_points: int = 50
    positive_effects: dict[str, float] = field(default_factory=dict)
    negative_effects: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "target_goal": self.target_goal,
            "reward_meta_points": self.reward_meta_points,
            "positive_effects": self.positive_effects.copy(),
            "negative_effects": self.negative_effects.copy(),
        }


@dataclass
class MetaGoalData:
    id: str
    name: str
    description: str
    target_metric: str
    target_value: int
    permanent_bonus: dict[str, Any] = field(default_factory=dict)


class MetaProgressionRegistry:
    """メタゴールおよび周回設定のレジストリ"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.meta_goals: dict[str, MetaGoalData] = {}
            cls._instance.cycle_modifiers: list[CycleModifierData] = []
            cls._instance.fragment_templates: dict[str, Any] = {}
            cls._instance._awarded_truth_piece_categories: set[str] = set()
        return cls._instance

    def load(self, path: str = "data/meta_goals.yaml") -> None:
        self.meta_goals.clear()
        self.cycle_modifiers.clear()
        self.fragment_templates.clear()

        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    raw = yaml.safe_load(f) or {}

                for gid, gdata in raw.get("meta_goals", {}).items():
                    self.meta_goals[gid] = MetaGoalData(
                        id=gdata.get("id", gid),
                        name=gdata.get("name", gid),
                        description=gdata.get("description", ""),
                        target_metric=gdata.get("target_metric", ""),
                        target_value=gdata.get("target_value", 1),
                        permanent_bonus=gdata.get("permanent_bonus", {}),
                    )

                for mdata in raw.get("cycle_modifier_pool", []):
                    self.cycle_modifiers.append(
                        CycleModifierData(
                            id=mdata.get("id", "mod_default"),
                            name=mdata.get("name", "特異点"),
                            description=mdata.get("description", ""),
                            target_goal=mdata.get("target_goal", ""),
                            reward_meta_points=mdata.get("reward_meta_points", 50),
                            positive_effects=mdata.get("positive_effects", {}),
                            negative_effects=mdata.get("negative_effects", {}),
                        )
                    )

                self.fragment_templates = raw.get("fragment_templates", {})
            except Exception as e:
                logger.exception("Unhandled exception")
                print(f"[MetaProgressionRegistry] Load failed: {e}")

        # フォールバックデフォルト
        if not self.fragment_templates:
            self.fragment_templates = {
                "prefixes": {
                    "combat": ["猛者たる", "剛槍の", "不抜の"],
                    "magic": ["魔導の", "秘術の", "星詠みの"],
                    "survival": ["不死身の", "強靭なる"],
                    "exploration": ["探求の", "遍歴の"],
                    "social": ["信望の", "友愛の"],
                },
                "roots": {
                    "combat": ["武勇の記憶", "剣閃の残照"],
                    "magic": ["叡智の記憶", "魔導の刻印"],
                    "survival": ["生命の残響", "生存の記憶"],
                    "exploration": ["踏破の記憶", "道標の記憶"],
                    "social": ["絆の記憶", "盟約の追憶"],
                },
            }


REGISTRY = MetaProgressionRegistry()


class MemoryFragmentGenerator:
    """動的記憶の欠片生成器"""

    @classmethod
    def generate(
        cls,
        player: Any,
        trigger_type: str = "general",
        context: dict[str, Any] | None = None,
        registry: MetaProgressionRegistry | None = None,
    ) -> MemoryFragmentData:
        reg = registry or REGISTRY
        if not reg.fragment_templates:
            reg.load()

        context = context or {}
        generation = getattr(player, "reincarnation_count", 0) + 1

        # カテゴリ決定ロジック (トリガーやプレイヤー特性から判定)
        category = context.get("category")
        if not category:
            if trigger_type in ("boss_kill", "combat_mastery"):
                category = "combat"
            elif trigger_type in ("spell_mastery", "ancient_relic"):
                category = "magic"
            elif trigger_type in ("near_death", "survival_milestone"):
                category = "survival"
            elif trigger_type in ("deep_dungeon", "explore_secret"):
                category = "exploration"
            elif trigger_type in ("friend_help", "faction_leader"):
                category = "social"
            else:
                # プレイヤーのプレイスタイルから推定
                attrs = getattr(player, "attributes", None)
                if attrs and getattr(attrs, "magic", 10) > 18:
                    category = "magic"
                elif attrs and getattr(attrs, "strength", 10) > 18:
                    category = "combat"
                else:
                    category = random.choice(
                        ["combat", "magic", "survival", "exploration", "social"]
                    )

        prefixes = reg.fragment_templates.get("prefixes", {}).get(category, ["神秘の"])
        roots = reg.fragment_templates.get("roots", {}).get(category, ["前世の記憶"])

        prefix = random.choice(prefixes)
        root = random.choice(roots)
        name = f"【第{generation}世代】{prefix}{root}"

        # バフ特性の動的決定
        buff_traits: dict[str, float] = {}
        unique_seed = random.randint(100, 999)
        frag_id = f"frag_gen{generation}_{category}_{unique_seed}"

        if category == "combat":
            buff_traits["physical_atk_bonus"] = round(random.uniform(2.0, 6.0), 1)
            buff_traits["str_bonus"] = random.randint(1, 3)
            lore = f"かつて武器を手に強敵を討ち倒した第{generation}世代の武勇の残照。"
        elif category == "magic":
            buff_traits["magic_atk_bonus"] = round(random.uniform(2.0, 6.0), 1)
            buff_traits["mp_max_bonus"] = random.randint(5, 15)
            lore = f"深遠なる魔導の真理に触れた第{generation}世代の叡智の光。"
        elif category == "survival":
            buff_traits["hp_max_bonus"] = random.randint(10, 25)
            buff_traits["defense_bonus"] = round(random.uniform(1.5, 4.5), 1)
            lore = f"幾多の死線を乗り越え培われた第{generation}世代の不屈の生命力。"
        elif category == "exploration":
            buff_traits["speed_bonus"] = random.randint(1, 3)
            buff_traits["item_find_bonus"] = round(random.uniform(3.0, 8.0), 1)
            lore = f"未知の深淵と秘境を歩み続けた第{generation}世代の道標。"
        else:  # social
            buff_traits["charisma_bonus"] = random.randint(1, 4)
            buff_traits["gold_gain_bonus"] = round(random.uniform(5.0, 15.0), 1)
            lore = f"他者と心を通わせ、大きな絆を紡ぎ出した第{generation}世代の追憶。"

        secrets: list[str] = []
        if random.random() < 0.35:
            secrets.append(f"unlocked_secret_dungeon_theme_{category}")

        return MemoryFragmentData(
            fragment_id=frag_id,
            name=name,
            description=lore,
            generation=generation,
            category=category,
            buff_traits=buff_traits,
            lore_snippet=lore,
            unlocked_secrets=secrets,
        )


class MetaProgressionManager:
    """メタゴールと永続進行の総合管理クラス"""

    def __init__(self, registry: MetaProgressionRegistry | None = None):
        self.registry = registry or REGISTRY
        if not self.registry.meta_goals:
            self.registry.load()
        self._awarded_truth_piece_categories: set[str] = set()

    def check_and_award_truth_piece_sets(self, player: Any, engine: Any | None = None) -> None:
        """カテゴリごとの断片セットが完了したら真実の一片を付与"""
        arch_reg = ArchaeologyRegistry()
        # すべての断片を取得し、カテゴリごとにグループ化
        fragments_by_category: dict[str, list[str]] = {}
        for frag_id, frag_data in arch_reg._fragments.items():
            category = frag_data.get("category", "unknown")
            if category not in fragments_by_category:
                fragments_by_category[category] = []
            fragments_by_category[category].append(frag_id)

        # プレイヤーが収集した断片IDリストを取得
        reinc_comp = player.get_component(ReincarnationComponent)
        collected_fragment_ids = set()
        for frag_dict in reinc_comp.collected_fragments:
            if isinstance(frag_dict, dict):
                fid = frag_dict.get("fragment_id")
                if fid:
                    collected_fragment_ids.add(fid)

        # 各カテゴリについて、すべての断片を収集していたら真実の一片を付与
        for category, fragment_ids in fragments_by_category.items():
            if not fragment_ids:
                continue
            # すべての断片を収集しているかチェック
            if all(fid in collected_fragment_ids for fid in fragment_ids):
                # まだこのカテゴリの真実の一片を付与していない場合のみ付与
                if category not in self._awarded_truth_piece_categories:
                    # 真実の一片を付与
                    archaeology_comp = player.get_component(ArchaeologyComponent)
                    archaeology_comp.truth_pieces.append(f"TruthPiece_{category}")
                    self._awarded_truth_piece_categories.add(category)
                    if engine and hasattr(engine, "log"):
                        engine.log(
                            f"★★★【真実の一片】{category}の断片セットをコンプリート！",
                            (255, 215, 0),
                        )

    def roll_cycle_modifiers(self, count: int = 2, seed: int | None = None) -> list[dict[str, Any]]:
        """転生時に付与するランダムな周回特異点を抽選"""
        if seed is not None:
            rng = random.Random(seed)
        else:
            rng = random

        pool = list(self.registry.cycle_modifiers)
        if not pool:
            return []

        selected = rng.sample(pool, min(count, len(pool)))
        return [m.to_dict() for m in selected]

    def add_memory_fragment(
        self, player: Any, fragment: MemoryFragmentData, engine: Any | None = None
    ) -> bool:
        """プレイヤーに記憶の欠片を付与し、通知・バフを同期"""
        frag_dict = fragment.to_dict()

        # ReincarnationComponent に蓄積
        reinc_comp = player.get_component(ReincarnationComponent)
        # 重複チェック (ID)
        if any(
            f.get("fragment_id") == fragment.fragment_id
            for f in reinc_comp.collected_fragments
            if isinstance(f, dict)
        ):
            return False

        reinc_comp.collected_fragments.append(frag_dict)
        self.check_and_award_truth_piece_sets(player, engine)

        # StorytellerComponent にも断片として連携
        story_comp = player.get_component(StorytellerComponent)
        if frag_dict["name"] not in story_comp.memory_fragments:
            story_comp.memory_fragments.append(frag_dict["name"])

        # メッセージ通知
        if engine and hasattr(engine, "log"):
            engine.log(f"★【記憶の残照】『{fragment.name}』を心に刻んだ！", (255, 215, 0))

        # メタゴール判定
        self.check_meta_goals(player, engine)
        # 永続ボーナス再計算
        self.recalculate_and_apply_bonuses(player)
        return True

    def check_meta_goals(self, player: Any, engine: Any | None = None) -> list[str]:
        """メタゴールの達成状況を評価"""
        ach_comp = player.get_component(AchievementComponent)
        reinc_comp = player.get_component(ReincarnationComponent)
        player.get_component(TitleComponent)

        completed_new: list[str] = []

        for gid, gdata in self.registry.meta_goals.items():
            if ach_comp.meta_progression.get(gid, 0) >= 1:
                continue

            metric = gdata.target_metric
            target = gdata.target_value
            achieved = False

            if metric == "cumulative_depth":
                current = ach_comp.meta_progression.get("cumulative_depth_stat", 0)
                achieved = current >= target
            elif metric == "collected_fragments_count":
                achieved = len(reinc_comp.collected_fragments) >= target
            elif metric == "reincarnation_count":
                achieved = reinc_comp.reincarnation_count >= target
            elif metric == "unique_fragment_categories":
                categories = {
                    f.get("category") for f in reinc_comp.collected_fragments if isinstance(f, dict)
                }
                achieved = len(categories) >= target

            if achieved:
                ach_comp.meta_progression[gid] = 1
                completed_new.append(gid)
                if engine and hasattr(engine, "log"):
                    engine.log(
                        f"🏆【メタゴール達成】『{gdata.name}』！ 永続の加護を得た！",
                        (255, 180, 50),
                    )

        return completed_new

    def recalculate_and_apply_bonuses(self, player: Any) -> dict[str, float]:
        """記憶の欠片と達成メタゴールから永続ボーナスを集計して適用（冪等性を担保）"""
        ach_comp = player.get_component(AchievementComponent)
        reinc_comp = player.get_component(ReincarnationComponent)
        attrs = getattr(player, "attributes", None)

        # 0. 前回適用済みのボーナスがあればロールバック（二重適用防止）
        prev_bonuses = getattr(ach_comp, "permanent_bonuses", {}) or {}
        if prev_bonuses:
            if attrs:
                if "str_bonus" in prev_bonuses:
                    attrs.strength -= int(prev_bonuses["str_bonus"])
                if "all_attributes" in prev_bonuses:
                    bonus = int(prev_bonuses["all_attributes"])
                    attrs.strength -= bonus
                    attrs.endurance -= bonus
                    attrs.dexterity -= bonus
                    attrs.perception -= bonus
                    attrs.learning -= bonus
                    attrs.will -= bonus
                    attrs.magic -= bonus
                    attrs.charisma -= bonus
            if "speed_bonus" in prev_bonuses and hasattr(player, "speed"):
                player.speed -= int(prev_bonuses["speed_bonus"])
            if "speed" in prev_bonuses and hasattr(player, "speed"):
                player.speed -= int(prev_bonuses["speed"])

        total_bonuses: dict[str, float] = {}

        # 1. メタゴール達成によるボーナス
        for gid, gdata in self.registry.meta_goals.items():
            if ach_comp.meta_progression.get(gid, 0) >= 1:
                for bkey, bval in gdata.permanent_bonus.items():
                    total_bonuses[bkey] = total_bonuses.get(bkey, 0.0) + float(bval)

        # 2. 収集した記憶の欠片によるボーナス
        for frag in reinc_comp.collected_fragments:
            if isinstance(frag, dict):
                traits = frag.get("buff_traits", {})
                for tkey, tval in traits.items():
                    total_bonuses[tkey] = total_bonuses.get(tkey, 0.0) + float(tval)

        # 3. プレイヤーへの実数値適用
        ach_comp.permanent_bonuses = {
            k: int(v) if isinstance(v, (int, float)) and float(v).is_integer() else v
            for k, v in total_bonuses.items()
        }

        # 主能力・HP/MP等のステータス反映
        if attrs:
            if "str_bonus" in total_bonuses:
                attrs.strength += int(total_bonuses["str_bonus"])
            if "all_attributes" in total_bonuses:
                bonus = int(total_bonuses["all_attributes"])
                attrs.strength += bonus
                attrs.endurance += bonus
                attrs.dexterity += bonus
                attrs.perception += bonus
                attrs.learning += bonus
                attrs.will += bonus
                attrs.magic += bonus
                attrs.charisma += bonus

        if "speed_bonus" in total_bonuses and hasattr(player, "speed"):
            player.speed += int(total_bonuses["speed_bonus"])
        if "speed" in total_bonuses and hasattr(player, "speed"):
            player.speed += int(total_bonuses["speed"])

        # HP / MP の再計算と現在値の調整
        if hasattr(player, "calculate_max_hp"):
            hp_bonus = int(total_bonuses.get("max_hp", 0)) + int(
                total_bonuses.get("hp_max_bonus", 0)
            )
            player.max_hp = player.calculate_max_hp() + hp_bonus
            player.hp = min(player.hp, player.max_hp)

        if hasattr(player, "calculate_max_mp"):
            mp_bonus = int(total_bonuses.get("max_mp", 0)) + int(
                total_bonuses.get("mp_max_bonus", 0)
            )
            player.max_mp = player.calculate_max_mp() + mp_bonus
            player.mp = min(player.mp, player.max_mp)

        return total_bonuses
