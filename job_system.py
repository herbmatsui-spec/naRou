"""
ジョブシステム (職業システム)
ジョブデータ管理・転職条件判定・ジョブ補正適用・ジョブレベルアップ
Steps 38-47
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, TYPE_CHECKING
import yaml
from pathlib import Path

if TYPE_CHECKING:
    from entity import Entity


@dataclass
class JobEffect:
    """ジョブ効果 (Step 39)"""
    type: str                                    # stat_modifier, unlock_skill, equipment_bonus 等
    value: Union[int, float, str]
    target: Optional[str] = None                # strength, magic, shield 等


@dataclass
class JobData:
    """ジョブマスターデータ (Step 40)"""
    id: str
    name: str
    tier: int = 0
    description: str = ""
    stat_modifiers: Dict[str, int] = field(default_factory=dict)
    equipment_restrictions: Dict[str, bool] = field(default_factory=dict)
    exclusive_skills: List[str] = field(default_factory=list)
    unlock_conditions: Dict[str, Any] = field(default_factory=dict)


class JobRegistry:
    """ジョブレジストリ (シングルトン) (Steps 41, 42)"""
    _instance: Optional['JobRegistry'] = None
    _jobs: Dict[str, JobData] = {}
    _loaded: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._jobs = {}
            cls._loaded = False
        return cls._instance

    def load(self, path: str = "data/jobs.yaml") -> None:
        """YAMLからジョブ定義をロード (Step 42)"""
        if self._loaded:
            return
        p = Path(path)
        if not p.exists():
            self._loaded = True
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            jobs_data = data.get('jobs', {})
            for job_id, j in jobs_data.items():
                job = JobData(
                    id=j.get('id', job_id),
                    name=j.get('name', job_id),
                    tier=j.get('tier', 0),
                    description=j.get('description', ''),
                    stat_modifiers=j.get('stat_modifiers') or {},
                    equipment_restrictions=j.get('equipment_restrictions') or {},
                    exclusive_skills=j.get('exclusive_skills') or [],
                    unlock_conditions=j.get('unlock_conditions') or {}
                )
                self._jobs[job.id] = job
            self._loaded = True
        except Exception:
            self._loaded = True

    def get(self, job_id: str) -> Optional[JobData]:
        """特定ジョブを取得 (Step 41)"""
        return self._jobs.get(job_id)

    def all(self) -> Dict[str, JobData]:
        """すべてのジョブ辞書を返す (Step 41)"""
        return self._jobs


REGISTRY = JobRegistry()


class JobManager:
    """ジョブ管理・転職マネージャー (Steps 43-47)"""

    def __init__(self, registry: Optional[JobRegistry] = None):
        self.registry = registry or REGISTRY

    def check_unlock_conditions(self, player: 'Entity', job_data: JobData) -> bool:
        """プレイヤーがジョブの解放条件を満たしているか判定 (Step 44)"""
        if not job_data:
            return False
        conds = job_data.unlock_conditions
        if not conds:
            return True

        # 1. 前提レベル
        if "level" in conds:
            if player.level < conds["level"]:
                return False

        # 2. 前提ジョブ
        if "job" in conds:
            req_job = conds["job"]
            if player.job != req_job and req_job not in getattr(player, 'previous_jobs', []) and req_job not in getattr(player, 'mastered_jobs', []):
                return False

        # 3. 前提スキル
        if "skills" in conds:
            for sk_name, req_lv in conds["skills"].items():
                # skills 辞書またはスキルツリー進捗をチェック
                sk_obj = player.skills.get(sk_name)
                current_lv = sk_obj.level if sk_obj else 0
                if current_lv < req_lv:
                    # スキルツリー習得フラグで判定
                    from skill_tree_system import REGISTRY as STR_REG
                    STR_REG.load()
                    learned = []
                    for tree_skills in getattr(player, 'skill_tree_progress', {}).values():
                        learned.extend(tree_skills)
                    if sk_name not in learned:
                        return False

        # 4. 前提ステータス
        if "stats" in conds:
            for stat_name, req_val in conds["stats"].items():
                if hasattr(player.attributes, stat_name):
                    val = getattr(player.attributes, stat_name)
                    if val < req_val:
                        return False

        return True

    def change_job(self, player: 'Entity', job_id: str) -> bool:
        """転職処理 (Step 45)"""
        job_data = self.registry.get(job_id)
        if not job_data:
            return False

        if player.job == job_id:
            return False

        if not self.check_unlock_conditions(player, job_data):
            return False

        # 現在のジョブを履歴に保存
        if player.job and player.job not in player.previous_jobs:
            player.previous_jobs.append(player.job)

        # ジョブレベルが一定以上（例: Lv10）ならマスター記録
        if player.job_level >= 10 and player.job not in player.mastered_jobs:
            player.mastered_jobs.append(player.job)

        # 転職
        player.job = job_id
        player.job_level = 1
        player.job_exp = 0

        # ステータス再計算 (Step 45, 49)
        self.apply_job_stats(player, job_data)
        player.recalculate_stats()
        return True

    def get_available_jobs(self, player: 'Entity') -> List[JobData]:
        """転職可能かつ解放条件を満たしているジョブ一覧を取得 (Step 46)"""
        available = []
        for job in self.registry.all().values():
            if job.id != player.job and self.check_unlock_conditions(player, job):
                available.append(job)
        return available

    def apply_job_stats(self, player: 'Entity', job_data: JobData) -> None:
        """ジョブのstat_modifiersを適用 (Step 47)"""
        if not job_data or not job_data.stat_modifiers:
            return
        # インターフェース定義
        # recalculate_stats 時に自動反映
        pass
