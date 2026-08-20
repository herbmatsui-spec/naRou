# 実装計画書：Aの世界変更のコミット・プッシュ

- **計画ID**: PLAN_COMMIT_PUSH
- **作成日**: 2026-08-20
- **目的**: 本セッションで行った「Aの世界（スキル喰い）」関連の変更のみを安全にコミットし、リモートへプッシュする
- **前提となる制約**: 作業ツリーは「未解決競合 67件」＋「無関係変更 500+件」の混在状態（セッション開始前からの未完了マージ痕跡）

---

## 0. 現状の要約（再確認）
- `git status -s` で **543ファイル** が変更中含み、うち **67件が unmerged（AA/UU 等）**。
- 本セッションの変更は **約20ファイル** のみ（下記「対象ファイル」）。残りは全て無関係な別作業。
- `.git/MERGE_HEAD` は不在だが unmerged エントリが残っており、そのままでは `git commit` が拒否される。

## 1. ゴール
- unmerged ブロックを最小解決し、コミットを可能にする。
- **本セッションの対象ファイルのみ**をコミット（他500+件の変更はステージ/ワーキングに残したまま、コミット・プッシュ対象にしない）。
- `origin/main` への fast-forward プッシュ。

## 2. 対象ファイル（本セッションの変更のみ）
### 設計ドキュメント（docs/world_a/）
- `docs/world_a/DESIGN_A_SKILL_EATER.md`（編集：正規仕様注記・§2.7/§2.8/§3.2/§6 追加）
- `docs/world_a/DESIGN_A_IMPLEMENTATION_PHASES.md`（改名移動 docs/ → docs/world_a/）
- `docs/world_a/DESIGN_A_IMPLEMENTATION_PHASES_PT2.md`
- `docs/world_a/DESIGN_A_IMPLEMENTATION_PHASES_PT3.md`
- `docs/world_a/DESIGN_A_NPC_DIALOGUES.md`
- `docs/world_a/DESIGN_A_QUESTS.md`
- `docs/world_a/DESIGN_A_SKILLS.md`
- `docs/world_a/GAP_03_mapping.md`（新規：§2 マッピング実態ギャップリスト）
- `docs/world_a/INDEX.md`（新規：フォルダ目次）
- `docs/world_a/PLAN_01_data_path_unification.md`（新規）
- `docs/world_a/PLAN_02_design_hierarchy.md`（新規）
- `docs/world_a/PLAN_03_mapping_gap.md`（新規）
- `docs/world_a/PLAN_06_test_traceability.md`（新規）
- `docs/world_a/PLAN_ADD_exploration_doc.md`（新規）
- `docs/world_a/PLAN_NEW9_1_test_path.md`（新規）
- `docs/world_a/PLAN_NEW9_2_devour_rate.md`（新規）
- `docs/world_a/TRACEABILITY_06_tests.md`（新規）
- `docs/world_a/reference_multiverse_W4.md`（新規）

### 実装（ソース）
- `skill_eater_combat_system.py`（喰らい base_rate 0.20 → 0.60）
- `skill_eater_audio_system.py`（AUDIO_DIR の Windows 絶対パス → `assets/audio`）
- `skill_eater_presentation_system.py`（EMOTE_DIR の Windows 絶対パス → `assets/emote/pixel/style1`）

### テスト（パス置換: `e:/narou2/...` → `Path(__file__).parents[1] / "data/worlds/skill_eater/skills.yaml"`）
- `tests/test_skill_eater_phase1.py`
- `tests/test_skill_eater_phase2.py`
- `tests/test_skill_eater_phase3.py`
- `tests/test_skill_eater_phase4_5.py`
- `tests/test_skill_eater_phase6_7_8.py`
- `tests/test_skill_eater_full_72_steps.py`
- `tests/test_skill_eater_presentation_integration.py`
- `tests/test_skill_eater_audio_integration.py`

## 3. 実装手順（ステップ）

### Step 1 — unmerged の解決（最小）
- `git add -A` を実行。**目的**: 67件の unmerged エントリを「作業ツリー版を保持」で解決し、コミット可能状態にする。
  - `AA`（both added）は内容競合なし → 作業ツリー版で解決（安全）。
  - 本操作はインデックス操作のみ。ワーキングツリーの実ファイル内容は変更されない（非破壊）。

### Step 2 — 対象ファイルの確実なステージ
- 対象ファイルを明示的に `git add <list>` でステージ（作業ツリーの変更が確実にインデックスに乗るよう确保）。
  - 既に staged のもの（改名済み docs 等）も再 add で問題なし。

### Step 3 — 対象ファイルのみをコミット（部分コミット）
- `git commit -- <対象ファイルリスト>` を実行。
  - `git commit -- <pathspec>` は指定パスのみをコミットし、それ以外の staged エントリ（無関係500+件）はコミットされずステージに残る → **無関係変更を含めない**。

### Step 4 — プッシュ
- `git push origin main` を実行（fast-forward 想定: ローカル main は origin/main と同一コミットからの1コミット先行）。

### Step 5 — 検証
- `git status` で unmerged が 0 になったこと、かつ無関係ファイルが「未コミット（ステージ/未ステージ）のまま」であることを確認。
- `git log --oneline -3` で対象コミットが上空にあることを確認。

## 4. コミットメッセージ（案）
```
docs(world_a): Aの世界の設計文書整理とテスト/実装のパス・数値修正

- docs/world_a/ にAの世界設計を集約（INDEX/GAP/トレーサビリティ/計画書）
- 設計階層の正規仕様化（DESIGN_Aをworld bibleと明記）
- 探索システムの設計本文追記（§2.8/§3.2）
- テストの Windows 絶対パス(e:/narou2)を cwd 非依存パスへ修正（8ファイル）
- 喰らい成功率 base_rate 0.20→0.60（設計値60%と整合）
- AUDIO_DIR/EMOTE_DIR の Windows 絶対パスを実体(assets/)へ修正
```

## 5. リスクと対策
- **unmerged 解決時の意図しない内容混入**: `AA` のみで内容競合なし。`git add -A` 後も `git commit -- <対象のみ>` とするため、無関係ファイルはコミットに入らない。
- **無関係変更の誤コミット**: 部分コミット（`git commit -- <paths>`）により防止。
- **プッシュ時の競合**: 事前確認で local/main == origin/main ベース。fast-forward となる。
- **ワーキングツリー破壊**: 一切の `git reset --hard` / `git checkout` / `git clean` は使用しない。

## 6. 影響範囲
- コミットされるのは上記対象ファイルのみ。
- リポジトリ全体の他の変更（core/・tools/・webgl/・data/generated/ 等）は一切コミット・プッシュされない（ローカルにそのまま残る）。
