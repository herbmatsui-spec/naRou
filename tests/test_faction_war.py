"""派閥戦争ライフサイクルのテスト (T36 案A)

開戦 → 進行 → 決着 → 結果反映の一連、プレイヤー影響フック (撃破/善意悪行/拠点攻防)、
勝敗判定の境界を検証する。
"""

from __future__ import annotations

import pytest

from faction_war_system import (
    REGISTRY,
    WAR_BOSS_GAUGE,
    WAR_DEED_GAUGE,
    WAR_END_INFLUENCE_LOSS,
    WAR_END_INFLUENCE_WIN,
    WAR_END_PRICE_SHIFT,
    WAR_END_REP_CAP,
    WAR_GAUGE_LIMIT,
    WAR_KILL_GAUGE,
    WAR_MAX_DRIFT,
    WAR_PROGRESS_INTERVAL,
    WAR_RESTART_COOLDOWN_TURNS,
    FactionWarData,
    FactionWarManager,
    FactionWarRegistry,
)

ATTACKER_ID = "war_test_attacker"
DEFENDER_ID = "war_test_defender"


# ---------------------------------------------------------------------------
# テスト用スタブ
# ---------------------------------------------------------------------------


class WarPlayer:
    """派閥評判と座標を持つ最小プレイヤースタブ"""

    def __init__(self):
        self.faction_reputation = {}
        self.x = 10
        self.y = 10


class StubKernel:
    """faction_war_manager のみ登録済みの Kernel スタブ"""

    def __init__(self, war_manager):
        self._war_manager = war_manager

    def has_system(self, name):
        return name == "faction_war_manager"

    def get_system(self, name):
        return self._war_manager if name == "faction_war_manager" else None


class StubEngine:
    """FactionManager 連携テスト用の最小エンジンスタブ"""

    def __init__(self, war_manager, turns=0, player=None):
        self.kernel = StubKernel(war_manager)
        self.turns = turns
        self.player = player if player is not None else WarPlayer()
        self.floating_texts = []
        self.logs = []

    def log(self, text, color=(230, 230, 230), level="INFO"):
        self.logs.append((text, color, level))


class KillTarget:
    """撃破対象のスタブ (属性は明示的にセットされたもののみ持つ)"""

    def __init__(self, name="兵士", faction_id=None, is_boss=False, is_hostile=None):
        self.name = name
        if faction_id is not None:
            self.faction_id = faction_id
        if is_boss:
            self.is_boss = True
        if is_hostile is not None:
            self.is_hostile = is_hostile


@pytest.fixture
def war_env():
    """2 つのライバル派閥を登録し、テスト後にレジストリを復元する"""
    saved_factions = dict(REGISTRY._factions)
    saved_loaded = REGISTRY._loaded
    REGISTRY._factions.clear()
    REGISTRY._loaded = True
    attacker = FactionWarData(
        id=ATTACKER_ID,
        name="王国軍",
        influence=70,
        territories=["王都", "要塞"],
        rival_factions=[DEFENDER_ID],
    )
    defender = FactionWarData(
        id=DEFENDER_ID,
        name="盗賊団",
        influence=40,
        territories=["隠れ家", "港町"],
        rival_factions=[ATTACKER_ID],
    )
    REGISTRY._factions[ATTACKER_ID] = attacker
    REGISTRY._factions[DEFENDER_ID] = defender
    yield attacker, defender
    REGISTRY._factions.clear()
    REGISTRY._factions.update(saved_factions)
    REGISTRY._loaded = saved_loaded


@pytest.fixture
def active_war(war_env):
    """開戦済みの戦争 (進行中) を用意する"""
    manager = FactionWarManager()
    war = manager.start_war(ATTACKER_ID, DEFENDER_ID)
    assert war is not None
    return manager, war


# ---------------------------------------------------------------------------
# ライフサイクル一連: 開戦 → 進行 → 決着 → 結果反映
# ---------------------------------------------------------------------------


