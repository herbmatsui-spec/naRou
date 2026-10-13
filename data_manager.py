"""
Elona Masterpiece Edition - DataManager System (Data-Driven Architecture v2)
Centralized loading, caching, schema validation, and repository pattern for all game data.
"""

from __future__ import annotations

import functools
import sys
from pathlib import Path

_root_dir = Path(__file__).resolve().parent
if str(_root_dir) not in sys.path:
    sys.path.insert(0, str(_root_dir))

# Pydantic等の外部ライブラリが見つからない場合のスタブフォールバック
try:
    import pydantic
except ImportError:
    stubs_dir = _root_dir / "stubs"
    if str(stubs_dir) not in sys.path:
        sys.path.insert(0, str(stubs_dir))

import logging
import random
from typing import TYPE_CHECKING, Any

import yaml

# Module-level YAML cache (shared across all DataManager instances)
_YAML_CACHE: dict[str, dict[str, Any]] = {}


def _cached_load_yaml(path: Path) -> dict[str, Any]:
    """Cached YAML loading - module-level cache shared across instances."""
    path_str = str(path)
    if path_str in _YAML_CACHE:
        return _YAML_CACHE[path_str]
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    _YAML_CACHE[path_str] = data
    return data


def clear_yaml_cache() -> None:
    """Clear the global YAML load cache (for testing)."""
    _YAML_CACHE.clear()

from constants import QUALITY_BAD, QUALITY_GOD, QUALITY_GOOD, QUALITY_MIRACLE, QUALITY_NORMAL
from core_framework import BaseSystem
from data.generated.character.gods import God
from data.generated.character.jobs import Job
from data.generated.dungeon.dungeon import DungeonThemeDefinition
from data.generated.faction.factions import Faction

# 生成されたPydanticモデル（スキーマバリデーション用）
from data.generated.item.enchantment import EnchantmentDefinition
from data.generated.item.item import ItemDefinition
from data.generated.item.recipe import RecipeDefinition
from data.generated.meta.achievements import Achievement
from data.generated.meta.titles import Title
from data.generated.monster.monster import MonsterAbility, MonsterDefinition
from data.generated.quest.quest import QuestDefinition
from data.generated.skill.skill import Effect, SkillCategory, SkillDefinition
from data.generated.skill.skill_fusion import SkillFusion
from data.generated.skill.skill_trees import SkillTree
from data.generated.skill.spells import Spell
from data.generated.social.guilds import Guild

# リポジトリ層
from data.repositories import (
    AchievementRepository,
    DungeonThemeRepository,
    EnchantmentRepository,
    FactionRepository,
    GodRepository,
    GuildRepository,
    ItemRepository,
    JobRepository,
    MonsterRepository,
    QuestRepository,
    RecipeRepository,
    SkillFusionRepository,
    SkillRepository,
    SkillTreeRepository,
    SpellRepository,
    TitleRepository,
)
from ecs.entity import Attributes, Entity
from item_system import MATERIALS, Item, create_sample_item
from systems import MonsterPreset

if TYPE_CHECKING:
    from game import Engine

logger = logging.getLogger(__name__)

# world スキルの tier (文字列) を SkillDefinition の tier (技能木上の段位) に読み替えるための順位表
_SKILL_TIER_RANK = {"Common": 0, "Rare": 1, "Unique": 2, "Concept": 3, "Eater": 4}


