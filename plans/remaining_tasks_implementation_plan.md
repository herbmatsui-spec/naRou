# 残りタスク 詳細実装計画書

## 概要
本計画書は、`IMPLEMENTATION_PLAN_QUEST_PARANOID.md` に基づく残りのフェーズ（4, 5, 7, 8, 9）について詳細な実装手順を定義する。
推奨順序: 4 → 5 → 7 → 8 → 9

---

## フェーズ4: マルチエンド分岐ナラティブDAG (Steps 13-17)

### Step 13: ナラティブノード/エッジ定義（DAG）
- **目的**: `quest_narrative_dag.py` に `NarrativeNode` と `NarrativeEdge` のデータクラスを定義し、DAG 構造を表現する。
- **ファイル**: `quest_narrative_dag.py` (新規作成または既存ファイルの修正)
- **詳細**:
  - `NarrativeNode`: id, description, choices (List[Choice]), consequences (Dict[str, Any])
  - `NarrativeEdge`: source_node_id, target_node_id, condition (optional ConditionNode from CQCT)
  - DAG 検証関数 (has_cycle, topological_sort)
- **検証**:
  - ユニットテスト: `tests/test_narrative_dag.py` を作成し、ノード/エッジ作成、DAG 検証をテスト。
  - 既存の `quest_narrative_dag.py` がある場合は、不足している機能を追加。

### Step 14: 選択肢→分岐→サブ目的→報酬/次クエスト のYAMLスキーマ
- **目的**: `data/quest_narratives.yaml` にナラティブの定義スキーマを作成。
- **ファイル**: `data/quest_narratives.yaml` (新規作成)
- **詳細**:
  - ナラティブIDごとに、ノードリストとエッジリストを定義。
  - 各ノード: id, description, choices (リスト: choice_id, 表示テキスト, 導くノードID, 必要条件オプション)
  - 各エッジ: source, target, condition (オプション, CQCTのDSL文字列)
- **検証**:
  - YAML スキーマバリデーション (必須フィールド存在チェック)
  - テスト: `tests/test_narrative_yaml.py` を作成し、YAML のロードと基本構造をテスト。

### Step 15: DAG実行エンジン（現在ノード管理・選択適用・フラグ更新）
- **目的**: `narrative_executor.py` に `NarrativeExecutor` クラスを実装。
- **ファイル**: `narrative_executor.py` (新規作成または既存ファイルの修正)
- **詳細**:
  - 現在のアクティブナラティブIDと現在ノードIDを保持。
  - プレイヤーの選択を受け取り、条件(CQCT)を評価後、次のノードに遷移。
  - フラグ更新 (story_variables への書き込み) とサブ目的の生成 (QuestObjective への変換)。
  - ナラティブ完了時のコールバック (報酬付与、次クエストのトリガー)。
- **検証**:
  - ユニットテスト: `tests/test_narrative_executor.py` を作成し、選択肢による遷移、フラグ更新、サブ目的生成をテスト。

### Step 16: `story_choices.yaml` / `story_endings.yaml` 統合
- **目的**: 既存の `story_choices.yaml` と `story_endings.yaml` フラグをナラティブ実行と自動同期。
- **ファイル**: 既存ファイルの修正および連携コード
- **詳細**:
  - ナラティブ実行時にフラグ更新が発生した場合、`story_choices.yaml` と `story_endings.yaml` の参照フラグを更新。
  - 逆方向: これらのファイルのフラグ変更がナラティブの条件評価に影響するようにする。
- **検証**:
  - 統合テスト: ナラティブ実行後のフラグ変更がストーリーの選択肢/エンディングに反映されることをテスト。

### Step 17: メインクエストシステムへの組み込み
- **目的**: `main_quest_system.py` に `narrative_dag_id` フィールドを追加し、ナラティブDAGを起動。
- **ファイル**: `main_quest_system.py` (修正)
- **詳細**:
  - `Quest` クラスに `narrative_dag_id: Optional[str] = None` を追加。
  - クエスト開始時に `narrative_dag_id` が設定されている場合、`NarrativeExecutor` を起動。
  - ナラティブ完了イベントをリスンし、クエスト完了条件とする。
- **検証**:
  - テスト: `tests/test_main_quest_narrative.py` を作成し、ナラティブ付きクエストの開始と完了をテスト。

---

## フェーズ5: プロシージャルダンジョン相互生成 (Steps 18-21)

### Step 18: クエスト→ダンジョン要求仕様DSL（部屋/トラップ/敵/ボス座標）
- **目的**: `quest_dungeon_spec.py` に `DungeonSpec` データクラスを定義。
- **ファイル**: `quest_dungeon_spec.py` (新規作成または既存ファイルの修正)
- **詳細**:
  - `DungeonSpec`: width, height, rooms (List[Room]), traps (List[Trap]), enemies (List[EnemySpawn]), boss_position (Position)
  - 各サブクラス (Room, Trap, EnemySpawn, Position) を定義。
  - YAML からのロードとバリデーションメソッド。
