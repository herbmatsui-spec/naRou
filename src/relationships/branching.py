"""
NPC Relationship Simulation - Branching Scenario Generation Engine
Step 7: Branching scenario generation
"""

from __future__ import annotations

import itertools
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .engine import RelationshipManager
from .models import FactionAffiliation, InteractionType, RelationshipType


class ScenarioTriggerType(Enum):
    """分岐シナリオをトリガーする関係状態のタイプ"""

    RELATIONSHIP_THRESHOLD = "relationship_threshold"  # 関係レベルがしきい値を超えた
    RELATIONSHIP_CONFLICT = "relationship_conflict"  # 複数の関係が対立している
    TRIANGULAR_RELATIONSHIP = "triangular_relationship"  # 三角関係
    FACTION_TENSION = "faction_tension"  # 派閥間緊張
    BETRAYAL_DISCOVERY = "betrayal_discovery"  # 裏切り発覚
    ROMANCE_DEVELOPMENT = "romance_development"  # 恋愛発展
    MENTORSHIP_MILESTONE = "mentorship_milestone"  # 師弟関係の節目
    REUNION = "reunion"  # 再会
    LOSS = "loss"  # 喪失


@dataclass
class ScenarioCondition:
    """分岐シナリオの条件"""

    condition_type: ScenarioTriggerType
    character_ids: list[str] = field(default_factory=list)
    relationship_type: RelationshipType | None = None
    threshold_level: int | None = None
    comparison: str = "greater_than"  # greater_than, less_than, equals
    context_requirements: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScenarioBranch:
    """分岐シナリオの枝"""

    branch_id: str
    description: str
    conditions: list[ScenarioCondition] = field(default_factory=list)
    priority: int = 1  # 高いほど優先
    consequences: dict[str, Any] = field(default_factory=dict)
    available_choices: list[dict[str, Any]] = field(default_factory=list)
    requirements: dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedScenario:
    """生成された分岐シナリオ"""

    scenario_id: str
    title: str
    description: str
    trigger_type: ScenarioTriggerType
    involved_characters: list[str]
    branches: list[ScenarioBranch]
    created_at: float = field(default_factory=time.time)
    expiration_time: float | None = None
    is_active: bool = True
    context: dict[str, Any] = field(default_factory=dict)


