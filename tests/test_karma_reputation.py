"""カルマ・名声システムのテスト (T42 ラウンド4案C)

カルマ増減イベント反映 (善行/悪行/クランプ)、data/karma.yaml の段階定義に基づく
段階判定の境界値、段階別の実効影響 (店価格倍率・NPC反応)、評判ゲート
(ReputationGate) の閾値チェックと解放判定、combat_system / pet_system の
イベントフック統合を検証する。
"""

from __future__ import annotations

import os
from enum import Enum, auto
from types import SimpleNamespace

import pytest
import yaml

from engine.systems.combat_system import CombatSystem
from engine.systems.pet_system import PetSystemHandler
from karma_system import KarmaManager, KarmaRegistry
from naRou.systems import FACTION_MONSTER
from reputation_gate_system import (
    FACTION_KINGDOM_GARDE,
    GateAction,
    ReputationGate,
    ReputationThreshold,
    create_thresholds_from_yaml,
    ensure_reputation_gate,
)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KARMA_YAML_PATH = os.path.join(_REPO_ROOT, "data", "karma.yaml")

# 段階境界 (data/karma.yaml と同一): 大善 >= 50 / 善 20..49 / 中立 -19..19 / 悪 -49..-20 / 大悪 <= -50
STAGE_BOUNDARIES = [
    (100, "saint", "大善"),
    (50, "saint", "大善"),
    (49, "good", "善"),
    (20, "good", "善"),
    (19, "neutral", "中立"),
    (0, "neutral", "中立"),
    (-19, "neutral", "中立"),
    (-20, "evil", "悪"),
    (-49, "evil", "悪"),
    (-50, "demon", "大悪"),
    (-100, "demon", "大悪"),
]

# 善行 / 悪行イベントと設定値 (秩序混沌, 善悪) — data/karma.yaml の actions と同一
GOOD_ACTIONS = [
    ("defeat_monster", 0, 1),
    ("donate_to_temple", 1, 2),
    ("relief_wounded", 1, 2),
    ("spare_enemy", 1, 2),
]
EVIL_ACTIONS = [
    ("steal", -1, -2),
    ("attack_innocent", -1, -2),
    ("murder_innocent", -2, -5),
    ("attack_gwen", -3, -15),
]


# ---------------------------------------------------------------------------
# テスト用スタブ
# ---------------------------------------------------------------------------


class KarmaPlayer:
    """カルマ値 (善悪・秩序混沌・露見度) を持つ最小プレイヤースタブ"""

    def __init__(self, good_evil: int = 0, law_chaos: int = 0, exposure: int = 0):
        self.karma_good_evil = good_evil
        self.karma_law_chaos = law_chaos
        self.template_exposure = exposure


class KarmaEngine:
    """KarmaManager 呼び出し用の最小エンジンスタブ (ログと survival を記録)"""

    def __init__(self, player=None):
        self.player = player
        self.survival = SimpleNamespace(karma=0, gold=0)
        self.logs: list[tuple[str, tuple[int, int, int], str]] = []

    def log(self, text, color=(230, 230, 230), level="INFO"):
        self.logs.append((text, color, level))


class GatePlayer:
    """評判ゲート用の最小プレイヤースタブ (関係・派閥評判を持つ)"""

    def __init__(self):
        self.character_relationships = {}
        self.faction_reputation = {}


class StubFactionData:
    """派閥影響力だけを持つ派閥データスタブ"""

    def __init__(self, influence: int):
        self.influence = influence


class StubFactionWarManager:
    """registry (dict) 経由で派閥影響力を返すマネージャースタブ"""

    def __init__(self, factions: dict):
        self.registry = factions


class StubNPC:
    """敵対化対象の NPC スタブ"""

    def __init__(self, name: str):
        self.name = name
        self.is_hostile = False


class StubEntityManager:
    """登録済みエンティティを返すだけのマネージャースタブ"""

    def __init__(self, entities):
        self._entities = entities

    def get_all_entities(self):
        return self._entities


class StubRelationshipManager:
    """関係更新を記録するマネージャースタブ"""

    def __init__(self):
        self.updates: list[tuple] = []

    def update_relationship(self, player, npc_id, kind, trust_delta, affinity_delta):
        self.updates.append((npc_id, kind, trust_delta, affinity_delta))


class StubQuestStatus(Enum):
    """クエスト状態スタブ (実装は status.__class__.AVAILABLE / LOCKED を参照する)"""

    LOCKED = auto()  # 解放前
    AVAILABLE = auto()  # 受注可能


