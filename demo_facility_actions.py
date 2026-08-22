#!/usr/bin/env python3
"""
demo_facility_actions.py
Aの世界（スキル喰い） 施設アクションシステム デモスクリプト
"""
from __future__ import annotations

from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_economy_system import SkillEaterEconomySystem
from skill_eater_facility_actions import (
    FacilityActionRegistry,
    SkillEaterFacilitySystem,
    calculate_success_rate,
)
from skill_eater_presentation_system import SkillEaterPresentationSystem
from skill_eater_system import CharacterState, SkillEaterRegistry


def print_header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_action_result(result, prefix: str = ""):
    status = "[SUCCESS]" if result.success else "[FAIL]"
    critical = " [CRITICAL!]" if result.is_critical else ""
    print(f"{prefix}{status}{critical}")
    print(f"{prefix}  Message: {result.log_message}")
    if result.rewards:
        print(f"{prefix}  Rewards: {result.rewards}")
    if result.played_sounds:
        print(f"{prefix}  Sounds: {result.played_sounds}")
    print()


def demo_basic_setup():
    print_header("1. 基本セットアップ")

    # レジストリ初期化
    registry = SkillEaterRegistry.get_instance()

    # オーディオ・プレゼンテーション（モックモード）
    audio = SkillEaterAudioSystem(enable_real_audio=False)
    presentation = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)

    # 経済システム（施設システム内蔵）
    economy = SkillEaterEconomySystem(
        registry=registry,
        audio=audio,
        presentation=presentation,
    )

    # 施設システムファサード
    facility_system = SkillEaterFacilitySystem(
        registry=registry,
        economy=economy,
        audio=audio,
        presentation=presentation,
    )

    # アクションレジストリ
    action_registry = FacilityActionRegistry.get_instance()

    print(f"登録済みアクション総数: {len(action_registry.get_all_actions())}")
    for facility_id in ["workshop", "lab", "medbay", "command", "bar"]:
        actions = action_registry.get_actions_by_facility(facility_id)
        print(f"  {facility_id}: {[a.name for a in actions]}")

    return economy, facility_system, audio, presentation


def demo_player_creation():
    print_header("2. プレイヤー作成")

    player = CharacterState(
        id="demo_player",
        name="デモ主人公",
        hp=100,
        max_hp=100,
        mp=50,
        max_mp=50,
        atk=15,
        defense=12,
        intelligence=18,
        speed=14,
        analysis_level=3,
        max_memory_capacity=12,
        junk=500,
    )

    # 必要スキルをいくつか習得
    player.add_skill("rar_utility_005")  # サイバネティクス知識
    player.add_skill("com_magic_001")    # 解析魔法
    player.add_skill("rar_combat_012")   # 戦術指揮
    player.add_skill("uni_midas_001")    # 高度解析
    player.add_skill("con_fire_001")     # 禁忌の知識

    print(f"名前: {player.name}")
    print(f"HP: {player.hp}/{player.max_hp}")
    print(f"MP: {player.mp}/{player.max_mp}")
    print(f"ATK: {player.atk} DEF: {player.defense} INT: {player.intelligence} SPD: {player.speed}")
    print(f"解析Lv: {player.analysis_level}")
    print(f"メモリ容量: {player.current_memory_usage}/{player.max_memory_capacity}")
    print(f"ジャンク: {player.junk}")
    print(f"所持スキル: {list(player.skills.keys())}")

    return player


def demo_success_rate_calculation(economy, player):
    print_header("3. 成功率計算デモ")

    from skill_eater_facility_actions import FacilityAction

    test_action = FacilityAction(
        id="test", name="テスト", facility_id="workshop",
        base_success_rate=0.40, required_skill="rar_utility_005"
    )

    for level in range(1, 6):
        facility = economy.base_facilities["workshop"]
        facility.level = level
        rate = calculate_success_rate(facility, player, test_action)
        print(f"  施設Lv.{level}: 成功率 {rate*100:.0f}%")


