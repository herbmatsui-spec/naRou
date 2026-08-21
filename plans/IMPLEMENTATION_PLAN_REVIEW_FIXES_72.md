# 実装計画書：コードレビュー指摘の修正（72ステップ）

## 概要

コードレビュー（2026-08-20）で発見した問題を、低性能な LLM でも 1 ステップずつ確実に実装できるよう
**72 の小さなステップ**に分解した計画です。各ステップは「編集するファイル」「変更内容（before/after）」
「検証コマンド」のみで完結します。ステップ間に依存は最小限で、どのステップも単独で取り消し可能です。

### 対象となる指摘（元レビューより）
1. **重大バグ**：`monitoring_management.py` で未定義変数 `monitor_dir` により `NameError` が発生する。
2. **デッドコード（no-op）**：lint 過剰適用により「代入だけを削った結果を捨てる文」が多数残っている。
3. **例外の丸め吞み**：`except Exception:` が 92 件、意図的フォールバックだったものが黙殺されている。
4. **lint 債務**：`ruff --select F,B,E9` で約 220 件（F401/F841/B007 等、多くは自動修正可）。

### 進め方のルール（weak-LLM 向け）
- 各ステップは **1 ファイル・1 編集** を基本とする。複数行でも「同じ意図の削除」なら 1 ステップ。
- 編集前に必ず対象ファイルを `read` すること（行番号はずれる可能性があるため、内容（snippet）で特定する）。
- 各行の no-op は「代入のない単独文」である。同じメソッドの他の使用は **絶対に触らない**。
- 削除すると意図が分からなくなる箇所は、行を削除せず `# TODO: <本来の意図>` コメント化する。
- 各ステップ末尾の「検証」を必ず実行し、失敗したらそのステップだけ戻して報告する。

---

## PHASE 0 — 準備（ステップ 1–4）

### Step 1. 作業ブランチの作成
- 操作：`git checkout -b fix/review-cleanup`
- 検証：`git branch --show-current` → `fix/review-cleanup`

### Step 2. ruff の確認
- 操作：`python3 -m ruff --version`
- 検証：バージョンが表示されること（0.16.x 等）。未導入なら `pip install ruff` は行わず報告。

### Step 3. 現状ベースラインの保存
- 操作：`python3 -m ruff check . --select F,B,E9 --output-format concise > /tmp/ruff_baseline.txt 2>/dev/null; wc -l /tmp/ruff_baseline.txt`
- 検証：行数が記録されること（後のステップで減少を確認するため）。

### Step 4. テスト収集の確認
- 操作：`python3 -m pytest --collect-only -q 2>&1 | tail -3`
- 検証：`429 tests collected` と表示されること。

---

## PHASE 1 — 重大バグ修正（ステップ 5–8）

### Step 5. `monitoring_management.py`：`__init__` で `monitor_dir` を保存
- ファイル：`monitoring_management.py`
- 対象：`class MonitoringManager:` の `__init__(self, monitor_dir="monitoring_management"):`
- before：
  ```python
  def __init__(self, monitor_dir="monitoring_management"):
      self._setup_prometheus()
  ```
- after：
  ```python
  def __init__(self, monitor_dir="monitoring_management"):
      self.monitor_dir = Path(monitor_dir)
      self._setup_prometheus()
  ```
- 検証：`python3 -c "import monitoring_management; monitoring_management.MonitoringManager()"`

### Step 6. `monitoring_management.py`：メソッド内の未定義参照を削除
- ファイル：`monitoring_management.py`
- 対象：`_setup_prometheus` 内の `self.monitor_dir = Path(monitor_dir)`
- before：`self.monitor_dir = Path(monitor_dir)` （`monitor_dir` はここでは未定義）
- after：この行を **削除**（Step 5 で `self.monitor_dir` は既に設定済み）。
- 検証：Step 5 と同じ import テストが `NameError` にならないこと。

### Step 7. インポート確認
- 操作：`python3 -c "import monitoring_management; m=monitoring_management.MonitoringManager(); print(m.monitor_dir)"`
- 検証：`monitoring_management` と表示されること。

### Step 8. コミット（重大修正）
- 操作：`git add monitoring_management.py && git commit -m "fix: MonitoringManager の未定義 monitor_dir を修正"`
- 検証：`git log --oneline -1` に該当コミットがあること。

---

## PHASE 2 — デッドコード（no-op）の除去（ステップ 9–34）