class StubQuest:
    """LOCKED 状態で始まるクエストスタブ"""

    def __init__(self):
        self.status = StubQuestStatus.LOCKED


class StubMainQuestSystem:
    """quests 辞書を持つメインクエストシステムスタブ"""

    def __init__(self):
        self.quests = {"quest_rescue": StubQuest()}


class GateEngine:
    """ReputationGate 用の最小エンジンスタブ (ログ記録のみ)"""

    def __init__(self):
        self.logs: list[str] = []

    def log(self, text, color=(230, 230, 230), level="INFO"):
        self.logs.append(text)


class QuestGateEngine(GateEngine):
    """main_quest_system を備えたゲート用エンジンスタブ"""

    def __init__(self):
        super().__init__()
        self.main_quest_system = StubMainQuestSystem()


class HostileGateEngine(GateEngine):
    """entity_manager (+ 任意の relationship_manager) を備えたゲート用エンジンスタブ"""

    def __init__(self, entities, relationship_manager=None):
        super().__init__()
        self.entity_manager = StubEntityManager(entities)
        if relationship_manager is not None:
            self.relationship_manager = relationship_manager


class StubKillTarget:
    """撃破対象スタブ (faction 属性は明示セット時のみ持つ)"""

    def __init__(self, name: str = "ゴブリン", faction: str | None = None):
        self.name = name
        if faction is not None:
            self.faction = faction


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reload_karma_registry():
    """各テスト前に data/karma.yaml をレジストリへ再読み込みして状態を固定する"""
    KarmaRegistry().load(KARMA_YAML_PATH)
    yield


@pytest.fixture
def karma_manager() -> KarmaManager:
    """data/karma.yaml を読み込み済みの KarmaManager"""
    return KarmaManager()


# ---------------------------------------------------------------------------
# カルマ増減イベント反映
# ---------------------------------------------------------------------------


class TestKarmaEventReflection:
    """カルマ増減イベント反映のテスト"""

    @pytest.mark.parametrize(("action", "law_chaos_delta", "good_evil_delta"), GOOD_ACTIONS)
    def test_good_action_increases_karma(
        self, karma_manager, action, law_chaos_delta, good_evil_delta
    ):
        """善行イベントは秩序混沌・善悪カルマを設定値どおりに増やす"""
        player = KarmaPlayer()
        karma_manager.update_karma(player, action)
        assert player.karma_law_chaos == law_chaos_delta
        assert player.karma_good_evil == good_evil_delta

    @pytest.mark.parametrize(("action", "law_chaos_delta", "good_evil_delta"), EVIL_ACTIONS)
    def test_evil_action_decreases_karma(
        self, karma_manager, action, law_chaos_delta, good_evil_delta
    ):
        """悪行イベントは秩序混沌・善悪カルマを設定値どおりに減らす"""
        player = KarmaPlayer()
        karma_manager.update_karma(player, action)
        assert player.karma_law_chaos == law_chaos_delta
        assert player.karma_good_evil == good_evil_delta

    def test_amount_parameter_scales_delta(self, karma_manager):
        """update_karma の amount 引数でカルマ変化量が倍加する"""
        player = KarmaPlayer()
        karma_manager.update_karma(player, "donate_to_temple", amount=3)
        assert player.karma_law_chaos == 3
        assert player.karma_good_evil == 6

    def test_update_karma_returns_all_axes(self, karma_manager):
        """update_karma は (秩序混沌, 善悪, 露見度) のタプルを返す"""
        player = KarmaPlayer()
        result = karma_manager.update_karma(player, "template_deep_read")
        assert result == (-1, 0, 1)
        assert result == (
            player.karma_law_chaos,
            player.karma_good_evil,
            player.template_exposure,
        )

    def test_unknown_action_keeps_karma_unchanged(self, karma_manager):
        """未登録の行動イベントではカルマが変化しない"""
        player = KarmaPlayer()
        karma_manager.update_karma(player, "unknown_action_xyz")
        assert player.karma_law_chaos == 0
        assert player.karma_good_evil == 0


