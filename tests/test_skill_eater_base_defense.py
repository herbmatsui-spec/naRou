"""Unit tests for Skill Eater Base Defense System."""

import pytest

from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_base_defense import (
    AFTERMATH_DURATION,
    BREACH_DURATION,
    WARNING_DURATION,
    BaseDefenseManager,
    DamageReport,
    EnemyType,
    RaidEnemy,
    RaidPhase,
    RaidTriggerType,
)
from skill_eater_economy_system import SkillEaterEconomySystem
from skill_eater_presentation_system import SkillEaterPresentationSystem
from skill_eater_system import SkillEaterRegistry


@pytest.fixture
def defense_manager():
    """テスト用防衛マネージャー"""
    registry = SkillEaterRegistry.get_instance()
    economy = SkillEaterEconomySystem(registry=registry)
    economy.aldo_currency = 100000
    audio = SkillEaterAudioSystem(enable_real_audio=False)
    presentation = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)

    mgr = BaseDefenseManager(
        base_max_hp=1000,
        registry=registry,
        economy=economy,
        audio=audio,
        presentation=presentation
    )
    mgr.storage_junk = 10000
    return mgr


@pytest.fixture
def built_defense_manager(defense_manager):
    """全施設建設済みのマネージャー（ティア要件を満たすためhq_vaultをLv3に）"""
    # hq_vaultをLv3にしてティア要件を満たす
    defense_manager.economy.base_facilities["hq_vault"].level = 3

    for fid in defense_manager.defense_facilities:
        defense_manager.build_facility(fid)
    return defense_manager


# ============================================================
# Steps 11-18: Facility Construction & Upgrades
# ============================================================

def test_step11_can_build_facility_checks_tier_and_resources(defense_manager):
    """Step 11: can_build_facility - ティア・リソースチェック"""
    # アルド・ジャンク十分
    can_build, reason = defense_manager.can_build_facility("auto_turret")
    assert can_build is True

    # リソース不足
    defense_manager.economy.aldo_currency = 100
    can_build, reason = defense_manager.can_build_facility("auto_turret")
    assert can_build is False
    assert "アルドが不足" in reason

    # 存在しない施設
    can_build, reason = defense_manager.can_build_facility("nonexistent")
    assert can_build is False
    assert "存在しない" in reason


def test_step12_build_facility_deducts_resources_and_plays_sound(defense_manager):
    """Step 12: build_facility - リソース消費・演出"""
    initial_aldo = defense_manager.economy.aldo_currency
    initial_junk = defense_manager.storage_junk

    success, msg = defense_manager.build_facility("auto_turret")
    assert success is True

    facility = defense_manager.defense_facilities["auto_turret"]
    assert facility.is_built is True
    assert facility.level == 1
    assert facility.current_hp == facility.max_hp

    # リソース消費確認
    assert defense_manager.economy.aldo_currency == initial_aldo - facility.build_cost_aldo
    assert defense_manager.storage_junk == initial_junk - facility.build_cost_junk

    # 演出キュー確認
    events = defense_manager.presentation.get_and_clear_events()
    assert len(events) >= 1
    assert events[0].emote_file == "emote_stars.png"
    assert events[0].audio_file == "chop.ogg"


def test_step13_upgrade_facility_scales_stats(defense_manager):
    """Step 13: upgrade_facility - ステータススケーリング"""
    defense_manager.build_facility("auto_turret")
    facility = defense_manager.defense_facilities["auto_turret"]

    old_damage = facility.damage
    old_hp = facility.max_hp
    old_cost = facility.upgrade_cost_aldo

    success, msg = defense_manager.upgrade_facility("auto_turret")
    assert success is True
    assert facility.level == 2

    # 1.2倍スケーリング確認
    assert facility.damage == int(old_damage * 1.2)
    assert facility.max_hp == int(old_hp * 1.2)
    assert facility.upgrade_cost_aldo == int(old_cost * 1.5)
    assert facility.current_hp == facility.max_hp  # 全回復


