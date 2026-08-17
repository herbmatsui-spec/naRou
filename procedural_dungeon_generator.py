"""
Procedural Dungeon Generator with Story Integration (Steps 54-59)
"""

from __future__ import annotations
import os
import yaml
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from entity import Entity


# Step 55: DungeonThemeData
@dataclass
class DungeonThemeData:
    """ダンジョンテーマデータ (Step 55)"""
    theme_id: str
    name: str = ""
    base_layout: str = "cavern"
    difficulty_modifier: float = 1.0
    enemy_pools: Dict[str, List[str]] = field(default_factory=dict)
    environmental_hazards: List[str] = field(default_factory=list)
    special_rooms: List[str] = field(default_factory=list)
    story_hooks: List[str] = field(default_factory=list)


# Step 56, 57: DungeonThemeRegistry
class DungeonThemeRegistry:
    """ダンジョンテーマレジストリ (Step 56, 57)"""
    _instance: Optional[DungeonThemeRegistry] = None

    def __new__(cls) -> DungeonThemeRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._themes = {}
        return cls._instance

    def load(self, file_path: str = "data/dungeon_themes.yaml") -> None:
        """YAMLからダンジョンテーマを読み込む (Step 57)"""
        self._themes = {}
        if not os.path.exists(file_path):
            self._themes["goblin_cave"] = DungeonThemeData(
                theme_id="goblin_cave", name="ゴブリンの洞窟"
            )
            return

        with open(file_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        t_dict = raw.get("dungeon_themes", {})
        for tid, tdata in t_dict.items():
            self._themes[tid] = DungeonThemeData(
                theme_id=tid,
                name=tdata.get("name", tid),
                base_layout=tdata.get("base_layout", "cavern"),
                difficulty_modifier=float(tdata.get("difficulty_modifier", 1.0)),
                enemy_pools=tdata.get("enemy_pools", {}),
                environmental_hazards=tdata.get("environmental_hazards", []),
                special_rooms=tdata.get("special_rooms", []),
                story_hooks=tdata.get("story_hooks", [])
            )

    def get(self, theme_id: str) -> Optional[DungeonThemeData]:
        return self._themes.get(theme_id)

    def all_themes(self) -> Dict[str, DungeonThemeData]:
        return dict(self._themes)


REGISTRY = DungeonThemeRegistry()


# Step 58, 59: ProceduralDungeonGenerator
class ProceduralDungeonGenerator:
    """プロシージャルダンジョン生成器 (Steps 58, 59)"""
    def __init__(self, registry: Optional[DungeonThemeRegistry] = None):
        self.registry = registry or REGISTRY

    def select_theme_by_story(self, player: "Entity") -> DungeonThemeData:
        """ストーリー状態に基づくテーマ選択 (Step 59)"""
        if player and player.story_flags.get("goblin_invasion_active"):
            t = self.registry.get("goblin_cave")
            if t: return t

        # デフォルトフォールバック
        all_t = list(self.registry.all_themes().values())
        return all_t[0] if all_t else DungeonThemeData(theme_id="default", name="通常迷宮")

    def generate_dungeon(self, player: "Entity", width: int = 40, height: int = 30) -> Dict[str, Any]:
        """ダンジョン生成スタブ"""
        theme = self.select_theme_by_story(player)
        return {
            "theme": theme,
            "width": width,
            "height": height
        }