class TestKarmaClamp:
    """カルマ範囲制限 (クランプ) のテスト"""

    def test_good_evil_upper_clamp(self, karma_manager):
        """善悪カルマは範囲上限 (+100) でクランプされる"""
        player = KarmaPlayer(good_evil=99)
        karma_manager.update_karma(player, "donate_to_temple", amount=3)
        assert player.karma_good_evil == 100
        karma_manager.update_karma(player, "donate_to_temple", amount=10)
        assert player.karma_good_evil == 100

    def test_good_evil_lower_clamp(self, karma_manager):
        """善悪カルマは範囲下限 (-100) でクランプされる"""
        player = KarmaPlayer(good_evil=-99)
        karma_manager.update_karma(player, "attack_gwen")
        assert player.karma_good_evil == -100
        karma_manager.update_karma(player, "attack_gwen", amount=10)
        assert player.karma_good_evil == -100

    def test_law_chaos_clamp(self, karma_manager):
        """秩序混沌カルマも範囲 [-100, 100] でクランプされる"""
        player = KarmaPlayer(law_chaos=99)
        karma_manager.update_karma(player, "donate_to_temple", amount=5)
        assert player.karma_law_chaos == 100
        player.karma_law_chaos = -99
        karma_manager.update_karma(player, "attack_gwen", amount=5)
        assert player.karma_law_chaos == -100

    def test_exposure_upper_clamp(self, karma_manager):
        """露見度は範囲 [0, 100] の上限でクランプされる"""
        player = KarmaPlayer(exposure=98)
        karma_manager.update_karma(player, "template_deep_read", amount=5)
        assert player.template_exposure == 100


# ---------------------------------------------------------------------------
# カルマ段階判定
# ---------------------------------------------------------------------------


