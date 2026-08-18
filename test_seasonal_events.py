"""
テスト: シーズンイベントの統合テスト
"""
from __future__ import annotations
<<<<<<< ours
import json
from world_event_system import REGISTRY, EVENT_SCHEDULER, RANKING_MANAGER, WorldEventManager
=======
import time
import json
from world_event_system import REGISTRY, EVENT_SCHEDULER, REWARD_MANAGER, RANKING_MANAGER, TITLE_MANAGER, WorldEventManager
>>>>>>> theirs
from community_goal_manager import COMMUNITY_GOAL_MANAGER
from feedback_system import FEEDBACK_SYSTEM
from balance_tool import BALANCE_TOOL
from asset_manager import ASSET_MANAGER
<<<<<<< ours
=======
from entity import Entity  # We need to define a mock entity
from typing import Dict, Any
>>>>>>> theirs

class MockEntity:
    """テスト用のモックエンティティ"""
    def __init__(self, entity_id: str = "test_player"):
        self.id = entity_id
        self.active_world_events = []
        # モックエンティティには実際のコンポーネントがないが、必要な属性を追加
        self.stats = {"points": 0}

class MockEngine:
    """テスト用のモックエンジン"""
    def __init__(self):
        self.logs = []
        self.player = MockEntity()  # エンジンがプレイヤーを持っていると仮定
    
    def log(self, message: str, color: tuple = (255, 255, 255)):
        self.logs.append((message, color))
        print(f"[LOG] {message}")

def test_seasonal_event_flow():
    """シーズンイベントのフローをテストする"""
    print("=== シーズンイベントフローテスト開始 ===")
    
    # ワールドイベントをロード
    REGISTRY.load()
    
    # マネージャのインスタンス
    wm = WorldEventManager()
    player = MockEntity("hero")
    engine = MockEngine()
    
    # テスト用のターンを設定（イベントのstart_turnに合わせる）
    event = REGISTRY.get("interworld_invasion")
    if not event:
        print("ERROR: interworld_invasion イベントが見つかりません")
        return False
    
    test_turn = event.start_turn if event.start_turn is not None else 1000
    print(f"テストターン: {test_turn}")
    
    # 1. スケジューラーが正しいイベントを返すかを確認
    current_event = EVENT_SCHEDULER.get_current_seasonal_event(test_turn)
    if not current_event or current_event.id != "interworld_invasion":
        print("ERROR: スケジューラーが正しいイベントを返しません")
        return False
    print("✓ スケジューラーが正しいイベントを返す")
    
    # 2. イベントトリガーをチェック（スケジュールイベントが優先されるべき）
    triggered_event = wm.check_event_triggers(player, engine, current_turn=test_turn)
    if not triggered_event or triggered_event.id != "interworld_invasion":
        print("ERROR: イベントがトリガーされません")
        return False
    print("✓ イベントが正しくトリガーされる")
    
    # 3. イベントを実際にトリガー
    result = wm.trigger_event(player, triggered_event.id, engine)
    if not result:
        print("ERROR: イベントのトリガーに失敗")
        return False
    print("✓ イベントがトリガーされ、報酬が付与される")
    print(f"  プレイヤーのアクティブイベント: {player.active_world_events}")
    
    # 4. ポイントを加算してランキングとコミュニティゴールを更新
    wm.add_event_points(player, "interworld_invasion", "alien_soldier", amount=3)
    wm.add_event_points(player, "interworld_invasion", "alien_commander", amount=1)
    print("✓ ポイントが加算される")
    
    # 5. ランキングを確認
    ranking = RANKING_MANAGER.get_ranking("interworld_invasion")
    print(f"  ランキング: {ranking}")
    expected_points = 3 * 100 + 1 * 500  # alien_soldier:100, alien_commander:500
    if ranking and ranking[0][1] == expected_points:
        print("✓ ランキングポイントが正しく計算される")
    else:
        print(f"WARNING: ランキングポイントが期待値と異なる: 期待{expected_points}, 実際{ranking[0][1] if ranking else 'None'}")
    
    # 6. コミュニティゴール進捗を確認
    progress = COMMUNITY_GOAL_MANAGER.get_progress("interworld_invasion", "total_points")
    print(f"  コミュニティゴール進捗: {progress}")
    if progress == expected_points:
        print("✓ コミュニティゴール進捗が正しく更新される")
    else:
        print(f"WARNING: コミュニティゴール進捗が期待値と異なる: 期待{expected_points}, 実際{progress}")
    
    # 7. 称号付与をチェック（ポイントが十分であれば）
    stats = {"points": RANKING_MANAGER.get_player_score("interworld_invasion", player.id)}
    newly_granted = wm.check_and_grant_event_titles(player, event, stats)
    print(f"  新規獲得称号: {newly_granted}")
    # 現在のポイントは800なので、"異世界の征服者"(1000ポイント以上)はまだ獲得できない
    # ポイントを追加して1000超えるようにする
    wm.add_event_points(player, "interworld_invasion", "alien_soldier", amount=2)  # +200点
    stats = {"points": RANKING_MANAGER.get_player_score("interworld_invasion", player.id)}
    newly_granted = wm.check_and_grant_event_titles(player, event, stats)
    print(f"  追加ポイント後の新規獲得称号: {newly_granted}")
    if "異世界の征服者" in newly_granted:
        print("✓ 称号が正しく付与される")
    else:
        print("WARNING: 称号が付与されない可能性あり")
    
    # 8. フィードバックを送信（イベント終了後に）
    # イベント終了ターンを過ぎたことをシミュレート
    end_turn = event.end_turn if event.end_turn is not None else test_turn + event.duration
    feedback_turn = end_turn + 10
    print(f"  イベント終了ターン: {end_turn}, フィードバック送信ターン: {feedback_turn}")
    # フィードバックを送信
    feedback = {"rating": 5, "comment": "楽しかった！"}
    success = FEEDBACK_SYSTEM.submit_feedback("interworld_invasion", player.id, feedback)
    if success:
        print("✓ フィードバックが送信される")
    else:
        print("ERROR: フィードバックの送信に失敗")
        return False
    
    # 9. バランスツールで統計を取得
    stats = BALANCE_TOOL.get_event_statistics("interworld_invasion")
    print(f"  イベント統計: {json.dumps(stats, indent=2, ensure_ascii=False)}")
    
    # 10. アセットマネージャでアセットパスを取得（ダミー）
    asset_path = ASSET_MANAGER.get_event_image_path("interworld_invasion", "banner.png")
    print(f"  アセットパス例: {asset_path}")
    
    print("=== シーズンイベントフローテスト完了 ===")
    return True

if __name__ == "__main__":
    success = test_seasonal_event_flow()
    if success:
        print("\n🎉 すべてのテストが成功しました！")
    else:
        print("\n❌ テストが失敗しました。")
        exit(1)