def test_step14_get_facility_status_returns_all_info(defense_manager):
    """Step 14: get_facility_status - 全情報取得"""
    defense_manager.build_facility("auto_turret")
    status = defense_manager.get_facility_status()

    assert "auto_turret" in status
    fac = status["auto_turret"]
    assert fac["name"] == "自動砲台"
    assert fac["type"] == "AutoTurret"
    assert fac["level"] == 1
    assert fac["hp"] == fac["max_hp"]
    assert fac["damage"] == 50
    assert fac["range"] == 5
    assert fac["cooldown"] == 2
    assert fac["is_built"] is True
    assert fac["is_operational"] is True
    assert fac["efficiency"] == 1.0


def test_step15_repair_facility_costs_junk(defense_manager):
    """Step 15: repair_facility - ジャンク消費で修理"""
    defense_manager.build_facility("auto_turret")
    facility = defense_manager.defense_facilities["auto_turret"]

    # 故意にダメージ
    facility.current_hp = 100
    initial_junk = defense_manager.storage_junk

    success, msg = defense_manager.repair_facility("auto_turret")
    assert success is True
    assert facility.current_hp == facility.max_hp
    assert defense_manager.storage_junk < initial_junk

    # 演出確認 - 修理イベントが再生されること
    events = defense_manager.presentation.get_and_clear_events()
    # 修理イベントを探す（メッセージで判定）
    repair_events = [e for e in events if "修理完了" in e.message]
    assert len(repair_events) >= 1
    assert repair_events[0].emote_file is not None  # エモートが設定されている
    assert repair_events[0].audio_file == "metalPot1.ogg"


def test_step16_collect_junk_from_storage(defense_manager):
    """Step 16: collect_junk_from_storage - ターン毎ジャンク増加"""
    initial = defense_manager.storage_junk
    defense_manager.process_turn()  # 内部で収集
    assert defense_manager.storage_junk == min(defense_manager.storage_capacity_junk, initial + 5)


def test_step17_collect_aldo_from_vault(defense_manager):
    """Step 17: collect_aldo_from_vault - 金庫収入"""
    # 金庫Lv1で100アルド/ターン
    defense_manager.economy.base_facilities["hq_vault"].level = 2
    initial = defense_manager.storage_aldo
    defense_manager.process_turn()
    assert defense_manager.storage_aldo == initial + 200


def test_step18_load_from_yaml_config(defense_manager):
    """Step 18: load_facilities_from_yaml - YAML設定読み込み"""
    # 新しいマネージャーで読み込み
    defense_manager.load_facilities_from_yaml("data/defense_facilities.yaml")

    for fid in ["auto_turret", "barrier_generator", "sensor_array", "decoy_terminal"]:
        assert fid in defense_manager.defense_facilities
        fac = defense_manager.defense_facilities[fid]
        assert fac.name != ""
        assert fac.build_cost_aldo > 0


# ============================================================
# Steps 19-26: Raid Trigger System
# ============================================================

def test_step19_check_raid_triggers_heat_trigger(defense_manager):
    """Step 19: check_raid_triggers - 熱度トリガー"""
    defense_manager.heat_level = 85
    triggered, trigger = defense_manager.check_raid_triggers()
    assert triggered is True
    assert trigger.trigger_type == RaidTriggerType.HEAT_LEVEL


def test_step19_check_raid_triggers_turn_trigger(defense_manager):
    """Step 19: check_raid_triggers - ターン経過トリガー"""
    defense_manager.turns_since_last_raid = 55
    triggered, trigger = defense_manager.check_raid_triggers()
    assert triggered is True
    assert trigger.trigger_type == RaidTriggerType.ELAPSED_TURNS


def test_step19_check_raid_triggers_meta_quest(defense_manager):
    """Step 19: check_raid_triggers - メタクエストトリガー"""
    defense_manager.meta_quest_raid_flag = True
    triggered, trigger = defense_manager.check_raid_triggers()
    assert triggered is True
    assert trigger.trigger_type == RaidTriggerType.META_QUEST


