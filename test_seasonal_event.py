"""
テスト: シーズンイベントのトリガーとスケジューラー
"""
from world_event_system import WorldEventManager, REGISTRY
from event_scheduler import EventScheduler

class MockEntity:
    def __init__(self, entity_id="test_player"):
        self.id = entity_id
        self.active_world_events = []

class MockEngine:
    def __init__(self):
        self.logs = []
    def log(self, message, color):
        self.logs.append((message, color))

def test_seasonal_event_scheduling():
    # ワールドイベントをロード（すでにロードされているはずだが、再ロード）
    REGISTRY.load()
    
    # マネージャのインスタンス
    wm = WorldEventManager()
    player = MockEntity()
    engine = MockEngine()
    
    # テスト用のターンを設定（例えば、インターワールド侵攻の開始ターンに合わせる）
    # まず、インターワールド侵攻のイベントデータを取得
    event = REGISTRY.get("interworld_invasion")
    print(f"イベントデータ: {event}")
    if event:
        print(f"イベントのquarter: {event.quarter}")
        print(f"イベントのstart_turn: {event.start_turn}")
        print(f"イベントのend_turn: {event.end_turn}")
    
    # 現在のターンを設定（イベントのstart_turnに合わせる）
    # イベントにstart_turnが設定されていない場合は、デフォルトで1000とする
    test_turn = event.start_turn if event.start_turn is not None else 1000
    print(f"テストターン: {test_turn}")
    
    # スケジューラーを使って現在のイベントを取得
    scheduler = EventScheduler(REGISTRY)
    current_event = scheduler.get_current_seasonal_event(test_turn)
    print(f"スケジューラーが返す現在のイベント: {current_event}")
    
    # イベントトリガーをチェック
    triggered_event = wm.check_event_triggers(player, engine, current_turn=test_turn)
    print(f"トリガーされたイベント: {triggered_event}")
    
    if triggered_event and triggered_event.id == "interworld_invasion":
        print("SUCCESS: シーズンイベントが正しくトリガーされました")
        # イベントを実際にトリガー
        result = wm.trigger_event(player, triggered_event.id, engine)
        print(f"トリガー結果: {result}")
        print(f"プレイヤーのアクティブイベント: {player.active_world_events}")
        print(f"エンジンログ: {engine.logs}")
    else:
        print("FAILED: シーズンイベントがトリガーされませんでした")

if __name__ == "__main__":
    test_seasonal_event_scheduling()