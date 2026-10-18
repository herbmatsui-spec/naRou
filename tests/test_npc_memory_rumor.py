"""
T43 案A: NPC 記憶 + 噂伝播 完成度テスト

- 記憶登録 → 態度変化 → 好感度反映
- 行動フック (notify_player_action) → 目撃記憶 → 噂生成
- 噂伝播 → 時間経過 → NPC 間拡散 (距離/派閥による到達率)
- 情報非対称 (知らない NPC は知らない・語らない)
- 派閥戦争結果の噂化 (sync_faction_wars)
- 会話フック (dialogue_system) による可視化
- combat_system の悪行フックとの整合
"""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from dialogue_system import DialogueManager
from faction_war_system import FactionWar
from karma_system import KarmaRegistry
from npc_memory_system import (
    GLOBAL_MEMORY_REGISTRY,
    MemoryImportance,
    MemoryType,
    NPCMemoryManager,
    attitude_disposition,
    build_memory_dialogue_line,
    get_player_action_impact,
    notify_player_action,
)
from rumor_propagation_system import (
    PLAYER_ACTION_RUMOR_CREDIBILITY,
    DEFAULT_ACTION_RUMOR_CREDIBILITY,
    Rumor,
    RumorEngine,
    RumorPropagationConfig,
    RumorType,
    build_rumor_dialogue_line,
    describe_rumor,
    tick_world_rumors,
)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# テスト用スタブ
# ---------------------------------------------------------------------------


class StubNPC:
    """テスト用 NPC (記憶フックが触る最小限の属性)"""

    def __init__(self, name: str, x: int = 0, y: int = 0, faction_id: str | None = None):
        self.name = name
        self.x = x
        self.y = y
        self.faction_id = faction_id
        self.affection = 50


class StubPlayer:
    def __init__(self, name: str = "player"):
        self.name = name


class StubEngine:
    """テスト用エンジン (entity_manager / player / 任意の faction_war_manager)"""

    def __init__(self, npcs=(), player=None):
        self.npcs = list(npcs)
        self.entity_manager = SimpleNamespace(
            get_all_entities=lambda: self.npcs,
            get_living_entities=lambda: self.npcs,
        )
        self.player = player


@pytest.fixture(autouse=True)
def _clear_memory_registry():
    """GLOBAL_MEMORY_REGISTRY のシングルトン状態を各テストで分離する"""
    GLOBAL_MEMORY_REGISTRY._managers.clear()
    yield
    GLOBAL_MEMORY_REGISTRY._managers.clear()


@pytest.fixture
def always_spread(monkeypatch):
    """random.random を 0.5 固定にして伝播を決定化する (確率 > 0.2 の噂は必ず広がる)"""
    monkeypatch.setattr("rumor_propagation_system.random.random", lambda: 0.5)


# ---------------------------------------------------------------------------
# 記憶登録 → 態度変化 → 好感度
# ---------------------------------------------------------------------------


def test_player_action_registers_memory_and_shifts_attitude():
    """プレイヤー行動が記憶へ登録され、態度値が動く"""
    npc = StubNPC("村人A")
    mgr = GLOBAL_MEMORY_REGISTRY.get(npc)
    assert mgr.get_attitude_towards("player") == 0
    assert attitude_disposition(0) == "中立"

    mgr.record_player_action("murder_innocent", player_id="player")
    attitude = mgr.get_attitude_towards("player")
    assert attitude == get_player_action_impact("murder_innocent")["attitude"]
    assert attitude_disposition(attitude) == "警戒"

    mems = mgr.query(memory_type=MemoryType.PERSONAL_INTERACTION, tags=["player_action"])
    assert len(mems) == 1
    assert mems[0].content["actor_id"] == "player"
    assert mems[0].importance == MemoryImportance.CRITICAL


