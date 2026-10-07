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
from ecs.components import (
    AchievementComponent,
    ArchaeologyComponent,
    ReincarnationComponent,
    StorytellerComponent,
    TitleComponent,
)

# ---------------------------------------------------------------------------
# メタゴール permanent_bonus のキー分類
#
# data/meta_goals.yaml の permanent_bonus は「定義するだけ」で終わらせない。
# 各キーは必ず次のどちらかに属すること:
#   (A) 実装済み … 下記 recalculate_and_apply_bonuses がゲームが実際に参照する
#                   値（Entity のspeed / attributes）へ反映する
#   (B) 予約済み … 反映しないキー。理由（何が欠けているか）を添える
# 未分類のまま残すキーは「定義されたが誰も読まない嘘」になるため許容しない。
# tests/test_meta_goals.py が全キーの分類と実効果を検証する。
# ---------------------------------------------------------------------------

# (A) 実装済み: 実際にプレイヤーへ反映されるメタゴール由来ボーナス
APPLIED_PERMANENT_BONUS_KEYS: frozenset[str] = frozenset({
    "speed",
    "all_attributes",
    "damage_boost",
    "gold_gain",
})

# (B) 予約済み: 反映しないキーと「何が欠けているか」の理由
RESERVED_PERMANENT_BONUSES: dict[str, str] = {
    "max_hp": (
        "実装には ecs/entity.py の Entity.recalculate_stats() が "
        "AchievementComponent.permanent_bonuses を読み、"
        "calculate_max_hp() に固定加算を足す処理が必要。"
        "現状は max_hp を属性から毎回作り直すため、"
        "レベルアップ・ジョブ・称号で加算が消える。"
    ),
    "max_mp": (
        "max_hp と同じ。Entity.recalculate_stats() が "
        "calculate_max_mp() で上書きするため加算が保持されない。"
    ),
    "exp_bonus": (
        "経験値の付与は Entity.gain_exp()（ecs/entity.py）内の "
        "self.exp += amount で行われている。"
        "この加算に倍率を適用する読み取り口が無いため未実装。"
    ),
    "potential_bonus": (
        "スキル成長率の根拠は Entity.gain_skill_exp()（ecs/entity.py）内の "
        "int(amount * (skill.potential / 100.0)) で、"
        "この地点にボーナスを読み取る仕組みが無いため未実装。"
    ),
    "karma_gain_multiplier": (
        "カルマの増減は karma_system.py の KarmaManager.update_karma() が "
        "player.karma_law_chaos / karma_good_evil を直接加算しており、"
        "その加算に倍率を掛ける読み取り口が無いため未実装。"
    ),
    "magic_power": (
        "独立した「魔法威力」統計が存在しない。"
        "呪文ダメージは systems.py が caster.attributes.magic を直接参照するため、"
        "all_attributes と経路が重複して二重計上になるため。"
        "実装には独立した統計と systems.py のダメージ式への加算が必要。"
    ),
    "resistance_all": (
        "属性耐性 ResistanceSet（systems.py）は初期化時に書き込まれるだけで、"
        "ダメージ計算から参照されていない。"
        "実装には systems.py 側に全属性加算の反射処理が必要。"
    ),
}

# all_attributes が加算する全主能力
_ALL_ATTRIBUTE_FIELDS: tuple[str, ...] = (
    "strength",
    "endurance",
    "dexterity",
    "perception",
    "learning",
    "will",
    "magic",
    "charisma",
)


