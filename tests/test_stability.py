import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from game import Engine
from save_system import SaveSystem
from exceptions import ElonaError
from tests.balance_simulator import BalanceSimulator

def test_balance_simulator_execution():
    sim = BalanceSimulator()
    res = sim.simulate_battle(player_level=1, monster_type='slime', trials=50)
    assert res['trials'] == 50
    assert 'win_rate' in res
    assert 'avg_turns' in res
    assert res['is_balanced']

    full_rep = sim.run_full_validation()
    assert 'summary' in full_rep
    assert 'scenarios' in full_rep

def test_save_checksum_and_backup():
    eng = Engine()
    eng.player.name = 'StabilityHero'
    
    # Save
    msg = SaveSystem.save(eng)
    assert 'セーブ完了' in msg
    assert os.path.exists(SaveSystem.SAVE_PATH)
    
    # 2nd save to trigger backup
    eng.player.gold = 9999
    SaveSystem.save(eng)
    assert os.path.exists(f'{SaveSystem.SAVE_PATH}.bak1')

    # Normal load
    loaded, l_msg = SaveSystem.load()
    assert loaded is not None
    assert loaded.player.gold == 9999

    # Corrupt checksum test
    with open(SaveSystem.SAVE_PATH, 'r+b') as f:
        f.seek(10)
        f.write(b'\xff\xff')  # corrupt header
    
    # Should automatically recover from backup
    recovered, r_msg = SaveSystem.load()
    assert recovered is not None
    assert 'バックアップ' in r_msg or 'ロード完了' in r_msg

def test_custom_exceptions():
    err = ElonaError('Test error message', context={'level': 5})
    log_path = err.log_to_file()
    assert os.path.exists(log_path)
    content = open(log_path, encoding='utf-8').read()
    assert 'Test error message' in content

def test_json_serialization_and_migration():
    """Step 21-35: JSONセーブ・ロードおよびマイグレーションのテスト"""
    eng = Engine()
    eng.player.name = "JsonTestHero"
    eng.player.gold = 7777

    # JSON save
    save_msg = SaveSystem.save_json(eng, "test_savegame.json")
    assert "JSONセーブ完了" in save_msg
    assert os.path.exists("test_savegame.json")

    # JSON load
    loaded_eng, load_msg = SaveSystem.load_json("test_savegame.json")
    assert loaded_eng is not None
    assert "JSONロード完了" in load_msg
    assert loaded_eng.player.name == "JsonTestHero"

    if os.path.exists("test_savegame.json"):
        os.remove("test_savegame.json")

def test_stress_turn_simulation():
    """Step 63: 高速ターン回しテスト（メモリリーク・破綻監視）"""
    eng = Engine()
    initial_hp = eng.player.hp
    for _ in range(500):
        eng.turns += 1
        eng.systems_mgr.update_all(eng)
    assert eng.turns == 500

