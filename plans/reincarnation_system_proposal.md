# 輪廻転生・ニューゲーム+システム 詳細提案書

## 概要
輪廻転生・ニューゲーム+システムは、プレイヤーが一定の条件を満たすとキャラクターを転生させ、レベルはリセットされるものの累積された特典やボーナスを引き継いで新たな人生を始めるシステムです。これにより、長期的なプレイ動機付けと戦略的なキャラクター成長が可能になります。

## 9つの提案詳細

### 1. 基本転生システム
**データ構造（`data/reincarnation.yaml`）**
```yaml
reincarnation:
  base_requirements:
    min_level: 100  # 転生に必要な最低レベル
    max_level: 200  # 転生可能な最大レベル（オーバーレベル転生）
  stat_bonus_per_reincarnation:
    strength: 2
    vitality: 2
    magic: 1
    speed: 1
  level_reset_multiplier: 0.8  # 転生後の必要経験値係数（0.8 = 20% 割引）
```

**実装箇所**
- `entity.py` に `reincarnation_count: int = 0` フィールド追加
- `reincarnation_system.py` 新規ファイル作成（ReincarnationData, ReincarnationRegistry, ReincarnationManager クラス）
- `game.py` の レベルアップ処理 と 特定条件（レベル達到・アイテム使用等）で 転生オプションを表示
- `advanced_systems.py` の SaveSystem に 転生データの保存/読み込み追加

### 2. 特典継承システム（Benefits Inheritance）
**データ構造（`data/reincarnation_inheritance.yaml`）**
```yaml
inheritance:
  always_keep:  # 転生時に必ず引き継ぐもの
    - "titles"         # 獲得した称号は全て保持
    - "achievements"   # 実績は全て保持
    - "meta_progression" # メタ進行要素は全て保持
  selective_keep:   # 選択して引き継ぐもの（ポイント制）
    points_per_reincarnation: 3
    items:          # アイテム継承
      cost: 1
      max_count: 5  # 最大5アイテムまで選択可能
    skills:         # スキル継承
      cost: 2
      max_count: 2  # 最大2スキルまで選択可能
    gold_fraction:  # ゴールドの継承割合
      cost: 1
      ratio: 0.1    # 10% のゴールドを継続（ポイント1あたり）
```

**実装箇所**
- `entity.py` に 継承選択用の一時フィールド追加（転生準備中）
- `reincarnation_system.py` の 継承ロジック実装
- `game.py` の 転生UIで 継承選択画面を実装
- 各システム（タイトル、実績、アイテム等）で 転生時の継承可否フラグ参照

### 3. カーマ値システム（Karma System）
**データ構造（`data/karma.yaml`）**
```yaml
karma:
  alignment:  # カーマの軸
    law_chaos:   # 秩序-混沌軸
      range: [-1000, 1000]
      neutral: 0
    good_evil:   # 善-悪軸
      range: [-1000, 1000]
      neutral: 0
  actions:       # 行動によるカーマ変化
    murder_innocent:  # 無実者殺害
      law_chaos: -10
      good_evil: -20
    donate_to_temple: # 寺院への寄付
      law_chaos: 5
      good_evil: 15
  reincarnation_effects:  # 転生時のカーマ効果
    high_good:        # 高い善カーマ
      threshold: 500
      benefits:
        starting_gold_bonus: 0.5  # 50% 増加
        blessed_items_chance: 0.1 # 10% の確率で祝福アイテム開始
    high_evil:        # 高い悪カーマ
      threshold: -500
      benefits:
        starting_attack_bonus: 5
        curse_resistance: 0.2   # 20% 呪い耐性
```

**実装箇所**
- `entity.py` に `karma_law_chaos: int = 0` と `karma_good_evil: int = 0` フィールド追加
- `karma_system.py` 新規ファイル作成
- `game.py` の 各種行動（戦闘、アイテム使用、クエスト完了等）で カーマ変動を適用
- `reincarnation_system.py` の 転生時にカーマに基づくボーナス/ペナルティを適用
- UIで カーマ値と軸の表示（オプション）

### 4. 転生専用ダンジョンシステム
**データ構造（`data/reincarnation_dungeons.yaml`）**
```yaml
dungeons:
  first_life_trial:  # 1転生目専用ダンジョン
    min_reincarnation: 1
    max_reincarnation: 1
    name: "最初の試練"
    description: "転生者のみが挑戦できる試練のダンジョン"
    floors: 5
    rewards:
      unique_item: "rebirth_amulet"
      title: "転生者"
    unlock_condition: "first_reincarnation"
  eternal_arena:     # 永遠の闘技場（高転生専用）
    min_reincarnation: 5
    name: "永遠の闘技場"
    description: "5回以上転生した者のみが入場できる闘技場"
    floors: 50
    is_arena: true   # アリーナタイプ
    rewards:
      title: "arena_champion"
      stat_bonus_per_floor: {strength: 1}
```