def test_good_deeds_improve_attitude_and_affection():
    """救済 (善意行動) の積み重ねで態度・好感度が向上する"""
    npc = StubNPC("村人B")
    mgr = GLOBAL_MEMORY_REGISTRY.get(npc)
    mgr.record_player_action("relief_wounded")
    mgr.record_player_action("relief_wounded")
    attitude = mgr.get_attitude_towards("player")
    assert attitude == get_player_action_impact("relief_wounded")["attitude"] * 2
    assert attitude_disposition(attitude) == "友好的"

    affection = mgr.sync_attitude_effects("player")
    assert npc.affection == 50 + attitude // 2
    assert affection == npc.affection


def test_trusted_attitude_from_repeated_good_deeds():
    """善行を重ねると態度が「信頼」まで上がる"""
    npc = StubNPC("村人C")
    mgr = GLOBAL_MEMORY_REGISTRY.get(npc)
    for _ in range(4):
        mgr.record_player_action("relief_wounded")
    attitude = mgr.get_attitude_towards("player")
    assert attitude >= 50
    assert attitude_disposition(attitude) == "信頼"


def test_attitude_clamps_at_extremes():
    """態度値は -100..100 にクランプされ、大悪では敵対的・好感度 0 になる"""
    npc = StubNPC("村人D")
    mgr = GLOBAL_MEMORY_REGISTRY.get(npc)
    for _ in range(7):
        mgr.record_player_action("murder_innocent")
    attitude = mgr.get_attitude_towards("player")
    assert attitude == -100
    assert attitude_disposition(attitude) == "敵対的"
    assert mgr.sync_attitude_effects("player") == 0


def test_attitude_fades_as_memory_decays():
    """時間経過で記憶が減衰し、態度への影響も小さくなる"""
    npc = StubNPC("村人E")
    mgr = GLOBAL_MEMORY_REGISTRY.get(npc)
    base_time = 1000.0
    mgr.record_player_action("murder_innocent", timestamp=base_time)

    fresh = mgr.get_attitude_towards("player", current_time=base_time)
    later = mgr.get_attitude_towards("player", current_time=base_time + 3600.0)
    assert fresh < 0
    assert abs(later) <= abs(fresh)
    assert later < 0  # 残党は残る


def test_unknown_action_is_recorded_but_neutral():
    """未知の行動も記憶には残るが態度は動かない"""
    npc = StubNPC("村人F")
    result = notify_player_action(None, npc, "mysterious_dance", player=StubPlayer())
    assert result["attitude"] == 0
    assert result["rumor"] is None
    mems = GLOBAL_MEMORY_REGISTRY.get(npc).query(tags=["player_action"])
    assert len(mems) == 1


def test_trade_action_is_registered_without_rumor():
    """取引は態度をわずかに改善するが噂にはならない (重要度が低い)"""
    npc = StubNPC("商人")
    result = notify_player_action(None, npc, "trade", player=StubPlayer(), spread=True)
    assert result["attitude"] == get_player_action_impact("trade")["attitude"]
    assert result["attitude"] > 0
    assert result["rumor"] is None
    assert result["affection"] == 50 + result["attitude"] // 2


def test_memory_manager_standalone_api():
    """NPCMemoryManager 単体でもプレイヤー行動の記録・態度集計が動く"""
    npc = StubNPC("solo")
    mgr = NPCMemoryManager(npc)
    mgr.record_player_action("steal", player_id="hero")
    mgr.record_player_action("relief_wounded", player_id="hero")
    # steal (-10) と relief (+15) が合算される
    assert mgr.get_attitude_towards("hero") == 5
    # 別アクターの記憶は態度に影響しない
    assert mgr.get_attitude_towards("someone_else") == 0


# ---------------------------------------------------------------------------
# 行動フック: 目撃記憶と噂生成
# ---------------------------------------------------------------------------