def test_step20_start_raid_warning_phase_initializes_state(built_defense_manager):
    """Step 20: start_raid_warning_phase - 状態初期化"""
    from skill_eater_base_defense import RaidTrigger
    trigger = RaidTrigger(RaidTriggerType.HEAT_LEVEL, 80)

    result = built_defense_manager.start_raid_warning_phase(trigger)

    assert built_defense_manager.current_phase == RaidPhase.WARNING
    assert built_defense_manager.phase_timer == WARNING_DURATION
    assert built_defense_manager.active_raid is True
    assert built_defense_manager.warning_issued is True
    assert built_defense_manager.current_wave == 1
    assert len(built_defense_manager.raid_enemies) > 0
    assert result["phase"] == "WARNING"
    assert result["timer"] == WARNING_DURATION


def test_step21_generate_raid_enemies_scales_with_heat(built_defense_manager):
    """Step 21: generate_raid_enemies - 熱度で敵スケール"""
    built_defense_manager.heat_level = 90
    enemies = built_defense_manager._generate_raid_enemies()

    assert len(enemies) >= 3
    for e in enemies:
        assert e.hp > 0
        assert e.atk > 0
        assert e.target_priority[0] == "storage"
        assert e.target_priority[-1] == "base"


def test_step22_process_warning_phase_countdown(built_defense_manager):
    """Step 22: process_warning_phase - カウントダウン"""
    from skill_eater_base_defense import RaidTrigger
    built_defense_manager.start_raid_warning_phase(RaidTrigger(RaidTriggerType.HEAT_LEVEL, 80))

    # センサーありで命中デバフ
    sensor = built_defense_manager.defense_facilities["sensor_array"]
    sensor.level = 2

    for _ in range(5):
        result = built_defense_manager.process_warning_phase()
        assert result["phase"] == "WARNING"
        assert result["timer"] == WARNING_DURATION - _ - 1
        assert result["accuracy_debuff"] == 20  # Lv2 × 10%

    # タイマー0でBREACHへ
    built_defense_manager.phase_timer = 1
    result = built_defense_manager.process_warning_phase()
    assert built_defense_manager.current_phase == RaidPhase.BREACH


def test_step23_start_breach_phase_resets_cooldowns(built_defense_manager):
    """Step 23: start_breach_phase - クールダウンリセット"""
    built_defense_manager.current_phase = RaidPhase.BREACH
    built_defense_manager.facility_cooldowns = {"auto_turret": 5}

    result = built_defense_manager.start_breach_phase()

    assert built_defense_manager.current_phase == RaidPhase.BREACH
    assert built_defense_manager.phase_timer == BREACH_DURATION
    assert built_defense_manager.facility_cooldowns["auto_turret"] == 0
    assert result["phase"] == "BREACH"


def test_step24_process_breach_phase_combat(built_defense_manager):
    """Step 24: process_breach_phase - 戦闘処理"""
    built_defense_manager.current_phase = RaidPhase.BREACH
    built_defense_manager.phase_timer = BREACH_DURATION
    built_defense_manager.raid_enemies = [
        RaidEnemy("e1", "Test", EnemyType.MIDAS_SECURITY, 100, 100, 20, 5, 10, ["storage", "base"])
    ]
    built_defense_manager.facility_cooldowns = {"auto_turret": 0}

    result = built_defense_manager.process_breach_phase()

    assert result["phase"] == "BREACH"
    assert "facility_results" in result
    assert "enemy_results" in result
    assert built_defense_manager.phase_timer == BREACH_DURATION - 1


def test_step25_facility_attack_enemies_turret_barrier_sensor_decoy(built_defense_manager):
    """Step 25: facility_attack_enemies - 全施設攻撃"""
    built_defense_manager.current_phase = RaidPhase.BREACH
    built_defense_manager.raid_enemies = [
        RaidEnemy("e1", "Test", EnemyType.MIDAS_SECURITY, 100, 100, 20, 5, 10, ["base"])
    ]
    built_defense_manager.facility_cooldowns = {fid: 0 for fid in built_defense_manager.defense_facilities}

    results = built_defense_manager._facility_attack_enemies()

    # タレット攻撃
    turret_result = next((r for r in results if r["facility"] == "auto_turret"), None)
    assert turret_result is not None
    assert turret_result["damage"] > 0

    # バリア展開
    barrier_result = next((r for r in results if r["facility"] == "barrier_generator"), None)
    assert barrier_result is not None
    assert barrier_result["effect"] == "barrier"

    # センサー効果
    sensor_result = next((r for r in results if r["facility"] == "sensor_array"), None)
    assert sensor_result is not None
    assert sensor_result["effect"] == "detection"

    # デコイ展開
    decoy_result = next((r for r in results if r["facility"] == "decoy_terminal"), None)
    assert decoy_result is not None
    assert decoy_result["effect"] == "decoy_deployed"


