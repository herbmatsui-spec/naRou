# プロシージャル・クエスト生成システム 強化版 実装計画書作成のための計画（メタ計画）

本ドキュメントは、前フェーズで構築したプロシージャル・クエスト生成システムに対する
「3つの強化提案」の実装計画書をどの手順で作成し、その後どの順序で実装するかを定義する。
対象の3提案：①表示名の日本語ローカライズマップ ②連鎖クエスト（報酬カスケード）の自動生成 ③既存UI（journal_ui/ログブック）への統合表示。

---

## 1. 計画作成の手順（メタステップ）

### M1. 要件の再定義
- 検証で判明した課題（敵/アイテムの英語IDがそのまま表示される）を解消する日本語化を最優先項とする。
- 連鎖クエストによりリプレイ性・長期ログイン誘引をさらに強化する。
- 生成クエストを既存の冒険日誌UIに表示し、追跡可能性を確保する。

### M2. 既存コード調査（事実ベース）
- `procedural_quest_generator.py`：_compose のテンプレート置換、`GeneratedQuest` 構造、manager の complete_quest フロー。
- `data/procedural_scenarios.yaml`：quest_generation セクションの拡張方法。
- `journal_ui.py`：render() が main_quest_system のみを描画している前提を確認（生成クエスト用セクション追加が必要）。
- `components.py` / `entity.py` / `save_system.py`：連鎖状態の永続化拡張点を確認。

### M3. データ・拡張スキーマ設計
- YAML：`display_names`（enemy/item/stage/difficulty の日英対応）、`chain_config`（max_depth/escalation）。
- Python：`GeneratedQuest` へ chain 情報、`QuestObjectiveSpec` へ cascade_bonus。

### M4. 36ステップへの分割
- 事前設計(1-4) → 日本語化(5-12) → 連鎖クエスト(13-26) → UI統合(27-34) → 統合テスト(35-36)。
- 各ステップが「コード変更」と「テストアサーション」に対応。

### M5. テスト戦略
- `tests/test_procedural_quest_enhancement_36_steps.py` を作成。
- 日本語化：生成タイトルに英語IDが含まれないこと。
- 連鎖：完了→次生成→再完了のループと決定論。
- UI：render が生成クエストを描画すること（モックコンソール）。

### M6. 実装順序
- 計画書ステップ順に実装し、各フェーズ終了ごとに関連テストを実行して緑を維持。

---

## 2. 作成する成果物
1. `plans/procedural_quest_enhancement_meta_plan.md`（本ファイル）
2. `plans/procedural_quest_enhancement_implementation_plan.md`（36ステップ詳細計画、約1万字）
3. 実装: `data/procedural_scenarios.yaml` 拡張 / `procedural_quest_generator.py` 拡張 / `journal_ui.py` 拡張 / `components.py` 拡張
4. `tests/test_procedural_quest_enhancement_36_steps.py`

## 3. 完了基準
- 36ステップの実装計画書が作成され、実装がその順序で完了すること。
- `pytest tests/test_procedural_quest_enhancement_36_steps.py` が全ステップ成功すること。
- 3提案いずれも動作し、日本語化・連鎖・UI表示が証明されること。