class TestKarmaStageJudgment:
    """data/karma.yaml の段階定義に基づく段階判定のテスト"""

    @pytest.mark.parametrize(("good_evil", "stage_id", "stage_name"), STAGE_BOUNDARIES)
    def test_stage_boundaries(self, karma_manager, good_evil, stage_id, stage_name):
        """段階境界のちょうど上/下で正しい段階が判定される"""
        stage = karma_manager.get_stage(good_evil)
        assert stage.id == stage_id
        assert stage.name == stage_name

    def test_get_stage_name_matches_get_stage(self):
        """軽量参照用 (Web配信) の get_stage_name は get_stage の段階名と一致する"""
        for good_evil, _stage_id, stage_name in STAGE_BOUNDARIES:
            assert KarmaManager.get_stage_name(good_evil) == stage_name

    def test_stages_loaded_from_karma_yaml(self):
        """レジストリの段階定義は data/karma.yaml の karma キー配下と一致する"""
        with open(KARMA_YAML_PATH, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        yaml_stages = raw["karma"]["stages"]
        loaded = KarmaRegistry().get("default").stages
        assert len(loaded) == len(yaml_stages)
        for stage, defined in zip(loaded, yaml_stages):
            assert stage.id == defined["id"]
            assert stage.name == defined["name"]
            assert stage.min_good_evil == defined["min_good_evil"]
            assert stage.shop_price_modifier == pytest.approx(defined["shop_price_modifier"])


# ---------------------------------------------------------------------------
# 段階別実効影響
# ---------------------------------------------------------------------------


class TestKarmaStageEffects:
    """段階別実効影響 (店価格倍率・NPC反応) と段階反映のテスト"""

    @pytest.mark.parametrize(
        ("good_evil", "expected_modifier"),
        [
            (50, 0.8),
            (49, 0.9),
            (20, 0.9),
            (19, 1.0),
            (-19, 1.0),
            (-20, 1.15),
            (-49, 1.15),
            (-50, 1.3),
        ],
    )
    def test_shop_price_modifier_boundaries(
        self, karma_manager, good_evil, expected_modifier
    ):
        """段階境界ごとに店価格倍率が data/karma.yaml の設定どおりに変わる"""
        assert karma_manager.get_shop_price_modifier(good_evil) == pytest.approx(
            expected_modifier
        )

    @pytest.mark.parametrize("good_evil", [100, 50, 49, 20, 19, 0, -19, -20, -49, -50, -100])
    def test_shop_price_modifier_is_positive(self, karma_manager, good_evil):
        """店価格倍率はどの段階でも正の値を返す"""
        assert karma_manager.get_shop_price_modifier(good_evil) > 0

    def test_shop_price_discount_grows_with_good_karma(self, karma_manager):
        """善悪値が高いほど店価格倍率は単調に割引かれる"""
        modifiers = [karma_manager.get_shop_price_modifier(ge) for ge in range(-100, 101)]
        assert all(a >= b for a, b in zip(modifiers, modifiers[1:]))

    def test_npc_reaction_defined_for_all_stages(self, karma_manager):
        """全段階で NPC 反応説明が非空文字列で返る"""
        for good_evil, _stage_id, _stage_name in STAGE_BOUNDARIES:
            reaction = karma_manager.get_npc_reaction(good_evil)
            assert isinstance(reaction, str) and reaction

    def test_apply_action_sets_stage_and_epilogue_flag(self, karma_manager):
        """apply_action は段階名とエピローグ分岐フラグをプレイヤーへ設定する"""
        player = KarmaPlayer()
        stage = karma_manager.apply_action(player, "donate_to_temple", engine=None, amount=10)
        assert stage.name == "善"
        assert player.karma_stage == "善"
        assert player.epilogue_karma_flag == "epilogue_good"

    def test_apply_action_syncs_survival_karma(self, karma_manager):
        """apply_action は善悪値を engine.survival.karma へ同期する"""
        player = KarmaPlayer()
        engine = KarmaEngine(player)
        karma_manager.apply_action(player, "donate_to_temple", engine=engine, amount=10)
        assert player.karma_good_evil == 20
        assert engine.survival.karma == 20

    def test_stage_change_is_logged_with_stage_color(self, karma_manager):
        """段階変化時は NPC 反応付きのログが段階色で通知される"""
        player = KarmaPlayer()
        engine = KarmaEngine(player)
        stage = karma_manager.apply_action(player, "donate_to_temple", engine=engine, amount=10)
        assert len(engine.logs) == 1
        text, color, level = engine.logs[0]
        assert "中立 → 善" in text
        assert stage.npc_reaction in text
        assert color == stage.color
        assert level == "INFO"

    def test_no_log_when_stage_unchanged(self, karma_manager):
        """段階が変わらない場合はログへ通知しない"""
        player = KarmaPlayer()
        engine = KarmaEngine(player)
        karma_manager.apply_action(player, "donate_to_temple", engine=engine)
        assert engine.logs == []

    def test_evil_stage_change_logged_as_warning(self, karma_manager):
        """悪行による段階変化は WARNING レベルでログへ通知される"""
        player = KarmaPlayer()
        engine = KarmaEngine(player)
        karma_manager.apply_action(player, "attack_gwen", engine=engine, amount=2)
        assert len(engine.logs) == 1
        text, _color, level = engine.logs[0]
        assert "中立 → 悪" in text
        assert level == "WARNING"


# ---------------------------------------------------------------------------
# 評判閾値チェック
# ---------------------------------------------------------------------------


class TestReputationThresholdCheck:
    """ReputationThreshold の閾値判定テスト"""

    def test_positive_threshold_is_gte_and_inclusive(self):
        """正の閾値は auto で gte になり、ちょうどの値で満たす"""
        threshold = ReputationThreshold(
            threshold=30, action=GateAction.UNLOCK_SHOP, target_id="shop"
        )
        assert threshold.check(29) is False
        assert threshold.check(30) is True
        assert threshold.check(31) is True

    def test_negative_threshold_is_lte_and_inclusive(self):
        """負の閾値は auto で lte になり、ちょうどの値で満たす"""
        threshold = ReputationThreshold(
            threshold=-20, action=GateAction.TRIGGER_HOSTILE, target_id="npc"
        )
        assert threshold.check(-21) is True
        assert threshold.check(-20) is True
        assert threshold.check(-19) is False

    def test_explicit_comparison_overrides_auto(self):
        """comparison 明示時は auto 判定を上書きする"""
        threshold = ReputationThreshold(
            threshold=30, action=GateAction.UNLOCK_SHOP, target_id="shop", comparison="lte"
        )
        assert threshold.check(10) is True
        assert threshold.check(40) is False

    def test_create_thresholds_from_yaml(self):
        """YAML 形式の辞書リストから閾値定義リストを構築できる"""
        data = [
            {
                "threshold": 40,
                "action": "UNLOCK_DIALOGUE",
                "target_id": "chat",
                "params": {"style": "friendly"},
                "description": "テスト用",
                "one_time": False,
            },
            {"threshold": 10, "action": "GRANT_BUFF", "target_id": "blessing"},
        ]
        thresholds = create_thresholds_from_yaml(data)
        assert thresholds[0].threshold == 40
        assert thresholds[0].action is GateAction.UNLOCK_DIALOGUE
        assert thresholds[0].params == {"style": "friendly"}
        assert thresholds[0].one_time is False
        assert thresholds[1].action is GateAction.GRANT_BUFF
        assert thresholds[1].params == {}
        assert thresholds[1].one_time is True


# ---------------------------------------------------------------------------
# 評判ゲートの評価と解放判定
# ---------------------------------------------------------------------------


class TestReputationGateEvaluation:
    """評判ゲートの閾値評価と解放判定のテスト"""

    def test_npc_reputation_sums_base_and_trust(self):
        """NPC 評判は base_reputation + 関係 trust の合計になる"""
        gate = ReputationGate(GateEngine())
        gate.register_npc_gate("npc_a", [], base_reputation=5)
        player = GatePlayer()
        player.character_relationships["npc_a"] = {"trust": 12}
        assert gate.get_npc_reputation(player, "npc_a") == 17

    def test_faction_reputation_sums_base_and_player_rep(self):
        """派閥評判は base_reputation + プレイヤー評判の合計 (戦争マネージャ不在時)"""
        gate = ReputationGate(GateEngine())
        gate.register_faction_gate(FACTION_KINGDOM_GARDE, [], base_reputation=10)
        player = GatePlayer()
        player.faction_reputation[FACTION_KINGDOM_GARDE] = 7
        assert gate.get_faction_reputation(player, FACTION_KINGDOM_GARDE) == 17

    def test_faction_reputation_adds_influence_mapping(self):
        """派閥戦争マネージャの影響力は -50..+50 に写像されて加算される"""
        engine = GateEngine()
        engine.faction_war_manager = StubFactionWarManager(
            {FACTION_KINGDOM_GARDE: StubFactionData(influence=65)}
        )
        gate = ReputationGate(engine)
        player = GatePlayer()
        assert gate.get_faction_reputation(player, FACTION_KINGDOM_GARDE) == 15

    def test_evaluate_unregistered_npc_returns_empty(self):
        """未登録 NPC のゲート評価は空リストを返す"""
        gate = ReputationGate(GateEngine())
        assert gate.evaluate_npc_gates(GatePlayer(), "nobody") == []

    def test_evaluate_npc_gate_below_threshold(self):
        """信頼度が閾値不足の間はゲートは満たされない"""
        gate = ReputationGate(GateEngine())
        gate.register_npc_gate(
            "npc_a",
            [
                ReputationThreshold(
                    threshold=40,
                    action=GateAction.UNLOCK_DIALOGUE,
                    target_id="chat",
                    description="テスト用会話解放",
                )
            ],
        )
        player = GatePlayer()
        player.character_relationships["npc_a"] = {"trust": 39}
        assert gate.evaluate_npc_gates(player, "npc_a") == []

    def test_evaluate_npc_gate_at_exact_threshold(self):
        """信頼度が閾値ちょうどでゲートが満たされる"""
        gate = ReputationGate(GateEngine())
        gate.register_npc_gate(
            "npc_a",
            [
                ReputationThreshold(
                    threshold=40, action=GateAction.UNLOCK_DIALOGUE, target_id="chat"
                )
            ],
        )
        player = GatePlayer()
        player.character_relationships["npc_a"] = {"trust": 40}
        results = gate.evaluate_npc_gates(player, "npc_a")
        assert len(results) == 1
        assert results[0].target_id == "chat"

    def test_fire_gate_unlocks_dialogue_once(self):
        """発火は player.gate_unlocked_dialogues に記録され、one_time で再発火しない"""
        gate = ReputationGate(GateEngine())
        gate.register_npc_gate(
            "npc_a",
            [
                ReputationThreshold(
                    threshold=40, action=GateAction.UNLOCK_DIALOGUE, target_id="chat"
                )
            ],
        )
        player = GatePlayer()
        player.character_relationships["npc_a"] = {"trust": 40}
        results = gate.evaluate_npc_gates(player, "npc_a")
        assert gate.fire_gate(results[0], "npc:npc_a", player) is True
        assert "chat" in player.gate_unlocked_dialogues
        assert gate.fire_gate(results[0], "npc:npc_a", player) is False
        assert gate.evaluate_npc_gates(player, "npc_a") == []

    def test_check_all_gates_unlocks_shop_at_exact_threshold(self):
        """check_all_gates は派閥評判が閾値ちょうどのとき王立商店を解放する"""
        gate = ReputationGate(GateEngine())
        gate.register_faction_gate(
            FACTION_KINGDOM_GARDE,
            [
                ReputationThreshold(
                    threshold=30, action=GateAction.UNLOCK_SHOP, target_id="royal_shop"
                )
            ],
        )
        player = GatePlayer()
        player.faction_reputation[FACTION_KINGDOM_GARDE] = 30
        fired = gate.check_all_gates(player)
        assert fired == [f"faction:{FACTION_KINGDOM_GARDE}:UNLOCK_SHOP:royal_shop"]
        assert "royal_shop" in player.gate_unlocked_shops

    def test_check_all_gates_no_fire_below_threshold(self):
        """派閥評判が閾値不足なら何も発火しない"""
        gate = ReputationGate(GateEngine())
        gate.register_faction_gate(
            FACTION_KINGDOM_GARDE,
            [
                ReputationThreshold(
                    threshold=30, action=GateAction.UNLOCK_SHOP, target_id="royal_shop"
                )
            ],
        )
        player = GatePlayer()
        player.faction_reputation[FACTION_KINGDOM_GARDE] = 29
        assert gate.check_all_gates(player) == []
        assert not getattr(player, "gate_unlocked_shops", set())

    def test_check_all_gates_grants_buff_at_high_reputation(self):
        """高評判では商店解放に加えて加護 (バフ) も付与される"""
        gate = ReputationGate(GateEngine())
        gate.register_faction_gate(
            FACTION_KINGDOM_GARDE,
            [
                ReputationThreshold(
                    threshold=30, action=GateAction.UNLOCK_SHOP, target_id="royal_shop"
                ),
                ReputationThreshold(
                    threshold=60,
                    action=GateAction.GRANT_BUFF,
                    target_id="royal_favor",
                    params={"atk": 2, "def": 2},
                ),
            ],
        )
        player = GatePlayer()
        player.faction_reputation[FACTION_KINGDOM_GARDE] = 60
        fired = gate.check_all_gates(player)
        assert len(fired) == 2
        assert player.gate_buffs["royal_favor"] == {"atk": 2, "def": 2}

    def test_check_all_gates_applies_debuff_at_low_reputation(self):
        """負の評判では auto lte 判定でデバフ (厄災) が適用される"""
        gate = ReputationGate(GateEngine())
        gate.register_faction_gate(
            FACTION_KINGDOM_GARDE,
            [
                ReputationThreshold(
                    threshold=-60,
                    action=GateAction.APPLY_DEBUFF,
                    target_id="royal_wrath",
                    params={"def": -2},
                )
            ],
        )
        player = GatePlayer()
        player.faction_reputation[FACTION_KINGDOM_GARDE] = -60
        fired = gate.check_all_gates(player)
        assert len(fired) == 1
        assert player.gate_debuffs["royal_wrath"] == {"def": -2}

    def test_ensure_reputation_gate_lazy_and_idempotent(self):
        """ensure_reputation_gate は遅延生成し、2 回目以降は同一インスタンスを返す"""
        engine = GateEngine()
        gate1 = ensure_reputation_gate(engine)
        gate2 = ensure_reputation_gate(engine)
        assert isinstance(gate1, ReputationGate)
        assert gate1 is gate2
        assert FACTION_KINGDOM_GARDE in gate1._faction_gates

    def test_ensure_reputation_gate_default_gates_fire(self):
        """既定ゲート (王立商店・グウェン会話) が実際に解放判定される"""
        gate = ensure_reputation_gate(GateEngine())
        player = GatePlayer()
        player.faction_reputation[FACTION_KINGDOM_GARDE] = 30
        player.character_relationships["かたつむり少女『グウェン』"] = {"trust": 40}
        fired = gate.check_all_gates(player)
        assert "royal_shop" in player.gate_unlocked_shops
        assert "gwen_friend_chat" in player.gate_unlocked_dialogues
        # 評判 60 未満なので加護 (GRANT_BUFF) は未発火
        assert not any("GRANT_BUFF" in gate_id for gate_id in fired)


# ---------------------------------------------------------------------------
# ゲートアクション実行
# ---------------------------------------------------------------------------


class TestReputationGateActions:
    """ゲートアクション実行のテスト"""

    @staticmethod
    def _make_threshold(action: GateAction, target_id: str, params: dict | None = None):
        return ReputationThreshold(
            threshold=0, action=action, target_id=target_id, params=params or {}
        )

    def test_unlock_and_lock_quest(self):
        """UNLOCK_QUEST でクエストが解放され、LOCK_QUEST でロックされる"""
        engine = QuestGateEngine()
        gate = ReputationGate(engine)
        assert gate.fire_gate(
            self._make_threshold(GateAction.UNLOCK_QUEST, "quest_rescue"),
            "npc:test",
            GatePlayer(),
        )
        assert (
            engine.main_quest_system.quests["quest_rescue"].status
            == StubQuestStatus.AVAILABLE
        )
        assert gate.fire_gate(
            self._make_threshold(GateAction.LOCK_QUEST, "quest_rescue"),
            "npc:test",
            GatePlayer(),
        )
        assert (
            engine.main_quest_system.quests["quest_rescue"].status == StubQuestStatus.LOCKED
        )

    def test_quest_gate_unknown_target_fails(self):
        """存在しないクエスト ID では発火が失敗する"""
        gate = ReputationGate(QuestGateEngine())
        assert (
            gate.fire_gate(
                self._make_threshold(GateAction.UNLOCK_QUEST, "missing_quest"),
                "npc:test",
                GatePlayer(),
            )
            is False
        )

    def test_trigger_hostile_marks_npc_and_deteriorates_relationship(self):
        """TRIGGER_HOSTILE は NPC を敵対化し、関係悪化も記録する"""
        npc = StubNPC("衛兵")
        rel_mgr = StubRelationshipManager()
        gate = ReputationGate(HostileGateEngine([npc], rel_mgr))
        player = GatePlayer()
        assert (
            gate.fire_gate(
                self._make_threshold(GateAction.TRIGGER_HOSTILE, "衛兵"),
                "npc:test",
                player,
            )
            is True
        )
        assert npc.is_hostile is True
        assert rel_mgr.updates == [("衛兵", "betray", -50, -50)]

    def test_trigger_hostile_unknown_npc_fails(self):
        """対象 NPC が場にいなければ発火は失敗する"""
        gate = ReputationGate(HostileGateEngine([]))
        assert (
            gate.fire_gate(
                self._make_threshold(GateAction.TRIGGER_HOSTILE, "衛兵"),
                "npc:test",
                GatePlayer(),
            )
            is False
        )

    def test_remove_hostile_clears_flag(self):
        """REMOVE_HOSTILE は敵対フラグを解除する"""
        npc = StubNPC("衛兵")
        npc.is_hostile = True
        gate = ReputationGate(HostileGateEngine([npc]))
        assert (
            gate.fire_gate(
                self._make_threshold(GateAction.REMOVE_HOSTILE, "衛兵"),
                "npc:test",
                GatePlayer(),
            )
            is True
        )
        assert npc.is_hostile is False

    def test_custom_action_invoked_with_context(self):
        """CUSTOM アクションは登録済みコールバックを (engine, player, params) で呼ぶ"""
        gate = ReputationGate(GateEngine())
        calls: list[tuple] = []

        def reward(eng, player, params):
            calls.append((eng, player, params))
            return True

        gate.register_custom_action("quest_reward", reward)
        assert (
            gate.fire_gate(
                self._make_threshold(GateAction.CUSTOM, "quest_reward", {"gold": 100}),
                "npc:test",
                GatePlayer(),
            )
            is True
        )
        assert len(calls) == 1
        assert calls[0][2] == {"gold": 100}

    def test_unregistered_custom_action_fails(self):
        """未登録のカスタムアクションは発火に失敗する"""
        gate = ReputationGate(GateEngine())
        assert (
            gate.fire_gate(
                self._make_threshold(GateAction.CUSTOM, "missing_action"),
                "npc:test",
                GatePlayer(),
            )
            is False
        )


# ---------------------------------------------------------------------------
# combat_system 経由のフック統合
# ---------------------------------------------------------------------------


class TestCombatKarmaHook:
    """combat_system 経由のカルマイベントフック統合テスト"""

    @staticmethod
    def _engine(player) -> KarmaEngine:
        engine = KarmaEngine(player)
        engine.karma_manager = KarmaManager()
        return engine

    def test_monster_kill_feeds_defeat_monster(self):
        """monster 阵営の撃破フックは defeat_monster (善悪 +1) として反映される"""
        player = KarmaPlayer()
        engine = self._engine(player)
        CombatSystem(engine)._apply_karma_action(
            engine, StubKillTarget(name="ゴブリン", faction=FACTION_MONSTER)
        )
        assert player.karma_good_evil == 1
        assert player.karma_law_chaos == 0

    def test_innocent_kill_feeds_murder_innocent(self):
        """非 monster 阵営 (町人・衛兵) の撃破フックは murder_innocent (善悪 -5) として反映される"""
        player = KarmaPlayer()
        engine = self._engine(player)
        CombatSystem(engine)._apply_karma_action(
            engine, StubKillTarget(name="町人", faction="townsman")
        )
        assert player.karma_good_evil == -5
        assert player.karma_law_chaos == -2

    def test_kill_without_faction_defaults_to_monster(self):
        """faction 属性を持たない撃破対象は monster 扱いになる"""
        player = KarmaPlayer()
        engine = self._engine(player)
        CombatSystem(engine)._apply_karma_action(engine, StubKillTarget(name="スライム"))
        assert player.karma_good_evil == 1

    def test_hook_without_karma_manager_is_noop(self):
        """karma_manager が無いエンジンではフックは何もせずエラーにもならない"""
        player = KarmaPlayer()
        engine = KarmaEngine(player)  # karma_manager 未設定
        CombatSystem(engine)._apply_karma_action(
            engine, StubKillTarget(name="町人", faction="townsman")
        )
        assert player.karma_good_evil == 0

    def test_hook_without_player_is_noop(self):
        """player が無いエンジンではフックは何もしない"""
        engine = self._engine(None)
        CombatSystem(engine)._apply_karma_action(
            engine, StubKillTarget(name="ゴブリン", faction=FACTION_MONSTER)
        )
        assert engine.player is None

    def test_massacre_reaches_demon_stage_with_warnings(self):
        """無辜の民の連続撃破でカルマが下がり、大悪への段階変化が WARNING ログで通知される"""
        player = KarmaPlayer()
        engine = self._engine(player)
        combat = CombatSystem(engine)
        target = StubKillTarget(name="町人", faction="townsman")
        for _ in range(10):
            combat._apply_karma_action(engine, target)
        assert player.karma_good_evil == -50
        assert player.karma_stage == "大悪"
        assert player.epilogue_karma_flag == "epilogue_demon"
        # 段階変化ログは 中立→悪 と 悪→大悪 の 2 回のみ
        assert len(engine.logs) == 2
        assert all("カルマ" in text for text, _color, _level in engine.logs)
        assert all(level == "WARNING" for _text, _color, level in engine.logs)


# ---------------------------------------------------------------------------
# pet_system 経由のフック統合
# ---------------------------------------------------------------------------


class TestPetKarmaHook:
    """pet_system 経由のカルマイベントフック統合テスト"""

    def test_altar_offering_feeds_donate(self):
        """祭壇供物フックは donate_to_temple (善悪 +2) として反映される"""
        player = KarmaPlayer()
        engine = KarmaEngine(player)
        engine.karma_manager = KarmaManager()
        PetSystemHandler(engine)._apply_karma_action("donate_to_temple")
        assert player.karma_good_evil == 2
        assert player.karma_law_chaos == 1

    def test_hook_without_karma_manager_is_noop(self):
        """karma_manager が無いエンジンではフックは何もしない"""
        engine = KarmaEngine(KarmaPlayer())
        PetSystemHandler(engine)._apply_karma_action("donate_to_temple")
        assert engine.player.karma_good_evil == 0

    def test_hook_without_player_is_noop(self):
        """player が無いエンジンではフックは何もしない"""
        engine = KarmaEngine(None)
        engine.karma_manager = KarmaManager()
        PetSystemHandler(engine)._apply_karma_action("donate_to_temple")
        assert engine.player is None


# ---------------------------------------------------------------------------
# 撃破後の評判ゲート再評価フック
# ---------------------------------------------------------------------------


class TestReputationGateReevaluationHook:
    """combat_system の評判ゲート再評価フックのテスト"""

    def test_hook_creates_gate_and_unlocks_shop(self):
        """撃破フックは評判ゲートを遅延生成し、解放判定まで行う"""
        player = GatePlayer()
        player.faction_reputation[FACTION_KINGDOM_GARDE] = 30
        engine = KarmaEngine(player)
        CombatSystem(engine)._evaluate_reputation_gates(engine)
        assert isinstance(engine._reputation_gate, ReputationGate)
        assert "royal_shop" in player.gate_unlocked_shops

    def test_hook_without_player_is_noop(self):
        """player が無いエンジンではゲートは生成されない"""
        engine = KarmaEngine(None)
        CombatSystem(engine)._evaluate_reputation_gates(engine)
        assert not hasattr(engine, "_reputation_gate")
