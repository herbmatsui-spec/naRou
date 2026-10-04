"""
test_skill_casting.py
《喰らい》(devour) で奪ったスキルの「詠唱」経路 — devour→cast-wiring / S3

`tests/test_devour.py` は「奪取が `player.skills` に記録される」ことまでを見ただけで、
`player.skills` は所有権の入れ物であり詠唱は起きないことを明記していた ([S2.2])。
本ファイルはその先を見る: 奪った id を `CharacterState.skills`（World A の呪術帳）に載せ、
MP とクールダウンを払い、宣言された効果を実体へ当てる経路。

production 経路として検証する対象:
  - `engine/engine.py::Engine.execute_devour()` … 奪取 id を `player.skills` に登録する
  - `skill_eater/combat/engine.py::SkillEaterCombatSystem.player_spellbook()`
  - `skill_eater/combat/engine.py::SkillEaterCombatSystem.cast_devoured_skill()`

「登録されたこと」を成功とは数えない。各テストは敵 HP / 状態異常 / 消費 MP / クールダウンの
実変化を観測する。効果を持たない宣言は、でっち上げずに拒否されることを検証する。

前提: 奪取が必ず成功するよう解析レベルと対象の HP をテスト側で固定する。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pytest

from data_manager import DataManager
from game import Engine
from renderer import NullRenderer
from skill_eater_system import CharacterState

# 喰らい成功率を最大に固定するための解析レベル。対象の HP も 1 まで落としてあるので
# rate == 1.0 になり、乱数ロールに依存しない。
ANALYSIS_LEVEL = 5

# `cast_dart` の毒は成功確率 35%。1 回のロールでは不定なので、クールダウンが明けるまで
# 言い続け、少なくとも 1 回は発火することを観測する。
STATUS_ROLL_ROUNDS = 120


@pytest.fixture(scope="module")
def dm() -> DataManager:
    """モジュール共有の DataManager（yaml 読み込みは重いため 1 度だけ）"""
    return DataManager()


def _engine_with_adjacent_monster(dm: DataManager, monster_id: str) -> tuple[Engine, object]:
    """プレイヤー隣接に production 経路のモンスターを1体だけ配置した Engine を返す。"""
    engine = Engine(renderer=NullRenderer())
    engine.player.analysis_level = ANALYSIS_LEVEL
    monster = dm.create_monster(monster_id, x=engine.player.x + 1, y=engine.player.y)
    monster.hp = 1
    engine.entity_manager.add_entity(monster)
    return engine, monster


def _devour(dm: DataManager, monster_id: str) -> tuple[Engine, object, str]:
    """`Engine.execute_devour()` を1回だけ通し、奪取されたスキル id を返す。"""
    engine, monster = _engine_with_adjacent_monster(dm, monster_id)
    engine.execute_devour()
    recorded = list(engine.game_state_data.world_a_data.get("skills", []))
    assert recorded, f"{monster_id} の奪取が記録されなかった"
    return engine, monster, recorded[-1]


def _monster_state(monster: object, skill_ids: list[str]) -> CharacterState:
    """モンスター実体を World A の戦闘状態へ写す。

    `engine/engine.py` の `_character_state_from_entity` は private 関数であり、同ファイルは
    他作業者の編集対象なのでここでは複製する。喰らいの成否計算に必要な hp / status_effects と、
    奪取対象のスキルだけ，持っていれば足りる。
    """
    attributes = monster.attributes
    state = CharacterState(
        id=str(getattr(monster, "id", "enemy")),
        name=monster.name,
        hp=monster.hp,
        max_hp=monster.max_hp,
        mp=monster.mp,
        max_mp=monster.max_mp,
        atk=attributes.strength,
        defense=attributes.endurance,
        intelligence=attributes.perception,
        speed=monster.speed,
        status_effects=list(getattr(monster, "status_effects", None) or []),
    )
    for skill_id in skill_ids:
        state.add_skill(skill_id, ignore_capacity=True)
    return state


def _devour_into_spellbook(engine: Engine, monster: object, skill_id: str) -> CharacterState:
    """プレイヤー側の永続呪術帳に `SkillEaterCombatSystem.execute_devour()` を通す。

    `Engine.execute_devour()` は宣言順の先頭 1 つしか奪わないため、宣言された技のどれを
    狙った效力として「食った」状態にするかはテスト側の選択になる
    （production の `execute_devour()` は `target_skill_id` を受け取る）。
    """
    combat_sys = engine.skill_eater_combat_system
    spellbook = combat_sys.player_spellbook(engine.player)
    prey = _monster_state(monster, [skill_id])
    result = combat_sys.execute_devour(
        spellbook, prey, target_skill_id=skill_id, force_success=True
    )
    assert result.success, f"呪術帳への喰らい失敗: {result.log_messages}"
    assert result.stolen_skill_id == skill_id
    return spellbook


# --- S3.1: 奪った技は唱えられ、宣言どおりのダメージが実体に当たる ---------------------------------


def test_devoured_throw_stone_damages_the_monster(dm: DataManager) -> None:
    """契約 S3.1: ゴブリンの《石投げ》は敵 HP を formula どおりに減らす"""
    engine, monster, stolen_id = _devour(dm, "goblin")
    assert stolen_id == "throw_stone", f"前提: ゴブリンの宣言スキルが石投げである: {stolen_id!r}"

    combat_sys = engine.skill_eater_combat_system
    # 喰らいは敵を瀕死にしていくので、観測しやすいように体力を戻してから唱える
    monster.hp = 400
    hp_before = monster.hp
    mp_before = engine.player.mp

    result = combat_sys.cast_devoured_skill(engine.player, stolen_id, monster)

    assert result.success, f"唱えられない: {result.log_messages}"
    spellbook = combat_sys.player_spellbook(engine.player)
    # `throw_stone` の効果は Damage / formula: "dex * 1.2"（CharacterState では dex = speed）
    assert result.damage_dealt == int(spellbook.speed * 1.2)
    assert monster.hp == hp_before - result.damage_dealt, (
        f"敵の HP に宣言どおりのダメージが入っていない: {hp_before} -> {monster.hp}, "
        f"damage={result.damage_dealt}"
    )
    assert result.damage_dealt > 0
    # 宣言どおりの魔力消費（throw_stone の mp_cost は 3）
    assert engine.player.mp == mp_before - 3


def test_devoured_fire_breath_deals_elemental_damage(dm: DataManager) -> None:
    """契約 S3.1: 《炎の息吹》(hound_fire) の火属性ダメージが敵に到達する"""
    engine, monster, stolen_id = _devour(dm, "hound_fire")
    assert stolen_id == "fire_breath"

    combat_sys = engine.skill_eater_combat_system
    monster.hp = 400
    hp_before = monster.hp

    result = combat_sys.cast_devoured_skill(engine.player, stolen_id, monster)

    spellbook = combat_sys.player_spellbook(engine.player)
    assert result.success, f"唱えられない: {result.log_messages}"
    # `fire_breath` の効果は Damage / element: Fire / formula: "int * 1.8"
    assert result.damage_dealt == int(spellbook.intelligence * 1.8)
    assert monster.hp == hp_before - result.damage_dealt


# --- S3.2: 呪術帳はランをまたいで残り、MP とクールダウンで行動の回数が決まる ---------------------


def test_cooldown_is_spent_then_recovers_across_turns(dm: DataManager) -> None:
    """契約 S3.2: クールダウン中は再唱できず、ターン終了処理で 1 減る"""
    engine, monster, stolen_id = _devour(dm, "goblin")
    combat_sys = engine.skill_eater_combat_system
    monster.hp = 1000

    first = combat_sys.cast_devoured_skill(engine.player, stolen_id, monster)
    assert first.success

    second = combat_sys.cast_devoured_skill(engine.player, stolen_id, monster)
    assert not second.success, "クールダウン中の再唱は受理されてはいけない"
    assert second.damage_dealt == 0, "唱えられていないのにダメージが発生している"

    spellbook = combat_sys.player_spellbook(engine.player)
    # `throw_stone` の cooldown は 1。永続呪術帳なので唱った側がそのまま保持する
    assert spellbook.skills[stolen_id].current_cooldown == 1
    assert spellbook is combat_sys.player_spellbook(engine.player), (
        "呪術帳が呼び出しごとに作り直されている（ターン跨ぎで失われる）"
    )

    # 既存のターン終了処理（process_turn_end）がクールダウンを進める
    combat_sys.process_turn_end(spellbook)
    assert spellbook.skills[stolen_id].current_cooldown == 0

    third = combat_sys.cast_devoured_skill(engine.player, stolen_id, monster)
    assert third.success, f"クールダウン明けに唱えられない: {third.log_messages}"
    assert third.damage_dealt > 0


def test_casting_without_enough_mana_is_refused(dm: DataManager) -> None:
    """契約 S3.2: 魔力が足りないと唱えず、魔力も減らない"""
    engine, monster, stolen_id = _devour(dm, "hound_fire")  # fire_breath: mp_cost 12
    combat_sys = engine.skill_eater_combat_system
    monster.hp = 400
    engine.player.mp = 3

    result = combat_sys.cast_devoured_skill(engine.player, stolen_id, monster)

    assert not result.success
    assert result.damage_dealt == 0
    assert engine.player.mp == 3, "唱え損ねても魔力を消費してはいけない"
    assert monster.hp == 400


# --- S3.3: 回復・状態異常・能力値操作も「効果」として具体的に出る ---------------------------------


def test_devoured_heal_skill_restores_player_hp(dm: DataManager) -> None:
    """契約 S3.3: 《己の癒し》(novice_wizard) は唱えたプレイヤーの HP を実際に戻す"""
    engine, monster, _ = _devour(dm, "novice_wizard")
    combat_sys = engine.skill_eater_combat_system
    spellbook = _devour_into_spellbook(engine, monster, "heal_self")

    engine.player.hp = 10
    hp_before = engine.player.hp
    result = combat_sys.cast_devoured_skill(engine.player, "heal_self")

    assert result.success, f"唱えられない: {result.log_messages}"
    # `heal_self` の効果は Heal / target: Self / formula: "int * 1.4 + 15"
    assert result.heal_amount == int(spellbook.intelligence * 1.4 + 15)
    assert engine.player.hp == hp_before + result.heal_amount


def test_devoured_damage_skill_applies_declared_status(dm: DataManager) -> None:
    """契約 S3.3: 《呪毒弾》(novice_wizard) の毒状態が敵の実体に付く"""
    engine, monster, stolen_id = _devour(dm, "novice_wizard")
    assert stolen_id == "cast_dart", f"前提: 初出は呪毒弾である: {stolen_id!r}"

    combat_sys = engine.skill_eater_combat_system
    spellbook = combat_sys.player_spellbook(engine.player)
    monster.hp = 20000
    mp_before = engine.player.mp

    # 成功確率は 35% なので、クールダウンが明けるまで言い続けて発火を待つ
    fired = False
    for _ in range(STATUS_ROLL_ROUNDS):
        engine.player.mp = mp_before
        result = combat_sys.cast_devoured_skill(engine.player, stolen_id, monster)
        if result.status_applied:
            assert result.status_applied == ["Poison"]
            fired = True
            break
        combat_sys.process_turn_end(spellbook)

    assert fired, f"{STATUS_ROLL_ROUNDS} 回唱えても毒が付かなかった"
    assert "Poison" in list(getattr(monster, "status_effects", [])), (
        f"毒が敵の実体に付いていない: {getattr(monster, 'status_effects', None)}"
    )


def test_stat_mod_skill_moves_mana_between_combatants(dm: DataManager) -> None:
    """契約 S3.3: 《魔力吸引》(lich) は敵の魔力を自分の壺へ移す"""
    engine, monster, _ = _devour(dm, "lich")
    combat_sys = engine.skill_eater_combat_system
    _devour_into_spellbook(engine, monster, "drain_mp")

    engine.player.max_mp = 200
    engine.player.mp = 100
    monster.mp = 100
    target_mp_before = monster.mp
    player_mp_before = engine.player.mp

    result = combat_sys.cast_devoured_skill(engine.player, "drain_mp", monster)

    assert result.success, f"唱えられない: {result.log_messages}"
    # `drain_mp` の効果は StatMod / target: Enemy / stat: mp / formula: "-40" と
    # StatMod / target: Self / stat: mp / formula: "+25"
    assert monster.mp == target_mp_before - 40
    assert engine.player.mp == player_mp_before + 25


# --- S3.4: 実行できない宣言は、でっち上げずに拒否する ----------------------------------------------


def test_skill_with_only_unexecutable_effects_is_refused(dm: DataManager) -> None:
    """契約 S3.4: 《亡者の召喚》は PassiveEffect / AggroMod のみなので唱えられない"""
    engine, monster, _ = _devour(dm, "lich")
    combat_sys = engine.skill_eater_combat_system
    spellbook = _devour_into_spellbook(engine, monster, "summon_undead")
    assert spellbook.has_skill("summon_undead")

    engine.player.max_mp = 200
    engine.player.mp = 200
    mp_before = engine.player.mp

    result = combat_sys.cast_devoured_skill(engine.player, "summon_undead", monster)

    assert not result.success, "実行経路が無いのに成功扱いにしてはいけない"
    assert result.damage_dealt == 0
    assert result.heal_amount == 0
    assert result.status_applied == []
    assert engine.player.mp == mp_before, "唱え損ねても魔力を消費してはいけない"
    # 何が足りないのかをプレイヤーに伝える
    combined = " ".join(result.log_messages)
    assert "PassiveEffect" in combined and "AggroMod" in combined, combined


def test_partially_executable_skill_reports_the_skipped_effect(dm: DataManager) -> None:
    """契約 S3.4: 《力強打》(orc) はダメージだけ当たり、DamageMod(自刃の火炎カット等)は当たらない"""
    engine, monster, stolen_id = _devour(dm, "orc")
    assert stolen_id == "power_bash"

    combat_sys = engine.skill_eater_combat_system
    monster.hp = 400
    hp_before = monster.hp
    spellbook = combat_sys.player_spellbook(engine.player)

    result = combat_sys.cast_devoured_skill(engine.player, stolen_id, monster)

    assert result.success, f"唱えられない: {result.log_messages}"
    # `power_bash` の効果は Damage / formula: "str * 1.6" と DamageMod / target: Self
    assert result.damage_dealt == int(spellbook.atk * 1.6)
    assert monster.hp == hp_before - result.damage_dealt
    combined = " ".join(result.log_messages)
    assert "DamageMod" in combined, f"未実行の効果がプレイヤーに伝わっていない: {combined}"