def test_notify_player_action_records_witnesses_and_rumor():
    """悪行は対象・目撃者の記憶へ登録され、重要行動は噂として生成される"""
    victim = StubNPC("被害者", x=0, y=0)
    witness = StubNPC("目撃者", x=2, y=0)
    far = StubNPC("遠くの村人", x=100, y=100)
    player = StubPlayer()
    engine = StubEngine(npcs=[victim, witness, far], player=player)

    result = notify_player_action(engine, victim, "murder_innocent", player=player)

    # 対象 NPC の態度・好感度
    assert result["attitude"] == get_player_action_impact("murder_innocent")["attitude"]
    assert result["affection"] == 50 + result["attitude"] // 2

    # 距離 WITNESS_RADIUS 以内の生存 NPC だけが目撃する
    assert [w.name for w in result["witnesses"]] == ["目撃者"]
    witness_mgr = GLOBAL_MEMORY_REGISTRY.get_by_id("目撃者")
    assert len(witness_mgr.get_witness_of("player")) == 1
    # 目撃者の態度も (目撃分は半減して) 悪化する
    assert witness_mgr.get_attitude_towards("player") == get_player_action_impact(
        "murder_innocent"
    )["attitude"] // 2

    # 遠くの NPC は何も知らない (情報非対称)
    assert GLOBAL_MEMORY_REGISTRY.get_by_id("遠くの村人") is None

    # 重要行動なので噂が生成される (発信元は目撃者)
    assert result["rumor"] is not None
    assert result["rumor"].rumor_type == RumorType.PLAYER_ACTION
    assert result["rumor"].content["subject_id"] == "player"
    assert result["rumor"].origin_npc_id == "目撃者"
    assert result["rumor"] in engine.rumor_engine.get_rumors_known_by("目撃者")


def test_notify_player_action_relief_spreads_positive_rumor():
    """救済は対象の記憶に残り、重要度が高いので噂になる"""
    target = StubNPC("負傷者", x=0, y=0)
    player = StubPlayer()
    engine = StubEngine(npcs=[target], player=player)

    result = notify_player_action(engine, target, "relief_wounded", player=player)

    assert result["attitude"] > 0
    assert result["rumor"] is not None
    assert result["rumor"].base_credibility == pytest.approx(
        PLAYER_ACTION_RUMOR_CREDIBILITY["relief_wounded"]
    )


def test_player_action_rumor_credibility_table():
    """行動ごとの噂信憑性は既定テーブルに従う"""
    npc = StubNPC("発信者")
    engine = StubEngine(npcs=[npc], player=StubPlayer())
    rumor_engine = RumorEngine(engine)

    murder = rumor_engine.inject_player_action_rumor(
        "murder_innocent", origin_npc=npc, origin_location=(0, 0)
    )
    assert murder.base_credibility == pytest.approx(
        PLAYER_ACTION_RUMOR_CREDIBILITY["murder_innocent"]
    )
    exotic = rumor_engine.inject_player_action_rumor(
        "mysterious_dance", origin_npc=npc, origin_location=(0, 0)
    )
    assert exotic.base_credibility == pytest.approx(DEFAULT_ACTION_RUMOR_CREDIBILITY)


# ---------------------------------------------------------------------------
# 噂伝播: 時間経過 → 拡散 → 記憶 → 情報非対称
# ---------------------------------------------------------------------------


def _make_spread_world():
    """発信者・近所・遠方の 3 NPC と噂エンジンを用意する"""
    witness = StubNPC("目撃者", 0, 0, faction_id="townsman")
    near = StubNPC("近所のNPC", 1, 0, faction_id="townsman")
    far = StubNPC("遠方のNPC", 40, 40, faction_id="townsman")
    engine = StubEngine(npcs=[witness, near, far], player=StubPlayer())
    rumor_engine = RumorEngine(engine, RumorPropagationConfig(max_distance=10.0))
    rumor = rumor_engine.inject_player_action_rumor(
        "murder_innocent", origin_npc=witness, origin_location=(0, 0)
    )
    return engine, rumor_engine, rumor, witness, near, far


