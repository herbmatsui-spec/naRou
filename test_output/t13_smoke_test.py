"""T13 新機能の統合スモークテスト (実行後は削除してよい一時検証スクリプト)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game import Engine
from web_server import GameHTTPRequestHandler

engine = Engine()
handler = GameHTTPRequestHandler.__new__(GameHTTPRequestHandler)

# --- 1) pending_events 配信: GET相当(既定)は消費、POST相当(False)は保持 ---
engine.pending_events = [
    {"type": "cutscene", "source": "main_quest", "sequence": [{"text": "★完了！", "duration": 2600}]},
    {"type": "level_up", "level": 2},
]
s = handler._serialize_engine_state(engine, consume_pending_events=False)
assert s["pending_events"] == engine.pending_events and len(engine.pending_events) == 2, "POST応答で保持"
s = handler._serialize_engine_state(engine)
assert len(s["pending_events"]) == 2 and engine.pending_events == [], "GET相当で消費"
s2 = handler._serialize_engine_state(engine)
assert s2["pending_events"] == [], "消費後は空"
print("1) pending_events delivery: OK")

# --- 2) レベルアップ検知: CombatManager が光の柱+fanfare+イベントを発火 ---
from managers.combat_manager import CombatManager
from ecs.entity import Entity

enemy = Entity(5, 5, "s", (0, 255, 0), name="スライム")
player = engine.player
prev_level = player.level
player.exp = player.exp_next - 1  # 1キルでレベルアップする直前へ
before = len(engine.fx_manager.particles)
CombatManager().handle_kill_rewards(engine, enemy)
after = engine.fx_manager.particles[before:]
assert player.level == prev_level + 1, "レベル+1"
assert any(p.char == "✦" and p.color == (255, 215, 0) and p.vy < 0 for p in after), "金色上昇パーティクル"
lv = [e for e in engine.pending_events if e.get("type") == "level_up"]
assert lv and lv[0]["level"] == prev_level + 1, "level_upイベント"
print(f"2) level-up detection: OK (Lv{prev_level} -> Lv{player.level}, pillar={len(after)})")

# --- 3) カットシーン発火: _complete_quest ---
from main_quest_system import MainQuestSystem

mqs = MainQuestSystem()
q = mqs.quests["prologue_01"]
engine.pending_events = []
engine.game_state = "play"
engine.turns = 100
mqs._complete_quest(player, q, engine)
ev = engine.pending_events[0]
assert ev["type"] == "cutscene" and "完了" in ev["sequence"][0]["text"]
assert engine.game_state == "cutscene" and engine.cutscene_telop
assert engine.cutscene_revert_turn == 103
print("3) cutscene event: OK (steps=%d)" % len(ev["sequence"]))

# --- 4) tcod版 render_system カットシーン分岐 (描画+復帰) ---
import tcod

console = tcod.Console(80, 45)
engine2 = Engine()
engine2.game_state = "cutscene"
engine2.cutscene_telop = ["★メインクエスト【運命の始まり】 完了！"]
engine2.turns = 50
engine2.cutscene_revert_turn = 52
from engine.systems.render_system import RenderSystemHandler

RenderSystemHandler(engine2).render(console)  # 未復帰: 暗転+テロップ描画
assert engine2.game_state == "cutscene"
engine2.turns = 52
RenderSystemHandler(engine2).render(console)  # 復帰ターン到達
assert engine2.game_state == "play", "復帰ターンでplayへ"
print("4) tcod cutscene render branch: OK")
print("ALL SMOKE TESTS PASSED")