> 各ステップ：対象ファイルを開き、その「単独文（代入なし）」の行を削除、または TODO 化する。
> 検証は「`python3 -m ruff check <ファイル> --select B018` で該当行が消える」こと。

### Step 9. `world_layer.py`
- 対象：`# ここで難易度に基づくトラップ配置等を行う` の直前の `self.theme_data.get("difficulty_modifier", 1.0)`
- 変更：行を削除し、代わりに `# TODO: difficulty_modifier をトラップ配置へ適用する` を残す。

### Step 10. `world_map_manager.py`
- 対象：単独行 `time.time()`（`_unload_least_recently_used_layer` 内）
- 変更：行を削除（以降 `current_time` は使用されていないため）。

### Step 11. `ui_fx_systems.py`
- 対象：グリッチ処理内の単独読出 `console.ch[gx, gy]`
- 変更：行を削除（次の `console.ch[gx, gy] = ...` に値を渡すだけなので不要）。

### Step 12. `main_quest_system.py`
- 対象：`ws_manager.get_phase().name` の単独行
- 変更：行を削除（または `# TODO: フェーズ名をログ/UI に使用` を残す）。

### Step 13. `validate_tileset_def.py`
- 対象：`meta_h * directions` の単独行
- 変更：行を削除（`expected_h` は未使用だったため）。

### Step 14. `ui_title_display.py`
- 対象：単独行 `getattr(player, "id", str(id(player)))`
- 変更：行を削除（戻り値を使っていない）。

### Step 15. `core/difficulty.py`
- 対象：単独行 `preset.get("player_damage_taken", 1.0)`
- 変更：行を削除（または `# TODO: 難易度プリセットの補正値を適用` を残す）。

### Step 16. `reputation_gate_system.py`
- 対象：単独行 `params.get("duration", 300)`
- 変更：行を削除（または `duration = params.get("duration", 300)` にして後で使うなら TODO を残す）。

### Step 17. `data_manager.py`
- 対象：単独行 `skill_trees_raw.get("skill_trees", {})`
- 変更：行を削除。

### Step 18. `config_manager.py`
- 対象：単独行 `self.config.get("settings", {}).get("telemetry_enabled", False)`
- 変更：行を削除。

### Step 19. `asset_manager.py`
- 対象：連続する 3 行の `assets.get("emote_pixel", ...)` 等の単独文
- 変更：3 行すべて削除。

### Step 20. `reincarnation_system.py`
- 対象：単独行 `m.get("name", "")`
- 変更：行を削除。

### Step 21. `src/relationships/quest_integration.py`
- 対象：4 か所の `req.get("relationship_type", "favorability")` / `bonus.get(...)` の単独行
- 変更：4 行すべて削除。

### Step 22. `src/relationships/engine.py`
- 対象：単独行 `data.get("relationship_types", [RelationshipType.FAVORABILITY.value])`
- 変更：行を削除。

### Step 23. `src/relationships/graph.py`
- 対象：単独行 `data.get(...)`（約 454 行目）
- 変更：行を削除。

### Step 24. `tools/analyze_assets.py`
- 対象：2 か所の `config.get("sound", {})` 系単独行（約 270, 276 行目）
- 変更：2 行削除。

### Step 25. `tools/optimize_assets.py`
- 対象：2 か所の `config.get("sound", {})` 系単独行（約 161, 167 行目）
- 変更：2 行削除。

### Step 26. `tools/restore_assets.py`
- 対象：単独行 `config.get("backup", {})`
- 変更：行を削除。

### Step 27. `tools/backup_assets.py`
- 対象：単独行 `config.get("backup", {})...`
- 変更：行を削除。

### Step 28. `tools/stats_assets.py`
- 対象：2 か所の `.get("total_tilesets", 0)` / `.get("total_size_bytes"...)` 単独行
- 変更：2 行削除。

### Step 29. `tools/docs_assets.py`
- 対象：4 か所の `result.get(...)` 単独行
- 変更：4 行削除。

### Step 30. `uirenderer.py`
- 対象：`TILE_REGISTRY.get_uv(tile_id, scale="tiny_rogue_16")` の単独行（try 内）
- 変更：行を削除（後の `console.print` で `uv` を使っていないため）。

### Step 31. `visual_regression.py`（その1）
- 対象：`TCODRenderer(40, 24)` の単独行（2 か所）
- 変更：2 行削除（`renderer` は後で使われていないため）。

### Step 32. `visual_regression.py`（その2）
- 対象：`atlas.get_uv(...)` の単独行
- 変更：行を削除。

