"""
Skill Eater Phase 3: Ascension Board System (Steps 1-6)
マスタースキルを星座グリッドのノードに配置し、隣接リンクによる属性シナジーと強力なパッシブバフを管理する。
Phase 2: 探索連動ノード解放システム (Steps 13-24)
"""

from typing import Any, Dict, List

from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_dungeon_floor_manager import SkillEaterDungeonFloorManager
from skill_eater_exploration_system import ExplorationRank
from skill_eater_presentation_system import SkillEaterPresentationSystem


class AscensionBoard:
    """
    神格化（アセンション）スキルボード
    - 星座グリッド（ノードとリンク）の管理
    - マスタースキルコアの装着・解除
    - 属性シナジー計算とパッシブバフの適用
    - Phase 2: 探索連動ノード解放
    """

    _instance: "AscensionBoard | None" = None

    @classmethod
    def get_instance(cls) -> "AscensionBoard":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        cls._instance = None

    # Phase 2 Step 13: 探索連動ノード定義
    EXPLORATION_NODES: Dict[str, Dict[str, Any]] = {
        "deep_delver": {
            "name": "深層探索者",
            "description": "深淵の深層に到達した証",
            "level": 0,
            "max_level": 4,
            "thresholds": [50, 100, 150, 200],  # 深度閾値
            "unlocked": False,
        },
        "full_clearer": {
            "name": "全区画制覇者",
            "description": "全フロアをクリアした証",
            "level": 0,
            "max_level": 1,
            "thresholds": [99],  # 全99フロア
            "unlocked": False,
        },
        "secret_finder": {
            "name": "秘境発見者",
            "description": "全ての秘密部屋を発見した証",
            "level": 0,
            "max_level": 1,
            "thresholds": [50],  # 秘密部屋50個（調整可能）
            "unlocked": False,
        },
        "speed_runner": {
            "name": "速攻探索者",
            "description": "最短ターンで深層到達した証",
            "level": 0,
            "max_level": 1,
            "thresholds": [10000],  # ターン数閾値（調整可能）
            "unlocked": False,
        },
        "hazard_master": {
            "name": "侵食制御者",
            "description": "ハザードレベルを0に保ち続けた証",
            "level": 0,
            "max_level": 1,
            "thresholds": [100],  # ハザード0維持フロア数
            "unlocked": False,
        },
    }

    # Phase 2 Step 16: 探索連動ノード用パッシブバフ定義
    EXPLORATION_NODE_BUFFS: Dict[str, Dict[str, float]] = {
        "deep_delver": {"all_resistance": 10.0, "max_hp_bonus": 50.0},
        "full_clearer": {"item_find_rate": 25.0, "gold_gain": 20.0},
        "secret_finder": {"crit_rate": 15.0, "secret_detection": 50.0},
        "speed_runner": {"speed": 10.0, "turn_time_reduction": 15.0},
        "hazard_master": {"hazard_resistance": 100.0, "mp_cost_reduction": 20.0},
    }

    def __init__(self):
        # Step 2: 星座グリッド定義 (Node ID -> データ)
        self.nodes: Dict[str, Dict[str, Any]] = {
            "alpha": {"element": "Void", "equipped_core": None, "neighbors": ["beta", "gamma"]},
            "beta": {"element": "Void", "equipped_core": None, "neighbors": ["alpha", "delta"]},
            "gamma": {"element": "Void", "equipped_core": None, "neighbors": ["alpha", "delta"]},
            "delta": {"element": "Void", "equipped_core": None, "neighbors": ["beta", "gamma"]},
        }
        self.active_links_count = 0
        self.synergy_buffs: Dict[str, float] = {
            "all_damage_multiplier": 1.0,
            "mp_cost_reduction": 0.0,
            "crit_rate_bonus": 0.0,
        }

        # Phase 2: 探索連動ノード状態
        self.exploration_nodes: Dict[str, Dict[str, Any]] = {}
        for node_id, data in self.EXPLORATION_NODES.items():
            self.exploration_nodes[node_id] = {
                "name": data["name"],
                "description": data["description"],
                "level": 0,
                "max_level": data["max_level"],
                "thresholds": data["thresholds"],
                "unlocked": False,
            }

        # Presentation/Audio systems for unlock effects
        self._audio: SkillEaterAudioSystem | None = None
        self._presentation: SkillEaterPresentationSystem | None = None

    def _get_presentation_systems(self):
        """遅延初期化でプレゼンテーションシステムを取得"""
        if self._audio is None:
            self._audio = SkillEaterAudioSystem.get_instance()
        if self._presentation is None:
            self._presentation = SkillEaterPresentationSystem.get_instance()
        return self._audio, self._presentation

    def equip_core(self, node_id: str, core_name: str, core_element: str) -> Dict[str, Any]:
        """Step 3: マスタースキル（コア）をノードにセット"""
        if node_id not in self.nodes:
            return {"success": False, "message": f"Node {node_id} does not exist."}

        self.nodes[node_id]["equipped_core"] = core_name
        self.nodes[node_id]["element"] = core_element

        self._recalculate_synergies()
        return {
            "success": True,
            "message": f"Equipped [{core_name}] to node {node_id}.",
            "active_links": self.active_links_count,
            "buffs": self.synergy_buffs,
        }

    def unequip_core(self, node_id: str) -> Dict[str, Any]:
        """Step 6: ノードからコアを解除"""
        if node_id not in self.nodes:
            return {"success": False, "message": f"Node {node_id} does not exist."}

        removed = self.nodes[node_id]["equipped_core"]
        self.nodes[node_id]["equipped_core"] = None
        self.nodes[node_id]["element"] = "Void"

        self._recalculate_synergies()
        return {
            "success": True,
            "message": f"Removed core [{removed}] from node {node_id}.",
            "active_links": self.active_links_count,
            "buffs": self.synergy_buffs,
        }

    def _recalculate_synergies(self):
        """Step 4 & 5: 隣接リンクの属性一致シナジー計算とパッシブバフ付与"""
        checked_pairs = set()
        active_links = 0

        for n_id, node in self.nodes.items():
            if not node["equipped_core"]:
                continue
            for neighbor_id in node["neighbors"]:
                pair_key = tuple(sorted([n_id, neighbor_id]))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)

                neighbor = self.nodes[neighbor_id]
                if (
                    neighbor["equipped_core"]
                    and neighbor["element"] == node["element"]
                    and node["element"] != "Void"
                ):
                    active_links += 1

        self.active_links_count = active_links
        # 1リンクごとにダメージ+20%、MP消費軽減+10%、クリティカル+5%
        self.synergy_buffs["all_damage_multiplier"] = 1.0 + (0.20 * active_links)
        self.synergy_buffs["mp_cost_reduction"] = min(0.50, 0.10 * active_links)
        self.synergy_buffs["crit_rate_bonus"] = min(0.50, 0.05 * active_links)

    def get_board_state(self) -> Dict[str, Any]:
        """Step 6: UI向け状態出力"""
        return {
            "nodes": self.nodes,
            "active_links": self.active_links_count,
            "buffs": self.synergy_buffs,
        }

    # Phase 2 Step 14: ノード解放条件チェックメソッド
    def _check_exploration_node_conditions(
        self,
        exploration_rank: ExplorationRank,
        dungeon_manager: SkillEaterDungeonFloorManager | None = None,
    ) -> List[str]:
        """探索連動ノードの解放条件をチェックし、新たに解放されたノードIDリストを返す"""
        newly_unlocked = []

        for node_id, node_data in self.exploration_nodes.items():
            if node_data["unlocked"]:
                continue  # 既に解放済み

            thresholds = node_data["thresholds"]
            current_level = node_data["level"]
            max_level = node_data["max_level"]

            if current_level >= max_level:
                continue

            # 次のレベルの閾値をチェック
            if current_level < len(thresholds):
                threshold = thresholds[current_level]
                achieved = False

                if node_id == "deep_delver":
                    # 深層到達: 最大到達深度
                    achieved = exploration_rank.max_depth_reached >= threshold
                elif node_id == "full_clearer":
                    # 全区画制覇: クリア済みフロア数
                    achieved = exploration_rank.floors_cleared >= threshold
                elif node_id == "secret_finder":
                    # 秘密部屋全発見: 発見済み秘密部屋数
                    achieved = exploration_rank.secret_rooms_found >= threshold
                elif node_id == "speed_runner":
                    # 速攻: ターン数（簡易実装：深度到達ターン数で判定）
                    # 実際にはターン数トラッキングが必要
                    achieved = (
                        exploration_rank.max_depth_reached >= 50
                        and exploration_rank.total_exp >= threshold
                    )
                elif node_id == "hazard_master":
                    # ハザード制御: 実装簡易化のためフロアクリア数で代用
                    achieved = exploration_rank.floors_cleared >= threshold

                if achieved:
                    newly_unlocked.append(node_id)

        return newly_unlocked

    # Phase 2 Step 15: ノード解放実行メソッド
    def unlock_exploration_node(
        self,
        node_id: str,
        exploration_rank: ExplorationRank,
    ) -> Dict[str, Any]:
        """探索連動ノードを解放し、パッシブバフを付与"""
        if node_id not in self.exploration_nodes:
            return {"success": False, "message": f"Unknown exploration node: {node_id}"}

        node_data = self.exploration_nodes[node_id]
        if node_data["unlocked"] and node_data["level"] >= node_data["max_level"]:
            return {
                "success": True,
                "message": f"Node {node_id} already maxed out.",
                "level": node_data["level"],
            }

        # レベルアップ
        node_data["level"] += 1
        if node_data["level"] >= 1:
            node_data["unlocked"] = True

        # パッシブバフ適用
        buffs = self.EXPLORATION_NODE_BUFFS.get(node_id, {})
        for buff_key, buff_value in buffs.items():
            self.synergy_buffs[buff_key] = self.synergy_buffs.get(buff_key, 0.0) + buff_value

        # 演出再生
        self._play_node_unlock_fanfare(node_id, node_data["name"])

        return {
            "success": True,
            "message": f"Exploration node [{node_data['name']}] unlocked at level {node_data['level']}!",
            "level": node_data["level"],
            "buffs_applied": buffs,
            "current_buffs": self.synergy_buffs.copy(),
        }

    # Phase 2 Step 17: ノード解放時の演出・音声
    def _play_node_unlock_fanfare(self, node_id: str, node_name: str) -> None:
        audio, presentation = self._get_presentation_systems()
        presentation.add_event(
            emote_file="emote_crown.png",
            audio_file="ascension_node_unlock.ogg",
            message=f"アセンションノード『{node_name}』解放！",
        )
        audio.play_sound("ascension_node_unlock.ogg")

    # Phase 2 Step 18: 探索システムからの通知受け取り・一括チェック
    def check_and_unlock_exploration_nodes(
        self,
        exploration_rank: ExplorationRank,
        dungeon_manager: SkillEaterDungeonFloorManager | None = None,
    ) -> List[Dict[str, Any]]:
        """全探索連動ノードをチェックし、解放可能なものを一括解放"""
        newly_unlocked_ids = self._check_exploration_node_conditions(
            exploration_rank, dungeon_manager
        )
        results = []
        for node_id in newly_unlocked_ids:
            result = self.unlock_exploration_node(node_id, exploration_rank)
            results.append(result)
        return results

    # Phase 2 Step 22: アセンションボード状態取得API拡張
    def get_exploration_node_status(
        self, exploration_rank: ExplorationRank | None = None
    ) -> Dict[str, Any]:
        """探索連動ノードの状態を取得（UI表示用）"""
        status = {}
        for node_id, node_data in self.exploration_nodes.items():
            current_level = node_data["level"]
            max_level = node_data["max_level"]
            thresholds = node_data["thresholds"]
            next_threshold = thresholds[current_level] if current_level < len(thresholds) else None

            # 進捗率計算
            if next_threshold is not None:
                # 簡易的な進捗計算（実際のメトリクスに合わせて調整必要）
                if exploration_rank is not None:
                    if node_id == "deep_delver":
                        current = getattr(exploration_rank, "max_depth_reached", 0)
                    elif node_id == "full_clearer":
                        current = getattr(exploration_rank, "floors_cleared", 0)
                    elif node_id == "secret_finder":
                        current = getattr(exploration_rank, "secret_rooms_found", 0)
                    else:
                        current = 0
                else:
                    current = 0
                progress = min(1.0, current / next_threshold) if next_threshold > 0 else 1.0
            else:
                progress = 1.0

            status[node_id] = {
                "name": node_data["name"],
                "description": node_data["description"],
                "level": current_level,
                "max_level": max_level,
                "unlocked": node_data["unlocked"],
                "next_threshold": next_threshold,
                "progress": progress,
                "buffs": self.EXPLORATION_NODE_BUFFS.get(node_id, {}),
            }
        return status

    # Phase 2 Step 23: 深層到達ノードの段階的解放（専用メソッド）
    def update_deep_delver_progress(self, max_depth_reached: int) -> List[Dict[str, Any]]:
        """深層到達ノードの進捗を更新（深度到達時に呼び出し）"""
        results = []
        node_data = self.exploration_nodes.get("deep_delver")
        if not node_data:
            return results

        thresholds = node_data["thresholds"]
        current_level = node_data["level"]

        # 閾値を順にチェック
        for i, threshold in enumerate(thresholds):
            if i < current_level:
                continue  # 既に解放済みのレベル
            if max_depth_reached >= threshold:
                # このレベルを解放
                result = self.unlock_exploration_node(
                    "deep_delver",
                    type(
                        "obj",
                        (object,),
                        {
                            "max_depth_reached": max_depth_reached,
                            "floors_cleared": 0,
                            "secret_rooms_found": 0,
                            "total_exp": 0,
                        },
                    )(),
                )
                results.append(result)
            else:
                break  # 以降の閾値は未達成

        return results

    def get_full_board_state(self) -> Dict[str, Any]:
        """完全なボード状態取得（通常ノード＋探索連動ノード）"""
        return {
            "nodes": self.nodes,
            "active_links": self.active_links_count,
            "buffs": self.synergy_buffs,
            "exploration_nodes": self.get_exploration_node_status(),
        }