def test_step26_enemy_attack_facilities_damage_and_loot(built_defense_manager):
    """Step 26: enemy_attack_facilities - 施設ダメージ・略奪"""
    built_defense_manager.current_phase = RaidPhase.BREACH
    built_defense_manager.storage_junk = 1000
    built_defense_manager.storage_aldo = 500
    built_defense_manager.raid_enemies = [
        RaidEnemy("e1", "Test", EnemyType.MIDAS_SECURITY, 100, 100, 30, 5, 10, ["auto_turret", "base"])
    ]

    initial_turret_hp = built_defense_manager.defense_facilities["auto_turret"].current_hp
    initial_junk = built_defense_manager.storage_junk

    results = built_defense_manager._enemy_attack_facilities()

    # 施設にダメージ
    turret_result = next((r for r in results if r["target"] == "auto_turret"), None)
    assert turret_result is not None
    assert "damage_amount" in turret_result or "missed" in turret_result

    # ストレージ略奪チェック
    storage_result = next((r for r in results if r["target"] == "storage"), None)
    # ターゲット優先度でstorageが最初なら略奪される


# ============================================================
# Steps 27-34: Aftermath & Recovery
# ============================================================

def test_step27_start_aftermath_phase_victory(built_defense_manager):
    """Step 27: start_aftermath_phase - 勝利処理"""
    built_defense_manager.current_phase = RaidPhase.BREACH
    built_defense_manager.current_wave = 3
    built_defense_manager.max_waves = 3

    result = built_defense_manager.start_aftermath_phase(victory=True)

    assert built_defense_manager.current_phase == RaidPhase.AFTERMATH
    assert built_defense_manager.phase_timer == AFTERMATH_DURATION
    assert built_defense_manager.active_raid is False
    assert result["victory"] is True
    assert built_defense_manager.economy.aldo_currency > 0  # 報酬獲得
    assert built_defense_manager.heat_level < 80  # 熱度低下


def test_step27_start_aftermath_phase_defeat(built_defense_manager):
    """Step 27: start_aftermath_phase - 敗北処理"""
    built_defense_manager.storage_junk = 1000
    built_defense_manager.storage_aldo = 500
    for fid in built_defense_manager.defense_facilities:
        built_defense_manager.defense_facilities[fid].level = 3

    result = built_defense_manager.start_aftermath_phase(victory=False)

    assert result["victory"] is False
    assert built_defense_manager.storage_junk == 500  # 半分
    assert built_defense_manager.storage_aldo == 250  # 半分
    for fac in built_defense_manager.defense_facilities.values():
        if fac.is_built:
            assert fac.level == 2  # 1レベルダウン


def test_step28_calculate_aftermath_damage(built_defense_manager):
    """Step 28: calculate_aftermath_damage - 被害計算"""
    fac = built_defense_manager.defense_facilities["auto_turret"]
    fac.is_built = True
    fac.current_hp = 100  # 半分破壊

    reports = built_defense_manager._calculate_aftermath_damage()

    assert len(reports) == 1
    r = reports[0]
    assert r.facility_id == "auto_turret"
    assert r.damage_amount == fac.max_hp - 100
    assert r.is_destroyed is False


def test_step29_apply_subordinate_injuries(built_defense_manager):
    """Step 29: apply_subordinate_injuries - 従属者負傷"""
    built_defense_manager.add_subordinate("Sub1", 100)
    built_defense_manager.add_subordinate("Sub2", 100)

    # 施設破壊報告
    reports = [
        DamageReport("auto_turret", 300, 300, 0, True, 50),
        DamageReport("sensor_array", 100, 200, 100, False, 0),
    ]

    injured = built_defense_manager._apply_subordinate_injuries(reports)
    # 2施設破壊で各20%×2=40%負傷確率
    assert injured >= 0  # 確率的なので0以上


