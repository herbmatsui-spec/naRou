"""
NPC Relationship Simulation - Romance Relationship Mechanics
Step 9: Romance relationship mechanics
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from .engine import RelationshipManager
from .models import InteractionType, RelationshipType


class RomanceStage(Enum):
    """恋愛関係の進行段階"""

    STRANGERS = "strangers"  # 他人
    ACQUAINTANCES = "acquaintances"  # 知人
    FRIENDS = "friends"  # 友人
    CLOSE_FRIENDS = "close_friends"  # 親友
    ADMIRERS = "admirers"  # 好意を持つ
    DATING = "dating"  # 交際中
    COMMITTED = "committed"  # 真剣な関係
    ENGAGED = "engaged"  # 婚約
    MARRIED = "married"  # 結婚
    SOULMATES = "soulmates"  # 運命の人


class RomanceEventType(Enum):
    """恋愛関連イベントタイプ"""

    FIRST_MEETING = "first_meeting"
    CONFESSION = "confession"
    FIRST_DATE = "first_date"
    ANNIVERSARY = "anniversary"
    JEALOUSY = "jealousy"
    ARGUMENT = "argument"
    BREAKUP = "breakup"
    RECONCILIATION = "reconciliation"
    PROPOSAL = "proposal"
    WEDDING = "wedding"
    CHEATING = "cheating"
    REUNION = "reunion"


@dataclass
class RomanceState:
    """恋愛状態"""

    couple_id: tuple[str, str]  # (character_a, character_b)
    stage: RomanceStage = RomanceStage.STRANGERS
    romance_level: int = 0  # -100〜+100
    compatibility: float = 0.5  # 0.0〜1.0
    commitment_level: int = 0  # 0〜100
    jealousy_level: int = 0  # 0〜100
    trust_level: int = 50  # 0〜100
    last_interaction: float = field(default_factory=time.time)
    relationship_start: float | None = None
    memories: list[dict[str, Any]] = field(default_factory=list)
    flags: dict[str, bool] = field(default_factory=dict)


class RomanceMechanics:
    """
    ロマンス関係メカニズム
    好感度からロマンスへの転換、三角関係、別れ等を管理
    """

    def __init__(self, relationship_manager: RelationshipManager):
        self.rm = relationship_manager
        self.graph = relationship_manager.graph

        # 恋愛状態のストレージ
        self.romance_states: dict[tuple[str, str], RomanceState] = {}

        # 恋愛可能性パラメータ
        self._romance_config = self._load_romance_config()

        # イベントハンドラー
        self._event_handlers: dict[RomanceEventType, list[Callable[..., Any]]] = defaultdict(list)

        # 統計
        self._romance_stats = {
            "total_romances": 0,
            "successful_marriages": 0,
            "breakups": 0,
            "love_triangles": 0,
        }

    def _load_romance_config(self) -> dict[str, Any]:
        """ロマンス設定をロード"""
        return {
            "confession_threshold": 60,  # 告白に必要なロマンスレベル
            "dating_threshold": 40,  # 交際開始のしきい値
            "commitment_threshold": 70,  # 真剣な関係のしきい値
            "marriage_threshold": 90,  # 結婚のしきい値
            "compatibility_base": 0.5,  # 基本相性
            "jealousy_threshold": 50,  # 嫉妬発動のしきい値
            "breakup_threshold": -30,  # 別れのしきい値
            "trust_decay": 0.001,  # 信頼の自然減衰
            "romance_decay": 0.002,  # ロマンスの自然減衰
        }

    def calculate_compatibility(self, char_a: str, char_b: str) -> float:
        """二人のキャラクター間の相性を計算"""
        node_a = self.graph.get_node(char_a)
        node_b = self.graph.get_node(char_b)

        if not node_a or not node_b:
            return self._romance_config["compatibility_base"]

        # パーソナリティの類似性に基づく相性計算
        traits_a = node_a.personality_traits
        traits_b = node_b.personality_traits

        if not traits_a or not traits_b:
            return self._romance_config["compatibility_base"]

        # 共通の特性について距離を計算
        similarity = 0.0
        common_traits = 0
        for trait, value_a in traits_a.items():
            if trait in traits_b:
                # 特性値の差（0に近いほど類似）
                diff = abs(value_a - traits_b[trait])
                similarity += 1.0 - diff
                common_traits += 1

        if common_traits == 0:
            return self._romance_config["compatibility_base"]

        base_similarity = similarity / common_traits

        # 対立する特性（例：外向性vs内向性）による修正
        compatibility = base_similarity * 0.8 + 0.2  # 0.2-1.0の範囲

        return max(0.0, min(1.0, compatibility))

    def initiate_romance(self, char_a: str, char_b: str) -> RomanceState | None:
        """二人の間でロマンスを開始"""
        # 既存の状態をチェック
        couple_key = tuple(sorted([char_a, char_b]))
        if couple_key in self.romance_states:
            return self.romance_states[couple_key]

        # 現在の関係レベルを取得
        romance_level = self.rm.get_relationship_level(char_a, char_b, RelationshipType.ROMANCE)
        favorability = self.rm.get_relationship_level(char_a, char_b, RelationshipType.FAVORABILITY)

        # 初期ステージを決定
        if romance_level >= self._romance_config["dating_threshold"]:
            initial_stage = RomanceStage.DATING
        elif romance_level >= 20:
            initial_stage = RomanceStage.ADMIRERS
        elif favorability >= 40:
            initial_stage = RomanceStage.CLOSE_FRIENDS
        elif favorability >= 20:
            initial_stage = RomanceStage.FRIENDS
        else:
            initial_stage = RomanceStage.ACQUAINTANCES

        # 相性を計算
        compatibility = self.calculate_compatibility(char_a, char_b)

        # ロマンス状態を作成
        state = RomanceState(
            couple_id=couple_key,
            stage=initial_stage,
            romance_level=romance_level,
            compatibility=compatibility,
            relationship_start=(
                time.time()
                if initial_stage in [RomanceStage.DATING, RomanceStage.COMMITTED]
                else None
            ),
        )

        self.romance_states[couple_key] = state
        self._romance_stats["total_romances"] += 1

        # イベントを発行
        self._emit_romance_event(RomanceEventType.FIRST_MEETING, state)

        return state

    def update_romance_stage(self, char_a: str, char_b: str) -> RomanceStage | None:
        """ロマンスステージを現在の状態に基づいて更新"""
        couple_key = tuple(sorted([char_a, char_b]))
        state = self.romance_states.get(couple_key)
        if not state:
            return None

        old_stage = state.stage
        new_stage = old_stage

        # ロマンスレベルとコミットメントに基づいてステージを更新
        if (
            state.romance_level >= self._romance_config["marriage_threshold"]
            and state.commitment_level >= 80
        ):
            new_stage = RomanceStage.MARRIED
        elif (
            state.romance_level >= self._romance_config["commitment_threshold"]
            and state.commitment_level >= 50
        ):
            new_stage = RomanceStage.ENGAGED
        elif state.romance_level >= self._romance_config["commitment_threshold"]:
            new_stage = RomanceStage.COMMITTED
        elif state.romance_level >= self._romance_config["dating_threshold"]:
            new_stage = RomanceStage.DATING
        elif state.romance_level >= 20:
            new_stage = RomanceStage.ADMIRERS
        elif state.romance_level < self._romance_config["breakup_threshold"]:
            new_stage = RomanceStage.STRANGERS

        # ステージが変化した場合
        if new_stage != old_stage:
            state.stage = new_stage

            # ステージ変化イベントを発行
            if new_stage == RomanceStage.DATING and old_stage != RomanceStage.DATING:
                self._emit_romance_event(RomanceEventType.FIRST_DATE, state)
                if state.relationship_start is None:
                    state.relationship_start = time.time()
            elif new_stage == RomanceStage.MARRIED:
                self._emit_romance_event(RomanceEventType.WEDDING, state)
                self._romance_stats["successful_marriages"] += 1
            elif new_stage == RomanceStage.STRANGERS and old_stage != RomanceStage.STRANGERS:
                self._emit_romance_event(RomanceEventType.BREAKUP, state)
                self._romance_stats["breakups"] += 1

        return new_stage

    def can_confess(self, char_a: str, char_b: str) -> bool:
        """告白可能かチェック"""
        romance_level = self.rm.get_relationship_level(char_a, char_b, RelationshipType.ROMANCE)
        favorability = self.rm.get_relationship_level(char_a, char_b, RelationshipType.FAVORABILITY)

        return romance_level >= self._romance_config["confession_threshold"] and favorability >= 30

    def confess(self, char_a: str, char_b: str, confession_type: str = "sincere") -> dict[str, Any]:
        """告白を実行"""
        if not self.can_confess(char_a, char_b):
            return {"success": False, "reason": "insufficient_romance_level"}

        # ロマンス状態を初期化（まだの場合）
        state = self.initiate_romance(char_a, char_b)

        # パーソナリティによる成功確率を計算
        success_prob = self._calculate_confession_success(char_a, char_b, confession_type)

        # 成功の決定
        success = random.random() < success_prob

        if success:
            # 関係を強化
            self.rm.modify_relationship(char_a, char_b, InteractionType.CONFESSION, 20)
            state.romance_level = self.rm.get_relationship_level(
                char_a, char_b, RelationshipType.ROMANCE
            )
            state.stage = RomanceStage.DATING
            state.relationship_start = time.time()
            state.flags["confessed"] = True

            # イベント発行
            self._emit_romance_event(RomanceEventType.CONFESSION, state)

            return {
                "success": True,
                "romance_level": state.romance_level,
                "stage": state.stage.value,
            }
        else:
            # 関係を弱める（拒絶）
            self.rm.modify_relationship(char_a, char_b, InteractionType.CONFESSION, -10)
            state.romance_level = self.rm.get_relationship_level(
                char_a, char_b, RelationshipType.ROMANCE
            )

            return {
                "success": False,
                "romance_level": state.romance_level,
                "stage": state.stage.value,
                "reason": "rejected",
            }

    def _calculate_confession_success(
        self, char_a: str, char_b: str, confession_type: str
    ) -> float:
        """告白の成功確率を計算"""
        # 基本確率
        base_prob = 0.5

        # ロマンスレベルによる調整
        romance_level = self.rm.get_relationship_level(char_a, char_b, RelationshipType.ROMANCE)
        romance_factor = max(0, (romance_level - 50) / 100.0)  # 0.0-0.5
        base_prob += romance_factor

        # 相性による調整
        compatibility = self.calculate_compatibility(char_a, char_b)
        base_prob += (compatibility - 0.5) * 0.3  # -0.15-0.15

        # 告白タイプによる調整
        type_modifiers = {
            "sincere": 0.1,
            "casual": -0.1,
            "public": 0.05,
            "private": 0.0,
            "grand_gesture": 0.15,
        }
        base_prob += type_modifiers.get(confession_type, 0.0)

        # パーソナリティによる調整（受け手の開放性）
        node_b = self.graph.get_node(char_b)
        if node_b and "openness" in node_b.personality_traits:
            base_prob += (node_b.personality_traits["openness"] - 0.5) * 0.2

        return max(0.05, min(0.95, base_prob))

    def check_jealousy(self, char_a: str, char_b: str, third_party: str) -> dict[str, Any]:
        """嫉妬をチェック（三角関係）"""
        # char_a と char_b がロマンス関係
        couple_key = tuple(sorted([char_a, char_b]))
        state = self.romance_states.get(couple_key)
        if not state:
            return {"jealousy": False}

        # third_party と char_a の関係をチェック
        third_romance = self.rm.get_relationship_level(
            char_a, third_party, RelationshipType.ROMANCE
        )
        third_favorability = self.rm.get_relationship_level(
            char_a, third_party, RelationshipType.FAVORABILITY
        )

        # 嫉妬の条件
        if third_romance >= 30 or third_favorability >= 50:
            state.jealousy_level = min(100, state.jealousy_level + 20)

            if state.jealousy_level >= self._romance_config["jealousy_threshold"]:
                self._romance_stats["love_triangles"] += 1
                self._emit_romance_event(RomanceEventType.JEALOUSY, state)

                return {
                    "jealousy": True,
                    "level": state.jealousy_level,
                    "third_party": third_party,
                    "effect": self._apply_jealousy_effects(char_a, char_b, third_party),
                }

        return {"jealousy": False}

    def _apply_jealousy_effects(self, char_a: str, char_b: str, third_party: str) -> dict[str, int]:
        """嫉妬の効果を適用"""
        effects = {}

        # char_b の char_a への信頼を減少
        self.rm.modify_relationship(char_b, char_a, InteractionType.ARGUMENT, -5)
        effects["trust_reduction"] = -5

        # char_b の third_party への敵意を増加
        self.rm.modify_relationship(char_b, third_party, InteractionType.COMBAT_ENEMY, -10)
        effects["enmity_increase"] = -10

        return effects

    def break_up(self, char_a: str, char_b: str, reason: str = "drifted_apart") -> dict[str, Any]:
        """別れを実行"""
        couple_key = tuple(sorted([char_a, char_b]))
        state = self.romance_states.get(couple_key)
        if not state:
            return {"success": False, "reason": "no_romance"}

        # 関係を悪化
        self.rm.modify_relationship(char_a, char_b, InteractionType.BETRAYAL, -30)
        self.rm.modify_relationship(char_a, char_b, InteractionType.ARGUMENT, -15)

        # ステータス更新
        state.romance_level = self.rm.get_relationship_level(
            char_a, char_b, RelationshipType.ROMANCE
        )
        state.stage = RomanceStage.STRANGERS
        state.flags["broken_up"] = True
        state.relationship_start = None

        # 統計更新
        self._romance_stats["breakups"] += 1

        # イベント発行
        self._emit_romance_event(RomanceEventType.BREAKUP, state)

        return {
            "success": True,
            "romance_level": state.romance_level,
            "stage": state.stage.value,
            "reason": reason,
        }

    def reconcile(self, char_a: str, char_b: str) -> dict[str, Any]:
        """よりを戻す"""
        couple_key = tuple(sorted([char_a, char_b]))
        state = self.romance_states.get(couple_key)
        if not state:
            return {"success": False, "reason": "no_history"}

        # 関係を改善
        self.rm.modify_relationship(char_a, char_b, InteractionType.EMOTIONAL_SUPPORT, 25)

        state.romance_level = self.rm.get_relationship_level(
            char_a, char_b, RelationshipType.ROMANCE
        )
        state.flags["reconciled"] = True

        # ステージを再評価
        new_stage = self.update_romance_stage(char_a, char_b)

        # イベント発行
        self._emit_romance_event(RomanceEventType.RECONCILIATION, state)

        return {
            "success": True,
            "romance_level": state.romance_level,
            "stage": new_stage.value if new_stage else state.stage.value,
        }

    def propose_marriage(self, char_a: str, char_b: str) -> dict[str, Any]:
        """プロポーズを実行"""
        couple_key = tuple(sorted([char_a, char_b]))
        state = self.romance_states.get(couple_key)
        if not state:
            return {"success": False, "reason": "no_romance"}

        # 条件チェック
        if state.romance_level < self._romance_config["marriage_threshold"]:
            return {"success": False, "reason": "insufficient_romance"}

        if state.commitment_level < 80:
            return {"success": False, "reason": "insufficient_commitment"}

        # 成功
        state.stage = RomanceStage.ENGAGED
        state.flags["engaged"] = True

        # 関係を強化
        self.rm.modify_relationship(char_a, char_b, InteractionType.CONFESSION, 15)

        # イベント発行
        self._emit_romance_event(RomanceEventType.PROPOSAL, state)

        return {
            "success": True,
            "stage": state.stage.value,
            "romance_level": state.romance_level,
        }

    def calculate_anniversary_bonus(self, char_a: str, char_b: str) -> dict[str, Any]:
        """記念日ボーナスを計算・適用"""
        couple_key = tuple(sorted([char_a, char_b]))
        state = self.romance_states.get(couple_key)
        if not state or state.relationship_start is None:
            return {"success": False, "reason": "no_relationship"}

        # 経過時間を計算（年単位、ゲーム内時間）
        elapsed = time.time() - state.relationship_start
        years = elapsed / (365 * 24 * 3600)  # ゲーム内年

        # 記念日チェック（1年ごと）
        if years >= 1.0:
            anniversary_count = int(years)

            # ボーナス適用
            bonus_amount = min(20, anniversary_count * 5)
            self.rm.modify_relationship(
                char_a, char_b, InteractionType.EMOTIONAL_SUPPORT, bonus_amount
            )

            state.romance_level = self.rm.get_relationship_level(
                char_a, char_b, RelationshipType.ROMANCE
            )

            # イベント発行
            self._emit_romance_event(RomanceEventType.ANNIVERSARY, state)

            return {
                "success": True,
                "anniversary_count": anniversary_count,
                "bonus_amount": bonus_amount,
                "romance_level": state.romance_level,
            }

        return {"success": False, "reason": "not_anniversary"}

    def register_romance_event_handler(
        self, event_type: RomanceEventType, handler: Callable[..., Any]
    ) -> None:
        """ロマンスイベントハンドラーを登録"""
        self._event_handlers[event_type].append(handler)

    def _emit_romance_event(self, event_type: RomanceEventType, state: RomanceState) -> None:
        """ロマンスイベントを発行"""
        for handler in self._event_handlers.get(event_type, []):
            try:
                handler(event_type, state)
            except Exception as e:
                logger.exception("Unhandled exception")
                print(f"Error in romance event handler: {e}")

    def get_romance_state(self, char_a: str, char_b: str) -> RomanceState | None:
        """ロマンス状態を取得"""
        couple_key = tuple(sorted([char_a, char_b]))
        return self.romance_states.get(couple_key)

    def get_active_romances(self, character_id: str | None = None) -> list[RomanceState]:
        """アクティブなロマンスを取得"""
        if character_id is None:
            return [
                state
                for state in self.romance_states.values()
                if state.stage not in [RomanceStage.STRANGERS]
            ]

        return [
            state
            for state in self.romance_states.values()
            if character_id in state.couple_id and state.stage not in [RomanceStage.STRANGERS]
        ]

    def get_romance_statistics(self) -> dict[str, Any]:
        """ロマンス統計を取得"""
        return self._romance_stats.copy()

    def serialize(self) -> dict[str, Any]:
        """ロマンス状態をシリアライズ"""
        return {
            "romance_states": {
                f"{a}_{b}": {
                    "couple_id": [a, b],
                    "stage": state.stage.value,
                    "romance_level": state.romance_level,
                    "compatibility": state.compatibility,
                    "commitment_level": state.commitment_level,
                    "jealousy_level": state.jealousy_level,
                    "trust_level": state.trust_level,
                    "last_interaction": state.last_interaction,
                    "relationship_start": state.relationship_start,
                    "memories": state.memories,
                    "flags": state.flags,
                }
                for (a, b), state in self.romance_states.items()
            },
            "stats": self._romance_stats,
        }

    def deserialize(self, data: dict[str, Any]) -> None:
        """ロマンス状態をデシリアライズ"""
        self.romance_states.clear()
        self._romance_stats = data.get("stats", self._romance_stats)

        for state_data in data.get("romance_states", {}).values():
            couple_id = tuple(state_data["couple_id"])
            state = RomanceState(
                couple_id=couple_id,
                stage=RomanceStage(state_data["stage"]),
                romance_level=state_data["romance_level"],
                compatibility=state_data["compatibility"],
                commitment_level=state_data["commitment_level"],
                jealousy_level=state_data["jealousy_level"],
                trust_level=state_data["trust_level"],
                last_interaction=state_data.get("last_interaction", time.time()),
                relationship_start=state_data.get("relationship_start"),
                memories=state_data.get("memories", []),
                flags=state_data.get("flags", {}),
            )
            self.romance_states[couple_id] = state
