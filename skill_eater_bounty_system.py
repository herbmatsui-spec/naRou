"""
Skill Eater Phase 2: Bounty & Heist System (Steps 49-54)
ミダス商会幹部10人に対する指名手配、情報収集、罠設置、スキル強奪を管理。
Phase 3: 深層バウンティ・隠しボス・闇市場指名手配犯 連動システム (Steps 25-36)
"""

import random
from typing import Any, Dict, List

from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_concept_crystal import ConceptCrystallizer
from skill_eater_presentation_system import SkillEaterPresentationSystem


class MidasBountyManager:
    """
    ミダス商会幹部 指名手配・ハイストマネージャー
    Phase 3: 深層ダンジョンバウンティ・隠しボス・闇市場指名手配犯 対応
    """

    # Phase 3 Step 25: 深層敵バウンティ対象定義
    DEEP_DUNGEON_TARGETS: Dict[str, Dict[str, Any]] = {
        "abyss_warden": {
            "name": "深淵の守護者 アビス・ウォーデン",
            "title": "深層100階〜の守護者",
            "unique_skill": "虚無の障壁 (Void Barrier)",
            "base_hp": 15000,
            "base_atk": 800,
            "min_depth": 100,
            "intel_gathered": False,
            "intel_detail": "Weakness: Concept-based attacks bypass his void barrier.",
            "trap_set": False,
            "is_defeated": False,
            "reward_aldo": 50000,
            "reward_concept_crystal": "Concept of Absolute Void",
        },
        "void_stalker": {
            "name": "虚空の追跡者 ヴォイド・ストーカー",
            "title": "深層150階〜の暗殺者",
            "unique_skill": "次元断絶 (Dimensional Severance)",
            "base_hp": 25000,
            "base_atk": 1200,
            "min_depth": 150,
            "intel_gathered": False,
            "intel_detail": "Weakness: Multi-hit attacks disrupt his phase shifting.",
            "trap_set": False,
            "is_defeated": False,
            "reward_aldo": 100000,
            "reward_concept_crystal": "Concept of Absolute Space",
        },
        "babel_architect": {
            "name": "バベルの設計者 アーキテクト",
            "title": "深層200階 最深部の支配者",
            "unique_skill": "創世の権能 (Authority of Genesis)",
            "base_hp": 50000,
            "base_atk": 2000,
            "min_depth": 200,
            "intel_gathered": False,
            "intel_detail": "Weakness: Simultaneous multi-element assault overwhelms his adaptation.",
            "trap_set": False,
            "is_defeated": False,
            "reward_aldo": 500000,
            "reward_concept_crystal": "Concept of Absolute Creation",
        },
    }

    # Phase 3 Step 29: 隠しボス（シークレットボス）定義
    SECRET_BOSSES: Dict[str, Dict[str, Any]] = {
        "shadow_monarch": {
            "name": "影の君主 シャドウ・モナーク",
            "title": "闇市場の真の支配者",
            "unique_skill": "影の支配 (Dominion of Shadows)",
            "base_hp": 30000,
            "base_atk": 1000,
            "spawn_condition": "all_secret_rooms_found",
            "intel_gathered": False,
            "intel_detail": "Weakness: Light-based skills deal triple damage.",
            "trap_set": False,
            "is_defeated": False,
            "reward_aldo": 200000,
            "reward_concept_crystal": "Concept of Absolute Shadow",
        },
        "time_lost_king": {
            "name": "時を失った王 タイム・ロスト・キング",
            "title": "過去の時代から現れた異形",
            "unique_skill": "時間停止 (Time Stop)",
            "base_hp": 40000,
            "base_atk": 1500,
            "spawn_condition": "depth_200_and_all_bounties_cleared",
            "intel_gathered": False,
            "intel_detail": "Weakness: Skills with 'Time' tag are sealed; use instant-cast skills.",
            "trap_set": False,
            "is_defeated": False,
            "reward_aldo": 300000,
            "reward_concept_crystal": "Concept of Absolute Time",
        },
    }

    # Phase 3 Step 30: 闇市場指名手配犯
    SHADOW_BROKERS: List[Dict[str, Any]] = [
        {
            "id": "shadow_broker_01",
            "name": "闇ブローカー・シルク",
            "title": "情報屋の女王",
            "min_depth": 30,
            "base_hp": 8000,
            "base_atk": 400,
            "unique_skill": "情報操作 (Info Manipulation)",
            "reward_aldo": 20000,
        },
        {
            "id": "shadow_broker_02",
            "name": "闇ブローカー・ヴェノム",
            "title": "毒の調合師",
            "min_depth": 60,
            "base_hp": 10000,
            "base_atk": 500,
            "unique_skill": "万能毒 (Universal Poison)",
            "reward_aldo": 30000,
        },
        {
            "id": "shadow_broker_03",
            "name": "闇ブローカー・ゴースト",
            "title": "幽霊のような男",
            "min_depth": 100,
            "base_hp": 12000,
            "base_atk": 600,
            "unique_skill": "フェイズシフト (Phase Shift)",
            "reward_aldo": 50000,
        },
        {
            "id": "shadow_broker_04",
            "name": "闇ブローカー・アイアン",
            "title": "鋼鉄の商人",
            "min_depth": 140,
            "base_hp": 15000,
            "base_atk": 700,
            "unique_skill": "鉄壁の契約 (Ironclad Contract)",
            "reward_aldo": 80000,
        },
        {
            "id": "shadow_broker_05",
            "name": "闇ブローカー・オメガ",
            "title": "最後の調停者",
            "min_depth": 180,
            "base_hp": 20000,
            "base_atk": 900,
            "unique_skill": "世界の均衡 (World Balance)",
            "reward_aldo": 120000,
        },
    ]

    def __init__(self):
        # Step 50: ターゲット幹部定義（10人抜粋・主要幹部）
        self.executives: Dict[str, Dict[str, Any]] = {
            "exec_01_valerius": {
                "name": "徴税卿ヴァレリウス",
                "title": "ミダス商会 第10執行役員",
                "unique_skill": "Skill Taxation (スキル課税)",
                "base_hp": 3000,
                "base_atk": 180,
                "intel_gathered": False,
                "intel_detail": "Weakness: Short-circuit traps disrupt his gold barrier.",
                "trap_set": False,
                "is_defeated": False,
            },
            "exec_02_morgan": {
                "name": "投機狂モーガン",
                "title": "ミダス商会 第9執行役員",
                "unique_skill": "Risk Hedge (絶対損切り結界)",
                "base_hp": 4500,
                "base_atk": 220,
                "intel_gathered": False,
                "intel_detail": "Weakness: Rapid multi-hit attacks overload hedge capacity.",
                "trap_set": False,
                "is_defeated": False,
            },
        }
        self.defeated_count = 0

        # Phase 3: 深層バウンティ・隠しボス・闇ブローカー状態
        self.deep_targets: Dict[str, Dict[str, Any]] = {}
        for tid, data in self.DEEP_DUNGEON_TARGETS.items():
            self.deep_targets[tid] = data.copy()
            self.deep_targets[tid]["intel_gathered"] = False
            self.deep_targets[tid]["trap_set"] = False
            self.deep_targets[tid]["is_defeated"] = False

        self.secret_bosses: Dict[str, Dict[str, Any]] = {}
        for bid, data in self.SECRET_BOSSES.items():
            self.secret_bosses[bid] = data.copy()
            self.secret_bosses[bid]["intel_gathered"] = False
            self.secret_bosses[bid]["trap_set"] = False
            self.secret_bosses[bid]["is_defeated"] = False
            self.secret_bosses[bid]["spawned"] = False

        self.shadow_brokers: Dict[str, Dict[str, Any]] = {}
        for broker in self.SHADOW_BROKERS:
            bid = broker["id"]
            self.shadow_brokers[bid] = broker.copy()
            self.shadow_brokers[bid]["intel_gathered"] = False
            self.shadow_brokers[bid]["trap_set"] = False
            self.shadow_brokers[bid]["is_defeated"] = False
            self.shadow_brokers[bid]["encountered"] = False

        # Presentation systems for effects
        self._audio: SkillEaterAudioSystem | None = None
        self._presentation: SkillEaterPresentationSystem | None = None

    def _get_presentation_systems(self):
        if self._audio is None:
            self._audio = SkillEaterAudioSystem.get_instance()
        if self._presentation is None:
            self._presentation = SkillEaterPresentationSystem.get_instance()
        return self._audio, self._presentation

    def gather_intel(self, exec_id: str, hacker_cost_junk: int = 100) -> Dict[str, Any]:
        """Step 51: 情報収集フェーズ（弱点アンロック）"""
        # 幹部チェック
        if exec_id in self.executives:
            target = self.executives[exec_id]
        # 深層ターゲットチェック
        elif exec_id in self.deep_targets:
            target = self.deep_targets[exec_id]
        # 隠しボスチェック
        elif exec_id in self.secret_bosses:
            target = self.secret_bosses[exec_id]
        # 闇ブローカーチェック
        elif exec_id in self.shadow_brokers:
            target = self.shadow_brokers[exec_id]
        else:
            return {"success": False, "message": "Target not found."}

        if target["intel_gathered"]:
            return {
                "success": True,
                "message": "Intel already gathered.",
                "intel": target["intel_detail"],
            }

        target["intel_gathered"] = True
        return {
            "success": True,
            "message": f"Intelligence acquired on [{target['name']}]!",
            "target": target["name"],
            "intel": target["intel_detail"],
        }

    def set_ambush_trap(self, exec_id: str, trap_type: str = "EMP_ShortCircuit") -> Dict[str, Any]:
        """Step 52: 襲撃前の罠設置（事前デバフ準備）"""
        # 幹部チェック
        if exec_id in self.executives:
            target = self.executives[exec_id]
        # 深層ターゲットチェック
        elif exec_id in self.deep_targets:
            target = self.deep_targets[exec_id]
        # 隠しボスチェック
        elif exec_id in self.secret_bosses:
            target = self.secret_bosses[exec_id]
        # 闇ブローカーチェック
        elif exec_id in self.shadow_brokers:
            target = self.shadow_brokers[exec_id]
        else:
            return {"success": False, "message": "Target not found."}

        target["trap_set"] = True
        return {
            "success": True,
            "message": f"Ambush trap [{trap_type}] rigged for {target['name']}.",
            "trap_type": trap_type,
        }

    def initiate_combat(self, exec_id: str) -> Dict[str, Any]:
        """Step 53: 幹部との戦闘突入（情報・罠の有無で弱体化）"""
        # 幹部チェック
        if exec_id in self.executives:
            target = self.executives[exec_id]
        # 深層ターゲットチェック
        elif exec_id in self.deep_targets:
            target = self.deep_targets[exec_id]
        # 隠しボスチェック
        elif exec_id in self.secret_bosses:
            target = self.secret_bosses[exec_id]
        # 闇ブローカーチェック
        elif exec_id in self.shadow_brokers:
            target = self.shadow_brokers[exec_id]
        else:
            return {"error": "Target not found"}

        if target["is_defeated"]:
            return {"error": "Target already eliminated"}

        hp_multiplier = 1.0
        atk_multiplier = 1.0
        applied_debuffs = []

        if target["intel_gathered"]:
            atk_multiplier -= 0.20
            applied_debuffs.append("Weakness Exploited (ATK -20%)")
        if target["trap_set"]:
            hp_multiplier -= 0.30
            applied_debuffs.append("Ambush Trap Triggered (HP -30%)")

        effective_hp = int(target["base_hp"] * hp_multiplier)
        effective_atk = int(target["base_atk"] * atk_multiplier)

        return {
            "target_name": target["name"],
            "unique_skill": target["unique_skill"],
            "effective_hp": effective_hp,
            "effective_atk": effective_atk,
            "debuffs": applied_debuffs,
            "message": "Heist combat initiated!",
        }

    def eliminate_executive(self, exec_id: str) -> Dict[str, Any]:
        """Step 54: 幹部討伐時のスキル強奪・マイルストーン報酬"""
        if exec_id not in self.executives:
            return {"success": False, "message": "Executive not found."}

        target = self.executives[exec_id]
        if target["is_defeated"]:
            return {"success": False, "message": "Already defeated."}

        target["is_defeated"] = True
        self.defeated_count += 1
        stolen_skill = target["unique_skill"]

        return {
            "success": True,
            "message": f"EXECUTIVE ELIMINATED: {target['name']} has fallen!",
            "stolen_skill": stolen_skill,
            "defeated_count": self.defeated_count,
            "resistance_milestone_reward": "5000 Junk & Corporate Security Token",
        }

    # Phase 3 Step 26: バウンティ対象の動的生成メソッド
    def generate_deep_dungeon_bounties(self, current_depth: int) -> List[Dict[str, Any]]:
        """現在深度に応じて出現可能なバウンティ対象を返す"""
        available = []

        # 深層ターゲット
        for tid, data in self.deep_targets.items():
            if data["min_depth"] <= current_depth and not data["is_defeated"]:
                available.append(
                    {
                        "id": tid,
                        "type": "deep_target",
                        "name": data["name"],
                        "title": data["title"],
                        "unique_skill": data["unique_skill"],
                        "base_hp": data["base_hp"],
                        "base_atk": data["base_atk"],
                        "min_depth": data["min_depth"],
                        "reward_aldo": data["reward_aldo"],
                        "reward_concept_crystal": data["reward_concept_crystal"],
                        "intel_gathered": data["intel_gathered"],
                        "trap_set": data["trap_set"],
                    }
                )

        # 隠しボス（出現条件チェック）
        for bid, data in self.secret_bosses.items():
            if not data["is_defeated"] and not data["spawned"]:
                # 簡易条件チェック
                if data["spawn_condition"] == "all_secret_rooms_found":
                    # 実際には探索システムから秘密部屋発見数を取得
                    pass
                if data["spawn_condition"] == "depth_200_and_all_bounties_cleared":
                    if current_depth >= 200:
                        data["spawned"] = True
                        available.append(
                            {
                                "id": bid,
                                "type": "secret_boss",
                                "name": data["name"],
                                "title": data["title"],
                                "unique_skill": data["unique_skill"],
                                "base_hp": data["base_hp"],
                                "base_atk": data["base_atk"],
                                "reward_aldo": data["reward_aldo"],
                                "reward_concept_crystal": data["reward_concept_crystal"],
                            }
                        )

        # 闇ブローカー（ランダム遭遇判定）
        for bid, data in self.shadow_brokers.items():
            if (
                data["min_depth"] <= current_depth
                and not data["is_defeated"]
                and not data["encountered"]
            ):
                # 遭遇率: 深度 × 0.5%
                encounter_chance = current_depth * 0.005
                if random.random() < encounter_chance:
                    data["encountered"] = True
                    available.append(
                        {
                            "id": bid,
                            "type": "shadow_broker",
                            "name": data["name"],
                            "title": data["title"],
                            "unique_skill": data["unique_skill"],
                            "base_hp": data["base_hp"],
                            "base_atk": data["base_atk"],
                            "reward_aldo": data["reward_aldo"],
                        }
                    )

        return available

    # Phase 3 Step 28: バウンティ敵討伐時の特別報酬
    def eliminate_deep_target(self, target_id: str, player: Any = None) -> Dict[str, Any]:
        """深層ターゲット・隠しボス・闇ブローカー討伐時の報酬処理"""
        target = None
        target_type = None

        if target_id in self.deep_targets:
            target = self.deep_targets[target_id]
            target_type = "deep_target"
        elif target_id in self.secret_bosses:
            target = self.secret_bosses[target_id]
            target_type = "secret_boss"
        elif target_id in self.shadow_brokers:
            target = self.shadow_brokers[target_id]
            target_type = "shadow_broker"
        else:
            return {"success": False, "message": "Target not found."}

        if target["is_defeated"]:
            return {"success": False, "message": "Already defeated."}

        target["is_defeated"] = True
        self.defeated_count += 1
        stolen_skill = target["unique_skill"]

        # 報酬計算
        reward_aldo = target.get("reward_aldo", 10000)
        reward_crystal = target.get("reward_concept_crystal", None)

        # 概念結晶生成
        crystal_result = None
        if reward_crystal and player:
            try:
                crystallizer = ConceptCrystallizer()
                # 討伐報酬として概念結晶を生成（単体生成）
                crystal_result = {
                    "name": reward_crystal,
                    "category": "Boss Drop",
                    "is_concept_crystal": True,
                    "power": target["base_atk"] // 2,
                    "tags": ["Concept", "Boss Drop", "Inherited"],
                    "description": f"Defeated {target['name']} and crystallized their essence.",
                }
            except Exception:
                pass

        # 演出
        audio, presentation = self._get_presentation_systems()
        presentation.add_event(
            emote_file="emote_crown.png",
            audio_file="victory.ogg",
            message=f"《{target['name']}》を討伐！ {reward_aldo} アルド獲得！",
        )
        audio.play_sound("victory.ogg")

        if crystal_result:
            presentation.add_event(
                emote_file="emote_crystal.png",
                audio_file="crystal_resonance.ogg",
                message=f"概念結晶《{reward_crystal}》を獲得！",
            )
            audio.play_sound("crystal_resonance.ogg")

        return {
            "success": True,
            "message": f"TARGET ELIMINATED: {target['name']} has fallen!",
            "stolen_skill": stolen_skill,
            "defeated_count": self.defeated_count,
            "reward_aldo": reward_aldo,
            "reward_concept_crystal": crystal_result,
            "target_type": target_type,
        }

    # Phase 3 Step 29: 隠しボス出現条件チェック
    def check_secret_boss_spawn(self, current_depth: int, exploration_rank: Any) -> str | None:
        """隠しボスの出現条件をチェックし、出現するボスIDを返す"""
        for bid, data in self.secret_bosses.items():
            if data["is_defeated"] or data["spawned"]:
                continue

            if data["spawn_condition"] == "all_secret_rooms_found":
                if exploration_rank.secret_rooms_found >= 50:  # 閾値
                    data["spawned"] = True
                    return bid
            elif data["spawn_condition"] == "depth_200_and_all_bounties_cleared":
                if current_depth >= 200 and self.defeated_count >= len(
                    self.DEEP_DUNGEON_TARGETS
                ) + len(self.executives):
                    data["spawned"] = True
                    return bid

        return None

    # Phase 3 Step 30: 闇市場指名手配犯のランダム出現判定
    def roll_shadow_broker_encounter(self, current_depth: int) -> Dict[str, Any] | None:
        """闇ブローカーのランダム遭遇判定"""
        for bid, data in self.shadow_brokers.items():
            if (
                data["min_depth"] <= current_depth
                and not data["is_defeated"]
                and not data["encountered"]
            ):
                encounter_chance = current_depth * 0.005
                if random.random() < encounter_chance:
                    data["encountered"] = True
                    return {
                        "id": bid,
                        "name": data["name"],
                        "title": data["title"],
                        "unique_skill": data["unique_skill"],
                        "base_hp": data["base_hp"],
                        "base_atk": data["base_atk"],
                        "reward_aldo": data["reward_aldo"],
                    }
        return None

    # Phase 3 Step 31: バウンティ情報収集の探索連動
    def gather_bounty_intel(
        self, target_id: str, cost_type: str = "aldo", cost_amount: int = 5000
    ) -> Dict[str, Any]:
        """情報収集（アルドまたは探索経験値消費）"""
        # 簡易実装: 既存のgather_intelを使用
        return self.gather_intel(target_id)

    # Phase 3 Step 32: 罠設置の探索連動
    def set_bounty_trap(self, target_id: str, trap_type: str) -> Dict[str, Any]:
        """罠設置（タイプ別デバフ）"""
        trap_types = {
            "EMP": {"hp_mult": 0.7, "atk_mult": 1.0, "desc": "EMPパルスでシステム無力化"},
            "SEALING_WARD": {"hp_mult": 1.0, "atk_mult": 0.8, "desc": "封印結界でスキル封印"},
            "GRAVITY_WELL": {"hp_mult": 0.8, "atk_mult": 0.9, "desc": "重力井戸で機動力低下"},
            "CONCEPT_DAMPENER": {
                "hp_mult": 0.9,
                "atk_mult": 0.7,
                "desc": "概念減衰器で概念スキル弱体化",
            },
        }

        if trap_type not in trap_types:
            return {"success": False, "message": "Unknown trap type."}

        return self.set_ambush_trap(target_id, trap_type)

    # Phase 3 Step 33: バウンティ戦闘突入フロー
    def initiate_bounty_combat(self, target_id: str) -> Dict[str, Any]:
        """バウンティ戦闘突入（情報・罠状態反映）"""
        return self.initiate_combat(target_id)

    # Phase 3 Step 34: バウンティ討伐時の概念結晶ドロップ連動
    # eliminate_deep_target で実装済み

    # Phase 3 Step 35: バウンティUI表示用データ取得
    def get_available_bounties(self, current_depth: int) -> List[Dict[str, Any]]:
        """現在深度で挑戦可能なバウンティ一覧を取得"""
        return self.generate_deep_dungeon_bounties(current_depth)

    # 既存メソッド互換性のため
    def eliminate_executive_compat(self, exec_id: str) -> Dict[str, Any]:
        return self.eliminate_executive(exec_id)