- **検証**:
  - ユニットテスト: `tests/test_dungeon_spec.py` を作成し、仕様のロードとバリデーションをテスト。

### Step 19: `procedural_dungeon_generator.py` 拡張（仕様充足モード）
- **目的**: 既存の `procedural_dungeon_generator.py` に `generate_from_spec(spec)` モードを追加。
- **ファイル**: `procedural_dungeon_generator.py` (修正)
- **詳細**:
  - `DungeonSpec` を受け取り、指定された部屋/トラップ/敵/ボスを配置してダンジョンを生成。
  - 仕様を満たさない場合はフォールバックまたはエラー。
- **検証**:
  - テスト: `tests/test_dungeon_generator_spec.py` を作成し、仕様通りのダンジョンが生成されることをテスト。

### Step 20: 生成結果フィードバック（実階層数・ボス座標→クエスト目的更新）
- **目的**: ダンジョン生成結果をクエスト目的にフィードバックし、完全一致を保証。
- **ファイル**: 双方向連携 (複数ファイルにまたがる)
- **詳細**:
  - ダンジョン生成後に実際の階層数とボス座標を取得。
  - クエスト目的 (例: "N階層到達", "ボス討伐") のパラメータ (required_count, target_id) を更新。
  - `procedural_quest_generator.py` と `procedural_dungeon_generator.py` の連携。
- **検証**:
  - 統合テスト: クエストからダンジョンを生成し、生成結果がクエスト目的に正しく反映されることをテスト。

### Step 21: ダンジョン探索クエスト生成パイプライン統合
- **目的**: `procedural_quest_generator.py` に `source_type="dungeon_synced"` を追加。
- **ファイル**: `procedural_quest_generator.py` (修正)
- **詳細**:
  - クエストアーキタイプに `dungeon_synced` を追加し、ダンジョン仕様からクエストを生成。
  - ダンジョンのテーマ/深度を読み込み、目的と報酬を決定。
- **検証**:
  - テスト: `tests/test_dungeon_synced_quest.py` を作成し、ダンジョンシンククエストが生成されることをテスト。

---

## フェーズ7: 考古学・コーデックス・メタ進行三位一体 (Steps 25-28)

### Step 25: クエスト完了→記憶断片ドロップテーブル
- **目的**: `quest_fragment_rewards.py` に `FragmentDropTable` を実装。
- **ファイル**: `quest_fragment_rewards.py` (新規作成)
- **詳細**:
  - クエスト完了時に特定の記憶断片 (fragment) をドロップする確率テーブル。
  - クエストID, 難易度, フラグ状況に基づくドロップ率調整。
- **検証**:
  - ユニットテスト: `tests/test_fragment_rewards.py` を作成し、ドロップロジックをテスト。

### Step 26: `truth_codex` 解読進行との自動連携
- **目的**: `archaeology_system.py` と連携し、断片収集で解読ゲージを上昇。
- **ファイル**: `archaeology_system.py` (修正) および連携コード
- **詳細**:
  - 断片が取得されたとき、`archaeology_system` の解読ゲージを増加。
  - ゲージが最大に達したとき、特別なイベントまたは報酬をトリガー。
- **検証**:
  - 統合テスト: 断片を収集し、解読ゲージが上昇することをテスト。

### Step 27: セット完了ボーナス（真実の一片・NG+引継ぎフラグ）
- **目的**: `meta_progression_system.py` と連携し、断片セット完了で `TruthPiece` を付与。
- **ファイル**: `meta_progression_system.py` (修正) および連携コード
- **詳細**:
  - 特定の断片セットが収集されたとき、`TruthPiece` アイテムを付与。
  - NG+ モードでの引継ぎフラグを設定。
- **検証**:
  - テスト: `tests/test_meta_progression_bonus.py` を作成し、セット完了ボーナスをテスト。

### Step 28: 考古学サイト発掘クエストの動的生成
- **目的**: `procedural_quest_generator.py` に `archetype="excavation"` を追加。
- **ファイル**: `procedural_quest_generator.py` (修正)
- **詳細**:
  - 考古学サイトの発掘クエストを動的に生成。
  - サイトの難易度と残存断片数に基づいて目的と報酬を決定。
- **検証**:
  - テスト: `tests/test_excavation_quest.py` を作成し、発掘クエストが生成されることをテスト。

---

## フェーズ8: ペット同行クエスト (Steps 29-31)

### Step 29: 同行ペットプロファイル解析（種族/契約/融合/進化歴）
- **目的**: `pet_quest_analyzer.py` に `PetProfile` を実装。
- **ファイル**: `pet_quest_analyzer.py` (新規作成)
- **詳細**:
  - プレイヤーの同行ペットから種族, 契約タイプ, 融合歴, 進化段階を抽出。
  - ペットの特性 (属性, スキル, 成長率) をプロファイルにまとめる。
- **検証**:
  - ユニットテスト: `tests/test_pet_profile.py` を作成し、プロファイル抽出をテスト。

