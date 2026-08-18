"""
Elona Roguelike - フェーズ5: 高度な戦闘・属性・フレンドリーファイア・出血システム
Steps 37-45: 属性耐性, 詠唱失敗率, AoEパターン, Faction/Aggro, 出血と自然回復の相殺
"""

from __future__ import annotations
import random
from typing import List, Tuple, Optional, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass
from constants import Element

if TYPE_CHECKING:
    from entity import Entity

# 状態異常
STATUS_POISON    = "毒"
STATUS_PARALYSIS = "麻痺"
STATUS_CONFUSION = "混乱"
STATUS_BLIND     = "盲目"
STATUS_BLEEDING  = "出血"   # ステップ45
STATUS_HASTE     = "加速"
STATUS_SLOW      = "鈍足"
STATUS_RETURN    = "帰還待機" # ステップ63 遅延ワープ

# ファクション (ステップ42)
FACTION_PLAYER    = "player"
FACTION_MONSTER   = "monster"
FACTION_TOWNSFOLK = "townsfolk"
FACTION_GUARD     = "guard"


@dataclass
class StatusEffect:
    """状態異常 - Tick連動(ステップ16)"""
    name: str
    remaining_ticks: int    # 残り持続Tick
    power: int = 1          # 効果の強さ
    source: Optional[str] = None


class ResistanceSet:
    """属性耐性セット (ステップ37)"""
    def __init__(self):
        self.fire       = 0   # -100〜100, 0=通常, 100=無効, -50=弱点(1.5倍)
        self.cold       = 0
        self.lightning  = 0
        self.darkness   = 0
        self.chaos      = 0
        self.magic      = 0

    def get(self, element: Element) -> int:
        mapping = {
            Element.FIRE:      self.fire,
            Element.COLD:      self.cold,
            Element.LIGHTNING: self.lightning,
            Element.DARKNESS:  self.darkness,
            Element.CHAOS:     self.chaos,
            Element.MAGIC:     self.magic,
        }
        return mapping.get(element, 0)


class AggroList:
    """ヘイトリスト (ステップ42)"""
    def __init__(self):
        self._table: Dict[str, int] = {}  # entity name -> hate_value

    def add_hate(self, target_name: str, amount: int) -> None:
        self._table[target_name] = self._table.get(target_name, 0) + amount

    def top_target(self) -> Optional[str]:
        if not self._table:
            return None
        return max(self._table, key=lambda k: self._table[k])


