"""
Dungeon Quest Feedback Module (偏執的クエストシステム / 設計書 Phase 5 Step 20)
生成結果フィードバック（実階層数・ボス座標→クエスト目的更新）。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from procedural_dungeon_generator import ProceduralDungeonGenerator


@dataclass
class DungeonGenerationFeedback:
    """ダンジョン生成フィードバック"""

    spec_id: str
    quest_id: str
    generated_floors: int
    floor_details: list[dict[str, Any]] = field(default_factory=list)
    boss_room_coords: dict[str, Any] | None = None
    boss_room_id: str = ""
    entrance_coords: dict[str, Any] | None = None
    exit_coords: dict[str, Any] | None = None
    total_rooms: int = 0
    total_traps: int = 0
    total_enemies: int = 0
    verification_passed: bool = True
    missing_requirements: list[str] = field(default_factory=list)


class DungeonQuestFeedback:
    """ダンジョン生成結果をクエスト目的へフィードバックする管理クラス"""

    def __init__(
        self,
        dungeon_generator: ProceduralDungeonGenerator,
    ):
        self.generator = dungeon_generator
        self._feedback_cache: dict[str, DungeonGenerationFeedback] = {}

    def process_generation_result(
        self,
        generated: dict[str, Any],
        spec_id: str,
        quest_id: str,
    ) -> DungeonGenerationFeedback:
        """生成結果を処理し、フィードバックオブジェクトを作成"""

        floors = generated.get("floors", [])
        len(floors)

        floor_details = []
        boss_room_coords = None
        boss_room_id = ""
        entrance_coords = None
        exit_coords = None
        total_rooms = 0
        total_traps = 0
        total_enemies = 0

        for floor in floors:
            floor_num = floor.get("floor_number", 0)
            rooms = floor.get("rooms", [])
            entrance = floor.get("entrance_pos")
            exit_pos = floor.get("exit_pos")

            if entrance and entrance_coords is None:
                entrance_coords = {
                    "floor": floor_num,
                    "x": entrance[0],
                    "y": entrance[1],
                }
            if exit_pos and exit_coords is None:
                exit_coords = {"floor": floor_num, "x": exit_pos[0], "y": exit_pos[1]}

            floor_room_count = len(rooms)
            total_rooms += floor_room_count

            floor_traps = 0
            floor_enemies = 0

            for room in rooms:
                # トラップ数
                traps = room.get("traps", [])
                floor_traps += len(traps)

                # 敵数
                enemies = room.get("enemies", [])
                floor_enemies += len(enemies)

                # ボス部屋チェック
                if room.get("is_boss_room") or room.get("room_type") == "BOSS":
                    boss_room_coords = {
                        "floor": floor_num,
                        "x": room.get("x", 0),
                        "y": room.get("y", 0),
                        "room_id": room.get("room_id", ""),
                    }
                    boss_room_id = room.get("room_id", "")

            total_traps += floor_traps
            total_enemies += floor_enemies

            floor_details.append(
                {
                    "floor_number": floor_num,
                    "room_count": floor_room_count,
                    "trap_count": floor_traps,
                    "enemy_count": floor_enemies,
                    "entrance": entrance,
                    "exit": exit_pos,
                }
            )

        # 検証結果取得
        verification_passed = True
        missing_requirements = []
        verification = generated.get("verification")
        if verification and hasattr(verification, "satisfied"):
            verification_passed = verification.satisfied
            missing_requirements = (
                verification.missing_required_rooms
                + verification.missing_required_traps
                + verification.missing_required_enemies
            )
            if verification.boss_room_missing:
                missing_requirements.append("boss_room_missing")
            if verification.floor_count_mismatch:
                missing_requirements.append("floor_count_mismatch")

        feedback = DungeonGenerationFeedback(
            spec_id=generated.get("spec_id", ""),
            quest_id=quest_id,
            generated_floors=generated.get("generated_floors", 0),
            floor_details=floor_details,
            boss_room_coords=boss_room_coords,
            boss_room_id=boss_room_id,
            entrance_coords=entrance_coords,
            exit_coords=exit_coords,
            total_rooms=total_rooms,
            total_traps=total_traps,
            total_enemies=total_enemies,
            verification_passed=verification_passed,
            missing_requirements=missing_requirements,
        )

        self._feedback_cache[spec_id] = feedback
        return feedback

    def update_quest_objectives(
        self,
        feedback: DungeonGenerationFeedback,
        quest_objectives: list[Any],  # QuestObjective リスト
        objective_mapping: dict[str, str],  # objective_id -> spec element id
    ) -> list[str]:
        """クエスト目的を生成結果に基づいて更新"""
        logs = []

        for obj in quest_objectives:
            if obj.objective_id not in objective_mapping:
                continue

            target_element = objective_mapping[obj.objective_id]

            # マッピング例:
            # "reach_boss" -> "boss_room_coords"
            # "explore_floors" -> "generated_floors"
            # "count_rooms" -> "total_rooms"
            # "find_entrance" -> "entrance_coords"
            # "defeat_boss" -> "boss_room_id"

            if target_element == "generated_floors":
                obj.current_count = min(
                    obj.required_count,
                    (
                        self._feedback_cache[obj.objective_id].generated_floors
                        if obj.objective_id in self._feedback_cache
                        else 0
                    ),
                )
                # または feedback から直接
                # 下で統一処理

        # 統一更新処理
        for obj in quest_objectives:
            if obj.objective_id not in objective_mapping:
                continue

            target = objective_mapping[obj.objective_id]

            if target == "generated_floors":
                obj.current_count = feedback.generated_floors
            elif target == "total_rooms":
                obj.current_count = feedback.total_rooms
            elif target == "total_traps":
                obj.current_count = feedback.total_traps
            elif target == "total_enemies":
                obj.current_count = feedback.total_enemies
            elif target == "boss_room_coords" and feedback.boss_room_coords:
                obj.current_count = 1  # 発見済み
            elif (
                target == "boss_room_id"
                and feedback.boss_room_id
                or target == "entrance_coords"
                and feedback.entrance_coords
                or target == "exit_coords"
                and feedback.exit_coords
            ):
                obj.current_count = 1

            # 完了判定
            if obj.current_count >= obj.required_count and not obj.is_completed:
                obj.is_completed = True
                logs.append(
                    f"【目的達成】{obj.description} ({obj.current_count}/{obj.required_count})"
                )

        return logs


class DungeonQuestPipeline:
    """ダンジョン同期クエスト生成パイプライン (Step 21)"""

    def __init__(
        self,
        dungeon_generator: ProceduralDungeonGenerator,
    ):
        self.generator = dungeon_generator
        self.feedback_processor = DungeonQuestFeedback(dungeon_generator)

    def generate_synced_quest_dungeon(
        self,
        spec_id: str,
        quest_id: str,
        player: Any,
        objective_mapping: dict[str, str],
    ) -> dict[str, Any]:
        """仕様に基づくダンジョン生成 + クエスト目的同期"""

        # 仕様読み込み（簡易版: キャッシュまたはYAMLから）
        spec = self._load_spec(spec_id)
        if not spec:
            raise ValueError(f"Spec {spec_id} not found")

        spec.quest_id = quest_id

        # 生成実行
        generated = self.generator.generate_from_spec(spec)

        # フィードバック処理
        feedback = self.feedback_processor.process_generation_result(generated, spec_id, quest_id)

        return {
            "generated": generated,
            "feedback": feedback,
        }

    def _load_spec(self, spec_id: str):
        """仕様読み込み（簡易版）"""
        # デフォルトスペックのハードコードフォールバック
        if spec_id == "default_dungeon":
            from quest_dungeon_spec import DungeonSpec, FloorSpec

            return DungeonSpec(
                spec_id="default_dungeon",
                name="標準ダンジョン",
                min_floors=3,
                max_floors=5,
                width=60,
                height=60,
                floor_specs=[
                    FloorSpec(floor_number=1, min_rooms=3, max_rooms=5),
                    FloorSpec(floor_number=2, min_rooms=3, max_rooms=5),
                    FloorSpec(floor_number=3, min_rooms=2, max_rooms=4, is_boss_floor=True),
                ],
            )
        # YAMLから読み込みを試みる
        try:
            import os

            import yaml

            spec_path = "data/quest_dungeon_specs.yaml"
            if os.path.exists(spec_path):
                with open(spec_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                spec_data = data.get("dungeon_specs", {}).get(spec_id)
                if spec_data:
                    from quest_dungeon_spec import build_dungeon_spec_from_yaml

                    return build_dungeon_spec_from_yaml(spec_data)
        except Exception:
            logger.exception("Unhandled exception")
            # TODO: handle exception properly
            pass
        return None


def create_dungeon_synced_quest(
    spec_id: str,
    quest_id: str,
    title: str,
    description: str,
    objective_mapping: dict[str, str],
) -> dict[str, Any]:
    """ダンジョン同期クエスト定義を作成（プロシージャル生成用）"""
    return {
        "quest_id": quest_id,
        "title": title,
        "description": description,
        "source_type": "dungeon_synced",
        "dungeon_spec_id": spec_id,
        "objective_mapping": objective_mapping,
    }


__all__ = [
    "DungeonGenerationFeedback",
    "DungeonQuestFeedback",
    "DungeonQuestPipeline",
    "create_dungeon_synced_quest",
]
