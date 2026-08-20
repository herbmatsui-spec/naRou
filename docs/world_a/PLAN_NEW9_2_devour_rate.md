# 実装計画書：新9提案 #2 — 喰らい成功率式の実装・設計不一致修正

- **計画ID**: PLAN_NEW9_2
- **対象**: 改善提案 第2弾 の #2（喰らい成功率式の実装・設計不一致）
- **作成日**: 2026-08-20
- **ステップ範囲**: 本ドキュメントは **1〜72 ステップのうち ステップ 37〜72** を担当（前半は PLAN_NEW9_1: ステップ 1〜36）
- **スコープ**: `skill_eater_combat_system.py` の `calculate_devour_rate` 内 `base_rate = 0.20` を `base_rate = 0.60` に変更し、設計（DESIGN_A §3.1: base 60%、NAROU W4: base_success 0.6）と一致させる

---

## 目標
実装の喰らい基礎成功率を `0.20`（設計の1/3）から `0.60`（設計値）に修正し、「喰らいを中核とする」という設計意図どおりのバランスにする。

## 前提（確認済み事実）
- `skill_eater_combat_system.py:94` に `base_rate = 0.20` が存在（関数 `calculate_devour_rate` 内、91行付近）。
- 他の項目は設計と一致: `analysis_bonus = analyzer.analysis_level * 0.05`、`hp_bonus = (1 - hp/max_hp) * 0.50`、状態異常ボーナス `+0.20`（Paralyzed/Sleep）。
- テスト `tests/test_skill_eater_phase2.py` の `test_devour_success_flow` / `test_devour_failure_backlash` は `execute_devour(..., force_success=True/False)` を明示的に渡しており、**乱数に依存しない（決定論的）**。そのため `base_rate` 変更はテストを壊さない。

## 置換ルール
- **OLD**: `base_rate = 0.20`
- **NEW**: `base_rate = 0.60`

---

## ステップ 37〜72（本ドキュメント担当分）

### 準備・調査（ステップ 37〜48）
37. **bash**: `cd /home/herbmatsui/naRou` を実行し、リポジトリルートに移動する。
38. **read/edit**: `skill_eater_combat_system.py` を開く。
39. **bash**: `grep -n "def calculate_devour_rate" skill_eater_combat_system.py` を実行し、関数の開始行（91付近）を特定する。
40. **read**: 該当関数の全文（91〜104行）を読み、`base_rate = 0.20` の行を確認する。
41. **read**: `docs/world_a/DESIGN_A_SKILL_EATER.md` の §3.1 devour にある `success_rate_formula: "base(60%) + (analysis_level * 5%) + (target_hp_percent_missing * 0.5)"` を確認する。
42. **read**: `NAROU_9_WORLDS_DESIGN.md` の W4 `devour: base_success: 0.6` を確認する。
43. **判定**: 実装 `0.20` と設計 `0.60` を比較し、1/3 で厳しすぎると断定する（思考ステップ）。
44. **方針決定**: `base_rate = 0.20` のみを `0.60` に変更し、他のボーナス項（analysis/hp/状態）は設計と一致するため維持する（思考ステップ）。
45. **edit**: `skill_eater_combat_system.py` の `base_rate = 0.20` を `base_rate = 0.60` に置換する。
46. **bash**: `grep -n "base_rate = 0.60" skill_eater_combat_system.py` を実行し、変更された行が現れたことを確認する。
47. **bash**: `grep -n "base_rate = 0.20" skill_eater_combat_system.py` を実行し、結果が0件（残っていない）であることを確認する。
48. **read**: `calculate_devour_rate` の全文を再読し、他の行（analysis_bonus/hp_bonus/状態ボーナス/clamp）がそのままであることを確認する。

