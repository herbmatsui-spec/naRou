# 実績・トロフィーシステム 詳細提案書

## 概要
実績・トロフィーシステムは、プレイヤーの特定の行動やマイルストーンを達成すると称号、報酬、メタ進行要素を付与するシステムです。これにより、プレイヤーは長期的な目標を持ち、繰り返しプレイの動機付けが得られます。

## 9つの提案詳細

### 1. 基本実績システム
**データ構造（`data/achievements.yaml`）**
```yaml
achievements:
  first_blood:
    name: "最初の血"
    description: "初めて敵を倒す"
    icon: "💧"
    reward_title: "初心者"
    reward_gold: 100
    reward_item: "iron_sword"
    hidden: false
  dungeon_explorer:
    name: "ダンジョン探検家"
    description: "10 different ダンジョンフロアを探索"
    icon: "🗺️"
    reward_title: "探検家"
    reward_skill_points: 50
    hidden: false
  # ... more achievements
```

**実装箇所**
- `entity.py` に `achievements: List[str] = field(default_factory=list)` フィールド追加
- `achievement_system.py` 新規ファイル作成（AchievementData, AchievementRegistry, AchievementManager クラス）
- `game.py` の `_on_kill()`、`advance_world()` に実績チェックロジック追加
- `advanced_systems.py` の SaveSystem に実績データの保存/読み込み追加

### 2. 称号連動実績
**データ構造（`data/achievements.yaml` の拡張）**
```yaml
achievements:
  goblin_slayer:
    name: "ゴブリンスレイヤー"
    description: " goblin を 100 匹倒す"
    icon: "⚔️"
    reward_title: "goblin_slayer"  # タイトルシステムと連動
    reward_title_equip_auto: true  # 自動装備
    reward_stat_bonus:  # ステータスボーナス
      strength: 5
    hidden: false
```

**実装箇所**
- `achievement_system.py` の `grant_achievement()` メソッドでタイトルシステムと連動
- `title_system.py` の `TitleManager` に `check_achievement_based_titles()` メソッド追加
- `game.py` の実績付与時に自動タイトル装備ロジック追加

### 3. メタ進行要素（永続ボーナス）
**データ構造（`data/meta_progression.yaml`）**
```yaml
meta_progression:
  total_monsters_slain:
    name: "総討伐数"
    description: "倒したモンスターの総数に応じて永続ボーナス"
    icon: "📊"
    milestones:
      - count: 1000
        bonus: "gold_find"
        value: 5  # %  increase
        description: "ゴールド発見率 +5%"
      - count: 5000
        bonus: "item_drop"
        value: 10  # %  increase
        description: "アイテムドロップ率 +10%"
      - count: 10000
        bonus: "stat_growth"
        value: 0.1  # multiplier
        description: "ステータス成長率 +10%"
```

**実装箇所**
- `entity.py` に `meta_progression: Dict[str, int] = field(default_factory=list)` フィールド追加
- `meta_progression_system.py` 新規ファイル作成
- `game.py` の各種カウントアップ処理にメタ進行更新ロジック追加
- `advanced_systems.py` の SaveSystem にメタ進行データ追加
- 各種計算関数（経験値取得、アイテムドロップ等）にメタ進行ボーナス適用

### 4. 連鎖実績システム
**データ構造（`data/achievements.yaml` の拡張）**
```yaml
achievements:
  weapon_master_sword:
    name: "剣の達人"
    description: "剣スキルを最大まで上げる"
    icon: "⚔️"
    prerequisites: ["sword_novice", "sword_apprentice"]  # 前置実績
    reward_title: "sword_master"
    chain_bonus:  # 連鎖ボーナス
      next_achievement: "weapon_master_all"
      bonus_multiplier: 1.5
  weapon_master_all:
    name: "万能武器使い"
    description: "全武器タイプの達人になる"
    icon: "🌟"
    hidden: true  # 前置実績を達成するまで隠し
    reward_title: "legendary_fighter"
```

**実装箇所**
- `achievement_system.py` の AchievementManager に 前置実績チェックロジック追加
- 実績表示UIで 前置未達成の実績をグレーアウトまたは非表示
- 連鎖ボーナスの自動適用メカニズム実装
- `game.py` の実績チェック処理で 前置実績達成時の連鎖ボーナス付与

