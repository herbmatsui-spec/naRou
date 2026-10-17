"""
Elona Roguelike Clone - Expanded Entity, Pet, & God Systems
Modularized Component-Based Architecture (ECS)
"""

from __future__ import annotations

import logging
import random
from dataclasses import field
from typing import Any, TypeVar

from constants import AI_ROLE_KITER, DEFAULT_GOD_ID, KITER_PREFERRED_RANGE

logger = logging.getLogger(__name__)

from ecs.components import (
    AchievementComponent,
    AffectionComponent,
    ArchaeologyComponent,
    Attributes,
    AttributesComponent,
    BaseStatsComponent,
    EconomyComponent,
    EmoteComponent,
    GuildFactionComponent,
    LevelComponent,
    PetAIComponent,
    PetProfileComponent,
    ProceduralQuestComponent,
    ReincarnationComponent,
    Skill,
    SkillFusionComponent,
    SkillTreeJobComponent,
    StatusEffectsComponent,
    StorytellerComponent,
    TitleComponent,
)

# 後方互換: PetAI を PetAIComponent の別名として再エクスポート
PetAI = PetAIComponent

# 後方互換: GodInfo を god_system から再エクスポート (Step 26)
# プロパティ委譲ヘルパ (Step 41)
from core.progression_manager import ProgressionFlagComponent
from delegate_utils import delegate  # noqa: E402
from god_system import GodInfo  # noqa: E402

T = TypeVar("T")