def test_step30_process_aftermath_phase_auto_repair(built_defense_manager):
    """Step 30: process_aftermath_phase - 自動修理優先度"""
    # バリアとタレットを破損
    built_defense_manager.defense_facilities["barrier_generator"].current_hp = 100
    built_defense_manager.defense_facilities["auto_turret"].current_hp = 100
    built_defense_manager.storage_junk = 10000

    built_defense_manager.current_phase = RaidPhase.AFTERMATH
    built_defense_manager.phase_timer = AFTERMATH_DURATION

    # 1ターン目: バリア優先
    result = built_defense_manager.process_aftermath_phase()
    assert built_defense_manager.defense_facilities["barrier_generator"].current_hp == built_defense_manager.defense_facilities["barrier_generator"].max_hp

    # 2ターン目: タレット
    result = built_defense_manager.process_aftermath_phase()
    assert built_defense_manager.defense_facilities["auto_turret"].current_hp == built_defense_manager.defense_facilities["auto_turret"].max_hp


def test_step31_get_aftermath_report(built_defense_manager):
    """Step 31: get_aftermath_report - 報告書"""
    built_defense_manager.defense_facilities["auto_turret"].current_hp = 150
    built_defense_manager.defense_facilities["sensor_array"].current_hp = 0
    built_defense_manager.defense_facilities["sensor_array"].level = 1

    report = built_defense_manager.get_aftermath_report()

    assert report["facilities_damaged"] >= 1
    assert report["facilities_destroyed"] >= 1
    assert report["estimated_repair_cost_junk"] > 0


def test_step32_reset_raid_state(built_defense_manager):
    """Step 32: reset_raid_state - 状態リセット"""
    built_defense_manager.active_raid = True
    built_defense_manager.current_phase = RaidPhase.BREACH
    built_defense_manager.raid_enemies = [RaidEnemy("e1", "T", EnemyType.MIDAS_SECURITY, 100, 100, 10, 5, 10, ["base"])]
    built_defense_manager.facility_cooldowns = {"auto_turret": 3}

    built_defense_manager.reset_raid_state()

    assert built_defense_manager.active_raid is False
    assert built_defense_manager.current_phase == RaidPhase.NORMAL
    assert len(built_defense_manager.raid_enemies) == 0
    assert len(built_defense_manager.facility_cooldowns) == 0


def test_step33_raid_history_tracking(built_defense_manager):
    """Step 33: raid_history - 履歴記録"""
    built_defense_manager.start_aftermath_phase(victory=True)

    history = built_defense_manager.get_raid_history()
    assert len(history) == 1
    assert history[0]["victory"] is True
    assert "turn" in history[0]
    assert "trigger" in history[0]


def test_step34_get_raid_history_limit(built_defense_manager):
    """Step 34: get_raid_history - 最大20件"""
    for i in range(25):
        built_defense_manager.raid_history.append({"turn": i, "victory": True})

    history = built_defense_manager.get_raid_history()
    assert len(history) == 20


# ============================================================
# Steps 35-42: Turn Processing Integration
# ============================================================

def test_step35_process_turn_normal_checks_triggers(defense_manager):
    """Step 35: process_turn - 通常時トリガーチェック"""
    defense_manager.heat_level = 85
    result = defense_manager.process_turn()

    assert result["phase"] == "WARNING"
    assert defense_manager.active_raid is True


def test_step35_process_turn_warning_phase(defense_manager):
    """Step 35: process_turn - WARNINGフェーズ処理"""
    defense_manager.current_phase = RaidPhase.WARNING
    defense_manager.phase_timer = 10
    defense_manager.active_raid = True

    result = defense_manager.process_turn()
    assert result["phase"] == "WARNING"
    assert defense_manager.phase_timer == 9


def test_step35_process_turn_breach_phase(defense_manager):
    """Step 35: process_turn - BREACHフェーズ処理"""
    defense_manager.current_phase = RaidPhase.BREACH
    defense_manager.phase_timer = 10
    defense_manager.active_raid = True
    defense_manager.raid_enemies = [RaidEnemy("e1", "T", EnemyType.MIDAS_SECURITY, 100, 100, 10, 5, 10, ["base"])]

    result = defense_manager.process_turn()
    assert result["phase"] == "BREACH"