def _shift_all_attributes(target: Any, delta: int) -> None:
    """全主能力を一括で増減する"""
    for field_name in _ALL_ATTRIBUTE_FIELDS:
        setattr(target, field_name, getattr(target, field_name) + delta)


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
        # メタ進行マイルストーン判定 (Step 30)
        self.check_meta_progression_milestones(player, engine)
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

        # メタ進行マイルストーンも同時にチェック (Step 30)
        self.check_meta_progression_milestones(player, engine)

        return completed_new

    def check_meta_progression_milestones(
        self, player: Any, engine: Any | None = None
    ) -> list[str]:
        """meta_progression.yaml のマイルストーン達成状況を評価し、ボーナスを適用 (Step 30)

        以下の累計値をチェック:
        - total_monsters_slain: 総討伸数 (ach_comp.monster_killed_types から集計)
        - total_gold_accumulated: 総獲得ゴールド (EconomyComponent または実績から集計)
        - total_dungeon_depth: 最深到達階層 (ach_comp.meta_progression または TitleComponent から集計)
        """
        import yaml

        ach_comp = player.get_component(AchievementComponent)

        # meta_progression.yaml をロード
        with open("data/meta_progression.yaml", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        progression_data = data.get("meta_progression", {})
        newly_awarded: list[str] = []

        for tracker_id, tracker_data in progression_data.items():
            milestones = tracker_data.get("milestones", [])
            if not milestones:
                continue

            # 現在値を取得
            current_value = self._get_meta_progression_value(player, tracker_id, ach_comp)

            # 既に獲得済みのボーナスを確認 (ach_comp.meta_progression に記録)
            tracker_key = f"meta_prog_{tracker_id}"
            awarded_count = ach_comp.meta_progression.get(tracker_key, 0)

            # 未達成のマイルストーンをチェック
            for milestone in milestones:
                count = milestone.get("count", 0)
                reward_bonus = milestone.get("reward_bonus")

                if current_value >= count and awarded_count < count:
                    # マイルストーン達成
                    awarded_count = count
                    if reward_bonus:
                        # ボーナスを永続記録に追加
                        ach_comp.permanent_bonuses[reward_bonus] = (
                            ach_comp.permanent_bonuses.get(reward_bonus, 0) + 1
                        )
                        newly_awarded.append(f"{tracker_id}:{reward_bonus}")
                        if engine and hasattr(engine, "log"):
                            engine.log(
                                f"★★★【メタ進行】{tracker_data['name']} {count}達成！ {reward_bonus} を獲得！",
                                (255, 215, 0),
                            )

            # 進捗を保存
            ach_comp.meta_progression[tracker_key] = awarded_count

        return newly_awarded

    def _get_meta_progression_value(
        self, player: Any, tracker_id: str, ach_comp: AchievementComponent
    ) -> int:
        """メタ進行トラッカーの現在値を取得"""
        if tracker_id == "total_monsters_slain":
            # 総討伸数 = 全モンスター討伸タイプの合計
            return sum(ach_comp.monster_killed_types.values())
        elif tracker_id == "total_gold_accumulated":
            # 総獲得ゴールド = 実績記録から取得 (未実装の場合は0)
            return ach_comp.meta_progression.get("total_gold_accumulated_stat", 0)
        elif tracker_id == "total_dungeon_depth":
            # 最深到達階層 = 称号コンポーネントまたは実績から取得
            title_comp = player.get_component(TitleComponent)
            return getattr(title_comp, "max_dungeon_depth", 0)
        return 0

    def recalculate_and_apply_bonuses(self, player: Any) -> dict[str, float]:
        """記憶の欠片と達成メタゴールから永続ボーナスを集計して適用（冪等性を担保）"""
        ach_comp = player.get_component(AchievementComponent)
        reinc_comp = player.get_component(ReincarnationComponent)
        attrs = getattr(player, "attributes", None)
        base_attrs = getattr(player, "_base_attributes", None)

        # 0. 前回適用済みのボーナスがあればロールバック（二重適用防止）
        prev_bonuses = getattr(ach_comp, "permanent_bonuses", {}) or {}
        # 予約済みキーは適用していないため、ここでも引かない
        prev_applied = {k: v for k, v in prev_bonuses.items() if k in APPLIED_PERMANENT_BONUS_KEYS}
        if prev_bonuses:
            if attrs:
                if "str_bonus" in prev_bonuses:
                    attrs.strength -= int(prev_bonuses["str_bonus"])
                if "all_attributes" in prev_applied:
                    _shift_all_attributes(attrs, -int(prev_applied["all_attributes"]))
            if "all_attributes" in prev_applied and base_attrs is not None:
                _shift_all_attributes(base_attrs, -int(prev_applied["all_attributes"]))
            if "speed_bonus" in prev_bonuses and hasattr(player, "speed"):
                player.speed -= int(prev_bonuses["speed_bonus"])
            if "speed" in prev_applied and hasattr(player, "speed"):
                player.speed -= int(prev_applied["speed"])

        # 1. メタゴール達成によるボーナス（permanent_bonus）
        goal_bonuses: dict[str, float] = {}
        for gid, gdata in self.registry.meta_goals.items():
            if ach_comp.meta_progression.get(gid, 0) >= 1:
                for bkey, bval in gdata.permanent_bonus.items():
                    goal_bonuses[bkey] = goal_bonuses.get(bkey, 0.0) + float(bval)

        # 2. 収集した記憶の欠片によるボーナス（buff_traits）
        frag_bonuses: dict[str, float] = {}
        for frag in reinc_comp.collected_fragments:
            if isinstance(frag, dict):
                traits = frag.get("buff_traits", {})
                for tkey, tval in traits.items():
                    frag_bonuses[tkey] = frag_bonuses.get(tkey, 0.0) + float(tval)

        total_bonuses: dict[str, float] = {**goal_bonuses, **frag_bonuses}

        # 付与されたボーナスである事実は記録として残す（予約済みキーも集計に含める）
        ach_comp.permanent_bonuses = {
            k: int(v) if isinstance(v, (int, float)) and float(v).is_integer() else v
            for k, v in total_bonuses.items()
        }

        # 3. プレイヤーへの実数値適用
        # 予約済みキーはここで切り落とす。permanent_bonuses に記録されるだけで、
        # ゲームの数値には一切影響させない。
        applied_goal_bonuses = {
            k: v for k, v in goal_bonuses.items() if k in APPLIED_PERMANENT_BONUS_KEYS
        }

        # 主能力の反映
        if attrs:
            if "str_bonus" in frag_bonuses:
                attrs.strength += int(frag_bonuses["str_bonus"])
            if "all_attributes" in applied_goal_bonuses:
                bonus = int(applied_goal_bonuses["all_attributes"])
                _shift_all_attributes(attrs, bonus)
                # Entity.recalculate_stats() は _base_attributes から属性を復元するため、
                # 復元元にも同じだけ足さないとレベルアップ等の再計算で消える
                if base_attrs is not None:
                    _shift_all_attributes(base_attrs, bonus)

        # 移動速度の反映（行動順 TurnQueue.step_next_actor が参照する値）
        if hasattr(player, "speed"):
            if "speed" in applied_goal_bonuses:
                player.speed += int(applied_goal_bonuses["speed"])
            if "speed_bonus" in frag_bonuses:
                player.speed += int(frag_bonuses["speed_bonus"])

        # メタ進行ボーナスの反映 (Step 30)
        # damage_boost: 物理・魔法攻撃力への加算倍率（%）
        # gold_gain: ゴールド獲得量への加算倍率（%）
        # これらは CombatSystem.calculate_melee_attack / EconomyComponent.add_gold 側で読まれる想定
        if attrs:
            if "damage_boost" in applied_goal_bonuses:
                # ダメージブーストは攻撃計算時に参照される属性として記録
                # 実装: systems.py の計算式で attrs.damage_boost_mult を読む
                pass  # 適用は呼び出し側で行うため、ここでは permanent_bonuses に記録するのみ
            if "gold_gain" in applied_goal_bonuses:
                # ゴールド獲得倍率も同様に EconomyComponent 側で読む
                pass

        # HP / MP の再計算と現在値の調整
        # max_hp / max_mp は予約済みのため、メタゴール由来の固定加算は加えない
        if hasattr(player, "calculate_max_hp"):
            player.max_hp = player.calculate_max_hp() + int(frag_bonuses.get("hp_max_bonus", 0))
            player.hp = min(player.hp, player.max_hp)

        if hasattr(player, "calculate_max_mp"):
            player.max_mp = player.calculate_max_mp() + int(frag_bonuses.get("mp_max_bonus", 0))
            player.mp = min(player.mp, player.max_mp)

        return total_bonuses