### 5. 隠し実績・秘密実績
**データ構造（`data/achievements.yaml` の拡張）**
```yaml
achievements:
  the_secret_cow_level:
    name: "秘密の牛レベル"
    description: " 特殊な方法で秘密レベルに到達"
    icon: "🐄"
    hidden: true
    trigger_condition: "special_item_combo"  # 特殊アイテム組み合わせで発動
    reward_title: "cow_king"
    reward_unique_item: "holy_hand_grenade"
    reward_secret_area_unlock: "cow_level_access"
```

**実装箇所**
- `achievement_system.py` に 隠し実績のトリガーチェックメカニズム
- `game.py` の特定アクション（アイテム使用、特殊場所訪問等）で 隠し実績トリガーチェック
- 隠し実績達成時の 特別演出・通知システム
- 実績一覧UIでの 隠し実績表示制御（達成前は???、達成後は詳細表示）

### 6. 時間制限・イベント実績
**データ構造（`data/achievements.yaml` の拡張）**
```yaml
achievements:
  speed_runner:
    name: "スピードランナー"
    description: "1時間以内にゲームクリア"
    icon: "⏱️"
    time_limit: 3600  # seconds
    reward_title: "speed_demon"
    reward_stat_bonus:
      speed: 20
    reset_on_reincarnation: true  # 転生時にリセット
  festival_participant:
    name: "祭り参加者"
    description: "季節祭りに参加"
    icon: "🎪"
    available_dates: ["01-01", "08-15", "12-25"]  # 月日形式
    reward_title: "festival_goer"
    reward_unique_item: "festival_token"
```

**実装箇所**
- `entity.py` に `achievement_timers: Dict[str, int] = field(default_factory=list)` フィールド追加
- `achievement_system.py` に タイマーベースの実績チェックロジック
- `game.py` の `advance_world()` で 日付チェック・タイマー更新
- カレンダーシステムとの連携（既存の日付システムがある場合）
- 時間制限実績の 視覚的カウントダウンUI表示

### 7. コレクション・コンプリート実績
**データ構造（`data/achievements.yaml` の拡張）**
```yaml
achievements:
  monster_collector:
    name: "モンスター収集家"
    description: "全モンスタータイプを少なくとも1体ずつ倒す"
    icon: "📚"
    collection_type: "monster_species"
    target_count: 150  # 全モンスター種類数
    progress_tracking: true
    reward_title: "naturalist"
    reward_book_unlock: "bestiary"
  item_collector:
    name: "アイテム収集家"
    description: "レアアイテムを全種類収集"
    icon: "🎒"
    collection_type: "rare_items"
    target_count: 50
    reward_title: "hoarder"
    reward_storage_expansion: 20  # インベントリスロット増加
```

**実装箇所**
- `entity.py` に コレクション進捗用フィールド追加
  - `monster_killed_types: Dict[str, int] = field(default_factory=list)`
  - `unique_items_obtained: List[str] = field(default_factory=list)`
- `achievement_system.py` に コレクション進捗追跡ロジック
- `game.py` の モンスター撃破・アイテム取得処理で コレクション更新
- コレクションUIの 実装（未収集項目の表示、進捗率表示）
- コンプリート時の 特別報酬付与メカニズム

### 8. ソーシャル・競争実績
**データ構造（`data/achievements.yaml` の拡張）**
```yaml
achievements:
  weekly_champion:
    name: "週間チャンピオン"
    description: "今週のプレイ時間ランキング上位1%"
    icon: "🏆"
    social_based: true
    reset_period: "weekly"
    reward_title: "weekly_champ"
    reward_unique_effect: "weekly_spotlight"  # 視覚的エフェクト
  friend_helper:
    name: "友達助っ人"
    description: "フレンドのクエストを5回助ける"
    icon: "🤝"
    social_based: true
    reward_title: "loyal_friend"
    reward_coop_bonus: 10  # 協力プレイ時ボーナス増加
```

**実装箇所**
- `entity.py` に ソーシャル実績用フィールド追加（オンライン機能がある場合）
  - `social_points: int = 0`
  - `weekly_play_time: int = 0`
- `achievement_system.py` に ソーシャル実績評価ロジック
- ランキングシステムとの連携（既存か新規実装）
- 週次・月次リセットメカニズム
- ソーシャルボーナスの 協力プレイ効果実装