### Step 33. `tools/tiled_to_game.py`
- 対象：`json.load(f)` の単独行（`if tileset_defs =` が削られた跡）
- 変更：行を削除（`tileset_defs` は以降未使用のため空読み込み）。

### Step 34. 全体再スキャン（PHASE 2 完了確認）
- 操作：`python3 -m ruff check . --select B018 --output-format concise`
- 検証：Step 9–33 のファイルで B018 が 0 件になること。残る B018 があれば同様に削除。

---

## PHASE 3 — 例外処理の改善（重要モジュール優先）（ステップ 35–54）

> 各ステップ：モジュール先頭に `import logging` と `logger = logging.getLogger(__name__)` を追加し、
> `except Exception:` ブロック内に `logger.exception("...")`（または `logger.warning("...")`）を 1 行追加する。
> 検証：`python3 -m py_compile <ファイル>` が通ること。

### Step 35. `web_server.py`：ロガー追加
- ファイル先頭付近に `import logging` と `logger = logging.getLogger(__name__)` を追加。

### Step 36. `web_server.py`：FOV import except
- 対象：`except Exception:`（fov import 周辺）に `logger.exception("FOV モジュール利用不可")` を追加。

### Step 37. `web_server.py`：tokens except
- 対象：`load_design_tokens` の except に `logger.exception("トークン取得失敗")` を追加。

### Step 38. `web_server.py`：font_scale except
- 対象：フォントスケール取得の except に `logger.exception("フォントスケール取得失敗")` を追加。

### Step 39. `web_server.py`：tutorial steps except
- 対象：チュートリアル読み込みの except に `logger.exception("チュートリアル読み込み失敗")` を追加。

### Step 40. `web_server.py`：light_map except
- 対象：ライトマップ計算の except に `logger.exception("ライトマップ計算失敗")` を追加。

### Step 41. `web_server.py`：browser launch except
- 対象：ブラウザ起動の except に `logger.warning("ブラウザ起動不可")` を追加。

### Step 42. `update_checker.py`：ロガー + except
- ロガー追加、`fetch_remote_version` の `except Exception:` に `logger.warning("バージョン取得失敗")` を追加。

### Step 43. `uirenderer.py`：ロガー追加
- ロガー追加（Step 30 のファイルと同一）。

### Step 44. `uirenderer.py`：2 つの except
- try 内の 2 か所の `except Exception:` に `logger.exception("UI アイコン描画失敗")` を追加。

### Step 45. `save_system.py`：ロガー + 2 except
- ロガー追加、`F841` となっていた 2 か所の `except Exception as e:` に `logger.exception("セーブ失敗")` 等を追加。

### Step 46. `backup.py` / `backup_management.py`：ロガー + except
- 両ファイルにロガー追加と、主要な `except Exception` へのログ追加。

### Step 47. `restore.py` / `rollback_management.py`：ロガー + except
- 両ファイルにロガー追加と、主要な `except Exception` へのログ追加。

### Step 48. `upgrade.py` / `downgrade.py`：ロガー + except
- 両ファイルにロガー追加と、主要な `except Exception` へのログ追加。

### Step 49. `auto_repair.py` / `auto_repair_management.py`：ロガー + except
- 両ファイルにロガー追加と、主要な `except Exception` へのログ追加。

### Step 50. `config_manager.py`：ロガー + except
- ロガー追加（Step 18 のファイルと同一）、設定読み込みの `except` にログ追加。

### Step 51. `entity.py`：ロガー + 主要 except
- ロガー追加、シリアライズ/デシリアライズ周辺の `except Exception` に `logger.exception` を追加（全件ではなく主要 2–3 か所）。

### Step 52. `game.py`：ロガー + 主要 except
- ロガー追加、メインループ/初期化周辺の `except Exception` にログ追加。

### Step 53. `audio/backend.py` / `audio/bgm_player.py`：ロガー + except
- 両ファイルにロガー追加と、再生/読み込みの `except` にログ追加。

### Step 54. `sound_manager.py`：ロガー + except
- ロガー追加、再生エラーの `except` に `logger.exception("音声再生失敗")` を追加。

---

## PHASE 4 — 広範囲 `except` の一括改善（ステップ 55–60）

### Step 55. 残りリストの取得
- 操作：`grep -rln "except Exception" --include=*.py . | grep -vE "tests/|tools/" > /tmp/except_files.txt; wc -l /tmp/except_files.txt`
- 検証：リストが保存されること。