def test_rumor_spreads_between_npcs_and_shifts_attitude(always_spread):
    """噂は伝播ステップで近隣 NPC へ広がり、聞いた NPC の態度が悪化する"""
    _engine, rumor_engine, rumor, _witness, near, far = _make_spread_world()

    spreads = rumor_engine.propagate_step()
    assert spreads >= 1
    assert "近所のNPC" in rumor.known_by

    # 受信者の記憶にはプレイヤーへの評判イベントが記録される
    near_mgr = GLOBAL_MEMORY_REGISTRY.get_by_id("近所のNPC")
    rep_events = near_mgr.get_reputation_towards("player")
    assert len(rep_events) == 1
    assert rep_events[0].memory_type == MemoryType.REPUTATION_EVENT
    # 伝聞は態度への影響が半減する (直接体験の半分)
    assert near_mgr.get_attitude_towards("player") == get_player_action_impact(
        "murder_innocent"
    )["attitude"] // 2

    # 遠方 (max_distance 外) の NPC は知らないまま
    assert "遠方のNPC" not in rumor.known_by
    assert rumor_engine.get_rumors_known_by("遠方のNPC") == []
    assert GLOBAL_MEMORY_REGISTRY.get_by_id("遠方のNPC") is None


def test_rumor_multi_hop_spread_advances_with_time(always_spread):
    """時間経過 (複数ステップ) で噂が多段に拡散する"""
    a = StubNPC("発信者", 0, 0)
    b = StubNPC("中継者", 1, 0)
    c = StubNPC("末端のNPC", 2, 0)
    engine = StubEngine(npcs=[a, b, c], player=StubPlayer())
    rumor_engine = RumorEngine(engine, RumorPropagationConfig(max_distance=10.0))
    rumor = rumor_engine.inject_player_action_rumor(
        "murder_innocent", origin_npc=a, origin_location=(0, 0)
    )

    spreads = rumor_engine.advance(steps=4)
    assert spreads >= 2
    assert {"発信者", "中継者", "末端のNPC"} <= rumor.known_by


def test_spread_probability_respects_distance_and_faction():
    """伝播確率は距離減衰し、同派閥ボーナスで上昇する (既定の到達率定義を尊重)"""
    engine = StubEngine(npcs=[], player=StubPlayer())
    rumor_engine = RumorEngine(engine)
    rumor_engine.register_npc(StubNPC("a"), (0, 0), faction_id="f1")
    rumor_engine.register_npc(StubNPC("b"), (0, 0), faction_id="f1")

    rumor = Rumor(
        rumor_id="r1",
        rumor_type=RumorType.PLAYER_ACTION,
        content={},
        origin_npc_id="a",
        origin_location=(0, 0),
        timestamp=0.0,
        base_credibility=1.0,
    )
    p_close_same = rumor_engine._calculate_spread_probability(rumor, "a", "b", 5.0)
    p_far_same = rumor_engine._calculate_spread_probability(rumor, "a", "b", 30.0)
    rumor_engine._npc_factions["b"] = "f2"
    p_close_diff = rumor_engine._calculate_spread_probability(rumor, "a", "b", 5.0)

    assert p_close_same > p_far_same  # 距離減衰
    assert p_close_same > p_close_diff  # 同派閥ボーナス


def test_rumor_expiry_removes_stale_rumors():
    """寿命を過ぎた噂は伝播网络から消える (時間経過の効果)"""
    engine = StubEngine(npcs=[], player=StubPlayer())
    rumor_engine = RumorEngine(engine, RumorPropagationConfig(rumor_lifetime=100.0))
    npc = StubNPC("発信者", 0, 0)
    engine.npcs.append(npc)
    rumor = rumor_engine.inject_player_action_rumor(
        "murder_innocent", origin_npc=npc, origin_location=(0, 0)
    )
    assert rumor_engine.get_active_rumor_count() == 1

    rumor_engine.propagate_step(current_time=rumor.timestamp + 1000.0)
    assert rumor_engine.get_active_rumor_count() == 0


