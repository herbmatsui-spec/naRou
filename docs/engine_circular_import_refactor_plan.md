# 実装計画: engine.py の循環参照リスク低減（コンストラクタ内遅延インポートの解消）

- 優先度: 4（中）
- 対象: `naRou/engine/engine.py`（2664 行）
- 目的: コンストラクタ／メソッド内の遅延 `import` を排除し、パッケージ境界を整理して初期化バグを防ぐ
- 方針: 依存レイヤを明文化し、重いサブシステム読み込りを専用の bootstrap モジュールに集約する。各ステップは小さく、低性能 LLM でも 1 回の edit で完結する粒度。

---

## 背景と現状（なぜ危険か）

`engine.py` の `__init__` および各メソッドには、実行時に `from naRou.xxx import Yyy` を毎回行う「遅延インポート」が多数散在する。

- コンストラクタ内: `engine.py:85` `SystemInitError`、`engine.py:91-100` の 10 個の Package 類、`engine.py:140` `GameStateInitializer`、`engine.py:161` `SystemInitializer`
- メソッド内: `engine.py:173` `DataParseError`、`engine.py:199` `ResourceLoadError`、`engine.py:241` `InputHandler`、`engine.py:398/405` `TerritoryState`、`engine.py:682/688` `REGISTRY/GENERATOR`、`engine.py:905/963/1066` `CharacterState` 等、`engine.py:1195` `setup_systems`、`engine.py:1225` `StateMachine`、`engine.py:1348` `CombatManager` など計 30 件以上。

これらは「本来はトップレベルで import したいが循環参照を恐れてメソッド内に逃がしている」状態の匂い（code smell）である。新しいサブシステムを増やすたびに同じパターンが増殖し、初期化順序のバグが起きやすくなる。

一方、既存の `naRou/packages/*/package.py` は `IPackage` + `PackageMetadata(dependencies=[...])` という明確な境界を持っている。この境界を使い、エンジン側の依存を「レイヤリング」して整理する。

---

## 依存レイヤの定義（目標アーキテクチャ）

```
L0 例外/定数       naRou/exceptions, naRou/constants
L1 カーネル/基底    naRou/packages/core/kernel/*, naRou/packages/core/package
L2 ドメインパッケージ naRou/packages/{gameplay,character,social,meta,world,world_a,narrative,platform}
L3 エンジン補助     naRou/core/world_state_manager, naRou/core/system_initializer,
                    naRou/core/systems/setup_coordinator, naRou/core/state_machine
L4 入出力/UI        naRou/input_handler, naRou/renderer, naRou/ui/*
L5 エンジン         naRou/engine/engine.py  ← ここから重い import を追い出す
```

原則:
- L0〜L4 のモジュールは**トップレベル import** にする（循環しないことが証明済み）。
- どうしても循環するものだけ `TYPE_CHECKING` ブロックへ移動。
- エンジン起動時に必要な「重い一括読み込み」は `naRou/engine/bootstrap.py` に集約し、Engine はそれを 1 回呼ぶだけにする。

---

## フェーズ A: 現状測定と安全網（ステップ 1–12）

1. `naRou/engine/` に `refactor_notes.md` を作成し、目的を 1 行書く。
2. `git status` でクリーンな状態を確認し、作業用ブランチ `refactor/engine-imports` を作成する。
3. `tests/` ディレクトリを確認し、engine 関連のテストファイル名を `refactor_notes.md` に列挙する。
4. `python -c "import naRou.engine.engine"` が成功することを確認し、所要時間を計測して `refactor_notes.md` に記録する（ベースライン）。
5. 既存テストを 1 度全実行し、失敗数を `refactor_notes.md` に記録する（ベースライン）。
6. `engine.py` 内の `^\s+(from|import) ` パターンを grep し、遅延インポート行の一覧（行番号付き）を `refactor_notes.md` に貼る。
7. 各遅延 import について「型専用か／実行時必要か」を 1 列ずつ判定し表を作る。
8. `naRou/exceptions.py` を開き、エクスポートされている例外名を `refactor_notes.md` に列挙する。
9. `naRou/packages/core/kernel/kernel.py` を開き、`Kernel` の public メソッド名を `refactor_notes.md` に列挙する。
10. `naRou/core/world_state_manager.py` の `GameStateInitializer` シグネチャを確認しメモする。
11. `naRou/core/system_initializer.py` の `SystemInitializer.initialize_ui_and_services` シグネチャを確認しメモする。
12. `naRou/core/systems/setup_coordinator.py` の `setup_systems` シグネチャを確認しメモする。

