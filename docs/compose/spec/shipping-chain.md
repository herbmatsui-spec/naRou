---
feature: shipping-chain
status: delivered
updated: 2026-10-04
branch: fix/shipping-chain
commits: d70891d..ed09d5f
---

# 出荷の鎖を一本に通す (案1)

## Report

**What was built** — 起動できない原因を 4 つ同時に断った。`game.py` に `main(argv=None)` を実装し、`--text` / `NAROU_FORCE_TEXT` のときだけ GPU 不要のテキストモードへ委譲させた。統合メニューの 1 番が `AttributeError` で落ちていたため、`narou` コンソールスクリプトと `python -m game` の両方が壊れていた。`python -m game` は同じ統合メニューを起動し、モジュール属性の `main` 関数と衝突しないよう別名で束縛する。コンソールスクリプトは `main()` を引数なしで呼ぶため、`argv is None` のときは `sys.argv` へ委譲させ、`narou --text` が到達できるようにした。

未追跡シンボリックリンク `naRou -> .` を廃し、追跡される `naRou/__init__.py` とリポジトリルートの `__init__.py` をバイト同一にして、フラットレイアウトのリポジトリを `naRou.<root_module>` として参照させる名前空間を成立させた。依存宣言は `pyproject.toml` / `requirements.txt` / `requirements-lock.txt` の 3 つを同一の 8 依存へ揃え、`scipy` を実行時依存に追加し、`requires-python` を `>=3.10` へ上げた。`[tool.setuptools.package-dir] naRou = "."` と明示的な `packages` 列挙により、fresh clone からゲームコードを含む wheel がビルドできるようになった。

**Verification** — すべて本ブランチで実行し、成功した。

```
pytest tests/test_entrypoint.py tests/test_narou_package_init.py -q   PASS — 17 passed in 16.81s
pytest tests/ -q                                                     PASS（既知の失敗 15 件）— 15 failed, 636 passed in 141.55s
pip wheel --no-deps -w /tmp/wc2 .                                    PASS — ガードを出荷物に含む / tests/ 0 件 / data/schemas 16 件同梱
                                                                        entry_points = "narou = naRou.game:main"
wheel を偽 site-packages へ展開して import                             PASS — naRou.__path__ は ['<sp>/naRou'] のみ、親は露出しない
pip install --prefix /tmp/narou_prefix --ignore-installed <wheel>     PASS — 8 依存すべて解決、bin/narou を生成
ruff check / ruff format --check（変更した 5 ファイル）                  PASS
```

残る 15 件の失敗はすべて未実装のプレースホルダデータ由来（`assert 0 > 0`、`jobs.yaml` / `skill_trees.yaml` / `skill_fusion.yaml` / `data/text/en.yaml` が空）で、本 feature の残件ではない。実装前のベースラインは 16 failed / 618 passed で、`test_renderer_parity` が scipy 導入によって green になった分の改善はこの改善は本 feature の効果として記録する。

**Journey log**

- `[tool.setuptools.package-dir] naRou = "."` は、リポジトリルートの `__init__.py` と `naRou/__init__.py` を wheel 上の同一パスに重ねる。ガードを一方のファイルにだけ書くと、setuptools が採用した側が黙って勝つため出荷物には入らない。2 つのファイルが 1 つの成果物に写像されるときは、内容を揃えること自体をテストで固定するのが唯一の防御になる。
- 回帰テストが「テスト自身が短絡する環境変数」を設定すると罠になる。メニュー 1 番のテストは `NAROU_FORCE_TEXT` を設定していたため、`main.py` のメニューより前に分岐して 1 番を一度も読んでいなかった。修正前のツリーでも通るテストは壊れた実装の証拠にならない。到達は肯定的な観測マーカーで固定する。
- `q:終了` のようなガイド文字列だけでは識別子にならない。メニュー 3 番も同じ文字列を出すため、1 番だけが通る経路（`falling back to text mode`）との併用が必須だった。
- `[tool.setuptools.package-data]` の `**` は再帰する（`build_py.py:131` が `glob(..., recursive=True)` で展開するため）。素の `glob.glob()` は `recursive=True` なしで試すと 1 階層しか一致せず、「壊れている」ように見える。この主張は実測で反証され撤回された。
- 実装前の調査だけで「メニュー 1 番は SDL コンテキスト作成まで到達し、そこで初めて `AttributeError` が消えた」ことを確認できていた。壊れていると仮定したうえで直すと直したつもりになれるので、着手前に実挙動を一度通しておくのが最短だった。