def test_propagate_step_syncs_registered_npcs_from_engine():
    """エンジンの生存 NPC が伝播ネットワークへ自動登録される"""
    witness = StubNPC("目撃者", 0, 0)
    listener = StubNPC("聞き手", 1, 0)
    engine = StubEngine(npcs=[witness, listener], player=StubPlayer())
    rumor_engine = RumorEngine(engine)

    assert rumor_engine.sync_registered_npcs() == 2
    assert rumor_engine._npc_locations["目撃者"] == (0, 0)
    assert rumor_engine._npc_locations["聞き手"] == (1, 0)


# ---------------------------------------------------------------------------
# 派閥戦争結果の噂化
# ---------------------------------------------------------------------------


def _make_war_world():
    winner_npc = StubNPC("勝利派閥の兵", 0, 0, faction_id="f_win")
    loser_npc = StubNPC("敗北派閥の兵", 1, 0, faction_id="f_lose")
    far = StubNPC("遥か離れたNPC", 100, 100, faction_id=None)
    engine = StubEngine(npcs=[winner_npc, loser_npc, far], player=StubPlayer())
    rumor_engine = RumorEngine(engine, RumorPropagationConfig(max_distance=10.0))
    return engine, rumor_engine, winner_npc, loser_npc, far


def test_faction_war_result_becomes_rumor_and_spreads(always_spread):
    """派閥戦争の終結が検出され、勝利派閥 NPC を発信元とした噂が広がる"""
    engine, rumor_engine, _winner_npc, loser_npc, far = _make_war_world()

    # ベースライン同期: この時点で終了済みの戦争は噂化しない
    engine.faction_war_manager = SimpleNamespace(
        wars={}, check_war_conditions=lambda a, b: False
    )
    assert rumor_engine.sync_faction_wars(current_turn=0) == []
    assert rumor_engine.get_active_rumor_count() == 0

    # その後、戦争が終結 (勝利: f_win)
    war = FactionWar(attacker_id="f_win", defender_id="f_lose")
    war.status = "ended"
    war.winner_id = "f_win"
    engine.faction_war_manager.wars["f_lose&f_win"] = war

    # 次の同期で新たに終結した戦争だけが噂化される
    rumors = rumor_engine.sync_faction_wars(current_turn=100)
    assert len(rumors) == 1
    rumor = rumors[0]
    assert rumor.rumor_type == RumorType.FACTION_MOVE
    assert rumor.content["winner_id"] == "f_win"
    assert rumor.content["loser_id"] == "f_lose"

    # 二重同期で噂が重複生成されない
    assert rumor_engine.sync_faction_wars(current_turn=101) == []

    # 時間経過で周辺 NPC へ伝播する
    rumor_engine.propagate_step()
    assert "敗北派閥の兵" in rumor.known_by
    # 遥か離れた NPC は戦争の結末を知らない (情報非対称)
    assert "遥か離れたNPC" not in rumor.known_by


def test_sync_faction_wars_ignores_active_wars_and_missing_manager():
    """進行中の戦争は噂化せず、派閥マネージャが無い環境でもエラーにならない"""
    engine, rumor_engine, *_ = _make_war_world()
    active = FactionWar(attacker_id="f_win", defender_id="f_lose")
    engine.faction_war_manager = SimpleNamespace(wars={"f_lose&f_win": active})
    assert rumor_engine.sync_faction_wars(current_turn=10) == []
    assert rumor_engine.get_active_rumor_count() == 0

    bare_rumor_engine = RumorEngine(SimpleNamespace(player=None))
    assert bare_rumor_engine.sync_faction_wars() == []


