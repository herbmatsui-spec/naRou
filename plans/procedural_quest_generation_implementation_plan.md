# プロシージャル・クエスト生成システム 実装計画書（36ステップ）

> 対象：`procedural_scenarios.yaml` の拡張と、新モジュール `procedural_quest_generator.py` の追加。
> ゴール：依頼ボード／ランダムダンジョン探索／NPC個別クエストを「難易度×報酬×舞台」で自動生成し、プレイ時間を指数拡張・リプレイ性を確保する。
> 設計原則：既存の `Registry/Manager/Data` 3層パターンと ECS コンポーネント永続化に厳密準拠。

---

## フェーズA：データ設計（ステップ 1-8）

### ステップ 1：quest_generation セクションの追加
`data/procedural_scenarios.yaml` に `scenario_templates`（既存）を残したまま、新トップキー `quest_generation:` を追加。ここが本システムの全設定の入り口となる。既存ローダ（`StorytellerRegistry`）は `scenario_templates` のみを読むため影響なし。

### ステップ 2：クエストアーキタイプ定義
`quest_generation.archetypes` に7種を定義：slay（討伐）/ gather（採取）/ escort（護衛）/ explore（探索）/ boss_hunt（ボス討伐）/ rescue（救出）/ delivery（配達）。各要素は `objective_type`（kill/collect/visit/escort/explore）、`title_template`、`desc_template`、`reward_weight`（報酬倍率）、`base_complexity`（難易度寄与）を持つ。

### ステップ 3：難易度ティア定義
`quest_generation.difficulty_tiers` に6段階を定義：tutorial（序）/ easy（低）/ normal（中）/ hard（高）/ extreme（極）/ abyss（深淵）。各ティアは `level_range:[min,max]`、`enemy_multiplier`（指数）、`objective_complexity`（目的数増加倍率）、`recommended_power`（推奨戦力）を持つ。enemy_multiplier はティアごとに指数増加させ「指数拡張」を実現。

### ステップ 4：報酬テーブル定義
`quest_generation.reward_tables` に5段階を定義：copper/silver/gold/rainbow/legendary。各テーブルは `gold_range:[min,max]`、`exp_range`、`item_pool:[...]`、`bonus`（名声/友好度/メタポイント）を持つ。難易度と掛け合わせて最終報酬を算出。

### ステップ 5：舞台設定定義
`quest_generation.stage_settings` に8種を定義：town/forest/cave/ruins/volcano/snowfield/swamp/abyss。各舞台は `flavor`（情景文）、`enemy_pool:[...]`、`hazard`（環境ハザード）、`depth_modifier`（深度補正）、`environmental_modifier`（報酬/難易度補正）を持つ。これが「組み合わせ爆発」の軸の一つ。

### ステップ 6：NPC個別クエストテーマ定義
`quest_generation.npc_quest_themes` に NPC 種別ごとのテーマを定義：villager/merchant/noble/priest/adventurer。各テーマは `quest_pool:[archetype_id...]`、`relationship_gate`（友好度閾値）、`flavor`（個別台詞）を持つ。友好度がゲートとなる。

### ステップ 7：既存シナリオの維持検証
`scenario_templates.goblin_invasion` がそのまま存在し、既存 `StorytellerRegistry` が壊らないことをテストで確認（後方互換の保証）。

### ステップ 8：依頼ボード設定
`quest_generation.request_board` に `max_active`（同時掲示数=例8）、`refresh_cycle`（リフレッシュ周期）、`type_weights`（アーキタイプ出現重み）、`min_difficulty`/`max_difficulty`（プレイヤー進行度で可変）を定義。

---

## フェーズB：データクラス（ステップ 9-14）

### ステップ 9：QuestArchetype
`@dataclass` で定義。`id,name,objective_type,title_template,desc_template,reward_weight:float,base_complexity:int` を持つ。

### ステップ 10：DifficultyTier
`id,name,level_range:List[int],enemy_multiplier:float,objective_complexity:float,recommended_power:int` を持つ。

### ステップ 11：RewardTable
`id,name,gold_range:List[int],exp_range:List[int],item_pool:List[str],bonus:Dict[str,int]` を持つ。

### ステップ 12：StageSetting
`id,name,flavor,enemy_pool:List[str],hazard,depth_modifier:float,environmental_modifier:float` を持つ。

### ステップ 13：NPCQuestTheme
`npc_type,quest_pool:List[str],relationship_gate:int,flavor` を持つ。

### ステップ 14：GeneratedQuest / QuestObjectiveSpec
`QuestObjectiveSpec(objective_id,description,target_type,target_id,required_count)` と `GeneratedQuest(quest_id,title,description,source_type,archetype_id,difficulty_id,reward_id,setting_id,npc_id,seed,recommended_level,objectives:List[QuestObjectiveSpec],reward:Dict,expires)` を定義。これが生成物の正体。

---

## フェーズC：レジストリ（ステップ 15-18）

### ステップ 15：QuestGenerationRegistry クラス
全設定を保持し、シングルトンで Engine 全体から共有するレジストリ。

