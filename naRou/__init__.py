"""naRou 名前空間のリポジトリルートへの写像。

リポジトリはフラットレイアウト（ルート直下にモジュールが並ぶ）だが、コードベースと
テストは `from naRou.<module> import ...` という名前空間でモジュールを参照する。かつては
未追跡のシンボリックリンク `naRou -> .` がその役割を負っていたが、git に含まれないため
fresh clone・wheel・worktree のいずれでも解決できなかった。`__path__` へリポジトリルートを
追加することで、同じ参照を追跡可能なファイルだけで成立させる。

インストール済み wheel では親ディレクトリが site-packages になり、拡張すると site-packages
全体が naRou の名前空間として露出して `import naRou.<任意のモジュール>` が通ってしまう。
そこで `pyproject.toml` をソースチェックアウトの目印として判定する。
"""

from __future__ import annotations

import os

_SOURCE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if os.path.isfile(os.path.join(_SOURCE_ROOT, "pyproject.toml")):
    if _SOURCE_ROOT not in __path__:
        __path__.append(_SOURCE_ROOT)