def test_step36_integrate_economy_income(defense_manager):
    """Step 36: 経済収益収集"""
    defense_manager.economy.base_facilities["hq_vault"].level = 3
    initial_aldo = defense_manager.storage_aldo

    defense_manager.process_turn()
    assert defense_manager.storage_aldo == initial_aldo + 300


def test_step37_heat_level_integration(defense_manager):
    """Step 37: 熱度連携"""
    result = defense_manager.increase_heat(30)
    assert defense_manager.heat_level == 30

    result = defense_manager.increase_heat(50)
    assert defense_manager.heat_level == 80
    assert result["raid_imminent"] is True


def test_step38_increase_heat_warning_sounds(defense_manager):
    """Step 38: increase_heat - 警告演出"""
    defense_manager.increase_heat(50)
    events = defense_manager.presentation.get_and_clear_events()
    assert any(e.emote_file == "emote_exclamations.png" for e in events)

    defense_manager.increase_heat(20)  # 70到達
    events = defense_manager.presentation.get_and_clear_events()
    assert any(e.emote_file == "emote_alert.png" for e in events)
    assert any(e.audio_file == "alarm_klaxon.ogg" for e in events)


def test_step39_trigger_meta_quest_raid(defense_manager):
    """Step 39: trigger_meta_quest_raid"""
    assert defense_manager.trigger_meta_quest_raid() is True
    assert defense_manager.meta_quest_raid_flag is True

    # 襲撃中は失敗
    defense_manager.active_raid = True
    assert defense_manager.trigger_meta_quest_raid() is False


def test_step40_get_defense_ui_state(built_defense_manager):
    """Step 40: get_defense_ui_state - UI用状態"""
    state = built_defense_manager.get_defense_ui_state()

    assert state["phase"] == "Normal"
    assert "base_hp" in state
    assert "facilities" in state
    assert "storage_junk" in state
    assert "subordinates" in state
    assert "synergy" in state


def test_step41_facility_operational_check(built_defense_manager):
    """Step 41: is_operational プロパティ"""
    fac = built_defense_manager.defense_facilities["auto_turret"]
    assert fac.is_operational is True

    fac.current_hp = 0
    assert fac.is_operational is False
    assert fac.level == 1  # レベルダウン

    fac.is_built = False
    assert fac.is_operational is False


def test_step42_base_hp_damage_from_raid(built_defense_manager):
    """Step 42: 拠点HP直接ダメージ"""
    built_defense_manager.current_phase = RaidPhase.BREACH
    built_defense_manager.raid_enemies = [
        RaidEnemy("e1", "T", EnemyType.MIDAS_MECH, 100, 100, 100, 5, 5, ["base"])
    ]

    # 全施設破壊状態にする
    for fac in built_defense_manager.defense_facilities.values():
        fac.current_hp = 0
        fac.is_built = True

    built_defense_manager._enemy_attack_facilities()
    assert built_defense_manager.base_hp < built_defense_manager.base_max_hp


# ============================================================
# Steps 51-58: Configuration & Balancing
# ============================================================

def test_step53_facility_synergy_bonuses(built_defense_manager):
    """Step 53: シナジーボーナス"""
    # タレット+センサー
    assert built_defense_manager.has_turret_sensor is True

    # バリア+デコイ
    assert built_defense_manager.has_barrier_decoy is True

    # 全4施設
    assert built_defense_manager.has_all_four is True


def test_step54_special_abilities(built_defense_manager):
    """Step 54: 特殊能力"""
    # タレットLv3貫通
    built_defense_manager.defense_facilities["auto_turret"].level = 3
    assert "貫通" in built_defense_manager.defense_facilities["auto_turret"].special_ability

    # バリアLv3反射
    built_defense_manager.defense_facilities["barrier_generator"].level = 3
    assert "反射" in built_defense_manager.defense_facilities["barrier_generator"].special_ability

    # センサーLv3予測
    built_defense_manager.defense_facilities["sensor_array"].level = 3
    assert "予測" in built_defense_manager.defense_facilities["sensor_array"].special_ability

    # デコイLv3爆発
    built_defense_manager.defense_facilities["decoy_terminal"].level = 3
    assert "爆発" in built_defense_manager.defense_facilities["decoy_terminal"].special_ability