def demo_workshop_actions(economy, facility_system, player, audio, presentation):
    print_header("4. ワークショップ アクション")

    # インプラント製作
    print("--- インプラント製作 ---")
    result = facility_system.execute_action("workshop", "craft_implant", player)
    print_action_result(result)

    # 装備修理
    print("--- 装備修理 ---")
    result = facility_system.execute_action("workshop", "repair_gear", player)
    print_action_result(result)

    # 義体インストール
    print("--- 義体インストール ---")
    result = facility_system.execute_action("workshop", "install_cybernetic", player)
    print_action_result(result)

    print(f"更新後のメモリ容量: {player.current_memory_usage}/{player.max_memory_capacity}")
    print(f"残りジャンク: {player.junk}")
    print(f"残りアルド: {economy.aldo_currency}")


def demo_lab_actions(economy, facility_system, player, audio, presentation):
    print_header("5. 研究室 アクション")

    # 未鑑定結晶を追加
    player.unidentified_crystals = ["proc_unknown_001", "proc_unknown_002"]

    # スキル結晶解析
    print("--- スキル結晶解析 ---")
    result = facility_system.execute_action("lab", "analyze_skill_crystal", player)
    print_action_result(result)

    # リバースエンジニアリング
    print("--- リバースエンジニアリング ---")
    result = facility_system.execute_action("lab", "reverse_engineer_tech", player)
    print_action_result(result)

    # 対策開発
    print("--- 対策開発 ---")
    result = facility_system.execute_action("lab", "develop_countermeasure", player, boss_id="midas_ceo")
    print_action_result(result)

    print(f"残りジャンク: {player.junk}")
    print(f"残りアルド: {economy.aldo_currency}")
    print(f"未鑑定結晶: {player.unidentified_crystals}")


def demo_medbay_actions(economy, facility_system, player, audio, presentation):
    print_header("6. 医療ベイ アクション")

    # 毒性を蓄積
    player.addiction_buildup = 75
    player.status_effects.append("Addicted")

    # 毒性治療
    print("--- 毒性治療 ---")
    result = facility_system.execute_action("medbay", "treat_toxicity", player)
    print_action_result(result)
    print(f"侵食度: {player.addiction_buildup}")
    print(f"ステータス: {player.status_effects}")

    # 従属者強化（従属者がいないのでスキップ）
    print("--- 従属者強化手術（スキップ：従属者なし） ---")

    # 記憶消去（高コストなのでスキップ）
    print("--- 記憶消去・リセット（スキップ：高コスト） ---")


def demo_command_actions(economy, facility_system, player, audio, presentation):
    print_header("7. 指揮室 アクション")

    # 部隊派遣
    print("--- 部隊派遣（スカベンジ） ---")
    result = facility_system.execute_action("command", "dispatch_squad", player, mission_type="scavenge")
    print_action_result(result)

    # 襲撃計画
    print("--- 襲撃計画立案 ---")
    result = facility_system.execute_action("command", "plan_raid", player, target_id="midas_branch")
    print_action_result(result)

    # 休戦交渉
    print("--- 休戦交渉 ---")
    economy.factions["midas"].is_hostile = True
    economy.factions["midas"].reputation = -50
    economy.heat_level = 30
    result = facility_system.execute_action("command", "negotiate_truce", player, faction_id="midas")
    print_action_result(result)
    print(f"ミダス敵対: {economy.factions['midas'].is_hostile}")
    print(f"ミダス好感度: {economy.factions['midas'].reputation}")
    print(f"警戒度: {economy.heat_level}")

    print(f"残りジャンク: {player.junk}")
    print(f"残りアルド: {economy.aldo_currency}")


def demo_bar_actions(economy, facility_system, player, audio, presentation):
    print_header("8. バー/交易所 アクション")

    # 情報収集
    print("--- 情報収集 ---")
    result = facility_system.execute_action("bar", "gather_intel", player)
    print_action_result(result)

    # 傭兵雇用
    print("--- 傭兵雇用 ---")
    result = facility_system.execute_action("bar", "hire_mercenary", player)
    print_action_result(result)
    if hasattr(player, "active_mercenaries") and player.active_mercenaries:
        merc = player.active_mercenaries[-1]
        print(f"  雇用傭兵: {merc.name} ({merc.merc_type}) 残り{merc.duration_turns}ターン")

    # アルド洗浄
    print("--- アルド洗浄 ---")
    economy.heat_level = 50
    economy.aldo_currency = 10000
    result = facility_system.execute_action("bar", "launder_aldo", player, amount=3000)
    print_action_result(result)
    print(f"警戒度: {economy.heat_level}")
    print(f"アルド: {economy.aldo_currency}")

    print(f"残りジャンク: {player.junk}")