### Step 30: ペット固有目的テンプレート・進化触媒連動
- **目的**: `data/pet_quests.yaml` にペット固有のクエスト目的テンプレートを定義。
- **ファイル**: `data/pet_quests.yaml` (新規作成)
- **詳細**:
  - ペットの種族/契約ごとに、専用の目的テンプレート (例: "特殊アイテム収集", "特定敵討伐") を定義。
  - 進化に必要な触媒アイテムをクエスト報酬として設定。
- **検証**:
  - テスト: `tests/test_pet_quests_yaml.py` を作成し、YAML のロードとテンプレート取得をテスト。

### Step 31: クエスト生成・完了時のペット成長フック
- **目的**: クエスト生成/完了時にペットの成長フックを呼び出す。
- **ファイル**: `pet_evolution_system.py`, `pet_fusion_system.py` 連携
- **詳細**:
  - クエスト生成時: ペットの好奇心や忠誠度を刺激する目的を追加 (オプション)。
  - クエスト完了時: ペットの経験値を増加し、進化条件を満たしているかチェック。
  - 進化条件を満たしている場合、専用スキルを解放または進化イベントをトリガー。
- **検証**:
  - 統合テスト: クエスト完了後にペットが成長し、進化条件を満たすことをテスト。

---

## フェーズ9: リアルタイムワールドシミュレーション連動 (Steps 32-36)

### Step 32: ワールドイベント監視バス（戦争/疫病/彗星/継承）
- **目的**: `world_event_hooks.py` に `EventMonitor` を実装。
- **ファイル**: `world_event_hooks.py` (新規作成)
- **詳細**:
  - `world_event_system.py` からイベント発生/終了を監視。
  - イベントタイプ (戦争, 疫病, 彗星, 継承) に応じてハンドラーを呼び出す。
  - イベント期間中のみ有効なフラグやバフを管理。
- **検証**:
  - ユニットテスト: `tests/test_event_monitor.py` を作成し、イベント監視とハンドラー呼び出し simplify
- **検証**:
  - 統合テスト: ワールドイベントが発生したとき、適切なフラグが設定されることをテスト。

### Step 33: 緊急クエスト自動注入（イベント発生中のみ有効）
- **目的**: `emergency_quest_injector.py` にて緊急クエストを動的ボードに注入。
- **ファイル**: `emergency_quest_injector.py` (新規作成)
- **詳細**:
  - イベント発生中、`request_board` に緊急クエストを追加。
  - イベント終了時に緊急クエストを削除。
  - 緊急クエストは通常のクエストより高い報酬とタイムリミットを設定。
- **検証**:
  - テスト: `tests/test_emergency_injector.py` を作成し、イベント中にクエストが注入されることをテスト。

### Step 34: 派閥戦争専用クエストテンプレート（前線/補給/スパイ）
- **目的**: `data/faction_war_quests.yaml` に派閥戦争専用テンプレート brightness
- **ファイル**: `data/faction_war_quests.yaml` (新規作成)
- **詳細**:
  - 前線 (敵拠点討伐), 補給 (資源輸送), スパイ (情報収集) の3種類のクエストテンプレートを定義。
  - 派閥 ID と戦争状況に基づいてクエストを生成。
- **検証**:
  - テスト: `tests/test_faction_war_quests_yaml.py` を作成し、テンプレートのロードをテスト。

### Step 35: 未完了時の機会喪失記録・NPC会話/エンディング反映
- **目的**: `missed_opportunity_system.py` にて機会喪失を記録・反映。
- **ファイル**: `missed_opportunity_system.py` (新規作成)
- **詳細**:
  - 時間制限クエストやイベントクエストが未完了だったとき、`MissedOpportunity` レコードを作成。
  - NPC 会話時に機会喪失についての特別な台詞を表示。
  - エンディング計算時に機会喪失数をマイナス要素として反映。
- **検証**:
  - テスト: `tests/test_missed_opportunity.py` を作成し、機会喪失が記録され反映されることをテスト。

### Step 36: 全システム統合テスト・バランス調整・ドキュメント化
- **目的**: 全システムの統合テストを実施し、バランスを調整。ドキュメントを更新。
- **ファイル**: 全ファイル (テストおよびドキュメント)
- **詳細**:
  - `tests/test_full_integration.py` を作成し、すべてのフェーズが連携して動作することをテスト。
  - バランス調整: クエスト難易度、報酬、発生頻度をプレイテストに基づいて調整。
  - ドキュメント: `README.md` や設計書を更新し、実装内容を反映。
- **検証**:
  - 全テストスイート (`pytest tests/`) を実行し、すべてがパスすることを確認。

---

## 依存関係と注意点
- フェーズ4はCQCT (フェーズ1) に依存するため、フェーズ1が正常に動作していることを前提とする。
- フェーズ5はプロシージャルダンジョンジェネレータおよびプロシージャルクエストジェネレータに依存する。
- フェーズ7は考古学システムおよびメタ進行システムに依存する。
- フェーズ8はペットシステム (進化・融合) に依存する。
- フェーズ9はワールドイベントシステムに依存する。
- 各ステップでは、既存のテストが破損しないように後方互換性を保つこと。