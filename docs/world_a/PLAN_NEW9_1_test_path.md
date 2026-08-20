# 実装計画書：新9提案 #1 — テストのハードコードパス修正

- **計画ID**: PLAN_NEW9_1
- **対象**: 改善提案 第2弾 の #1（テストのハードコードパス修正）
- **作成日**: 2026-08-20
- **ステップ範囲**: 本ドキュメントは **1〜72 ステップのうち ステップ 1〜36** を担当（続きは PLAN_NEW9_2: ステップ 37〜72）
- **スコープ**: 8テストファイルの `yaml_path = Path("e:/narou2/data/worlds/skill_eater/skills.yaml")` を cwd 非依存の `Path(__file__).parents[1] / "data/worlds/skill_eater/skills.yaml"` に置換する

---

## 目標
Windows 絶対パス `e:/narou2/...` を除去し、Linux/Mac/CI でも `data/worlds/skill_eater/skills.yaml` を正しくロードできるようにする。

## 前提（確認済み事実）
- 該当行は 8ファイルに各1件、計8件（`grep -rn "e:/narou2" tests/*.py` で確認済み）。
- 全8ファイルで `from pathlib import Path` は既にインポート済み → `Path(__file__)` が使用可能。
- `__file__` はテストファイルの絶対パス。`parents[1]` は `tests/` の1つ上＝リポジトリルート `/home/herbmatsui/naRou`。
  - よって `Path(__file__).parents[1] / "data/worlds/skill_eater/skills.yaml"` は正しく実体を指す。

## 置換ルール（全ファイル共通）
- **OLD**: `Path("e:/narou2/data/worlds/skill_eater/skills.yaml")`
- **NEW**: `Path(__file__).parents[1] / "data/worlds/skill_eater/skills.yaml"`

---

## ステップ 1〜36（本ドキュメント担当分）

### 準備・調査（ステップ 1〜6）
1. **bash**: `cd /home/herbmatsui/naRou` を実行し、作業ディレクトリをリポジトリルートに移動する。
2. **bash**: `grep -rn "e:/narou2" tests/*.py` を実行し、該当が8ファイル・各1行であることを目視確認する。
3. **bash**: `for f in tests/test_skill_eater_*.py; do echo "$f $(grep -c e:/narou2 "$f")"; done` を実行し、全ファイルで出現回数が `1` であることを確認する。
4. **決定**: 置換後の文字列を `Path(__file__).parents[1] / "data/worlds/skill_eater/skills.yaml"` と決定する（このステップは思考ステップ）。
5. **bash**: `grep -n "from pathlib import Path" tests/test_skill_eater_phase1.py` を実行し、`Path` のインポートが存在することを確認する（他7件も同様だが既知のため省略可）。
6. **方針決定**: 各ファイルは edit ツールで置換し、編集ごとにそのファイルのみ `grep -c "e:/narou2"` で0件化を確認する方針を決める（思考ステップ）。

### 各ファイルの置換（ステップ 7〜22）
7. **edit**: `tests/test_skill_eater_phase1.py` を開き、行内の `Path("e:/narou2/data/worlds/skill_eater/skills.yaml")` を `Path(__file__).parents[1] / "data/worlds/skill_eater/skills.yaml"` に置換する（ファイル内の全出現を置換）。
8. **bash**: `grep -c "e:/narou2" tests/test_skill_eater_phase1.py` を実行し、結果が `0` であることを確認する。
9. **edit**: `tests/test_skill_eater_phase2.py` を同様に置換する。
10. **bash**: `grep -c "e:/narou2" tests/test_skill_eater_phase2.py` → `0` を確認する。
11. **edit**: `tests/test_skill_eater_phase3.py` を同様に置換する。
12. **bash**: `grep -c "e:/narou2" tests/test_skill_eater_phase3.py` → `0` を確認する。
13. **edit**: `tests/test_skill_eater_phase4_5.py` を同様に置換する。
14. **bash**: `grep -c "e:/narou2" tests/test_skill_eater_phase4_5.py` → `0` を確認する。
15. **edit**: `tests/test_skill_eater_phase6_7_8.py` を同様に置換する。
16. **bash**: `grep -c "e:/narou2" tests/test_skill_eater_phase6_7_8.py` → `0` を確認する。
17. **edit**: `tests/test_skill_eater_full_72_steps.py` を同様に置換する。
18. **bash**: `grep -c "e:/narou2" tests/test_skill_eater_full_72_steps.py` → `0` を確認する。
19. **edit**: `tests/test_skill_eater_presentation_integration.py` を同様に置換する。
20. **bash**: `grep -c "e:/narou2" tests/test_skill_eater_presentation_integration.py` → `0` を確認する。
21. **edit**: `tests/test_skill_eater_audio_integration.py` を同様に置換する。
22. **bash**: `grep -c "e:/narou2" tests/test_skill_eater_audio_integration.py` → `0` を確認する。

### 一括検証・テスト実行（ステップ 23〜36）
23. **bash**: `grep -rn "e:/narou2" tests/*.py` を実行し、出力が空（0件）であることを確認する。
24. **bash**: `python -m unittest tests.test_skill_eater_phase1 -v` を実行する。
25. **確認**: 出力に `OK` または `passed` があり、エラー（Error/Fail）がないことを確認する。
26. **bash**: `python -m unittest tests.test_skill_eater_phase2 -v` を実行する。
27. **確認**: 出力に `OK` があり、エラーがないことを確認する。
28. **bash**: `python -m unittest tests.test_skill_eater_phase3 -v` を実行する。
29. **確認**: 出力に `OK` があり、エラーがないことを確認する。
30. **bash**: `python -m unittest tests.test_skill_eater_phase4_5 -v` を実行する。
31. **確認**: 出力に `OK` があり、エラーがないことを確認する。
32. **bash**: `python -m unittest tests.test_skill_eater_phase6_7_8 -v` を実行する。
33. **確認**: 出力に `OK` があり、エラーがないことを確認する。
34. **bash**: `python -m unittest tests.test_skill_eater_full_72_steps -v` を実行する。
35. **bash**: `python -m unittest tests.test_skill_eater_presentation_integration -v` および `python -m unittest tests.test_skill_eater_audio_integration -v` を実行する。
36. **確認**: 全8テストファイルがエラーなく通過したことを確認し、**bash**: `git diff --stat` で変更が各ファイル1行ずつ（計8行）であることをレビューする。

---

## 受け入れ基準
1. `grep -rn "e:/narou2" tests/*.py` の結果が空（0件）である。
2. 全8テストファイルが `python -m unittest` でエラーなく通過する。
3. `git diff` で変更行が各ファイル1行（パス文字列のみ）である。

## 影響範囲・リスク
- **影響**: テストファイル8件のみ。ゲームコード・設計ドキュメントには変更なし。
- **リスク**: 极低。`__file__` ベースの解決は cwd に依存せず、Windows でも `Path` が正規化するため安全。
- **注意**: `tests/__pycache__/*.pyc` に古いパスが残る場合があるが、実行時には `.py` から再生成される。必要なら `find tests -name "__pycache__" -type d -exec rm -rf {} +` で削除可（任意）。

## 関連
- 続きのステップ 37〜72 は `PLAN_NEW9_2_devour_rate.md`（新9提案 #2）を参照。