class TestWarLifecycle:
    def test_full_lifecycle_start_progress_end_results(self, war_env):
        """開戦 → ゲージ進行 → 決着 → 結果反映が一連で動く"""
        attacker, defender = war_env
        player = WarPlayer()
        manager = FactionWarManager()

        # 開戦: ライバル関係 + 影響力差 30 >= 閾値
        events = manager.progress_wars(0, player)
        started = [e for e in events if e["type"] == "war_started"]
        assert len(started) == 1
        war = manager.get_war(ATTACKER_ID, DEFENDER_ID)
        assert war is not None and war.status == "active"
        assert war.attacker_id == ATTACKER_ID  # 影響力の高い側が攻撃側

        # 進行: WAR_PROGRESS_INTERVAL 経過で攻撃側 (影響力優位) にゲージが傾く
        manager.progress_wars(WAR_PROGRESS_INTERVAL - 1, player)
        assert war.gauge == 0.0
        manager.progress_wars(WAR_PROGRESS_INTERVAL * 5, player)
        assert war.gauge > 0

        # 決着: ゲージ上限で攻撃側の決定的勝利
        war.gauge = WAR_GAUGE_LIMIT
        events = manager.progress_wars(WAR_PROGRESS_INTERVAL * 5 + 1, player)
        ended = [e for e in events if e["type"] == "war_ended"]
        assert len(ended) == 1
        assert ended[0]["winner_id"] == ATTACKER_ID
        assert ended[0]["reason"] == "decisive"
        assert war.status == "ended" and war.winner_id == ATTACKER_ID

        # 結果反映: 影響力 / 物価 / 領土
        assert attacker.influence == 70 + WAR_END_INFLUENCE_WIN
        assert defender.influence == 40 - WAR_END_INFLUENCE_LOSS
        assert attacker.price_modifier == pytest.approx(-WAR_END_PRICE_SHIFT)
        assert defender.price_modifier == pytest.approx(WAR_END_PRICE_SHIFT)
        assert defender.territories == ["隠れ家"]  # 1 領土が移動
        assert attacker.territories == ["王都", "要塞", "港町"]

    def test_start_requires_rival_and_influence_gap(self, war_env):
        """ライバル関係が無い/影響力差が小さいペアは自動開戦しない"""
        attacker, defender = war_env
        # 影響力差を閾値未満に
        attacker.influence = 55
        manager = FactionWarManager()
        events = manager.progress_wars(0, None)
        assert not any(e["type"] == "war_started" for e in events)
        assert manager.get_war(ATTACKER_ID, DEFENDER_ID) is None

        # 差があってもライバル関係が無ければ開戦しない
        attacker.influence = 90
        attacker.rival_factions = []
        defender.rival_factions = []
        events = manager.progress_wars(0, None)
        assert not any(e["type"] == "war_started" for e in events)

    def test_no_duplicate_active_war_between_pair(self, active_war):
        """進行中の戦争があるペアは重複して開戦しない"""
        manager, war = active_war
        events = manager.progress_wars(1, None)
        assert not any(e["type"] == "war_started" for e in events)
        assert manager.get_war(ATTACKER_ID, DEFENDER_ID) is war

    def test_restart_cooldown_blocks_redeclaration(self, war_env):
        """終戦直後の同一ペア再開戦はクールダウン中は抑止される"""
        manager = FactionWarManager()
        manager.progress_wars(0, None)
        war = manager.get_war(ATTACKER_ID, DEFENDER_ID)
        war.gauge = WAR_GAUGE_LIMIT
        manager.progress_wars(1, None)
        assert war.status == "ended"

        events = manager.progress_wars(2, None)
        assert not any(e["type"] == "war_started" for e in events)
        # クールダウン明け+戦力差が開いたままなら再開戦し得る
        events = manager.progress_wars(1 + WAR_RESTART_COOLDOWN_TURNS, None)
        assert any(e["type"] == "war_started" for e in events)

    def test_manual_start_war_api(self, war_env):
        """start_war はクエスト等からの手動開戦に使え、get_active_war で参照できる"""
        manager = FactionWarManager()
        war = manager.start_war(ATTACKER_ID, DEFENDER_ID, start_turn=100)
        assert war is not None
        assert manager.get_active_war(ATTACKER_ID) is war
        assert manager.get_active_war(DEFENDER_ID) is war
        # 重複開戦は拒否
        assert manager.start_war(ATTACKER_ID, DEFENDER_ID) is None
        # 未登録派閥・同一派閥は拒否
        assert manager.start_war(ATTACKER_ID, "unknown") is None
        assert manager.start_war(ATTACKER_ID, ATTACKER_ID) is None

    def test_gauge_drift_clamped(self, war_env):
        """自然変動量は影響力差/10 を上限でクランプする"""
        attacker, defender = war_env
        attacker.influence = 95
        defender.influence = 5
        manager = FactionWarManager()
        manager.progress_wars(0, None)
        war = manager.get_war(ATTACKER_ID, DEFENDER_ID)
        manager.progress_wars(WAR_PROGRESS_INTERVAL, None)
        assert war.gauge == pytest.approx(WAR_MAX_DRIFT)

    def test_gauge_drift_defender_side_negative(self, war_env):
        """影響力が劣る側を攻撃側にした場合、ゲージは防衛側へ傾く"""
        attacker, defender = war_env
        attacker.influence = 30
        defender.influence = 80
        manager = FactionWarManager()
        war = manager.start_war(ATTACKER_ID, DEFENDER_ID)
        manager.progress_wars(WAR_PROGRESS_INTERVAL, None)
        assert war.gauge < 0