**実装箇所**
- `entity.py` に `unlocked_reincarnation_dungeons: List[str] = field(default_factory=list)` フィールド追加
- `reincarnation_dungeon_system.py` 新規ファイル作成
- `map_engine.py` の ダンジョン生成ロジックで 転生回数に基づくダンジョン選択
- `game.py` の ダンジョン入場チェックで 転生回数制限を検証
- `reincarnation_system.py` の 転生時に 新規ダンジョンアンロックをチェック

### 5. 段階的難易度スケーリング
**データ構造（`data/reincarnation_scaling.yaml`）**
```yaml
scaling:
  enemy_stats_multiplier:  # 転生ごとの敵能力増加
    base: 1.0
    per_reincarnation: 0.15  # 15% 増加/転生
    max_multiplier: 3.0      # 最大300% まで
  item_drop_improvement:   # 転生ごとのアイテムドロップ改善
    base: 1.0
    per_reincarnation: 0.05  # 5% 増加/転生
    max_multiplier: 2.0
  experience_penalty:      # 転生ごとの経験値獲得ペナルティ（バランス調整）
    base: 1.0
    per_reincarnation: 0.02  # 2% 増加/転生
    max_multiplier: 1.5
```

**実装箇所**
- `systems.py` の 戦闘計算 で 転生回数ベースの敵能力修正を適用
- `item_system.py` の ドロップ計算 で 転生回数ベースのドロップ率修正
- `game.py` の 経験値取得処理 で 転生回数ベースの経験値ペナルティ適用
- バランス調整用の 定数 を 定数ファイルまたは設定ファイルに追加

### 6. レガシースキルシステム
**データ構造（`data/legacy_skills.yaml`）**
```yaml
legacy_skills:
  soul_memory:      # 魂の記憶
    min_reincarnation: 2
    description: "前生のスキル経験値の一部を保持"
    effect: 
      type: "skill_experience_retention"
      ratio: 0.1  # 前生のスキル経験値の10%を現在のスキルに加算
    unlock_condition: "reincarnation_count >= 2"
  ancestral_knowledge: # 先祖の知識
    min_reincarnation: 5
    description: "特定スキルタイプの学習速度向上"
    effect:
      type: "skill_learning_bonus"
      skill_type: "magic"
      bonus: 0.2  # 魔法スキルの学習速度20%向上
    unlock_condition: "reincarnation_count >= 5"
```

**実装箇所**
- `entity.py` に `legacy_skills: List[str] = field(default_factory=list)` フィールド追加
- `legacy_skill_system.py` 新規ファイル作成
- `game.py` の スキル経験値取得処理 で レガシースキル効果を適用
- `reincarnation_system.py` の 転生時に 新規レガシースキルアンロックをチェック
- スキルUIで レガシースキル効果の表示

### 7. 転生チャレンジシステム
**データ構造（`data/reincarnation_challenges.yaml`）**
```yaml
challenges:
  pacifist_run:      # 非暴力転生
    description: "敵を倒さずに転生する"
    requirements:
      kills: 0
      min_reincarnation: 1
    rewards:
      title: "pacifist"
      karma_bonus: {good_evil: 100}
      unique_item: "peace_amulet"
  speed_reincarnation: # 高速転生
    description: "1時間以内に最初の転生を達成する"
    requirements:
      play_time_seconds: 3600
      max_reincarnation: 1
    rewards:
      title: "speed_reincarnator"
      stat_bonus: {speed: 5}
      experience_bonus: 0.1  # 次の人生での経験値獲得+10%
```

**実装箇所**
- `entity.py` に チャレンジ進捗用フィールド追加（実績システムと連携可能）
- `reincarnation_challenge_system.py` 新規ファイル作成
- `game.py` の 各種カウントアップ処理で チャレンジ進捗を更新
- `reincarnation_system.py` の 転生時に チャレンジ達成条件をチェックし報酬付与
- 実績システムとの連携（チャレンジ達成を実績として扱うオプション）

### 8. メモリーフラグメントシステム
**データ構造（`data/memory_fragments.yaml`）**
```yaml
fragments:
  first_life_memory:  # 最初の人生の記憶
    description: "最初の人生での出来事の断片"
    icon: "🧩"
    unlock_condition: "first_reincarnation_and_defeat_dragon"
    lore: "あなたは最初の人生で古竜を倒したが..."
    effect:
      type: "title_unlock"
      title: "dragon_slayer_memory"
  collective_unconscious: # 集合無意識
    description: "転生者共通の無意識の断片"
    icon: "🌀"
    unlock_condition: "total_reincarnations_across_all_players >= 1000"  # サーバー共有条件の例
    lore: "無数の転生者たちの経験が織りなす..."
    effect:
      type: "global_buff"
      buff: {all_stats: 1}
      duration: "until_next_reincarnation"
```

