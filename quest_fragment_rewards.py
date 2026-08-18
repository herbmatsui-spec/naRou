"""
Quest Fragment Rewards Module (偏執的クエストシステム / 設計書 Phase 7 Step 25)
クエスト完了→記憶断片ドロップテーブル。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import random


@dataclass
class FragmentDrop:
    """単一の断片ドロップ定義"""
    fragment_id: str
    min_count: int = 1
    max_count: int = 1
    weight: int = 100  # ドロップウェイト（高いほど出やすい）
    required_flags: List[str] = field(default_factory=list)
    forbidden_flags: List[str] = field(default_factory=list)


@dataclass
class FragmentDropTable:
    """記憶断片ドロップテーブル"""
    table_id: str
    quest_id: str  # 関連するクエストID
    drops: List[FragmentDrop] = field(default_factory=list)
    default_drop: Optional[FragmentDrop] = None  # デフォルトドロップ（マッチしない場合）

    def drop_fragments(self, player_flags: Optional[List[str]] = None) -> List[str]:
        """プレイヤーのフラグに基づいて断片をドロップ"""
        player_flags = player_flags or []
        pool: List[FragmentDrop] = []
        for drop in self.drops:
            # 必要フラグチェック
            if not all(flag in player_flags for flag in drop.required_flags):
                continue
            # 禁止フラグチェック
            if any(flag in player_flags for flag in drop.forbidden_flags):
                continue
            pool.append(drop)

        if not pool and self.default_drop:
            pool = [self.default_drop]

        if not pool:
            return []

        # ウェイト付き抽選
        total_weight = sum(drop.weight for drop in pool)
        if total_weight == 0:
            return []

        # 複数回抽選（min-max範囲で）
        results: List[str] = []
        for drop in pool:
            # このドロップタイプの個数を決定
            count = random.randint(drop.min_count, drop.max_count)
            # ウェイトに基づいて実際にドロップするか決定
            if random.random() * total_weight < drop.weight:
                results.extend([drop.fragment_id] * count)

        return results


# グローバルレジストリ（シンプル実装）
_FRAGMENT_DROP_TABLES: Dict[str, FragmentDropTable] = {}


def register_fragment_drop_table(table: FragmentDropTable) -> None:
    """ドロップテーブルを登録"""
    _FRAGMENT_DROP_TABLES[table.table_id] = table


def get_fragment_drop_table(table_id: str) -> Optional[FragmentDropTable]:
    """ドロップテーブルを取得"""
    return _FRAGMENT_DROP_TABLES.get(table_id)


def drop_fragments_for_quest(quest_id: str, player_flags: Optional[List[str]] = None) -> List[str]:
    """クエストIDに基づいて断片をドロップ"""
    table = get_fragment_drop_table(quest_id)
    if table:
        return table.drop_fragments(player_flags)
    return []


def load_fragment_drop_tables_from_yaml() -> None:
    """YAMLからドロップテーブルをロード"""
    import os
    import yaml

    yaml_path = "data/fragment_drop_tables.yaml"
    if not os.path.exists(yaml_path):
        return

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    for table_id, table_data in data.get("fragment_drop_tables", {}).items():
        drops = []
        for drop_data in table_data.get("drops", []):
            drops.append(FragmentDrop(
                fragment_id=drop_data["fragment_id"],
                min_count=drop_data.get("min_count", 1),
                max_count=drop_data.get("max_count", 1),
                weight=drop_data.get("weight", 100),
                required_flags=drop_data.get("required_flags", []),
                forbidden_flags=drop_data.get("forbidden_flags", []),
            ))
        table = FragmentDropTable(
            table_id=table_id,
            quest_id=table_data.get("quest_id", ""),
            drops=drops,
            default_drop=None  # YAMLからデフォルトドロップを設定する場合はここで追加
        )
        register_fragment_drop_table(table)


__all__ = [
    "FragmentDrop",
    "FragmentDropTable",
    "register_fragment_drop_table",
    "get_fragment_drop_table",
    "drop_fragments_for_quest",
    "load_fragment_drop_tables_from_yaml",
]