# ---------------------------------------------------------------------------
# プレイヤー影響の反映
# ---------------------------------------------------------------------------


class TestPlayerInfluence:
    def test_record_kill_shifts_gauge_toward_opponent(self, active_war):
        """派閥 NPC 撃破は対戦側へゲージを傾け、対戦側の貢献に記録される"""
        manager, war = active_war
        # 防衛側 NPC の撃破 → 攻撃側にゲージ + 貢献
        delta = manager.record_kill(DEFENDER_ID)
        assert delta == WAR_KILL_GAUGE
        assert war.gauge == WAR_KILL_GAUGE
        assert war.player_contributions[ATTACKER_ID] == 1
        # 攻撃側 NPC の撃破 → 逆方向
        delta = manager.record_kill(ATTACKER_ID)
        assert delta == -WAR_KILL_GAUGE
        assert war.gauge == 0.0
        assert war.player_contributions[DEFENDER_ID] == 1

    def test_record_kill_boss_bigger_shift(self, active_war):
        """ボス級の撃破は拠点攻防級の戦果として大きく反映される"""
        manager, war = active_war
        delta = manager.record_kill(DEFENDER_ID, boss=True)
        assert delta == WAR_BOSS_GAUGE
        assert war.player_contributions[ATTACKER_ID] == 1

    def test_record_deed_good_and_evil(self, active_war):
        """善意は当該派閥を後押しし、悪行は削ぐ"""
        manager, war = active_war
        # 攻撃側への善意 → ゲージ +
        delta = manager.record_deed(ATTACKER_ID, good=True)
        assert delta == WAR_DEED_GAUGE
        assert war.player_contributions[ATTACKER_ID] == 1
        # 攻撃側への悪行 → ゲージ -
        delta = manager.record_deed(ATTACKER_ID, good=False)
        assert delta == -WAR_DEED_GAUGE
        assert war.player_contributions[ATTACKER_ID] == 0
        # 防衛側への善意 → ゲージ - (防衛側優勢方向)
        delta = manager.record_deed(DEFENDER_ID, good=True)
        assert delta == -WAR_DEED_GAUGE
        assert war.player_contributions[DEFENDER_ID] == 1

    def test_record_territory_battle(self, active_war):
        """拠点攻防の成否がゲージに反映される"""
        manager, war = active_war
        delta = manager.record_territory_battle(ATTACKER_ID, success=True)
        assert delta == WAR_BOSS_GAUGE
        delta = manager.record_territory_battle(ATTACKER_ID, success=False)
        assert delta == -WAR_BOSS_GAUGE
        assert war.gauge == 0.0
        assert war.player_contributions[ATTACKER_ID] == 0

    def test_player_hooks_without_active_war_return_zero(self, war_env):
        """戦争が進行していない場合、影響フックは 0.0 を返すだけで動作する"""
        manager = FactionWarManager()
        assert manager.record_kill(ATTACKER_ID) == 0.0
        assert manager.record_deed(DEFENDER_ID, good=True) == 0.0
        assert manager.record_territory_battle(ATTACKER_ID, success=True) == 0.0
        assert manager.get_active_wars() == []

    def test_contributions_convert_to_reputation_on_war_end(self, active_war):
        """終戦時にプレイヤー貢献が派閥評判へ変換される (上限付き)"""
        manager, war = active_war
        player = WarPlayer()
        for _ in range(3):
            manager.record_kill(DEFENDER_ID)  # 攻撃側へ +3
        manager.record_deed(DEFENDER_ID, good=True)  # 防衛側へ +1
        war.gauge = WAR_GAUGE_LIMIT  # 決着させる
        manager.end_war(war, current_turn=10, player=player)
        assert war.winner_id == ATTACKER_ID
        assert player.faction_reputation[ATTACKER_ID] == 3
        assert player.faction_reputation[DEFENDER_ID] == 1
        # 変換済みの貢献はクリアされる
        assert war.player_contributions == {}

    def test_contribution_conversion_capped(self, active_war):
        """評判変換は 1 派閥あたり WAR_END_REP_CAP で頭打ちになる"""
        manager, war = active_war
        player = WarPlayer()
        for _ in range(50):
            manager.record_kill(DEFENDER_ID)
        manager.end_war(war, current_turn=10, player=player)
        assert player.faction_reputation[ATTACKER_ID] == WAR_END_REP_CAP

    def test_faction_manager_routes_faction_kill_to_war(self, active_war):
        """FactionManager 経由の撃破イベントが戦争ゲージへ反映される (combat フック)"""
        from managers.faction_manager import FactionManager

        manager, war = active_war
        engine = StubEngine(manager, turns=1)
        engine.player.faction_reputation = {ATTACKER_ID: 5}

        FactionManager().update_kill_reputation(engine, KillTarget(faction_id=DEFENDER_ID))

        assert war.gauge == WAR_KILL_GAUGE
        assert war.player_contributions[ATTACKER_ID] == 1

    def test_faction_manager_patron_gains_from_monster_kill(self, active_war):
        """派閥外の敵対モンスター撃破は支持派閥 (最も評判が高い派閥) の戦果になる"""
        from managers.faction_manager import FactionManager

        manager, war = active_war
        player = WarPlayer()
        player.faction_reputation = {DEFENDER_ID: 8, ATTACKER_ID: 3}
        engine = StubEngine(manager, turns=1, player=player)

        FactionManager().update_kill_reputation(engine, KillTarget(name="ゴブリン"))

        # 最も評判の高い防衛側の戦果 → ゲージは防衛側 (負方向) へ
        assert war.player_contributions[DEFENDER_ID] == 1
        assert war.player_contributions.get(ATTACKER_ID, 0) == 0

    def test_faction_manager_civilian_kill_not_counted(self, active_war):
        """非敵対 (is_hostile=False) の派閥外存在の撃破は戦況に影響しない"""
        from managers.faction_manager import FactionManager

        manager, war = active_war
        player = WarPlayer()
        player.faction_reputation = {ATTACKER_ID: 5}
        engine = StubEngine(manager, turns=1, player=player)

        FactionManager().update_kill_reputation(
            engine, KillTarget(name="村人", is_hostile=False)
        )

        assert war.gauge == 0.0
        assert war.player_contributions == {}

    def test_faction_manager_civilian_faction_npc_is_evil_deed(self, active_war):
        """非敵対の攻撃側派閥 NPC 撃破は防衛側有利 (撃破) + 悪行 (攻撃側削り) になる"""
        from managers.faction_manager import FactionManager

        manager, war = active_war
        engine = StubEngine(manager, turns=1)

        FactionManager().update_kill_reputation(
            engine, KillTarget(faction_id=ATTACKER_ID, is_hostile=False)
        )

        # 撃破: 攻撃側 NPC なので防衛側へ +WAR_KILL_GAUGE (ゲージ -5)
        # 悪行: 攻撃側への悪行でさらにゲージ -WAR_DEED_GAUGE
        assert war.gauge == pytest.approx(-WAR_KILL_GAUGE - WAR_DEED_GAUGE)
        assert war.player_contributions[ATTACKER_ID] == -1
        assert war.player_contributions[DEFENDER_ID] == 1

    def test_faction_manager_update_wars_logs_and_floating_text(self, war_env):
        """update_wars が開戦/終結イベントをログと FloatingText へ出力する"""
        from managers.faction_manager import FactionManager

        manager = FactionWarManager()
        engine = StubEngine(manager, turns=0)

        FactionManager().update_wars(engine)

        # 開戦ログ + FloatingText
        assert any("宣戦布告" in text for text, _, _ in engine.logs)
        assert len(engine.floating_texts) == 1
        # 決着
        war = manager.get_war(ATTACKER_ID, DEFENDER_ID)
        war.gauge = WAR_GAUGE_LIMIT
        engine.turns = 1
        FactionManager().update_wars(engine)
        assert any("勝利" in text for text, _, _ in engine.logs)
        assert any("勝利" in ft.text for ft in engine.floating_texts)
        # 結果反映ログ
        assert any("影響力" in text for text, _, _ in engine.logs)

    def test_faction_manager_noop_without_war_system(self, war_env):
        """Kernel に faction_war_manager が無い環境では何もしない"""

        class KernelWithoutWar:
            def has_system(self, name):
                return False

            def get_system(self, name):
                return None

        from managers.faction_manager import FactionManager

        engine = StubEngine(None, turns=0)
        engine.kernel = KernelWithoutWar()
        engine.logs = []
        FactionManager().update_wars(engine)  # must not raise
        FactionManager().update_kill_reputation(engine, KillTarget(name="兵士"))  # must not raise