class CombatSystem:
    """高度な戦闘計算 - 属性・詠唱失敗・AoE・フレンドリーファイア・出血 (ステップ37〜45)"""

    # AoEパターン生成 (ステップ40)
    @staticmethod
    def aoe_radius(cx: int, cy: int, radius: int = 1) -> List[Tuple[int, int]]:
        """円形範囲の座標リスト"""
        coords = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if abs(dx) + abs(dy) <= radius * 1.5:
                    coords.append((cx + dx, cy + dy))
        return coords

    @staticmethod
    def aoe_beam(sx: int, sy: int, direction: Tuple[int, int], length: int = 5) -> List[Tuple[int, int]]:
        """直線ビーム範囲"""
        dx, dy = direction
        return [(sx + dx * i, sy + dy * i) for i in range(1, length + 1)]

    @staticmethod
    def aoe_nova(cx: int, cy: int) -> List[Tuple[int, int]]:
        """周囲全方位（8マス）"""
        return [(cx + dx, cy + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)]

    @staticmethod
    def calc_element_damage(base_dmg: int, element: Element, resistance: int) -> int:
        """属性耐性を考慮したダメージ計算 (ステップ38)"""
        # resistance: 100=無効, 0=通常, -50=弱点(1.5倍)
        multiplier = max(0.0, 1.0 - (resistance / 100.0))
        return max(0, int(base_dmg * multiplier))

    @staticmethod
    def calc_spell_success(caster: "Entity", spell_id: str) -> Tuple[bool, Optional[int]]:
        """魔法詠唱成功率 (ステップ39) - 失敗時にマナ反動ダメージ"""
        skill_lv = caster.skills.get("magic_cast", None)
        skill_val = skill_lv.level if skill_lv else 1
        magic_attr = caster.attributes.magic if hasattr(caster, "attributes") else 10

        # 成功率計算: スキルLv * 8 + 知力 * 3 + 乱数
        success_rate = min(98, max(5, skill_val * 8 + magic_attr * 3 - 20))
        roll = random.randint(1, 100)

        if roll <= success_rate:
            return True, None
        else:
            # 失敗: マナ反動ダメージ
            backlash = random.randint(3, 10 + magic_attr)
            return False, backlash

    @staticmethod
    def calculate_melee_attack(
        attacker: "Entity",
        defender: "Entity",
        weapon=None,
        element: Element = Element.PHYSICAL
    ) -> Tuple[int, bool, str]:
        """近接攻撃 + 属性ダメージ + 出血付与 (ステップ37, 38, 45)"""
        hit_rate = 75 + attacker.attributes.dexterity - defender.attributes.dexterity
        if weapon:
            hit_rate += weapon.hit_bonus * 5
        hit_rate = max(10, min(95, hit_rate))

        if random.randint(1, 100) > hit_rate:
            return 0, False, f"{attacker.name}の攻撃は{defender.name}にかわされた。"

        crit_rate = 5 + int(attacker.attributes.perception / 5)
        is_crit = random.randint(1, 100) <= crit_rate

        dice_n = weapon.dice_num if weapon else 1
        dice_s = weapon.dice_side if weapon else 4
        bonus  = weapon.dmg_bonus if weapon else 0
        roll_dmg = sum(random.randint(1, dice_s) for _ in range(dice_n)) + bonus
        roll_dmg += int(attacker.attributes.strength / 3)
        if is_crit:
            roll_dmg = int(roll_dmg * 1.5) + dice_s

        # 属性耐性適用
        res = getattr(defender, "resistances", ResistanceSet())
        res_val = res.get(element) if hasattr(res, "get") else 0
        final_dmg = CombatSystem.calc_element_damage(roll_dmg, element, res_val)
        final_dmg = max(1, final_dmg - random.randint(0, max(1, int(defender.attributes.endurance / 4))))

        # 転生スケーリング適用 (Steps 53, 54)
        # TODO: Reincarnation scaling
        if not getattr(attacker, "is_player", False):
            # 敵の攻撃力にプレイヤーの転生スケーリングを適用
            reinc_count = getattr(defender, "reincarnation_count", 0)
            if reinc_count > 0:
                mult = min(5.0, 1.0 + reinc_count * 0.15)
                final_dmg = int(final_dmg * mult)

        # 出血判定 (ステップ45): 大きなダメージ時に5%
        if final_dmg > 8 and random.random() < 0.05:
            if not hasattr(defender, "status_effects"):
                defender.status_effects = []
            # 既存の出血を更新
            defender.status_effects = [s for s in defender.status_effects if s.name != STATUS_BLEEDING]
            defender.status_effects.append(StatusEffect(STATUS_BLEEDING, 500, power=2))

        crit_msg = "★会心の一撃！ " if is_crit else ""
        msg = f"{attacker.name}は{defender.name}に{final_dmg}ダメージ！ {crit_msg}"
        return final_dmg, is_crit, msg

    @staticmethod
    def apply_aoe(
        caster: "Entity",
        coords: List[Tuple[int, int]],
        base_dmg_range: Tuple[int, int],
        element: Element,
        entities: List["Entity"],
        karma_ref: Any = None,
    ) -> List[str]:
        """AoE範囲攻撃 - フレンドリーファイア含む (ステップ40, 41)"""
        logs = []
        for ex, ey in coords:
            for e in list(entities):
                if e.x == ex and e.y == ey and e.hp > 0:
                    base = random.randint(*base_dmg_range)
                    res = getattr(e, "resistances", ResistanceSet())
                    res_val = res.get(element) if hasattr(res, "get") else 0
                    dmg = CombatSystem.calc_element_damage(base + caster.attributes.magic, element, res_val)
                    e.hp -= dmg
                    logs.append(f"  -> {e.name}に{dmg}の{element.name}ダメージ！")
                    # フレンドリーファイア: ペットや市民を巻き込んだらカルマ低下
                    if e.is_pet if hasattr(e, "is_pet") else False:
                        if karma_ref is not None:
                            karma_ref["value"] -= 5
                        logs.append(f"    【悪行】{e.name}を巻き込んだ！ カルマ-5")
        return logs

    @staticmethod
    def process_status_effects(entity: "Entity") -> List[str]:
        """状態異常のTick処理 (ステップ16, 45)"""
        if not hasattr(entity, "status_effects"):
            entity.status_effects = []
        logs = []
        remaining = []
        for eff in entity.status_effects:
            eff.remaining_ticks -= 10
            if eff.name == STATUS_POISON:
                dmg = max(1, eff.power)
                entity.hp -= dmg
                if random.random() < 0.1:
                    logs.append(f"{entity.name}は毒に蝕まれる！(-{dmg} HP)")
            elif eff.name == STATUS_BLEEDING:
                dmg = max(1, eff.power)
                entity.hp -= dmg
                if random.random() < 0.15:
                    logs.append(f"{entity.name}の傷口から血が流れ出す！(-{dmg} HP)")
            elif eff.name == STATUS_PARALYSIS:
                entity.energy = min(entity.energy, 0)

            if eff.remaining_ticks > 0:
                remaining.append(eff)
            else:
                if eff.name == STATUS_BLEEDING:
                    logs.append(f"{entity.name}の出血が止まった。")

        entity.status_effects = remaining

        # 出血中は自然回復ストップ (ステップ45)
        is_bleeding = any(e.name == STATUS_BLEEDING for e in entity.status_effects)
        return logs, is_bleeding

    @staticmethod
    def cast_spell(caster: "Entity", spell_name: str, target: "Entity") -> Tuple[int, str]:
        """詠唱失敗率つき魔法発動 (ステップ39)"""
        success, backlash = CombatSystem.calc_spell_success(caster, spell_name)
        if not success:
            caster.hp -= backlash
            return 0, f"詠唱に失敗した！ 魔力が暴走し{backlash}のダメージを受けた！"

        if spell_name == "magic_dart":
            mp_cost = 4
            if caster.mp < mp_cost: return 0, "MPが足りない！"
            caster.mp -= mp_cost
            dmg = random.randint(1, 6) + int(caster.attributes.magic / 2) + 5
            target.hp -= dmg
            return dmg, f"{caster.name}は魔法の矢を放ち{target.name}に{dmg}ダメージ！"
        elif spell_name == "minor_heal":
            mp_cost = 6
            if caster.mp < mp_cost: return 0, "MPが足りない！"
            caster.mp -= mp_cost
            heal = 25 + int(caster.attributes.will / 2)
            caster.hp = min(caster.max_hp, caster.hp + heal)
            return heal, f"{caster.name}の傷が癒えた！ (HP +{heal})"
        elif spell_name == "fireball":
            mp_cost = 10
            if caster.mp < mp_cost: return 0, "MPが足りない！"
            caster.mp -= mp_cost
    # === エクスクルーシブスキル処理 (Steps 62, 63) ===
    @staticmethod
    def is_exclusive_skill(skill_id: str) -> bool:
        """スキルIDがエクスクルーシブスキルか判定 (Step 62)"""
        try:
            import yaml
            from pathlib import Path
            p = Path("data/exclusive_skills.yaml")
            if not p.exists():
                return False
            with open(p, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            return skill_id in data.get('exclusive_skills', {})
        except Exception:
            return False

    @staticmethod
    def get_exclusive_skill_data(skill_id: str) -> Optional[Dict[str, Any]]:
        """エクスクルーシブスキルの定義データを取得 (Step 62)"""
        try:
            import yaml
            from pathlib import Path
            p = Path("data/exclusive_skills.yaml")
            if not p.exists():
                return None
            with open(p, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            return data.get('exclusive_skills', {}).get(skill_id)
        except Exception:
            return None

    @staticmethod
    def execute_exclusive_skill(caster: "Entity", skill_id: str, target: "Entity") -> Tuple[int, str]:
        """エクスクルーシブスキル実行 (Step 63)"""
        data = CombatSystem.get_exclusive_skill_data(skill_id)
        if not data:
            return 0, "不明な専用スキル。"

        mp_cost = data.get('mp_cost', 10)
        if caster.mp < mp_cost:
            return 0, f"MPが足りない！ (必要MP: {mp_cost})"

        caster.mp -= mp_cost
        effects = data.get('effects', {})
        name = data.get('name', skill_id)

        # ダメージ計算
        dmg = 0
        if skill_id == "shield_bash":
            dmg = int(caster.attributes.strength * 1.5) + random.randint(3, 8)
            target.hp -= dmg
            if not hasattr(target, "status_effects"):
                target.status_effects = []
            target.status_effects.append(StatusEffect(STATUS_PARALYSIS, 30, power=2))
            return dmg, f"{caster.name}の【{name}】！ {target.name}に{dmg}ダメージとスタンを付与！"

        elif skill_id == "iaijutsu":
            dmg = int(caster.attributes.dexterity * 2.5 + caster.attributes.strength * 1.2) + random.randint(10, 20)
            target.hp -= dmg
            return dmg, f"★{caster.name}の神速の【{name}】！ 刀閃が走り{target.name}に{dmg}の致命傷！"

        elif skill_id == "meteor":
            dmg = int(caster.attributes.magic * 4.0) + random.randint(20, 50)
            target.hp -= dmg
            if not hasattr(target, "status_effects"):
                target.status_effects = []
            target.status_effects.append(StatusEffect(STATUS_BLEEDING, 500, power=5))
            return dmg, f"🌌{caster.name}の【{name}】！ 天より隕石が降り注ぎ{target.name}に{dmg}の破滅的ダメージ！"

        return 0, f"{caster.name}は【{name}】を放った！"


class SurvivalSystem:
    """サバイバル・空腹・信仰・カルマ・エーテル病"""
    def __init__(self):
        self.hunger      = 8000
        self.sleepiness  = 0
        self.karma       = 20
        self.gold        = 500
        self.platinum    = 5
        self.ether_disease = 0
        self.mutations: List[str] = []
        self.god         = "なし"
        self.piety       = 0
        self.tax_pending = 0    # 未払い税金

    def pass_turn(self, player: "Entity") -> List[str]:
        logs = []
        self.hunger -= 1
        self.sleepiness += 1
        if self.hunger <= 0:
            self.hunger = 0
            player.hp -= 2
            logs.append("★飢えが体を蝕んでいる！(-2 HP)")
        elif self.hunger < 1000:
            if random.random() < 0.1:
                logs.append("空腹で倒れそうだ…何か食べないと。")
        return logs

    def eat(self, player: "Entity", food_item: "Item") -> List[str]:
        logs = []
        is_rotten = "腐った" in food_item.name
        self.hunger = min(10000, self.hunger + food_item.nutrition)
        if is_rotten:
            logs.append(f"腐った {food_item.name} を食べた！ 激しい吐き気に襲われる！")
            # 猛毒付与
            if not hasattr(player, "status_effects"):
                player.status_effects = []
            player.status_effects.append(StatusEffect(STATUS_POISON, 1500, power=4))
        else:
            logs.append(f"{player.name}は {food_item.name} を食べた。")
            if food_item.nutrition > 2000:
                player.attributes.strength += 1
                player.recalculate_stats()
                logs.append("力がみなぎってきた！(筋力+1)")
        return logs

    def sleep(self, player: "Entity") -> List[str]:
        self.sleepiness = 0
        player.hp = player.max_hp
        player.mp = player.max_mp
        player.stamina = player.max_stamina
        return ["ぐっすり眠った。HP・MP・スタミナが全快した！"]


from dataclasses import dataclass as _dc

@_dc
class Quest:
    title: str
    target_monster: str
    target_count: int
    current_count: int = 0
    reward_gold: int = 200
    reward_platinum: int = 2
    completed: bool = False


class MonsterPreset:
    @staticmethod
    def create(name: str, x: int, y: int) -> "Entity":
        from entity import Entity, Attributes
        from config_manager import DataCache

        m_data = DataCache.get_data("data/monsters.yaml")
        if m_data and name in m_data:
            entry = m_data[name]
            attr_dict = entry.get("attributes", {})
            attr = Attributes(
                strength=attr_dict.get("strength", 10),
                endurance=attr_dict.get("endurance", 10),
                dexterity=attr_dict.get("dexterity", 10),
                perception=attr_dict.get("perception", 10),
                learning=attr_dict.get("learning", 10),
                will=attr_dict.get("will", 10),
                magic=attr_dict.get("magic", 10),
                charisma=attr_dict.get("charisma", 10),
            )
            e = Entity(
                x=x,
                y=y,
                char=entry.get("char", "👾"),
                color=tuple(entry.get("color", [255, 255, 255])),
                name=entry.get("name", name),
                speed=entry.get("speed", 70),
                attributes=attr,
            )
            e.max_hp = entry.get("max_hp", 20)
            e.hp = e.max_hp
            e.faction = FACTION_MONSTER
            e.aggro = AggroList()
            e.resistances = ResistanceSet()
            e.status_effects = []
            return e

        # フォールバック
        presets = {
            "slime":  ("ぷち",    "🍮", (100, 255, 100), 50,  Attributes(strength=5,  endurance=6,  dexterity=6)),
            "goblin": ("ゴブリン", "👺", (200, 100, 50),  70,  Attributes(strength=8,  endurance=8,  dexterity=8)),
            "orc":    ("オーク",   "👹", (150, 150, 50),  65,  Attributes(strength=14, endurance=12, dexterity=6)),
        }
        if name not in presets:
            return Entity(x, y, "👾", (255, 255, 255), "モンスター")
        n, c, col, spd, attr = presets[name]
        e = Entity(x, y, c, col, n, speed=spd, attributes=attr)
        hp_map = {"slime": 14, "goblin": 24, "orc": 42}
        e.max_hp = hp_map.get(name, 20)
        e.hp = e.max_hp
        e.faction = FACTION_MONSTER
        e.aggro = AggroList()
        e.resistances = ResistanceSet()
        e.status_effects = []
        return e



# --- LocalizationManager integration (i18n, Step 3.x) ---
def localize(key: str, language: str = None, manager=None) -> str:
    """Return localized text for *key* using LocalizationManager.

    Provides a thin, dependency-free wrapper so callers can localize UI
    strings without importing the manager directly.
    """
    from localization_manager import LocalizationManager
    mgr = manager or LocalizationManager()
    return mgr.get_text(key, language)
