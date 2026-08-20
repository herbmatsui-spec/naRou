"""
NPC Relationship Simulation - Master-Disciple Relationship Mechanics
Step 10: Master-disciple relationship mechanics
"""

from __future__ import annotations

import logging
logger = logging.getLogger(__name__)
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .engine import RelationshipManager
from .models import InteractionType, RelationshipType


class MentorshipStage(Enum):
    """師弟関係の段階"""

    NONE = "none"  # 関係なし
    ACQUAINTANCE = "acquaintance"  # 知人（知識交換あり）
    APPRENTICE = "apprentice"  # 見習い
    DISCIPLE = "disciple"  # 弟子
    ADEPT = "adept"  # 熟練者
    JOURNEYMAN = "journeyman"  # 一人前
    MASTER = "master"  # 師範
    GRANDMASTER = "grandmaster"  # 大師範


class SkillTransferType(Enum):
    """スキル伝達タイプ"""

    BASIC = "basic"  # 基本スキル
    ADVANCED = "advanced"  # 上級スキル
    SECRET = "secret"  # 秘伝
    ULTIMATE = "ultimate"  # 奥義
    INHERITED = "inherited"  # 継承スキル


@dataclass
class MentorshipState:
    """師弟関係状態"""

    master_id: str
    disciple_id: str
    stage: MentorshipStage = MentorshipStage.NONE
    mentorship_level: int = 0  # 0〜100
    knowledge_transferred: list[str] = field(default_factory=list)
    skills_learned: list[str] = field(default_factory=list)
    loyalty: int = 50  # 0〜100
    wisdom_sharing_count: int = 0
    last_lesson: float | None = None
    mentorship_start: float | None = None
    flags: dict[str, bool] = field(default_factory=dict)


@dataclass
class SkillKnowledge:
    """スキル知識定義"""

    skill_id: str
    name: str
    transfer_type: SkillTransferType
    required_mentorship_level: int
    difficulty: int  # 0〜100
    prerequisites: list[str] = field(default_factory=list)


