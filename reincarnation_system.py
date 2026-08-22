"""
輪廻転生システム
Phase 5: ニューゲーム+引継ぎシステム (Steps 49-60)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ReincarnationData:
    """転生データクラス"""

    id: str
    min_level: int
    max_level: int
    stat_bonus: int
    level_reset_multiplier: float
    name: str
    description: str


# Phase 5 Step 49: NewGamePlusData データクラス定義
@dataclass
class NewGamePlusData:
    """ニューゲーム+引継ぎデータ"""

    max_depth_reached: int = 0
    total_secrets_found: int = 0
    faction_reputations: Dict[str, int] = field(default_factory=dict)
    base_tier: int = 1
    exploration_rank: int = 1
    exploration_total_exp: int = 0
    ascension_nodes_unlocked: int = 0
    concept_crystals_owned: int = 0
    completed_bounties: int = 0
    reincarnation_count: int = 0
    total_level_earned: int = 0

    def to_dict(self) -> dict:
        return {
            "max_depth_reached": self.max_depth_reached,
            "total_secrets_found": self.total_secrets_found,
            "faction_reputations": self.faction_reputations,
            "base_tier": self.base_tier,
            "exploration_rank": self.exploration_rank,
            "exploration_total_exp": self.exploration_total_exp,
            "ascension_nodes_unlocked": self.ascension_nodes_unlocked,
            "concept_crystals_owned": self.concept_crystals_owned,
            "completed_bounties": self.completed_bounties,
            "reincarnation_count": self.reincarnation_count,
            "total_level_earned": self.total_level_earned,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NewGamePlusData":
        return cls(
            max_depth_reached=data.get("max_depth_reached", 0),
            total_secrets_found=data.get("total_secrets_found", 0),
            faction_reputations=data.get("faction_reputations", {}),
            base_tier=data.get("base_tier", 1),
            exploration_rank=data.get("exploration_rank", 1),
            exploration_total_exp=data.get("exploration_total_exp", 0),
            ascension_nodes_unlocked=data.get("ascension_nodes_unlocked", 0),
            concept_crystals_owned=data.get("concept_crystals_owned", 0),
            completed_bounties=data.get("completed_bounties", 0),
            reincarnation_count=data.get("reincarnation_count", 0),
            total_level_earned=data.get("total_level_earned", 0),
        )


class ReincarnationRegistry:
    """称号レジストリ（シングルトン的）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data: dict[str, ReincarnationData] = {}
        return cls._instance

    def load(self, path: str = "data/reincarnation.yaml") -> None:
        """YAMLファイルから転生データを読み込み"""
        self._data.clear()

        try:
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                if data and "reincarnation" in data:
                    # 基本要件を全転生データに適用
                    base_req = data["reincarnation"].get("base_requirements", {})

                    # デフォルト転生データを作成（実際のゲームでは複数の転生タイプがあるかもしれない）
                    default_data = ReincarnationData(
                        id="default",
                        min_level=base_req.get("min_level", 50),
                        max_level=base_req.get("max_level", 200),
                        stat_bonus=base_req.get("stat_bonus_per_reincarnation", 5),
                        level_reset_multiplier=base_req.get("level_reset_multiplier", 0.1),
                        name="輪廻転生",
                        description="一定レベルに到達すると転生が可能になる",
                    )
                    self._data["default"] = default_data
            else:
                # ファイルが存在しない場合のデフォルトデータ
                default_data = ReincarnationData(
                    id="default",
                    min_level=50,
                    max_level=200,
                    stat_bonus=5,
                    level_reset_multiplier=0.1,
                    name="輪廻転生",
                    description="一定レベルに到達すると転生が可能になる",
                )
                self._data["default"] = default_data

        except Exception as e:
            logger.warning("Error loading reincarnation data from yaml: %s", e)
            # エラー時のデフォルトデータ
            default_data = ReincarnationData(
                id="default",
                min_level=50,
                max_level=200,
                stat_bonus=5,
                level_reset_multiplier=0.1,
                name="輪廻転生",
                description="一定レベルに到達すると転生が可能になる",
            )
            self._data["default"] = default_data

    def all(self) -> dict[str, ReincarnationData]:
        """全転生データを取得"""
        return self._data.copy()

    def get(self, reincarnation_id: str) -> ReincarnationData | None:
        """特定の転生データを取得"""
        return self._data.get(reincarnation_id)


