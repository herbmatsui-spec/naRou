# PLAN P3 — F821 未定義名5件の修復 (案3)

基準: `main` @ `080b7ea` (+ 保全コミット後)
根拠: `plans/AUDIT_2026-10-06_EVALUATION_AND_9_PROPOSALS.md` §1.4/§2
原則: 1ファイル1ステップ、green→green、単独で revert 可能。ruff の `F` ルールセットは F821 を既に select している (`pyproject.toml:123`) — ゲート自体は存在し、ローカルの違反をゼロにして push 時に機能させるのが目的。

---

## 0. 目的と非目標

**目的**: 実測5件の F821 (未定義名 — 到達すれば NameError) を修復し、`ruff check . --select F821` をゼロにする。

**非目標**: F811 (5件 — 案7)、W293/W292/I001 (37件 — 案7)、mypy 全体の是正、挙動変更 (バグが実際に到達不能な箇所は、その事実を確認してから最小修正)。

---

## 1. 実測された5件と修復方針

| 位置 | 未定義名 | 実測された状況 | 修復方針 |
|---|---|---|---|
| `sound_manager.py:142` | `Callable` | ファイル先頭に `from __future__ import annotations` があるためランタイムでは非評価 (潜伏のみ)。`get_type_hints` を呼ぶと NameError | `from collections.abc import Callable` を import に追加 |
| `save_system.py:352` | `game` | 文字列注釈 `"game.Engine"` が未 import の名前を参照 (`from __future__ import annotations` あり、潜伏のみ) | `TYPE_CHECKING` ブロックで `from naRou.game import Engine` を import し、注釈を `"Engine"` に |
| `engine/systems/world_system.py:123` | `engine` ×3 | `def _spawn_dungeon(self)` が引数なしで `engine.dungeon_spawner(engine.kernel, engine)` を参照する**実バグ**。`Engine._spawn_dungeon` (`engine/engine.py:1092`) の壊れた重複であり、grep 実測では呼び出し元ゼロ | 実装時に呼び出しゼロを再確認してから**削除** (壊れた重複コードの撤去) |

---

## 2. リグレッション防止テスト (計画時に名指し)

| テスト | 役割 |
|---|---|
| `tests/test_audio_fallback.py` | 音声プレイヤー (sound_manager) の既存ガード |
| `tests/test_immersion.py` | sound_manager を触る既存ガード |
| `tests/test_run_boundary.py` | ラン境界 (SaveSystem.clear_run / WorldSystem 経路) の既存ガード |
| `tests/test_stability.py` | SaveSystem を触る既存ガード |
| `tests/test_architecture_refactor.py` | world_system 経路の既存ガード |
| コアチャンク14ファイル | 全体の green→green 保証 (P1 と同じ14ファイル) |

**非空虚性のルール**: 修正が「到達不能な壊れた重複の削除」であることを、削除前の grep (呼び出しゼロ) と削除後のテスト緑の両方で証明する。

---

## 3. 原子サブステップ

### ステップ 3-1: `sound_manager.py` の Callable import
1. `from collections.abc import Callable` を標準ライブラリ import 群に追加する。
2. `ruff check sound_manager.py` が F821 ゼロであることを確認。
3. `pytest tests/test_audio_fallback.py tests/test_immersion.py` が緑 → コミット `step-16: sound_manager の Callable 注釈に実体を与える`。

### ステップ 3-2: `save_system.py` の game.Engine 注釈
1. `from typing import TYPE_CHECKING` を追加し、`if TYPE_CHECKING: from naRou.game import Engine` ブロックを設ける。
2. `clear_run` の注釈 `"game.Engine"` を `"Engine"` に変更する。
3. `ruff check save_system.py` F821 ゼロを確認。
4. `pytest tests/test_run_boundary.py tests/test_stability.py` が緑 → コミット `step-17: save_system の注釈を TYPE_CHECKING import に統一する`。

### ステップ 3-3: `engine/systems/world_system.py` の壊れた重複メソッド撤去
1. `grep -rn "._spawn_dungeon\|_spawn_dungeon" --include="*.py"` で呼び出し元ゼロを**再確認** (計画時点の実測: `Engine._spawn_dungeon` への2呼び出しのみ、WorldSystem 側の重複は呼ばれない)。
2. `world_system.py:120-127` の `_spawn_dungeon` を削除する。
3. `ruff check engine/systems/world_system.py` F821 ゼロを確認。
4. `pytest tests/test_run_boundary.py tests/test_architecture_refactor.py` が緑 → コアチャンク緑 → コミット `step-18: 呼ばれない壊れた _spawn_dungeon の重複を撤去する`。

### ステップ 3-4: ゲートの最終確認
1. `ruff check . --select F821` が**ゼロ件**であることを確認。
2. `ruff check .` の残件が F811 5件 + W293/W292/I001 37件 (案7の対象) のみに減ったことを確認。
3. CI の ruff ゲート (`.github/workflows/ci.yml:23`, `validate.yml:29`) が push 時に機能する状態であることを報告書に記す (CI 自体の変更は不要)。
4. コアチャンクを最終実行し、開始時のカウントと一致すること。

---

## 4. Definition of Done

1. `ruff check . --select F821` がゼロ件。
2. コアチャンクの pass/fail/xfail カウントが開始時と完全一致。
3. 3コミットそれぞれが単独で revert 可能。
4. `world_system.py` の重複撤去について、呼び出しゼロの再確認記録がコミットメッセージに残っている。

---

## 5. 検証と失敗時

- ステップ 3-3 で呼び出し元が**見つかった**場合: 削除ではなく引数を通す最小修正に切り替える (`def _spawn_dungeon(self, engine)` + 呼び出し側の引数追加)。
- 修正で既存テストが赤になった場合: 当該コミットを取り消し、当該テストの契約を先に読み直してから再計画する。