### ステップ 16：シングルトン化
`__new__` で同一インスタンスを返す既存パターンを踏襲。`REGISTRY` モジュール定数を公開。

### ステップ 17：load() 実装
`data/procedural_scenarios.yaml` を読み、`quest_generation` 配下を各データクラスへマッピング。ファイル不在時は組み込みフォールバックを返し、テスト環境でも動くよう保証。

### ステップ 18：取得メソッド群
`get_archetype / get_difficulty / get_reward / get_setting / get_npc_theme / board_config / all_tiers / all_settings` を実装し、生成エンジンから参照可能にする。

---

## フェーズD：合成エンジン（ステップ 19-23）

### ステップ 19：シード決定論ヘルパー `_seeded_rng`
`(seed, *keys)` から `random.Random` を決定論的に生成するヘルパー。同一入力→同一出力を保証しリプレイ性の基盤とする。

### ステップ 20：コア合成 `_compose`
`archetype × difficulty × reward × setting` を受け取り `GeneratedQuest` を構築。各軸のパラメータを掛け合わせて目的数・敵数・推奨レベルを算出。

### ステップ 21：タイトル/説明文自動生成
テンプレートに `{setting}` `{archetype}` `{difficulty}` 等を埋め込み、情景豊かな日本語タイトル/説明を生成。ハザード・敵プールから文を動的生成。

### ステップ 22：目的オブジェクト自動生成
`objective_type` と難易度の `objective_complexity` から `required_count` を指数補正して `QuestObjectiveSpec` を生成（討伐なら敵数、採取なら個数、探索なら到達深度など）。

### ステップ 23：報酬合成
難易度 `enemy_multiplier` × 報酬テーブル `gold_range/exp_range` を掛け、アイテムをシード選択、ボーナス（名声/友好/メタ）を加算して `reward` 辞書を確定。

---

## フェーズE：依頼ボード（ステップ 24-27）

### ステップ 24：generate_board_quest
ボード用クエスト1件を生成。type_weights に従いアーキタイプを選び、プレイヤーレベルに応じた難易度帯から difficulty を抽選。

### ステップ 25：generate_board_pool
`max_active` 件を生成し、シードで重複排除（同一タイトル/同一4軸組み合わせを弾く）して多様性を保証。

### ステップ 26：refresh_board（マネージャ）
ボードを再生成し `ProceduralQuestComponent.active_board` を更新。refresh_cycle 経過で自動リフレッシュ。

### ステップ 27：出現重み・推奨レベル適用
プレイヤー進行度で `min/max_difficulty` を動的制限し、高ティアほど稀に出現するよう重みを補正。

---

## フェーズF：ランダムダンジョン探索（ステップ 28-30）

### ステップ 28：generate_dungeon_quest
`procedural_dungeon_generator` のテーマ/深度を読み込み、ダンジョン潜入クエストを生成。

### ステップ 29：ダンジョン目的生成
「N階層到達」「ボス討伐」「特定アイテム持ち帰り」のいずれかを目的とし、深度×難易度で required_count を算出。

### ステップ 30：舞台×テーマ合成
ダンジョンテーマと `stage_settings` を掛け合わせ、敵プール・ハザード・報酬補正を統合。

---

## フェーズG：NPC個別クエスト（ステップ 31-33）

### ステップ 31：generate_npc_quest
NPC の `npc_type` からテーマを選び、個別クエストを生成。`npc_id` をクエストに紐付け。

### ステップ 32：友好度ゲート
`relationship_system` のレベル/友好度が `relationship_gate` 以上でなければ生成・受諾を拒否。

### ステップ 33：個別フレーバー・報酬
NPC 種別の `flavor` を説明文に埋め込み、友好度に応じボーナス報酬を上乗せ。

---

## フェーズH：管理・進捗・報酬（ステップ 34-35）

### ステップ 34：update_progress / complete_quest
イベント（kill/collect/visit/explore）に基づき目的を進捗させ、全目的達成で complete。報酬を金貨/経験/アイテム/名声に付与。

### ステップ 35：ProceduralQuestComponent 追加と永続化
`components.py` に `ProceduralQuestComponent`（active_board/accepted_quests/completed_count/board_seed/history）を追加。`entity.py` へ登録、`save_system.py` の互換リストへ追加し永続化。

---

## フェーズI：統合・テスト（ステップ 36）

### ステップ 36：Engine 統合 ＋ 36ステップ総合テスト
`game.py` に `quest_generation_registry / procedural_quest_generator / procedural_quest_manager` を登録。`tests/test_procedural_quest_generation_36_steps.py` を作成し、各ステップをアサーションで検証。決定論（同一シード同一クエスト）と組み合わせ爆発（1000通り超の一意性）を証明し、全テスト成功をもって完了とする。

---

## 成果指標（KPI）
- 組み合わせ数：7×6×5×8 = 1,680 通り（基底）＋シード多様性で実質無限。
- リプレイ性：同一シード再現率 100%、異シード非重複率 >99%。
- プレイ時間曲線：難易度ティアの敵数・所要時間が指数増加（線形→指数）。