def demo_cooldown_and_resource_management(economy, facility_system, player, audio, presentation):
    print_header("9. クールダウン・リソース管理デモ")

    print("--- 連続実行テスト（クールダウン確認） ---")
    for i in range(3):
        result = facility_system.execute_action("workshop", "repair_gear", player)
        print(f"  実行{i+1}: {'成功' if result.success else '失敗'} - {result.log_message[:50]}...")

    print(f"\n  クールダウン状態: {player.facility_action_cooldowns}")

    # ターン経過シミュレーション
    print("\n--- ターン経過（クールダウン減少） ---")
    for turn in range(2):
        facility_system.decrease_cooldowns(player)
        print(f"  ターン{turn+1}後: {player.facility_action_cooldowns}")

    # もう一度実行
    result = facility_system.execute_action("workshop", "repair_gear", player)
    print(f"  クールダウン解除後実行: {'成功' if result.success else '失敗'}")


def demo_facility_upgrade(economy, player, audio, presentation):
    print_header("10. 施設アップグレード")

    for facility_id in ["workshop", "lab", "medbay", "command", "bar"]:
        facility = economy.base_facilities[facility_id]
        print(f"\n{facility.name} Lv.{facility.level}")
        print(f"  現在のアクション: {facility.actions}")
        print(f"  アップグレードコスト: {facility.upgrade_cost_aldo} アルド")

    # ワークショップをアップグレード
    print("\n--- ワークショップをLv.2にアップグレード ---")
    player.junk = 100
    economy.aldo_currency = 5000
    success, msg = economy.upgrade_facility(player, "workshop")
    print(f"  結果: {'成功' if success else '失敗'} - {msg}")

    facility = economy.base_facilities["workshop"]
    print(f"  新レベル: Lv.{facility.level}")
    print(f"  次回コスト: {facility.upgrade_cost_aldo} アルド")


def demo_presentation_audio():
    print_header("11. 演出・音声システム確認")

    audio = SkillEaterAudioSystem(enable_real_audio=False)
    presentation = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)

    # 施設アクション実行後のイベントキュー確認
    events = presentation.get_and_clear_events()
    print(f"演出イベントキュー: {len(events)}件")
    for evt in events[:3]:
        print(f"  - Emote: {evt.emote_file}, Audio: {evt.audio_file}, Msg: {evt.message[:40]}...")

    sounds = audio.get_and_clear_played_sounds()
    print(f"再生音声キュー: {len(sounds)}件")
    for snd in sounds[:5]:
        print(f"  - {snd}")


def main():
    print("Aの世界：スキル喰い - 施設アクションシステム デモ")
    print("=" * 60)

    # セットアップ
    economy, facility_system, audio, presentation = demo_basic_setup()
    player = demo_player_creation()

    # 成功率計算
    demo_success_rate_calculation(economy, player)

    # 各施設のアクションデモ
    demo_workshop_actions(economy, facility_system, player, audio, presentation)
    demo_lab_actions(economy, facility_system, player, audio, presentation)
    demo_medbay_actions(economy, facility_system, player, audio, presentation)
    demo_command_actions(economy, facility_system, player, audio, presentation)
    demo_bar_actions(economy, facility_system, player, audio, presentation)

    # クールダウン・リソース管理
    demo_cooldown_and_resource_management(economy, facility_system, player, audio, presentation)

    # 施設アップグレード
    demo_facility_upgrade(economy, player, audio, presentation)

    # 演出・音声確認
    demo_presentation_audio()

    print_header("デモ完了")
    print("全施設アクションの基本動作を確認しました。")


if __name__ == "__main__":
    main()
