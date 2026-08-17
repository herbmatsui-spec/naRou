# シーズン制ライブコンテンツ・パイプライン マニュアル

## 概要
このドキュメントは、naRouにおけるシーズン制ライブコンテンツ・パイプラインの仕組みと設定方法について説明します。このパイプラインにより、四半期ごとの期間限定イベントをデータ駆動で追加し、専用報酬・ランキング・称号を提供できます。

## 目次
1. [システム概要](#システム概要)
2. [ワールドイベントYAMLの設定](#ワールドイベントyamlyamlの設定)
3. [報酬システム](#報酬システム)
4. [ランキングシステム](#ランキングシステム)
5. [称号システム](#称号システム)
6. [スケジューラー](#スケジューラー)
7. [コミュニティゴール](#コミュニティゴール)
8. [フィードバックシステム](#フィードバックシステム)
9. [バランス調整ツール](#バランス調整ツール)
10. [アセット管理](#アセット管理)
11. [UI連携](#ui連携)
12. [イベントの追加方法](#イベントの追加方法)
13. [トラブルシューティング](#トラブルシューティング)

## システム概要
シーズン制ライブコンテンツ・パイプラインは、以下のコンポーネントで構成されます：
- **WorldEventSystem**: イベントのトリガー、発生、進行を管理
- **RewardManager**: イベント報酬の付与を処理
- **RankingManager**: イベントポイントとランキングを管理
- **TitleManager**: イベント称号の付与を処理
- **EventScheduler**: イベントのスケジュール（開始・終了ターン）を管理
- **CommunityGoalManager**: サーバー全体での協力目標を管理
- **FeedbackSystem**: イベント終了後のプレイヤーフィードバックを収集
- **BalanceTool**: イベントデータを分析しバランス調整を提案
- **AssetManager**: イベント専用アセット（画像、サウンド、ストーリー）を管理

これらのコンポーネントは連携して、データ駆動の期間限定イベントを実現します。

## ワールドイベントYAMLの設定
すべてのワールドイベントは `data/world_events.yaml` で定義されます。ファイルの構造は以下の通りです：

```yaml
world_events:
  イベントID:
    id: "イベントID"
    name: "イベント名"
    description: "イベントの説明"
    trigger_conditions:
      turns_interval: 整数  # ターン間隔（オプション）
      chance: 浮動小数点   # 発生確率（0.0-1.0）
    duration: 整数          # イベント持続ターン数
    effects:
      # イベント効果（例: enemy_dmg_mult: 1.3）
    story_triggers:
      - "ストーリートリガーID"
    # シーズンイベント用追加フィールド
    quarter: 整数           # 1:春, 2:夏, 3:秋, 4:冬（オプション）
    rewards:
      special_currency: "通貨ID"  # オプション
      currency_amount: 整数       # オプション、デフォルト100
      item_drops:
        "アイテムID": ドロップ確率  # オプション
    rankings:
      type: "points"                # 現在はポイント型のみサポート
      point_sources:
        "アクションタイプ": ポイント値  # 例: "alien_soldier": 100
    titles:
      - condition: "条件式"         # 例: "points >= 1000"
        title: "称号名"
        description: "称号の説明"
    community_goal:
      type: "ゴールタイプ"         # 例: "total_points"
      target: 整数                 # 目標値
      reward: "達成時の報酬"       # 例: "global_exp_boost_2x"
    announcement_period: 整数      # イベント開始前何ターンから予告するか
    start_turn: 整数               # イベント開始ターン（オプション）
    end_turn: 整数                 # イベント終了ターン（オプション）
```

### フィールドの説明
- **trigger_conditions**: ランダムイベントとしての発生条件。シーズンイベントではスケジューラーが優先されるため、必須ではない。
- **duration**: イベントがアクティブであるターン数。
- **effects**: イベントが発生中に適用されるゲーム効果（敵ダメージ倍率など）。
- **story_triggers**: イベント発生時にトリガーされるストーリーフラグ。
- **quarter**: シーズンイベントの場合、対応する四半期（1-4）。スケジュールターンが設定されている場合は無視される。
- **rewards**: イベント期間中に付与可能な報酬。
  - `special_currency`: イベント専用通貨のID。
  - `currency_amount`: 通貨付与量（デフォルト100）。
  - `item_drops`: アイテムIDとドロップ確率のマッピング。
- **rankings**: イベント期間中のランキング設定。
  - `point_sources`: アクションタイプごとのポイント値（例: 敵の討伐でポイント獲得）。
- **titles**: イベント達成度に応じて付与される称号のリスト。
  - `condition`: 称号付与条件（簡易式評価、`points >= 1000` のような形式）。
  - `title`: 称号名。
  - `description`: 称号の説明。
- **community_goal**: サーバー全体での協力目標。
  - `type`: ゴールの種類（現在は "total_points" のみサポート）。
  - `target`: 目標達成に必要な値。
  - `reward`: 目標達成時の全プレイヤーへの報酬。
- **announcement_period**: イベント開始前何ターンから予告を開始するか。
- **start_turn / end_turn**: イベントのスケジュールされた開始・終了ターン。設定されている場合、quarterフィールドより優先される。

## 報酬システム
RewardManager はイベント発生時にプレイヤーに報酬を付与します。
- 特別通貨: `special_currency` フィールドで指定された通貨を付与。
- アイテムドロップ: `item_drops` フィールドに従ってランダムでアイテムを付与。
実際のアイテム・通貨システムへの連携はゲーム固有の実装に委ねられます（現在の実装ではプレースホルダー）。

## ランキングシステム
RankingManager はイベントごとにプレイヤーのポイントを追跡します。
- ポイントは `add_event_points` メソッド（ワールドイベントマネージャ経由）または直接 `add_points` で加算。
- ポイント値はイベントの `rankings.point_sources` からアクションタイプごとに参照。
- ランキングはポイントの降順でソートされ、`get_ranking` メソッドで取得可能。

## 称号システム
TitleManager はイベント達成条件に基づいて称号を付与します。
- 条件は簡易評価エンジンで処理され、現在は `points >= X` 形式のみサポート。
- プレイヤーが条件を満たすと、`check_and_grant_event_titles` メソッドで新規獲得称号のリストを取得。
- 称号はプレイヤーごとに保存され、重複付与は防止される。

## スケジューラー
EventScheduler は現在のターンと四半期に基づいてアクティブなシーズンイベントを決定します。
- `start_turn` と `end_turn` が設定されている場合、その期間内にイベントがアクティブ。
- 設定されていない場合は、`quarter` フィールドに基づいて現在の四半期と一致するイベントをアクティブとみなす。
- アナウンス期間は `announcement_period` フィールドで設定され、イベント開始前の指定ターンからアナウンス対象となる。

## コミュニティゴール
CommunityGoalManager はサーバー全体での協力目標を管理します。
- 現在のところ「総ポイント」タイプのみサポート。
- ワールドイベントマネージャの `add_event_points` メソッドがポイント加算時に自動的に進捗を更新。
- 目標達成時に `is_goal_achieved` メソッドで確認可能。

## フィードバックシステム
FeedbackSystem はイベント終了後にプレイヤーからのフィードバックを収集します。
- フィードバックは JSON ファイルとして `feedback/` ディレクトリに保存。
- 各フィードバックにはイベントID、プレイヤーID、タイムスタンプ、評価（1-5）、コメントを含む。
- `get_average_rating` メソッドでイベントの平均評価を取得可能。

## バランス調整ツール
BalanceTool は収集したデータに基づいてイベントバランスの調整を提案します。
- 参加率、平均評価、ゴール達成率に基づいてトリガー確率、報酬量、難易度、ゴール目標などの調整を提案。
- `get_event_statistics` メソッドでイベントの統計情報を取得。
- `suggest_adjustments` メソッドで調整提案を取得。

## アセット管理
AssetManager はイベント専用アセット（画像、サウンド、ストーリー）のパスを管理します。
- アセットは `assets/events/<イベントID>/<タイプ>/<ファイル名>` の構造で配置。
- タイプは `image`, `sound`, `story` など。
- `get_event_image_path`, `get_event_sound_path`, `get_event_story_path` メソッドでパスgreg

## UI連携
Webサーバー経由で UI データを取得するための API エンドポイントが提供されます（`web_server.py` 参照）：
- `GET /api/event/info?turn=<ターン数>`: 現在のアクティブイベント情報
- `GET /api/event/ranking?event_id=<ID>&top_n=<数>`: 指定イベントのランキング
- `GET /api/event/score?event_id=<ID>&player_id=<ID>`: プレイヤーのスコア
- `GET /api/event/titles?event_id=<ID>&player_id=<ID>`: プレイヤーの称号（実装簡易版）
- `GET /api/event/all_rankings`: すべてのイベントのランキング

## イベントの追加方法
新しいシーズンイベントを追加するには、`data/world_events.yaml` に以下の手順で追加します：
1. イベントIDを決定（例: `ancient_civilization_awakening`）
2. 必須フィールド（id, name, description, duration, など）を設定
3. シーズンイベントである場合、`quarter` または `start_turn`/`end_turn` を設定
4. 報酬、ランキング、称号、コミュニティゴール、アナウンス期間などを必要に応じて設定
5. ファイルを保存し、ゲームを再起動（またはイベントレジストリをリロード）

### 例：夏のイベント「古代文明の覚醒」
```yaml
ancient_civilization_awakening:
  id: "ancient_civilization_awakening"
  name: "古代文明の覚醒"
  description: "古代の遺跡から秘めた力が目覚め、特別な報酬が得られる。"
  trigger_conditions:
    turns_interval: 1200
    chance: 0.08
  duration: 180
  effects:
    ancient_relic_drop_chance: 0.15
    exp_gain_mult: 1.75
  story_triggers:
    - "ancient_whispers"
  quarter: 2
  rewards:
    special_currency: "ancient_shards"
    currency_amount: 50
    item_drops:
      "relic_fragment": 0.2
      "ancient_core": 0.05
  rankings:
    type: "points"
    point_sources:
      "guardian": 200
      "ancient_core": 500
  titles:
    - condition: "points >= 1500"
      title: "古代の探求者"
      description: "古代文明の覚醒で1500ポイント以上を獲得した証"
    - condition: "points >= 5000"
      title: "文明の守護者"
      description: "古代文明の覚醒で5000ポイント以上を獲得した伝説の考古学者"
  community_goal:
    type: "total_points"
    target: 500000
    reward: "global_drop_rate_1.5x"
  announcement_period: 75
  start_turn: 450
  end_turn: 630
```

## トラブルシューティング
- **イベントが発生しない**：
  - スケジューラーが正しく設定されているか確認（`start_turn`/`end_turn` または `quarter`）
  - YAMLの構文が正しいか確認（`yamllint data/world_events.yaml` などで検証）
  - ゲームログでイベントレジストリのロードエラーがないか確認
- **ランキングが更新されない**：
  - ポイント加算メソッドが正しく呼び出されているか確認
  - イベントの `rankings.point_sources` が正しく設定されているか確認
- **称号が付与されない**：
  - 条件式が正しい形式か確認（現在サポートは `points >= X` のみ）
  - プレイヤーのポイントが条件を満たしているか確認
- **コミュニティゴールが進まない**：
  - ポイント加算時に自動更新されるはずだが、イベントIDが一致しているか確認
  - ゴールタイプが `total_points` に設定されているか確認

## 開発者向け
### コンポーネントの依存関係
- `WorldEventSystem`: コアロジック
- `RewardManager`, `RankingManager`, `TitleManager`, `EventScheduler`, `CommunityGoalManager`, `FeedbackSystem`, `BalanceTool`, `AssetManager`: 各機能を担当するマネージャークラス
- 各マネージャーはシングルトンインスタンスとして `world_event_system.py` または自身のモジュールで生成

### カスタマイズポイント
- 称号条件の評価ロジックは `TitleManager._evaluate_condition` を拡張
- 報酬付与ロジックは `RewardManager._grant_currency` / `_grant_item` を実装
- アセットの実際の読み込みはゲーム固有のレンダラーサイドで実装

## バージョン情報
- バージョン: 1.0.0
- 最終更新: 2026-08-17