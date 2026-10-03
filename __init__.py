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
に重なり、どちらが採用されるかは setuptools の走査順に依存する。内容を揃えることで採用順に
依存しなくなるため、編集時は必ず両方を同期させること
(`tests/test_narou_package_init.py` が一致を検証する)。

パッケージの `__init__.py` として読まれれば `__path__` があるが、pytest はリポジトリの
パッケージ階層の親としてルートの `__init__.py` を素のモジュール `__init__` として読み込む
ため、`__path__` を持たないまま実行されることがある。名前空間を伸ばす対象が無いので、その
場合は何もしない。
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
