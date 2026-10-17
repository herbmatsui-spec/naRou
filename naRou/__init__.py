"""naRou 名前空間のリポジトリルートへの写像。

リポジトリはフラットレイアウト（ルート直下にモジュールが並ぶ）だが、コードベースと
テストは `from naRou.<module> import ...` という名前空間でモジュールを参照する。かつては
未追跡のシンボリックリンク `naRou -> .` がその役割を負っていたが、git に含まれないため
fresh clone・wheel・worktree のいずれでも解決できなかった。`__path__` へリポジトリルートを
追加することで、同じ参照を追跡可能なファイルだけで成立させる。

インストール済み wheel では親ディレクトリが site-packages になり、拡張すると site-packages
全体が naRou の名前空間として露出して `import naRou.<任意のモジュール>` が通ってしまう。
そこで `pyproject.toml` をソースチェックアウトの目印として判定する。

この内容は `<root>/naRou/__init__.py` と `<root>/__init__.py` の 2 か所に同一で存在する。
`[tool.setuptools.package-dir] naRou = "."` により両者は wheel 上で同じ `naRou/__init__.py`
に重なる。`package-dir` は配置先のリポジトリルートを指すため、実際に wheel に載るのは
ルートのファイル側である。両者を同一に保ち、編集時に片方だけ直して乖離しないよう、
その一致自体をテストで固定する (`tests/test_narou_package_init.py`)。

パッケージの `__init__.py` として読まれれば `__path__` がある。素のモジュールとして読まれた
場合は `__path__` が定義されておらず、伸ばす先の名前空間が存在しないため何もしない。
"""

from __future__ import annotations

import os

# 自身がルート直下の naRou/ であるか、ルートそのもの（__init__.py として読まれる側）であるかを
# pyproject.toml で自己判定し、どちらの配置でも同じ結果になるようにする。判定順は安全側で
# _HERE を先に見る: __init__.py として実行された時点で _HERE は既に __path__ に入っており、
# この分岐は __path__ を広げない。名前空間を広げうるのは _PARENT（= ソースチェックアウト）だけ。
_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)

_SOURCE_ROOT = next(
    (
        candidate
        for candidate in (_HERE, _PARENT)
        if os.path.isfile(os.path.join(candidate, "pyproject.toml"))
    ),
    None,
)

_PACKAGE_PATH = globals().get("__path__")
if _SOURCE_ROOT is not None and _PACKAGE_PATH is not None:
    if _SOURCE_ROOT not in _PACKAGE_PATH:
        _PACKAGE_PATH.append(_SOURCE_ROOT)
