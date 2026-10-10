"""入力層 (input_actions / input_handler) の回帰テスト。

このテストが固定する、ゲームとして壊れていた2点:

1. 消耗品を使う経路が存在しなかった
   - 開始持ち物品に「軽傷治療のポーション x8」があるのに、入力層に
     使用/飲む/食べる/読むの動詞が1つも無かった。
   - ここでは実物の Engine と実際のキーイベントで操作し、
     スタックが減り、効果が適用され、0個で消えることを確認する。
2. キーバインドが別のバインドに隠れていた
   - 移動 (hjkl) が先に登録されていたため [h]=ヘルプ と [j]=ジャーナルが死んでいた。
   - Shift+S は 2つのアクションに二重登録され、実質どちらにも届かなかった。

ルーティング (どの Verb に届くか) だけを確認したいテストは _resolve_action() を使う。
これは実行を伴わないので、セーブファイルを書く [s] やプロセスを終了する [Esc] も
副作用を出さずに検証できる。
"""

from __future__ import annotations

import pytest
import tcod.event

from constants import CAT_FOOD, CAT_POTION, CAT_SCROLL
from game import Engine
from input_actions import (
    ActionDevour,
    ActionRegistry,
    ActionScan,
    HelpAction,
    InventoryAction,
    JobAction,
    JournalAction,
    LookModeAction,
    MovementAction,
    QuitAction,
    SaveAction,
    SkillTreeAction,
    UseConsumableAction,
)
from input_handler import InputHandler
from item_system import create_sample_item

KS = tcod.event.KeySym
MOD = tcod.event.Modifier


def _key(sym, mod=0):
    """実際の tcod キーイベントを作る"""
    return tcod.event.KeyDown(sym=sym, scancode=0, mod=mod)


def _resolve_action(sym, mod=0):
    """押されたキーが最初にヒットする Action を返す (実行しない)"""
    event = _key(sym, mod)
    for binding in InputHandler._action_registry.get_bindings("play"):
        if InputHandler._is_key_match(event, binding):
            return binding.action
    return None


def _messages(engine) -> list[str]:
    """画面に出たログ文言だけを抜き出す"""
    return [message.text for message in engine.msg_log.messages]


def _potion(engine):
    """所持中のポーションのスタック (Item)"""
    return next(item for item in engine.inventory.items if item.category == CAT_POTION)


def _potion_count(engine) -> int:
    return sum(item.count for item in engine.inventory.items if item.category == CAT_POTION)


def _drop_consumables(engine, keep: tuple[str, ...] = ()) -> None:
    """所持品から消耗品を取り除く (keep に挙げたカテゴリは残す)"""
    engine.inventory.items = [
        item
        for item in engine.inventory.items
        if item.category not in (CAT_POTION, CAT_FOOD, CAT_SCROLL)
        or item.category in keep
    ]


@pytest.fixture
def registry():
    """既定バインドを登録し直す (クラス変数はテスト間で共有される)"""
    InputHandler._action_registry = ActionRegistry()
    InputHandler._actions_registered = False
    InputHandler.register_default_actions()
    return InputHandler._action_registry


@pytest.fixture
def engine(registry):
    """実物の Engine (ダンジョン生成まで実施)"""
    eng = Engine()
    # 戦闘の余波で回復量が読めなくなるため、周囲の敵は退場させる
    for entity in list(eng.entity_manager.get_living_entities()):
        if entity is not eng.player and not getattr(entity, "is_pet", False):
            eng.entity_manager.remove_entity(entity)
    return eng


# ============================================================
# Defect 1: 消耗品を使う経路
# ============================================================


def test_use_key_drinks_potion_from_inventory(engine):
    """[e] で回復ポーションを1個飲み、スタックが減り HP が回復する"""
    potion = _potion(engine)
    count_before = potion.count
    engine.player.hp = 10
    hp_before = engine.player.hp

    InputHandler.handle_event(_key(KS.E), engine)

    assert _potion_count(engine) == count_before - 1
    assert engine.player.hp == hp_before + potion.heal_amount


def test_use_key_consumes_exactly_one_per_press(engine):
    """1回押すごとに1個だけ減る (スタック全体が消えることはない)"""
    count_before = _potion_count(engine)
    engine.player.hp = 10

    InputHandler.handle_event(_key(KS.E), engine)

    assert count_before - _potion_count(engine) == 1


