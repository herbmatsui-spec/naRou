"""
Skill Eater Phase 3: Ascension Board System (Steps 1-6)
マスタースキルを星座グリッドのノードに配置し、隣接リンクによる属性シナジーと強力なパッシブバフを管理する。
"""

from typing import Dict, Any, List, Optional

class AscensionBoard:
    """
    神格化（アセンション）スキルボード
    - 星座グリッド（ノードとリンク）の管理
    - マスタースキルコアの装着・解除
    - 属性シナジー計算とパッシブバフの適用
    """
    def __init__(self):
        # Step 2: 星座グリッド定義 (Node ID -> データ)
        self.nodes: Dict[str, Dict[str, Any]] = {
            "alpha": {"element": "Void", "equipped_core": None, "neighbors": ["beta", "gamma"]},
            "beta": {"element": "Void", "equipped_core": None, "neighbors": ["alpha", "delta"]},
            "gamma": {"element": "Void", "equipped_core": None, "neighbors": ["alpha", "delta"]},
            "delta": {"element": "Void", "equipped_core": None, "neighbors": ["beta", "gamma"]}
        }
        self.active_links_count = 0
        self.synergy_buffs: Dict[str, float] = {
            "all_damage_multiplier": 1.0,
            "mp_cost_reduction": 0.0,
            "crit_rate_bonus": 0.0
        }

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
            "buffs": self.synergy_buffs
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
            "buffs": self.synergy_buffs
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
                if neighbor["equipped_core"] and neighbor["element"] == node["element"] and node["element"] != "Void":
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
            "buffs": self.synergy_buffs
        }