### Step 56. 各モジュールへのロガー追加（一括）
- 操作：`/tmp/except_files.txt` の各ファイル先頭（既存 import の次）に
  `import logging` と `logger = logging.getLogger(__name__)` を手動で追加。
- 検証：各ファイルで `grep -n "logger = logging.getLogger" <ファイル>` が 1 件あること。

### Step 57. `except Exception:` へのログ挿入（ガイドライン）
- 操作：各ファイルで `except Exception:` を見つけ、ブロック先頭に
  `logger.exception("<ファイル名> で例外")` を 1 行挿入。
- 検証：`python3 -m py_compile <ファイル>` が通ること。

### Step 58. `src/relationships/*` の例外
- 対象：`betrayal, dynamics, engine, event_integration, mentorship, persistence, romance, quest_integration, worldstate_integration`
- 操作：Step 56–57 をこの 9 ファイルに適用。

### Step 59. `core/` および `systems` 系モジュールの例外
- 対象：`core_framework.py`, `systems.py`, `map_engine.py`, `map_renderer.py`, `telemetry_manager.py` 等
- 操作：Step 56–57 を適用。

### Step 60. 一括改善の確認
- 操作：`grep -rn "except Exception" --include=*.py . | grep -v "logger.exception" | grep -v "logger.warning" | wc -l`
- 検証：残数が 0（またはログ付き以外がない）こと。

---

## PHASE 5 — lint 債務の自動解消（ステップ 61–66）

### Step 61. ruff 自動修正の実行
- 操作：`python3 -m ruff check . --fix`
- 検証：`--fix` で解決された件数が表示されること（F401/F841/B007 の多くが消える）。

### Step 62. 残差の確認
- 操作：`python3 -m ruff check . --select F,B,E9 --output-format concise | wc -l`
- 検証：Step 3 のベースラインより減少していること。

### Step 63. 残り未使用 import の手動削除
- 操作：`ruff check . --select F401` の出力を 1 件ずつ確認し、未使用 import を削除。
- 検証：F401 が 0 件になること。

### Step 64. 未使用ループ変数の `_` 化
- 操作：`ruff check . --select B007` で出た `for x in ...` のうち使われない変数を `_` に変更。
- 検証：B007 が 0 件になること。

### Step 65. 重複定義の統合（`entity.py`）
- 対象：`F811` の `skill_tree_progress`（871/876）と `learned_passive_skills`（899/902）
- 変更：重複した定義を 1 つにまとめる（後勝ちの内容を残し、不要な方を削除）。
- 検証：`python3 -m ruff check entity.py --select F811` が 0 件。

### Step 66. lint 最終確認
- 操作：`python3 -m ruff check . --select F,B,E9,C4 --output-format concise > /tmp/ruff_after.txt; diff /tmp/ruff_baseline.txt /tmp/ruff_after.txt | head`
- 検証：エラー件数が大幅に減少していること。

---

## PHASE 6 — 検証・コミット（ステップ 67–72）

### Step 67. 全ファイルのコンパイル
- 操作：`python3 -m compileall -q -x "(\.git|__pycache__|tests/|tools/|packages/)" .`
- 検証：終了コード 0。

### Step 68. テスト収集の再確認
- 操作：`python3 -m pytest --collect-only -q 2>&1 | tail -1`
- 検証：`429 tests collected`（減っていないこと）。

### Step 69. テスト実行
- 操作：`python3 -m pytest tests/ -q 2>&1 | tail -15`
- 検証：失敗があれば該当ステップに戻って修正（テスト自体のバグなら別途対応）。

### Step 70. 変更範囲の確認
- 操作：`git diff --stat`
- 検認：意図しないファイル（バイナリ等）が含まれていないこと。

### Step 71. コミット（論理単位）
- 操作：例
  - `git add monitoring_management.py && git commit -m "fix: 未定義 monitor_dir を修正"`
  - `git add -A && git commit -m "refactor: no-op デッドコード除去と except へのログ追加、lint 清理"`
- 検証：`git log --oneline -3`

### Step 72. プッシュと PR
- 操作：`git push -u origin fix/review-cleanup`
- 検証：リモートに反映され、PR を作成（またはレビュー依頼）。

---

## 終了基準（Done Definition）
- `monitoring_management.py` の `NameError` が解消している。
- `ruff --select B018` が 0 件（no-op デッドコードなし）。
- 主要モジュールの `except Exception` が `logger` で記録される。
- `ruff --select F,B,E9` のエラー件数がベースラインから大幅減（目標 50% 以上減）。
- `pytest tests/` が全件通過（または既知の失敗のみ）。
