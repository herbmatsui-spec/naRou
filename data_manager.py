"""
Elona Masterpiece Edition - DataManager System (Data-Driven Architecture v2)
Centralized loading, caching, schema validation, and repository pattern for all game data.
"""

from __future__ import annotations

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

import random
from typing import TYPE_CHECKING, Any

import yaml

from constants import (
    QUALITY_BAD,
    QUALITY_GOD,
    QUALITY_GOOD,
    QUALITY_MIRACLE,
    QUALITY_NORMAL,
)
from core_framework import BaseSystem
from data.generated.character.gods import God
from data.generated.character.jobs import Job
from data.generated.dungeon.dungeon import DungeonThemeDefinition
from data.generated.faction.factions import Faction

# 生成されたPydanticモデル（スキーマバリデーション用）
from data.generated.item.item import ItemDefinition
from data.generated.meta.achievements import Achievement
from data.generated.meta.titles import Title
from data.generated.monster.monster import MonsterDefinition
from data.generated.quest.quest import QuestDefinition
from data.generated.skill.skill_fusion import SkillFusion
from data.generated.skill.skill_trees import SkillTree
from data.generated.skill.spells import Spell
from data.generated.social.guilds import Guild

# リポジトリ層
from data.repositories import (
    AchievementRepository,
    DungeonThemeRepository,
    FactionRepository,
    GodRepository,
    GuildRepository,
    ItemRepository,
    JobRepository,
    MonsterRepository,
    QuestRepository,
    SkillFusionRepository,
    SkillRepository,
    SkillTreeRepository,
    SpellRepository,
    TitleRepository,
)
from entity import Attributes, Entity
from item_system import (
    MATERIALS,
    Item,
    create_sample_item,
)
from systems import MonsterPreset

if TYPE_CHECKING:
    from game import Engine


class DataManager(BaseSystem):
    """リポジトリパターン・スキーマバリデーション対応データマネージャ"""

    def __init__(self, data_dir: str = "data", schemas_dir: str = "data/schemas"):
        super().__init__()
        self.data_dir = Path(data_dir)
        self.schemas_dir = Path(schemas_dir)

        # リポジトリ
        self.items: ItemRepository
        self.monsters: MonsterRepository
        self.skills: SkillRepository
        self.skill_trees: SkillTreeRepository
        self.spells: SpellRepository
        self.skill_fusions: SkillFusionRepository
        self.quests: QuestRepository
        self.factions: FactionRepository
        self.achievements: AchievementRepository
        self.titles: TitleRepository
        self.jobs: JobRepository
        self.gods: GodRepository
        self.dungeon_themes: DungeonThemeRepository
        self.guilds: GuildRepository

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

        # モンスター (フラット辞書)
        monsters_raw = self._load_yaml("monsters.yaml") or {}
        self.monsters = MonsterRepository(
            {k: MonsterDefinition.model_validate(v) for k, v in monsters_raw.items()}
        )

        # スキル (スタンドアロン skills.yaml は未定義のため空リポジトリ)
        self.skills = SkillRepository({})

        # スキルツリー (ラッパー key: skill_trees)
        skill_trees_raw = self._load_yaml("skill_trees.yaml") or {}
        st_data = (
            skill_trees_raw.get("skill_trees", {})
            if isinstance(skill_trees_raw, dict)
            else {}
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

        # スキル融合 (ラッパー key: fusions)
        fusion_raw = self._load_yaml("skill_fusion.yaml") or {}
        fu_data = fusion_raw.get("fusions", {}) if isinstance(fusion_raw, dict) else {}
        self.skill_fusions = SkillFusionRepository(
            {
                k: (
                    SkillFusion.model_validate(v)
                    if not isinstance(v, SkillFusion)
                    else v
                )
                for k, v in fu_data.items()
            }
        )

        # クエスト (ラッパー key: main_quests, リスト形式)
        # main_quests.yaml はスキーマと構造が異なるため tolerant ロード
        self.quests = QuestRepository(self._build_quests_tolerant())

        # 派閥 (ラッパー key: factions)
        factions_raw = self._load_yaml("factions.yaml") or {}
        fac_data = (
            factions_raw.get("factions", {}) if isinstance(factions_raw, dict) else {}
        )
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
                k: (
                    Achievement.model_validate(v)
                    if not isinstance(v, Achievement)
                    else v
                )
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
        self.dungeon_themes = DungeonThemeRepository(
            self._build_dungeon_themes_tolerant()
        )

        # ギルド (ラッパー key: guilds)
        guilds_raw = self._load_yaml("guilds.yaml") or {}
        gui_data = guilds_raw.get("guilds", {}) if isinstance(guilds_raw, dict) else {}
        self.guilds = GuildRepository(
            {
                k: (Guild.model_validate(v) if not isinstance(v, Guild) else v)
                for k, v in gui_data.items()
            }
        )

        # ローカライゼーション読み込み
        self._load_localization()

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

    def validate_all(self) -> None:
        """全リポジトリの整合性チェック (参照整合性等は将来拡張)"""

    def _load_yaml(self, filename: str) -> dict[str, Any]:
        path = self.data_dir / filename
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

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

    def get_random_item_for_floor(
        self, floor_level: int, x: int = 0, y: int = 0
    ) -> Item:
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
        return self.create_item(
            item_id, x, y, material=mat, quality=quality, cursed=cursed
        )

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
        mob.skills = [getattr(s, "root", s) for s in (data.skills or [])]
        mob.status_effects = []
        return mob

    def get_random_monster_for_floor(
        self, floor_level: int, x: int = 0, y: int = 0
    ) -> Entity:
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
            tier_pool = list(self.monsters._data.keys())

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

        return errors

    def get_localization(self, locale: str) -> dict[str, str]:
        return self.localization.get(locale, {})


# --- LocalizationManager integration (i18n, Step 3.x) ---
def localize(key: str, language: str = None, manager=None) -> str:
    """Return localized text for *key* using LocalizationManager."""
    from localization_manager import LocalizationManager

    mgr = manager or LocalizationManager()
    return mgr.get_text(key, language)
