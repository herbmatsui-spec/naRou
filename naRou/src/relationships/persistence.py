"""
NPC Relationship Simulation - Save/Load Support
Step 18: Save/load support for relationships
"""

from __future__ import annotations

import gzip
import json
import os
import pickle
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .engine import RelationshipManager
from .graph import RelationshipGraph
from .models import RelationshipType


class SaveFormat(Enum):
    """セーブフォーマット"""

    JSON = "json"  # 人間可読、デバッグ用
    PICKLE = "pickle"  # バイナリ、高速
    COMPRESSED = "compressed"  # 圧縮バイナリ


@dataclass
class SaveMetadata:
    """セーブメタデータ"""

    version: str = "1.0"
    save_time: float = field(default_factory=time.time)
    node_count: int = 0
    edge_count: int = 0
    checksum: str = ""


class RelationshipPersistence:
    """
    関係データの永続化システム
    関係グラフの効率的なシリアライズとデシリアライズ、バージョン管理
    """

    CURRENT_VERSION = "1.0"

    def __init__(self, relationship_manager: RelationshipManager):
        self.rm = relationship_manager
        self.graph = relationship_manager.graph

    def save_to_dict(self) -> dict[str, Any]:
        """関係データを辞書形式にエクスポート"""
        # グラフデータ
        graph_data = self.graph.to_dict()

        # テンプレートと設定
        templates_data = {
            tid: {
                "template_id": t.template_id,
                "name": t.name,
                "relationship_type": t.relationship_type.value,
                "initial_level": t.initial_level,
                "decay_rate": t.decay_rate,
                "romance_potential": t.romance_potential,
                "betrayal_risk": t.betrayal_risk,
                "mentorship_value": t.mentorship_value,
                "faction_influence": t.faction_influence,
            }
            for tid, t in self.rm.templates.items()
        }

        return {
            "version": self.CURRENT_VERSION,
            "save_time": time.time(),
            "graph": graph_data,
            "templates": templates_data,
            "global_settings": self.rm.global_settings,
        }

    def save_to_file(self, filename: str, format: SaveFormat = SaveFormat.JSON) -> bool:
        """ファイルにセーブ"""
        data = self.save_to_dict()

        try:
            if format == SaveFormat.JSON:
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            elif format == SaveFormat.PICKLE:
                with open(filename, "wb") as f:
                    pickle.dump(data, f)
            elif format == SaveFormat.COMPRESSED:
                with gzip.open(filename, "wb") as f:
                    pickle.dump(data, f)

            return True
        except Exception as e:
            print(f"Error saving relationship data: {e}")
            return False

    def load_from_dict(self, data: dict[str, Any]) -> bool:
        """辞書形式からロード"""
        if not data:
            return False

        # バージョンチェック
        version = data.get("version", "0.0")
        if version != self.CURRENT_VERSION:
            # 後方互換性のための変換が必要な場合はここで処理
            print(
                f"Warning: Loading relationship data version {version}, current is {self.CURRENT_VERSION}"
            )

        # グラフをロード
        graph_data = data.get("graph", {})
        if graph_data:
            self.graph = RelationshipGraph.from_dict(graph_data)
            self.rm.graph = self.graph

        # テンプレートをロード
        templates_data = data.get("templates", {})
        self.rm.templates.clear()
        for tid, t_data in templates_data.items():
            from .models import RelationshipTemplate

            self.rm.templates[tid] = RelationshipTemplate(
                template_id=t_data["template_id"],
                name=t_data["name"],
                relationship_type=RelationshipType(t_data["relationship_type"]),
                initial_level=t_data.get("initial_level", 0),
                decay_rate=t_data.get("decay_rate", 0.01),
                romance_potential=t_data.get("romance_potential", 0.0),
                betrayal_risk=t_data.get("betrayal_risk", 0.0),
                mentorship_value=t_data.get("mentorship_value", 0.0),
                faction_influence=t_data.get("faction_influence", 0.0),
            )

        # グローバル設定をロード
        if "global_settings" in data:
            self.rm.global_settings.update(data["global_settings"])

        self.rm._is_initialized = True
        return True

    def load_from_file(self, filename: str) -> bool:
        """ファイルからロード"""
        if not os.path.exists(filename):
            return False

        try:
            # 拡張子からフォーマットを判定
            if filename.endswith((".gz", ".pkl.gz")):
                with gzip.open(filename, "rb") as f:
                    data = pickle.load(f)
            elif filename.endswith(".pkl"):
                with open(filename, "rb") as f:
                    data = pickle.load(f)
            else:
                with open(filename, encoding="utf-8") as f:
                    data = json.load(f)

            return self.load_from_dict(data)
        except Exception as e:
            print(f"Error loading relationship data: {e}")
            return False

    def create_backup(self, base_filename: str) -> str | None:
        """バックアップを作成"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{base_filename}.{timestamp}.bak"

        if self.save_to_file(backup_filename, SaveFormat.COMPRESSED):
            return backup_filename
        return None

    def get_save_size(self, format: SaveFormat = SaveFormat.JSON) -> int:
        """セーブデータのサイズを推定（バイト）"""

        data = self.save_to_dict()
        if format == SaveFormat.JSON:
            return len(json.dumps(data).encode("utf-8"))
        else:
            return len(pickle.dumps(data))


class ComprehensiveRelationshipSaveSystem:
    """
    包括的な関係セーブシステム
    すべての関係サブシステム（ロマンス、師弟、裏切り、記憶等）の統合セーブ/ロード
    """

    def __init__(self, relationship_manager: RelationshipManager):
        self.rm = relationship_manager
        self.persistence = RelationshipPersistence(relationship_manager)

        # サブシステム参照（後で設定）
        self.romance_system: Any | None = None
        self.mentorship_system: Any | None = None
        self.betrayal_system: Any | None = None
        self.memory_system: Any | None = None
        self.personality_system: Any | None = None
        self.dialogue_system: Any | None = None
        self.faction_system: Any | None = None
        self.quest_integration: Any | None = None
        self.world_integration: Any | None = None

    def register_subsystem(self, name: str, system: Any) -> None:
        """サブシステムを登録"""
        setattr(self, name, system)

    def save_comprehensive(
        self, filename: str, format: SaveFormat = SaveFormat.JSON
    ) -> dict[str, Any]:
        """包括的なセーブ"""
        save_data = {
            "version": RelationshipPersistence.CURRENT_VERSION,
            "save_time": time.time(),
            "core": self.persistence.save_to_dict(),
            "subsystems": {},
        }

        # 各サブシステムからデータを収集
        if self.romance_system and hasattr(self.romance_system, "serialize"):
            save_data["subsystems"]["romance"] = self.romance_system.serialize()

        if self.mentorship_system and hasattr(self.mentorship_system, "serialize"):
            save_data["subsystems"]["mentorship"] = self.mentorship_system.serialize()

        if self.betrayal_system and hasattr(self.betrayal_system, "serialize"):
            save_data["subsystems"]["betrayal"] = self.betrayal_system.serialize()

        if self.memory_system and hasattr(self.memory_system, "serialize"):
            save_data["subsystems"]["memory"] = self.memory_system.serialize()

        if self.personality_system and hasattr(self.personality_system, "serialize"):
            save_data["subsystems"]["personality"] = self.personality_system.serialize()

        if self.dialogue_system and hasattr(self.dialogue_system, "serialize"):
            save_data["subsystems"]["dialogue"] = self.dialogue_system.serialize()

        if self.faction_system and hasattr(self.faction_system, "serialize"):
            save_data["subsystems"]["faction"] = {
                "factions": {
                    fid: {
                        "faction_id": f.faction_id,
                        "name": f.name,
                        "members": list(f.members),
                        "leader_id": f.leader_id,
                        "power_level": f.power_level,
                        "ideology": f.ideology,
                    }
                    for fid, f in self.faction_system.factions.items()
                },
                "relations": {
                    f"{a}_{b}": {
                        "faction_a": r.faction_a,
                        "faction_b": r.faction_b,
                        "relation_type": r.relation_type.value,
                        "relation_strength": r.relation_strength,
                    }
                    for (a, b), r in self.faction_system.faction_relations.items()
                },
            }

        if self.quest_integration and hasattr(self.quest_integration, "serialize"):
            save_data["subsystems"]["quest"] = self.quest_integration.serialize()

        if self.world_integration and hasattr(self.world_integration, "serialize"):
            save_data["subsystems"]["world"] = self.world_integration.serialize()

        # ファイルに書き込み
        try:
            if format == SaveFormat.JSON:
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(save_data, f, indent=2, ensure_ascii=False)
            elif format == SaveFormat.PICKLE:
                with open(filename, "wb") as f:
                    pickle.dump(save_data, f)
            elif format == SaveFormat.COMPRESSED:
                with gzip.open(filename, "wb") as f:
                    pickle.dump(save_data, f)

            return {
                "success": True,
                "filename": filename,
                "size_bytes": os.path.getsize(filename) if os.path.exists(filename) else 0,
                "subsystems_saved": list(save_data["subsystems"].keys()),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def load_comprehensive(self, filename: str) -> dict[str, Any]:
        """包括的なロード"""
        if not os.path.exists(filename):
            return {"success": False, "error": "file_not_found"}

        try:
            # フォーマット判定
            if filename.endswith(".gz"):
                with gzip.open(filename, "rb") as f:
                    save_data = pickle.load(f)
            elif filename.endswith(".pkl"):
                with open(filename, "rb") as f:
                    save_data = pickle.load(f)
            else:
                with open(filename, encoding="utf-8") as f:
                    save_data = json.load(f)

            # コアデータをロード
            if "core" in save_data:
                self.persistence.load_from_dict(save_data["core"])

            # サブシステムデータをロード
            subsystems = save_data.get("subsystems", {})
            loaded = []

            if (
                "romance" in subsystems
                and self.romance_system
                and hasattr(self.romance_system, "deserialize")
            ):
                self.romance_system.deserialize(subsystems["romance"])
                loaded.append("romance")

            if (
                "mentorship" in subsystems
                and self.mentorship_system
                and hasattr(self.mentorship_system, "deserialize")
            ):
                self.mentorship_system.deserialize(subsystems["mentorship"])
                loaded.append("mentorship")

            if (
                "betrayal" in subsystems
                and self.betrayal_system
                and hasattr(self.betrayal_system, "deserialize")
            ):
                self.betrayal_system.deserialize(subsystems["betrayal"])
                loaded.append("betrayal")

            if (
                "memory" in subsystems
                and self.memory_system
                and hasattr(self.memory_system, "deserialize")
            ):
                self.memory_system.deserialize(subsystems["memory"])
                loaded.append("memory")

            if (
                "personality" in subsystems
                and self.personality_system
                and hasattr(self.personality_system, "deserialize")
            ):
                self.personality_system.deserialize(subsystems["personality"])
                loaded.append("personality")

            if (
                "dialogue" in subsystems
                and self.dialogue_system
                and hasattr(self.dialogue_system, "deserialize")
            ):
                self.dialogue_system.deserialize(subsystems["dialogue"])
                loaded.append("dialogue")

            if "faction" in subsystems and self.faction_system:
                self._load_faction_data(subsystems["faction"])
                loaded.append("faction")

            if (
                "quest" in subsystems
                and self.quest_integration
                and hasattr(self.quest_integration, "deserialize")
            ):
                self.quest_integration.deserialize(subsystems["quest"])
                loaded.append("quest")

            if (
                "world" in subsystems
                and self.world_integration
                and hasattr(self.world_integration, "deserialize")
            ):
                self.world_integration.deserialize(subsystems["world"])
                loaded.append("world")

            return {
                "success": True,
                "loaded_subsystems": loaded,
                "version": save_data.get("version", "unknown"),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _load_faction_data(self, faction_data: dict[str, Any]) -> None:
        """派閥データをロード"""
        # 派閥をクリア
        self.faction_system.factions.clear()
        self.faction_system.faction_relations.clear()

        # 派閥を復元
        for fid, f_data in faction_data.get("factions", {}).items():
            from .faction import FactionNode

            faction = FactionNode(
                faction_id=f_data["faction_id"],
                name=f_data["name"],
                members=set(f_data.get("members", [])),
                leader_id=f_data.get("leader_id"),
                power_level=f_data.get("power_level", 0),
                ideology=f_data.get("ideology", ""),
            )
            self.faction_system.factions[fid] = faction

        # 関係を復元
        from .faction import FactionRelation, FactionRelationType

        for r_data in faction_data.get("relations", {}).values():
            relation = FactionRelation(
                faction_a=r_data["faction_a"],
                faction_b=r_data["faction_b"],
                relation_type=FactionRelationType(r_data["relation_type"]),
                relation_strength=r_data["relation_strength"],
            )
            self.faction_system.faction_relations[
                tuple(sorted([r_data["faction_a"], r_data["faction_b"]]))
            ] = relation

    def create_incremental_save(self, filename: str, last_save_time: float) -> dict[str, Any]:
        """増分セーブ（最後のセーブ以降の変更のみ）"""
        # 簡易実装：全データを保存するが、メタデータで最終セーブ時刻を記録
        result = self.save_comprehensive(filename)
        result["last_save_time"] = last_save_time
        result["incremental"] = True
        return result

    def verify_save_integrity(self, filename: str) -> dict[str, Any]:
        """セーブデータの整合性を検証"""
        if not os.path.exists(filename):
            return {"valid": False, "reason": "file_not_found"}

        try:
            # ロードテスト
            test_result = self.load_comprehensive(filename)
            if not test_result["success"]:
                return {"valid": False, "reason": test_result.get("error", "unknown")}

            # ノード数とエッジ数をチェック
            node_count = len(self.rm.graph.nodes)
            edge_count = len(self.rm.graph.edges)

            return {
                "valid": True,
                "node_count": node_count,
                "edge_count": edge_count,
                "loaded_subsystems": test_result.get("loaded_subsystems", []),
            }
        except Exception as e:
            return {"valid": False, "reason": str(e)}


# 便利な関数
def save_relationships(
    rm: RelationshipManager,
    filename: str,
    format: str = "json",
    comprehensive: bool = True,
    save_system: ComprehensiveRelationshipSaveSystem | None = None,
) -> dict[str, Any]:
    """関係データを保存する便利関数"""
    if comprehensive and save_system:
        return save_system.save_comprehensive(filename, SaveFormat(format))
    else:
        persistence = RelationshipPersistence(rm)
        return {"success": persistence.save_to_file(filename, SaveFormat(format))}


def load_relationships(
    rm: RelationshipManager,
    filename: str,
    comprehensive: bool = True,
    save_system: ComprehensiveRelationshipSaveSystem | None = None,
) -> dict[str, Any]:
    """関係データをロードする便利関数"""
    if comprehensive and save_system:
        return save_system.load_comprehensive(filename)
    else:
        persistence = RelationshipPersistence(rm)
        return {"success": persistence.load_from_file(filename)}
