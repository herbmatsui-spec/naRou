"""
Skill Eater Phase 4: Concept Crystallization System (Steps 7-10)
同系統のスキル3つを消費して1つの「上位概念スキル（Concept）」に圧縮・統合し、持ち込み枠を節約する。
Phase 4 Extension: 概念結晶ドロップシステム (Steps 37-48)
"""

import random
from typing import Any, Dict, List

from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_exploration_system import ExplorationRank
from skill_eater_presentation_system import SkillEaterPresentationSystem


class ConceptCrystallizer:
    """
    概念結晶化マネージャー
    """

    # Phase 4 Step 37: ドロップテーブル定義
    DROP_TABLES: Dict[str, Dict[str, Any]] = {
        "first_floor_boss": {
            "base_rate": 0.15,  # 15%
            "depth_bonus_per_level": 0.005,  # 深度ごと+0.5%
            "rank_bonus_per_level": 0.05,  # ランクごと+5%
            "first_clear_bonus": 0.20,  # 初見クリア+20%
            "crystal_categories": [
                "Fire",
                "Ice",
                "Lightning",
                "Dark",
                "Holy",
                "Physical",
                "Arcane",
            ],
        },
        "secret_area": {
            "base_rate": 0.25,  # 25%
            "depth_bonus_per_level": 0.003,
            "rank_bonus_per_level": 0.05,
            "first_clear_bonus": 0.15,
            "crystal_categories": ["Shadow", "Illusion", "Space", "Time", "Mind", "Soul"],
        },
        "faction_boss": {
            "base_rate": 0.30,  # 30%
            "depth_bonus_per_level": 0.002,
            "rank_bonus_per_level": 0.03,
            "first_clear_bonus": 0.10,
            "crystal_categories": ["Order", "Chaos", "Wealth", "Knowledge", "Power", "Freedom"],
        },
        "deep_bounty": {
            "base_rate": 0.50,  # 50%
            "depth_bonus_per_level": 0.001,
            "rank_bonus_per_level": 0.02,
            "first_clear_bonus": 0.0,
            "crystal_categories": ["Void", "Genesis", "Absolute", "Origin", "End", "Infinity"],
        },
    }

    # ドロップ履歴
    drop_history: List[Dict[str, Any]] = []

    def __init__(self):
        self._audio: SkillEaterAudioSystem | None = None
        self._presentation: SkillEaterPresentationSystem | None = None

    def _get_presentation_systems(self):
        if self._audio is None:
            self._audio = SkillEaterAudioSystem.get_instance()
        if self._presentation is None:
            self._presentation = SkillEaterPresentationSystem.get_instance()
        return self._audio, self._presentation

    def crystallize_skills(
        self, category: str, skills_to_fuse: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Step 8, 9, 10: 3つのスキルを消費して1つの上位概念スキルを生成"""
        if len(skills_to_fuse) != 3:
            return {
                "success": False,
                "message": "Exactly 3 skills are required for Concept Crystallization.",
            }

        # カテゴリの一致チェック
        for s in skills_to_fuse:
            if category not in s.get("tags", []):
                return {
                    "success": False,
                    "message": f"All 3 skills must share the [{category}] tag.",
                }

        # パッシブ効果と威力の合算
        total_power = sum(s.get("power", 0) for s in skills_to_fuse)
        combined_passives = []
        for s in skills_to_fuse:
            if "passive" in s:
                combined_passives.append(s["passive"])

        concept_skill_name = f"Concept of Absolute {category} (純粋なる{category}の概念)"
        concept_skill = {
            "name": concept_skill_name,
            "category": category,
            "is_concept_crystal": True,
            "power": total_power + 100,  # 結晶化ボーナス
            "tags": [category, "Concept", "Mastery", "Inherited"],
            "passives": combined_passives,
            "description": f"Three {category} skills compressed into a singular world-defying concept.",
        }

        return {
            "success": True,
            "concept_skill": concept_skill,
            "message": f"CRYSTALLIZATION COMPLETE: Synthesized [{concept_skill_name}]!",
        }

    # Phase 4 Step 38: ドロップ判定メソッド
    def roll_concept_crystal_drop(
        self,
        category: str,
        depth: int,
        exploration_rank: ExplorationRank,
        is_first_clear: bool = False,
    ) -> Dict[str, Any] | None:
        """概念結晶ドロップ判定"""
        if category not in self.DROP_TABLES:
            return None

        table = self.DROP_TABLES[category]

        # 基礎ドロップ率計算
        rate = table["base_rate"]
        rate += depth * table["depth_bonus_per_level"]
        rate += exploration_rank.rank * table["rank_bonus_per_level"]
        if is_first_clear:
            rate += table["first_clear_bonus"]

        # 上限制限
        rate = min(0.95, rate)

        # 判定
        if random.random() > rate:
            return None

        # カテゴリからランダム選択
        crystal_category = random.choice(table["crystal_categories"])

        # 概念結晶生成
        crystal_name = f"Concept of {crystal_category} (純粋なる{crystal_category}の概念)"
        crystal = {
            "name": crystal_name,
            "category": crystal_category,
            "is_concept_crystal": True,
            "power": 100 + depth * 2 + exploration_rank.rank * 10,
            "tags": [crystal_category, "Concept", "Boss Drop", "Inherited"],
            "description": f"Dropped from {category} at depth {depth}.",
        }

        # 履歴記録
        self.drop_history.append(
            {
                "timestamp": __import__("time").time(),
                "category": category,
                "depth": depth,
                "crystal_name": crystal_name,
                "exploration_rank": exploration_rank.rank,
            }
        )

        return crystal

    # Phase 4 Step 39: 初見フロアボス討伐ドロップ
    def roll_first_floor_boss_drop(
        self,
        depth: int,
        exploration_rank: ExplorationRank,
        is_first_clear: bool = True,
    ) -> Dict[str, Any] | None:
        return self.roll_concept_crystal_drop(
            "first_floor_boss", depth, exploration_rank, is_first_clear
        )

    # Phase 4 Step 40: 秘密エリアクリアドロップ
    def roll_secret_area_drop(
        self,
        depth: int,
        exploration_rank: ExplorationRank,
        is_first_clear: bool = True,
    ) -> Dict[str, Any] | None:
        return self.roll_concept_crystal_drop(
            "secret_area", depth, exploration_rank, is_first_clear
        )

    # Phase 4 Step 41: 派閥ボス討伐ドロップ
    def roll_faction_boss_drop(
        self,
        depth: int,
        exploration_rank: ExplorationRank,
        is_first_clear: bool = False,
    ) -> Dict[str, Any] | None:
        return self.roll_concept_crystal_drop(
            "faction_boss", depth, exploration_rank, is_first_clear
        )

    # Phase 4 Step 42: 概念結晶ドロップ演出
    def _play_crystal_drop_effect(self, crystal_name: str) -> None:
        audio, presentation = self._get_presentation_systems()
        presentation.add_event(
            emote_file="emote_crystal.png",
            audio_file="crystal_resonance.ogg",
            message=f"概念結晶《{crystal_name}》を獲得！",
        )
        audio.play_sound("crystal_resonance.ogg")

    # Phase 4 Step 43: 自動合成オプション
    def auto_crystallize_if_possible(self, player: Any) -> List[Dict[str, Any]]:
        """所持スキルから同カテゴリ3つ揃っていれば自動合成提案"""
        # 簡易実装: プレイヤーのスキルをチェックして同カテゴリ3つ以上あるカテゴリを返す
        suggestions = []
        if not hasattr(player, "skills"):
            return suggestions

        skill_categories: Dict[str, List[str]] = {}
        for skill_id in player.skills.keys():
            # スキル定義からカテゴリ取得（簡易版）
            category = "Unknown"
            if "fire" in skill_id.lower():
                category = "Fire"
            elif "ice" in skill_id.lower() or "cold" in skill_id.lower():
                category = "Ice"
            elif "lightning" in skill_id.lower():
                category = "Lightning"
            elif "dark" in skill_id.lower() or "shadow" in skill_id.lower():
                category = "Dark"
            elif "holy" in skill_id.lower() or "light" in skill_id.lower():
                category = "Holy"

            if category not in skill_categories:
                skill_categories[category] = []
            skill_categories[category].append(skill_id)

        for category, skills in skill_categories.items():
            if len(skills) >= 3:
                suggestions.append(
                    {
                        "category": category,
                        "available_skills": skills[:3],
                        "message": f"カテゴリ[{category}]のスキルが3つ以上揃っています。概念結晶化可能です。",
                    }
                )

        return suggestions

    # Phase 4 Step 44: 探索ランクによるドロップ率補正（roll_concept_crystal_dropに統合済み）

    # Phase 4 Step 45: 概念結晶ドロップ履歴管理
    def get_drop_history(self) -> List[Dict[str, Any]]:
        return self.drop_history.copy()

    def clear_drop_history(self) -> None:
        self.drop_history.clear()

    # Phase 4 Step 46: ドロップ率表示（デバッグ/UI用）
    def get_drop_rates(self, depth: int, exploration_rank: ExplorationRank) -> Dict[str, float]:
        rates = {}
        for category, table in self.DROP_TABLES.items():
            rate = table["base_rate"]
            rate += depth * table["depth_bonus_per_level"]
            rate += exploration_rank.rank * table["rank_bonus_per_level"]
            rate += table["first_clear_bonus"]  # 初見時の最大値
            rates[category] = min(0.95, rate)
        return rates

    # Phase 4 Step 48: 音声ファイル存在確認・フォールバック
    def check_audio_files(self) -> Dict[str, bool]:
        """必要な音声ファイルの存在確認"""
        import os

        audio_dir = os.path.join(os.path.dirname(__file__), "assets", "audio")
        required_files = {
            "crystal_resonance.ogg": os.path.exists(
                os.path.join(audio_dir, "crystal_resonance.ogg")
            ),
            "rank_up_fanfare.ogg": os.path.exists(os.path.join(audio_dir, "rank_up_fanfare.ogg")),
            "ascension_node_unlock.ogg": os.path.exists(
                os.path.join(audio_dir, "ascension_node_unlock.ogg")
            ),
        }
        return required_files
