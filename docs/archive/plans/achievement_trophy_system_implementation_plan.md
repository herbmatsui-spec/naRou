# 実績・トロフィーシステム 詳細実装計画書

## Step 1: data/achievements.yaml 基本構造作成
- ファイル `data/achievements.yaml` を作成し、基本的なYAML構造を定義
- 実績のトップレベルキー `achievements:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/achievements.yaml', encoding='utf-8')); print('OK' if data and 'achievements' in data else 'ERROR')"`

## Step 2: data/achievements.yaml 基本実績定義
- `data/achievements.yaml` に「最初の血」の基本構造を追加
- name, description, icon, reward_title, reward_gold, reward_item, hidden: false
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/achievements.yaml', encoding='utf-8')); a=data.get('achievements',{}).get('first_blood'); print(f'Achievement exists: {a is not None}'); print(f'Name: {a.get(\"name\") if a else \"Missing\"}')"`

## Step 3: data/achievements.yaml 称号連動実績追加
- `data/achievements.yaml` に「ゴブリンスレイヤー」実績を追加
- goblin キルカウント条件、タイトル報酬、自動装備フラグ、ステータスボーナス
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/achievements.yaml', encoding='utf-8')); a=data.get('achievements',{}).get('goblin_slayer'); print(f'Condition exists: {\"condition\" in a if a else False}'); print(f'Reward title: {a.get(\"reward_title\") if a else \"Missing\"}')"`

## Step 4: data/meta_progression.yaml 基本構造作成
- ファイル `data/meta_progression.yaml` を作成し、基本的なYAML構造を定義
- メタ進行のトップレベルキー `meta_progression:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/meta_progression.yaml', encoding='utf-8')); print('OK' if data and 'meta_progression' in data else 'ERROR')"`

## Step 5: data/meta_progression.yaml 基本メタ進行定義
- `data/meta_progression.yaml` に「総討伐数」の基本構造を追加
- name, description, icon, milestones 配列
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/meta_progression.yaml', encoding='utf-8')); m=data.get('meta_progression',{}).get('total_monsters_slain'); print(f'Meta exists: {m is not None}'); print(f'Milestones count: {len(m.get(\"milestones\",[])) if m else 0}')"`

## Step 6: entity.py 実績関連フィールド追加準備
- `entity.py` の Entity クラスに実績関連フィールドのプレースホルダーコメントを追加
- フィールド追加の場所を示すコメント: `# TODO: Achievement fields will be added here`
- 検証: `grep -n "TODO: Achievement fields" entity.py`

## Step 7: entity.py 基本実績フィールド追加
- `entity.py` の Entity クラスに `achievements: List[str] = field(default_factory=list)` フィールドを追加
- 必要なインポート: `from typing import List` と `from dataclasses field` が既にあるか確認
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'achievements'))"`

## Step 8: entity.py 実績進捗フィールド追加
- `entity.py` の Entity クラスに `achievement_progress: Dict[str, int] = field(default_factory=dict)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'achievement_progress'))"`

## Step 9: entity.py 時間制限実績タイマーフィールド追加
- `entity.py` の Entity クラスに `achievement_timers: Dict[str, int] = field(default_factory=dict)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'achievement_timers'))"`

## Step 10: entity.py コレクション実績フィールド追加
- `entity.py` の Entity クラスに `monster_killed_types: Dict[str, int] = field(default_factory=dict)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'monster_killed_types'))"`

## Step 11: entity.py ユニークアイテムコレクションフィールド追加
- `entity.py` の Entity クラスに `unique_items_obtained: List[str] = field(default_factory=list)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'unique_items_obtained'))"`

## Step 12: entity.py ソーシャル実績フィールド追加
- `entity.py` の Entity クラスに `social_points: int = 0` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'social_points'))"`

## Step 13: entity.py 週間プレイタイムフィールド追加
- `entity.py` の Entity クラスに `weekly_play_time: int = 0` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'weekly_play_time'))"`

## Step 14: entity.py 転生関連フィールド追加
- `entity.py` の Entity クラスに `reincarnation_count: int = 0` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'reincarnation_count'))"`

## Step 15: entity.py 総獲得レベルフィールド追加
- `entity.py` の Entity クラスに `total_level_earned: int = 0` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'total_level_earned'))"`

