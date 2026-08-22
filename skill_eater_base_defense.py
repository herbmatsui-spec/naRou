"""
Skill Eater Phase 2: Base Defense System (Steps 55-61 + Extended)
ミダス商会の警戒度上昇に伴う拠点防衛戦（タワーディフェンス）、トラップ配置、拠点耐久値管理。
防衛施設: AutoTurret, BarrierGenerator, SensorArray, DecoyTerminal
襲撃フェーズ: WARNING(30s) → BREACH(戦闘) → AFTERMATH(修理・資源回収)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_economy_system import SkillEaterEconomySystem
from skill_eater_presentation_system import SkillEaterPresentationSystem
from skill_eater_system import CharacterState, SkillEaterRegistry


class RaidPhase(str, Enum):
    """襲撃フェーズ"""

    NORMAL = "Normal"
    WARNING = "Warning"
    BREACH = "Breach"
    AFTERMATH = "Aftermath"


class RaidTriggerType(str, Enum):
    """襲撃トリガータイプ"""

    HEAT_LEVEL = "HeatLevel"
    ELAPSED_TURNS = "ElapsedTurns"
    META_QUEST = "MetaQuest"


class DefenseFacilityType(str, Enum):
    """防衛施設タイプ"""

    AUTO_TURRET = "AutoTurret"
    BARRIER_GENERATOR = "BarrierGenerator"
    SENSOR_ARRAY = "SensorArray"
    DECOY_TERMINAL = "DecoyTerminal"


class EnemyType(str, Enum):
    """敵タイプ"""

    MIDAS_SECURITY = "MidasSecurity"
    MIDAS_ELITE = "MidasElite"
    MIDAS_MECH = "MidasMech"
    MIDAS_HACKER = "MidasHacker"


# 音響・エモート定数
ALARM_KLAXON = "alarm_klaxon.ogg"
TURRET_FIRE = "turret_fire.ogg"
BARRIER_HUM = "barrier_hum.ogg"
EXPLOSION_DEBRIS = "explosion_debris.ogg"
EMOTE_SHIELD = "emote_shield.png"
EMOTE_WRENCH = "emote_wrench.png"
EMOTE_ALERT = "emote_alert.png"
EMOTE_CROSS = "emote_cross.png"
EMOTE_STARS = "emote_stars.png"
EMOTE_EXCLAMATIONS = "emote_exclamations.png"
METAL_LATCH = "metalLatch.ogg"
METAL_CLICK = "metalClick.ogg"
METAL_POT1 = "metalPot1.ogg"
CHOP = "chop.ogg"
DOOR_CLOSE_1 = "doorClose_1.ogg"
DOOR_OPEN_2 = "doorOpen_2.ogg"
HANDLE_COINS = "handleCoins.ogg"
HANDLE_COINS2 = "handleCoins2.ogg"
FANFARE = "fanfare.ogg"


# フェーズ継続時間（ターン数）
WARNING_DURATION = 30
BREACH_DURATION = 120
AFTERMATH_DURATION = 10


@dataclass
class DefenseFacility:
    """防衛施設データ"""

    id: str
    name: str
    facility_type: DefenseFacilityType
    level: int = 1
    max_level: int = 5
    tier_required: int = 1
    build_cost_aldo: int = 5000
    build_cost_junk: int = 200
    upgrade_cost_aldo: int = 5000
    upgrade_cost_junk: int = 200
    base_hp: int = 300
    current_hp: int = 300
    base_damage: int = 50
    base_range: int = 5
    base_cooldown: int = 2
    effect_description: str = ""
    special_ability: str = ""
    is_built: bool = False

    @property
    def max_hp(self) -> int:
        return int(self.base_hp * (1.2 ** (self.level - 1)))

    @property
    def damage(self) -> int:
        return int(self.base_damage * (1.2 ** (self.level - 1)))

    @property
    def range(self) -> int:
        return self.base_range + (self.level - 1)

    @property
    def cooldown(self) -> int:
        return max(1, self.base_cooldown - (self.level - 1) // 2)

    @property
    def is_operational(self) -> bool:
        return self.is_built and self.level > 0 and self.current_hp > 0

    @property
    def efficiency(self) -> float:
        if not self.is_operational:
            return 0.0
        if self.current_hp < self.max_hp * 0.5:
            return 0.5
        return 1.0

    def take_damage(self, amount: int) -> dict[str, Any]:
        """ダメージを受ける"""
        old_hp = self.current_hp
        self.current_hp = max(0, self.current_hp - amount)
        destroyed = old_hp > 0 and self.current_hp <= 0
        if destroyed:
            self.level = max(1, self.level - 1)
        return {
            "facility_id": self.id,
            "damage_amount": amount,
            "hp_before": old_hp,
            "hp_after": self.current_hp,
            "is_destroyed": destroyed,
            "level_after": self.level,
        }

    def repair(self, amount: int) -> dict[str, Any]:
        """修理する"""
        old_hp = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return {
            "facility_id": self.id,
            "repaired_amount": self.current_hp - old_hp,
            "hp_before": old_hp,
            "hp_after": self.current_hp,
        }

    def upgrade(self) -> bool:
        """アップグレード"""
        if self.level >= self.max_level:
            return False
        self.level += 1
        self.current_hp = self.max_hp
        self.upgrade_cost_aldo = int(self.upgrade_cost_aldo * 1.5)
        self.upgrade_cost_junk = int(self.upgrade_cost_junk * 1.5)
        return True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DefenseFacility:
        facility_type = DefenseFacilityType(data.get("facility_type", "AutoTurret"))
        return cls(
            id=data["id"],
            name=data["name"],
            facility_type=facility_type,
            level=data.get("level", 1),
            max_level=data.get("max_level", 5),
            tier_required=data.get("tier_required", 1),
            build_cost_aldo=data.get("build_cost_aldo", 5000),
            build_cost_junk=data.get("build_cost_junk", 200),
            upgrade_cost_aldo=data.get("upgrade_cost_aldo", 5000),
            upgrade_cost_junk=data.get("upgrade_cost_junk", 200),
            base_hp=data.get("base_hp", 300),
            current_hp=data.get("current_hp", 300),
            base_damage=data.get("base_damage", 50),
            base_range=data.get("base_range", 5),
            base_cooldown=data.get("base_cooldown", 2),
            effect_description=data.get("effect_description", ""),
            special_ability=data.get("special_ability", ""),
            is_built=data.get("is_built", False),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "facility_type": self.facility_type.value,
            "level": self.level,
            "max_level": self.max_level,
            "tier_required": self.tier_required,
            "build_cost_aldo": self.build_cost_aldo,
            "build_cost_junk": self.build_cost_junk,
            "upgrade_cost_aldo": self.upgrade_cost_aldo,
            "upgrade_cost_junk": self.upgrade_cost_junk,
            "base_hp": self.base_hp,
            "current_hp": self.current_hp,
            "base_damage": self.base_damage,
            "base_range": self.base_range,
            "base_cooldown": self.base_cooldown,
            "effect_description": self.effect_description,
            "special_ability": self.special_ability,
            "is_built": self.is_built,
        }


@dataclass
class RaidTrigger:
    """襲撃トリガー"""

    trigger_type: RaidTriggerType
    threshold: int
    current_value: int = 0
    is_active: bool = False

    def check(self) -> bool:
        return self.current_value >= self.threshold

    def update(self, value: int) -> None:
        self.current_value = value
        self.is_active = self.check()


@dataclass
class DamageReport:
    """被害報告"""

    facility_id: str
    damage_amount: int
    hp_before: int
    hp_after: int
    is_destroyed: bool
    junk_looted: int = 0
    subordinate_injured: bool = False


@dataclass
class RaidEnemy:
    """襲撃敵"""

    id: str
    name: str
    enemy_type: EnemyType
    hp: int
    max_hp: int
    atk: int
    defense: int
    speed: int
    target_priority: list[str] = field(default_factory=list)
    is_dead: bool = False

    def take_damage(self, amount: int) -> bool:
        self.hp = max(0, self.hp - amount)
        if self.hp <= 0:
            self.is_dead = True
        return self.is_dead


@dataclass
class Subordinate:
    """従属者"""

    id: str
    name: str
    hp: int
    max_hp: int
    skills: list[str] = field(default_factory=list)
    is_incapacitated: bool = False
    incapacitated_turns: int = 0

    def take_damage(self, amount: int) -> bool:
        self.hp = max(0, self.hp - amount)
        if self.hp <= 0:
            self.is_incapacitated = True
            self.incapacitated_turns = 5
        return self.is_incapacitated

    def heal(self, amount: int) -> None:
        self.hp = min(self.max_hp, self.hp + amount)
        if self.hp > 0 and self.is_incapacitated:
            self.is_incapacitated = False
            self.incapacitated_turns = 0


class BaseDefenseManager:
    """
    レジスタンス拠点防衛戦マネージャー
    """

    DEFAULT_FACILITIES = [
        {
            "id": "auto_turret",
            "name": "自動砲台",
            "facility_type": "AutoTurret",
            "tier_required": 1,
            "build_cost_aldo": 5000,
            "build_cost_junk": 200,
            "upgrade_cost_aldo": 5000,
            "upgrade_cost_junk": 200,
            "base_hp": 300,
            "base_damage": 50,
            "base_range": 5,
            "base_cooldown": 2,
            "effect_description": "範囲内の敵を自動攻撃する",
            "special_ability": "Lv3+: 貫通ショット（防御50%無視）",
        },
        {
            "id": "barrier_generator",
            "name": "バリア発生装置",
            "facility_type": "BarrierGenerator",
            "tier_required": 2,
            "build_cost_aldo": 8000,
            "build_cost_junk": 300,
            "upgrade_cost_aldo": 8000,
            "upgrade_cost_junk": 300,
            "base_hp": 500,
            "base_damage": 0,
            "base_range": 0,
            "base_cooldown": 10,
            "effect_description": "全施設にシールドを付与する",
            "special_ability": "Lv3+: 受けたダメージの25%を反射",
        },
        {
            "id": "sensor_array",
            "name": "センサーアレイ",
            "facility_type": "SensorArray",
            "tier_required": 2,
            "build_cost_aldo": 6000,
            "build_cost_junk": 250,
            "upgrade_cost_aldo": 6000,
            "upgrade_cost_junk": 250,
            "base_hp": 200,
            "base_damage": 0,
            "base_range": 10,
            "base_cooldown": 1,
            "effect_description": "敵の位置を探知し、命中率を低下させる",
            "special_ability": "Lv3+: 次ターンの敵標的を予測",
        },
        {
            "id": "decoy_terminal",
            "name": "デコイ端末",
            "facility_type": "DecoyTerminal",
            "tier_required": 3,
            "build_cost_aldo": 10000,
            "build_cost_junk": 400,
            "upgrade_cost_aldo": 10000,
            "upgrade_cost_junk": 400,
            "base_hp": 300,
            "base_damage": 0,
            "base_range": 0,
            "base_cooldown": 15,
            "effect_description": "敵の注意を引くデコイを展開する",
            "special_ability": "Lv3+: 破壊時に範囲爆発",
        },
    ]

    def __init__(
        self,
        base_max_hp: int = 1000,
        registry: SkillEaterRegistry | None = None,
        economy: SkillEaterEconomySystem | None = None,
        audio: SkillEaterAudioSystem | None = None,
        presentation: SkillEaterPresentationSystem | None = None,
    ):
        self.registry = registry or SkillEaterRegistry.get_instance()
        self.economy = economy or SkillEaterEconomySystem()
        self.audio = audio or SkillEaterAudioSystem.get_instance()
        self.presentation = presentation or SkillEaterPresentationSystem.get_instance()

        if audio and not presentation:
            self.presentation.audio_system = audio

        # 基本ステータス
        self.base_max_hp = base_max_hp
        self.base_hp = base_max_hp
        self.heat_level = 0

        # 防衛施設
        self.defense_facilities: dict[str, DefenseFacility] = {}
        self._init_default_facilities()

        # ストレージ・従属者
        self.storage_junk: int = 0
        self.storage_aldo: int = 0
        self.storage_capacity_junk: int = 5000
        self.subordinates: list[Subordinate] = []

        # 襲撃状態
        self.current_phase: RaidPhase = RaidPhase.NORMAL
        self.phase_timer: int = 0
        self.active_raid: bool = False
        self.warning_issued: bool = False
        self.raid_enemies: list[RaidEnemy] = []
        self.current_wave: int = 1
        self.max_waves: int = 3

        # トリガー設定
        self.triggers: list[RaidTrigger] = [
            RaidTrigger(RaidTriggerType.HEAT_LEVEL, 80),
            RaidTrigger(RaidTriggerType.ELAPSED_TURNS, 50),
            RaidTrigger(RaidTriggerType.META_QUEST, 1),
        ]
        self.turns_since_last_raid: int = 0
        self.meta_quest_raid_flag: bool = False

        # 戦闘ログ
        self.combat_log: list[str] = []
        self.raid_history: list[dict[str, Any]] = []

        # 施設クールダウン管理
        self.facility_cooldowns: dict[str, int] = {}

        # シナジー効果
        self._update_synergy_bonuses()

    def _init_default_facilities(self) -> None:
        """デフォルト施設の初期化"""
        for fac_data in self.DEFAULT_FACILITIES:
            facility = DefenseFacility.from_dict(fac_data)
            self.defense_facilities[facility.id] = facility

    def _update_synergy_bonuses(self) -> None:
        """シナジー効果の更新"""
        built_facilities = {f.id for f in self.defense_facilities.values() if f.is_built}

        self.has_turret_sensor = (
            "auto_turret" in built_facilities and "sensor_array" in built_facilities
        )
        self.has_barrier_decoy = (
            "barrier_generator" in built_facilities and "decoy_terminal" in built_facilities
        )
        self.has_all_four = len(built_facilities) >= 4

    # ============================================================
    # Steps 11-18: Facility Construction & Upgrades
    # ============================================================

    def can_build_facility(self, facility_id: str) -> tuple[bool, str]:
        """施設建設可能かチェック"""
        facility = self.defense_facilities.get(facility_id)
        if not facility:
            return False, "存在しない施設です。"

        if facility.is_built:
            return False, "既に建設済みです。"

        # ティアチェック（経済システムの施設レベルで代用）
        hq_level = self.economy.base_facilities.get("hq_vault", None)
        current_tier = hq_level.level if hq_level else 1
        if current_tier < facility.tier_required:
            return (
                False,
                f"ティア{facility.tier_required}以上が必要です（現在: ティア{current_tier}）。",
            )

        # リソースチェック
        if self.economy.aldo_currency < facility.build_cost_aldo:
            return (
                False,
                f"アルドが不足しています（必要: {facility.build_cost_aldo}, 所持: {self.economy.aldo_currency}）。",
            )

        if self.storage_junk < facility.build_cost_junk:
            return (
                False,
                f"ジャンクが不足しています（必要: {facility.build_cost_junk}, 所持: {self.storage_junk}）。",
            )

        return True, "建設可能です。"

    def build_facility(self, facility_id: str) -> tuple[bool, str]:
        """施設を建設"""
        can_build, reason = self.can_build_facility(facility_id)
        if not can_build:
            self._play_fail_sound()
            return False, reason

        facility = self.defense_facilities[facility_id]

        # リソース消費
        self.economy.aldo_currency -= facility.build_cost_aldo
        self.storage_junk -= facility.build_cost_junk

        # 建設完了
        facility.is_built = True
        facility.current_hp = facility.max_hp
        facility.level = 1

        self._update_synergy_bonuses()

        # 演出
        self.presentation.add_event(
            emote_file=EMOTE_STARS, audio_file=CHOP, message=f"【施設建設】{facility.name} が完成！"
        )
        self.audio.play_sound(METAL_POT1)

        return True, f"{facility.name} を建設しました！"

    def upgrade_facility(self, facility_id: str) -> tuple[bool, str]:
        """施設をアップグレード"""
        facility = self.defense_facilities.get(facility_id)
        if not facility:
            return False, "存在しない施設です。"

        if not facility.is_built:
            return False, "未建設の施設です。"

        if facility.level >= facility.max_level:
            return False, "既に最大レベルです。"

        if self.economy.aldo_currency < facility.upgrade_cost_aldo:
            self._play_fail_sound()
            return False, f"アルド不足（必要: {facility.upgrade_cost_aldo}）。"

        if self.storage_junk < facility.upgrade_cost_junk:
            self._play_fail_sound()
            return False, f"ジャンク不足（必要: {facility.upgrade_cost_junk}）。"

        # 消費・アップグレード
        self.economy.aldo_currency -= facility.upgrade_cost_aldo
        self.storage_junk -= facility.upgrade_cost_junk
        facility.upgrade()

        self.presentation.add_event(
            emote_file=EMOTE_STARS,
            audio_file=CHOP,
            message=f"【施設強化】{facility.name} が Lv.{facility.level} に昇格！",
        )
        self.audio.play_sound(METAL_POT1)

        return True, f"{facility.name} が Lv.{facility.level} に強化されました！"

    def repair_facility(self, facility_id: str, junk_amount: int | None = None) -> tuple[bool, str]:
        """施設を修理"""
        facility = self.defense_facilities.get(facility_id)
        if not facility or not facility.is_built:
            return False, "修理対象が見つかりません。"

        if facility.current_hp >= facility.max_hp:
            return False, "修理の必要はありません。"

        # 必要ジャンク計算
        hp_needed = facility.max_hp - facility.current_hp
        junk_needed = hp_needed * 2
        if junk_amount is not None:
            junk_needed = min(junk_needed, junk_amount)

        if self.storage_junk < junk_needed:
            return False, f"ジャンク不足（必要: {junk_needed}, 所持: {self.storage_junk}）。"

        self.storage_junk -= junk_needed
        result = facility.repair(junk_needed // 2)  # 2ジャンク=1HP

        self.presentation.add_event(
            emote_file=EMOTE_WRENCH,
            audio_file=METAL_POT1,
            message=f"【修理完了】{facility.name} HP: {result['hp_after']}/{facility.max_hp}",
        )

        return (
            True,
            f"{facility.name} を修理しました（HP: {result['hp_after']}/{facility.max_hp}）。",
        )

    def get_facility_status(self) -> dict[str, Any]:
        """全施設のステータス取得"""
        return {
            fid: {
                "id": f.id,
                "name": f.name,
                "type": f.facility_type.value,
                "level": f.level,
                "max_level": f.max_level,
                "hp": f.current_hp,
                "max_hp": f.max_hp,
                "damage": f.damage,
                "range": f.range,
                "cooldown": f.cooldown,
                "is_built": f.is_built,
                "is_operational": f.is_operational,
                "efficiency": f.efficiency,
                "effect": f.effect_description,
                "special": f.special_ability,
                "upgrade_cost_aldo": f.upgrade_cost_aldo,
                "upgrade_cost_junk": f.upgrade_cost_junk,
            }
            for fid, f in self.defense_facilities.items()
        }

    def _play_fail_sound(self) -> None:
        """失敗音再生"""
        self.presentation.add_event(emote_file=EMOTE_CROSS, audio_file=METAL_CLICK, message="失敗")

    # ============================================================
    # Steps 19-26: Raid Trigger System
    # ============================================================

    def increase_heat(self, amount: int) -> dict[str, Any]:
        """警戒度上昇（経済システムから呼ばれる）"""
        old_heat = self.heat_level
        self.heat_level = min(100, self.heat_level + amount)

        # 警戒度に応じた警告演出
        if old_heat < 50 <= self.heat_level:
            self.presentation.add_event(
                emote_file=EMOTE_EXCLAMATIONS,
                audio_file=METAL_CLICK,
                message=f"警戒度上昇: {self.heat_level}%",
            )
        elif old_heat < 70 <= self.heat_level:
            self.presentation.add_event(
                emote_file=EMOTE_ALERT,
                audio_file=ALARM_KLAXON,
                message=f"【危険】警戒度: {self.heat_level}% - 襲撃の可能性大",
            )
        elif old_heat < 90 <= self.heat_level:
            self.presentation.add_event(
                emote_file=EMOTE_ALERT,
                audio_file=ALARM_KLAXON,
                message=f"【切迫】警戒度: {self.heat_level}% - 襲撃差し迫る！",
            )

        # トリガー更新
        self.triggers[0].update(self.heat_level)

        return {"current_heat": self.heat_level, "raid_imminent": self.heat_level >= 80}

    def check_raid_triggers(self) -> tuple[bool, RaidTrigger | None]:
        """襲撃トリガーチェック"""
        # ターン経過トリガー更新
        self.triggers[1].update(self.turns_since_last_raid)

        # メタクエストトリガー更新
        self.triggers[2].update(1 if self.meta_quest_raid_flag else 0)

        # 熱度トリガー更新
        self.triggers[0].update(self.heat_level)

        for trigger in self.triggers:
            if trigger.check():
                return True, trigger

        return False, None

    def start_raid_warning_phase(self, trigger: RaidTrigger) -> dict[str, Any]:
        """WARNINGフェーズ開始"""
        self.current_phase = RaidPhase.WARNING
        self.phase_timer = WARNING_DURATION
        self.active_raid = True
        self.warning_issued = True
        self.current_wave = 1

        # 敵生成
        self.raid_enemies = self._generate_raid_enemies()

        # 警報演出
        self.presentation.add_event(
            emote_file=EMOTE_ALERT,
            audio_file=ALARM_KLAXON,
            message="【緊急警報！】ミダス部隊が接近中！ 防衛準備を！",
            duration_ms=5000,
        )

        return {
            "phase": "WARNING",
            "timer": self.phase_timer,
            "trigger": trigger.trigger_type.value,
            "enemies": len(self.raid_enemies),
            "enemy_types": [e.enemy_type.value for e in self.raid_enemies],
            "message": "襲撃警報発令！ 30ターン後に戦闘開始！",
        }

    def _generate_raid_enemies(self) -> list[RaidEnemy]:
        """襲撃敵生成"""
        base_count = 3 + (self.heat_level // 20)
        built_count = sum(1 for f in self.defense_facilities.values() if f.is_built)
        enemy_count = max(3, base_count - built_count // 2)

        enemies = []
        enemy_pool = [
            (EnemyType.MIDAS_SECURITY, 80, 20, 5, 10),
            (EnemyType.MIDAS_ELITE, 150, 35, 10, 8),
            (EnemyType.MIDAS_MECH, 300, 50, 15, 5),
            (EnemyType.MIDAS_HACKER, 100, 25, 5, 15),
        ]

        heat_multiplier = 1.0 + (self.heat_level / 100) * 0.5

        for i in range(enemy_count):
            # 熱度に応じて強い敵が出やすく
            weights = [40, 30, 20, 10]
            if self.heat_level > 50:
                weights = [20, 30, 30, 20]
            if self.heat_level > 80:
                weights = [10, 20, 40, 30]

            import random

            enemy_type = random.choices([e[0] for e in enemy_pool], weights=weights)[0]
            base_stats = next(e for e in enemy_pool if e[0] == enemy_type)

            hp = int(base_stats[1] * heat_multiplier)
            atk = int(base_stats[2] * heat_multiplier)
            defense = int(base_stats[3] * heat_multiplier)
            speed = base_stats[4]

            # 標的優先度
            priority = [
                "storage",
                "barrier_generator",
                "auto_turret",
                "sensor_array",
                "decoy_terminal",
                "base",
            ]

            enemy = RaidEnemy(
                id=f"enemy_{i}",
                name=f"{enemy_type.value}_{i}",
                enemy_type=enemy_type,
                hp=hp,
                max_hp=hp,
                atk=atk,
                defense=defense,
                speed=speed,
                target_priority=priority,
            )
            enemies.append(enemy)

        return enemies

    def process_warning_phase(self) -> dict[str, Any]:
        """WARNINGフェーズ処理"""
        if self.current_phase != RaidPhase.WARNING:
            return {"error": "Not in WARNING phase"}

        self.phase_timer -= 1

        # センサーアレイ効果: 敵命中率低下
        sensor = self.defense_facilities.get("sensor_array")
        accuracy_debuff = 0
        if sensor and sensor.is_operational:
            accuracy_debuff = sensor.level * 10

        # 定期的にアラーム音
        if self.phase_timer % 10 == 0:
            self.audio.play_sound(ALARM_KLAXON)

        if self.phase_timer <= 0:
            return self.start_breach_phase()

        return {
            "phase": "WARNING",
            "timer": self.phase_timer,
            "accuracy_debuff": accuracy_debuff,
            "enemies_approaching": len(self.raid_enemies),
        }

    def start_breach_phase(self) -> dict[str, Any]:
        """BREACHフェーズ開始"""
        self.current_phase = RaidPhase.BREACH
        self.phase_timer = BREACH_DURATION

        # 施設クールダウンリセット
        self.facility_cooldowns = {fid: 0 for fid in self.defense_facilities}

        # 戦闘開始演出
        self.presentation.add_event(
            emote_file=EMOTE_SHIELD,
            audio_file=TURRET_FIRE,
            message="【襲撃開始！】敵部隊が拠点に侵攻！",
            duration_ms=3000,
        )

        return {
            "phase": "BREACH",
            "timer": self.phase_timer,
            "wave": self.current_wave,
            "enemies": len([e for e in self.raid_enemies if not e.is_dead]),
            "message": "戦闘フェーズ突入！",
        }

    def process_breach_phase(self) -> dict[str, Any]:
        """BREACHフェーズ処理（1ターン分）"""
        if self.current_phase != RaidPhase.BREACH:
            return {"error": "Not in BREACH phase"}

        # 施設攻撃
        facility_results = self._facility_attack_enemies()

        # 敵攻撃
        enemy_results = self._enemy_attack_facilities()

        # ターン経過
        self.phase_timer -= 1
        for fid in self.facility_cooldowns:
            if self.facility_cooldowns[fid] > 0:
                self.facility_cooldowns[fid] -= 1

        # 勝敗判定
        alive_enemies = [e for e in self.raid_enemies if not e.is_dead]

        if not alive_enemies:
            # ウェーブクリア
            if self.current_wave < self.max_waves:
                self.current_wave += 1
                self.raid_enemies = self._generate_raid_enemies()
                return {
                    "phase": "BREACH",
                    "result": "WAVE_CLEARED",
                    "next_wave": self.current_wave,
                    "timer": self.phase_timer,
                    "facility_results": facility_results,
                    "enemy_results": enemy_results,
                }
            else:
                # 全ウェーブ撃退
                return self.start_aftermath_phase(victory=True)

        if self.phase_timer <= 0:
            # 時間切れ = 敵の勝利
            return self.start_aftermath_phase(victory=False)

        return {
            "phase": "BREACH",
            "timer": self.phase_timer,
            "wave": self.current_wave,
            "enemies_remaining": len(alive_enemies),
            "facility_results": facility_results,
            "enemy_results": enemy_results,
        }

    def _facility_attack_enemies(self) -> list[dict[str, Any]]:
        """施設から敵への攻撃"""
        results = []
        alive_enemies = [e for e in self.raid_enemies if not e.is_dead]
        if not alive_enemies:
            return results

        # オートタレット
        turret = self.defense_facilities.get("auto_turret")
        if turret and turret.is_operational and self.facility_cooldowns.get("auto_turret", 0) <= 0:
            target = min(alive_enemies, key=lambda e: e.speed)  # 最速を狙う
            damage = int(turret.damage * turret.efficiency)
            if self.has_turret_sensor:
                damage = int(damage * 1.2)
            target.take_damage(damage)
            self.facility_cooldowns["auto_turret"] = turret.cooldown

            self.audio.play_sound(TURRET_FIRE)
            results.append(
                {
                    "facility": "auto_turret",
                    "target": target.id,
                    "damage": damage,
                    "target_hp": target.hp,
                    "killed": target.is_dead,
                }
            )

        # バリア発生装置
        barrier = self.defense_facilities.get("barrier_generator")
        if (
            barrier
            and barrier.is_operational
            and self.facility_cooldowns.get("barrier_generator", 0) <= 0
        ):
            shield_amount = barrier.level * 100
            for fac in self.defense_facilities.values():
                if fac.is_operational and fac.id != "barrier_generator":
                    # 一時シールドとして扱う（簡易実装: HP上限超過分をバリアとして記録）
                    pass
            # デコイにもシールド
            if self.has_barrier_decoy:
                decoy = self.defense_facilities.get("decoy_terminal")
                if decoy and decoy.is_operational:
                    pass  # デコイHP増加処理は別途

            self.facility_cooldowns["barrier_generator"] = barrier.cooldown
            self.audio.play_sound(BARRIER_HUM)
            self.presentation.add_event(
                emote_file=EMOTE_SHIELD,
                audio_file=BARRIER_HUM,
                message=f"バリア展開！ シールド値: {shield_amount}",
            )

            results.append(
                {
                    "facility": "barrier_generator",
                    "effect": "barrier",
                    "shield_amount": shield_amount,
                }
            )

        # センサーアレイ（パッシブ効果は process_warning_phase で処理）
        sensor = self.defense_facilities.get("sensor_array")
        if sensor and sensor.is_operational:
            results.append(
                {
                    "facility": "sensor_array",
                    "effect": "detection",
                    "accuracy_debuff": sensor.level * 10,
                    "predict_target": sensor.level >= 3,
                }
            )

        # デコイ端末
        decoy = self.defense_facilities.get("decoy_terminal")
        if decoy and decoy.is_operational and self.facility_cooldowns.get("decoy_terminal", 0) <= 0:
            # デコイ展開（敵のターゲットをデコイに誘導）
            self.facility_cooldowns["decoy_terminal"] = decoy.cooldown
            results.append(
                {
                    "facility": "decoy_terminal",
                    "effect": "decoy_deployed",
                    "decoy_hp": decoy.level * 300,
                    "explodes_on_death": decoy.level >= 3,
                }
            )

        return results

    def _enemy_attack_facilities(self) -> list[dict[str, Any]]:
        """敵から施設への攻撃"""
        results = []
        alive_enemies = [e for e in self.raid_enemies if not e.is_dead]
        operational_facilities = [f for f in self.defense_facilities.values() if f.is_operational]

        for enemy in alive_enemies:
            # ターゲット選択
            target = None
            for priority in enemy.target_priority:
                if priority == "storage":
                    target = "storage"
                    break
                elif priority == "base":
                    target = "base"
                    break
                else:
                    fac = self.defense_facilities.get(priority)
                    if fac and fac.is_operational:
                        target = priority
                        break

            if not target:
                target = "base"

            # 攻撃実行
            if target == "storage":
                looted = min(self.storage_junk // 10, enemy.atk * 2)
                self.storage_junk = max(0, self.storage_junk - looted)
                self.storage_aldo = max(
                    0, self.storage_aldo - min(self.storage_aldo // 20, enemy.atk)
                )
                results.append(
                    {
                        "attacker": enemy.id,
                        "target": "storage",
                        "junk_looted": looted,
                        "aldo_looted": min(self.storage_aldo // 20, enemy.atk),
                    }
                )
                self.audio.play_sound(EXPLOSION_DEBRIS)

            elif target == "base":
                damage = max(1, enemy.atk - 10)  # 基地防御10
                self.base_hp = max(0, self.base_hp - damage)
                results.append(
                    {
                        "attacker": enemy.id,
                        "target": "base",
                        "damage": damage,
                        "base_hp": self.base_hp,
                    }
                )
                self.audio.play_sound(EXPLOSION_DEBRIS)
                if self.base_hp <= 0:
                    self.presentation.add_event(
                        emote_file=EMOTE_CROSS,
                        audio_file=EXPLOSION_DEBRIS,
                        message="【拠点陥落】ベースが破壊された！",
                    )

            else:
                facility = self.defense_facilities[target]
                # センサーアレイの命中デバフ
                accuracy = 1.0
                sensor = self.defense_facilities.get("sensor_array")
                if sensor and sensor.is_operational:
                    accuracy -= sensor.level * 0.1
                accuracy = max(0.3, accuracy)

                import random

                if random.random() < accuracy:
                    damage = max(1, enemy.atk - facility.level * 5)
                    dmg_result = facility.take_damage(damage)
                    results.append({"attacker": enemy.id, "target": target, **dmg_result})

                    if dmg_result["is_destroyed"]:
                        self.presentation.add_event(
                            emote_file=EMOTE_CROSS,
                            audio_file=EXPLOSION_DEBRIS,
                            message=f"{facility.name} が破壊された！",
                        )
                        # ジャンク略奪
                        looted = facility.level * 50
                        self.storage_junk = max(0, self.storage_junk - looted)
                        results[-1]["junk_looted"] = looted
                    else:
                        self.audio.play_sound(EXPLOSION_DEBRIS)
                else:
                    results.append({"attacker": enemy.id, "target": target, "missed": True})

        return results

    # ============================================================
    # Steps 27-34: Aftermath & Recovery
    # ============================================================

    def start_aftermath_phase(self, victory: bool) -> dict[str, Any]:
        """AFTERMATHフェーズ開始"""
        self.current_phase = RaidPhase.AFTERMATH
        self.phase_timer = AFTERMATH_DURATION
        self.active_raid = False

        # 被害計算
        damage_reports = self._calculate_aftermath_damage()
        subordinate_injuries = self._apply_subordinate_injuries(damage_reports)

        # 報酬/ペナルティ
        if victory:
            reward_aldo = self.current_wave * 500
            reward_junk = self.current_wave * 100
            self.economy.aldo_currency += reward_aldo
            self.storage_junk += reward_junk
            self.economy.factions["resistance"].reputation = min(
                100, self.economy.factions["resistance"].reputation + 10
            )
            self.heat_level = max(0, self.heat_level - 30)

            self.presentation.add_event(
                emote_file=EMOTE_STARS,
                audio_file=FANFARE,
                message=f"【防衛成功】撃退報酬: {reward_aldo}アルド, {reward_junk}ジャンク",
            )
        else:
            # 敗北ペナルティ
            self.storage_junk = self.storage_junk // 2
            self.storage_aldo = self.storage_aldo // 2
            for fac in self.defense_facilities.values():
                if fac.is_built:
                    fac.level = max(1, fac.level - 1)
            self.heat_level = max(0, self.heat_level - 10)

            self.presentation.add_event(
                emote_file=EMOTE_CROSS,
                audio_file=EXPLOSION_DEBRIS,
                message="【防衛失敗】拠点が深刻な被害を受けた...",
            )

        # 履歴記録
        self.raid_history.append(
            {
                "turn": self.turns_since_last_raid,
                "trigger": self._get_last_trigger_type(),
                "victory": victory,
                "waves_cleared": self.current_wave - 1 if not victory else self.max_waves,
                "base_hp": self.base_hp,
                "facilities_destroyed": sum(
                    1
                    for f in self.defense_facilities.values()
                    if f.is_built and f.level == 1 and f.current_hp < f.max_hp
                ),
                "junk_lost": sum(r.junk_looted for r in damage_reports),
                "subordinates_injured": subordinate_injuries,
                "rewards": {"aldo": reward_aldo, "junk": reward_junk} if victory else {},
            }
        )
        if len(self.raid_history) > 20:
            self.raid_history = self.raid_history[-20:]

        self.turns_since_last_raid = 0
        self.meta_quest_raid_flag = False

        return {
            "phase": "AFTERMATH",
            "timer": self.phase_timer,
            "victory": victory,
            "damage_reports": [r.__dict__ for r in damage_reports],
            "subordinates_injured": subordinate_injuries,
            "base_hp": self.base_hp,
            "message": "戦闘終了。修理と回収を開始。",
        }

    def _calculate_aftermath_damage(self) -> list[DamageReport]:
        """被害計算"""
        reports = []
        for fac in self.defense_facilities.values():
            if fac.is_built and fac.current_hp < fac.max_hp:
                junk_looted = fac.level * 50 if fac.current_hp == 0 else 0
                reports.append(
                    DamageReport(
                        facility_id=fac.id,
                        damage_amount=fac.max_hp - fac.current_hp,
                        hp_before=fac.max_hp,
                        hp_after=fac.current_hp,
                        is_destroyed=(fac.current_hp == 0),
                        junk_looted=junk_looted,
                    )
                )
        return reports

    def _apply_subordinate_injuries(self, damage_reports: list[DamageReport]) -> int:
        """従属者負傷適用"""
        if not self.subordinates:
            return 0

        destroyed_count = sum(1 for r in damage_reports if r.is_destroyed)
        if destroyed_count == 0:
            return 0

        injured = 0
        for sub in self.subordinates:
            if sub.is_incapacitated:
                continue
            import random

            if random.random() < 0.2 * destroyed_count:
                dmg = int(sub.max_hp * 0.2)
                sub.take_damage(dmg)
                injured += 1
                self.presentation.add_event(
                    emote_file=EMOTE_CROSS, audio_file=METAL_CLICK, message=f"{sub.name} が負傷！"
                )
        return injured

    def process_aftermath_phase(self) -> dict[str, Any]:
        """AFTERMATHフェーズ処理"""
        if self.current_phase != RaidPhase.AFTERMATH:
            return {"error": "Not in AFTERMATH phase"}

        self.phase_timer -= 1

        # 自動修理（優先度: バリア > タレット > センサー > デコイ）
        repair_priority = ["barrier_generator", "auto_turret", "sensor_array", "decoy_terminal"]
        for fid in repair_priority:
            fac = self.defense_facilities.get(fid)
            if fac and fac.is_built and fac.current_hp < fac.max_hp:
                repair_cost = (fac.max_hp - fac.current_hp) * 2
                if self.storage_junk >= repair_cost:
                    self.storage_junk -= repair_cost
                    fac.repair(fac.max_hp - fac.current_hp)
                    self.presentation.add_event(
                        emote_file=EMOTE_WRENCH,
                        audio_file=METAL_POT1,
                        message=f"自動修理: {fac.name} 完全復旧",
                    )
                break  # 1ターン1施設のみ

        # 従属者回復
        for sub in self.subordinates:
            if sub.is_incapacitated:
                sub.incapacitated_turns -= 1
                if sub.incapacitated_turns <= 0:
                    sub.heal(sub.max_hp // 2)
            elif sub.hp < sub.max_hp:
                sub.heal(int(sub.max_hp * 0.1))

        if self.phase_timer <= 0:
            return self._return_to_normal()

        return {
            "phase": "AFTERMATH",
            "timer": self.phase_timer,
            "base_hp": self.base_hp,
            "storage_junk": self.storage_junk,
        }

    def _return_to_normal(self) -> dict[str, Any]:
        """通常状態に戻る"""
        self.current_phase = RaidPhase.NORMAL
        self.warning_issued = False
        self.raid_enemies.clear()
        self.facility_cooldowns.clear()

        return {
            "phase": "NORMAL",
            "message": "平常運転に戻りました。",
            "base_hp": self.base_hp,
            "facilities": self.get_facility_status(),
        }

    def _get_last_trigger_type(self) -> str:
        for t in self.triggers:
            if t.is_active:
                return t.trigger_type.value
        return "Unknown"

    def get_aftermath_report(self) -> dict[str, Any]:
        """事後報告取得"""
        total_repair_cost = sum(
            (f.max_hp - f.current_hp) * 2
            for f in self.defense_facilities.values()
            if f.is_built and f.current_hp < f.max_hp
        )
        return {
            "base_hp": f"{self.base_hp}/{self.base_max_hp}",
            "facilities_damaged": sum(
                1
                for f in self.defense_facilities.values()
                if f.is_built and f.current_hp < f.max_hp
            ),
            "facilities_destroyed": sum(
                1 for f in self.defense_facilities.values() if f.is_built and f.current_hp == 0
            ),
            "junk_lost": sum(r.junk_looted for r in self._calculate_aftermath_damage()),
            "subordinates_injured": sum(1 for s in self.subordinates if s.is_incapacitated),
            "estimated_repair_cost_junk": total_repair_cost,
            "storage_junk": self.storage_junk,
            "storage_aldo": self.storage_aldo,
        }

    def reset_raid_state(self) -> None:
        """襲撃状態リセット"""
        self.current_phase = RaidPhase.NORMAL
        self.phase_timer = 0
        self.active_raid = False
        self.warning_issued = False
        self.raid_enemies.clear()
        self.current_wave = 1
        self.facility_cooldowns.clear()

    def get_raid_history(self) -> list[dict[str, Any]]:
        """襲撃履歴取得"""
        return self.raid_history[-20:]

    # ============================================================
    # Steps 35-42: Turn Processing Integration
    # ============================================================

    def process_turn(self) -> dict[str, Any]:
        """メインターン処理（ゲームループから毎ターン呼ばれる）"""
        self.turns_since_last_raid += 1

        # 経済システムからの収益収集
        self._collect_economy_income()

        # 襲撃中: フェーズ別処理（active_raidに関わらず現在のフェーズを優先）
        if self.current_phase == RaidPhase.WARNING:
            return self.process_warning_phase()
        elif self.current_phase == RaidPhase.BREACH:
            return self.process_breach_phase()
        elif self.current_phase == RaidPhase.AFTERMATH:
            return self.process_aftermath_phase()

        # 通常時（NORMALフェーズ）: トリガーチェック
        if not self.active_raid:
            triggered, trigger = self.check_raid_triggers()
            if triggered:
                return self.start_raid_warning_phase(trigger)

        return self.get_defense_ui_state()

    def _collect_economy_income(self) -> None:
        """経済収益収集"""
        # 金庫からの収入
        vault = self.economy.base_facilities.get("hq_vault")
        if vault and vault.level > 0:
            income = vault.level * 100
            self.storage_aldo += income

        # ジャンク自然増加（微量）
        self.storage_junk = min(self.storage_capacity_junk, self.storage_junk + 5)

    def trigger_meta_quest_raid(self) -> bool:
        """メタクエストからの襲撃トリガー"""
        if not self.active_raid:
            self.meta_quest_raid_flag = True
            return True
        return False

    def get_defense_ui_state(self) -> dict[str, Any]:
        """UI用ステータス取得"""
        return {
            "phase": self.current_phase.value,
            "phase_timer": self.phase_timer,
            "heat_level": self.heat_level,
            "base_hp": f"{self.base_hp}/{self.base_max_hp}",
            "facilities": self.get_facility_status(),
            "enemies_remaining": len([e for e in self.raid_enemies if not e.is_dead]),
            "current_wave": self.current_wave,
            "max_waves": self.max_waves,
            "storage_junk": self.storage_junk,
            "storage_aldo": self.storage_aldo,
            "storage_capacity_junk": self.storage_capacity_junk,
            "subordinates": [
                {
                    "name": s.name,
                    "hp": s.hp,
                    "max_hp": s.max_hp,
                    "incapacitated": s.is_incapacitated,
                }
                for s in self.subordinates
            ],
            "synergy": {
                "turret_sensor": self.has_turret_sensor,
                "barrier_decoy": self.has_barrier_decoy,
                "all_four": self.has_all_four,
            },
        }

    def add_subordinate(
        self, name: str, max_hp: int, skills: list[str] | None = None
    ) -> Subordinate:
        """従属者追加"""
        sub = Subordinate(
            id=f"sub_{len(self.subordinates)}",
            name=name,
            hp=max_hp,
            max_hp=max_hp,
            skills=skills or [],
        )
        self.subordinates.append(sub)
        return sub

    # ============================================================
    # Steps 43-50: Audio/Visual Integration (already integrated above)
    # ============================================================

    # ============================================================
    # Steps 51-58: Configuration & Balancing
    # ============================================================

    # 定数はファイル冒頭に定義済み

    def balance_test(self, simulations: int = 100) -> dict[str, Any]:
        """バランステスト用シミュレーション"""
        victories = 0
        total_damage = 0
        total_turns = 0

        for _ in range(simulations):
            # 施設フル建設・Lv3想定
            for fac in self.defense_facilities.values():
                fac.is_built = True
                fac.level = 3
                fac.current_hp = fac.max_hp

            self.heat_level = 50
            self.base_hp = self.base_max_hp
            self.active_raid = True
            self.current_phase = RaidPhase.BREACH
            self.phase_timer = BREACH_DURATION
            self.raid_enemies = self._generate_raid_enemies()
            self.current_wave = 1

            turns = 0
            while self.active_raid and turns < 200:
                result = self.process_breach_phase()
                turns += 1
                if result.get("result") == "WAVE_CLEARED":
                    continue
                elif "victory" in result:
                    if result["victory"]:
                        victories += 1
                    break

            total_turns += turns

        return {
            "simulations": simulations,
            "victories": victories,
            "win_rate": victories / simulations,
            "avg_turns": total_turns / simulations,
            "recommendation": (
                "Balanced" if 0.4 < victories / simulations < 0.7 else "Needs Adjustment"
            ),
        }

    # ============================================================
    # Steps 65: Save/Load
    # ============================================================

    def to_dict(self) -> dict[str, Any]:
        """シリアライズ"""
        return {
            "base_max_hp": self.base_max_hp,
            "base_hp": self.base_hp,
            "heat_level": self.heat_level,
            "storage_junk": self.storage_junk,
            "storage_aldo": self.storage_aldo,
            "storage_capacity_junk": self.storage_capacity_junk,
            "turns_since_last_raid": self.turns_since_last_raid,
            "meta_quest_raid_flag": self.meta_quest_raid_flag,
            "current_phase": self.current_phase.value,
            "phase_timer": self.phase_timer,
            "active_raid": self.active_raid,
            "warning_issued": self.warning_issued,
            "current_wave": self.current_wave,
            "max_waves": self.max_waves,
            "defense_facilities": {fid: f.to_dict() for fid, f in self.defense_facilities.items()},
            "subordinates": [
                {
                    "id": s.id,
                    "name": s.name,
                    "hp": s.hp,
                    "max_hp": s.max_hp,
                    "skills": s.skills,
                    "is_incapacitated": s.is_incapacitated,
                    "incapacitated_turns": s.incapacitated_turns,
                }
                for s in self.subordinates
            ],
            "raid_history": self.raid_history,
            "facility_cooldowns": self.facility_cooldowns,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        registry: SkillEaterRegistry | None = None,
        economy: SkillEaterEconomySystem | None = None,
        audio: SkillEaterAudioSystem | None = None,
        presentation: SkillEaterPresentationSystem | None = None,
    ) -> BaseDefenseManager:
        """デシリアライズ"""
        mgr = cls(
            base_max_hp=data.get("base_max_hp", 1000),
            registry=registry,
            economy=economy,
            audio=audio,
            presentation=presentation,
        )

        mgr.base_hp = data.get("base_hp", mgr.base_max_hp)
        mgr.heat_level = data.get("heat_level", 0)
        mgr.storage_junk = data.get("storage_junk", 0)
        mgr.storage_aldo = data.get("storage_aldo", 0)
        mgr.storage_capacity_junk = data.get("storage_capacity_junk", 5000)
        mgr.turns_since_last_raid = data.get("turns_since_last_raid", 0)
        mgr.meta_quest_raid_flag = data.get("meta_quest_raid_flag", False)
        mgr.current_phase = RaidPhase(data.get("current_phase", "Normal"))
        mgr.phase_timer = data.get("phase_timer", 0)
        mgr.active_raid = data.get("active_raid", False)
        mgr.warning_issued = data.get("warning_issued", False)
        mgr.current_wave = data.get("current_wave", 1)
        mgr.max_waves = data.get("max_waves", 3)
        mgr.facility_cooldowns = data.get("facility_cooldowns", {})

        # 施設復元
        for fid, fac_data in data.get("defense_facilities", {}).items():
            if fid in mgr.defense_facilities:
                mgr.defense_facilities[fid] = DefenseFacility.from_dict(fac_data)

        # 従属者復元
        for sub_data in data.get("subordinates", []):
            sub = Subordinate(
                id=sub_data["id"],
                name=sub_data["name"],
                hp=sub_data["hp"],
                max_hp=sub_data["max_hp"],
                skills=sub_data.get("skills", []),
                is_incapacitated=sub_data.get("is_incapacitated", False),
                incapacitated_turns=sub_data.get("incapacitated_turns", 0),
            )
            mgr.subordinates.append(sub)

        mgr.raid_history = data.get("raid_history", [])
        mgr._update_synergy_bonuses()

        return mgr

    def load_facilities_from_yaml(self, file_path: str | Path) -> None:
        """YAMLから施設定義読み込み"""
        path = Path(file_path)
        if not path.exists():
            return

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or "facilities" not in data:
            return

        for fac_data in data["facilities"]:
            facility = DefenseFacility.from_dict(fac_data)
            self.defense_facilities[facility.id] = facility

        self._update_synergy_bonuses()

    # Step 40〜43: 拠点防衛報酬（脳拡張素材・割引券）と敗北時スキル略奪ペナルティ
    def resolve_raid_outcome(
        self,
        is_victory: bool,
        character: CharacterState | None = None,
    ) -> dict[str, Any]:
        """Step 41, 43: 防衛成功報酬（インプラント素材）または防衛失敗時のスキル略奪ペナルティ"""
        if is_victory:
            drops = ["brain_implant_chip_5mb", "cyber_doc_discount_coupon"]
            if character:
                character.base_memory_capacity_mb += 5  # インプラント素材で即時+5MB
                character.calculate_memory_usage()
            self.presentation.add_event(
                emote_file=EMOTE_STARS,
                audio_file=FANFARE,
                message="【防衛成功！】脳拡張インプラント素材(容量+5MB)を獲得！",
            )
            return {
                "success": True,
                "reward_drops": drops,
                "bonus_capacity_mb": 5,
                "message": "拠点防衛に完全成功！ 襲撃部隊から『脳拡張インプラントチップ(+5MB)』を鹵獲しました！",
            }
        else:
            looted_skill_id = None
            if character and character.skills:
                # 保管中または所持スキルからランダムに1つ略奪される
                looted_skill_id = random.choice(list(character.skills.keys()))
                character.remove_skill(looted_skill_id)
                character.calculate_memory_usage()
            self.presentation.add_event(
                emote_file=EMOTE_CROSS,
                audio_file=EXPLOSION_DEBRIS,
                message="【防衛失敗…】アジトが略奪された！",
            )
            return {
                "success": False,
                "looted_skill_id": looted_skill_id,
                "message": f"防衛ライン突破！ アジトからスキル《{looted_skill_id}》が略奪されました……！",
            }

    def increase_alert(self, amount: int = 100) -> dict[str, Any]:
        """Backward-compatibility wrapper for increase_heat / raid check"""
        self.increase_heat(amount)
        triggered = self.heat_level >= 100
        if triggered and self.current_phase == RaidPhase.NORMAL:
            trigger = RaidTrigger(
                trigger_type=RaidTriggerType.HEAT_LEVEL,
                threshold=100,
                current_value=self.heat_level,
            )
            self.start_raid_warning_phase(trigger)
        return {"raid_triggered": triggered, "heat": self.heat_level}

    def start_defense_battle(self) -> None:
        """Backward-compatibility helper to start battle"""
        if self.current_phase == RaidPhase.NORMAL:
            trigger = RaidTrigger(
                trigger_type=RaidTriggerType.HEAT_LEVEL,
                threshold=100,
                current_value=self.heat_level,
            )
            self.start_raid_warning_phase(trigger)
        self.start_breach_phase()

    def place_defense_trap(self, name: str, damage: int = 200) -> None:
        """Backward-compatibility trap placement"""
        if not hasattr(self, "_active_traps"):
            self._active_traps = []
        self._active_traps.append({"name": name, "damage": damage})

    def process_raid_wave(self, enemy_power: int = 250) -> dict[str, Any]:
        """Backward-compatibility raid wave calculation"""
        trap_dmg = 0
        if hasattr(self, "_active_traps"):
            for t in self._active_traps:
                trap_dmg += t.get("damage", 0)
            self._active_traps.clear()
        mitigated = min(trap_dmg, enemy_power)
        base_dmg = max(0, enemy_power - mitigated)
        self.base_hp = max(0, self.base_hp - base_dmg)
        return {
            "trap_damage_mitigated": mitigated,
            "base_damage_taken": base_dmg,
            "base_hp_remaining": self.base_hp,
        }
