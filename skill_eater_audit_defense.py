"""
Skill Eater: Babel Audit Defense System
バベル強制監査部隊を迎撃するタワーディフェンス型スラム防衛戦
既存 BaseDefenseManager (Midas襲撃) を継承し、監査特有のシステムを追加
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_base_defense import (
    BaseDefenseManager,
    DefenseFacility,
    DefenseFacilityType,
    RaidPhase,
    RaidTrigger,
    RaidTriggerType,
)
from skill_eater_economy_system import SkillEaterEconomySystem
from skill_eater_presentation_system import SkillEaterPresentationSystem
from skill_eater_system import CharacterState, SkillEaterRegistry


class AuditTier(str, Enum):
    """監査ティア (第1〜第5監査執行部隊)"""

    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"
    T5 = "T5"


class AuditUnitType(str, Enum):
    """監査ユニット兵科"""

    CLEANER = "Cleaner"           # 第1: 掃討執行隊
    PEACEKEEPER = "Peacekeeper"   # 第2: 治安執行隊
    PURIFIER = "Purifier"         # 第3: 浄化執行隊
    CARDINAL = "Cardinal"         # 第4: 枢機執行隊
    INQUISITOR = "Inquisitor"     # 第5: 審判執行部隊


class TrapType(str, Enum):
    """罠タイプ"""

    EMP = "EMP"
    POISON_CLOUD = "PoisonCloud"
    DECOY = "Decoy"


class AuditElement(str, Enum):
    """属性"""

    FIRE = "fire"
    ICE = "ice"
    THUNDER = "thunder"
    POISON = "poison"
    PHYSICAL = "physical"
    NONE = "none"


class AuditRole(str, Enum):
    """スキル役割"""

    ATTACK = "attack"
    DEFENSE = "defense"
    UTILITY = "utility"


@dataclass
class AuditUnit:
    """監査ユニット"""

    id: str
    name: str
    unit_type: AuditUnitType
    tier: AuditTier
    hp: int
    max_hp: int
    atk: int
    defense: int
    speed: int
    weakness_element: AuditElement = AuditElement.NONE
    is_dead: bool = False
    target_priority: list[str] = field(default_factory=list)

    def take_damage(self, amount: int) -> bool:
        self.hp = max(0, self.hp - amount)
        if self.hp <= 0:
            self.is_dead = True
        return self.is_dead


@dataclass
class AuditCaptain:
    """部隊長"""

    id: str
    name: str
    tier: AuditTier
    hp: int
    max_hp: int
    atk: int
    defense: int
    speed: int
    special_skill_id: str
    weakness_element: AuditElement = AuditElement.NONE
    is_dead: bool = False
    morale_bonus: float = 0.15
    target_priority: list[str] = field(default_factory=lambda: [
        "storage",
        "barrier_generator",
        "auto_turret",
        "sensor_array",
        "decoy_terminal",
        "base",
    ])

    def take_damage(self, amount: int) -> bool:
        self.hp = max(0, self.hp - amount)
        if self.hp <= 0:
            self.is_dead = True
        return self.is_dead


@dataclass
class DistillBlueprint:
    """錬成設計図 (捕食スキルから生成)"""

    id: str
    source_skill_id: str
    element: AuditElement
    role: AuditRole
    skill_level: int
    turret_stats: dict[str, Any] = field(default_factory=dict)
    is_locked: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_skill_id": self.source_skill_id,
            "element": self.element.value,
            "role": self.role.value,
            "skill_level": self.skill_level,
            "turret_stats": self.turret_stats,
            "is_locked": self.is_locked,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DistillBlueprint:
        return cls(
            id=data["id"],
            source_skill_id=data["source_skill_id"],
            element=AuditElement(data["element"]),
            role=AuditRole(data["role"]),
            skill_level=data["skill_level"],
            turret_stats=data.get("turret_stats", {}),
            is_locked=data.get("is_locked", True),
        )


@dataclass
class HuskBarricade:
    """Huskバリケード"""

    id: str
    hp: int
    max_hp: int
    cell: tuple[int, int]
    is_debris: bool = False

    def take_damage(self, amount: int) -> bool:
        self.hp = max(0, self.hp - amount)
        if self.hp <= 0 and not self.is_debris:
            self.is_debris = True
        return self.is_debris


@dataclass
class EmpMine:
    """EMP地雷"""

    id: str
    cell: tuple[int, int]
    trigger_radius: int = 1
    stun_turns: int = 3
    is_triggered: bool = False


@dataclass
class SeizedSkill:
    """強奪スキル"""

    skill_id: str
    name: str
    description: str
    source_tier: AuditTier


# 監査ティア設定 (設計書 15.6 表ベース)
AUDIT_TIER_CONFIG: dict[int, dict] = {
    1: {
        "unit_count": 8,
        "captain_hp": 600,
        "captain_atk": 80,
        "steal_base_rate": 55,
        "core_timer": 180,
        "incoming_skill": "sweep_priority",
    },
    2: {
        "unit_count": 14,
        "captain_hp": 1100,
        "captain_atk": 120,
        "steal_base_rate": 50,
        "core_timer": 160,
        "incoming_skill": "critical_control",
    },
    3: {
        "unit_count": 22,
        "captain_hp": 1800,
        "captain_atk": 180,
        "steal_base_rate": 45,
        "core_timer": 140,
        "incoming_skill": "purification_field",
    },
    4: {
        "unit_count": 34,
        "captain_hp": 3000,
        "captain_atk": 250,
        "steal_base_rate": 40,
        "core_timer": 120,
        "incoming_skill": "execute_death_immunity",
    },
    5: {
        "unit_count": 50,
        "captain_hp": 5200,
        "captain_atk": 350,
        "steal_base_rate": 20,
        "core_timer": 100,
        "incoming_skill": "judgment_decree",
    },
}

# 脅威度 → ティア閾値
THREAT_TIER_THRESHOLDS: dict[int, int] = {
    1: 0,
    2: 20,
    3: 40,
    4: 60,
    5: 80,
    6: 95,
}


# 錬成コスト
DISTILL_COST = {"junk": 200, "skill_lock": True}

# 属性タレット雛形
AUDIT_TURRET_TEMPLATES: dict[AuditElement, dict[str, Any]] = {
    AuditElement.FIRE: {
        "base_damage": 18,
        "base_range": 5,
        "base_cooldown": 2,
        "status": "burn",
        "status_duration": 3,
    },
    AuditElement.ICE: {
        "base_damage": 12,
        "base_range": 6,
        "base_cooldown": 3,
        "status": "freeze",
        "status_duration": 2,
    },
    AuditElement.THUNDER: {
        "base_damage": 20,
        "base_range": 4,
        "base_cooldown": 3,
        "status": "stun",
        "status_duration": 1,
    },
    AuditElement.POISON: {
        "base_damage": 10,
        "base_range": 5,
        "base_cooldown": 2,
        "status": "poison",
        "status_duration": 4,
    },
    AuditElement.PHYSICAL: {
        "base_damage": 25,
        "base_range": 3,
        "base_cooldown": 2,
        "status": "none",
        "status_duration": 0,
    },
}

# 特殊監査タイプ
class SpecialAuditType(str, Enum):
    NONE = "none"
    NIGHT = "night"
    HEAVY = "heavy"
    REVERSE_EAT = "reverse_eat"
    MERC_MIX = "merc_mix"


SPECIAL_AUDIT_TYPES = list(SpecialAuditType)


def load_audit_units(path: str | Path) -> dict[str, Any]:
    """監査ユニットYAML読込 (スタンドアロン関数)"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class AuditDefenseManager(BaseDefenseManager):
    """
    バベル監査部隊迎撃マネージャー
    BaseDefenseManager (Midas襲撃) を継承し、監査特有機能を追加
    """

    def __init__(
        self,
        base_max_hp: int = 1000,
        registry: SkillEaterRegistry | None = None,
        economy: SkillEaterEconomySystem | None = None,
        audio: SkillEaterAudioSystem | None = None,
        presentation: SkillEaterPresentationSystem | None = None,
    ):
        super().__init__(
            base_max_hp=base_max_hp,
            registry=registry,
            economy=economy,
            audio=audio,
            presentation=presentation,
        )

        # 監査固有状態
        self.threat_level: int = 0
        self.audit_tier: AuditTier = AuditTier.T1
        self.audit_state: dict[str, Any] = {}
        self.premonition_days: int = 0
        self.premonition_active: bool = False

        # 錬成システム
        self.blueprints: dict[str, DistillBlueprint] = {}
        self.locked_skills: set[str] = set()

        # 罠・壁
        self.husk_barricades: dict[str, HuskBarricade] = {}
        self.emp_mines: dict[str, EmpMine] = {}

        # 強奪スキル
        self.seized_skills: dict[str, SeizedSkill] = {}

        # シナジーフラグ
        self.has_freeze_thunder_combo: bool = False
        self.has_poison_fire_combo: bool = False

        # アクセシビリティ
        self.defense_options: dict[str, Any] = {
            "speed": 1.0,
            "auto_layout": False,
            "colorblind_icons": True,
        }

        # 監査ユニットデータ (YAMLから読込)
        self.audit_units_data: dict[str, Any] = {}

    # ============================================================
    # 脅威度・予兆・ティア
    # ============================================================

    def compute_threat(self, registry: SkillEaterRegistry | None = None) -> int:
        """脅威度計算 (設計書準拠)"""
        reg = registry or self.registry
        threat = 0

        # 捕食スキル数・ランク
        for skill in reg.owned_skills.values():
            threat += 1  # 基本1
            rank = getattr(skill, "rank", "common")
            if rank == "rare":
                threat += 2  # 合計3
            elif rank == "epic":
                threat += 5  # 合計6
            elif rank == "legendary":
                threat += 11  # 合計12

        # 強奪済み専用スキル
        threat += len(self.seized_skills) * 10

        # スラム勢力Lv (territory_system連携想定)
        try:
            from naRou.skill_eater_territory_system import SkillEaterTerritorySystem
            territory = SkillEaterTerritorySystem()
            threat += territory.get_slum_influence_level() * 2
        except Exception:
            pass

        # 反逆行為フラグ
        if getattr(reg, "anti_babel_acts", 0):
            threat += reg.anti_babel_acts * 5

        self.threat_level = min(100, threat)
        return self.threat_level

    def add_threat(self, amount: int) -> dict[str, Any]:
        """脅威度加算"""
        old = self.threat_level
        self.threat_level = min(100, self.threat_level + amount)

        # 予兆チェック
        premonition = False
        if old < 80 <= self.threat_level:
            premonition = True

        return {
            "current_threat": self.threat_level,
            "audit_imminent": self.threat_level >= 80,
            "premonition_triggered": premonition,
        }

    def threat_to_tier(self, threat: int | None = None) -> AuditTier:
        """脅威度からティア決定"""
        t = threat if threat is not None else self.threat_level
        tier = AuditTier.T1
        for t_num in range(1, 6):
            if t >= THREAT_TIER_THRESHOLDS[t_num]:
                tier = AuditTier(f"T{t_num}")
        self.audit_tier = tier
        return tier

    def start_audit_premonition(self, tier: AuditTier | None = None) -> dict[str, Any]:
        """予兆期間開始"""
        if tier is None:
            tier = self.audit_tier

        self.audit_tier = tier
        self.premonition_days = 3 + (tier.value[1] == "5")  # T5は4日
        self.premonition_active = True
        self.current_phase = RaidPhase.WARNING
        self.phase_timer = self.premonition_days * 10  # ターン換算
        self.active_raid = True
        self.warning_issued = True
        self.current_wave = 1

        # 敵生成
        self.raid_enemies = self._generate_audit_enemies()

        # 警報演出
        self.presentation.add_event(
            emote_file="emote_alert.png",
            audio_file="alarm_klaxon.ogg",
            message=f"【緊急警報！】第{tier.value[1]}監査執行部隊が接近中！ 防衛準備を！",
            duration_ms=5000,
        )

        return {
            "phase": "WARNING",
            "timer": self.phase_timer,
            "premonition_days": self.premonition_days,
            "tier": tier.value,
            "enemies": len(self.raid_enemies),
            "message": f"第{tier.value[1]}監査部隊来襲予告！ {self.premonition_days}日後に戦闘開始！",
        }

    def generate_briefing(self, tier: AuditTier | None = None) -> dict[str, Any]:
        """来襲ブリーフィング生成"""
        t = tier or self.audit_tier
        data = self.audit_units_data.get(t.value, {})
        units = data.get("units", [])
        captain = data.get("captain", {})

        # 属性カウンター推奨
        weaknesses = [u.get("weakness", "none") for u in units]
        recommended = max(set(weaknesses), key=weaknesses.count) if weaknesses else "none"

        return {
            "tier": t.value,
            "composition": units,
            "captain_skill": captain.get("special_skill_id", ""),
            "recommended_counter_element": recommended,
            "core_timer": AUDIT_TIER_CONFIG[int(t.value[1])]["core_timer"],
        }

    def check_audit_trigger(self) -> tuple[bool, RaidTrigger | None]:
        """監査トリガーチェック"""
        # 脅威度トリガー
        if self.threat_level >= THREAT_TIER_THRESHOLDS[5]:  # 95以上で強制
            trigger = RaidTrigger(RaidTriggerType.AUDIT_THREAT, self.threat_level)
            trigger.update(self.threat_level)
            if trigger.check():
                return True, trigger

        # 通常の熱度トリガーも併用
        return super().check_raid_triggers()

    # ============================================================
    # Phase 8: 特殊監査・チュートリアル (Steps 64-69)
    # ============================================================

    def roll_special_audit(self) -> SpecialAuditType:
        """特殊監査タイプ抽選"""
        import random
        # 通常監査が大半、特殊は稀
        roll = random.random()
        if roll < 0.7:
            return SpecialAuditType.NONE
        elif roll < 0.8:
            return SpecialAuditType.NIGHT
        elif roll < 0.85:
            return SpecialAuditType.HEAVY
        elif roll < 0.9:
            return SpecialAuditType.REVERSE_EAT
        elif roll < 0.95:
            return SpecialAuditType.MERC_MIX
        else:
            return SpecialAuditType.NONE

    def is_tutorial_audit(self) -> bool:
        """初回監査(チュートリアル)かどうか"""
        return len(self.raid_history) == 0 and self.audit_tier == AuditTier.T1

    def get_tutorial_hints(self) -> list[str]:
        """チュートリアル用ヒント"""
        if self.is_tutorial_audit():
            return [
                "炎タレットを1つ錬成・建設しよう",
                "Husk壁を設置して進路を遮ろう",
                "部隊長を弱体化させて捕食・強奪を狙おう",
            ]
        return []

    # ============================================================
    # 錬成システム
    # ============================================================

    def classify_skill(self, skill: Any) -> tuple[AuditElement, AuditRole]:
        """スキル分類 (要素, 役割)"""
        name = getattr(skill, "name", "").lower()
        tags = getattr(skill, "tags", [])

        # 要素判定
        element = AuditElement.PHYSICAL
        if any(k in name for k in ["炎", "fire", "inferno", "flare", "burn"]):
            element = AuditElement.FIRE
        elif any(k in name for k in ["氷", "frost", "ice", "freeze", "blizzard"]):
            element = AuditElement.ICE
        elif any(k in name for k in ["雷", "thunder", "bolt", "spark", "shock"]):
            element = AuditElement.THUNDER
        elif any(k in name for k in ["毒", "poison", "venom", "toxic", "acid"]):
            element = AuditElement.POISON

        # 役割判定
        role = AuditRole.ATTACK
        if any(k in tags for k in ["defense", "shield", "barrier", "guard"]):
            role = AuditRole.DEFENSE
        elif any(k in tags for k in ["utility", "move", "teleport", "heal", "buff"]):
            role = AuditRole.UTILITY

        return element, role

    def distill_cost(self, skill: Any) -> dict[str, Any]:
        """錬成コスト計算"""
        return DISTILL_COST.copy()

    def distill_skill(self, skill_id: str) -> DistillBlueprint | None:
        """捕食スキルを錬成して設計図生成"""
        skill = self.registry.owned_skills.get(skill_id)
        if not skill:
            return None

        # コストチェック
        cost = self.distill_cost(skill)
        if self.storage_junk < cost["junk"]:
            return None

        # 実行
        self.storage_junk -= cost["junk"]
        element, role = self.classify_skill(skill)
        skill_level = getattr(skill, "level", 1)

        # スキルロック
        self.locked_skills.add(skill_id)

        # 設計図生成
        template = AUDIT_TURRET_TEMPLATES.get(element, AUDIT_TURRET_TEMPLATES[AuditElement.PHYSICAL])
        turret_stats = template.copy()
        # スキルLvスケーリング
        scale = 1.15 ** (skill_level - 1)
        turret_stats["base_damage"] = int(turret_stats["base_damage"] * scale)

        blueprint = DistillBlueprint(
            id=f"bp_{skill_id}",
            source_skill_id=skill_id,
            element=element,
            role=role,
            skill_level=skill_level,
            turret_stats=turret_stats,
            is_locked=True,
        )

        self.blueprints[blueprint.id] = blueprint
        return blueprint

    def undistill(self, blueprint_id: str) -> bool:
        """解体・復元"""
        bp = self.blueprints.get(blueprint_id)
        if not bp:
            return False

        # 資源還元 70%
        self.storage_junk += int(DISTILL_COST["junk"] * 0.7)
        self.locked_skills.discard(bp.source_skill_id)
        del self.blueprints[blueprint_id]
        return True

    def list_blueprints(self) -> list[DistillBlueprint]:
        return list(self.blueprints.values())

    def get_blueprint(self, blueprint_id: str) -> DistillBlueprint | None:
        return self.blueprints.get(blueprint_id)

    # ============================================================
    # 属性タレット建設
    # ============================================================

    def build_distilled_turret(self, blueprint_id: str, facility_id: str | None = None) -> tuple[bool, str]:
        """錬成設計図からタレット建設"""
        bp = self.blueprints.get(blueprint_id)
        if not bp:
            return False, "設計図が見つかりません"

        fid = facility_id or f"audit_turret_{bp.element.value}_{len([f for f in self.defense_facilities.values() if f.is_built])}"

        # DefenseFacility 生成 (element, blueprint_id 追加)
        turret = DefenseFacility(
            id=fid,
            name=f"{bp.element.value.capitalize()}タレット (Lv{bp.skill_level})",
            facility_type=DefenseFacilityType.AUTO_TURRET,
            level=1,
            max_level=5,
            tier_required=1,
            build_cost_aldo=0,  # 錬成で支払い済み
            build_cost_junk=0,
            upgrade_cost_aldo=3000,
            upgrade_cost_junk=100,
            base_hp=200,
            current_hp=200,
            base_damage=bp.turret_stats.get("base_damage", 20),
            base_range=bp.turret_stats.get("base_range", 5),
            base_cooldown=bp.turret_stats.get("base_cooldown", 2),
            effect_description=f"{bp.element.value}属性攻撃 + {bp.turret_stats.get('status', 'none')}",
            special_ability=f"源スキルLv{bp.skill_level}連動",
            is_built=True,
        )
        # 独自属性を付与 (to_dictで保持されるよう拡張)
        turret.element = bp.element
        turret.blueprint_id = bp.blueprint_id if hasattr(bp, 'blueprint_id') else bp.id
        turret.status_effect = bp.turret_stats.get("status", "none")
        turret.status_duration = bp.turret_stats.get("status_duration", 0)

        self.defense_facilities[fid] = turret
        return True, f"{turret.name} を建設しました！"

    # ============================================================
    # Husk壁・EMP地雷
    # ============================================================

    def place_husk_barricade(self, husk: Any, cell: tuple[int, int]) -> HuskBarricade:
        """Huskをバリケードに変換"""
        from skill_eater_husk_system import create_husk

        # HuskComponent からステータス取得想定
        hp = getattr(husk, "hp", 120)
        barricade = HuskBarricade(
            id=f"barricade_{len(self.husk_barricades)}",
            hp=hp,
            max_hp=hp,
            cell=cell,
        )
        self.husk_barricades[barricade.id] = barricade
        return barricade

    def plant_emp_mine(self, cell: tuple[int, int]) -> EmpMine:
        """EMP地雷設置"""
        mine = EmpMine(
            id=f"emp_{len(self.emp_mines)}",
            cell=cell,
        )
        self.emp_mines[mine.id] = mine
        return mine

    # ============================================================
    # 監査ユニット生成
    # ============================================================

    def _generate_audit_enemies(self) -> list[AuditUnit]:
        """監査敵生成 (オーバーライド)"""
        tier_num = int(self.audit_tier.value[1])
        config = AUDIT_TIER_CONFIG[tier_num]
        data = self.audit_units_data.get(self.audit_tier.value, {})

        enemies: list[AuditUnit] = []
        units_data = data.get("units", [])

        for i in range(config["unit_count"]):
            if units_data:
                udata = units_data[i % len(units_data)]
                unit = AuditUnit(
                    id=f"audit_{i}",
                    name=f"{self.audit_tier.value}_{udata.get('name', 'Unit')}_{i}",
                    unit_type=self.audit_tier,
                    tier=self.audit_tier,
                    hp=udata.get("hp", 100),
                    max_hp=udata.get("hp", 100),
                    atk=udata.get("atk", 20),
                    defense=udata.get("defense", 5),
                    speed=udata.get("speed", 10),
                    weakness_element=AuditElement(udata.get("weakness", "none")),
                    target_priority=[
                        "storage",
                        "barrier_generator",
                        "auto_turret",
                        "sensor_array",
                        "decoy_terminal",
                        "base",
                    ],
                )
            else:
                # フォールバック
                unit = AuditUnit(
                    id=f"audit_{i}",
                    name=f"{self.audit_tier.value}_Unit_{i}",
                    unit_type=self.audit_tier,
                    tier=self.audit_tier,
                    hp=100 + tier_num * 30,
                    max_hp=100 + tier_num * 30,
                    atk=20 + tier_num * 10,
                    defense=5 + tier_num * 2,
                    speed=10,
                    target_priority=[
                        "storage",
                        "barrier_generator",
                        "auto_turret",
                        "sensor_array",
                        "decoy_terminal",
                        "base",
                    ],
                )
            enemies.append(unit)

        # 部隊長追加
        captain_data = data.get("captain", {})
        captain = AuditCaptain(
            id="captain",
            name=f"{self.audit_tier.value} Captain",
            tier=self.audit_tier,
            hp=captain_data.get("hp", config["captain_hp"]),
            max_hp=captain_data.get("hp", config["captain_hp"]),
            atk=captain_data.get("atk", config["captain_atk"]),
            defense=captain_data.get("defense", 20),
            speed=captain_data.get("speed", 8),
            special_skill_id=captain_data.get("special_skill_id", config["incoming_skill"]),
            weakness_element=AuditElement(captain_data.get("weakness", "none")),
        )
        enemies.append(captain)

        return enemies

    # ============================================================
    # 部隊長強奪
    # ============================================================

    def can_seize(self, captain: AuditCaptain) -> bool:
        """強奪可否判定"""
        if captain.hp > captain.max_hp * 0.3:
            return False
        # 状態異常チェック (スタン/凍結/毒 いずれか1つ以上必要)
        if not hasattr(captain, 'status_effects') or not captain.status_effects:
            return False
        required_status = {"stun", "freeze", "poison"}
        has_required = any(s["type"] in required_status and s["duration"] > 0 for s in captain.status_effects)
        return has_required

    def seize_captain(self, captain: AuditCaptain) -> dict[str, Any]:
        """部隊長強奪実行"""
        if not self.can_seize(captain):
            return {"success": False, "reason": "条件未満"}

        tier_num = int(captain.tier.value[1])
        config = AUDIT_TIER_CONFIG[tier_num]
        base_rate = config["steal_base_rate"]
        # 第5は-20ペナルティ
        if tier_num == 5:
            base_rate -= 20

        # プレイヤー捕食スキルLvで補正 (簡易)
        skill_lv = 1  # TODO: 実際の捕食スキルLv参照
        rate = base_rate + skill_lv * 4
        rate = max(0, min(95, rate))

        success = random.random() * 100 < rate

        if success:
            # 成功: スキル付与
            skill_id = captain.special_skill_id
            seized = SeizedSkill(
                skill_id=skill_id,
                name=skill_id.replace("_", " ").title(),
                description=f"第{tier_num}監査部隊長から強奪",
                source_tier=captain.tier,
            )
            self.seized_skills[skill_id] = seized
            # TODO: registryへ付与

            # 撤退
            self.squad_retreat = True

            return {
                "success": True,
                "skill_id": skill_id,
                "message": f"【強奪成功】《{seized.name}》を剥奪！ 残兵は撤退した！",
            }
        else:
            # 失敗: 反撃 + 毒性
            from naRou.skill_eater_toxicity_system import SkillToxicityManager
            tox = SkillToxicityManager()
            tox.add_toxicity(15)

            return {
                "success": False,
                "counter_damage": captain.atk // 2,
                "toxicity_added": 15,
                "message": "【強奪失敗】部隊長の反撃を受け、毒性が上昇した！",
            }

    # ============================================================
    # シナジー
    # ============================================================

    def update_synergy_flags(self) -> None:
        """シナジーフラグ更新"""
        built = {f.id for f in self.defense_facilities.values() if f.is_built}

        # 氷→雷
        self.has_freeze_thunder_combo = (
            any(f.id.startswith("audit_turret_ice") for f in self.defense_facilities.values() if f.is_built)
            and any(f.id.startswith("audit_turret_thunder") for f in self.defense_facilities.values() if f.is_built)
        )

        # 毒→炎
        self.has_poison_fire_combo = (
            any(f.id.startswith("audit_turret_poison") for f in self.defense_facilities.values() if f.is_built)
            and any(f.id.startswith("audit_turret_fire") for f in self.defense_facilities.values() if f.is_built)
        )

    # ============================================================
    # 施設攻撃拡張: 状態異常付与 (Step 31)
    # ============================================================

    def _facility_attack_enemies(self) -> list[dict[str, Any]]:
        """施設から敵への攻撃 (属性タレットの状態異常付与・シナジー付き)"""
        # 親の攻撃実行
        results = super()._facility_attack_enemies()

        # 属性タレットの状態異常付与・シナジー処理
        alive_enemies = [e for e in self.raid_enemies if not e.is_dead]
        if not alive_enemies:
            return results

        # シナジーフラグ更新
        self.update_synergy_flags()

        for fac in self.defense_facilities.values():
            if not fac.is_operational:
                continue
            if self.facility_cooldowns.get(fac.id, 0) > 0:
                continue

            # 属性タレットかチェック
            if fac.facility_type == DefenseFacilityType.AUTO_TURRET and fac.element != "none":
                target = min(alive_enemies, key=lambda e: e.speed)

                # 壁裏DPSボーナス (隣接するHusk壁がある場合)
                bonus = 1.0
                if self.husk_barricades:
                    # 簡易: 壁があれば全タレットにボーナス
                    bonus = 1.25

                damage = int(fac.damage * fac.efficiency * bonus)
                target.take_damage(damage)

                # 状態異常付与
                status = getattr(fac, 'status_effect', 'none')
                duration = getattr(fac, 'status_duration', 0)
                if status != "none" and duration > 0:
                    self._apply_status_to_enemy(target, status, duration)

                # シナジー: 氷→雷拡散
                if self.has_freeze_thunder_combo and fac.element == "thunder":
                    # 凍結中の敵への雷攻撃で隣接にも拡散
                    for e in alive_enemies:
                        if e.id != target.id:
                            e_status = getattr(e, 'status_effects', [])
                            if any(s["type"] == "freeze" and s["duration"] > 0 for s in e_status):
                                e.take_damage(int(damage * 0.5))
                                results.append({
                                    "facility": fac.id,
                                    "target": e.id,
                                    "damage": int(damage * 0.5),
                                    "target_hp": e.hp,
                                    "killed": e.is_dead,
                                    "synergy": "freeze_thunder_spread",
                                })

                # シナジー: 毒→炎爆発
                if self.has_poison_fire_combo and fac.element == "fire":
                    # 毒状態の敵への炎攻撃で小範囲AoE
                    for e in alive_enemies:
                        if e.id != target.id:
                            e_status = getattr(e, 'status_effects', [])
                            if any(s["type"] == "poison" and s["duration"] > 0 for s in e_status):
                                e.take_damage(int(damage * 0.5))
                                results.append({
                                    "facility": fac.id,
                                    "target": e.id,
                                    "damage": int(damage * 0.5),
                                    "target_hp": e.hp,
                                    "killed": e.is_dead,
                                    "synergy": "poison_fire_explosion",
                                })

                self.facility_cooldowns[fac.id] = fac.cooldown
                self.audio.play_sound("turret_fire.ogg")

                results.append({
                    "facility": fac.id,
                    "target": target.id,
                    "damage": damage,
                    "target_hp": target.hp,
                    "killed": target.is_dead,
                    "status_applied": status,
                    "status_duration": duration,
                    "wall_bonus": bonus > 1.0,
                })

        return results

    def _apply_status_to_enemy(self, enemy: AuditUnit, status: str, duration: int) -> None:
        """敵に状態異常を付与 (簡易実装: status_effects リストに追加)"""
        if not hasattr(enemy, 'status_effects'):
            enemy.status_effects = []
        enemy.status_effects.append({"type": status, "duration": duration, "source": "turret"})

    # ============================================================
    # Phase 4: EMP地雷・Husk壁処理 (Steps 37-45)
    # ============================================================

    def _check_emp_triggers(self) -> list[dict[str, Any]]:
        """EMP地雷の起動チェック"""
        results = []
        alive_enemies = [e for e in self.raid_enemies if not e.is_dead]

        for mine in list(self.emp_mines.values()):
            if mine.is_triggered:
                continue

            # 敵が範囲内にいるかチェック
            for enemy in alive_enemies:
                if hasattr(enemy, 'cell'):
                    enemy_cell = enemy.cell
                else:
                    # 簡易: 敵のインデックスをセル位置として扱う
                    enemy_cell = (0, self.raid_enemies.index(enemy))

                dx = abs(enemy_cell[0] - mine.cell[0])
                dy = abs(enemy_cell[1] - mine.cell[1])
                distance = max(dx, dy)  # チェビシェフ距離

                if distance <= mine.trigger_radius:
                    # 起動!
                    mine.is_triggered = True
                    # 範囲内の敵をスタン
                    for e in alive_enemies:
                        if hasattr(e, 'cell'):
                            e_cell = e.cell
                        else:
                            e_cell = (0, self.raid_enemies.index(e))
                        edx = abs(e_cell[0] - mine.cell[0])
                        edy = abs(e_cell[1] - mine.cell[1])
                        if max(edx, edy) <= mine.trigger_radius:
                            self._apply_status_to_enemy(e, "stun", mine.stun_turns)

                    results.append({
                        "mine_id": mine.id,
                        "cell": mine.cell,
                        "stunned_enemies": len(alive_enemies),
                        "stun_turns": mine.stun_turns,
                    })
                    self.audio.play_sound("explosion_debris.ogg")
                    break

        return results

    def process_breach_phase(self) -> dict[str, Any]:
        """BREACHフェーズ処理 (EMP・壁対応版)"""
        if self.current_phase != RaidPhase.BREACH:
            return {"error": "Not in BREACH phase"}

        # EMP地雷チェック
        emp_results = self._check_emp_triggers()

        # 施設攻撃
        facility_results = self._facility_attack_enemies()

        # 敵攻撃 (壁・地雷・施設・拠点)
        enemy_results = self._enemy_attack_facilities_with_traps()

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
                self.raid_enemies = self._generate_audit_enemies()
                return {
                    "phase": "BREACH",
                    "result": "WAVE_CLEARED",
                    "next_wave": self.current_wave,
                    "timer": self.phase_timer,
                    "facility_results": facility_results,
                    "enemy_results": enemy_results,
                    "emp_results": emp_results,
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
            "emp_results": emp_results,
        }

    def _enemy_attack_facilities_with_traps(self) -> list[dict[str, Any]]:
        """敵から施設・壁・地雷への攻撃"""
        results = []
        alive_enemies = [e for e in self.raid_enemies if not e.is_dead]
        operational_facilities = [f for f in self.defense_facilities.values() if f.is_operational]

        # 壁と地雷もターゲット候補に
        operational_barricades = [b for b in self.husk_barricades.values() if not b.is_debris]
        active_mines = [m for m in self.emp_mines.values() if not m.is_triggered]

        for enemy in alive_enemies:
            # スタン中は行動不能
            if hasattr(enemy, 'status_effects'):
                if any(s["type"] == "stun" and s["duration"] > 0 for s in enemy.status_effects):
                    continue

            # ターゲット選択 (優先度: 壁 > 地雷 > 売店 > タレット > 拠点)
            target = None
            target_type = None

            # 壁があれば最優先で狙う (物理的障害物)
            if operational_barricades:
                target = operational_barricades[0]
                target_type = "barricade"
            # 地雷があれば次に狙う
            elif active_mines:
                target = active_mines[0]
                target_type = "mine"
            else:
                # 通常の優先度
                for priority in enemy.target_priority:
                    if priority == "storage":
                        target = "storage"
                        target_type = "storage"
                        break
                    elif priority == "base":
                        target = "base"
                        target_type = "base"
                        break
                    else:
                        # 施設
                        fac = self.defense_facilities.get(priority)
                        if fac and fac.is_operational:
                            target = priority
                            target_type = "facility"
                            break

            if not target:
                target = "base"
                target_type = "base"

            # 攻撃実行
            if target_type == "storage":
                looted = min(self.storage_junk // 10, enemy.atk * 2)
                self.storage_junk = max(0, self.storage_junk - looted)
                self.storage_aldo = max(
                    0, self.storage_aldo - min(self.storage_aldo // 20, enemy.atk)
                )
                results.append({
                    "attacker": enemy.id,
                    "target": "storage",
                    "junk_looted": looted,
                    "aldo_looted": min(self.storage_aldo // 20, enemy.atk),
                })
                self.audio.play_sound("explosion_debris.ogg")

            elif target_type == "base":
                damage = max(1, enemy.atk - 10)
                self.base_hp = max(0, self.base_hp - damage)
                results.append({
                    "attacker": enemy.id,
                    "target": "base",
                    "damage": damage,
                    "base_hp": self.base_hp,
                })
                self.audio.play_sound("explosion_debris.ogg")
                if self.base_hp <= 0:
                    self.presentation.add_event(
                        emote_file="emote_cross.png",
                        audio_file="explosion_debris.ogg",
                        message="【拠点陥落】ベースが破壊された！",
                    )

            elif target_type == "barricade":
                barricade = target
                damage = max(1, enemy.atk - 5)
                was_debris = barricade.is_debris
                barricade.take_damage(damage)
                results.append({
                    "attacker": enemy.id,
                    "target": barricade.id,
                    "target_type": "barricade",
                    "damage": damage,
                    "barricade_hp": barricade.hp,
                    "is_debris": barricade.is_debris,
                })
                if barricade.is_debris and not was_debris:
                    self.presentation.add_event(
                        emote_file="emote_cross.png",
                        audio_file="explosion_debris.ogg",
                        message="Husk壁が破壊された！",
                    )
                else:
                    self.audio.play_sound("explosion_debris.ogg")

            elif target_type == "mine":
                mine = target
                # 地雷は一撃で破壊
                mine.is_triggered = True
                results.append({
                    "attacker": enemy.id,
                    "target": mine.id,
                    "target_type": "mine",
                    "destroyed": True,
                })
                self.audio.play_sound("explosion_debris.ogg")

            else:
                # 施設攻撃 (親のロジックを簡易版で実行)
                facility = target
                accuracy = 1.0
                sensor = self.defense_facilities.get("sensor_array")
                if sensor and sensor.is_operational:
                    accuracy -= sensor.level * 0.1
                accuracy = max(0.3, accuracy)

                import random
                if random.random() < accuracy:
                    damage = max(1, enemy.atk - facility.level * 5)
                    dmg_result = facility.take_damage(damage)
                    results.append({"attacker": enemy.id, "target": facility.id, **dmg_result})

                    if dmg_result["is_destroyed"]:
                        self.presentation.add_event(
                            emote_file="emote_cross.png",
                            audio_file="explosion_debris.ogg",
                            message=f"{facility.name} が破壊された！",
                        )
                        looted = facility.level * 50
                        self.storage_junk = max(0, self.storage_junk - looted)
                        results[-1]["junk_looted"] = looted
                    else:
                        self.audio.play_sound("explosion_debris.ogg")
                else:
                    results.append({"attacker": enemy.id, "target": facility.id, "missed": True})

        return results

    # ============================================================
    # UI状態
    # ============================================================

    def get_defense_ui_state(self) -> dict[str, Any]:
        base = super().get_defense_ui_state()
        base.update({
            "threat_level": self.threat_level,
            "audit_tier": self.audit_tier.value,
            "premonition_days": self.premonition_days,
            "premonition_active": self.premonition_active,
            "blueprints": [bp.to_dict() if hasattr(bp, 'to_dict') else bp.__dict__ for bp in self.blueprints.values()],
            "husk_barricades": {k: v.__dict__ for k, v in self.husk_barricades.items()},
            "emp_mines": {k: v.__dict__ for k, v in self.emp_mines.items()},
            "seized_skills": {k: v.__dict__ for k, v in self.seized_skills.items()},
            "synergy": {
                **base.get("synergy", {}),
                "freeze_thunder": self.has_freeze_thunder_combo,
                "poison_fire": self.has_poison_fire_combo,
            },
            "defense_options": self.defense_options,
        })
        return base

    # ============================================================
    # 保存/復元
    # ============================================================

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update({
            "threat_level": self.threat_level,
            "audit_tier": self.audit_tier.value,
            "premonition_days": self.premonition_days,
            "premonition_active": self.premonition_active,
            "blueprints": {k: v.__dict__ for k, v in self.blueprints.items()},
            "locked_skills": list(self.locked_skills),
            "husk_barricades": {k: v.__dict__ for k, v in self.husk_barricades.items()},
            "emp_mines": {k: v.__dict__ for k, v in self.emp_mines.items()},
            "seized_skills": {k: v.__dict__ for k, v in self.seized_skills.items()},
            "defense_options": self.defense_options,
        })
        return base

    @classmethod
    def from_dict(cls, data: dict[str, Any], **kwargs) -> AuditDefenseManager:
        mgr = cls(**kwargs)
        # 親のフィールド復元 (defense_facilities含む)
        for k, v in data.items():
            if hasattr(mgr, k) and k not in ("triggers", "raid_enemies", "subordinates", "facility_cooldowns", "combat_log", "raid_history"):
                setattr(mgr, k, v)

        # defense_facilities 復元 (親のto_dict形式で保存されている)
        if "defense_facilities" in data:
            mgr.defense_facilities = {}
            for fid, fdata in data["defense_facilities"].items():
                mgr.defense_facilities[fid] = DefenseFacility.from_dict(fdata)

        # 子固有
        mgr.threat_level = data.get("threat_level", 0)
        mgr.audit_tier = AuditTier(data.get("audit_tier", "T1"))
        mgr.premonition_days = data.get("premonition_days", 0)
        mgr.premonition_active = data.get("premonition_active", False)
        mgr.locked_skills = set(data.get("locked_skills", []))

        # blueprints
        mgr.blueprints = {}
        for k, v in data.get("blueprints", {}).items():
            mgr.blueprints[k] = DistillBlueprint(**v)

        # husk_barricades
        mgr.husk_barricades = {}
        for k, v in data.get("husk_barricades", {}).items():
            mgr.husk_barricades[k] = HuskBarricade(**v)

        # emp_mines
        mgr.emp_mines = {}
        for k, v in data.get("emp_mines", {}).items():
            mgr.emp_mines[k] = EmpMine(**v)

        # seized_skills
        mgr.seized_skills = {}
        for k, v in data.get("seized_skills", {}).items():
            mgr.seized_skills[k] = SeizedSkill(**v)

        return mgr

    def load_audit_units_data(self, path: str | Path) -> None:
        """監査ユニットYAML読込"""
        with open(path, "r", encoding="utf-8") as f:
            self.audit_units_data = yaml.safe_load(f)

    def balance_test(self, simulations: int = 20) -> dict[str, Any]:
        """監査用バランステスト"""
        victories = 0
        total_turns = 0

        for _ in range(simulations):
            # フル建設 Lv3 想定
            for fac in self.defense_facilities.values():
                fac.is_built = True
                fac.level = 3
                fac.current_hp = fac.max_hp

            self.threat_level = 50
            self.audit_tier = AuditTier.T3
            self.base_hp = self.base_max_hp
            self.active_raid = True
            self.current_phase = RaidPhase.BREACH
            self.phase_timer = 120
            self.raid_enemies = self._generate_audit_enemies()
            self.current_wave = 1
            self.facility_cooldowns = {fid: 0 for fid in self.defense_facilities}

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
            "win_rate": victories / simulations if simulations else 0,
            "avg_turns": total_turns / simulations if simulations else 0,
            "recommendation": "Balanced" if 0.4 < (victories / simulations if simulations else 0) < 0.7 else "Needs Adjustment",
        }

    # ============================================================
    # Turn Processing Integration (Step 18)
    # ============================================================

    def process_turn(self) -> dict[str, Any]:
        """メインターン処理 - 監査トリガー追加"""
        self.turns_since_last_raid += 1

        # 経済システムからの収益収集
        self._collect_economy_income()

        # 襲撃中: フェーズ別処理
        if self.current_phase == RaidPhase.WARNING:
            return self.process_warning_phase()
        elif self.current_phase == RaidPhase.BREACH:
            return self.process_breach_phase()
        elif self.current_phase == RaidPhase.AFTERMATH:
            return self.process_aftermath_phase()

        # 通常時（NORMALフェーズ）: 監査トリガーチェック + 親のトリガー
        if not self.active_raid:
            # 監査脅威度トリガー
            triggered, trigger = self.check_audit_trigger()
            if triggered:
                return self.start_audit_premonition()

            # 親のトリガー (Midas熱度など)
            triggered, trigger = super().check_raid_triggers()
            if triggered:
                return self.start_raid_warning_phase(trigger)

        return self.get_defense_ui_state()
