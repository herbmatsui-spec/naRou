"""
Reincarnation Challenge System Module (Steps 66-71)
"""

from __future__ import annotations
import os
import yaml
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from entity import Entity
    from game import Engine


# Step 67: ReincarnationChallengeData
@dataclass
class ReincarnationChallengeData:
    """転生チャレンジデータ (Step 67)"""
    id: str
    name: str = ""
    description: str = ""
    requirements: Dict[str, Any] = field(default_factory=dict)
    rewards: Dict[str, Any] = field(default_factory=dict)


# Step 68, 69: ReincarnationChallengeRegistry
class ReincarnationChallengeRegistry:
    """転生チャレンジレジストリ (Step 68, 69)"""
    _instance: Optional[ReincarnationChallengeRegistry] = None

    def __new__(cls) -> ReincarnationChallengeRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._challenges = {}
        return cls._instance

    def load(self, file_path: str = "data/reincarnation_challenges.yaml") -> None:
        """YAMLからチャレンジを読み込む (Step 69)"""
        self._challenges = {}
        if not os.path.exists(file_path):
            self._challenges["speed_ascension"] = ReincarnationChallengeData(
                id="speed_ascension", name="迅雷の転生", requirements={"turns_limit": 3000, "level_target": 50}
            )
            return

        with open(file_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        c_dict = raw.get("reincarnation_challenges", {})
        for cid, data in c_dict.items():
            self._challenges[cid] = ReincarnationChallengeData(
                id=cid,
                name=data.get("name", cid),
                description=data.get("description", ""),
                requirements=data.get("requirements", {}),
                rewards=data.get("rewards", {})
            )

    def get(self, c_id: str) -> Optional[ReincarnationChallengeData]:
        return self._challenges.get(c_id)

    def all(self) -> Dict[str, ReincarnationChallengeData]:
        return dict(self._challenges)


REGISTRY = ReincarnationChallengeRegistry()


# Step 70: ReincarnationChallengeManager
class ReincarnationChallengeManager:
    """チャレンジ進捗・達成管理 (Steps 70, 71)"""
    def __init__(self, registry: Optional[ReincarnationChallengeRegistry] = None):
        self.registry = registry or REGISTRY

    def update_challenge_progress(self, player: "Entity", challenge_key: str, amount: int = 1, engine: Optional[Any] = None) -> List[str]:
        """チャレンジ進捗を更新 (Step 70)"""
        cur = player.challenge_progress.get(challenge_key, 0)
        player.challenge_progress[challenge_key] = cur + amount
        return self.check_completions(player, engine)

    def check_completions(self, player: "Entity", engine: Optional[Any] = None) -> List[str]:
        """チャレンジ達成判定 (Step 70)"""
        completed = []
        for cid, cdata in self.registry.all().items():
            if player.challenge_progress.get(f"{cid}_completed", 0) > 0:
                continue

            req = cdata.requirements
            req_turns = req.get("turns_limit")
            req_lvl = req.get("level_target", 50)
            req_kill_max = req.get("kill_count_max")

            is_ok = True
            if req_turns is not None and getattr(player, "total_turns", 0) > req_turns:
                is_ok = False
            if player.level < req_lvl and req_lvl > 0:
                is_ok = False
            if req_kill_max is not None and sum(player.kill_counts.values()) > req_kill_max:
                is_ok = False

            if is_ok:
                player.challenge_progress[f"{cid}_completed"] = 1
                self.grant_rewards(player, cdata, engine)
                completed.append(cid)

        return completed

    def grant_rewards(self, player: "Entity", cdata: ReincarnationChallengeData, engine: Optional[Any] = None) -> None:
        """チャレンジ報酬付与 (Step 70)"""
        rew = cdata.rewards
        if rew.get("gold", 0) > 0:
            if hasattr(player, "gold"):
                player.gold += rew["gold"]
            if engine and hasattr(engine, "survival"):
                engine.survival.gold += rew["gold"]

        if rew.get("skill_points", 0) > 0:
            player.skill_points += rew["skill_points"]
            player.total_skill_points_earned += rew["skill_points"]

        if rew.get("title"):
            if rew["title"] not in player.titles:
                player.titles.append(rew["title"])

        if engine:
            from sound_manager import SoundManager
            SoundManager.play_se("level_up")
            engine.log(f"★チャレンジ達成！ 【{cdata.name}】の報酬を獲得！", (255, 215, 0))
