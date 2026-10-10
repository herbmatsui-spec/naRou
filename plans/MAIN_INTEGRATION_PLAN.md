# main ブランチ統合計画 — feature/design-v2-impl → origin/main

**作成日**: 2026-10-10
**状態**: 統合判断待ち (成果は feature ブランチに確保済み)

---

## 1. 現状 (実測)

| ブランチ | 最新コミット | 日付 | 内容 |
|---------|-------------|------|------|
| `feature/design-v2-impl` (ローカル=リモート) | `c5f3c11` | 2026-10-10 | GAME_DESIGN_V2 計画完了 (230 passed / xfail 0) |
| `origin/main` | `3fbfb44` | 2026-08-24 | PR #8 `refactor/split-large-files` のマージ |

- **共通祖先**: `5430a45` (2026-08-22)
- **リモート main は 1.5ヶ月古い**: 8/24 以降リモートへは何も push されていない
- **ローカル側の 38 コミット (9月〜10月) はリモートへ未反映**

---

## 2. 競合の性質 (構造的)

リモートの PR #8 (auto-commit author, 8/24) は**大規模な物理レイアウト変更**:

| 変更 | 規模 |
|------|------|
| 498ファイルをルート → `naRou/` 物理ディレクトリへ移動 | +93,088行 |
| `engine/engine.py` (2630行) / `systems.py` (628行) を**削除して分割** | -5,545行 (7ファイル) |
| `pyproject.toml`: 依存を tcod+Pillow の2つに縮小、version 1.0.5 | — |

ローカル側 (我々の 38 コミット) は**フラットレイアウトのまま** 1.5ヶ月分の機能実装:

- Phase 1: 死・終局・進行・経済 (`engine/game_state.py`, `config.py` 修正等)
- Phase 2: AP制戦闘・射程攻撃・背後攻撃・8呪文・敵能力15id・void_boss
- Phase 3: 接尾辞23種・鑑定・呪い・英語140キー・プレースホルダ全置換
- **230テスト**が全て緑 (フラットレイアウト前提)

**競合 ~100ファイル**: リモートの「分割+移動」とローカルの「同一ファイルへの機能追記」が衝突。
単純なマージ解決では、リモートの分割モジュールに我々の変更を移植する作業 (実質リライト) が発生する。

---

## 3. 統合方針の選択肢

### 案 A: feature を統合ベースにする (推奨)
1. `feature/design-v2-impl` → main への **PR を作成** (リモート main を上書きする force push ではなく PR 経由)
2. PR のマージ時、リモート側の分割 refactor は「マージで解決」:
   - 我々の変更 (新機能・テスト・データ) を残す
   - リモートの 8/24 分割は、`git merge -X ours` 相当で**構造的に放棄** (後日、分割をやり直す)
3. ただし **PR #8 の意図 (巨大ファイルの分割) は正当** — 分割は別 feature として改めて実施する

### 案 B: リモート構造に我々の機能を移植 (大工事)
- 498ファイルの新レイアウトに Phase 2/3 の実装を移植し直す
- 移植コスト: engine.py への ~50箇所の変更を分割後モジュールへ再配置、テスト import パス修正等
- **リスク**: 高い。230テストの前提 (フラット import) を崩す

### 案 C: force push (非推奨)
- PR #8 の 8 コミットが失われる
- **ただし**: 共通祖先は同じ (5430a45) で、リモート側に我々が失うべき独自機能は
  Husk Puppet Hacking / Meta Scenario Intervention の2機能のみ (67a2a97)。
  これらが不要と判断されるなら実行可能。

---

## 4. 推奨フロー

```
1. [実施済み] feature/design-v2-impl をリモートに push → 成果確保
2. [次] GitHub で feature/design-v2-impl → main の PR を作成
   (PR 本文に本計画書の §2-3 を要約して競合の性質を明示)
3. [判断] PR #8 の2機能 (Husk Puppet Hacking / Meta Scenario Intervention) が
   必要か不要かを確認:
   - 不要 → 案A でマージ (リモート分割は放棄、分割は別 feature で再実施)
   - 必要 → 案B で移植、または該当機能だけ cherry-pick 相当で再実装
4. [完了後] main をリモートへ push (fast-forward になる)
```

---

## 5. 検証方法 (統合後)

```bash
# コアスイートが緑であること (統合の受け入れ基準)
pytest tests/test_player_death.py tests/test_win_condition.py tests/test_ap_system.py \
       tests/test_ranged_attack.py tests/test_backstab.py tests/test_spells.py \
       tests/test_intent_truthfulness.py tests/test_affix_system.py tests/test_i18n.py
# → 230 passed / xfail 0 であること

# GAME_DESIGN_V2 の完了定義表の再確認
# plans/GAME_DESIGN_V2_RESULT.md §完了の定義チェックリスト
```
