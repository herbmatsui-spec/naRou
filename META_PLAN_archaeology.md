# メタ計画書: 「考古学・発掘・解読」メタゲーム 詳細36ステップ実装計画の作成プロセス

## 1. 目的
`memory_fragments.yaml`（記憶の欠片）と `story_endings.yaml`（ストーリーエンディング）を連携させ、
「断片収集 → 解読 → 真実到達 → 解釈によるエンディング分岐」という考古学ループを実装するための
詳細36ステップ計画書を作成する。さらに、単なるクリアから「謎解き・考察」へ引き上げるための
コミュニティ議論・二次創作喚起策を9件提案する。

## 2. なぜ「計画の計画」が必要か
- 既存資産（ECS `SystemManager` / `BaseSystem` / `components.py` の dataclass コンポーネント /
  `save_system.py` のスキーマ / `DataManager` の YAML 読み込み）の約束事を守るため。
- 既存テスト（`test_dungeon_world_storyteller_72_steps.py` の Step13-16）が参照する
  `memory_fragments.yaml` / `story_endings.yaml` の構造を壊さないため。
- 36ステップという粒度で「何を・どの順で・誰が」実装するかを事前合意し、手戻りを防ぐため。

## 3. 計画書作成のフェーズ分割（36ステップの原案）

### フェーズA: 分析と設計（ステップ1-5）
- 既存2 YAML の構造把握と考古学ループのモデル化
- 拡張スキーマ（glyph_script / decoder_key / truth_codex）の定義
- 統合ポイント（components / game / save / journal_ui）の洗い出し
- 成功基準とテスト戦略の策定
- 作業 TODO と進捗管理方法の決定

### フェーズB: データ層（ステップ6-14）
- `memory_fragments.yaml` の拡張（既存互換 + 新規断片3件）
- `data/archaeology_sites.yaml`（発掘遺跡・深度・ドロップ）
- `data/decoder_keys.yaml`（言語族と鍵の獲得）
- `data/truth_codex.yaml`（解読済断片集合 → 真理 → 候補エンディング）
- `ArchaeologyComponent` の追加と entity / save 連携
- YAML 読み込み検証テスト

### フェーズC: システムコア（ステップ15-24）
- `archaeology_system.py` の骨格（4 YAML を統合する Registry）
- 発掘→収集→解読→真理到達→解釈分岐の各ロジック
- メタ進行・実績・エンディング解放条件への接続
- システム単体テスト

### フェーズD: 統合（ステップ25-30）
- `game.py` への登録、発掘アクション入力フック、遺跡マーカ描画
- 考古学ジャーナルパネル、ログ・効果音

### フェーズE: コミュニティ・二次創作（ステップ31-33）
- 9件の提案をまとめた設計ドキュメント
- 解釈台帳（interpretation ledger）の保存・出力
- 共有用サマリー（テキスト/Markdown）出力

### フェーズF: 検証と仕上げ（ステップ34-36）
- 36ステップ検証テストの作成と pytest 実行
- バランス・後方互換の確認と修正
- 実装サマリーの作成

## 4. 成果物
- `META_PLAN_archaeology.md`（本ファイル：計画作成の計画）
- `DETAILED_IMPLEMENTATION_PLAN_archaeology.md`（詳細36ステップ計画書、9提案含む、約1万字）
- 計画に従い実装されたコード・データ・テスト

## 5. 品質基準
- 各ステップは具体的かつ実行可能（ファイル・関数・コマンドが明示）
- ステップ間の依存関係が明確
- 既存 YAML スキーマとの後方互換を維持
- 日本語、読みやすい見出し構造
- 実装後、pytest が全て通ること