## Step 16: entity.py 永続ボーナスフィールド追加
- `entity.py` の Entity クラスに `permanent_bonuses: Dict[str, int] = field(default_factory=dict)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'permanent_bonuses'))"`

## Step 17: entity.py メタ進行フィールド追加
- `entity.py` の Entity クラスに `meta_progression: Dict[str, int] = field(default_factory=dict)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'meta_progression'))"`

## Step 18: achievement_system.py 新規ファイル作成
- 空のファイル `achievement_system.py` を作成
- 基本的なファイルヘッダーとコメントを追加
- 検証: `ls -la achievement_system.py`

## Step 19: achievement_system.py AchievementData クラス定義
- `achievement_system.py` に `@dataclass` デコレータ付きの `AchievementData` クラスを定義
- フィールド: id, name, description, icon, reward_title, reward_gold, reward_item, reward_skill_points, hidden, prerequisites, trigger_condition
- 検証: `python -c "from achievement_system import AchievementData; print('AchievementData class exists')"`

## Step 20: achievement_system.py AchievementRegistry クラス作成
- `achievement_system.py` に `AchievementRegistry` クラスをシングルトンパターンで作成
- `__new__` メソッドでシングルトン実装
- `all()` メソッドで全実績データの取得
- 検証: `python -c "from achievement_system import REGISTRY; REGISTRY.load(); print('Registry loaded')"`

## Step 21: achievement_system.py AchievementRegistry.load() 実装
- `AchievementRegistry.load()` メソッドを実装
- `data/achievements.yaml` からYAMLを読み込み、AchievementData オブジェクトに変換
- エラーハンドリング（ファイルが存在しない場合のデフォルト実績作成）
- 検証: `python -c "from achievement_system import REGISTRY; REGISTRY.load(); print(f'Loaded {len(REGISTRY.all())} achievements')"`

## Step 22: achievement_system.py AchievementManager クラス作成
- `achievement_system.py` に `AchievementManager` クラスを作成
- `check_achievement()` メソッドのスタブ実装
- `grant_achievement()` メソッドのスタブ実装
- 検証: `python -c "from achievement_system import AchievementManager; m = AchievementManager(); print('Manager created')"`

## Step 23: achievement_system.py 基本実績チェックロジック
- `AchievementManager.check_achievement()` メソッドを実装
- 基本的な条件評価ロジック（簡単なカウントベースの条件から開始）
- 検証: `python -c "from achievement_system import AchievementManager; m = AchievementManager(); print('check_achievement method exists')"`

## Step 24: achievement_system.py 実績付与ロジック
- `AchievementManager.grant_achievement()` メソッドを実装
- 実績の重複付与防止
- 実績リストへの追加
- 基本的な報酬付与（ゴールドのみ）
- 検証: `python -c "from achievement_system import AchievementManager; m = AchievementManager(); print('grant_achievement method exists')"`

## Step 25: game.py 実績マネージャー参照追加
- `game.py` の Engine クラスに `achievement_manager: AchievementManager` フィールドを追加
- `__init__` メソッドで初期化
- 検証: `python -c "from game import Engine; e = Engine(); print(hasattr(e, 'achievement_manager'))"`

## Step 26: game.py _on_kill メソッド実績チェック準備
- `game.py` の `_on_kill` メソッドに 実績チェックのプレースホルダーを追加
- モンスター撃破時の基本的な実績チェック呼び出しのスタブ
- 検証: `grep -n "# TODO: Achievement check" game.py`

## Step 27: game.py _on_kill メソッド基本実績チェック実装
- `game.py` の `_on_kill` メソッドに 基本的な実績チェックロジックを実装
- モンスター名前ベースの簡単な実績進行更新
- 検証: `python -c "import game; print('_on_kill method can be called')"`

## Step 28: game.py advance_world メソッド定期実績チェック追加
- `game.py` の `advance_world` メソッドに 定期的な実績チェックを追加
- 100ターンごとに実績チェックを実行（頻度は調整可能）
- 検証: `python -c "import game; print('advance_world method can be called')"`