# ---------------------------------------------------------------------------
# 勝敗判定の境界
# ---------------------------------------------------------------------------


class TestVictoryBoundaries:
    def test_decisive_victory_at_exact_gauge_limit_attacker(self, active_war):
        """ゲージがちょうど +WAR_GAUGE_LIMIT で攻撃側勝利"""
        manager, war = active_war
        winner, reason = manager.determine_winner(war, current_turn=10)
        assert winner is None and reason is None  # まだ決着しない
        war.gauge = WAR_GAUGE_LIMIT
        winner, reason = manager.determine_winner(war, current_turn=10)
        assert winner == ATTACKER_ID and reason == "decisive"

    def test_decisive_victory_at_exact_negative_gauge_limit_defender(self, active_war):
        """ゲージがちょうど -WAR_GAUGE_LIMIT で防衛側勝利"""
        manager, war = active_war
        war.gauge = -WAR_GAUGE_LIMIT
        winner, reason = manager.determine_winner(war, current_turn=10)
        assert winner == DEFENDER_ID and reason == "decisive"

    def test_duration_expiry_higher_gauge_wins(self, active_war):
        """期間満了時はゲージ優勢側の勝利"""
        manager, war = active_war
        war.gauge = 5.0
        expiry = war.start_turn + war.duration_turns
        winner, reason = manager.determine_winner(war, expiry)
        assert winner == ATTACKER_ID and reason == "duration"
        war.gauge = -5.0
        winner, reason = manager.determine_winner(war, expiry)
        assert winner == DEFENDER_ID and reason == "duration"

    def test_duration_expiry_draw_no_effects(self, war_env):
        """期間満了でゲージ拮抗なら停戦: 派閥側の変動は行われない"""
        attacker, defender = war_env
        # 影響力を均等にして自然変動を 0 にし、手動開戦で拮抗した戦争を作る
        attacker.influence = 60
        defender.influence = 60
        manager = FactionWarManager()
        war = manager.start_war(ATTACKER_ID, DEFENDER_ID)
        expiry = war.start_turn + war.duration_turns
        events = manager.progress_wars(expiry, None)
        ended = [e for e in events if e["type"] == "war_ended"]
        assert len(ended) == 1
        assert ended[0]["reason"] == "draw"
        assert war.winner_id is None
        # 停戦: 影響力/物価/領土とも不変
        assert attacker.influence == 60
        assert defender.influence == 60
        assert attacker.price_modifier == 0.0
        assert attacker.territories == ["王都", "要塞"]

    def test_draw_clears_player_contributions(self, active_war):
        """停戦時はプレイヤー貢献が評判へ変換されず破棄される"""
        manager, war = active_war
        player = WarPlayer()
        manager.record_kill(DEFENDER_ID)
        war.gauge = 0.0  # ゲージを拮抗させて停戦に持ち込む
        expiry = war.start_turn + war.duration_turns
        manager.end_war(war, current_turn=expiry, player=player)
        assert war.winner_id is None
        assert player.faction_reputation == {}
        assert war.player_contributions == {}

    def test_territory_transfer_skipped_when_loser_has_single_territory(self, war_env):
        """敗北派閥の領土が 1 つのみの場合、領土移動は行われない"""
        attacker, defender = war_env
        defender.territories = ["隠れ家"]
        manager = FactionWarManager()
        manager.progress_wars(0, None)
        war = manager.get_war(ATTACKER_ID, DEFENDER_ID)
        war.gauge = WAR_GAUGE_LIMIT
        manager.end_war(war, current_turn=10, player=None)
        assert defender.territories == ["隠れ家"]
        assert attacker.territories == ["王都", "要塞"]

    def test_ended_war_not_processed_twice(self, active_war):
        """終結済みの戦争は二重に処理されない"""
        manager, war = active_war
        player = WarPlayer()
        war.gauge = WAR_GAUGE_LIMIT
        first = manager.progress_wars(10, player)
        assert len([e for e in first if e["type"] == "war_ended"]) == 1
        attacker_influence = REGISTRY.get(ATTACKER_ID).influence
        second = manager.progress_wars(11, player)
        assert not any(e["type"] == "war_ended" for e in second)
        assert REGISTRY.get(ATTACKER_ID).influence == attacker_influence
        assert manager.end_war(war, current_turn=12, player=player) is None