## フェーズ B: 境界コントラクトの明文化（ステップ 13–21）

13. `naRou/engine/__init__.py` を開き、現在の内容を確認する（空ならそのまま）。
14. `naRou/engine/layers.py` を新規作成し、docstring のみ書く（「依存レイヤ定数定義モジュール」）。
15. `layers.py` に `LAYER_EXCEPTIONS = "L0"` などの文字列定数を 1 つ追加する。
16. `layers.py` に `LAYER_KERNEL = "L1"` を追加する。
17. `layers.py` に `LAYER_PACKAGES = "L2"` を追加する。
18. `layers.py` に `LAYER_ENGINE_SUPPORT = "L3"` を追加する。
19. `layers.py` に `LAYER_IO_UI = "L4"` を追加する。
20. `layers.py` に `LAYER_ENGINE = "L5"` を追加する。
21. `refactor_notes.md` に「許容される import 方向は L0→L5 のみ。逆方向は禁止」とルールを明記する。

## フェーズ C: bootstrap モジュールの作成（ステップ 22–33）

22. `naRou/engine/bootstrap.py` を新規作成し、docstring（「Engine 起動用の重い import を集約」）のみ書く。
23. `bootstrap.py` の先頭に `from __future__ import annotations` を 1 行追加する。
24. `bootstrap.py` に `import logging` と `logger = logging.getLogger(__name__)` を追加する。
25. `bootstrap.py` に `from naRou.exceptions import SystemInitError` をトップレベルで追加する（L0）。
26. `bootstrap.py` に 10 個の Package import（`CharacterPackage` 等）をトップレベルで追加する（L2）。
27. `bootstrap.py` に `from naRou.packages.core.kernel.kernel import Kernel` を追加する（L1）。
28. `bootstrap.py` に `GameStateInitializer` の import を追加する（L3）。
29. `bootstrap.py` に `SystemInitializer` の import を追加する（L3）。
30. `bootstrap.py` に `setup_systems`（setup_coordinator）の import を追加する（L3）。
31. `bootstrap.py` に `build_kernel()` 関数の空骨架（docstring + `pass`）を作成する。
32. `build_kernel()` に `Kernel()` 生成と 10 個の `load_package` 呼び出しを移植し、`SystemInitError` で包む。
33. `build_kernel()` が `kernel` を返すことを確認するため、関数末尾に `return kernel` を書く。

## フェーズ D: コンストラクタの遅延インポート解消（ステップ 34–48）

34. `engine.py:85` の `from naRou.exceptions import SystemInitError` を削除し、代わりに bootstrap 側で済ませているため Engine 側には書かない方針を採用（例外は L0 なのでトップレベル import に変更）。
35. `engine.py` トップレベル import 群（line 26-73 付近）の末尾に `from naRou.exceptions import SystemInitError` を 1 行追加する。
36. `engine.py` の `__init__` 冒頭ブロック（line 84-118）の `from naRou.packages... import ...` 8 行（91-100）を全削除する。
37. 削除した Package import を `engine.py` トップレベル import 群に 1 つずつ移動する（1 行目: `CharacterPackage`）。
38. 同上で `CorePackage` をトップレベルに移動。
39. 同上で `GameplayPackage` をトップレベルに移動。
40. 同上で `MetaPackage` をトップレベルに移動。
41. 同上で `NarrativePackage` をトップレベルに移動。
42. 同上で `PlatformPackage` をトップレベルに移動。
43. 同上で `SocialPackage` をトップレベルに移動。
44. 同上で `WorldPackage` をトップレベルに移動。
45. 同上で `WorldAPackage` をトップレベルに移動。
46. 同上で `Kernel` をトップレベルに移動（`TYPE_CHECKING` ブロックから外し実 import にする）。
47. `__init__` のカーネル生成コードを `from naRou.engine.bootstrap import build_kernel` をトップレベルに追加し、`self.kernel = build_kernel()` の 1 行に置換する（DI パスは `if kernel is not None` のまま残す）。
48. `engine.py:140` の `from naRou.core.world_state_manager import GameStateInitializer` を削除し、トップレベル import に 1 行追加する。

