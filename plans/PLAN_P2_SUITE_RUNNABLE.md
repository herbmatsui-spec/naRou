# PLAN P2 — テストスイートを実行可能にする (案2)

基準: `main` @ `080b7ea` (+ 保全コミット後)
根拠: `plans/AUDIT_2026-10-06_EVALUATION_AND_9_PROPOSALS.md` §1.2/§2
原則: **計測が先**。「ハング」と見えたものの正体は重さ (測定済み)。機構を名指して直す。

---

## 0. 目的と非目標

**目的**: フルスイートが有界時間内に完走するようにする。「実装→検証」ループの検証側を成立させる。

**非目標**: テストの意味付けの変更 (期待値を緩めるときは必ず非空虚性の証明を添える)、プロダクション動作の変更 (テスト実行時のみ効く機構)。

---

## 1. 測定済みの根拠

| 事実 | 実測値 |
|---|---|
| `Engine()` 1回の構築 | **平均 2.213秒** |
| 構築のたびに走る不要物 | 全YAMLデータ再読込 (skill trees, jobs, fusions, scenarios, quests, pet quests)、`import pygame` 試行×2 (音声フォールバックが ModuleNotFoundError を握りつぶす)、**`start_web_server(engine, port=8080)`** (`core/system_initializer.py:29`) |
| `test_ranged_ability_accuracy_depends_on_defender` | Engine() を **120回** 構築 → **約265秒+** の単一テスト |
| ストーリーテラーテスト | 単独では **3.35秒でパス** — スイート内の停滞は累積時間 |
| pytest-timeout / xdist | ともに未インストール |

---

## 2. リグレッション防止テスト (計画時に名指し)

| テスト | 役割 |
|---|---|
| `tests/test_narou_package_init.py` | パッケージ初期化の既存ガード |
| `tests/test_audio_fallback.py` | 音声フォールバックの既存ガード (commit `f8c8b4d` で実装拡張に追従済み) |
| `tests/test_difficulty.py` | 難易度シミュレーションの既存ガード |
| `tests/test_enemy_abilities.py` (ハング対象テスト含む) | 敵能力の配線ガード |
| `tests/test_dungeon_world_storyteller_72_steps.py::test_all_72_steps_storyteller_system` | スイート内完走の指標になる単独3.35秒テスト |
| **新規** `tests/test_web_server_gate.py` | `Engine()` がテスト実行時にWebサーバーを起動しないことを spy で検証 |
| **新規** `tests/test_pytest_timeout_config.py` | pyproject の timeout 設定が存在することを検証 (`test_entrypoint.py` の宣言整合パターンを踏襲) |

**非空虚性のルール**: 新規テストには必ず「1つだけ意図的に壊す → 赤になる」を実行し、その出力をコミットメッセージに残す (`tests/helpers/non_vacuity.py` の `assert_can_fail` / `assert_distinguishes` を使用)。

---

## 3. 原子サブステップ

### ステップ 2-1: Engine() の 2.2秒の内訳を計測 (コード変更なし)
1. `cProfile` で `Engine(renderer=NullRenderer())` を3回プロファイルし、data loading / pygame 試行 / web server / その他の配分を記録する。
2. 以降のサブステップの優先順位をこの内訳で確定する (推定で手を入れない)。

### ステップ 2-2: テスト実行時の Web サーバー起動を止める
1. `core/system_initializer.py:29` 周辺: 環境変数 `NAROU_DISABLE_WEB_SERVER` を読み、設定されていれば `start_web_server` を呼ばない機構を追加する (プロダクション既定は現状維持)。
2. `tests/conftest.py` で `os.environ.setdefault("NAROU_DISABLE_WEB_SERVER", "1")` を設定する。
3. 新規 `tests/test_web_server_gate.py`: `web_server.start_web_server` を monkeypatch した spy で、env 設定時に呼ばれないこと / env 未設定時に呼ばれること (非空虚性) を検証する。
4. 既存ガード (`test_narou_package_init.py`, コアチャンク) が緑であることを確認 → コミット `step-12: テスト実行時にWebサーバーを起動しない`。

### ステップ 2-3: 重い反復ループのサンプリング削減
1. `tests/test_enemy_abilities.py::test_ranged_ability_accuracy_depends_on_defender`: 60+60回 → **20+20回** に削減 (防御 dex 2 vs 40 の差は大きく、20試行で統計的に判別可能 — 5回連続実行でフレークしないことを確認)。
2. 同ファイル内の 40〜80回 ループを持つテスト (`test_fire_breath_damage_is_reduced_by_fire_resistance` 等) を同基準で削減する。
3. `tests/test_difficulty.py::test_every_difficulty_can_kill_the_player`: `num_sims = 1000` → **200** に削減 (3 プリセット × 200 = 600 Entity シミュレーション — 軽量な Entity 直接なので許容範囲)。削減前に、200試行でも全プリセットで死亡が観測されることを確認する。
4. 削減した各テストを5回連続実行して flake なしを確認 → コアチャンク緑 → コミット `step-13: 重い反復ループを統計的に十分な試行数に削減する`。

### ステップ 2-4: Engine() のデータ再読込キャッシュ (内訳が data loading 大半の場合のみ)
1. ステップ 2-1 の計測で data loading が 2.2秒の過半を占めることを確認済みであること。
2. 不変のレジストリ読込 (skill_tree_system, job_system, skill_fusion_system の3つ) に module-level キャッシュを導入する (可変データ `config.yaml` `monsters.yaml` には手を入れない — テストがデータを書き換える前提のものがあるため)。
3. キャッシュヒットを検証する spy テストを新規追加 (2回目の構築で load が走らないこと)。
4. 既存ガード (データ整合テスト群 + コアチャンク) が緑 → コミット `step-14: 不変レジストリの読込をキャッシュする`。

### ステップ 2-5: pytest-timeout の導入
1. `pip install pytest-timeout` (テスト環境) + `pyproject.toml` の `[project.optional-dependencies].dev` に `pytest-timeout` を追加。
2. `[tool.pytest.ini_options]` に `timeout = 300` と `timeout_method = "thread"` を追加 (個々の重いテストが凍結したら FAIL にする — スイート全体の凍結を防ぐ装置)。
3. 新規 `tests/test_pytest_timeout_config.py`: pyproject を parse して `timeout` と `timeout_method` が設定されていることを検証。
4. コミット `step-15: pytest-timeout を導入してスイート凍結を FAIL に変える`。

---

## 4. Definition of Done

1. フルスイート (ストーリーテラーテスト込み) が `timeout 900s` で完走する。
2. `test_ranged_ability_accuracy_depends_on_defender` が単独で 60秒以内に完走する。
3. コアチャンクの pass/fail/xfail カウントが開始時と不変 (既知の 1 failed を除き増減なし)。
4. 各新規テストの非空虚性証明 (壊す→赤) の出力がコミットメッセージに残っている。

---

## 5. 検証と失敗時

- 反復数を削減したテストが5回実行で1度でも flake した場合: 試行数を一段階戻す (20→30)。
- キャッシュ導入でデータ整合テストが赤になった場合: キャッシュを取り消し、案6 (速度対策) として反復数削減のみで着地させる。
- `timeout_method = "thread"` で偽陽性が多発する場合: `timeout = 600` に緩めるか、対象テストを `@pytest.mark.timeout(120)` で個別指定する。