# ---------------------------------------------------------------------------
# 連携・配信データ
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_get_faction_status_shape(self, active_war):
        """get_faction_status が Web 配信用フィールドを返す"""
        manager, war = active_war
        manager.record_kill(DEFENDER_ID)
        status = {s["id"]: s for s in manager.get_faction_status()}
        att = status[ATTACKER_ID]
        assert att["name"] == "王国軍"
        assert att["influence"] == 70
        assert att["territories"] == ["王都", "要塞"]
        assert att["at_war"] is True
        assert att["war"]["enemy_id"] == DEFENDER_ID
        assert att["war"]["is_attacker"] is True
        assert att["war"]["gauge"] == pytest.approx(WAR_KILL_GAUGE)
        dfd = status[DEFENDER_ID]
        assert dfd["war"]["is_attacker"] is False

    def test_get_faction_status_peaceful(self, war_env):
        """開戦していない派閥は at_war=False で war を持たない"""
        manager = FactionWarManager()
        status = manager.get_faction_status()
        assert len(status) == 2
        assert all(s["at_war"] is False and "war" not in s for s in status)

    def test_war_result_feeds_reputation_gate(self, war_env):
        """終戦後の影響力変動が評判ゲート (ReputationGate) に反映される"""
        from reputation_gate_system import ReputationGate

        attacker, defender = war_env
        manager = FactionWarManager()
        manager.progress_wars(0, None)
        war = manager.get_war(ATTACKER_ID, DEFENDER_ID)
        war.gauge = WAR_GAUGE_LIMIT
        manager.end_war(war, current_turn=1, player=None)

        player = WarPlayer()
        player.faction_reputation[ATTACKER_ID] = 10

        class GateEngine:
            faction_war_manager = manager

        gate = ReputationGate(GateEngine())
        rep = gate.get_faction_reputation(player, ATTACKER_ID)
        # 派閥影響力 (70+10) - 50 + プレイヤー評判 10
        assert rep == attacker.influence - 50 + 10

    def test_load_faction_war_yaml_compatible(self):
        """既存 data/faction_war.yaml のロードに影響しない (price_modifier 既定 0.0)"""
        registry = FactionWarRegistry()
        registry._factions = {}
        registry._loaded = False
        registry.load("data/faction_war.yaml")
        factions = registry.all()
        assert "kingdom_garde" in factions
        assert all(f.price_modifier == 0.0 for f in factions.values())
        assert factions["kingdom_garde"].influence == 65