def test_potion_disappears_when_stack_reaches_zero(engine):
    """最後の1個を使うとポーションはインベントリから消える"""
    _potion(engine).count = 1

    InputHandler.handle_event(_key(KS.E), engine)

    assert _potion_count(engine) == 0
    assert all(item.category != CAT_POTION for item in engine.inventory.items)


def test_use_key_reports_feedback(engine):
    """玩家に「何を飲んだか」がログで通知される"""
    potion = _potion(engine)
    engine.player.hp = 10

    InputHandler.handle_event(_key(KS.E), engine)

    assert any(potion.name in text for text in _messages(engine))


def test_potion_is_saved_when_player_is_at_full_hp(engine):
    """満HPで無闇にポーションを消費しない"""
    count_before = _potion_count(engine)
    engine.player.hp = engine.player.max_hp

    InputHandler.handle_event(_key(KS.E), engine)

    assert _potion_count(engine) == count_before


def test_inventory_use_key_consumes_potion_with_same_effect(engine):
    """[i] → 消耗品タブ → [e] の従来経路も同じ効果・同じ消費になる"""
    potion = _potion(engine)
    count_before = potion.count
    engine.player.hp = 10
    hp_before = engine.player.hp

    InputHandler.handle_event(_key(KS.I), engine)
    assert engine.game_state == "inventory"
    engine.inventory_tab = 3  # 消耗品タブ (ポーション/食料)
    engine.inventory_cursor = 0

    InputHandler.handle_event(_key(KS.E), engine)

    assert _potion_count(engine) == count_before - 1
    assert engine.player.hp == hp_before + potion.heal_amount
    assert engine.game_state == "play"


def test_use_key_eats_food_when_no_potion_is_usable(engine):
    """飲めるポーションが無いときは食料を食べる"""
    _drop_consumables(engine)
    engine.inventory.add_item(create_sample_item("bread"))
    food = next(item for item in engine.inventory.items if item.category == CAT_FOOD)
    count_before = food.count
    hunger_before = engine.survival.hunger

    InputHandler.handle_event(_key(KS.E), engine)

    assert food.count == count_before - 1
    # 食事は1ターン消費するため、空腹が1だけ減るぶんは許容する
    assert engine.survival.hunger >= hunger_before + food.nutrition - 5


def test_use_key_reads_scroll_and_reveals_unidentified_items(engine):
    """巻物を読むと鑑定効果が働き、巻物自身は消費される"""
    scroll = create_sample_item("scroll_identify")
    _drop_consumables(engine)
    engine.inventory.items.append(scroll)
    hidden = create_sample_item("longsword")
    hidden.identified = False
    engine.inventory.add_item(hidden)
    engine.player.hp = engine.player.max_hp  # 満HP: ポーション消費を先に選ばせない

    InputHandler.handle_event(_key(KS.E), engine)

    assert scroll not in engine.inventory.items
    assert hidden.identified is True
    assert any(scroll.name in text for text in _messages(engine))


@pytest.mark.parametrize(
    ("item_name", "category"),
    [
        ("potion_heal", CAT_POTION),
        ("bread", CAT_FOOD),
        ("scroll_identify", CAT_SCROLL),
    ],
)
def test_every_consumable_category_is_usable_from_inventory(engine, item_name, category):
    """ポーション/食料/巻物のいずれもインベントリから1個だけ消費できる"""
    _drop_consumables(engine)
    item = create_sample_item(item_name)
    engine.inventory.items.append(item)
    count_before = item.count
    engine.player.hp = max(1, engine.player.max_hp - 20)

    InputHandler.handle_event(_key(KS.I), engine)
    engine.inventory_tab = 0  # 全般タブ
    engine.inventory_cursor = len(engine.inventory.items) - 1
    InputHandler.handle_event(_key(KS.E), engine)

    assert item not in engine.inventory.items or item.count == count_before - 1
    assert all(it.category != category or it is not item for it in engine.inventory.items)


def test_use_key_without_consumable_reports_reason_and_keeps_turn(engine):
    """対象が無くても理由は通知し、ターンも消費しない"""
    _drop_consumables(engine)
    turns_before = engine.turns
    logs_before = len(_messages(engine))

    InputHandler.handle_event(_key(KS.E), engine)

    assert engine.turns == turns_before
    assert len(_messages(engine)) > logs_before


