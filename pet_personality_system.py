"""
Elona Masterpiece Edition - Pet Personality & Bonding System (Phase 6, Steps 49-72)
Manages pet personalities, favorite foods, feeding/bond growth, equipment restrictions, and tactical AI.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

from naRou.constants import (
    FOOD_TAG_FISH,
    FOOD_TAG_HERB,
    FOOD_TAG_MEAT,
    FOOD_TAG_SWEET,
    FOOD_TAG_VEGETABLE,
    PERSONALITY_AGGRESSIVE,
    PERSONALITY_BRAVE,
    PERSONALITY_CALM,
    PERSONALITY_COWARDLY,
    PERSONALITY_GLUTTONOUS,
    PERSONALITY_LABELS,
)

if TYPE_CHECKING:
    from naRou.ecs.entity import Entity

# initialize_pet_personality が抽選する好物タグ候補
_CANDIDATE_FOOD_TAGS = (FOOD_TAG_MEAT, FOOD_TAG_FISH, FOOD_TAG_SWEET, FOOD_TAG_HERB, FOOD_TAG_VEGETABLE)


class PetPersonalitySystem:
    """ペットの性格・好物・絆・育成管理システム"""

    @staticmethod
    def assign_random_personality(pet: Entity, candidate_personalities: list[str] | None = None) -> str:
        """ペット生成時に性格をランダム抽選して付与 (Step 55)"""
        candidates = candidate_personalities or [
            PERSONALITY_BRAVE,
            PERSONALITY_COWARDLY,
            PERSONALITY_CALM,
            PERSONALITY_GLUTTONOUS,
            PERSONALITY_AGGRESSIVE,
        ]
        chosen = random.choice(candidates)
        pet.personality = chosen
        return chosen

    @staticmethod
    def initialize_pet_personality(pet: Entity) -> str:
        """新規ペットへ性格と好物を付与する (未付与の属性のみ)。

        旧セーブや既存の付与値を尊重し、上書きはしない。
        戻り値は最終的な性格。
        """
        if not getattr(pet, "personality", None):
            PetPersonalitySystem.assign_random_personality(pet)
        if not getattr(pet, "favorite_food_tags", None):
            pet.favorite_food_tags = [random.choice(_CANDIDATE_FOOD_TAGS)]
        return getattr(pet, "personality", PERSONALITY_BRAVE)

    @staticmethod
    def get_effective_bond_percent(pet: Entity) -> int:
        """0-100 に正規化した実効絆度を返す。

        - entity 属性 bond (0-100 スケール、feed_pet 系が管理) があればそれを優先
        - 無ければ pet.pet_ai.bond (契約の max_bond スケール) を百分率へ正規化
        - どちらも無ければ旧デフォルトの 50
        """
        entity_bond = getattr(pet, "bond", None)
        if entity_bond is not None:
            return max(0, min(100, int(entity_bond)))

        pet_ai = getattr(pet, "pet_ai", None)
        if pet_ai is not None:
            bond = int(getattr(pet_ai, "bond", 0))
            max_bond = 1000
            try:
                from pet_contract_system import REGISTRY as CONTRACT_REG

                CONTRACT_REG.load()
                contract = CONTRACT_REG.get(getattr(pet_ai, "contract_id", "default"))
                if contract is not None:
                    max_bond = int(getattr(contract, "max_bond", max_bond))
            except Exception:
                pass  # 契約データ不在時は既定スケール (0-1000) を使う
            return max(0, min(100, bond * 100 // max(1, max_bond)))

        return 50

    @staticmethod
    def feed_pet(pet: Entity, food_item: Any) -> tuple[bool, int, str]:
        """
        ペットに食料を与える処理 (Steps 57-60, 68)
        - 好物タグ一致で大幅絆UP (+10)
        - 腐敗・呪い食料で絆DOWN (-5)
        - 通常食料で小幅UP (+3)
        - 性格「食いしん坊」ならさらにボーナス
        """
        if not food_item:
            return False, getattr(pet, "bond", 50), "与えるアイテムがありません。"

        # 食料判定
        category = getattr(food_item, "category", "")
        if category not in ("food", "potion", "herb", "consumable"):
            return False, getattr(pet, "bond", 50), f"{getattr(food_item, 'name', 'アイテム')} は食べられません。"

        food_tags = getattr(food_item, "food_tags", []) or []
        pet_favorites = getattr(pet, "favorite_food_tags", []) or []
        is_cursed = getattr(food_item, "cursed", False)
        is_rotten = getattr(food_item, "rotten", False) or getattr(food_item, "is_rotten", False)
        personality = getattr(pet, "personality", PERSONALITY_BRAVE)

        bond_delta = 0
        pet_name = getattr(pet, "name", "ペット")
        food_name = getattr(food_item, "name", "食べ物")

        if is_cursed or is_rotten:
            bond_delta = -5
            msg = f"{pet_name} は {food_name} を口にして苦悶の表情を浮かべた…！ (絆 -5)"
        elif any(tag in pet_favorites for tag in food_tags):
            # 好物！
            bond_delta = 10
            if personality == PERSONALITY_GLUTTONOUS:
                bond_delta += 3
            msg = f"💖 {pet_name} は大好物の {food_name} を食べて大喜びした！ (絆 +{bond_delta})"
        else:
            # 通常食料
            bond_delta = 3
            if personality == PERSONALITY_GLUTTONOUS:
                bond_delta += 2
            msg = f"😋 {pet_name} は {food_name} を美味しそうに平らげた。 (絆 +{bond_delta})"

        cur_bond = getattr(pet, "bond", 50)
        new_bond = max(0, min(100, cur_bond + bond_delta))
        pet.bond = new_bond

        return True, new_bond, msg

    @staticmethod
    def can_equip_item(pet: Entity, item: Any) -> tuple[bool, str]:
        """
        ペットの装備制限判定 (Steps 65, 66)
        - 高レア装備（奇跡・神器）は絆50以上が必要
        - 絆が不足していると装備を拒否
        """
        if not item:
            return False, "アイテムが指定されていません。"

        rarity = getattr(item, "rarity", "normal")
        bond = getattr(pet, "bond", 50)
        pet_name = getattr(pet, "name", "ペット")

        if rarity in ("miracle", "god", "epic", "legendary") and bond < 50:
            return False, f"{pet_name} はまだあなたへの信頼（絆: {bond}/50）が足りず、強力な装備を受け取れない！"

        return True, f"{pet_name} は {getattr(item, 'name', '装備')} を身につけた。"

    @staticmethod
    def get_bond_stat_modifiers(pet: Entity) -> dict[str, int | float]:
        """
        絆レベルに応じたステータス・戦闘補正 (Step 67)
        """
        bond = PetPersonalitySystem.get_effective_bond_percent(pet)
        return {
            "hp_bonus": int(bond * 0.4),  # 最大 +40 HP
            "hit_bonus": int(bond * 0.1),  # 最大 +10 命中
            "damage_multiplier": round(1.0 + (bond / 100.0) * 0.25, 2),  # 最大 1.25倍
            "dv_bonus": int(bond * 0.08),  # 回避補正
        }

    @staticmethod
    def evaluate_ai_behavior(pet: Entity, player: Entity, enemies: list[Entity]) -> dict[str, Any]:
        """
        性格および戦況に基づくペットの行動決定ロジック (Steps 61-64, 69)
        - BRAVE: 強敵・ボスへ突進。HP低下時も撤退せず攻撃継続
        - COWARDLY: HP 50%未満でプレイヤーの背後へ逃走
        - CALM: 最もHPが低い敵を各個撃破、主人が危険な場合は護衛
        - AGGRESSIVE: 最も近い敵に猛攻
        - GLUTTONOUS: 近接攻撃優先
        """
        personality = getattr(pet, "personality", PERSONALITY_BRAVE)
        pet_hp = getattr(pet, "hp", 10)
        pet_max_hp = getattr(pet, "max_hp", 10)
        hp_ratio = pet_hp / max(1, pet_max_hp)

        if not enemies:
            return {"action": "follow_player", "target": player}

        # 臆病 (Cowardly): HP 50%以下で逃避行動 (Step 63)
        if personality == PERSONALITY_COWARDLY and hp_ratio < 0.50:
            return {
                "action": "retreat_to_player",
                "target": player,
                "reason": "臆病な性格のため、負傷して主人の後ろに隠れようとしている",
            }

        # 勇敢 (Brave): 最も手強い敵（HP最大）を優先 (Step 62)
        if personality == PERSONALITY_BRAVE:
            strongest = max(enemies, key=lambda e: getattr(e, "max_hp", 0))
            return {
                "action": "attack",
                "target": strongest,
                "reason": "勇敢な性格のため、最も強大な敵に立ち向かっている",
            }

        # 冷静 (Calm): 最もHPが減少している敵を狙い各個撃破 (Step 64)
        if personality == PERSONALITY_CALM:
            weakest = min(enemies, key=lambda e: getattr(e, "hp", 999))
            return {
                "action": "attack",
                "target": weakest,
                "reason": "冷静な性格のため、確実に仕留められる敵を狙っている",
            }

        # 好戦的 (Aggressive): 最も距離の近い敵を狙う
        if personality == PERSONALITY_AGGRESSIVE:
            closest = min(
                enemies,
                key=lambda e: (getattr(e, "x", 0) - getattr(pet, "x", 0)) ** 2
                + (getattr(e, "y", 0) - getattr(pet, "y", 0)) ** 2,
            )
            return {
                "action": "attack",
                "target": closest,
                "reason": "好戦的な性格のため、最も近い敵に突撃している",
            }

        # デフォルト (食いしん坊など)
        return {
            "action": "attack",
            "target": enemies[0],
            "reason": "敵と交戦中",
        }

    @staticmethod
    def apply_bond_gameplay_effects(engine: Any) -> None:
        """turn 進行から呼ばれる絆の実ゲーム効果適用 (改善案6 機能3)。

        絆に応じた最大HPボーナスをペットへ反映する。ボーナスは前回適用分を
        記憶して差分計算するため冪等で、レベルアップ等の外部による max_hp
        変更も打ち消さない。自動回復は行わない (控えめな初期値)。
        """
        pet = getattr(engine, "pet", None)
        if pet is None or getattr(pet, "hp", 0) <= 0:
            return

        try:
            mods = PetPersonalitySystem.get_bond_stat_modifiers(pet)
            hp_bonus = int(mods.get("hp_bonus", 0))
        except Exception:
            return

        last = int(getattr(pet, "_bond_applied_hp", 0))
        base_max_hp = int(getattr(pet, "max_hp", 0)) - last
        pet._bond_applied_hp = hp_bonus
        new_max = base_max_hp + hp_bonus
        if new_max > 0:
            pet.max_hp = new_max
        if int(getattr(pet, "hp", 0)) > int(getattr(pet, "max_hp", 0)):
            pet.hp = pet.max_hp