class BranchingScenarioGenerator:
    """
    分岐シナリオ生成エンジン
    関係グラフの状態に基づいてストーリー分岐を検出・生成する
    """

    def __init__(self, relationship_manager: RelationshipManager):
        self.rm = relationship_manager
        self.graph = relationship_manager.graph

        # 生成されたシナリオのキャッシュ
        self._active_scenarios: dict[str, GeneratedScenario] = {}

        # シナリオ定義（YAML等からロード可能）
        self._scenario_templates: dict[str, Any] = self._load_scenario_templates()

        # 分岐の重複を防ぐための履歴
        self._recently_generated: list[
            tuple[ScenarioTriggerType, tuple[str, ...], str]
        ] = []

    def _load_scenario_templates(self) -> dict[str, Any]:
        """シナリオテンプレートのロード（簡易実装）"""
        return {
            "confession_opportunity": {
                "title": "告白のチャンス",
                "description": "{char_name}との関係が深まった。今が告白のチャンスかもしれない。",
                "conditions": {
                    "relationship_type": "romance",
                    "threshold": 60,
                    "comparison": "greater_than",
                },
                "branches": [
                    {
                        "branch_id": "confess",
                        "description": "勇気を出して告白する",
                        "consequences": {"romance_delta": 20, "friendship_delta": 5},
                        "choices": [
                            {
                                "choice_id": "romantic_confession",
                                "text": "本当の気持ちを伝える",
                                "requirements": {},
                            },
                            {
                                "choice_id": "casual_confession",
                                "text": "軽い気持ちで伝える",
                                "requirements": {},
                            },
                        ],
                    },
                    {
                        "branch_id": "wait",
                        "description": "タイミングを見計らう",
                        "consequences": {"romance_delta": 5},
                        "choices": [
                            {
                                "choice_id": "wait_longer",
                                "text": "もう少し関係を深めてから",
                                "requirements": {},
                            }
                        ],
                    },
                ],
            },
            "betrayal_crisis": {
                "title": "裏切りの危機",
                "description": "{char_name}との信頼関係が揺らいでいる。",
                "conditions": {
                    "relationship_type": "betrayal",
                    "threshold": 30,
                    "comparison": "greater_than",
                },
                "branches": [
                    {
                        "branch_id": "confront",
                        "description": "直接対決する",
                        "consequences": {"betrayal_delta": 10, "enmity_delta": 15},
                        "choices": [
                            {
                                "choice_id": "violent_confront",
                                "text": "暴力で解決する",
                                "requirements": {"combat_skill": 30},
                            },
                            {
                                "choice_id": "verbal_confront",
                                "text": "言葉で問い詰める",
                                "requirements": {},
                            },
                        ],
                    },
                    {
                        "branch_id": "forgive",
                        "description": "許しを乞う",
                        "consequences": {
                            "betrayal_delta": -20,
                            "favorability_delta": 10,
                        },
                        "choices": [
                            {
                                "choice_id": "sincere_apology",
                                "text": "心から謝罪する",
                                "requirements": {},
                            }
                        ],
                    },
                ],
            },
            "mentorship_succession": {
                "title": "後継者の儀式",
                "description": "{char_name}から本物の後継者として認められた。",
                "conditions": {
                    "relationship_type": "mentorship",
                    "threshold": 80,
                    "comparison": "greater_than",
                },
                "branches": [
                    {
                        "branch_id": "accept",
                        "description": "後継者となる",
                        "consequences": {
                            "mentorship_delta": 10,
                            "skill_unlock": "master_technique",
                        },
                        "choices": [
                            {
                                "choice_id": "accept_gracefully",
                                "text": "光栄に受ける",
                                "requirements": {},
                            }
                        ],
                    },
                    {
                        "branch_id": "decline",
                        "description": "独自の道を歩む",
                        "consequences": {"mentorship_delta": -5, "freedom_gain": 20},
                        "choices": [
                            {
                                "choice_id": "polite_decline",
                                "text": "感謝しつつ断る",
                                "requirements": {},
                            }
                        ],
                    },
                ],
            },
            "faction_conflict": {
                "title": "派閥対立の勃発",
                "description": "派閥間の緊張が臨界点に達した。",
                "conditions": {"trigger_type": "faction_tension", "threshold": 70},
                "branches": [
                    {
                        "branch_id": "support_faction",
                        "description": "自分の派閥を支持する",
                        "consequences": {"faction_reputation_delta": 20},
                        "choices": [
                            {
                                "choice_id": "active_support",
                                "text": "積極的に支持する",
                                "requirements": {},
                            },
                            {
                                "choice_id": "passive_support",
                                "text": "静かに支持する",
                                "requirements": {},
                            },
                        ],
                    },
                    {
                        "branch_id": "mediate",
                        "description": "和平を模索する",
                        "consequences": {
                            "faction_reputation_delta": 5,
                            "peace_bonus": 30,
                        },
                        "choices": [
                            {
                                "choice_id": "diplomatic_mediation",
                                "text": "外交的に仲介する",
                                "requirements": {"diplomacy": 40},
                            }
                        ],
                    },
                ],
            },
        }

    def check_for_scenarios(self, player_id: str = "player") -> list[GeneratedScenario]:
        """プレイヤーの関係状態に基づいてシナリオをチェック・生成"""
        generated_scenarios = []

        # 1. 関係閾値ベースのシナリオをチェック
        threshold_scenarios = self._check_threshold_scenarios(player_id)
        generated_scenarios.extend(threshold_scenarios)

        # 2. 関係対立ベースのシナリオをチェック
        conflict_scenarios = self._check_conflict_scenarios(player_id)
        generated_scenarios.extend(conflict_scenarios)

        # 3. 三角関係シナリオをチェック
        triangular_scenarios = self._check_triangular_scenarios(player_id)
        generated_scenarios.extend(triangular_scenarios)

        # 4. 派閥緊張シナリオをチェック
        faction_scenarios = self._check_faction_tension_scenarios(player_id)
        generated_scenarios.extend(faction_scenarios)

        # 重複を排除し、アクティブシナリオとして登録
        unique_scenarios = self._deduplicate_scenarios(generated_scenarios)
        for scenario in unique_scenarios:
            self._active_scenarios[scenario.scenario_id] = scenario

        return unique_scenarios

    def _deduplicate_scenarios(
        self, scenarios: list[GeneratedScenario]
    ) -> list[GeneratedScenario]:
        """重複を排除したシナリオリストを返す"""
        seen_keys = set()
        unique = []
        for scenario in scenarios:
            # 関与キャラクターとトリガータイプで重複を判定
            key = (scenario.trigger_type, tuple(sorted(scenario.involved_characters)))
            if key not in seen_keys:
                seen_keys.add(key)
                unique.append(scenario)
        return unique

    def _check_threshold_scenarios(self, player_id: str) -> list[GeneratedScenario]:
        """関係閾値ベースのシナリオをチェック"""
        scenarios = []

        # プレイヤーのすべての関係を取得
        relationships = self.rm.get_all_relationships(player_id)

        for target_id, rel_dict in relationships.items():
            for rel_type, level in rel_dict.items():
                # 各シナリオテンプレートの閾値条件をチェック
                for template_id, template in self._scenario_templates.items():
                    conditions = template.get("conditions", {})
                    if "relationship_type" not in conditions:
                        continue

                    template_rel_type = RelationshipType(
                        conditions["relationship_type"]
                    )
                    if template_rel_type != rel_type:
                        continue

                    threshold = conditions.get("threshold", 0)
                    comparison = conditions.get("comparison", "greater_than")

                    should_trigger = False
                    if (
                        comparison == "greater_than"
                        and level > threshold
                        or comparison == "less_than"
                        and level < threshold
                        or comparison == "equals"
                        and level == threshold
                    ):
                        should_trigger = True

                    if should_trigger:
                        scenario = self._create_scenario_from_template(
                            template_id, template, [player_id, target_id]
                        )
                        if scenario:
                            scenarios.append(scenario)

        return scenarios

    def _check_conflict_scenarios(self, player_id: str) -> list[GeneratedScenario]:
        """関係対立ベースのシナリオをチェック"""
        scenarios = []

        # プレイヤーのすべての関係を取得
        relationships = self.rm.get_all_relationships(player_id)

        # 関係のペアをチェック（Aとの関係が良く、Bとの関係が悪い場合など）
        for (target_a, rel_dict_a), (target_b, rel_dict_b) in itertools.combinations(
            relationships.items(), 2
        ):
            # 同じタイプの関係で対立があるかチェック
            for rel_type in set(rel_dict_a.keys()) & set(rel_dict_b.keys()):
                level_a = rel_dict_a[rel_type]
                level_b = rel_dict_b[rel_type]

                # 大きな対立があるか（例：一方が+50、他方が-50）
                if abs(level_a - level_b) >= 80 and (level_a > 40 or level_b > 40):
                    conflict_scenario = self._create_conflict_scenario(
                        player_id, target_a, target_b, rel_type
                    )
                    if conflict_scenario:
                        scenarios.append(conflict_scenario)

        return scenarios

    def _check_triangular_scenarios(self, player_id: str) -> list[GeneratedScenario]:
        """三角関係シナリオをチェック"""
        scenarios = []

        # プレイヤーのすべての関係を取得
        relationships = self.rm.get_all_relationships(player_id)

        # ロマンス関係が複数ある場合（三角関係）
        romance_targets = []
        for target_id, rel_dict in relationships.items():
            if (
                RelationshipType.ROMANCE in rel_dict
                and rel_dict[RelationshipType.ROMANCE] > 40
            ):
                romance_targets.append((target_id, rel_dict[RelationshipType.ROMANCE]))

        # 2人以上のロマンス対象がいる場合
        if len(romance_targets) >= 2:
            target_ids = [t[0] for t in romance_targets]
            # さらに、二人の間に関係があるかチェック
            for target_a, target_b in itertools.combinations(target_ids, 2):
                # 二人の間にも関係がある場合は三角関係の可能性
                edge = self.graph.get_edge(
                    target_a, target_b, RelationshipType.FAVORABILITY
                )
                if edge and edge.level > 0:
                    triangular_scenario = self._create_triangular_scenario(
                        player_id, target_ids
                    )
                    if triangular_scenario:
                        scenarios.append(triangular_scenario)

        return scenarios

    def _check_faction_tension_scenarios(
        self, player_id: str
    ) -> list[GeneratedScenario]:
        """派閥緊張シナリオをチェック"""
        scenarios = []

        # 派閥所属を取得
        player_node = self.graph.get_node(player_id)
        if not player_node or not player_node.faction_affiliations:
            return scenarios

        # プレイヤーが所属する派閥と敵対する派閥をチェック
        player_factions = player_node.faction_affiliations

        # 他のキャラクターの派閥所属を収集
        faction_members: dict[str, list[str]] = defaultdict(list)
        for char_id, node in self.graph.nodes.items():
            if char_id == player_id:
                continue
            for faction_id, affiliation in node.faction_affiliations.items():
                faction_members[faction_id].append(char_id)

        # 緊張状態を検出（プレイヤーの派閥と敵対派閥のメンバーが接近）
        for player_faction, player_affil in player_factions.items():
            if player_affil in [FactionAffiliation.HOSTILE, FactionAffiliation.RIVAL]:
                continue

            for faction_id, members in faction_members.items():
                if faction_id == player_faction:
                    continue

                # 敵対派閥のメンバーとの関係をチェック
                tension_level = 0
                for member_id in members:
                    edge = self.graph.get_edge(
                        player_id, member_id, RelationshipType.FAVORABILITY
                    )
                    if edge:
                        tension_level += abs(edge.level)

                if tension_level > 70:  # 緊張レベルのしきい値
                    faction_scenario = self._create_faction_scenario(
                        player_id, player_faction, faction_id, members
                    )
                    if faction_scenario:
                        scenarios.append(faction_scenario)

        return scenarios

    def _create_scenario_from_template(
        self, template_id: str, template: dict[str, Any], involved_chars: list[str]
    ) -> GeneratedScenario | None:
        """テンプレートからシナリオを作成"""
        # 重複チェック
        dedupe_key = (
            ScenarioTriggerType.RELATIONSHIP_THRESHOLD,
            tuple(involved_chars),
            template_id,
        )
        if self._is_recently_generated(dedupe_key):
            return None

        self._mark_as_generated(dedupe_key)

        # ブランチを作成
        branches = []
        for branch_data in template.get("branches", []):
            branch = ScenarioBranch(
                branch_id=branch_data["branch_id"],
                description=branch_data["description"],
                consequences=branch_data.get("consequences", {}),
                available_choices=branch_data.get("choices", []),
            )
            branches.append(branch)

        # キャラクター名を取得して説明をフォーマット
        char_name = "Unknown"
        if len(involved_chars) > 1:
            target_node = self.graph.get_node(involved_chars[1])
            if target_node:
                char_name = target_node.name

        description = template["description"].format(char_name=char_name)

        scenario = GeneratedScenario(
            scenario_id=f"{template_id}_{int(time.time())}",
            title=template["title"],
            description=description,
            trigger_type=ScenarioTriggerType.RELATIONSHIP_THRESHOLD,
            involved_characters=involved_chars,
            branches=branches,
            context={"template_id": template_id},
        )

        return scenario

    def _create_conflict_scenario(
        self, player_id: str, target_a: str, target_b: str, rel_type: RelationshipType
    ) -> GeneratedScenario | None:
        """関係対立シナリオを作成"""
        dedupe_key = (
            ScenarioTriggerType.RELATIONSHIP_CONFLICT,
            (player_id, target_a, target_b),
            rel_type.value,
        )
        if self._is_recently_generated(dedupe_key):
            return None

        self._mark_as_generated(dedupe_key)

        name_a = self._get_character_name(target_a)
        name_b = self._get_character_name(target_b)

        branches = [
            ScenarioBranch(
                branch_id="support_a",
                description=f"{name_a}を支持する",
                consequences={"favorability_delta": {target_a: 10, target_b: -10}},
                available_choices=[
                    {
                        "choice_id": "side_with_a",
                        "text": f"{name_a}の味方をする",
                        "requirements": {},
                    }
                ],
            ),
            ScenarioBranch(
                branch_id="support_b",
                description=f"{name_b}を支持する",
                consequences={"favorability_delta": {target_b: 10, target_a: -10}},
                available_choices=[
                    {
                        "choice_id": "side_with_b",
                        "text": f"{name_b}の味方をする",
                        "requirements": {},
                    }
                ],
            ),
            ScenarioBranch(
                branch_id="mediate",
                description="両者を仲介する",
                consequences={
                    "favorability_delta": {
                        target_a: 5,
                        target_b: 5,
                        "diplomacy_bonus": 15,
                    }
                },
                available_choices=[
                    {
                        "choice_id": "mediate_conflict",
                        "text": "平和的に解決する",
                        "requirements": {"diplomacy": 30},
                    }
                ],
            ),
        ]

        scenario = GeneratedScenario(
            scenario_id=f"conflict_{int(time.time())}",
            title="関係の対立",
            description=f"{name_a}と{name_b}の関係で板挟みになっている。あなたはどうする？",
            trigger_type=ScenarioTriggerType.RELATIONSHIP_CONFLICT,
            involved_characters=[player_id, target_a, target_b],
            branches=branches,
            context={"relationship_type": rel_type.value},
        )

        return scenario

    def _create_triangular_scenario(
        self, player_id: str, target_ids: list[str]
    ) -> GeneratedScenario | None:
        """三角関係シナリオを作成"""
        dedupe_key = (
            ScenarioTriggerType.TRIANGULAR_RELATIONSHIP,
            tuple([player_id] + target_ids),
            "love_triangle",
        )
        if self._is_recently_generated(dedupe_key):
            return None

        self._mark_as_generated(dedupe_key)

        names = [self._get_character_name(tid) for tid in target_ids]
        name_str = "と".join(names)

        branches = [
            ScenarioBranch(
                branch_id="choose_one",
                description=f"{name_str}のうち一人を選ぶ",
                consequences={"romance_delta": 15, "jealousy_delta": 20},
                available_choices=[
                    {
                        "choice_id": f"choose_{tid}",
                        "text": f"{self._get_character_name(tid)}を選ぶ",
                        "requirements": {},
                    }
                    for tid in target_ids
                ],
            ),
            ScenarioBranch(
                branch_id="keep_options_open",
                description="両方との関係を続ける",
                consequences={"romance_delta": 5, "risk_delta": 30},
                available_choices=[
                    {
                        "choice_id": "keep_options",
                        "text": "曖昧なままにする",
                        "requirements": {},
                    }
                ],
            ),
        ]

        scenario = GeneratedScenario(
            scenario_id=f"triangle_{int(time.time())}",
            title="三角関係の葛藤",
            description=f"{name_str}との関係が複雑になっている。あなたはどうする？",
            trigger_type=ScenarioTriggerType.TRIANGULAR_RELATIONSHIP,
            involved_characters=[player_id] + target_ids,
            branches=branches,
            context={"target_ids": target_ids},
        )

        return scenario

    def _create_faction_scenario(
        self,
        player_id: str,
        player_faction: str,
        enemy_faction: str,
        members: list[str],
    ) -> GeneratedScenario | None:
        """派閥緊張シナリオを作成"""
        dedupe_key = (
            ScenarioTriggerType.FACTION_TENSION,
            (player_id, player_faction, enemy_faction),
            "tension",
        )
        if self._is_recently_generated(dedupe_key):
            return None

        self._mark_as_generated(dedupe_key)

        branches = [
            ScenarioBranch(
                branch_id="escalate",
                description="対立を激化させる",
                consequences={"faction_reputation_delta": 25, "war_risk": 40},
                available_choices=[
                    {
                        "choice_id": "escalate_conflict",
                        "text": "派閥の誇りを守る",
                        "requirements": {},
                    }
                ],
            ),
            ScenarioBranch(
                branch_id="seek_peace",
                description="和平を模索する",
                consequences={"faction_reputation_delta": -10, "peace_bonus": 35},
                available_choices=[
                    {
                        "choice_id": "seek_peace",
                        "text": "和平交渉を提案する",
                        "requirements": {"diplomacy": 50},
                    }
                ],
            ),
        ]

        scenario = GeneratedScenario(
            scenario_id=f"faction_{int(time.time())}",
            title="派閥対立の決断",
            description=f"{player_faction}派閥と{enemy_faction}派閥の緊張が高まっている。",
            trigger_type=ScenarioTriggerType.FACTION_TENSION,
            involved_characters=[player_id] + members[:3],  # 最初の3名まで
            branches=branches,
            context={"player_faction": player_faction, "enemy_faction": enemy_faction},
        )

        return scenario

    def apply_scenario_choice(
        self,
        scenario: GeneratedScenario,
        branch_id: str,
        choice_id: str,
        player_id: str = "player",
    ) -> dict[str, Any]:
        """プレイヤーの選択を適用し、結果を返す"""
        if scenario.scenario_id not in self._active_scenarios:
            return {"error": "scenario_not_active"}

        # ブランチと選択肢を検索
        selected_branch = None
        selected_choice = None
        for branch in scenario.branches:
            if branch.branch_id == branch_id:
                selected_branch = branch
                for choice in branch.available_choices:
                    if choice["choice_id"] == choice_id:
                        selected_choice = choice
                        break
                break

        if not selected_branch or not selected_choice:
            return {"error": "invalid_choice"}

        # 選択の要件をチェック（簡易実装）
        requirements = selected_choice.get("requirements", {})
        if requirements:
            # 実際の要件チェックは呼び出し元で行うべきだが、ここではダミー実装
            pass

        # 結果を適用
        consequences = selected_branch.consequences
        applied_results = {}

        for target_id in scenario.involved_characters:
            if target_id == player_id:
                continue

            for rel_type in RelationshipType:
                delta_key = f"{rel_type.value}_delta"
                if delta_key in consequences:
                    delta = consequences[delta_key]
                    if isinstance(delta, dict):
                        # ターゲットごとの差分
                        if target_id in delta:
                            self.rm.modify_relationship(
                                player_id,
                                target_id,
                                InteractionType.QUEST_COOPERATION,  # 適当なインタラクションタイプ
                                delta[target_id],
                            )
                            applied_results[f"{target_id}_{rel_type.value}"] = delta[
                                target_id
                            ]
                    else:
                        # 一律の差分
                        self.rm.modify_relationship(
                            player_id,
                            target_id,
                            InteractionType.QUEST_COOPERATION,
                            delta,
                        )
                        applied_results[f"{target_id}_{rel_type.value}"] = delta

        # シナリオを非アクティブ化
        scenario.is_active = False
        del self._active_scenarios[scenario.scenario_id]

        return {
            "success": True,
            "applied_results": applied_results,
            "consequences": consequences,
        }

    def _is_recently_generated(self, dedupe_key: tuple) -> bool:
        """最近生成されたかチェック（重複防止）"""
        current_time = time.time()
        # 1時間以内の重複を防ぐ
        for key, gen_time in self._recently_generated:
            if key == dedupe_key and current_time - gen_time < 3600:
                return True
        return False

    def _mark_as_generated(self, dedupe_key: tuple) -> None:
        """生成済みとしてマーク"""
        self._recently_generated.append((dedupe_key, time.time()))
        # 古いエントリーを削除
        current_time = time.time()
        self._recently_generated = [
            (k, t)
            for k, t in self._recently_generated
            if current_time - t < 7200  # 2時間以上経過したものは削除
        ]

    def _get_character_name(self, character_id: str) -> str:
        """キャラクター名を取得"""
        node = self.graph.get_node(character_id)
        return node.name if node else character_id

    def get_active_scenarios(self) -> list[GeneratedScenario]:
        """アクティブなシナリオを取得"""
        return list(self._active_scenarios.values())

    def clear_expired_scenarios(self) -> int:
        """期限切れのシナリオをクリア"""
        current_time = time.time()
        expired_ids = []

        for scenario_id, scenario in self._active_scenarios.items():
            if scenario.expiration_time and current_time > scenario.expiration_time:
                expired_ids.append(scenario_id)

        for scenario_id in expired_ids:
            del self._active_scenarios[scenario_id]

        return len(expired_ids)
