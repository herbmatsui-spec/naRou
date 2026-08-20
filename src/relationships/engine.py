"""
NPC Relationship Simulation - Relationship Engine Core Logic
Step 4: Relationship engine core logic
"""

from __future__ import annotations

import os
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any

import yaml

from .graph import RelationshipGraph
from .models import (
    InteractionType,
    RelationshipEdge,
    RelationshipLevel,
    RelationshipModifier,
    RelationshipNode,
    RelationshipTemplate,
    RelationshipType,
)


class RelationshipManager:
    """
    関係システムのメインマネージャー
    関係グラフのロード、更新、クエリのための中央インターフェースを提供
    """

    def __init__(self, data_path: str = "data/character_relations.yaml"):
        self.data_path = data_path
        self.graph = RelationshipGraph()
        self.templates: dict[str, RelationshipTemplate] = {}
        self.global_settings: dict[str, Any] = {}

        # キャッシュと最適化
        self._template_cache: dict[str, RelationshipTemplate] = {}
        self._last_save_time: float = 0
        self._is_initialized: bool = False

        # イベントコールバック
        self._change_listeners: list[
            Callable[[str, str, RelationshipType, int], None]
        ] = []
        self._threshold_listeners: dict[
            tuple[str, str, RelationshipType, RelationshipLevel], list[Callable]
        ] = defaultdict(list)

        # 自動減衰タスク
        self._last_decay_check: float = time.time()

        # 初期化
        self._load_data()
        self._is_initialized = True

    def _load_data(self) -> None:
        """YAMLファイルからテンプレートと設定をロード"""
        if not os.path.exists(self.data_path):
            # デフォルトデータを作成
            self._create_default_data()
            return

        try:
            with open(self.data_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            # テンプレートをロード
            templates_data = data.get("relationship_templates", {})
            for template_id, template_data in templates_data.items():
                template = self._parse_template(template_id, template_data)
                self.templates[template_id] = template

            # グローバル設定をロード
            self.global_settings = data.get("global_settings", {})

        except Exception as e:
            print(f"Error loading relationship data: {e}")
            self._create_default_data()

    def _create_default_data(self) -> None:
        """デフォルトデータを作成（ファイルがない場合）"""
        # 基本的なテンプレートのみ作成
        self.templates = {
            "neutral": RelationshipTemplate(
                template_id="neutral",
                name="中立関係",
                relationship_type=RelationshipType.FAVORABILITY,
                initial_level=0,
                decay_rate=0.01,
            )
        }
        self.global_settings = {
            "max_single_change": 25,
            "min_relationship_level": -100,
            "max_relationship_level": 100,
            "decay_check_interval": 3600,
        }

    def _parse_template(
        self, template_id: str, data: dict[str, Any]
    ) -> RelationshipTemplate:
        """YAMLデータからRelationshipTemplateオブジェクトを作成"""
        # 単一のrelationship_typeか配列かを処理
        rel_type_input = data.get(
            "relationship_type",
            data.get("relationship_types", [RelationshipType.FAVORABILITY.value]),
        )
        if isinstance(rel_type_input, list):
            # 配列の場合、最初の要素をメインタイプとする（後方互換性のため）
            main_rel_type = (
                RelationshipType(rel_type_input[0])
                if rel_type_input
                else RelationshipType.FAVORABILITY
            )
        else:
            main_rel_type = RelationshipType(rel_type_input)

        # 初期レベルと減衰率の処理
        initial_levels = data.get("initial_levels", {})
        decay_rates = data.get("decay_rates", {})

        # メインタイプの値を取得（なければデフォルト）
        initial_level = initial_levels.get(
            main_rel_type.value, data.get("initial_level", 0)
        )
        decay_rate = decay_rates.get(main_rel_type.value, data.get("decay_rate", 0.01))

        # interaction_effectsをパース
        raw_effects = data.get("interaction_effects", [])
        interaction_effects = []
        for effect in raw_effects:
            parsed_effect = {
                "action": effect.get("action", ""),
                "effects": effect.get("effects", {}),
                **{k: v for k, v in effect.items() if k not in ["action", "effects"]},
            }
            interaction_effects.append(parsed_effect)

        return RelationshipTemplate(
            template_id=template_id,
            name=data.get("name", template_id),
            relationship_type=main_rel_type,
            initial_level=initial_level,
            decay_rate=decay_rate,
            interaction_effects=interaction_effects,
            benefits_at_levels=data.get("benefits_at_levels", {}),
            memory_triggers=data.get("memory_triggers", []),
            # 拡張フィールド
            romance_potential=data.get("romance_potential", 0.0),
            betrayal_risk=data.get("betrayal_risk", 0.0),
            mentorship_value=data.get("mentorship_value", 0.0),
            faction_influence=data.get("faction_influence", 0.0),
        )

    def save_data(self) -> bool:
        """現在のテンプレートと設定をYAMLファイルに保存"""
        try:
            data = {
                "relationship_templates": {},
                "global_settings": self.global_settings,
            }

            for template_id, template in self.templates.items():
                data["relationship_templates"][template_id] = {
                    "id": template.template_id,
                    "name": template.name,
                    "relationship_type": template.relationship_type.value,
                    "initial_level": template.initial_level,
                    "decay_rate": template.decay_rate,
                    "interaction_effects": template.interaction_effects,
                    "benefits_at_levels": template.benefits_at_levels,
                    "memory_triggers": template.memory_triggers,
                    "romance_potential": template.romance_potential,
                    "betrayal_risk": template.betrayal_risk,
                    "mentorship_value": template.mentorship_value,
                    "faction_influence": template.faction_influence,
                }

            # ディレクトリが存在しない場合は作成
            os.makedirs(
                os.path.dirname(self.data_path)
                if os.path.dirname(self.data_path)
                else ".",
                exist_ok=True,
            )

            with open(self.data_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    data, f, default_flow_style=False, allow_unicode=True, indent=2
                )

            self._last_save_time = time.time()
            return True

        except Exception as e:
            print(f"Error saving relationship data: {e}")
            return False

    def initialize_character(
        self,
        character_id: str,
        name: str,
        personality_traits: dict[str, float] | None = None,
    ) -> RelationshipNode:
        """新しいキャラクターをシステムに初期化"""
        if not self._is_initialized:
            self._load_data()

        node = RelationshipNode(
            character_id=character_id,
            name=name,
            personality_traits=personality_traits or {},
        )

        self.graph.add_node(node)
        return node

    def establish_relationship(
        self,
        source_id: str,
        target_id: str,
        template_id: str,
        source_name: str | None = None,
        target_name: str | None = None,
    ) -> bool:
        """テンプレートに基づいて二つのキャラクター間に関係を確立"""
        # テンプレートを取得
        template = self.templates.get(template_id)
        if not template:
            print(f"Template {template_id} not found")
            return False

        # キャラクターが存在しない場合は作成
        source_node = self.graph.get_node(source_id)
        if not source_node:
            source_node = self.initialize_character(
                source_id, source_name or f"Character_{source_id}"
            )

        target_node = self.graph.get_node(target_id)
        if not target_node:
            target_node = self.initialize_character(
                target_id, target_name or f"Character_{target_id}"
            )

        # テンプレートから関係を作成（多層対応）
        relationship_types = getattr(
            template, "relationship_types", [template.relationship_type]
        )
        initial_levels = getattr(
            template,
            "initial_levels",
            {template.relationship_type.value: template.initial_level},
        )
        decay_rates = getattr(
            template,
            "decay_rates",
            {template.relationship_type.value: template.decay_rate},
        )

        success = True
        for rel_type in relationship_types:
            rel_type_enum = (
                RelationshipType(rel_type) if isinstance(rel_type, str) else rel_type
            )
            initial_level = initial_levels.get(rel_type, template.initial_level)
            decay_rate = decay_rates.get(rel_type, template.decay_rate)

            edge = RelationshipEdge(
                source_id=source_id,
                target_id=target_id,
                relationship_type=rel_type_enum,
                level=initial_level,
                decay_rate=decay_rate,
            )

            if not self.graph.add_edge(edge):
                success = False

        # リスナーに通知
        if success:
            self._notify_relationship_created(source_id, target_id, template_id)

        return success

    def modify_relationship(
        self,
        source_id: str,
        target_id: str,
        interaction_type: InteractionType,
        amount: int,
        context: dict[str, Any] | None = None,
        multiplier: float = 1.0,
    ) -> dict[RelationshipType, int]:
        """特定のインタラクションに基づいて関係を変更"""
        # 入力値の検証と制限
        max_change = self.global_settings.get("max_single_change", 25)
        amount = max(-max_change, min(max_change, amount))

        if amount == 0:
            return {}

        # 関係変更の修正子を作成
        modifier = RelationshipModifier(
            interaction_type=interaction_type,
            amount=amount,
            multiplier=multiplier,
            context=context or {},
            timestamp=time.time(),
        )

        # すべての関係タイプに対して変更を適用
        changes: dict[RelationshipType, int] = {}
        edges = self.graph.get_edges_between(source_id, target_id)

        for edge in edges:
            # パーソナリティによる修正を計算
            personality_multiplier = self._calculate_personality_modifier(
                source_id, target_id, interaction_type
            )
            final_multiplier = multiplier * personality_multiplier

            # 最終的な変更量を計算
            final_amount = int(amount * final_multiplier)

            # 変更を適用
            edge.add_modifier(
                RelationshipModifier(
                    interaction_type=interaction_type,
                    amount=final_amount,
                    multiplier=1.0,  # すでに適用済み
                    context=context,
                    timestamp=time.time(),
                )
            )

            changes[edge.relationship_type] = edge.level

            # リスナーに通知
            self._notify_relationship_changed(
                source_id, target_id, edge.relationship_type, final_amount
            )

            # しきい値リスナーをチェック
            self._check_threshold_listeners(
                source_id, target_id, edge.relationship_type, edge.level
            )

        return changes

    def get_relationship_level(
        self, source_id: str, target_id: str, relationship_type: RelationshipType
    ) -> int:
        """二つのキャラクター間の特定の関係タイプのレベルを取得"""
        edge = self.graph.get_edge(source_id, target_id, relationship_type)
        return edge.level if edge else 0

    def get_relationship_level_category(
        self, source_id: str, target_id: str, relationship_type: RelationshipType
    ) -> RelationshipLevel:
        """関係レベルのカテゴリを取得"""
        level = self.get_relationship_level(source_id, target_id, relationship_type)
        edge = self.graph.get_edge(source_id, target_id, relationship_type)
        return edge.get_level_category() if edge else RelationshipLevel.NEUTRAL

    def get_all_relationships(
        self, character_id: str
    ) -> dict[str, dict[RelationshipType, int]]:
        """キャラクターのすべての関係を取得"""
        relationships = {}
        for target_id, edge in self.graph.get_related_nodes(character_id):
            if target_id not in relationships:
                relationships[target_id] = {}
            relationships[target_id][edge.relationship_type] = edge.level
        return relationships

    def apply_time_decay(self) -> dict[str, dict[RelationshipType, int]]:
        """時間経過による関係減衰を適用"""
        current_time = time.time()

        # 前回のチェックから十分な時間が経過したかチェック
        check_interval = self.global_settings.get("decay_check_interval", 3600)
        if current_time - self._last_decay_check < check_interval:
            return {}

        self._last_decay_check = current_time

        # すべてのエッジに減衰を適用
        changes = self.graph.apply_decay_to_all(current_time)

        # 変更をキャラクターごとにグループ化
        character_changes: dict[str, dict[RelationshipType, int]] = defaultdict(dict)

        # ここで変更を詳細に分解する必要があるが、
        # 現時点ではキャラクターIDと変化量のみを返す
        # 実際の実装では、どのエッジがどのように変化したかを追跡する必要がある

        return dict(character_changes)

    def _calculate_personality_modifier(
        self, source_id: str, target_id: str, interaction_type: InteractionType
    ) -> float:
        """パーソナリティ特性に基づく修正子を計算"""
        source_node = self.graph.get_node(source_id)
        target_node = self.graph.get_node(target_id)

        if not source_node or not target_node:
            return 1.0

        modifier = 1.0

        # 例: 外交的なキャラクターはポジティブなインタラクションでボーナス
        # 中立(0.5)で1.0になるよう中心化: 2.0 * trait
        if interaction_type in [
            InteractionType.TALK,
            InteractionType.GIFT,
            InteractionType.EMOTIONAL_SUPPORT,
        ]:
            extroversion = source_node.personality_traits.get("extroversion", 0.5)
            agreeableness = target_node.personality_traits.get("agreeableness", 0.5)
            modifier *= 2.0 * extroversion  # 外交性で0.0-2.0の範囲（0.5で1.0）
            modifier *= 2.0 * agreeableness  # 協調性で0.0-2.0の範囲（0.5で1.0）

        # 例: 神経質なキャラクターはネガティブなインタラクションでペナルティ
        elif interaction_type in [InteractionType.ARGUMENT, InteractionType.BETRAYAL]:
            neuroticism = source_node.personality_traits.get("neuroticism", 0.5)
            modifier *= 2.0 * neuroticism  # 神経質で0.0-2.0の範囲（0.5で1.0）

        return max(0.1, min(2.0, modifier))  # 0.1-2.0の範囲にクリッピング

    def add_change_listener(
        self, callback: Callable[[str, str, RelationshipType, int], None]
    ) -> None:
        """関係変更リスナーを追加"""
        self._change_listeners.append(callback)

    def add_threshold_listener(
        self,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType,
        threshold_level: RelationshipLevel,
        callback: Callable[[str, str, RelationshipType, int], None],
    ) -> None:
        """関係が特定のしきい値を通過したときのリスナーを追加"""
        key = (source_id, target_id, relationship_type, threshold_level)
        self._threshold_listeners[key].append(callback)

    def _notify_relationship_changed(
        self,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType,
        change_amount: int,
    ) -> None:
        """関係変更をリスナーに通知"""
        for callback in self._change_listeners:
            try:
                callback(source_id, target_id, relationship_type, change_amount)
            except Exception as e:
                print(f"Error in relationship change listener: {e}")

    def _notify_relationship_created(
        self, source_id: str, target_id: str, template_id: str
    ) -> None:
        """新しい関係作成をリスナーに通知"""
        # ここでは単純に変更リスナーを呼び出す
        for callback in self._change_listeners:
            try:
                # テンプレートから初期レベルを取得して通知
                template = self.templates.get(template_id)
                if template:
                    # 多層対応：すべての関係タイプについて通知
                    relationship_types = getattr(
                        template, "relationship_types", [template.relationship_type]
                    )
                    initial_levels = getattr(
                        template,
                        "initial_levels",
                        {template.relationship_type.value: template.initial_level},
                    )

                    for rel_type in relationship_types:
                        rel_type_enum = (
                            RelationshipType(rel_type)
                            if isinstance(rel_type, str)
                            else rel_type
                        )
                        initial_level = initial_levels.get(
                            rel_type, template.initial_level
                        )
                        callback(source_id, target_id, rel_type_enum, initial_level)
            except Exception as e:
                print(f"Error in relationship created listener: {e}")

    def _check_threshold_listeners(
        self,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType,
        new_level: int,
    ) -> None:
        """しきい値リスナーをチェックして必要ならば呼び出す"""
        # 新しいレベルがどのしきい値を通過したかをチェック
        for level in RelationshipLevel:
            key = (source_id, target_id, relationship_type, level)
            if key in self._threshold_listeners:
                # しきい値を超えたかチェック
                if new_level >= level.value:
                    # 実際には、以前のレベルと比較してちょうどしきい値を超えたときだけ呼び出すべきだが、
                    # 簡単のため、しきい値以上なら呼び出す（重複呼び出しの防止は実装時に改善）
                    for callback in self._threshold_listeners[key]:
                        try:
                            callback(source_id, target_id, relationship_type, new_level)
                        except Exception as e:
                            print(f"Error in threshold listener: {e}")

    def get_statistics(self) -> dict[str, Any]:
        """関係システムの統計情報を取得"""
        graph_stats = self.graph.get_graph_statistics()
        return {
            "template_count": len(self.templates),
            "initialized": self._is_initialized,
            "last_save_time": self._last_save_time,
            "graph_statistics": graph_stats,
        }
