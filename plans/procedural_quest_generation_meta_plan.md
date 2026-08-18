# プロシージャル・クエスト生成システム 実装計画書作成のための計画（メタ計画）

本ドキュメントは「36ステップ実装計画書」をどの手順で作成し、その後どの順序で実装するかを定義する。ゴールは「依頼ボード／ランダムダンジョン探索／NPC個別クエスト」の3経路を自動生成し、指数関数的なプレイ時間拡張とリプレイ性を実現すること。

---

## 1. 計画作成の手順（メタステップ）

### M1. 要件の分解
- ユーザー要求を「3経路の生成」「難易度×報酬×舞台の組み合わせ」「指数拡張」「リプレイ性」の4軸に分解。
- 既存 `procedural_scenarios.yaml` の `scenario_templates` を壊さず拡張する制約を確認。

### M2. 既存コード調査（事実ベース）
- `storyteller_system.py`：Registry/Manager/Data の 3 層パターンを確認。
- `guild_quest_system.py`：進捗・達成・報酬付与の実装を確認。
- `procedural_dungeon_generator.py`：`DungeonThemeRegistry`／`ProceduralDungeonGenerator` 連携方法を確認。
- `components.py`／`entity.py`／`game.py`／`save_system.py`：ECS コンポーネントの追加・Engine 登録・永続化フローを確認。
- `tests/test_dungeon_world_storyteller_72_steps.py`：ステップ逐次アサーションテストの記法を確認。

### M3. データモデルの設計
- YAML スキーマ：`quest_generation`（archetypes / difficulty_tiers / reward_tables / stage_settings / npc_quest_themes / request_board）。
- Python データクラス：QuestArchetype / DifficultyTier / RewardTable / StageSetting / NPCQuestTheme / GeneratedQuest / QuestObjectiveSpec。
- シード決定論の乱数ヘルパー設計。

### M4. 36ステップへの分割
- データ(1-8) → データクラス(9-14) → レジストリ(15-18) → 合成エンジン(19-23) → 依頼ボード(24-27) → ダンジョン(28-30) → NPC(31-33) → 管理/報酬(34-35) → 統合/テスト(36)。
- 各ステップが「コード変更」と「テストアサーション」に対応するよう設計。

### M5. テスト戦略の定義
- `tests/test_procedural_quest_generation_36_steps.py` を作成し、各ステップを番号付きアサーションで検証。
- 決定論（同一シード→同一クエスト）と組み合わせ爆発（最低 1000 通り超の一意性）を数値で証明。

### M6. 実装順序の定義
- 計画書のステップ順にコードを作成。各ステップ完了ごとに該当テストを実行し、緑になることを確認。

---

## 2. 作成する成果物
1. `plans/procedural_quest_generation_proposal.md`（9つの提案）← 完了
2. `plans/procedural_quest_generation_meta_plan.md`（本ファイル）
3. `plans/procedural_quest_generation_implementation_plan.md`（36ステップ詳細計画、約1万字）
4. `data/procedural_scenarios.yaml`（quest_generation 拡張）
5. `procedural_quest_generator.py`（新規モジュール）
6. `components.py` / `entity.py` / `game.py` / `save_system.py`（統合）
7. `tests/test_procedural_quest_generation_36_steps.py`（検証）

## 3. 完了基準
- 36ステップの実装計画書が作成され、実装がその順序で完了していること。
- `pytest tests/test_procedural_quest_generation_36_steps.py` が全ステップ成功すること。
- 3経路いずれもクエストが生成され、決定論・組み合わせ爆発が証明されていること。