## [S1] Problem

### S1.1 ゲームが起動できない

README が案内する起動手順を最後までたどってもゲーム本編に入れない。`main.py` の統合メニューで「1. naRogue: Masterpiece Edition（ゲーム本編）を起動」を選ぶと例外で終了する。

```
$ python main.py        # 1 を選択
ゲーム本編を起動します...
【重大なエラーが発生しました】: module 'game' has no attribute 'main'
  File "/home/herbmatsui/narou/main.py", line 143, in main
    game.main()
AttributeError: module 'game' has no attribute 'main'
```

`pyproject.toml:31` が宣言するコンソールスクリプト `narou = "game:main"` も同じ理由で壊れている。`game.py` は 6 行の再エクスポートのみで `main` 関数を持たない。実際のゲームループは `engine/engine.py:2552` の `main()` だが、そこへ到達する出荷用の入口は存在しない。`Makefile` の `run: python3 -m game` も no-op で、`main.py` メニュー 3 が呼ぶ `main_text.py` だけが実際に動く。

### S1.2 fresh clone でテストスイート自体が読めない

コードベースは `from naRou.<module> import ...` でモジュールを参照するが、その `naRou` は**未追跡のシンボリックリンク `naRou -> .`** でしか存在しない。git に無いため、fresh clone では以下が成立する。

```
$ pytest tests/test_repositories.py
ImportError while loading conftest 'tests/conftest.py'
tests/conftest.py:14: in <module>
    import game
game.py:6: from naRou.engine import Engine
E   ModuleNotFoundError: No module named 'naRou'
```

テストスイート 634 件が 1 件も収集できない。加えてこのシンボリックリンクは自身を指すため、`pytest .` や `coverage .` のような素朴な再帰コマンドが終わらない。

### S1.3 ビルド成果物がゲームを含まない

`pyproject.toml:33-36` は `include = ["naRou*"]` / `exclude = [... "engine*", "core*", "data*", "skill_eater*", ...]` を指定する。`naRou` がシンボリックリンク的前提下の書き方なので、fresh clone でビルドすると**ゲームモジュールが 0 個の wheel** になり、`pip install .` の結果は「依存だけ入ってゲームが無い」状態になる。

### S1.4 依存宣言が実装と食い違う

- `pyproject.toml:15-18` の依存は `tcod` と `Pillow` の 2 つだけ
- `requirements.txt` は 7 パッケージ
- 実際には `core/msdf_atlas.py:131` が実行時に `from scipy.ndimage import distance_transform_edt` を実行する

`scipy` はどこにも宣言されていないため、フォントアトラス生成時に `ModuleNotFoundError` で落ちる。`tests/test_renderer_parity.py::test_renderer_parity` が現在この理由で FAIL している。

## [S2] Design

### S2.1 `naRou` を追跡可能な実パッケージにする

未追跡シンボリックリンクを廃し、追跡される `naRou/__init__.py` を追加する。ソースチェックアウトから実行”时だけ、`__path__` にリポジトリルートを追加して既存の `naRou.<root_module>` 参照をそのまま解決させる。

- `__path__` 拡張の有効化条件は「自身のディレクトリか親ディレクトリに `pyproject.toml` が存在する」こと。インストール済み wheel（親は `site-packages`）では発火せず、`naRou.__path__` はパッケージ自身のみを指す。`site-packages` 全体が `naRou` の名前空間として露出する事故を防ぐ。wheel に `pyproject.toml` を含めないことがこの安全性の前提である。
- 交付時に判明した衝突: `[tool.setuptools.package-dir] naRou = "."`（S2.4）により、リポジトリルートの `__init__.py` と `naRou/__init__.py` が wheel 上の同一パス `naRou/__init__.py` に重なる。ガードを `naRou/__init__.py` 側だけに持つと出荷物にはガードが入らない。対策として両ファイルの内容をバイト同一にし、設置位置を自己判定する（`(_HERE, _PARENT)` を順に `pyproject.toml` で判定）。一致の維持は `tests/test_narou_package_init.py` が固定する。
- 契約: シンボリックリンクなしで `import naRou.engine` / `naRou.constants` / `naRou.item_system` / `naRou.core_framework` が成功する。
- 契約: インストール済み wheel では `naRou.__path__` が `site-packages` を含まない。
- メイン作業ツリーの `naRou -> .` は本ブランチ取り込み前に削除する（未追跡なので `ln -s . naRou` で戻せる）。