class Entity:
    """キャラクター基底クラス（ECSコンポーネント指向リファクタリング適用）"""

    def __init__(
        self,
        x: int = 0,
        y: int = 0,
        char: str = "@",
        color: tuple[int, int, int] = (255, 255, 255),
        name: str = "Unknown",
        is_player: bool = False,
        is_pet: bool = False,
        speed: int = 70,
        attributes: Attributes | dict[str, int] | None = None,
    ):
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.name = name
        self.is_player = is_player
        self.is_pet = is_pet
        self.speed = speed
        self.energy = 0

        # 敵意図予測 (提案2) — 次回ターンに取る行動の予測。描画のみに使用。
        self.next_intent: dict | None = None
        # 敵AIロール・陣形 (提案4)
        self.ai_role: str = self._default_ai_role(name)
        self.preferred_range: int = KITER_PREFERRED_RANGE if self.ai_role == AI_ROLE_KITER else 1

        # === ECS コンポーネントコンテナ ===
        self.components: dict[type, Any] = {}
        self._init_components()

        # 主能力（コンポーネント初期化後に設定）
        self._init_attributes = attributes

        # ベース能力値（ジョブ補正前の生の値）
        self._base_attributes: AttributesComponent | None = None

        # レベルと経験値 (LevelComponentへの委譲プロパティ)
        self.level = 1
        self.exp = 0
        # exp_next はプロパティで動的計算 (Step 21)

        # ペット関連 (ステップ73, 74, 80) — AffectionComponent/PetProfileComponent に委譲
        self.tactic: str = PetAI.TACTIC_ASSAULT

        # スキル一覧
        if self.is_player or self.is_pet:
            self._skills: dict[str, Skill] | None = self._init_default_skills()
        else:
            self._skills: dict[str, Skill] | None = None

        # TODO: Story/world state fields
        # 信仰システム (ステップ84, 86)
        self.god_id: str = DEFAULT_GOD_ID
        self.piety: int = 0  # 信仰深度
        self.received_servant: bool = False
        self.received_artifact: bool = False

        # 突然変異＆エーテル病 (ステップ56, 57, 122)
        self.mutations: dict[str, int] = {}
        self.ether_disease_stages: list[str] = []

        # ペット一覧
        self.pets: list[Entity] = []

        # 状態異常リスト (Step 70: HUD 表示のため全 Entity で常時存在)
        self.status_effects: list = []

        # 属性耐性 & 弱点 (PR #8 integration: origin/main より移植, Step 51, 53)
        self.base_resistances: dict[str, int] = {}
        self.weaknesses: list[str] = []
        # ECS 状態異常 API (add_status 等) が一度でも使われたら True になり、
        # status_effects プロパティの返却先がリストからコンポーネントへ切り替わる。
        self._status_effects_ecs: bool = False

        # チュートリアル完了履歴 (Step 1.2)
        self.completed_tutorials: set[str] = set()
        self.pending_tutorial_popup: dict[str, Any] | None = None

        # 主能力コンポーネントに初期値を適用
        self._apply_init_attributes()

        # 派生ステータス初期化
        self.max_hp = self.calculate_max_hp()
        self.hp = self.max_hp
        self.max_mp = self.calculate_max_mp()
        self.mp = self.max_mp
        self.max_stamina = self.calculate_max_stamina()
        self.stamina = self.max_stamina

    def _apply_init_attributes(self) -> None:
        """初期能力値をコンポーネントに適用し、ベース値を保存"""
        attrs_comp = self.get_required_component(AttributesComponent)
        if self._init_attributes is not None:
            if isinstance(self._init_attributes, dict):
                for k, v in self._init_attributes.items():
                    if hasattr(attrs_comp, k):
                        setattr(attrs_comp, k, v)
            else:
                # 既存の Attributes オブジェクトからコピー
                for k in attrs_comp.to_dict():
                    if hasattr(self._init_attributes, k):
                        setattr(attrs_comp, k, getattr(self._init_attributes, k))

        # ベース能力値を保存（ジョブ補正前の生の値）
        self._base_attributes = AttributesComponent()
        for k, v in attrs_comp.to_dict().items():
            setattr(self._base_attributes, k, v)

        delattr(self, "_init_attributes")

    def _init_components(self) -> None:
        """サブシステムごとのコンポーネントを初期化"""
        self.components[TitleComponent] = TitleComponent()
        self.components[GuildFactionComponent] = GuildFactionComponent()
        self.components[AffectionComponent] = AffectionComponent()
        self.components[PetProfileComponent] = PetProfileComponent()
        self.components[EmoteComponent] = EmoteComponent()
        self.components[PetAIComponent] = PetAIComponent()
        self.components[AchievementComponent] = AchievementComponent()
        self.components[ReincarnationComponent] = ReincarnationComponent()
        self.components[SkillTreeJobComponent] = SkillTreeJobComponent()
        self.components[SkillFusionComponent] = SkillFusionComponent()
        self.components[StorytellerComponent] = StorytellerComponent()
        self.components[AttributesComponent] = AttributesComponent()
        self.components[ProceduralQuestComponent] = ProceduralQuestComponent()
        self.components[ArchaeologyComponent] = ArchaeologyComponent()
        self.components[ProgressionFlagComponent] = ProgressionFlagComponent()
        self.components[BaseStatsComponent] = BaseStatsComponent()
        self.components[EconomyComponent] = EconomyComponent()
        self.components[LevelComponent] = LevelComponent()
        self.components[StatusEffectsComponent] = StatusEffectsComponent()

    def _lookup_component(self, component_type: type[T]) -> T | None:
        """コンポーネントを検索し、見つかったインスタンスを返す。

        見つからなければ None を返す。自動生成は行わない。
        クラス名によるフォールバック検索も行う（naRou/ecs 名前空間の違いを吸収）。
        """
        # First try exact class match
        if component_type in self.components:
            return self.components[component_type]
        # Then try by class name (handles naRou vs ecs namespace differences)
        type_name = component_type.__name__
        for comp_class, comp_instance in self.components.items():
            if comp_class.__name__ == type_name:
                return comp_instance
        return None

    def _assert_component_type(self, component_type: type[T], instance: Any) -> T:
        """コンポーネントインスタンスが要求型であることを型ガードで検証する。"""
        if not isinstance(instance, component_type):
            raise TypeError(
                f"Component stored as {type(instance).__name__!r} is not an instance of "
                f"{component_type.__name__}; expected {component_type.__name__}"
            )
        return instance

    def get_component(self, component_type: type[T]) -> T:
        """指定されたコンポーネントを取得（存在しなければ初期化して登録）"""
        instance = self._lookup_component(component_type)
        if instance is None:
            self.components[component_type] = component_type()
            return self.components[component_type]
        # 正クラス一致ヒットなら型ガードを適用（components dict への誤型格納を検出）。
        # 名前フォールバック（naRou/ecs 名前空間の重複クラス）は構造互換を前提とし、
        # 厳密な isinstance は適用しない。
        if component_type in self.components:
            return self._assert_component_type(component_type, instance)
        return instance

    def get_required_component(self, component_type: type[T]) -> T:
        """必須コンポーネントを取得する。

        存在しなければ KeyError を発生させる（自動生成は行わない）。
        必須コンポーネントの存在チェックはこのメソッドに集中する。
        """
        instance = self._lookup_component(component_type)
        if instance is None:
            raise KeyError(
                f"Entity {self.name!r} lacks required component {component_type.__name__}"
            )
        # 型ガード: 登録済みインスタンスが要求型であることを保証
        return self._assert_component_type(component_type, instance)

    def has_component(self, component_type: type) -> bool:
        """指定されたコンポーネントを所持しているか判定"""
        return self._lookup_component(component_type) is not None

    # -------------------------------------------------------------
    # 称号・統計プロパティ (TitleComponent への委譲)
    # -------------------------------------------------------------
    @property
    def titles(self) -> list[str]:
        return self.get_required_component(TitleComponent).titles

    @titles.setter
    def titles(self, val: list[str]):
        self.get_required_component(TitleComponent).titles = val

    @property
    def equipped_title(self) -> str | None:
        return self.get_required_component(TitleComponent).equipped_title

    @equipped_title.setter
    def equipped_title(self, val: str | None):
        self.get_required_component(TitleComponent).equipped_title = val

    @property
    def title_notifications(self) -> list[str]:
        return self.get_required_component(TitleComponent).title_notifications

    @title_notifications.setter
    def title_notifications(self, val: list[str]):
        self.get_required_component(TitleComponent).title_notifications = val

    @property
    def kill_counts(self) -> dict[str, int]:
        return self.get_required_component(TitleComponent).kill_counts

    @kill_counts.setter
    def kill_counts(self, val: dict[str, int]):
        self.get_required_component(TitleComponent).kill_counts = val

    @property
    def craft_counts(self) -> dict[str, int]:
        return self.get_required_component(TitleComponent).craft_counts

    @craft_counts.setter
    def craft_counts(self, val: dict[str, int]):
        self.get_required_component(TitleComponent).craft_counts = val

    @property
    def max_dungeon_depth(self) -> int:
        return self.get_required_component(TitleComponent).max_dungeon_depth

    @max_dungeon_depth.setter
    def max_dungeon_depth(self, val: int):
        self.get_required_component(TitleComponent).max_dungeon_depth = val

    @property
    def near_death_count(self) -> int:
        return self.get_required_component(TitleComponent).near_death_count

    @near_death_count.setter
    def near_death_count(self, val: int):
        self.get_required_component(TitleComponent).near_death_count = val

    @property
    def total_turns(self) -> int:
        return self.get_required_component(TitleComponent).total_turns

    @total_turns.setter
    def total_turns(self, val: int):
        self.get_required_component(TitleComponent).total_turns = val

    # -------------------------------------------------------------
    # 基本ステータスプロパティ (BaseStatsComponent への委譲)
    # -------------------------------------------------------------
    @property
    def hp(self) -> int:
        return self.get_required_component(BaseStatsComponent).hp

    @hp.setter
    def hp(self, val: int):
        self.get_required_component(BaseStatsComponent).hp = val

    @property
    def max_hp(self) -> int:
        return self.get_required_component(BaseStatsComponent).max_hp

    @max_hp.setter
    def max_hp(self, val: int):
        self.get_required_component(BaseStatsComponent).max_hp = val

    @property
    def mp(self) -> int:
        return self.get_required_component(BaseStatsComponent).mp

    @mp.setter
    def mp(self, val: int):
        self.get_required_component(BaseStatsComponent).mp = val

    @property
    def max_mp(self) -> int:
        return self.get_required_component(BaseStatsComponent).max_mp

    @max_mp.setter
    def max_mp(self, val: int):
        self.get_required_component(BaseStatsComponent).max_mp = val

    # -------------------------------------------------------------
    # APプロパティ (BaseStatsComponent への委譲) — Phase 2 Step 34
    # -------------------------------------------------------------
    @property
    def ap(self) -> int:
        return self.get_required_component(BaseStatsComponent).ap

    @ap.setter
    def ap(self, val: int):
        self.get_required_component(BaseStatsComponent).ap = val

    @property
    def max_ap(self) -> int:
        return self.get_required_component(BaseStatsComponent).max_ap

    @max_ap.setter
    def max_ap(self, val: int):
        self.get_required_component(BaseStatsComponent).max_ap = val

    def reset_ap(self) -> None:
        """ターン開始時にAPを最大値まで回復"""
        self.ap = self.max_ap

    def can_act(self, cost: int = 1) -> bool:
        """指定コスト分のAPがあるか判定"""
        return self.ap >= cost

    def spend_ap(self, cost: int = 1) -> bool:
        """APを消費する。足りなければFalseを返し消費しない"""
        if self.ap >= cost:
            self.ap -= cost
            return True
        return False

    # -------------------------------------------------------------
    # 向きプロパティ (BaseStatsComponent への委譲) — Step 3A
    # -------------------------------------------------------------
    @property
    def facing(self) -> str:
        return self.get_required_component(BaseStatsComponent).facing

    @facing.setter
    def facing(self, val: str):
        self.get_required_component(BaseStatsComponent).facing = val

    # -------------------------------------------------------------
    # 経済プロパティ (EconomyComponent への委譲) — delegate_utils 使用 (Step 41)
    # -------------------------------------------------------------
    gold = delegate(lambda self: self.get_required_component(EconomyComponent), "gold")
    platinum = delegate(lambda self: self.get_required_component(EconomyComponent), "platinum")

    # -------------------------------------------------------------
    # レベル・経験値プロパティ (LevelComponent への委譲)
    # -------------------------------------------------------------
    @property
    def level(self) -> int:
        return self.get_required_component(LevelComponent).level

    @level.setter
    def level(self, val: int):
        self.get_required_component(LevelComponent).level = val

    @property
    def exp(self) -> int:
        return self.get_required_component(LevelComponent).exp

    @exp.setter
    def exp(self, val: int):
        self.get_required_component(LevelComponent).exp = val

    @property
    def exp_next(self) -> int:
        """次のレベルに必要な経験値を計算 (Step 21: balance_standards.yaml から読込)"""
        # 遅延インポートで循環参照を避ける
        from pathlib import Path

        import yaml

        config_path = Path(__file__).resolve().parents[2] / "data" / "balance_standards.yaml"
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            exp_curve = data.get("exp_curve", {"base": 120, "growth": 1.35})
            base = exp_curve.get("base", 120)
            growth = exp_curve.get("growth", 1.35)
        else:
            base = 120
            growth = 1.35

        # level 1 -> 2 には base、level n -> n+1 には base * growth^(n-1)
        return int(base * (growth ** (self.level - 1)))

    # exp_next setter は不要 (計算値のため)

    @property
    def skill_points(self) -> int:
        return self.get_required_component(LevelComponent).skill_points

    @skill_points.setter
    def skill_points(self, val: int):
        self.get_required_component(LevelComponent).skill_points = val

    @property
    def total_skill_points_earned(self) -> int:
        return self.get_required_component(LevelComponent).total_skill_points_earned

    @total_skill_points_earned.setter
    def total_skill_points_earned(self, val: int):
        self.get_required_component(LevelComponent).total_skill_points_earned = val

    # -------------------------------------------------------------
    # 主能力プロパティ (AttributesComponent への委譲) - Step 2
    # -------------------------------------------------------------
    @property
    def attributes(self) -> AttributesComponent:
        """主能力コンポーネントを取得（後方互換性のため直接アクセス可能にする）"""
        return self.get_required_component(AttributesComponent)

    @attributes.setter
    def attributes(self, val: AttributesComponent):
        self.components[AttributesComponent] = val

    # 個別能力値へのアクセス用ヘルパー（後方互換性）
    @property
    def strength(self) -> int:
        return self.attributes.strength

    @strength.setter
    def strength(self, val: int):
        self.attributes.strength = val

    @property
    def endurance(self) -> int:
        return self.attributes.endurance

    @endurance.setter
    def endurance(self, val: int):
        self.attributes.endurance = val

    @property
    def dexterity(self) -> int:
        return self.attributes.dexterity

    @dexterity.setter
    def dexterity(self, val: int):
        self.attributes.dexterity = val

    @property
    def perception(self) -> int:
        return self.attributes.perception

    @perception.setter
    def perception(self, val: int):
        self.attributes.perception = val

    @property
    def learning(self) -> int:
        return self.attributes.learning

    @learning.setter
    def learning(self, val: int):
        self.attributes.learning = val

    @property
    def will(self) -> int:
        return self.attributes.will

    @will.setter
    def will(self, val: int):
        self.attributes.will = val

    @property
    def magic(self) -> int:
        return self.attributes.magic

    @magic.setter
    def magic(self, val: int):
        self.attributes.magic = val

    @property
    def charisma(self) -> int:
        return self.attributes.charisma

    @charisma.setter
    def charisma(self, val: int):
        self.attributes.charisma = val

    # -------------------------------------------------------------
    # ギルド・派閥プロパティ (GuildFactionComponent への委譲)
    # -------------------------------------------------------------
    @property
    def guild_id(self) -> str | None:
        return self.get_required_component(GuildFactionComponent).guild_id

    @guild_id.setter
    def guild_id(self, val: str | None):
        self.get_required_component(GuildFactionComponent).guild_id = val

    @property
    def guild_rank(self) -> str:
        return self.get_required_component(GuildFactionComponent).guild_rank

    @guild_rank.setter
    def guild_rank(self, val: str):
        self.get_required_component(GuildFactionComponent).guild_rank = val

    @property
    def guild_contribution(self) -> int:
        return self.get_required_component(GuildFactionComponent).guild_contribution

    @guild_contribution.setter
    def guild_contribution(self, val: int):
        self.get_required_component(GuildFactionComponent).guild_contribution = val

    @property
    def guild_role(self) -> str | None:
        return self.get_required_component(GuildFactionComponent).guild_role

    @guild_role.setter
    def guild_role(self, val: str | None):
        self.get_required_component(GuildFactionComponent).guild_role = val

    @property
    def faction_reputation(self) -> dict[str, int]:
        return self.get_required_component(GuildFactionComponent).faction_reputation

    @faction_reputation.setter
    def faction_reputation(self, val: dict[str, int]):
        self.get_required_component(GuildFactionComponent).faction_reputation = val

    @property
    def completed_faction_events(self) -> list[str]:
        return self.get_required_component(GuildFactionComponent).completed_faction_events

    @completed_faction_events.setter
    def completed_faction_events(self, val: list[str]):
        self.get_required_component(GuildFactionComponent).completed_faction_events = val

    @property
    def ranking_titles(self) -> list[str]:
        return self.get_required_component(GuildFactionComponent).ranking_titles

    @ranking_titles.setter
    def ranking_titles(self, val: list[str]):
        self.get_required_component(GuildFactionComponent).ranking_titles = val

    @property
    def guild_quest_progress(self) -> dict[str, int]:
        return self.get_required_component(GuildFactionComponent).guild_quest_progress

    @guild_quest_progress.setter
    def guild_quest_progress(self, val: dict[str, int]):
        self.get_required_component(GuildFactionComponent).guild_quest_progress = val

    # -------------------------------------------------------------
    # 実績・メタ進行プロパティ (AchievementComponent への委譲)
    # TODO: Achievement fields - delegated to AchievementComponent
    # -------------------------------------------------------------
    @property
    def achievements(self) -> list[str]:
        return self.get_required_component(AchievementComponent).achievements

    @achievements.setter
    def achievements(self, val: list[str]):
        self.get_required_component(AchievementComponent).achievements = val

    @property
    def achievement_progress(self) -> dict[str, int]:
        return self.get_required_component(AchievementComponent).achievement_progress

    @achievement_progress.setter
    def achievement_progress(self, val: dict[str, int]):
        self.get_required_component(AchievementComponent).achievement_progress = val

    @property
    def achievement_timers(self) -> dict[str, int]:
        return self.get_required_component(AchievementComponent).achievement_timers

    @achievement_timers.setter
    def achievement_timers(self, val: dict[str, int]):
        self.get_required_component(AchievementComponent).achievement_timers = val

    @property
    def monster_killed_types(self) -> dict[str, int]:
        return self.get_required_component(AchievementComponent).monster_killed_types

    @monster_killed_types.setter
    def monster_killed_types(self, val: dict[str, int]):
        self.get_required_component(AchievementComponent).monster_killed_types = val

    @property
    def unique_items_obtained(self) -> list[str]:
        return self.get_required_component(AchievementComponent).unique_items_obtained

    @unique_items_obtained.setter
    def unique_items_obtained(self, val: list[str]):
        self.get_required_component(AchievementComponent).unique_items_obtained = val

    @property
    def social_points(self) -> int:
        return self.get_required_component(AchievementComponent).social_points

    @social_points.setter
    def social_points(self, val: int):
        self.get_required_component(AchievementComponent).social_points = val

    @property
    def weekly_play_time(self) -> int:
        return self.get_required_component(AchievementComponent).weekly_play_time

    @weekly_play_time.setter
    def weekly_play_time(self, val: int):
        self.get_required_component(AchievementComponent).weekly_play_time = val

    @property
    def total_level_earned(self) -> int:
        return self.get_required_component(AchievementComponent).total_level_earned

    @total_level_earned.setter
    def total_level_earned(self, val: int):
        self.get_required_component(AchievementComponent).total_level_earned = val

    @property
    def permanent_bonuses(self) -> dict[str, int]:
        return self.get_required_component(AchievementComponent).permanent_bonuses

    @permanent_bonuses.setter
    def permanent_bonuses(self, val: dict[str, int]):
        self.get_required_component(AchievementComponent).permanent_bonuses = val

    @property
    def meta_progression(self) -> dict[str, int]:
        return self.get_required_component(AchievementComponent).meta_progression

    @meta_progression.setter
    def meta_progression(self, val: dict[str, int]):
        self.get_required_component(AchievementComponent).meta_progression = val

    @property
    def dungeon_floors_visited(self) -> set[tuple[int, int]]:
        return self.get_required_component(AchievementComponent).dungeon_floors_visited

    @dungeon_floors_visited.setter
    def dungeon_floors_visited(self, val: set[tuple[int, int]]):
        self.get_required_component(AchievementComponent).dungeon_floors_visited = val

    @property
    def play_time_seconds(self) -> int:
        return self.get_required_component(AchievementComponent).play_time_seconds

    @play_time_seconds.setter
    def play_time_seconds(self, val: int):
        self.get_required_component(AchievementComponent).play_time_seconds = val

    @property
    def last_festival_check(self) -> str:
        return self.get_required_component(AchievementComponent).last_festival_check

    @last_festival_check.setter
    def last_festival_check(self, val: str):
        self.get_required_component(AchievementComponent).last_festival_check = val

    @property
    def friend_helps(self) -> int:
        return self.get_required_component(AchievementComponent).friend_helps

    @friend_helps.setter
    def friend_helps(self, val: int):
        self.get_required_component(AchievementComponent).friend_helps = val

    @property
    def special_items_combo(self) -> list[str]:
        return self.get_required_component(AchievementComponent).special_items_combo

    @special_items_combo.setter
    def special_items_combo(self, val: list[str]):
        self.get_required_component(AchievementComponent).special_items_combo = val

    @property
    def achievement_notifications(self) -> list[str]:
        return self.get_required_component(AchievementComponent).achievement_notifications

    @achievement_notifications.setter
    def achievement_notifications(self, val: list[str]):
        self.get_required_component(AchievementComponent).achievement_notifications = val

    # -------------------------------------------------------------
    # 輪廻転生・カーマプロパティ (ReincarnationComponent への委譲)
    # -------------------------------------------------------------
    @property
    def reincarnation_count(self) -> int:
        return self.get_required_component(ReincarnationComponent).reincarnation_count

    @reincarnation_count.setter
    def reincarnation_count(self, val: int):
        self.get_required_component(ReincarnationComponent).reincarnation_count = val

    @property
    def karma_law_chaos(self) -> int:
        return self.get_required_component(ReincarnationComponent).karma_law_chaos

    @karma_law_chaos.setter
    def karma_law_chaos(self, val: int):
        self.get_required_component(ReincarnationComponent).karma_law_chaos = val

    @property
    def karma_good_evil(self) -> int:
        return self.get_required_component(ReincarnationComponent).karma_good_evil

    @karma_good_evil.setter
    def karma_good_evil(self, val: int):
        self.get_required_component(ReincarnationComponent).karma_good_evil = val

    @property
    def legacy_skills(self) -> list[str]:
        return self.get_required_component(ReincarnationComponent).legacy_skills

    @legacy_skills.setter
    def legacy_skills(self, val: list[str]):
        self.get_required_component(ReincarnationComponent).legacy_skills = val

    @property
    def unlocked_reincarnation_dungeons(self) -> list[str]:
        return self.get_required_component(ReincarnationComponent).unlocked_reincarnation_dungeons

    @unlocked_reincarnation_dungeons.setter
    def unlocked_reincarnation_dungeons(self, val: list[str]):
        self.get_required_component(ReincarnationComponent).unlocked_reincarnation_dungeons = val

    @property
    def collected_fragments(self) -> list[str]:
        return self.get_required_component(ReincarnationComponent).collected_fragments

    @collected_fragments.setter
    def collected_fragments(self, val: list[str]):
        self.get_required_component(ReincarnationComponent).collected_fragments = val

    @property
    def favor(self) -> dict[str, int]:
        return self.get_required_component(ReincarnationComponent).favor

    @favor.setter
    def favor(self, val: dict[str, int]):
        self.get_required_component(ReincarnationComponent).favor = val

    @property
    def inheritance_selection(self) -> dict[str, Any]:
        return self.get_required_component(ReincarnationComponent).inheritance_selection

    @inheritance_selection.setter
    def inheritance_selection(self, val: dict[str, Any]):
        self.get_required_component(ReincarnationComponent).inheritance_selection = val

    @property
    def challenge_progress(self) -> dict[str, int]:
        return self.get_required_component(ReincarnationComponent).challenge_progress

    @challenge_progress.setter
    def challenge_progress(self, val: dict[str, int]):
        self.get_required_component(ReincarnationComponent).challenge_progress = val

    @property
    def cycle_modifiers(self) -> list[dict[str, Any]]:
        return self.get_required_component(ReincarnationComponent).cycle_modifiers

    @cycle_modifiers.setter
    def cycle_modifiers(self, val: list[dict[str, Any]]):
        self.get_required_component(ReincarnationComponent).cycle_modifiers = val

    @property
    def legacy_records(self) -> list[dict[str, Any]]:
        return self.get_required_component(ReincarnationComponent).legacy_records

    @legacy_records.setter
    def legacy_records(self, val: list[dict[str, Any]]):
        self.get_required_component(ReincarnationComponent).legacy_records = val

    # -------------------------------------------------------------
    # スキルツリー・ジョブプロパティ (SkillTreeJobComponent への委譲)
    # -------------------------------------------------------------

    @property
    def skill_tree_progress(self) -> dict[str, list[str]]:
        return self.get_required_component(SkillTreeJobComponent).skill_tree_progress

    @skill_tree_progress.setter
    def skill_tree_progress(self, val: dict[str, list[str]]):
        self.get_required_component(SkillTreeJobComponent).skill_tree_progress = val

    @property
    def skill_points(self) -> int:
        return self.get_required_component(SkillTreeJobComponent).skill_points

    @skill_points.setter
    def skill_points(self, val: int):
        self.get_required_component(SkillTreeJobComponent).skill_points = val

    @property
    def total_skill_points_earned(self) -> int:
        return self.get_required_component(SkillTreeJobComponent).total_skill_points_earned

    @total_skill_points_earned.setter
    def total_skill_points_earned(self, val: int):
        self.get_required_component(SkillTreeJobComponent).total_skill_points_earned = val

    @property
    def learned_passive_skills(self) -> list[str]:
        return self.get_required_component(SkillTreeJobComponent).learned_passive_skills

    @learned_passive_skills.setter
    def learned_passive_skills(self, val: list[str]):
        self.get_required_component(SkillTreeJobComponent).learned_passive_skills = val

    passive_bonuses: dict[str, float] = field(default_factory=dict)
    passive_mp_regen: float = 0.0
    recent_skills: list[tuple[str, int]] = field(default_factory=list)

    @property
    def job(self) -> str:
        return self.get_required_component(SkillTreeJobComponent).job

    @job.setter
    def job(self, val: str):
        self.get_required_component(SkillTreeJobComponent).job = val

    @property
    def job_level(self) -> int:
        return self.get_required_component(SkillTreeJobComponent).job_level

    @job_level.setter
    def job_level(self, val: int):
        self.get_required_component(SkillTreeJobComponent).job_level = val

    @property
    def job_exp(self) -> int:
        return self.get_required_component(SkillTreeJobComponent).job_exp

    @job_exp.setter
    def job_exp(self, val: int):
        self.get_required_component(SkillTreeJobComponent).job_exp = val

    @property
    def previous_jobs(self) -> list[str]:
        return self.get_required_component(SkillTreeJobComponent).previous_jobs

    @previous_jobs.setter
    def previous_jobs(self, val: list[str]):
        self.get_required_component(SkillTreeJobComponent).previous_jobs = val

    @property
    def mastered_jobs(self) -> list[str]:
        return self.get_required_component(SkillTreeJobComponent).mastered_jobs

    @mastered_jobs.setter
    def mastered_jobs(self, val: list[str]):
        self.get_required_component(SkillTreeJobComponent).mastered_jobs = val

    @property
    def mastered_exclusive_skills(self) -> list[str]:
        return self.get_required_component(SkillTreeJobComponent).mastered_exclusive_skills

    @mastered_exclusive_skills.setter
    def mastered_exclusive_skills(self, val: list[str]):
        self.get_required_component(SkillTreeJobComponent).mastered_exclusive_skills = val

    @property
    def inherited_skills(self) -> list[str]:
        return self.get_required_component(SkillTreeJobComponent).inherited_skills

    @inherited_skills.setter
    def inherited_skills(self, val: list[str]):
        self.get_required_component(SkillTreeJobComponent).inherited_skills = val

    # -------------------------------------------------------------
    # スキル合成・進化プロパティ (SkillFusionComponent への委譲)
    # -------------------------------------------------------------
    @property
    def skill_fusion_materials(self) -> dict[str, int]:
        return self.get_required_component(SkillFusionComponent).skill_fusion_materials

    @skill_fusion_materials.setter
    def skill_fusion_materials(self, val: dict[str, int]):
        self.get_required_component(SkillFusionComponent).skill_fusion_materials = val

    @property
    def skill_evolution(self) -> dict[str, str]:
        return self.get_required_component(SkillFusionComponent).skill_evolution

    @skill_evolution.setter
    def skill_evolution(self, val: dict[str, str]):
        self.get_required_component(SkillFusionComponent).skill_evolution = val

    @property
    def awakened_skills(self) -> list[str]:
        return self.get_required_component(SkillFusionComponent).awakened_skills

    @awakened_skills.setter
    def awakened_skills(self, val: list[str]):
        self.get_required_component(SkillFusionComponent).awakened_skills = val

    @property
    def skill_traits(self) -> dict[str, dict[str, float]]:
        return self.get_required_component(SkillFusionComponent).skill_traits

    @skill_traits.setter
    def skill_traits(self, val: dict[str, dict[str, float]]):
        self.get_required_component(SkillFusionComponent).skill_traits = val

    @property
    def equipped_skills(self) -> list[str]:
        return self.get_required_component(SkillFusionComponent).equipped_skills

    @equipped_skills.setter
    def equipped_skills(self, val: list[str]):
        self.get_required_component(SkillFusionComponent).equipped_skills = val

    @property
    def inheritable_skills(self) -> list[str]:
        return self.get_required_component(SkillFusionComponent).inheritable_skills

    @inheritable_skills.setter
    def inheritable_skills(self, val: list[str]):
        self.get_required_component(SkillFusionComponent).inheritable_skills = val

    @property
    def skill_specialization(self) -> dict[str, str]:
        return self.get_required_component(SkillFusionComponent).skill_specialization

    @skill_specialization.setter
    def skill_specialization(self, val: dict[str, str]):
        self.get_required_component(SkillFusionComponent).skill_specialization = val

    @property
    def fusion_chain_progress(self) -> dict[str, int]:
        return self.get_required_component(SkillFusionComponent).fusion_chain_progress

    @fusion_chain_progress.setter
    def fusion_chain_progress(self, val: dict[str, int]):
        self.get_required_component(SkillFusionComponent).fusion_chain_progress = val

    @property
    def skill_archive_progress(self) -> dict[str, bool]:
        return self.get_required_component(SkillFusionComponent).skill_archive_progress

    @skill_archive_progress.setter
    def skill_archive_progress(self, val: dict[str, bool]):
        self.get_required_component(SkillFusionComponent).skill_archive_progress = val

    # -------------------------------------------------------------
    # ストーリーテラー・ワールドプロパティ (StorytellerComponent への委譲)
    # -------------------------------------------------------------
    @property
    def story_flags(self) -> dict[str, bool]:
        return self.get_required_component(StorytellerComponent).story_flags

    @story_flags.setter
    def story_flags(self, val: dict[str, bool]):
        self.get_required_component(StorytellerComponent).story_flags = val

    # -------------------------------------------------------------
    # プロシージャル・クエスト生成プロパティ (ProceduralQuestComponent への委譲)
    # -------------------------------------------------------------
    @property
    def procedural_quest(self) -> ProceduralQuestComponent:
        return self.get_required_component(ProceduralQuestComponent)

    @procedural_quest.setter
    def procedural_quest(self, val: ProceduralQuestComponent):
        self.components[ProceduralQuestComponent] = val

    @property
    def story_variables(self) -> dict[str, Any]:
        return self.get_required_component(StorytellerComponent).story_variables

    @story_variables.setter
    def story_variables(self, val: dict[str, Any]):
        self.get_required_component(StorytellerComponent).story_variables = val

    @property
    def story_choices_made(self) -> list[str]:
        return self.get_required_component(StorytellerComponent).story_choices_made

    @story_choices_made.setter
    def story_choices_made(self, val: list[str]):
        self.get_required_component(StorytellerComponent).story_choices_made = val

    @property
    def world_state_version(self) -> str:
        return self.get_required_component(StorytellerComponent).world_state_version

    @world_state_version.setter
    def world_state_version(self, val: str):
        self.get_required_component(StorytellerComponent).world_state_version = val

    @property
    def player_legacy(self) -> dict[str, Any]:
        return self.get_required_component(StorytellerComponent).player_legacy

    @player_legacy.setter
    def player_legacy(self, val: dict[str, Any]):
        self.get_required_component(StorytellerComponent).player_legacy = val

    @property
    def character_relationships(self) -> dict[str, dict[str, int]]:
        return self.get_required_component(StorytellerComponent).character_relationships

    @character_relationships.setter
    def character_relationships(self, val: dict[str, dict[str, int]]):
        self.get_required_component(StorytellerComponent).character_relationships = val

    @property
    def memory_fragments(self) -> list[str]:
        return self.get_required_component(StorytellerComponent).memory_fragments

    @memory_fragments.setter
    def memory_fragments(self, val: list[str]):
        self.get_required_component(StorytellerComponent).memory_fragments = val

    @property
    def active_world_events(self) -> list[str]:
        return self.get_required_component(StorytellerComponent).active_world_events

    @active_world_events.setter
    def active_world_events(self, val: list[str]):
        self.get_required_component(StorytellerComponent).active_world_events = val

    @property
    def completed_storylines(self) -> list[str]:
        return self.get_required_component(StorytellerComponent).completed_storylines

    @completed_storylines.setter
    def completed_storylines(self, val: list[str]):
        self.get_required_component(StorytellerComponent).completed_storylines = val

    @property
    def available_storylines(self) -> list[str]:
        return self.get_required_component(StorytellerComponent).available_storylines

    @available_storylines.setter
    def available_storylines(self, val: list[str]):
        self.get_required_component(StorytellerComponent).available_storylines = val

    @property
    def story_notifications(self) -> list[dict[str, Any]]:
        return self.get_required_component(StorytellerComponent).story_notifications

    @story_notifications.setter
    def story_notifications(self, val: list[dict[str, Any]]):
        self.get_required_component(StorytellerComponent).story_notifications = val

    @property
    def current_choice_prompt(self) -> dict[str, Any] | None:
        return self.get_required_component(StorytellerComponent).current_choice_prompt

    @current_choice_prompt.setter
    def current_choice_prompt(self, val: dict[str, Any] | None):
        self.get_required_component(StorytellerComponent).current_choice_prompt = val

    @property
    def ending_progress(self) -> dict[str, int]:
        return self.get_required_component(StorytellerComponent).ending_progress

    @ending_progress.setter
    def ending_progress(self, val: dict[str, int]):
        self.get_required_component(StorytellerComponent).ending_progress = val

    # 考古学・発掘・解読メタゲーム (ArchaeologyComponent への委譲, Steps 11, 24)
    @property
    def archaeology(self) -> ArchaeologyComponent:
        return self.get_required_component(ArchaeologyComponent)

    @archaeology.setter
    def archaeology(self, val: ArchaeologyComponent):
        self.components[ArchaeologyComponent] = val

    @property
    def excavated_sites(self) -> list[str]:
        return self.get_required_component(ArchaeologyComponent).excavated_sites

    @excavated_sites.setter
    def excavated_sites(self, val: list[str]):
        self.get_required_component(ArchaeologyComponent).excavated_sites = val

    @property
    def decoded_fragments(self) -> list[str]:
        return self.get_required_component(ArchaeologyComponent).decoded_fragments

    @decoded_fragments.setter
    def decoded_fragments(self, val: list[str]):
        self.get_required_component(ArchaeologyComponent).decoded_fragments = val

    @property
    def owned_keys(self) -> list[str]:
        return self.get_required_component(ArchaeologyComponent).owned_keys

    @owned_keys.setter
    def owned_keys(self, val: list[str]):
        self.get_required_component(ArchaeologyComponent).owned_keys = val

    @property
    def reached_truths(self) -> list[str]:
        return self.get_required_component(ArchaeologyComponent).reached_truths

    @reached_truths.setter
    def reached_truths(self, val: list[str]):
        self.get_required_component(ArchaeologyComponent).reached_truths = val

    @property
    def leaned_endings(self) -> dict[str, str]:
        return self.get_required_component(ArchaeologyComponent).leaned_endings

    @leaned_endings.setter
    def leaned_endings(self, val: dict[str, str]):
        self.get_required_component(ArchaeologyComponent).leaned_endings = val

    @property
    def interpretation_notes(self) -> dict[str, str]:
        return self.get_required_component(ArchaeologyComponent).interpretation_notes

    @interpretation_notes.setter
    def interpretation_notes(self, val: dict[str, str]):
        self.get_required_component(ArchaeologyComponent).interpretation_notes = val

    # -------------------------------------------------------------
    # 好感度・ペットプロフィール・エモート (コンポーネント委譲, Step 24)
    # -------------------------------------------------------------
    @property
    def affection(self) -> int:
        return self.get_required_component(AffectionComponent).affection

    @affection.setter
    def affection(self, val: int) -> None:
        self.get_required_component(AffectionComponent).affection = val

    @property
    def is_mounted(self) -> bool:
        return self.get_required_component(AffectionComponent).is_mounted

    @is_mounted.setter
    def is_mounted(self, val: bool) -> None:
        self.get_required_component(AffectionComponent).is_mounted = val

    @property
    def gene_skills(self) -> list[str]:
        return self.get_required_component(PetProfileComponent).gene_skills

    @gene_skills.setter
    def gene_skills(self, val: list[str]) -> None:
        self.get_required_component(PetProfileComponent).gene_skills = val

    @property
    def pet_type(self) -> str:
        return self.get_required_component(PetProfileComponent).pet_type

    @pet_type.setter
    def pet_type(self, val: str) -> None:
        self.get_required_component(PetProfileComponent).pet_type = val

    @property
    def pet_fusion_history(self) -> list[dict[str, Any]]:
        return self.get_required_component(PetProfileComponent).pet_fusion_history

    @pet_fusion_history.setter
    def pet_fusion_history(self, val: list[dict[str, Any]]) -> None:
        self.get_required_component(PetProfileComponent).pet_fusion_history = val

    @property
    def emote_state(self) -> str | None:
        return self.get_required_component(EmoteComponent).emote_state

    @emote_state.setter
    def emote_state(self, val: str | None) -> None:
        self.get_required_component(EmoteComponent).emote_state = val

    @property
    def emote_timer(self) -> float:
        return self.get_required_component(EmoteComponent).emote_timer

    @emote_timer.setter
    def emote_timer(self, val: float) -> None:
        self.get_required_component(EmoteComponent).emote_timer = val

    @property
    def emote_frame(self) -> int:
        return self.get_required_component(EmoteComponent).emote_frame

    @emote_frame.setter
    def emote_frame(self, val: int) -> None:
        self.get_required_component(EmoteComponent).emote_frame = val

    @property
    def pet_ai(self) -> "PetAIComponent":
        return self.get_required_component(PetAIComponent)

    def _default_ai_role(self, name: str) -> str:
        """敵の名前から陣形AIロールを自動判定 (提案4)"""
        from constants import AI_ROLE_BRUTE, AI_ROLE_FLANKER, AI_ROLE_KITER

        n = name or ""
        if any(k in n for k in ("弓", "魔", "術", "caster", "Mage", "Archer")):
            return AI_ROLE_KITER
        if any(k in n for k in ("騎", "騎士", "knight", "Knight")):
            return AI_ROLE_FLANKER
        return AI_ROLE_BRUTE

    def _init_default_skills(self) -> dict[str, Skill]:
        return {
            "martial_arts": Skill("格闘"),
            "short_sword": Skill("短剣"),
            "long_sword": Skill("長剣"),
            "evasion": Skill("回避"),
            "shield": Skill("盾"),
            "magic_cast": Skill("詠唱"),
            "healing": Skill("治癒"),
            "meditation": Skill("瞑想"),
            "faith": Skill("信仰"),  # ステップ91
            "mining": Skill("採掘"),  # ステップ103
            "fishing": Skill("釣り"),  # ステップ104
            "cooking": Skill("料理"),  # ステップ105
            "farming": Skill("栽培"),  # ステップ106
            "performance": Skill("演奏"),  # ステップ110
            "pickpocket": Skill("窃盗"),  # ステップ109
            "anatomy": Skill("解剖学"),  # ステップ111
            "negotiation": Skill("交渉"),  # ステップ138
        }

    @property
    def skills(self) -> dict[str, Skill]:
        if self._skills is None:
            self._skills = self._init_default_skills()
        return self._skills

    @skills.setter
    def skills(self, value: dict[str, Skill]) -> None:
        self._skills = value

    def calculate_max_hp(self) -> int:
        god_bonus = 10 if self.god_id == "jure" else 0
        base = (
            self.attributes.endurance * 2 + self.attributes.strength + (self.level * 5) + god_bonus
        )
        return max(10, base)

    def calculate_max_mp(self) -> int:
        god_bonus = 15 if self.god_id == "itzpalt" else 0
        base = self.attributes.magic * 2 + self.attributes.will + (self.level * 4) + god_bonus
        return max(10, base)

    def calculate_max_stamina(self) -> int:
        return max(50, self.attributes.endurance + self.attributes.will * 2)

    def recalculate_stats(self) -> None:
        # ジョブ補正適用 (Steps 48, 49)
        # ベース能力値から再計算（ベース値 + ジョブ補正）
        if self._base_attributes is not None:
            # ベース値を復元
            for attr_name, base_val in self._base_attributes.to_dict().items():
                if hasattr(self.attributes, attr_name):
                    setattr(self.attributes, attr_name, base_val)

            # Job modifiers placeholder (no-op)

        self.max_hp = self.calculate_max_hp()
        self.max_mp = self.calculate_max_mp()
        self.max_stamina = self.calculate_max_stamina()

        # パッシブスキル効果の適用 (Proposal 6)
        try:
            from skill_tree_system import get_passive_skill_manager

            mgr = get_passive_skill_manager()
            bonuses = mgr.aggregate_bonuses(self)
            self.passive_bonuses = bonuses
            if "max_hp_bonus" in bonuses:
                self.max_hp += int(bonuses["max_hp_bonus"])
                self.hp = min(self.hp, self.max_hp)
            if "mp_regen_bonus" in bonuses:
                self.passive_mp_regen = bonuses["mp_regen_bonus"]
        except Exception:
            logger.exception("ロード失敗")
        self.passive_bonuses = getattr(self, "passive_bonuses", {})

        self.hp = min(self.hp, self.max_hp)
        self.mp = min(self.mp, self.max_mp)
        self.stamina = min(self.stamina, self.max_stamina)

    def gain_exp(self, amount: int) -> list[str]:
        logs = []
        self.exp += amount
        # ジョブ経験値ボーナス (Step 52): 獲得経験値の10%を加算
        job_exp_gain = max(1, int(amount * 0.10))
        self.job_exp += job_exp_gain

        while self.exp >= self.exp_next:
            self.exp -= self.exp_next
            self.level += 1
            attr_pool = [
                "strength",
                "endurance",
                "dexterity",
                "perception",
                "learning",
                "will",
                "magic",
                "charisma",
            ]
            grown = random.sample(attr_pool, 2)
            for chosen in grown:
                setattr(self.attributes, chosen, getattr(self.attributes, chosen) + 1)
                # ベース値も更新
                if self._base_attributes is not None:
                    setattr(
                        self._base_attributes,
                        chosen,
                        getattr(self._base_attributes, chosen) + 1,
                    )

            # レベルアップ時スキルポイント付与 (Step 24)
            sp_gain = 5
            self.skill_points += sp_gain
            self.total_skill_points_earned += sp_gain

            self.recalculate_stats()
            self.hp = self.max_hp
            self.mp = self.max_mp
            logs.append(f"{self.name}はレベル {self.level} に上がった！ (HP/MP全快, +{sp_gain}SP)")
        return logs

    def gain_skill_exp(self, skill_key: str, amount: int) -> list[str]:
        logs = []
        if skill_key not in self.skills:
            return logs
        skill = self.skills[skill_key]
        growth = int(amount * (skill.potential / 100.0))
        skill.experience += max(1, growth)
        needed = skill.level * 20
        while skill.experience >= needed:
            skill.experience -= needed
            skill.level += 1
            skill.potential = max(10, skill.potential - 2)
            needed = skill.level * 20
            logs.append(f"{self.name}の【{skill.name}】が Lv{skill.level} に成長した！")
        return logs

    def pray_to_god(self) -> tuple[bool, str]:
        """神への祈り (ステップ92)"""
        if self.god_id == "eyth":
            return False, "あなたは特定の神を信仰していない。"
        if self.piety < 50:
            return False, "神はあなたの祈りにまだ耳を傾けてくれない…(信仰度が不足)"

        self.hp = self.max_hp
        self.mp = self.max_mp
        self.piety = max(0, self.piety - 30)
        god_name = GodInfo.GODS[self.god_id]["name"]
        return True, f"神【{god_name}】の御手があなたを包み込み、傷と魔力が全快した！"

    def to_dict(self) -> dict[str, Any]:
        """Entityの辞書形式シリアライズ (Step 21)"""
        data: dict[str, Any] = {
            "x": self.x,
            "y": self.y,
            "char": self.char,
            "color": list(self.color),
            "name": self.name,
            "is_player": self.is_player,
            "is_pet": self.is_pet,
            "speed": self.speed,
            "energy": self.energy,
            # 提案2/4: 一時情報なのでセーブ時は常に None/既定値
            "next_intent": None,
            "ai_role": self.ai_role,
            "preferred_range": self.preferred_range,
            "attributes": self.attributes.to_dict(),
            "level": self.level,
            "exp": self.exp,
            "exp_next": self.exp_next,
            "affection": self.affection,
            "tactic": self.tactic,
            "is_mounted": self.is_mounted,
            "gene_skills": list(self.gene_skills),
            "pet_type": self.pet_type,
            "pet_fusion_history": self.pet_fusion_history,
            "god_id": self.god_id,
            "piety": self.piety,
            "received_servant": self.received_servant,
            "received_artifact": self.received_artifact,
            "mutations": dict(self.mutations),
            "ether_disease_stages": list(self.ether_disease_stages),
            "completed_tutorials": list(self.completed_tutorials),
            "hp": self.hp,
            "max_hp": self.max_hp,
            "mp": self.mp,
            "max_mp": self.max_mp,
            "stamina": self.stamina,
            "max_stamina": self.max_stamina,
            "components": {},
        }
        # ペット性格系属性 (改善案2): PetPersonalitySystem が付与した場合のみ出力。
        # 未付与の Entity (敵など) にはキーを出さず、from_dict も触らない。
        if hasattr(self, "personality"):
            data["personality"] = self.personality
        if hasattr(self, "bond"):
            data["bond"] = self.bond
        if hasattr(self, "favorite_food_tags"):
            data["favorite_food_tags"] = list(self.favorite_food_tags)
        # コンポーネントのシリアライズ (JSONシリアライズ可能に変換: Step 21)
        for comp_type, comp in self.components.items():
            comp_name = comp_type.__name__
            # Use component's to_dict() method if available
            if hasattr(comp, "to_dict") and callable(comp.to_dict):
                data["components"][comp_name] = comp.to_dict()
            elif hasattr(comp, "__dict__"):
                comp_dict = {}
                for k, v in comp.__dict__.items():
                    if callable(v):
                        continue
                    try:
                        if isinstance(v, (set, tuple)):
                            comp_dict[k] = list(v)
                        elif isinstance(v, dict):
                            comp_dict[k] = {
                                str(dk): (list(dv) if isinstance(dv, (set, tuple)) else dv)
                                for dk, dv in v.items()
                                if not callable(dv)
                            }
                        else:
                            comp_dict[k] = v
                    except Exception:  # noqa: BLE001
                        logger.debug("Skip non-serializable component field %s.%s", comp_name, k)
                data["components"][comp_name] = comp_dict

        # スキルのシリアライズ
        if self._skills:
            data["skills"] = {
                k: {
                    "name": s.name,
                    "level": s.level,
                    "experience": s.experience,
                    "potential": s.potential,
                }
                for k, s in self._skills.items()
            }
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Entity:
        """Entityの辞書形式デシリアライズ (Step 21)"""
        attrs = Attributes.from_dict(data.get("attributes", {}))
        ent = cls(
            x=data.get("x", 0),
            y=data.get("y", 0),
            char=data.get("char", "@"),
            color=tuple(data.get("color", [255, 255, 255])),
            name=data.get("name", "Unknown"),
            is_player=data.get("is_player", False),
            is_pet=data.get("is_pet", False),
            speed=data.get("speed", 70),
            attributes=attrs,
        )
        ent.energy = data.get("energy", 0)
        # 提案2/4: 一時情報 next_intent は常に None で再開
        ent.next_intent = None
        ent.ai_role = data.get("ai_role", "brute")
        ent.preferred_range = data.get("preferred_range", 1)
        ent.level = data.get("level", 1)
        ent.exp = data.get("exp", 0)
        # exp_next は計算プロパティなので設定不要 (Step 21)
        ent.affection = data.get("affection", 50)
        ent.tactic = data.get("tactic", "assault")
        ent.is_mounted = data.get("is_mounted", False)
        ent.gene_skills = data.get("gene_skills", [])
        ent.pet_type = data.get("pet_type", "puppy")
        ent.pet_fusion_history = data.get("pet_fusion_history", [])
        ent.god_id = data.get("god_id", "eyth")
        ent.piety = data.get("piety", 0)
        ent.received_servant = data.get("received_servant", False)
        ent.received_artifact = data.get("received_artifact", False)
        ent.mutations = data.get("mutations", {})
        ent.ether_disease_stages = data.get("ether_disease_stages", [])
        ent.completed_tutorials = set(data.get("completed_tutorials", []))
        ent.hp = data.get("hp", ent.calculate_max_hp())
        ent.max_hp = data.get("max_hp", ent.calculate_max_hp())
        ent.mp = data.get("mp", ent.calculate_max_mp())
        ent.max_mp = data.get("max_mp", ent.calculate_max_mp())
        ent.stamina = data.get("stamina", ent.calculate_max_stamina())
        ent.max_stamina = data.get("max_stamina", ent.calculate_max_stamina())

        # ペット性格系属性の復元 (改善案2): キーが存在する場合のみ設定
        # (未付与 Entity の既定動作を変えない)
        if "personality" in data:
            ent.personality = data["personality"]
        if "bond" in data:
            ent.bond = data["bond"]
        if "favorite_food_tags" in data:
            ent.favorite_food_tags = list(data["favorite_food_tags"])

        # コンポーネントの復元
        comp_data_dict = data.get("components", {})
        # First, restore existing components
        for comp_type, comp in list(ent.components.items()):
            comp_name = comp_type.__name__
            if comp_name in comp_data_dict:
                comp_data = comp_data_dict[comp_name]
                # Use component's from_dict() classmethod if available
                if hasattr(comp_type, "from_dict") and callable(comp_type.from_dict):
                    new_comp = comp_type.from_dict(comp_data)
                    # Replace the component in the entity
                    ent.components[comp_type] = new_comp
                else:
                    for k, v in comp_data.items():
                        setattr(comp, k, v)

        # Then, create any components that were serialized but don't exist in the default entity
        for comp_name, comp_data in comp_data_dict.items():
            # Check if this component type is already handled
            already_handled = any(comp_type.__name__ == comp_name for comp_type in ent.components)
            if not already_handled:
                # Try to find the component class by name
                # We need to import the components module
                try:
                    from ecs.components import components as components_module
                    comp_type = getattr(components_module, comp_name, None)
                    if comp_type and hasattr(comp_type, "from_dict") and callable(comp_type.from_dict):
                        new_comp = comp_type.from_dict(comp_data)
                        ent.components[comp_type] = new_comp
                except (ImportError, AttributeError):
                    pass  # Component type not found, skip

        # スキルの復元
        if "skills" in data and ent._skills is not None:
            for sk_key, sk_dict in data["skills"].items():
                if sk_key in ent._skills:
                    ent._skills[sk_key].level = sk_dict.get("level", 1)
                    ent._skills[sk_key].experience = sk_dict.get("experience", 0)
                    ent._skills[sk_key].potential = sk_dict.get("potential", 100)

        return ent

    # -------------------------------------------------------------
    # 状態異常プロパティ・メソッド (PR #8 integration: origin/main より移植, Step 54)
    # -------------------------------------------------------------
    @property
    def status_effects(self):
        """ECS API 使用時は StatusEffectsComponent、レガシーコードはリストを返す。"""
        if getattr(self, "_status_effects_ecs", False):
            return self.get_required_component(StatusEffectsComponent)
        return self._status_effects_list

    @status_effects.setter
    def status_effects(self, value) -> None:
        if getattr(self, "_status_effects_ecs", False):
            # ECS モード: レガシー call site のリセット操作 ([] 代入) をクリアに変換
            if isinstance(value, list) and not value:
                self.get_required_component(StatusEffectsComponent).clear_all()
            return
        self._status_effects_list = value

    def has_status(self, effect_type: str) -> bool:
        self._status_effects_ecs = True
        return self.get_required_component(StatusEffectsComponent).has_effect(effect_type)

    def add_status(
        self,
        effect_type: str,
        duration: int,
        power: int = 1,
        source_name: str = "",
    ) -> bool:
        self._status_effects_ecs = True
        return self.get_required_component(StatusEffectsComponent).add_effect(
            effect_type, duration, power, source_name
        )

    def remove_status(self, effect_type: str) -> bool:
        self._status_effects_ecs = True
        return self.get_required_component(StatusEffectsComponent).remove_effect(effect_type)

    def clear_statuses(self) -> None:
        self._status_effects_ecs = True
        self.get_required_component(StatusEffectsComponent).clear_all()

    # -------------------------------------------------------------
    # 属性耐性計算 (PR #8 integration: origin/main より移植, Step 53, 56)
    # -------------------------------------------------------------
    def get_elemental_resistance(self, element: str) -> int:
        """基礎耐性 + 装備エンチャント耐性の合算"""
        base = self.base_resistances.get(element, 0)
        equip_res = 0
        inventory = getattr(self, "inventory", None)
        get_res = getattr(inventory, "get_elemental_resistances", None) if inventory else None
        if callable(get_res):
            equip_res = get_res().get(element, 0)
        return base + equip_res

    def is_weak_to(self, element: str) -> bool:
        """指定属性が弱点かどうか判定"""
        return element in self.weaknesses