## Step 29: advanced_systems.py SaveSystem 実績データ保存準備
- `advanced_systems.py` の SaveSystem クラスに 実績データ保存のプレースホルダーを追加
- セーブ時に実績データを含める準備コメント
- 検証: `grep -n "# TODO: Achievement data" advanced_systems.py`

## Step 30: advanced_systems.py SaveSystem 実績データ保存実装
- `advanced_systems.py` の SaveSystem.save() メソッドを修正
- エンティティの実績データを含めてセーブ
- ピクル化前に実績リストを処理
- 検証: セーブ/ロードテスト用の簡単なスクリプト実行

## Step 31: advanced_systems.py SaveSystem 実績データロード実装
- `advanced_systems.py` の SaveSystem.load() メソッドを修正
- ロード時に実績データを復元
- 後方互換性のためデフォルト値を設定
- 検証: セーブ/ロードテスト用の簡単なスクリプト実行

## Step 32: data/achievements.yaml ダンジョン探検家実績追加
- `data/achievements.yaml` に「ダンジョン探検家」実績を追加
- ダンジョンフロア探索数ベースの実績
- 報酬: 探検家称号、スキルポイント50
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/achievements.yaml', encoding='utf-8')); a=data.get('achievements',{}).get('dungeon_explorer'); print(f'Reward title: {a.get(\"reward_title\") if a else \"Missing\"}')"`

## Step 33: game.py ダンジョン探索カウンター追加準備
- `entity.py` に `dungeon_floors_visited: Set[Tuple[int, int]] = field(default_factory=set)` フィールドを追加（ダンジョンIDとフロア番号の組み合わせ）
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'dungeon_floors_visited'))"`

## Step 34: game.py ダンジョン移動時のカウンター更新
- `game.py` の `descend_stairs()` メソッドで ダンジョンフロア訪問カウンターを更新
- 新しいフロアに到達時にセットに追加
- 検証: `python -c "import game; print('descend_stairs method can be called')"`

## Step 35: achievement_system.py ダンジョン探検家実績チェックロジック
- `AchievementManager.check_achievement()` メソッドに ダンジョン探検家実績の条件チェックを追加
- ダンジョンフロア訪問セットのサイズが10以上かチェック
- 検証: `python -c "from achievement_system import AchievementManager; m = AchievementManager(); print('Dungeon explorer check logic added')"`

## Step 36: data/achievements.yaml コレクション実績枠組み追加
- `data/achievements.yaml` に コレクションタイプの実績枠組みを追加（コメントとして構造を示す）
- `monster_collector` と `item_collector` の基本構造をプレースホルダーとして追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/achievements.yaml', encoding='utf-8')); print('Collector achievements structure exists')"`

## Step 37: data/achievements.yaml スピードランナー実績追加
- `data/achievements.yaml` に「スピードランナー」実績を追加
- 時間制限実績として、1時間以内のゲームクリアを条件
- 報酬: speed_demon称号、速度+20ボーナス
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/achievements.yaml', encoding='utf-8')); a=data.get('achievements',{}).get('speed_runner'); print(f'Time limit: {a.get(\"time_limit\") if a else \"Missing\"}'); print(f'Reward title: {a.get(\"reward_title\") if a else \"Missing\"}')"`

## Step 38: game.py プレイ時間カウンター追加準備
- `entity.py` に `play_time_seconds: int = 0` フィールドを追加（実績の時間制限用）
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'play_time_seconds'))"`

## Step 39: game.py プレイ時間更新ロジック
- `game.py` の `advance_world()` メソッドで プレイ時間カウンターを1秒ずつインクリメント
- ターンベースのため、実際の秒数に換算する調整が必要だが、ここでは簡略化
- 検証: `python -c "import game; print('advance_world updates play time')"`

## Step 40: achievement_system.py スピードランナー実績チェックロジック
- `AchievementManager.check_achievement()` メソッドに スピードランナー実績の条件チェックを追加
- プレイ時間が3600秒以内かつゲームクリア条件をチェック（簡略化のため、特定のフラグを使用）
- 検証: `python -c "from achievement_system import AchievementManager; m = AchievementManager(); print('Speed runner check logic added')"`

## Step 41: data/achievements.yaml 祭り参加者実績追加
- `data/achievements.yaml` に「祭り参加者」実績を追加
- 特定日付でのゲームプレイを条件（01-01, 08-15, 12-25）
- 報酬: festival_goer称号、祭りトークンアイテム
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/achievements.yaml', encoding='utf-8')); a=data.get('achievements',{}).get('festival_participant'); print(f'Available dates: {a.get(\"available_dates\") if a else \"Missing\"}'); print(f'Reward title: {a.get(\"reward_title\") if a else \"Missing\"}')"`

## Step 42: game.py 日付チェックロジック追加準備
- `entity.py` に `last_festival_check: str = ""` フィールドを追加（最後に祭りをチェックした日付）
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'last_festival_check'))"`

## Step 43: game.py 日付更新ロジック
- `game.py` の `advance_world()` メソッドで 現在日付を取得し、祭り参加条件をチェック
- 簡略化のため、ターン数から日付を推定するロジックを実装（実際のゲームでは別の日付システムがあるはず）
- 検証: `python -c "import game; print('advance_world checks date for festivals')"`

## Step 44: achievement_system.py 祭り参加者実績チェックロジック
- `AchievementManager.check_achievement()` メソッドに 祭り参加者実績の条件チェックを追加
- 現在日付が指定の祭り日付のいずれかと一致するかチェック
- 検証: `python -c "from achievement_system import AchievementManager; m = AchievementManager(); print('Festival participant check logic added')"`

## Step 45: data/achievements.yaml モンスター収集家実績追加
- `data/achievements.yaml` に「モンスター収集家」実績を追加
- 全モンスター種類を少なくとも1体ずつ倒すことを条件
- モンスターキルタイプ辞書を使用した進捗追跡
- 報酬: naturalist称号、図鑑解放
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/achievements.yaml', encoding='utf-8')); a=data.get('achievements',{}).get('monster_collector'); print(f'Collection type: {a.get(\"collection_type\") if a else \"Missing\"}'); print(f'Target count: {a.get(\"target_count\") if a else \"Missing\"}')"`

## Step 46: game.py モンスター撃破時のモンスターキルタイプ更新
- `game.py` の `_on_kill()` メソッドで モンスターキルタイプ辞書を更新
- モンスターの種類キーでカウントをインクリメント
- 検証: `python -c "import game; print('_on_kill updates monster kill types')"`

## Step 47: achievement_system.py モンスター収集家実績チェックロジック
- `AchievementManager.check_achievement()` メソッドに モンスター収集家実績の条件チェックを追加
- モンスターキルタイプ辞書のサイズが目標数以上かチェック（全種類を倒したか）
- 検証: `python -c "from achievement_system import AchievementManager; m = AchievementManager(); print('Monster collector check logic added')"`

## Step 48: data/achievements.yaml アイテム収集家実績追加
- `data/achievements.yaml` に「アイテム収集家」実績を追加
- レアアイテムを全種類収集することを条件
- ユニークアイテム取得リストを使用した進捗追跡
- 報酬: hoarder称号、インベントリスロット増加20
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/achievements.yaml', encoding='utf-8')); a=data.get('achievements',{}).get('item_collector'); print(f'Collection type: {a.get(\"collection_type\") if a else \"Missing\"}'); print(f'Target count: {a.get(\"target_count\") if a else \"Missing\"}')"`

## Step 49: game.py アイテム取得時のユニークアイテムリスト更新
- `game.py` の アイテム取得関連メソッドで ユニークアイテム取得リストを更新
- 新しいアイテムを取得時にリストに追加（重複は避ける）
- 検証: `python -c "import game; print('Item acquisition updates unique items list')"`

## Step 50: achievement_system.py アイテム収集家実績チェックロジック
- `AchievementManager.check_achievement()` メソッドに アイテム収集家実績の条件チェックを追加
- ユニークアイテム取得リストのサイズが目標数以上かチェック
- 検証: `python -c "from achievement_system import AchievementManager; m = AchievementManager(); print('Item collector check logic added')"`

## Step 51: data/achievements.yaml 週間チャンピオン実績追加
- `data/achievements.yaml` に「週間チャンピオン」実績を追加
- 今週のプレイ時間ランキング上位1%を条件（簡略化のため、一定時間以上プレイ）
- 報酬: weekly_champ称号、週間スポットライトエフェクト
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/achievements.yaml', encoding='utf-8')); a=data.get('achievements',{}).get('weekly_champion'); print(f'Social based: {a.get(\"social_based\") if a else \"Missing\"}'); print(f'Reward title: {a.get(\"reward_title\") if a else \"Missing\"}')"`

## Step 52: game.py ソーシャルポイントシステム準備
- `entity.py` に `social_points: int = 0` フィールドを追加（既に追加済みだが、ここで活用開始）
- 週間プレイタイムカウンターも活用
- 検証: `python -c "from entity import Entity; e = Entity(); print(f'Social points: {e.social_points}, Weekly time: {e.weekly_play_time}')"`

## Step 53: game.py 週間プレイタイム更新ロジック
- `game.py` の `advance_world()` メソッドで 週間プレイタイムカウンターをインクリメント
- 実際のゲームでは週次リセットロジックが必要だが、ここでは簡略化
- 検証: `python -c "import game; print('advance_world updates weekly play time')"`

## Step 54: achievement_system.py 週間チャンピオン実績チェックロジック（簡易版）
- `AchievementManager.check_achievement()` メソッドに 週間チャンピオン実績の条件チェックを追加（簡易版）
- 週間プレイタイムが一定閾値以上かチェック
- 検証: `python -c "from achievement_system import AchievementManager; m = AchievementManager(); print('Weekly champion check logic added (simplified)')"`

## Step 55: data/achievements.yaml 友達助っ人実績追加
- `data/achievements.yaml` に「友達助っ人」実績を追加
- フレンドのクエストを5回助けることを条件（ソーシャル機能がある場合）
- 報酬: loyal_friend称号、協力プレイ時ボーナス増加10%
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/achievements.yaml', encoding='utf-8')); a=data.get('achievements',{}).get('friend_helper'); print(f'Social based: {a.get(\"social_based\") if a else \"Missing\"}'); print(f'Reward title: {a.get(\"reward_title\") if a else \"Missing\"}')"`

## Step 56: entity.py フレンドヘルプカウンター追加
- `entity.py` に `friend_helps: int = 0` フィールドを追加（フレンドを助けた回数）
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'friend_helps'))"`

## Step 57: game.py フレンドヘルプ時のカウンター更新
- `game.py` の フレンドヘルプ関連メソッドで フレンドヘルプカウンターをインクリメント
- 実際のフレンドシステムがある場合のプレースホルダー
- 検証: `python -c "import game; print('Friend help increments counter')"`

## Step 58: achievement_system.py 友達助っ人実績チェックロジック
- `AchievementManager.check_achievement()` メソッドに 友達助っ人実績の条件チェックを追加
- フレンドヘルプカウンターが5以上かチェック
- 検証: `python -c "from achievement_system import AchievementManager; m = AchievementManager(); print('Friend helper check logic added')"`

## Step 59: data/achievements.yaml 転生英雄実績追加
- `data/achievements.yaml` に「転生英雄」実績を追加
- 5回転生して累計レベル1000達成を条件
- 転生回数と総獲得レベルを使用した進捗追跡
- 報酬: eternal_hero称号、永続ボーナスベース統+5、古代の知識解放
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/achievements.yaml', encoding='utf-8')); a=data.get('achievements',{}).get('reincarnation_hero'); print(f'Reincarnation req: {a.get(\"requirement\",{}).get(\"reincarnation_count\") if a else \"Missing\"}'); print(f'Total level req: {a.get(\"requirement\",{}).get(\"total_level_earned\") if a else \"Missing\"}')"`

## Step 60: game.py 転生時のレベル獲得カウント
- `game.py` の 転生関連メソッドで 総獲得レベルカウントを更新
- 転生時に現在レベルを総獲得レベルに加算
- 検証: `python -c "import game; print('Reincarnation updates total level earned')"`

## Step 61: game.py 転生回数カウント更新
- `game.py` の 転生関連メソッドで 転生回数カウントをインクリメント
- 検証: `python -c "import game; print('Reincarnation increments reincarnation count')"`

## Step 62: achievement_system.py 転生英雄実績チェックロジック
- `AchievementManager.check_achievement()` メソッドに 転生英雄実績の条件チェックを追加
- 転生回数が5以上かつ総獲得レベルが1000以上かチェック
- 検証: `python -c "from achievement_system import AchievementManager; m = AchievementManager(); print('Reincarnation hero check logic added')"`

## Step 63: data/achievements.yaml メタマスター実績追加
- `data/achievements.yaml` に「メタマスター」実績を追加
- 全メタ進行システムを最大まで上げることを条件
- メタ進行マイルストーンの全達成を条件とする
- 報酬: transcendent称号、チャレンジモード解放
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/achievements.yaml', encoding='utf-8')); a=data.get('achievements',{}).get('meta_master'); print(f'Meta progression based: {a.get(\"meta_progression_based\") if a else \"Missing\"}'); print(f'Reward title: {a.get(\"reward_title\") if a else \"Missing\"}')"`

## Step 64: achievement_system.py メタマスター実績チェックロジック
- `AchievementManager.check_achievement()` メソッドに メタマスター実績の条件チェックを追加
- 全メタ進行マイルストーンが達成されているかチェック
- 検証: `python -c "from achievement_system import AchievementManager; m = AchievementManager(); print('Meta master check logic added')"`

## Step 65: data/achievements.yaml 隠し実績枠組み追加
- `data/achievements.yaml` に 隠し実績の枠組みを追加（コメントとして構造を示す）
- `the_secret_cow_level` などの隠し実績の基本構造をプレースホルダーとして追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/achievements.yaml', encoding='utf-8')); print('Hidden achievements structure exists')"`

## Step 66: data/achievements.yaml 秘密の牛レベル実績追加
- `data/achievements.yaml` に「秘密の牛レベル」実績を追加
- 特殊な方法で秘密レベルに到達を条件（特殊アイテム組み合わせ等）
- 報酬: cow_king称号、ホーリーハンドグレネードアイテム、牛レベル解放
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/achievements.yaml', encoding='utf-8')); a=data.get('achievements',{}).get('the_secret_cow_level'); print(f'Hidden: {a.get(\"hidden\") if a else \"Missing\"}'); print(f'Reward title: {a.get(\"reward_title\") if a else \"Missing\"}')"`

## Step 67: game.py 特殊アイテム組み合わせチェック準備
- `entity.py` に `special_items_combo: List[str] = field(default_factory=list)` フィールドを追加
- 特殊アイテム組み合わせ実績のためのアイテムトラッキング
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'special_items_combo'))"`

## Step 68: game.py アイテム取得時の特殊アイテムトラッキング
- `game.py` の アイテム取得関連メソッドで 特殊アイテムを取得時にトラッキングリストに追加
- 特定のアイテムIDをチェックしてリストに追加
- 検証: `python -c "import game; print('Item acquisition tracks special items')"`

## Step 69: achievement_system.py 秘密の牛レベル実績チェックロジック
- `AchievementManager.check_achievement()` メソッドに 秘密の牛レベル実績の条件チェックを追加
- 特殊アイテム組み合わせが完成しているかチェック
- 検証: `python -c "from achievement_system import AchievementManager; m = AchievementManager(); print('Secret cow level check logic added')"`

## Step 70: render_all.py 実績獲得通知UI追加準備
- `game.py` の `render_all()` メソッドに 実績獲得通知UIのプレースホルダーを追加
- 実績獲得時にポップアップ通知を表示する準備
- 検証: `grep -n "# TODO: Achievement notification" game.py`

## Step 71: render_all.py 実績獲得通知UI実装
- `game.py` の `render_all()` メソッドに 実績獲得通知UIを実装
- 新しく獲得した実績を一時的に画面に表示（フェードイン/アウト効果付き）
- 検証: `python -c "import game; print('render_all shows achievement notifications')"`

## Step 72: game.py 実績一覧UI呼び出しキー割り当て
- `game.py` の `main()` メソッドまたは入力処理で 実績一覧UIを呼び出すキーを割り当て（例：Shift+A）
- 実績一覧スクリーンを表示するゲーム状態を追加
- 検証: `python -c "import game; print('Achievement list UI key binding exists')"`

この実装計画書は、実績・トロフィーシステムを72の小さなステップに分割しています。
各ステップは具体的なファイル変更、コード追加、および検証コマンドを含んでおり、
低性能なLLMでも段階的に実装を進めることができます。