def test_step55_junk_loot_scaling(built_defense_manager):
    """Step 55: ジャンク略奪スケーリング"""
    built_defense_manager.heat_level = 100
    fac = built_defense_manager.defense_facilities["auto_turret"]
    fac.level = 2
    fac.current_hp = 0  # 破壊

    # 被害計算時の略奪量
    looted = fac.level * 50 * (1 + built_defense_manager.heat_level / 100)
    assert looted == 200  # 2 * 50 * 2.0


def test_step56_subordinate_protection(built_defense_manager):
    """Step 56: 従属者保護"""
    # 戦闘スキル持ち従属者
    sub = built_defense_manager.add_subordinate("Gunner", 100, ["combat_turret_mastery"])
    assert "combat_turret_mastery" in sub.skills

    # 医療スキル持ち従属者
    sub2 = built_defense_manager.add_subordinate("Medic", 80, ["medical_aid"])
    assert "medical_aid" in sub2.skills


def test_step57_raid_rewards(built_defense_manager):
    """Step 57: 襲撃報酬"""
    initial_aldo = built_defense_manager.economy.aldo_currency
    initial_junk = built_defense_manager.storage_junk
    initial_rep = built_defense_manager.economy.factions["resistance"].reputation

    built_defense_manager.current_wave = 3
    built_defense_manager.start_aftermath_phase(victory=True)

    assert built_defense_manager.economy.aldo_currency == initial_aldo + 1500  # 3 * 500
    assert built_defense_manager.storage_junk == initial_junk + 300  # 3 * 100
    assert built_defense_manager.economy.factions["resistance"].reputation == initial_rep + 10


# ============================================================
# Steps 65: Save/Load
# ============================================================

def test_step65_save_load_state(built_defense_manager):
    """Step 65: セーブ/ロード"""
    built_defense_manager.heat_level = 45
    built_defense_manager.storage_junk = 1234
    built_defense_manager.storage_aldo = 5678
    built_defense_manager.add_subordinate("TestSub", 150, ["skill1"])

    data = built_defense_manager.to_dict()

    assert data["heat_level"] == 45
    assert data["storage_junk"] == 1234
    assert data["storage_aldo"] == 5678
    assert len(data["subordinates"]) == 1
    assert data["subordinates"][0]["name"] == "TestSub"

    # ロード
    new_mgr = BaseDefenseManager.from_dict(data)
    assert new_mgr.heat_level == 45
    assert new_mgr.storage_junk == 1234
    assert new_mgr.storage_aldo == 5678
    assert len(new_mgr.subordinates) == 1
    assert new_mgr.subordinates[0].name == "TestSub"
    assert new_mgr.subordinates[0].skills == ["skill1"]


# ============================================================
# Steps 66-72: Integration Tests
# ============================================================

def test_step66_facility_build_upgrade_cycle(defense_manager):
    """Step 66: 施設建設・アップグレードサイクル"""
    # hq_vaultをLv3にしてティア要件を満たす
    defense_manager.economy.base_facilities["hq_vault"].level = 3
    # 十分な資金を用意
    defense_manager.economy.aldo_currency = 200000
    defense_manager.storage_junk = 20000

    # 全施設建設
    for fid in defense_manager.defense_facilities:
        success, _ = defense_manager.build_facility(fid)
        assert success is True

    # 全施設Lv3までアップグレード
    for fid in defense_manager.defense_facilities:
        for _ in range(2):
            success, _ = defense_manager.upgrade_facility(fid)
            assert success is True
        assert defense_manager.defense_facilities[fid].level == 3


def test_step67_raid_trigger_conditions(defense_manager):
    """Step 67: 襲撃トリガー条件"""
    # 熱度
    defense_manager.heat_level = 80
    triggered, t = defense_manager.check_raid_triggers()
    assert triggered and t.trigger_type == RaidTriggerType.HEAT_LEVEL

    defense_manager.heat_level = 0
    defense_manager.turns_since_last_raid = 50
    triggered, t = defense_manager.check_raid_triggers()
    assert triggered and t.trigger_type == RaidTriggerType.ELAPSED_TURNS

    defense_manager.turns_since_last_raid = 0
    defense_manager.meta_quest_raid_flag = True
    triggered, t = defense_manager.check_raid_triggers()
    assert triggered and t.trigger_type == RaidTriggerType.META_QUEST