# ============================================================
# Defect 2: 死んでいたキーバインド
# ============================================================


def test_h_reaches_help(engine):
    """[h] が移動に奪われずにヘルプへ届く"""
    engine.game_state = "play"

    InputHandler.handle_event(_key(KS.H), engine)

    assert engine.game_state == "help"


def test_l_reaches_look(engine):
    """[l] が調査モードへ届く"""
    engine.game_state = "play"

    InputHandler.handle_event(_key(KS.L), engine)

    assert engine.game_state == "look"


def test_j_reaches_journal(engine):
    """[j] が移動に奪われずにジャーナルへ届く"""
    engine.game_state = "play"

    InputHandler.handle_event(_key(KS.J), engine)

    assert engine.game_state == "journal"


def test_shift_j_reaches_job(engine):
    """[Shift+j] はジョブ画面 (素の [j] とは別 Verb)"""
    engine.game_state = "play"

    InputHandler.handle_event(_key(KS.J, MOD.SHIFT), engine)

    assert engine.game_state == "jobs"


def test_shift_s_opens_skill_tree_and_differs_from_s(registry):
    """[Shift+s] はスキルツリー。素の [s] (セーブ) とは区別できる"""
    assert _resolve_action(KS.S) is SaveAction
    assert _resolve_action(KS.S, MOD.SHIFT) is SkillTreeAction


def test_escape_resolves_to_quit_action(registry):
    """未登録だった QuitAction が [Esc] に結び付いている"""
    assert _resolve_action(KS.ESCAPE) is QuitAction


def test_existing_movement_bindings_are_preserved(registry):
    """既存の移動バインド (矢印 / [k]) は保存されている"""
    expected = {
        KS.UP: (0, -1),
        KS.K: (0, -1),
        KS.DOWN: (0, 1),
        KS.LEFT: (-1, 0),
        KS.RIGHT: (1, 0),
    }
    for sym, (dx, dy) in expected.items():
        action = _resolve_action(sym)
        assert isinstance(action, MovementAction), f"{sym!r} が移動へ届いていない"
        assert (action.dx, action.dy) == (dx, dy)


def test_no_duplicate_key_modifier_registrations(registry):
    """同じ (キー, 修飾子) に別アクションが二重登録されていない"""
    seen: dict[tuple[int, int], set[str]] = {}
    for binding in registry.get_bindings("play"):
        key = (binding.key, binding.modifiers)
        seen.setdefault(key, set()).add(type(binding.action).__name__)
    duplicated = {key: names for key, names in seen.items() if len(names) > 1}
    assert not duplicated, f"二重登録されたキーがある: {duplicated}"


def test_lock_key_modifiers_do_not_block_letter_bindings(registry):
    """NumLock / CapsLock が ON でも無修飾のアルファベットキーは死なない"""
    lock_mod = MOD.NUM | MOD.CAPS

    assert _resolve_action(KS.S, lock_mod) is SaveAction
    assert isinstance(_resolve_action(KS.E, lock_mod), UseConsumableAction)
    assert _resolve_action(KS.S, MOD.SHIFT | lock_mod) is SkillTreeAction


def test_known_verb_bindings_are_uniquely_owned(registry):
    """主要な Verb が意図したキーに乗っている (他の Verb に影を奪われていない)"""
    assert isinstance(_resolve_action(KS.H), HelpAction)
    assert isinstance(_resolve_action(KS.QUESTION), HelpAction)
    assert isinstance(_resolve_action(KS.L), LookModeAction)
    assert isinstance(_resolve_action(KS.I), InventoryAction)
    assert isinstance(_resolve_action(KS.J), JournalAction)
    assert isinstance(_resolve_action(KS.J, MOD.SHIFT), JobAction)
    assert isinstance(_resolve_action(KS.S, MOD.SHIFT), SkillTreeAction)
    assert isinstance(_resolve_action(KS.K, MOD.SHIFT), SkillTreeAction)
    assert isinstance(_resolve_action(KS.X), ActionScan)
    assert isinstance(_resolve_action(KS.V), ActionDevour)
    assert isinstance(_resolve_action(KS.E), UseConsumableAction)
    assert isinstance(_resolve_action(KS.ESCAPE), QuitAction)