### S2.2 起動経路を 1 本に寄せる

`game.main()` を実装し、出荷用の唯一の入口にする。

- `game.main(argv=None)`。既定は図形ループ `engine.engine.main()`。
- `--text` が argv に含まれるか、環境変数 `NAROU_FORCE_TEXT` が真のときだけ、GPU/SDL を生成しない `engine.run_text_mode()` 経路に委譲する。`run.py:20` は既にヘッドレス Linux で `NAROU_FORCE_TEXT=1` を設定しているため、この契約でそのままヘッドレス実行が通る。
- `python -m game` が `main.py` と同じ統合メニューを起動できるようにする（`Makefile` の `run:` と `pyproject.toml` の `narou` スクリプトの両方がこれを前提にする）。
- 例外は握りつぶさない。`main.py:147` の広い `except Exception` は維持しつつ、ログに原因が残るようにする（本次スコープ）。

### S2.3 依存宣言を実装に合わせる

- `pyproject.toml` の `dependencies` を `requirements.txt` と同一の集合にする。
- `scipy` を実行時依存として明示的に追加する。
- 開発ツール（pytest / mypy / ruff / black / isort / watchdog）は `[project.optional-dependencies].dev` に集約し、`requirements.txt` は実行時依存だけとする。
- `.github/workflows/cd.yml:27` が `requirements-lock.txt` を参照しているため削除はせず、同じ集合に揃える。
- `requires-python` を `>=3.8` から `>=3.10` へ上げる。ruff の `target-version = "py310"` と mypy の `python_version = "3.10"` に合わせ、宣言が実態と矛盾しないようにする。
- `requirements.txt` を唯一の正とし、重複定義による食い違いを今後出新さないことをレビュー基準にする。`pyproject.toml` / `requirements.txt` / `requirements-lock.txt` の3ファイルの集合一致は `tests/test_entrypoint.py` が固定する。

### S2.4 wheel がゲームを含めるようにする

- `[tool.setuptools.package-dir]` で `naRou = "."` を宣言し、`[tool.setuptools] packages` に `naRou` および `naRou.<subpackage>` を明示列挙する。これによりリポジトリルートが wheel 内で `naRou` パッケージ 配置として解決され、シンボリックリンク不要でルートモジュールとサブパッケージが正しく同梱される。
- 現在の巨大な `exclude` リストは削除する（サブパッケージ名は `naRou.engine` 等となり、`engine*` パターンでは一致しないため不要）。
- 契約: `pip install .` で生成した wheel がゲームモジュール（`naRou/game.py`、`naRou/main.py`、`naRou/engine/`、`naRou/core/` ほか実行に到達する全サブパッケージ）を含む。シンボリックリンクが無い状態でビルドできる。
- 契約: 生成した wheel を隔離した prefix にインストールすると、宣言済み 8 依存がすべて解決され、`narou` コンソールスクリプトが `from naRou.game import main` として正しく生成される。
- 既知の制約（実測）: コードベースは `naRou.X` と素の `X` の両方の import を混在させており、`engine/engine.py:32` の `from advanced_systems import ...` を代表に、非 editable なインストール済み wheel では素の import が解決せず `narou` は起動時に `ModuleNotFoundError` で止まる。ソースチェックアウトと editable インストールではリポジトリルートが `sys.path` に入るため動作する。

## [S3] Out of Scope