### 9. 転生・メタ実績システム
**データ構造（`data/achievements.yaml` の拡張）**
```yaml
achievements:
  reincarnation_hero:
    name: "転生英雄"
    description: "5回転生して累計レベル1000達成"
    icon: "🔄"
    meta_progression_based: true
    requirement:
      reincarnation_count: 5
      total_level_earned: 1000
    reward_title: "eternal_hero"
    reward_permanent_bonus:  # 転生しても消えないボーナス
      base_stat_increase: 5
    reward_legacy_unlock: "ancient_wisdom"  # 次の転生で知識継承
  meta_master:
    name: "メタマスター"
    description: "全メタ進行システムを最大まで上げる"
    icon: "⭐"
    meta_progression_based: true
    reward_title: "transcendent"
    reward_game_mode_unlock: "challenge_mode"
```

**実装箇所**
- `entity.py` に 転生・メタ実績用フィールド追加
  - `reincarnation_count: int = 0`
  - `total_level_earned: int = 0`
  - `permanent_bonuses: Dict[str, int] = field(default_factory=list)`
- `achievement_system.py` に 転生ベースの実績チェックロジック
- 転生システムとの連携（実績データの一部を引き継ぐかリセットするか選択可能）
- 永続ボーナスの 転生間保持メカニズム
- メタマスター達成時の 特別ゲームモード・コンテンツアンロック

## 実装優先度マトリクス

| 優先度 | 実績タイプ | 説明 | 実装難易度 |
|--------|------------|------|------------|
| 高 | 基本実績システム | 基盤となる実績付与・報酬システム | 低 |
| 高 | 称号連動実績 | 既存タイトルシステムとの連携 | 低 |
| 中 | メタ進行要素 | 長期プレイヤーのモチベーション維持 | 中 |
| 中 | 連鎖実績システム | 実績の関連性を持たせた設計 | 中 |
| 低 | 隠し実績・秘密実績 | 発見の楽しさを提供 | 中 |
| 低 | 時間制限・イベント実績 | 季節イベント・タイムアタック要素 | 中 |
| 中 | コレクション・コンプリート実績 | 収集欲を刺激するシステム | 中 |
| 低 | ソーシャル・競争実績 | コミュニティ形成・競争促進（オンライン機能前提） | 高 |
| 低 | 転生・メタ実績システム | 超長期プレイヤー向けの深い要素 | 高 |

## entity.py への追加フィールド

```python
@dataclass
class Entity:
    # ... existing fields ...
    # 実績システム
    achievements: List[str] = field(default_factory=list)
    achievement_progress: Dict[str, int] = field(default_factory=list)  # 進行中の実績進捗
    achievement_timers: Dict[str, int] = field(default_factory=list)  # 時間制限実績用タイマー
    
    # コレクション実績用
    monster_killed_types: Dict[str, int] = field(default_factory=list)
    unique_items_obtained: List[str] = field(default_factory=list)
    
    # ソーシャル実績用（オンライン機能がある場合）
    social_points: int = 0
    weekly_play_time: int = 0
    
    # 転生・メタ実績用
    reincarnation_count: int = 0
    total_level_earned: int = 0
    permanent_bonuses: Dict[str, int] = field(default_factory=list)
    
    # メタ進行要素用
    meta_progression: Dict[str, int] = field(default_factory=list)
```

## 統合フロー

1. プレイヤーが行動を行う（モンスター撃破、アイテム取得、場所訪問等）
2. `game.py` の各種処理で 関連するカウンター更新
3. `advance_world()` で 定期的な実績チェック（ターンベースまたは時間ベース）
4. `achievement_system.py` の `check_all_achievements()` が 条件を評価
5. 条件達成時、`grant_achievement()` で 実績付与処理
6. 実績付与時に:
   - 称号付与（タイトルシステムと連動）
   - アイテム・ゴールド報酬付与
   - メタ進行ボーナス更新
   - 隠し実績トリガーチェック
   - ソーシャルポイント加算
7. `advanced_systems.py` の SaveSystem で 実績データの永続化
8. `render_all()` で 実績獲得通知UI表示
9. 実績一覧UI（特定キーで呼び出し）で 実績進捗表示

## 次のステップ

1. 「実績・トロフィーシステムの詳細な実装計画書を作成して　低性能なLLMでも実装可能なように１～７２までの小さなステップに分割して」
   - 本提案書を基に、72段階の細かい実装手順に分割した計画書を作成