## フェーズ E: メソッド内遅延インポートの解消（ステップ 49–60）

49. `engine.py:161` の `SystemInitializer` import を削除しトップレベルへ移動。
50. `engine.py:173` の `DataParseError` import を削除し、ステップ 35 の例外 import 群に統合（既存なら何もしない）。
51. `engine.py:199` の `ResourceLoadError` import を削除し例外 import 群に統合。
52. `engine.py:241` の `InputHandler` import を削除しトップレベルへ移動（L4）。
53. `engine.py:398/405` の `TerritoryState` import を削除し、メソッド冒頭からトップレベルへ 1 行移動。
54. `engine.py:682/688` の `REGISTRY`/`GENERATOR` import を削除しトップレベルへ移動。
55. `engine.py:905/963/1066` の `CharacterState`/`SkillEaterRegistry` import を削除しトップレベルへ移動。
56. `engine.py:1023/1024` の `create_husk`/`HuskInventoryComponent` import を削除しトップレベルへ移動。
57. `engine.py:1195` の `setup_systems` import を削除しトップレベル（bootstrap 経由でも可）へ移動。
58. `engine.py:1225` の `StateMachine` import を削除しトップレベルへ移動。
59. `engine.py:1239` の `ContextMenuBuilder` import を削除しトップレベルへ移動。
60. `engine.py:1348/1354/1385` の `CombatManager`/`SECRET_REGISTRY`/`Item` import を削除しトップレベルへ移動。

## フェーズ F: 型専用 import の整理と境界強化（ステップ 61–66）

61. `engine.py` の `TYPE_CHECKING` ブロック（line 26-27）に `from naRou.input_handler import InputHandler` を型専用として追加（実行時は不要な型ヒント用）。
62. 同ブロックに `from naRou.core.world_state_manager import GameStateInitializer` を型専用として追加。
63. 同ブロックに `from naRou.core.system_initializer import SystemInitializer` を型専用として追加。
64. `bootstrap.build_kernel()` に「循環検出」用の簡易ログ（`logger.info("kernel built with N packages")`）を 1 行追加。
65. `naRou/engine/__init__.py` に `from naRou.engine.bootstrap import build_kernel` を追加し、public API として公開する。
66. `refactor_notes.md` に「追加で発見した循環参照があれば bootstrap へ逃がす」という運用ルールを追記。

## フェーズ G: 検証とロールアウト（ステップ 67–72）

67. `python -c "import naRou.engine.engine"` を実行し、インポート成功と所要時間を記録（ステップ 4 のベースラインと比較）。
68. `python -c "from naRou.engine.bootstrap import build_kernel; build_kernel()"` を実行し Kernel 構築が例外なく終わることを確認。
69. 既存テストスイートを再実行し、失敗数がステップ 5 のベースラインと一致することを確認。
70. `engine.py` 内に残る `^\s+(from|import) ` パターンを grep し、全てトップレベルまたは `TYPE_CHECKING` 内であることを目視確認（メソッド内遅延 import が 0 件になる）。
71. `git diff --stat` で変更範囲を確認し、意図しないファイルが含まれていないかチェック。
72. `refactor_notes.md` に「完了サマリ（削減した遅延 import 件数、ベースライン比較）」を記入し、PR 用の説明文を draft する。

---

## 完了の定義（Definition of Done）

- `engine.py` のメソッド内（トップレベル・`TYPE_CHECKING` 以外）の遅延 `import` が 0 件。
- 重い一括読み込みが `naRou/engine/bootstrap.py` に集約され、Engine は `build_kernel()` 等を呼ぶだけ。
- インポート所要時間がベースライン（ステップ 4）から悪化していない。
- 既存テストがステップ 5 のベースライン通りにパスする。
- `refactor_notes.md` に依存レイヤルールが明記され、今後の追加時の運用が定まっている。

## 低性能 LLM 向けの実施注意

- 各ステップは「1 ファイルにつき 1 回の小さな edit」に留める。
- ステップ間で必ず `python -c "import naRou.engine.engine"` を走らせて壊れていないことを確認する（特に 34–60）。
- 循環参照エラー（`ImportError` / `circular import`）が出たら、その import を `TYPE_CHECKING` ブロックへ逃がすか `bootstrap.py` へ移動してから次へ進む。
- 一度に複数ステップをまとめない。