# グローバルレジストリインスタンス
REGISTRY = ReincarnationRegistry()


class ReincarnationManager:
    """転生管理クラス"""

    # Phase 5 Step 59: 引継ぎ上限・バランス調整パラメータ
    MAX_NG_PLUS_BONUS_CAP = 50
    NG_PLUS_DEPTH_BONUS_MULT = 1
    NG_PLUS_SECRET_BONUS_MULT = 2
    NG_PLUS_FACTION_BONUS_MULT = 5
    NG_PLUS_BASE_TIER_MULT = 1
    NG_PLUS_RANK_BONUS_MULT = 100
    NG_PLUS_ASCENSION_BONUS_MULT = 5
    NG_PLUS_CRYSTAL_BONUS_MULT = 10

    def __init__(self, registry: ReincarnationRegistry | None = None):
        self.registry = registry or REGISTRY

    def can_reincarnate(self, player: Any) -> bool:
        """転生可能かチェック"""
        # 基本的なレベルチェック
        reincarnation_data = self.registry.get("default")
        if not reincarnation_data:
            return False

        return (
            player.level >= reincarnation_data.min_level
            and player.level <= reincarnation_data.max_level
        )

    # Phase 5 Step 50: 引継ぎデータ収集メソッド
    def collect_new_game_plus_data(self, player: Any, engine: Any = None) -> NewGamePlusData:
        """各システムから引継ぎデータを収集"""
        ng_data = NewGamePlusData()

        # 最大到達深度
        ng_data.max_depth_reached = getattr(player, "max_dungeon_depth", 0)

        # 探索データ
        try:
            from skill_eater_exploration_system import SkillEaterExplorationSystem

            exploration = SkillEaterExplorationSystem.get_instance()
            if exploration:
                ng_data.total_secrets_found = exploration.exploration_rank.secret_rooms_found
                ng_data.exploration_rank = exploration.exploration_rank.rank
                ng_data.exploration_total_exp = exploration.exploration_rank.total_exp
        except Exception:
            pass

        # 派閥評価
        try:
            from skill_eater_economy_system import SkillEaterEconomySystem

            economy = (
                SkillEaterEconomySystem.get_instance()
                if hasattr(SkillEaterEconomySystem, "get_instance")
                else None
            )
            if economy:
                for faction_id, faction_state in economy.factions.items():
                    ng_data.faction_reputations[faction_id] = faction_state.reputation
        except Exception:
            pass

        # アジトティア（施設レベル合計）
        try:
            from skill_eater_economy_system import SkillEaterEconomySystem

            economy = (
                SkillEaterEconomySystem.get_instance()
                if hasattr(SkillEaterEconomySystem, "get_instance")
                else None
            )
            if economy:
                total_level = sum(f.level for f in economy.base_facilities.values())
                ng_data.base_tier = max(1, total_level // 3)
        except Exception:
            pass

        # アセンションノード解放数
        try:
            from skill_eater_ascension_board import AscensionBoard

            ascension = AscensionBoard.get_instance()
            if ascension:
                unlocked = sum(1 for n in ascension.exploration_nodes.values() if n["unlocked"])
                ng_data.ascension_nodes_unlocked = unlocked
        except Exception:
            pass

        # 概念結晶所持数
        try:
            # プレイヤーのスキルから概念結晶をカウント
            if hasattr(player, "skills"):
                crystal_count = sum(
                    1 for s in player.skills.values() if getattr(s, "is_concept_crystal", False)
                )
                ng_data.concept_crystals_owned = crystal_count
        except Exception:
            pass

        # 完了バウンティ数
        try:
            from skill_eater_bounty_system import MidasBountyManager

            bounty = (
                MidasBountyManager.get_instance()
                if hasattr(MidasBountyManager, "get_instance")
                else None
            )
            if bounty:
                ng_data.completed_bounties = bounty.defeated_count
        except Exception:
            pass

        # 転生回数・累計レベル
        ng_data.reincarnation_count = getattr(player, "reincarnation_count", 0)
        ng_data.total_level_earned = getattr(player, "total_level_earned", 0)

        return ng_data

    # Phase 5 Step 51: 引継ぎボーナス計算式
    def _calculate_ng_plus_bonuses(self, data: NewGamePlusData) -> Dict[str, Any]:
        """引継ぎボーナスを計算"""
        bonuses = {}

        # 最大深度ボーナス: depth // 10 → 初期ステータス上昇
        depth_bonus = min(
            self.MAX_NG_PLUS_BONUS_CAP, data.max_depth_reached // 10 * self.NG_PLUS_DEPTH_BONUS_MULT
        )
        bonuses["all_attributes"] = depth_bonus

        # 秘密発見数: count * 2 → 初期アイテム発見率上昇
        secret_bonus = min(
            self.MAX_NG_PLUS_BONUS_CAP, data.total_secrets_found * self.NG_PLUS_SECRET_BONUS_MULT
        )
        bonuses["item_find_rate"] = secret_bonus

        # 派閥関係: 友好度に応じて初期評価・ショップ割引
        total_faction_rep = sum(max(0, v) for v in data.faction_reputations.values())
        faction_bonus = min(
            self.MAX_NG_PLUS_BONUS_CAP, total_faction_rep // 10 * self.NG_PLUS_FACTION_BONUS_MULT
        )
        bonuses["faction_reputation_bonus"] = faction_bonus

        # アジトティア: 施設レベル → 初期施設レベル
        base_bonus = min(self.MAX_NG_PLUS_BONUS_CAP, data.base_tier * self.NG_PLUS_BASE_TIER_MULT)
        bonuses["base_facility_level"] = base_bonus

        # 探索ランク: ランク × 100 → 初期探索経験値
        rank_bonus = min(
            self.MAX_NG_PLUS_BONUS_CAP * 100, data.exploration_rank * self.NG_PLUS_RANK_BONUS_MULT
        )
        bonuses["starting_exploration_exp"] = rank_bonus

        # アセンション解放数: ノード数 × 5% → 永続ダメージボーナス
        ascension_bonus = min(
            0.5, data.ascension_nodes_unlocked * 0.05 * self.NG_PLUS_ASCENSION_BONUS_MULT / 100
        )
        bonuses["all_damage_multiplier"] = 1.0 + ascension_bonus

        # 概念結晶所持数: 個数 × 10 → 初期MP上昇
        crystal_bonus = min(
            self.MAX_NG_PLUS_BONUS_CAP * 10,
            data.concept_crystals_owned * self.NG_PLUS_CRYSTAL_BONUS_MULT,
        )
        bonuses["max_mp_bonus"] = crystal_bonus

        return bonuses

    # Phase 5 Step 52: 転生実行時の引継ぎ適用
    def apply_ng_plus_bonuses(self, player: Any, ng_data: NewGamePlusData) -> None:
        """ニューゲーム+ボーナスをプレイヤーに適用"""
        bonuses = self._calculate_ng_plus_bonuses(ng_data)

        # ステータス適用
        if hasattr(player, "attributes"):
            attr_bonus = bonuses.get("all_attributes", 0)
            if attr_bonus > 0:
                player.attributes.strength += attr_bonus
                player.attributes.endurance += attr_bonus
                player.attributes.dexterity += attr_bonus
                player.attributes.perception += attr_bonus
                player.attributes.learning += attr_bonus
                player.attributes.will += attr_bonus
                player.attributes.magic += attr_bonus
                player.attributes.charisma += attr_bonus

        # MP上昇
        mp_bonus = bonuses.get("max_mp_bonus", 0)
        if mp_bonus > 0 and hasattr(player, "max_mp"):
            player.max_mp += mp_bonus
            player.mp = min(player.mp, player.max_mp)

        # アイテム発見率等の特殊ボーナスはプレイヤーにフラグとして保存
        player.ng_plus_bonuses = bonuses

    # Phase 5 Step 53: 引継ぎ演出・音声
    def _play_ng_plus_fanfare(self, engine: Any = None) -> None:
        try:
            from skill_eater_audio_system import SkillEaterAudioSystem
            from skill_eater_presentation_system import SkillEaterPresentationSystem

            audio = SkillEaterAudioSystem.get_instance()
            presentation = SkillEaterPresentationSystem.get_instance()

            presentation.add_event(
                emote_file="emote_crown.png",
                audio_file="rank_up_fanfare.ogg",
                message="輪廻の記憶を継承した！ ニューゲーム+ボーナス適用！",
            )
            audio.play_sound("rank_up_fanfare.ogg")

            if engine and hasattr(engine, "log"):
                engine.log(
                    "★★★【輪廻転生】前世の記憶と力を引き継ぎ、新たな旅が始まる！", (255, 215, 0)
                )
        except Exception:
            pass

    def reincarnate(self, player: Any, engine: Any | None = None) -> bool:
        """転生を実行（Phase 5: NG+データ収集・ボーナス適用を追加）"""
        if not self.can_reincarnate(player):
            return False

        # 転生データを取得
        reincarnation_data = self.registry.get("default")
        if not reincarnation_data:
            return False

        # Phase 5 Step 50: NG+引継ぎデータ収集
        ng_data = self.collect_new_game_plus_data(player, engine)

        # 1. 前世の総括と動的記憶の欠片の生成・付与
        try:
            from meta_progression_system import MemoryFragmentGenerator, MetaProgressionManager

            frag = MemoryFragmentGenerator.generate(
                player=player,
                trigger_type="reincarnation",
                context={"reincarnation_count": player.reincarnation_count},
            )
            # メタ進行マネージャー経由で記憶を付与
            if engine and hasattr(engine, "meta_progression_manager"):
                engine.meta_progression_manager.add_memory_fragment(player, frag, engine)
            else:
                MetaProgressionManager().add_memory_fragment(player, frag, engine)
        except Exception as e:
            logger.warning("[ReincarnationManager] Memory fragment creation failed: %s", e)

        # 2. 次世代のランダム周回特異点・フラグの抽選
        try:
            from meta_progression_system import MetaProgressionManager

            mgr = (
                engine.meta_progression_manager
                if (engine and hasattr(engine, "meta_progression_manager"))
                else MetaProgressionManager()
            )
            mods = mgr.roll_cycle_modifiers(count=2)
            player.cycle_modifiers = mods
        except Exception as e:
            logger.warning("[ReincarnationManager] Cycle modifier rolling failed: %s", e)

        # 3. 転生処理
        player.reincarnation_count += 1
        if hasattr(player, "total_level_earned"):
            player.total_level_earned += player.level

        # レベルをリセット（初期レベル1に戻る）
        player.level = 1
        player.exp = 0
        if hasattr(player, "exp_next"):
            player.exp_next = 100

        # 4. 永続ボーナスの再計算とステータス初期化
        try:
            from meta_progression_system import MetaProgressionManager

            mgr = (
                engine.meta_progression_manager
                if (engine and hasattr(engine, "meta_progression_manager"))
                else MetaProgressionManager()
            )
            mgr.recalculate_and_apply_bonuses(player)
        except Exception as e:
            logger.warning("[ReincarnationManager] Bonus recalculation failed: %s", e)

        # Phase 5 Step 52: NG+ボーナス適用
        self.apply_ng_plus_bonuses(player, ng_data)

        # Phase 5 Step 53: 引継ぎ演出
        self._play_ng_plus_fanfare(engine)

        if engine and hasattr(engine, "log"):
            engine.log(
                f"★転生を実行した！ (転生回数: {player.reincarnation_count}, 累計レベル: {getattr(player, 'total_level_earned', 0)})",
                (255, 215, 0),
            )
            if player.cycle_modifiers:
                mod_names = "、".join(
                    [m.get("name", "") for m in player.cycle_modifiers if isinstance(m, dict)]
                )
                engine.log(f"⚡【運命の特異点】新たな時代の法則: {mod_names}", (150, 220, 255))
            # NG+ボーナス詳細ログ
            bonuses = self._calculate_ng_plus_bonuses(ng_data)
            for key, value in bonuses.items():
                engine.log(f"  引継ぎボーナス [{key}]: +{value}", (200, 255, 200))

        return True