**実装箇所**
- `entity.py` に `collected_fragments: List[str] = field(default_factory=list)` フィールド追加
- `memory_fragment_system.py` 新規ファイル作成
- `game.py` の 特定イベント（ボス撃破、特殊場所訪問、転生等）で フラグメント獲得チェック
- フラグメント効果の適用ロジック（タイトル、バフ等）
- ロックされたフラグメントの ヒントシステム（オプション）
- 共有条件がある場合の オンライン連携 ロジック

### 9. 神聖恩寵システム（Divine Favor System）
**データ構造（`data/divine_favor.yaml`）**
```yaml
favor:
  gods:           # 各神の恩寵
    jure:         # 神ジュレ（法と秩序の神）
      favor_per_prayer: 10
      max_favor: 1000
      reincarnation_bonuses:
        - threshold: 200
          bonus: {law_chaos: 50}  # 法のカーマ+50
        - threshold: 500
          bonus:  # 転生時に保護の祝福
            type: "blessing"
            effect: "damage_reduction"
            value: 0.1  # 10% ダメージ軽減
            duration: "100 turns"
    lulwy:        # 神ルルウィー（風と速さの神）
      favor_per_action:  # 素早い行動による恩寵獲得
        dodge_attack: 5
        cast_quick_spell: 3
      max_favor: 800
      reincarnation_bonuses:
        - threshold: 300
          bonus: {speed: 3}  # 転生時の初期速度+3
        - threshold: 600
          bonus:  # 転生時に風の恩寵
            type: "elemental_affinity"
            element: "wind"
            value: 0.2  # 風属性耐性+20%
```

**実装箇所**
- `entity.py` に 各神への `favor: Dict[str, int] = field(default_factory=list)` フィールド追加
- `divine_favor_system.py` 新規ファイル作成（既存の神システムがある場合は拡張）
- `game.py` の 祈祷・特定行動 で 恩寵値を増減
- `reincarnation_system.py` の 転生時に 高恩寵神のボーナスを適用
- 既存の 神システム との連携（神情報に恩寵閾値・ボーナスデータを追加）

## 実装優先度マトリクス

| 優先度 | システム | 説明 | 実装難易度 |
|--------|----------|------|------------|
| 高 | 基本転生システム | 転生の核となるメカニクス | 中 |
| 高 | 特典継承システム | プレイヤーの引き継ぎ要望に直接応答 | 中 |
| 中 | カーマ値システム | 道徳的選択の深みを追加 | 中 |
| 中 | 転生専用ダンジョン | 転生者専用コンテンツでやりがい提供 | 中 |
| 中 | 段階的難易度スケーリング | 長期バランス維持のため必須 | 低 |
| 低 | レガシースキルシステム | 転生の戦略的深みを追加 | 高 |
| 低 | 転生チャレンジシステム | 特殊プレイスタイルを促進 | 中 |
| 低 | メモリーフラグメントシステム | 収集要素とロリー要素 | 高 |
| 中 | 神聖恩寵システム | 既存神システムとの連携で深み追加 | 中 |

## entity.py への追加フィールド

```python
@dataclass
class Entity:
    # ... existing fields ...
    # 転生システム
    reincarnation_count: int = 0
    karma_law_chaos: int = 0
    karma_good_evil: int = 0
    legacy_skills: List[str] = field(default_factory=list)
    unlocked_reincarnation_dungeons: List[str] = field(default_factory=list)
    collected_fragments: List[str] = field(default_factory=list)
    favor: Dict[str, int] = field(default_factory=list)  # 神ID: 恩寵値
    
    # 転生準備用一時フィールド（転生選択画面で使用）
    inheritance_selection: Dict[str, Any] = field(default_factory=dict)
    
    # チャレンジ進捗用（実績システムと連携可）
    challenge_progress: Dict[str, int] = field(default_factory=dict)
```

## 統合フロー

1. プレイヤーがレベル上限に到達するか、特定の転生アイテムを使用
2. `game.py` が 転生オプションを表示（転生可能条件をチェック）
3. プレイヤーが 転生を選択
4. 転生準備UIで:
   - 引き継ぐアイテム/スキルを選択（ポイント制）
   - 現在のカーマ値を確認
   - 利用可能な転生ボーナスを表示
5. 転生実行時に:
   - `reincarnation_system.py` が 継承処理を実行
   - カーマに基づくボーナス/ペナルティを適用
   - レガシースキル・神恩寵ボーナスを付与
   - 転生回数をインクリメント
   - レベル・経験値をリセット（ただし累積ボーナス適用）
   - 新規ダンジョン・チャレンジ・フラグメントのアンロックをチェック
6. `advanced_systems.py` の SaveSystem で 転生データを保存
7. 新しい人生では:
   - 基本ステータスは低いが、累積ボーナス適用
   - 転生専用ダンジョンへのアクセス可能
   - エンハンスド難易度での戦闘
   - 継承されたスキル/アイテムで 有利なスタート

## 次のステップ

1. 「輪廻転生・ニューゲーム+システムの詳細な実装計画書を作成して　低性能なLLMでも実装可能なように１～７２までの小さなステップに分割して」
   - 本提案書を基に、72段階の細かい実装手順に分割した計画書を作成