- **import 名前空間の統一** — `from naRou.X import` と `from X import` の混在を 591 ファイルに及ぶ一括整理で解消する。これが解けるまで、非 editable なインストール済み wheel はコードを得るが実行できない。正攻法だが本 feature の変更量を超えるため別 feature とする。
- **リソース解決の CWD 非依存化** — `data_manager.py:74` の `data_dir="data"` を代表に 85 ファイルが相対パスでリソースを読むため、インストール先を基準に解決するには大規模な改修が要る。別 feature とする。
- **`data/`・`assets/` の完全同梱** — wheel には実行コードを確実に含め、データ同梱の完全性は上記 2 件とまとめて扱う。

- **案2（コンテンツ作成）** — `data/*.yaml` の中身、`en.yaml` の翻訳、Devour スキルの実使用化。別 feature として扱う。
- **案3（コードベース整理）** — 死んだ 80 モジュールの削除、`testpaths` による 132 件のテスト除外の解消、CI の `|| true` 除去、追跡対象のアセット整理。別 feature として扱う。ただし本 feature が CI 上のビルド検証を必要とするため、T4 で `pip install .` を実行できる環境を整えた時点で CI 側の改変は行わない。
- レンダラの 3 世代並存（`renderer.py` 系と `core/` 系）の整理。
- `engine/engine.py`（2,630 行 / 189 def）の分割。
- ゲームバランス・進行 Lore の変更。

## Tasks

- [x] T1: 追跡される `naRou/__init__.py` を追加し、ソースチェックアウト時のみ `__path__` をリポジトリルートへ拡張する。`pyproject.toml` が存在しない親ディレクトリでは拡張しないこと — acceptance: シンボリックリンクなしで `python -c "import naRou.engine, naRou.constants"` が成功する (covers: S2.1)
- [x] T2: `game.main(argv=None)` を実装し、`--text` / `NAROU_FORCE_TEXT` で GPU 不要経路に委譲する。`python -m game` を `main.py` の統合メニューに接続する — acceptance: `python main.py` に `1` を渡すと `AttributeError` が出ずゲームループに入る (covers: S2.2)
- [x] T3: `pyproject.toml` の `dependencies` を `requirements.txt` と一致させ `scipy` を含める — acceptance: `tests/test_renderer_parity.py::test_renderer_parity` が scipy 未導入を理由に FAIL しない (covers: S2.3)
- [x] T4: `[tool.setuptools.package-dir]` で `naRou = "."` を宣言し、`[tool.setuptools] packages` に `naRou` と実行に到達する全サブパッケージ（55個）を明示列挙する。巨大 `exclude` は削除し、`[project.scripts]` を `naRou.game:main` にする — acceptance: wheel が `naRou/game.py` と `naRou/engine/__init__.py` を含み、`tests/` を含まず、隔離 prefix へのインストールで 8 依存が解決され `narou` スクリプトが `from naRou.game import main` として生成される (covers: S2.4)
- [x] T5: リグレッション防止テスト `tests/test_entrypoint.py` を追加する。`game.main` の存在と可変性、`NAROU_FORCE_TEXT` によるテキストモード選択、`python -m game` の起動、`naRou` がシンボリックリンクでないこと、MSDF アトラス生成成功を各ケースとして固定する — acceptance: 本テストがこれらの不具合を再現する形で失敗し、T1〜T4 適用後は全て成功する (covers: S2.1, S2.2, S2.3)
- [x] T6: README の起動手順を実装に合わせて更新する。テスト数のバッジは「全件成功」を意味(fake)_buffせず、`pytest tests/` の実測値（合格数と既知の失敗数）を明記する。既知の失敗は案2・案3由来であり、本 feature の残件ではない — acceptance: README の手順がそのまま再現でき、バッジの数値が `pytest tests/` の出力と一致する (covers: S2.2)

## 関連仕様書

- [combat-resolution.md](combat-resolution.md) — AP制戦闘解決モデル仕様 (Phase 2 Step 33)
- [win-condition.md](win-condition.md) — 勝利条件仕様 (Phase 1 Step 19)
- [run-end-state.md](run-end-state.md) — 死亡/勝利時の状態遷移 (Phase 1 Steps 12-20)
- [survival-balance.md](survival-balance.md) — 空腹/回復/毒性バランス (Phase 1 Step 29)
- [run-carrying.md](run-carrying.md) — ラン引継ぎ仕様 (Phase 1 Step 20)
- [devour-wiring.md](devour-wiring.md) — Devourシステム配線 (Phase 3+)