import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from sound_manager import BGMManager, AmbientLayer
from config_manager import DataCache
from world_state_system import WorldStateManager
from game import Engine

def test_dynamic_soundscape():
    bgm = BGMManager()
    msg = bgm.play_bgm('town')
    assert 'bgm_town' in msg
    assert bgm.current_theme == 'town'

    # Crisis trigger
    crisis_msg = bgm.check_crisis_trigger(hp=10, max_hp=100)
    assert crisis_msg is not None
    assert bgm.is_crisis

    # Recover from crisis
    rec_msg = bgm.check_crisis_trigger(hp=90, max_hp=100)
    assert rec_msg is not None
    assert not bgm.is_crisis

    # Ambient sound
    amb = AmbientLayer()
    amb_msg = amb.update_ambient('dungeon')
    assert 'amb_water_drop' in amb_msg
    assert amb.current_ambient == 'amb_water_drop'

def test_data_cache_performance():
    DataCache.clear()
    data1 = DataCache.get_data('data/audio_config.yaml')
    assert data1 is not None
    assert 'bgm' in data1

    # Second fetch should hit cache
    data2 = DataCache.get_data('data/audio_config.yaml')
    assert data1 is data2

def test_world_news_and_echoes():
    eng = Engine()
    wsm = WorldStateManager()
    news = wsm.generate_world_news(eng)
    assert len(news) > 0

    eng.player.faction_reputation['adventurer_guild'] = 60
    echo = wsm.get_action_echo(eng.player, 'adventurer_guild')
    assert '大活躍' in echo