class MentorshipMechanics:
    """
    師弟関係メカニズム
    スキル伝承、知識共有、師弟関係特有のイベントを管理
    """

    def __init__(self, relationship_manager: RelationshipManager):
        self.rm = relationship_manager
        self.graph = relationship_manager.graph

        # 師弟関係のストレージ
        self.mentorship_states: dict[tuple[str, str], MentorshipState] = {}

        # スキル知識ベース
        self.skill_knowledge: dict[str, SkillKnowledge] = self._load_skill_knowledge()

        # 設定
        self._mentorship_config = self._load_mentorship_config()

        # イベントハンドラー
        self._event_handlers: dict[str, list[Callable[..., Any]]] = defaultdict(list)

        # 統計
        self._mentorship_stats = {
            "total_mentorships": 0,
            "completed_apprenticeships": 0,
            "masters_created": 0,
            "betrayals": 0,
        }

    def _load_skill_knowledge(self) -> dict[str, SkillKnowledge]:
        """スキル知識ベースをロード"""
        return {
            "basic_sword": SkillKnowledge(
                "basic_sword", "基本剣術", SkillTransferType.BASIC, 10, 10
            ),
            "advanced_sword": SkillKnowledge(
                "advanced_sword",
                "上級剣術",
                SkillTransferType.ADVANCED,
                30,
                30,
                ["basic_sword"],
            ),
            "secret_sword": SkillKnowledge(
                "secret_sword",
                "秘剣",
                SkillTransferType.SECRET,
                60,
                60,
                ["advanced_sword"],
            ),
            "ultimate_sword": SkillKnowledge(
                "ultimate_sword",
                "奥義・天剣",
                SkillTransferType.ULTIMATE,
                90,
                90,
                ["secret_sword"],
            ),
            "basic_magic": SkillKnowledge(
                "basic_magic", "基本魔法", SkillTransferType.BASIC, 10, 15
            ),
            "advanced_magic": SkillKnowledge(
                "advanced_magic",
                "上級魔法",
                SkillTransferType.ADVANCED,
                35,
                40,
                ["basic_magic"],
            ),
            "forbidden_magic": SkillKnowledge(
                "forbidden_magic",
                "禁呪",
                SkillTransferType.SECRET,
                65,
                80,
                ["advanced_magic"],
            ),
            "healing_art": SkillKnowledge(
                "healing_art", "治癒術", SkillTransferType.BASIC, 15, 20
            ),
            "resurrection": SkillKnowledge(
                "resurrection",
                "復活の術",
                SkillTransferType.ULTIMATE,
                95,
                95,
                ["healing_art"],
            ),
            "alchemy": SkillKnowledge(
                "alchemy", "錬金術", SkillTransferType.ADVANCED, 40, 50
            ),
            "crafting": SkillKnowledge(
                "crafting", "鍛冶術", SkillTransferType.BASIC, 20, 25
            ),
            "stealth": SkillKnowledge(
                "stealth", "隠密術", SkillTransferType.BASIC, 15, 30
            ),
            "leadership": SkillKnowledge(
                "leadership", "統率学", SkillTransferType.ADVANCED, 45, 45
            ),
            "diplomacy": SkillKnowledge(
                "diplomacy", "外交術", SkillTransferType.ADVANCED, 40, 40
            ),
        }

    def _load_mentorship_config(self) -> dict[str, Any]:
        """師弟関係設定をロード"""
        return {
            "apprentice_threshold": 20,  # 見習い開始のしきい値
            "disciple_threshold": 40,  # 弟子のしきい値
            "adept_threshold": 60,  # 熟練者のしきい値
            "journeyman_threshold": 75,  # 一人前のしきい値
            "master_threshold": 90,  # 師範のしきい値
            "knowledge_transfer_rate": 0.1,  # 知識伝達率
            "loyalty_decay": 0.0005,  # 忠誠の自然減衰
            "lesson_interval": 3600,  # レッスン間隔（秒）
        }

    def establish_mentorship(
        self,
        master_id: str,
        disciple_id: str,
        initial_stage: MentorshipStage = MentorshipStage.ACQUAINTANCE,
    ) -> MentorshipState | None:
        """師弟関係を確立"""
        # 既存の関係をチェック
        key = (master_id, disciple_id)
        if key in self.mentorship_states:
            return self.mentorship_states[key]

        # 関係レベルを取得
        mentorship_level = self.rm.get_relationship_level(
            master_id, disciple_id, RelationshipType.MENTORSHIP
        )

        # ステージを決定
        if mentorship_level >= self._mentorship_config["master_threshold"]:
            stage = MentorshipStage.MASTER
        elif mentorship_level >= self._mentorship_config["journeyman_threshold"]:
            stage = MentorshipStage.JOURNEYMAN
        elif mentorship_level >= self._mentorship_config["adept_threshold"]:
            stage = MentorshipStage.ADEPT
        elif mentorship_level >= self._mentorship_config["disciple_threshold"]:
            stage = MentorshipStage.DISCIPLE
        elif mentorship_level >= self._mentorship_config["apprentice_threshold"]:
            stage = MentorshipStage.APPRENTICE
        else:
            stage = initial_stage

        # 状態を作成
        state = MentorshipState(
            master_id=master_id,
            disciple_id=disciple_id,
            stage=stage,
            mentorship_level=mentorship_level,
            mentorship_start=time.time() if stage != MentorshipStage.NONE else None,
        )

        self.mentorship_states[key] = state
        self._mentorship_stats["total_mentorships"] += 1

        # イベント発行
        self._emit_mentorship_event("mentorship_established", state)

        return state

    def update_mentorship_stage(
        self, master_id: str, disciple_id: str
    ) -> MentorshipStage | None:
        """師弟ステージを更新"""
        key = (master_id, disciple_id)
        state = self.mentorship_states.get(key)
        if not state:
            return None

        old_stage = state.stage

        # レベルに基づいてステージを更新
        if state.mentorship_level >= self._mentorship_config["master_threshold"]:
            new_stage = MentorshipStage.MASTER
        elif state.mentorship_level >= self._mentorship_config["journeyman_threshold"]:
            new_stage = MentorshipStage.JOURNEYMAN
        elif state.mentorship_level >= self._mentorship_config["adept_threshold"]:
            new_stage = MentorshipStage.ADEPT
        elif state.mentorship_level >= self._mentorship_config["disciple_threshold"]:
            new_stage = MentorshipStage.DISCIPLE
        elif state.mentorship_level >= self._mentorship_config["apprentice_threshold"]:
            new_stage = MentorshipStage.APPRENTICE
        else:
            new_stage = MentorshipStage.ACQUAINTANCE

        # ステージ変化イベント
        if new_stage != old_stage:
            state.stage = new_stage

            if (
                new_stage == MentorshipStage.APPRENTICE
                and old_stage == MentorshipStage.ACQUAINTANCE
            ):
                self._mentorship_stats["completed_apprenticeships"] += 1
                self._emit_mentorship_event("apprenticeship_started", state)
            elif new_stage == MentorshipStage.MASTER:
                self._mentorship_stats["masters_created"] += 1
                self._emit_mentorship_event("master_recognized", state)

        return new_stage

    def teach_skill(
        self, master_id: str, disciple_id: str, skill_id: str
    ) -> dict[str, Any]:
        """スキルを教える"""
        # 師弟関係を確認
        state = self.establish_mentorship(master_id, disciple_id)
        if not state:
            return {"success": False, "reason": "no_mentorship"}

        # スキル知識を確認
        skill = self.skill_knowledge.get(skill_id)
        if not skill:
            return {"success": False, "reason": "unknown_skill"}

        # 前提条件をチェック
        for prereq in skill.prerequisites:
            if prereq not in state.skills_learned:
                return {
                    "success": False,
                    "reason": "prerequisites_not_met",
                    "missing": prereq,
                }

        # 師弟レベルが十分かチェック
        if state.mentorship_level < skill.required_mentorship_level:
            return {
                "success": False,
                "reason": "insufficient_mentorship_level",
                "required": skill.required_mentorship_level,
                "current": state.mentorship_level,
            }

        # 成功：スキルを伝授
        if skill_id not in state.skills_learned:
            state.skills_learned.append(skill_id)
            state.knowledge_transferred.append(skill_id)
            state.wisdom_sharing_count += 1
            state.last_lesson = time.time()

        # 関係を強化
        self.rm.modify_relationship(
            master_id, disciple_id, InteractionType.KNOWLEDGE_SHARE, 15
        )
        state.mentorship_level = self.rm.get_relationship_level(
            master_id, disciple_id, RelationshipType.MENTORSHIP
        )

        # ステージを更新
        self.update_mentorship_stage(master_id, disciple_id)

        # イベント発行
        self._emit_mentorship_event("skill_taught", state, skill_id=skill_id)

        return {
            "success": True,
            "skill": skill.name,
            "mentorship_level": state.mentorship_level,
            "stage": state.stage.value,
        }

    def learn_skill(
        self, disciple_id: str, master_id: str, skill_id: str, effort: int = 50
    ) -> dict[str, Any]:
        """スキルを学ぶ（弟子側のアクション）"""
        state = self.mentorship_states.get((master_id, disciple_id))
        if not state:
            return {"success": False, "reason": "no_mentorship"}

        # スキルが教えられているかチェック
        if skill_id not in state.knowledge_transferred:
            return {"success": False, "reason": "skill_not_offered"}

        # 学習成功率を計算
        skill = self.skill_knowledge[skill_id]
        base_rate = self._mentorship_config["knowledge_transfer_rate"]
        success_rate = base_rate * (1 + effort / 100.0) * (1 + state.loyalty / 200.0)

        import random

        success = random.random() < min(0.95, success_rate)

        if success:
            # 学習成功
            if skill_id not in state.skills_learned:
                state.skills_learned.append(skill_id)

            # 忠誠を増加
            state.loyalty = min(100, state.loyalty + 5)

            # 関係を強化
            self.rm.modify_relationship(
                master_id, disciple_id, InteractionType.KNOWLEDGE_SHARE, 10
            )

            return {"success": True, "skill": skill.name, "mastery": "learned"}
        else:
            # 学習失敗
            state.loyalty = max(0, state.loyalty - 2)
            return {
                "success": False,
                "reason": "learning_failed",
                "skill": skill.name,
                "retry_recommended": True,
            }

    def check_disciple_betrayal(
        self, master_id: str, disciple_id: str, betrayal_severity: int = 10
    ) -> dict[str, Any]:
        """弟子の裏切りをチェック・実行"""
        state = self.mentorship_states.get((master_id, disciple_id))
        if not state:
            return {"success": False, "reason": "no_mentorship"}

        # 忠誠度が低い場合、裏切りの可能性
        if state.loyalty <= 20:
            # 裏切り発生
            self._mentorship_stats["betrayals"] += 1
            state.flags["betrayed"] = True

            # 関係を大幅に悪化
            self.rm.modify_relationship(
                master_id, disciple_id, InteractionType.BETRAYAL, -betrayal_severity * 2
            )
            state.mentorship_level = self.rm.get_relationship_level(
                master_id, disciple_id, RelationshipType.MENTORSHIP
            )

            # ステージを下げる
            state.stage = MentorshipStage.NONE
            del self.mentorship_states[(master_id, disciple_id)]

            # イベント発行
            self._emit_mentorship_event("disciple_betrayed", state)

            return {
                "success": True,
                "betrayal_severity": betrayal_severity,
                "mentorship_level": state.mentorship_level,
            }

        return {
            "success": False,
            "reason": "loyalty_too_high",
            "loyalty": state.loyalty,
        }

    def protect_master(
        self, disciple_id: str, master_id: str, sacrifice_level: int = 50
    ) -> dict[str, Any]:
        """師を守る（弟子の行動）"""
        state = self.mentorship_states.get((master_id, disciple_id))
        if not state:
            return {"success": False, "reason": "no_mentorship"}

        # 忠誠を大幅に増加
        state.loyalty = min(100, state.loyalty + sacrifice_level // 2)

        # 関係を強化
        self.rm.modify_relationship(
            master_id, disciple_id, InteractionType.RESCUE, sacrifice_level
        )
        state.mentorship_level = self.rm.get_relationship_level(
            master_id, disciple_id, RelationshipType.MENTORSHIP
        )

        # ステージを更新
        self.update_mentorship_stage(master_id, disciple_id)

        # イベント発行
        self._emit_mentorship_event("master_protected", state)

        return {
            "success": True,
            "loyalty": state.loyalty,
            "mentorship_level": state.mentorship_level,
            "stage": state.stage.value,
        }

    def surpass_master(self, disciple_id: str, master_id: str) -> dict[str, Any]:
        """師を超える（弟子の成長）"""
        state = self.mentorship_states.get((master_id, disciple_id))
        if not state:
            return {"success": False, "reason": "no_mentorship"}

        # 条件：十分なスキルと関係レベル
        if len(state.skills_learned) < 5:
            return {"success": False, "reason": "insufficient_skills"}

        if state.mentorship_level < 70:
            return {"success": False, "reason": "insufficient_mentorship"}

        # 師弟関係を変更（対等な関係に）
        state.flags["surpassed"] = True
        state.stage = MentorshipStage.JOURNEYMAN

        # 相互の関係を強化（友人としても）
        self.rm.modify_relationship(
            master_id, disciple_id, InteractionType.EMOTIONAL_SUPPORT, 20
        )

        # イベント発行
        self._emit_mentorship_event("disciple_surpassed", state)

        return {
            "success": True,
            "stage": state.stage.value,
            "skills_learned": len(state.skills_learned),
        }

    def get_available_skills(
        self, master_id: str, disciple_id: str
    ) -> list[dict[str, Any]]:
        """弟子が学べる利用可能なスキルを取得"""
        state = self.mentorship_states.get((master_id, disciple_id))
        if not state:
            return []

        available = []
        for skill_id, skill in self.skill_knowledge.items():
            # 既に学習済みはスキップ
            if skill_id in state.skills_learned:
                continue

            # 前提条件をチェック
            prereq_met = all(
                prereq in state.skills_learned for prereq in skill.prerequisites
            )
            if not prereq_met:
                continue

            # 師弟レベルをチェック
            if state.mentorship_level < skill.required_mentorship_level:
                continue

            available.append(
                {
                    "skill_id": skill_id,
                    "name": skill.name,
                    "transfer_type": skill.transfer_type.value,
                    "difficulty": skill.difficulty,
                    "required_level": skill.required_mentorship_level,
                }
            )

        return available

    def register_mentorship_event_handler(
        self, event_type: str, handler: Callable[..., Any]
    ) -> None:
        """師弟イベントハンドラーを登録"""
        self._event_handlers[event_type].append(handler)

    def _emit_mentorship_event(
        self, event_type: str, state: MentorshipState, **kwargs: Any
    ) -> None:
        """師弟イベントを発行"""
        for handler in self._event_handlers.get(event_type, []):
            try:
                handler(event_type, state, **kwargs)
            except Exception as e:
                logger.exception("Unhandled exception")
                print(f"Error in mentorship event handler: {e}")

    def get_mentorship_state(
        self, master_id: str, disciple_id: str
    ) -> MentorshipState | None:
        """師弟状態を取得"""
        return self.mentorship_states.get((master_id, disciple_id))

    def get_active_mentorships(
        self, character_id: str | None = None, role: str = "either"
    ) -> list[MentorshipState]:
        """アクティブな師弟関係を取得"""
        if character_id is None:
            return list(self.mentorship_states.values())

        result = []
        for state in self.mentorship_states.values():
            if (
                role in ["master", "either"]
                and state.master_id == character_id
                or role in ["disciple", "either"]
                and state.disciple_id == character_id
            ):
                result.append(state)
        return result

    def get_mentorship_statistics(self) -> dict[str, Any]:
        """師弟関係統計を取得"""
        return self._mentorship_stats.copy()

    def serialize(self) -> dict[str, Any]:
        """師弟状態をシリアライズ"""
        return {
            "mentorship_states": {
                f"{m}_{d}": {
                    "master_id": state.master_id,
                    "disciple_id": state.disciple_id,
                    "stage": state.stage.value,
                    "mentorship_level": state.mentorship_level,
                    "knowledge_transferred": state.knowledge_transferred,
                    "skills_learned": state.skills_learned,
                    "loyalty": state.loyalty,
                    "wisdom_sharing_count": state.wisdom_sharing_count,
                    "last_lesson": state.last_lesson,
                    "mentorship_start": state.mentorship_start,
                    "flags": state.flags,
                }
                for (m, d), state in self.mentorship_states.items()
            },
            "stats": self._mentorship_stats,
        }

    def deserialize(self, data: dict[str, Any]) -> None:
        """師弟状態をデシリアライズ"""
        self.mentorship_states.clear()
        self._mentorship_stats = data.get("stats", self._mentorship_stats)

        for state_data in data.get("mentorship_states", {}).values():
            state = MentorshipState(
                master_id=state_data["master_id"],
                disciple_id=state_data["disciple_id"],
                stage=MentorshipStage(state_data["stage"]),
                mentorship_level=state_data["mentorship_level"],
                knowledge_transferred=state_data.get("knowledge_transferred", []),
                skills_learned=state_data.get("skills_learned", []),
                loyalty=state_data.get("loyalty", 50),
                wisdom_sharing_count=state_data.get("wisdom_sharing_count", 0),
                last_lesson=state_data.get("last_lesson"),
                mentorship_start=state_data.get("mentorship_start"),
                flags=state_data.get("flags", {}),
            )
            self.mentorship_states[(state.master_id, state.disciple_id)] = state