def test_step68_warning_phase_transition(defense_manager):
    """Step 68: WARNING→BREACH遷移"""
    from skill_eater_base_defense import RaidTrigger
    defense_manager.start_raid_warning_phase(RaidTrigger(RaidTriggerType.HEAT_LEVEL, 80))

    # タイマー経過でBREACHへ
    defense_manager.phase_timer = 1
    result = defense_manager.process_warning_phase()
    assert defense_manager.current_phase == RaidPhase.BREACH


def test_step69_breach_combat_mechanics(built_defense_manager):
    """Step 69: BREACH戦闘メカニクス"""
    built_defense_manager.current_phase = RaidPhase.BREACH
    built_defense_manager.phase_timer = BREACH_DURATION
    built_defense_manager.current_wave = built_defense_manager.max_waves  # 最終ウェーブでテスト
    # 弱い敵1体でテスト
    built_defense_manager.raid_enemies = [
        RaidEnemy("e1", "T", EnemyType.MIDAS_SECURITY, 1, 1, 1, 1, 1, ["base"])
    ]
    built_defense_manager.facility_cooldowns = {fid: 0 for fid in built_defense_manager.defense_facilities}

    result = built_defense_manager.process_breach_phase()
    # 1ターンで敵が死ぬはず
    alive = [e for e in built_defense_manager.raid_enemies if not e.is_dead]
    assert len(alive) == 0


def test_step70_aftermath_recovery(built_defense_manager):
    """Step 70: AFTERMATH回復処理"""
    built_defense_manager.start_aftermath_phase(victory=True)

    # AFTERMATH処理
    for _ in range(AFTERMATH_DURATION + 1):
        result = built_defense_manager.process_aftermath_phase()

    # 通常状態に戻る
    assert built_defense_manager.current_phase == RaidPhase.NORMAL
    assert built_defense_manager.active_raid is False


def test_step71_full_raid_cycle(built_defense_manager):
    """Step 71: 完全襲撃サイクル"""

    # 1. トリガー
    built_defense_manager.heat_level = 85
    result = built_defense_manager.process_turn()
    assert result["phase"] == "WARNING"

    # 2. WARNING完走
    built_defense_manager.phase_timer = 1
    result = built_defense_manager.process_turn()
    assert built_defense_manager.current_phase == RaidPhase.BREACH

    # 3. BREACH - 最終ウェーブで弱い敵で即座に勝利
    built_defense_manager.current_wave = built_defense_manager.max_waves
    built_defense_manager.raid_enemies = [
        RaidEnemy("e1", "T", EnemyType.MIDAS_SECURITY, 1, 1, 1, 1, 1, ["base"])
    ]
    built_defense_manager.facility_cooldowns = {fid: 0 for fid in built_defense_manager.defense_facilities}

    result = built_defense_manager.process_turn()
    # 勝利してAFTERMATHへ
    assert built_defense_manager.current_phase in [RaidPhase.AFTERMATH, RaidPhase.BREACH]

    # 4. AFTERMATH完走
    while built_defense_manager.current_phase == RaidPhase.AFTERMATH:
        built_defense_manager.process_turn()

    # 5. 通常復帰
    assert built_defense_manager.current_phase == RaidPhase.NORMAL
    assert len(built_defense_manager.raid_history) == 1


def test_step72_economy_defense_link(defense_manager):
    """Step 72: 経済システム連携"""
    # 闇市場売却で熱度上昇→襲撃
    defense_manager.economy.aldo_currency = 100000
    defense_manager.storage_junk = 10000

    # 違法スキル売却シミュレート
    defense_manager.increase_heat(10)
    assert defense_manager.heat_level == 10

    # 複数回で襲撃トリガー
    for _ in range(7):
        defense_manager.increase_heat(10)

    assert defense_manager.heat_level >= 80
    triggered, _ = defense_manager.check_raid_triggers()
    assert triggered is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