def test_faction_war_rumor_describes_winner():
    """戦争の噂は会話文として勝敗を説明できる"""
    npc = StubNPC("発信者", 0, 0, faction_id="f_win")
    engine = StubEngine(npcs=[npc], player=StubPlayer())
    rumor_engine = RumorEngine(engine)
    rumor = rumor_engine.inject_faction_war_rumor("f_win", "f_lose", npc, (0, 0))

    line = describe_rumor(rumor)
    assert "f_win" in line and "f_lose" in line
    assert line.startswith("「")


# ---------------------------------------------------------------------------
# 会話フック (可視化)
# ---------------------------------------------------------------------------


def test_dialogue_references_player_memory():
    """記憶を持つ NPC は会話でプレイヤーの行動に言及する"""
    npc = StubNPC("記憶のある村人")
    GLOBAL_MEMORY_REGISTRY.get(npc).record_player_action("murder_innocent")

    speaker, line = DialogueManager.get_dialogue(npc, StubPlayer(), engine=None)
    assert speaker == "記憶のある村人"
    assert line != DialogueManager.DEFAULT_NPC_DIALOGUE
    assert "殺人" in line


def test_dialogue_without_memory_stays_default():
    """記憶も噂も無い NPC は従来どおりの既定台詞を話す"""
    npc = StubNPC("初対面の村人")
    _speaker, line = DialogueManager.get_dialogue(npc, StubPlayer(), engine=None)
    assert line == DialogueManager.DEFAULT_NPC_DIALOGUE


def test_dialogue_references_known_rumor_only():
    """噂を知る NPC だけが噂を語り、知らない NPC は語らない"""
    knower = StubNPC("噂好きのNPC", 0, 0)
    ignorant = StubNPC("何も知らないNPC", 50, 50)
    engine = StubEngine(npcs=[knower, ignorant], player=StubPlayer())
    rumor_engine = RumorEngine(engine)
    rumor_engine.inject_player_action_rumor(
        "murder_innocent", origin_npc=knower, origin_location=(0, 0)
    )

    line = build_rumor_dialogue_line(rumor_engine, "噂好きのNPC", player_name="player")
    assert line is not None
    assert "人を斬り殺した" in line
    assert "お前" in line and "player" not in line  # 主語は会話形へ置換される
    # 噂が届いていない NPC は沈黙する
    assert build_rumor_dialogue_line(rumor_engine, "何も知らないNPC") is None

    # dialogue_system 経由でも同じ振る舞いになる
    engine.rumor_engine = rumor_engine
    _speaker, text = DialogueManager.get_dialogue(knower, StubPlayer(), engine)
    assert "人を斬り殺した" in text
    _speaker, text2 = DialogueManager.get_dialogue(ignorant, StubPlayer(), engine)
    assert text2 == DialogueManager.DEFAULT_NPC_DIALOGUE


def test_memory_dialogue_line_builder_direct():
    """build_memory_dialogue_line は記憶の極性に応じた台詞を返す"""
    npc = StubNPC("台詞確認用")
    assert build_memory_dialogue_line(npc) is None  # 記憶が無い
    mgr = GLOBAL_MEMORY_REGISTRY.get(npc)
    for _ in range(4):
        mgr.record_player_action("relief_wounded")
    line = build_memory_dialogue_line(npc)
    assert line is not None and "看病" in line


# ---------------------------------------------------------------------------
# ゲームループ連携
# ---------------------------------------------------------------------------


def test_tick_world_rumors_lazy_creates_engine_and_never_raises():
    """tick_world_rumors は rumor_engine を遅延生成し、例外を外部へ漏らさない"""
    engine = StubEngine(npcs=[], player=StubPlayer())
    assert getattr(engine, "rumor_engine", None) is None
    tick_world_rumors(engine)
    assert engine.rumor_engine is not None
    tick_world_rumors(engine)  # 2 回目以降は既存エンジンを再利用


def test_tick_world_rumors_with_bare_namespace_is_noop():
    """最小エンジンスタブでも定期処理がエラーにならない"""
    engine = SimpleNamespace(turns=0)
    tick_world_rumors(engine)
    # rumor_engine は生成されるが、伝播対象が無いため何も起きない
    assert getattr(engine, "rumor_engine", None) is not None
    assert engine.rumor_engine.get_active_rumor_count() == 0