class DataManager(BaseSystem):
    """リポジトリパターン・スキーマバリデーション対応データマネージャ"""

    def __init__(self, data_dir: str = "data", schemas_dir: str = "data/schemas"):
        super().__init__()
        self.data_dir = Path(data_dir)
        self.schemas_dir = Path(schemas_dir)

        # リポジトリ
        self.items: ItemRepository
        self.recipes: RecipeRepository  # PR#8 統合 (origin/main 同様のクラフトレシピ)
        self.monsters: MonsterRepository
        self.skills: SkillRepository
        self.skill_trees: SkillTreeRepository
        self.spells: SpellRepository
        self.skill_fusions: SkillFusionRepository
        self.monster_abilities: dict[str, Any]  # MonsterAbility dict
        self.quests: QuestRepository
        self.factions: FactionRepository
        self.achievements: AchievementRepository
        self.titles: TitleRepository
        self.jobs: JobRepository
        self.gods: GodRepository
        self.dungeon_themes: DungeonThemeRepository
        self.guilds: GuildRepository
        self.enchantments: EnchantmentRepository

        # ローカライゼーション
        self.localization: dict[str, dict[str, str]] = {}

        # 素材データ
        self.materials_data: dict[str, Any] = dict(MATERIALS)

        # 起動時に全データをロード (リポジトリ構築)
        self.load_all()

    def initialize(self, engine: Engine) -> None:
        """全データロード + スキーマバリデーション + リポジトリ構築"""
        self.load_all()
        self.validate_all()

    def load_all(self) -> None:
        """全データロード + スキーマバリデーション + リポジトリ構築"""
        # アイテム (フラット辞書)
        items_raw = self._load_yaml("items.yaml") or {}
        self.items = ItemRepository(
            {k: ItemDefinition.model_validate(v) for k, v in items_raw.items()}
        )

        # クラフトレシピ (フラット辞書) (PR#8 統合: origin/main と同様のロード)
        recipes_raw = self._load_yaml("recipes.yaml") or {}
        self.recipes = RecipeRepository(
            {k: RecipeDefinition.model_validate(v) for k, v in recipes_raw.items()}
        )

        # エンチャント (フラット辞書)
        enchantments_raw = self._load_yaml("item_enchantments.yaml") or {}
        self.enchantments = EnchantmentRepository(
            {k: EnchantmentDefinition.model_validate(v) for k, v in enchantments_raw.items()}
        )

        # モンスター (フラット辞書)
        monsters_raw = self._load_yaml("monsters.yaml") or {}
        # モデル再構築 (forward refs 解決用) - pytest 経由の import では module level で失敗するためここで実行
        if hasattr(MonsterDefinition, "model_rebuild"):
            MonsterDefinition.model_rebuild()
        self.monsters = MonsterRepository(
            {k: MonsterDefinition.model_validate(v) for k, v in monsters_raw.items()}
        )

        # スキル (ワールドのスキルカタログと职业技能。記法が異なるため tolerant ロード)
        self.skills = SkillRepository(self._build_skills_tolerant())

        # スキルツリー (ラッパー key: skill_trees)
        skill_trees_raw = self._load_yaml("skill_trees.yaml") or {}
        st_data = (
            skill_trees_raw.get("skill_trees", {}) if isinstance(skill_trees_raw, dict) else {}
        )
        self.skill_trees = SkillTreeRepository(
            {
                k: (SkillTree.model_validate(v) if not isinstance(v, SkillTree) else v)
                for k, v in st_data.items()
            }
        )

        # 呪文 (フラット辞書, RootModel)
        spells_raw = self._load_yaml("spells.yaml") or {}
        self.spells = SpellRepository(
            {
                k: (Spell.model_validate(v) if not isinstance(v, Spell) else v)
                for k, v in spells_raw.items()
            }
        )

        # モンスター能力 (Phase 2 Step 46-47)
        abilities_raw = self._load_yaml("monster_abilities.yaml") or {}
        self.monster_abilities = {
            k: MonsterAbility.model_validate({**v, "id": k}) for k, v in abilities_raw.items()
        }

        # クエスト (ラッパー key: main_quests, リスト形式)
        # main_quests.yaml はスキーマと構造が異なるため tolerant ロード
        self.quests = QuestRepository(self._build_quests_tolerant())

        # 派閥 (ラッパー key: factions)
        factions_raw = self._load_yaml("factions.yaml") or {}
        fac_data = factions_raw.get("factions", {}) if isinstance(factions_raw, dict) else {}
        self.factions = FactionRepository(
            {
                k: (Faction.model_validate(v) if not isinstance(v, Faction) else v)
                for k, v in fac_data.items()
            }
        )

        # 実績 (ラッパー key: achievements)
        ach_raw = self._load_yaml("achievements.yaml") or {}
        ach_data = ach_raw.get("achievements", {}) if isinstance(ach_raw, dict) else {}
        self.achievements = AchievementRepository(
            {
                k: (Achievement.model_validate(v) if not isinstance(v, Achievement) else v)
                for k, v in ach_data.items()
            }
        )

        # 称号 (ラッパー key: titles)
        titles_raw = self._load_yaml("titles.yaml") or {}
        ti_data = titles_raw.get("titles", {}) if isinstance(titles_raw, dict) else {}
        self.titles = TitleRepository(
            {
                k: (Title.model_validate(v) if not isinstance(v, Title) else v)
                for k, v in ti_data.items()
            }
        )

        # 職業 (ラッパー key: jobs)
        jobs_raw = self._load_yaml("jobs.yaml") or {}
        job_data = jobs_raw.get("jobs", {}) if isinstance(jobs_raw, dict) else {}
        self.jobs = JobRepository(
            {
                k: (Job.model_validate(v) if not isinstance(v, Job) else v)
                for k, v in job_data.items()
            }
        )

        # 神 (フラット辞書, RootModel)
        gods_raw = self._load_yaml("gods.yaml") or {}
        self.gods = GodRepository(
            {
                k: (God.model_validate(v) if not isinstance(v, God) else v)
                for k, v in gods_raw.items()
            }
        )

        # ダンジョンテーマ (ラッパー key: dungeon_themes)
        # dungeon_themes.yaml はスキーマと構造が異なるため tolerant ロード
        self.dungeon_themes = DungeonThemeRepository(self._build_dungeon_themes_tolerant())

        # ギルド (ラッパー key: guilds)
        guilds_raw = self._load_yaml("guilds.yaml") or {}
        gui_data = guilds_raw.get("guilds", {}) if isinstance(guilds_raw, dict) else {}
        self.guilds = GuildRepository(
            {
                k: (Guild.model_validate(v) if not isinstance(v, Guild) else v)
                for k, v in gui_data.items()
            }
        )

        # スキル融合 (ラッパー key: fusions)
        skill_fusion_raw = self._load_yaml("skill_fusion.yaml") or {}
        sf_data = skill_fusion_raw.get("fusions", {}) if isinstance(skill_fusion_raw, dict) else {}
        self.skill_fusions = SkillFusionRepository(
            {
                k: (SkillFusion.model_validate(v) if not isinstance(v, SkillFusion) else v)
                for k, v in sf_data.items()
            }
        )

        # ローカライゼーション読み込み
        self._load_localization()

        # モンスターが参照する未知のスキル id は握り潰さずログに出す
        for error in self._unresolved_monster_skills():
            logger.warning("%s", error)

    def _build_quests_tolerant(self) -> dict[str, QuestDefinition]:
        """main_quests.yaml は QuestDefinition スキーマと構造が異なるため、
        スキーマを迂回してモデルを構築する (必須フィールドは既定値で補完)。"""
        raw = self._load_yaml("main_quests.yaml") or {}
        entries = raw.get("main_quests") or []
        out: dict[str, QuestDefinition] = {}
        for q in entries:
            qid = q.get("quest_id") or q.get("id")
            if not qid:
                continue
            out[qid] = QuestDefinition.model_construct(
                id=qid,
                title=q.get("title", ""),
                description=q.get("description"),
                type=None,
                objectives=[],
                rewards=[],
                prerequisites=[],
                repeatable=False,
                tags=[],
            )
        return out

    def _build_dungeon_themes_tolerant(self) -> dict[str, DungeonThemeDefinition]:
        """dungeon_themes.yaml は DungeonThemeDefinition スキーマと構造が異なるため、
        スキーマを迂回してモデルを構築する。"""
        raw = self._load_yaml("dungeon_themes.yaml") or {}
        entries = raw.get("dungeon_themes") or {}
        out: dict[str, DungeonThemeDefinition] = {}
        for tid, t in entries.items():
            if not isinstance(t, dict):
                continue
            out[tid] = DungeonThemeDefinition.model_construct(
                id=tid,
                name=t.get("name", ""),
                description=None,
                theme=t.get("base_layout", ""),
                min_level=None,
                max_level=None,
            )
        return out

    def _build_skills_tolerant(self) -> dict[str, SkillDefinition]:
        """スキル定義は `data/worlds/skill_eater/skills.yaml` と `data/exclusive_skills.yaml` に
        あり、どちらも SkillDefinition スキーマとは記法・id 規約が異なる。
        スキーマを迂回してモデルを構築する (world のカタログを先に読み、id が重複しないもののみ追加)。"""
        entries: list[tuple[str, dict[str, Any]]] = []
        world_raw = self._load_yaml("worlds/skill_eater/skills.yaml") or {}
        entries.extend(
            (str(e["id"]), e)
            for e in (world_raw.get("skills") or [])
            if isinstance(e, dict) and e.get("id")
        )

        # exclusive_skills.yaml は id を辞書キーに持つため、キーを id として読む
        exclusive_raw = self._load_yaml("exclusive_skills.yaml") or {}
        entries.extend(
            (str(skill_id), e)
            for skill_id, e in (exclusive_raw.get("exclusive_skills") or {}).items()
            if isinstance(e, dict)
        )

        out: dict[str, SkillDefinition] = {}
        for skill_id, entry in entries:
            out.setdefault(skill_id, self._build_skill_tolerant(skill_id, entry))
        return out

    @staticmethod
    def _build_skill_tolerant(skill_id: str, entry: dict[str, Any]) -> SkillDefinition:
        """1 件のスキル定義を SkillDefinition に写す。

        world の tier は文字列、スキーマの tier はスキル木上の整数段位なので順位に読み替える。
        cost (技能ポイント) はスキーマの必須だが、奪取は技能ポイントを経由しないため最低値 1 に固定する。
        """
        tags = {str(t).lower() for t in entry.get("tags") or []}
        category = SkillCategory.combat
        for tag, mapped in (
            ("magic", SkillCategory.magic),
            ("labor", SkillCategory.craft),
            ("craft", SkillCategory.craft),
            ("social", SkillCategory.social),
            ("economy", SkillCategory.social),
        ):
            if tag in tags:
                category = mapped
                break

        effects = [
            Effect.model_construct(
                type=eff.get("type", "Unknown"),
                value=eff.get("value", 0.0),
                target=eff.get("target", "self"),
                condition=eff.get("condition"),
                duration=eff.get("duration", 0),
            )
            for eff in entry.get("effects") or []
            if isinstance(eff, dict)
        ]

        return SkillDefinition.model_construct(
            id=skill_id,
            name=entry.get("name", skill_id),
            description=entry.get("flavor_text") or entry.get("description"),
            category=category,
            icon=entry.get("icon"),
            cost=1,
            prerequisites=[],
            effects=effects,
            tree_id=None,
            tier=_SKILL_TIER_RANK.get(str(entry.get("tier", "Common")), 0),
            max_level=1,
            cooldown=int(entry.get("cooldown", 0) or 0),
            mp_cost=int(entry.get("mp_cost", 0) or 0),
            range=1,
            target_type=None,
        )

    def _unresolved_monster_skills(self) -> list[str]:
        """`data/monsters.yaml` が参照するスキルのうち SkillRepository で解決しないものを列挙する。"""
        return [
            f"Monster '{m_id}' references unknown skill '{skill_id}'"
            for m_id, monster in self.monsters._data.items()
            for skill_id in (getattr(s, "root", s) for s in (monster.skills or []))
            if self.skills.get(str(skill_id)) is None
        ]

    def validate_all(self) -> None:
        """全リポジトリの整合性チェック (参照整合性等は将来拡張)"""

    def _load_yaml(self, filename: str) -> dict[str, Any]:
        path = self.data_dir / filename
        if not path.exists():
            return {}
        return _cached_load_yaml(path)

    def clear_cache(self) -> None:
        """Clear the YAML load cache (for testing)."""
        clear_yaml_cache()

    def _load_localization(self) -> None:
        text_dir = self.data_dir / "text"
        if not text_dir.exists():
            return
        for locale_file in text_dir.glob("*.yaml"):
            locale = locale_file.stem
            with open(locale_file, encoding="utf-8") as f:
                self.localization[locale] = yaml.safe_load(f) or {}

    def get_text(self, key: str, locale: str = "ja") -> str:
        return self.localization.get(locale, {}).get(key, key)

    def _color_tuple(self, color) -> tuple:
        if not color:
            return (255, 255, 255)
        return tuple(int(getattr(c, "root", c)) for c in color)

    # ==================== ITEM GENERATION ====================

    def create_item(
        self,
        item_id: str,
        x: int = 0,
        y: int = 0,
        material: str | None = None,
        quality: str = QUALITY_NORMAL,
        cursed: bool = False,
        count: int = 1,
        identified: bool = True,
    ) -> Item:
        """YAMLデータ定義からItemインスタンスを生成"""
        data = self.items.get(item_id)
        if not data:
            return create_sample_item(item_id, x, y)

        mat_choice = material or data.material

        # 品質によるボーナス計算
        hit_bonus = int(data.hit_bonus)
        dmg_bonus = int(data.dmg_bonus)
        pv = int(data.pv)
        dv = int(data.dv)

        if quality == QUALITY_GOOD:
            hit_bonus += random.randint(1, 3)
            dmg_bonus += random.randint(1, 2)
            pv += 1
        elif quality == QUALITY_MIRACLE:
            hit_bonus += random.randint(3, 7)
            dmg_bonus += random.randint(2, 5)
            pv += random.randint(2, 4)
            dv += random.randint(1, 3)
        elif quality == QUALITY_GOD:
            hit_bonus += random.randint(8, 15)
            dmg_bonus += random.randint(6, 12)
            pv += random.randint(5, 10)
            dv += random.randint(4, 8)
        elif quality == QUALITY_BAD:
            hit_bonus = max(0, hit_bonus - 2)
            dmg_bonus = max(0, dmg_bonus - 1)

        item = Item(
            name=data.name,
            category=data.category,
            char=data.char or "*",
            color=self._color_tuple(data.color),
            x=x,
            y=y,
            base_weight=float(data.base_weight),
            base_value=int(data.base_value),
            count=count,
            material=mat_choice,
            quality=quality,
            identified=identified,
            dice_num=int(data.dice_num),
            dice_side=int(data.dice_side),
            hit_bonus=hit_bonus,
            dmg_bonus=dmg_bonus,
            pv=pv,
            dv=dv,
            heal_amount=int(data.heal_amount),
            nutrition=int(data.nutrition),
            spell_id=data.spell_id or "",
            sp_stock=int(data.sp_stock),
            cursed=cursed,
        )
        return item

    def get_random_item_for_floor(self, floor_level: int, x: int = 0, y: int = 0) -> Item:
        """フロア深度に応じたアイテムの動的ランダム生成"""
        if not self.items._data:
            return create_sample_item("potion_heal", x, y)

        candidates = list(self.items._data.keys())
        item_id = random.choice(candidates)

        # 品質抽選 (深い階層ほど奇跡・神器の確率アップ)
        r = random.random()
        god_prob = min(0.05, 0.005 * floor_level)
        miracle_prob = min(0.18, 0.02 * floor_level)
        good_prob = min(0.35, 0.08 * floor_level)

        if r < god_prob:
            quality = QUALITY_GOD
        elif r < god_prob + miracle_prob:
            quality = QUALITY_MIRACLE
        elif r < god_prob + miracle_prob + good_prob:
            quality = QUALITY_GOOD
        elif r > 0.92:
            quality = QUALITY_BAD
        else:
            quality = QUALITY_NORMAL

        materials = list(MATERIALS.keys())
        mat = (
            random.choice(materials)
            if quality in (QUALITY_GOOD, QUALITY_MIRACLE, QUALITY_GOD)
            else None
        )
        cursed = (quality == QUALITY_BAD) or (random.random() < 0.05)
        item = self.create_item(item_id, x, y, material=mat, quality=quality, cursed=cursed)
        # Step 58.1: 接尾辞ロール (品質連動: GOD必ず2個 / NORMAL 0.3 / BAD禁止)
        try:
            from item_system import roll_affixes

            roll_affixes(item, quality=quality)
        except Exception:
            pass  # 接尾辞システム不在でも生成を止めない
        return item

    # ==================== MONSTER GENERATION ====================

    def create_monster(
        self,
        monster_id: str,
        x: int = 0,
        y: int = 0,
        level_scale: int = 1,
        faction: str = "monster",
    ) -> Entity:
        """YAMLデータ定義からMonster Entityインスタンスを生成"""
        data = self.monsters.get(monster_id)
        if not data:
            return MonsterPreset.create(monster_id, x, y)

        attrs_data = data.attributes or {}
        scale_mult = 1.0 + (level_scale - 1) * 0.15

        scaled_attrs = Attributes(
            strength=int(attrs_data.get("strength", 10) * scale_mult),
            endurance=int(attrs_data.get("endurance", 10) * scale_mult),
            dexterity=int(attrs_data.get("dexterity", 10) * scale_mult),
            perception=int(attrs_data.get("perception", 10) * scale_mult),
            learning=int(attrs_data.get("learning", 8) * scale_mult),
            will=int(attrs_data.get("will", 8) * scale_mult),
            magic=int(attrs_data.get("magic", 8) * scale_mult),
            charisma=int(attrs_data.get("charisma", 8) * scale_mult),
        )

        base_hp = int(data.max_hp * scale_mult)
        base_speed = int(data.speed)

        mob = Entity(
            x=x,
            y=y,
            char=data.char or "M",
            color=self._color_tuple(data.color),
            name=data.name,
            speed=base_speed,
            attributes=scaled_attrs,
            is_player=False,
            is_pet=False,
        )
        mob.max_hp = base_hp
        mob.hp = base_hp
        mob.faction = faction
        mob.ai_type = data.ai_type if data.ai_type else "aggressive"
        if data.ai_role:
            from constants import AI_ROLE_KITER, KITER_PREFERRED_RANGE

            mob.ai_role = data.ai_role
            mob.preferred_range = (
                KITER_PREFERRED_RANGE if data.ai_role == AI_ROLE_KITER else 1
            )
        mob.abilities = [
            self.monster_abilities.get(getattr(s, "root", getattr(s, "id", s)))
            for s in (data.abilities or data.skills or [])
            if self.monster_abilities.get(getattr(s, "root", getattr(s, "id", s)))
        ]
        # Step 51: 属性耐性をデータ定義から Entity へ流し込む
        res_data = data.resistances or {}
        if res_data:
            from systems import ResistanceSet

            res_set = ResistanceSet()
            res_set.fire = int(res_data.get("fire", 0))
            res_set.cold = int(res_data.get("cold", 0))
            res_set.lightning = int(res_data.get("lightning", 0))
            res_set.darkness = int(res_data.get("darkness", 0))
            res_set.chaos = int(res_data.get("chaos", 0))
            res_set.magic = int(res_data.get("magic", 0))
            mob.resistances = res_set
        # 後方互換: skills も設定
        mob.skills = [getattr(s, "root", s) for s in (data.skills or [])]
        mob.status_effects = []
        return mob

    def get_random_monster_for_floor(self, floor_level: int, x: int = 0, y: int = 0) -> Entity:
        """フロア深度に応じたモンスターの動的ランダム生成"""
        if not self.monsters._data:
            return MonsterPreset.create("slime", x, y)

        # 階層に応じたモンスター候補のフィルタ
        tier_pool = []
        for m_id, m_val in self.monsters._data.items():
            min_floor = m_val.min_floor or 1
            max_floor = m_val.max_floor or 999
            if min_floor <= floor_level <= max_floor + 3:
                tier_pool.append(m_id)

        if not tier_pool:
            # Fallback: pick closest 3 monsters by depth distance (Step 24)
            candidates = []
            for m_id, m_val in self.monsters._data.items():
                min_floor = m_val.min_floor or 1
                max_floor = m_val.max_floor or 999
                # Calculate distance from requested floor
                if floor_level < min_floor:
                    dist = min_floor - floor_level
                elif floor_level > max_floor:
                    dist = floor_level - max_floor
                else:
                    dist = 0
                candidates.append((dist, m_id))
            candidates.sort(key=lambda x: x[0])
            tier_pool = [m_id for _, m_id in candidates[:3]]

        chosen_id = random.choice(tier_pool)
        return self.create_monster(chosen_id, x, y, level_scale=floor_level)

    def validate_all_data(self) -> list[str]:
        """全データの整合性バリデーション (スキーマチェック)"""
        errors = []
        # アイテムチェック
        for i_id, i_val in self.items._data.items():
            if not i_val.name:
                errors.append(f"Item '{i_id}' missing 'name'")
            if not i_val.category:
                errors.append(f"Item '{i_id}' missing 'category'")

        # モンスターチェック
        for m_id, m_val in self.monsters._data.items():
            if not m_val.name:
                errors.append(f"Monster '{m_id}' missing 'name'")
            if m_val.max_hp <= 0:
                errors.append(f"Monster '{m_id}' missing 'max_hp'")

        # モンスターが参照するスキル id の解決チェック
        errors.extend(self._unresolved_monster_skills())

        return errors

    def get_localization(self, locale: str) -> dict[str, str]:
        return self.localization.get(locale, {})


# --- LocalizationManager integration (i18n, Step 3.x) ---
from localization_manager import localize  # noqa: E402,F401