### 計算式の手計算検証（ステップ 49〜54）
49. **計算**: 例1 `analysis_level=0, hp満タン(欠損0), 通常` → `0.60 + 0 + 0 = 0.60`。
50. **計算**: 例2 `analysis_level=5, hp欠損0.5, 通常` → `0.60 + 0.25 + 0.25 = 1.10` → clamp で `0.95`。
51. **計算**: 例3 `analysis_level=1, hp満タン, Paralyzed` → `0.60 + 0.05 + 0 + 0.20 = 0.85`。
52. **計算**: 例4 `analysis_level=0, hp満タン, 通常` → `0.60`（clamp `min(0.95,...)` で 0.60 維持）。
53. **確認**: 上記が `max(0.05, min(0.95, round(total, 2)))` で正しく収まることを目視確認する。
54. **確認**: 設計意図（序盤でも base 60% で喰らせる）との整合を確認する（思考ステップ）。

### テスト実行・検証（ステップ 55〜61）
55. **read**: `tests/test_skill_eater_phase2.py` の `test_devour_success_flow` / `test_devour_failure_backlash` が `force_success` 引数を使っていることを確認し、乱数非依存であることを再確認する。
56. **bash**: `python -m unittest tests.test_skill_eater_phase2 -v` を実行する。
57. **確認**: 出力で `test_devour_success_flow` と `test_devour_failure_backlash` が `passed` / `ok` であることを確認する。
58. **bash**: `python -m unittest tests.test_skill_eater_phase1 -v` を実行する（`analyze_target` が `devour_success_rate` を表示するため影響を確認）。
59. **確認**: エラーがないことを確認する。
60. **bash**: `python -m unittest discover tests "test_skill_eater_*.py"` を実行し、全 skill_eater テストを一括実行する。
61. **確認**: 全テストが `passed` / `OK` であることを確認する。

### 文書整合・最終確認（ステップ 62〜72）
62. **read**: `docs/world_a/DESIGN_A_SKILL_EATER.md` §3.1 の devour 記述が既に `base(60%)` で記載されており、本変更で整合している（更新不要）ことを確認する。
63. **read**: `NAROU_9_WORLDS_DESIGN.md` W4 の `base_success: 0.6` が既に一致していることを確認する。
64. **read**: `docs/world_a/TRACEABILITY_06_tests.md` の喰らい行が `✅` であることを確認する（この変更でステータス不変）。
65. **任意/edit**: `docs/world_a/GAP_03_mapping.md` 等に「実装値(0.60) = 設計値(60%) で整合済」の注記を追記する（必要な場合のみ）。
66. **bash**: `git diff skill_eater_combat_system.py` を実行し、変更が `base_rate = 0.20` → `0.60` の1行のみであることを確認する。
67. **bash**: `grep -rn "0\.20" skill_eater_combat_system.py` を実行し、別箇所に意図せぬ `0.20` ハードコードがないか確認する。
68. **read**: `analyze_target` 内で `devour_success_rate=devour_rate` として表示される箇所があり、新しい 0.60 ベースの値が反映されることをコードで確認する。
69. **冪等性確認**: 再び `base_rate = 0.60` への置換を試みても差分が出ない（既に 0.60）ことを確認する（思考ステップ）。
70. **bash**: `python -c "import skill_eater_combat_system"` を実行し、インポートエラーがないことを確認する。
71. **bash**: 手順60の全テスト再実行結果が緑（passed）であることを最終確認する（手順60で済んでいれば省略可）。
72. **完了**: 提案2実装済みを宣言。実装 `base_rate=0.60` が設計（60% / 0.6）と一致したことを報告する。

---

## 受け入れ基準
1. `skill_eater_combat_system.py` で `base_rate = 0.60` となっている（`base_rate = 0.20` は存在しない）。
2. 手計算で base のみが 0.60 になり、他ボーナス項は維持されている。
3. 全 skill_eater テストが `python -m unittest discover tests "test_skill_eater_*.py"` で通過する。
4. `git diff` で変更は `base_rate` の1行のみ。

## 影響範囲・リスク
- **影響**: `skill_eater_combat_system.py` の1行のみ。テスト・設計ドキュメント・データには変更なし。
- **リスク**: 低。テストは `force_success` 決定論のため壊れない。実装値が設計値に収束するだけ。
- **注意**: バランス変更により「喰らい」が全体的に易しくなる。ゲーム全体の難易度が気になる場合は、代わりに `analysis_level` ボーナス係数の調整を検討（本計画外）。

## 関連
- 前半のステップ 1〜36 は `PLAN_NEW9_1_test_path.md`（新9提案 #1）を参照。
