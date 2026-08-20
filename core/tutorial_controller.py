"""tutorial_controller.py - チュートリアル手順の進行管理（Step 38）。

data/tutorial_steps.json を読み込み、現在の手順を返したり前後に進めたりする。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TutorialController:
    def __init__(self, path: str = "data/tutorial_steps.json") -> None:
        self.path = Path(path)
        self.steps: list[dict[str, Any]] = self._load()
        self.index: int = 0

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception:  # noqa: BLE001, S110 - 破損ファイルは空リストへ
            pass
        return []

    def current(self) -> dict[str, Any] | None:
        if 0 <= self.index < len(self.steps):
            return self.steps[self.index]
        return None

    def current_text(self) -> str:
        cur = self.current()
        return cur.get("text", "") if cur else ""

    def advance(self) -> dict[str, Any] | None:
        if self.index < len(self.steps) - 1:
            self.index += 1
        return self.current()

    def back(self) -> dict[str, Any] | None:
        if self.index > 0:
            self.index -= 1
        return self.current()

    def total(self) -> int:
        return len(self.steps)

    def is_last(self) -> bool:
        return self.index >= len(self.steps) - 1