# ---------------------------------------------------------------------------
# combat_system の悪行フックとの整合 (R4-C)
# ---------------------------------------------------------------------------


class StubKillTarget:
    """combat_system フック用の撃破対象スタブ"""

    def __init__(self, name: str, faction: str | None = None):
        self.name = name
        self.faction = faction
        self.affection = 50


@pytest.fixture
def karma_registry_loaded():
    """data/karma.yaml (無ければ既定値) をカルマレジストリへ読み込む"""
    KarmaRegistry().load(os.path.join(_REPO_ROOT, "data", "karma.yaml"))
    yield


def test_combat_murder_hook_records_memory_and_rumor(karma_registry_loaded):
    """combat_system の悪行フックが NPC 記憶・態度・噂へ連鎖する (R4-C と整合)"""
    from engine.systems.combat_system import CombatSystem
    from karma_system import KarmaManager

    player = SimpleNamespace(
        name="player", karma_good_evil=0, karma_law_chaos=0, template_exposure=0
    )
    engine = SimpleNamespace(karma_manager=KarmaManager(), player=player)
    target = StubKillTarget("町人", faction="townsman")

    CombatSystem(engine)._apply_karma_action(engine, target)

    # 既存のカルマフックは維持される
    assert player.karma_good_evil == -5
    # 撃破された NPC の記憶に悪行が残り、態度が最悪方向へ動く
    mgr = GLOBAL_MEMORY_REGISTRY.get_by_id("町人")
    assert mgr is not None
    assert mgr.get_attitude_towards("player") == get_player_action_impact("murder_innocent")[
        "attitude"
    ]
    # 噂エンジンが遅延生成され、悪行の噂が登録される
    assert getattr(engine, "rumor_engine", None) is not None
    assert engine.rumor_engine.get_active_rumor_count() == 1


def test_combat_monster_kill_does_not_create_evil_rumor(karma_registry_loaded):
    """魔物撃破 (善行扱い) では悪行の噂は生成されない"""
    from engine.systems.combat_system import CombatSystem
    from karma_system import KarmaManager

    player = SimpleNamespace(
        name="player", karma_good_evil=0, karma_law_chaos=0, template_exposure=0
    )
    engine = SimpleNamespace(karma_manager=KarmaManager(), player=player)
    target = StubKillTarget("ゴブリン", faction="monster")

    CombatSystem(engine)._apply_karma_action(engine, target)

    assert player.karma_good_evil == 1
    assert getattr(engine, "rumor_engine", None) is None
    assert GLOBAL_MEMORY_REGISTRY.get_by_id("ゴブリン") is None


def test_entity_relief_hook_records_memory(karma_registry_loaded):
    """entity_system の看病フックが対象 NPC の記憶へ救済を登録する"""
    from engine.systems.entity_system import EntitySystem
    from karma_system import KarmaManager

    player = SimpleNamespace(
        name="player", karma_good_evil=0, karma_law_chaos=0, template_exposure=0
    )
    engine = SimpleNamespace(
        karma_manager=KarmaManager(), player=player, log=lambda *a, **k: None
    )
    neighbor = StubNPC("負傷した村人")
    neighbor.hp = 5
    neighbor.max_hp = 20
    neighbor.faction = "townsman"

    EntitySystem(engine)._relieve_wounded_neighbor(neighbor)

    assert player.karma_good_evil == 2  # 既存のカルマフック
    mgr = GLOBAL_MEMORY_REGISTRY.get_by_id("負傷した村人")
    assert mgr is not None
    assert mgr.get_attitude_towards("player") == get_player_action_impact("relief_wounded")[
        "attitude"
    ]
    # 看病は重要度が高いので噂も生成される
    assert engine.rumor_engine.get_active_rumor_count() == 1
