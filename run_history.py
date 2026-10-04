"""run 履歴の永続化 (docs/compose/spec/run-carrying.md [S2.1])

`feature/run-end` がゲームを終えられるようにしたが、その結果は画面から消えるだけで
次の run に渡らなかった。ここでは死亡した run の集計をディスクに残し、次回起動時に
「前回どこで死んだか」「自己最高記録」を提示する。

プレイヤーが run をまたいで実際に比較する値は深さと撃破数程度であり、
提示できる情報はその 2 つに尽きる。それ以外の集計は記録だけに残す。

履歴ファイルは run 記録であり、`savegame.bin`（Engine 全体の pickle）とは別枠にする。
壊れた履歴で起動が失敗してはならない。読み取り失敗は理由と共に記録し、
提示文に「黙って無視」しない。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

HISTORY_FILENAME = "run_history.json"
HISTORY_VERSION = 1

# 履歴ファイルが読めなかったときに提示する 1 行。初回起動（ファイル無し）とは区別する。
_UNREADABLE_PREFIX = "【前回の記録を読み込めませんでした】"
_FIRST_RUN_PREFIX = "【前回の記録はありません（初回起動）】"


@dataclass(frozen=True)
class RunHistory:
    """run をまたいで保持する記録"""

    runs: int = 0
    last_depth: int = 0
    last_kills: int = 0
    last_turns: int = 0
    last_cause: str = ""
    best_depth: int = 0
    best_kills: int = 0
    devoured_skills: tuple[str, ...] = ()

    @classmethod
    def from_summary(cls, summary) -> RunHistory:
        """`RunSummary` から履歴の 1 レコードを作る。"""
        return cls(
            runs=1,
            last_depth=summary.depth,
            last_kills=summary.kills,
            last_turns=summary.turns,
            last_cause=summary.cause,
            best_depth=summary.depth,
            best_kills=summary.kills,
            devoured_skills=tuple(getattr(summary, "devoured_skill_ids", ()) or ()),
        )

    def merged_with(self, previous: RunHistory | None) -> RunHistory:
        """以前の履歴に今回の結果を積む。自己最高記録は shallower な run で下げない。"""
        if previous is None:
            return self
        return RunHistory(
            runs=previous.runs + self.runs,
            last_depth=self.last_depth,
            last_kills=self.last_kills,
            last_turns=self.last_turns,
            last_cause=self.last_cause,
            best_depth=max(previous.best_depth, self.best_depth),
            best_kills=max(previous.best_kills, self.best_kills),
            # 喰いスキルは累積させる。run をまたいで得たものは消さない。
            devoured_skills=tuple(dict.fromkeys(previous.devoured_skills + self.devoured_skills)),
        )


@dataclass
class _StoreState:
    history: RunHistory | None = None
    unreadable_reason: str = ""
    present: bool = False


@dataclass
class RunHistoryStore:
    """run 履歴ファイルへの読み書き。

    読み取りは決して例外を投げない。壊れた・読み取り不能な履歴は
    `unreadable_reason` に理由を残し、起動を妨げない。
    """

    base_dir: Path = field(default_factory=Path.cwd)

    @property
    def path(self) -> Path:
        return self.base_dir / HISTORY_FILENAME

    # --- 書き込み ---------------------------------------------------

    def record(self, summary) -> RunHistory:
        """`RunSummary` を履歴に積み、全文を書き出す。"""
        previous = self.load()
        merged = RunHistory.from_summary(summary).merged_with(previous)
        self._write(merged)
        return merged

    def _write(self, history: RunHistory) -> None:
        payload = asdict(history)
        payload["version"] = HISTORY_VERSION
        payload["devoured_skills"] = list(history.devoured_skills)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- 読み取り ---------------------------------------------------

    def load(self) -> RunHistory | None:
        """履歴を読み返す。読めなければ理由を記録し None を返す。"""
        state = self.load_state()
        return state.history

    def load_state(self) -> _StoreState:
        if not self.path.exists():
            return _StoreState(history=None, unreadable_reason="", present=False)
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            return _StoreState(history=None, unreadable_reason=str(exc), present=True)
        if not isinstance(raw, dict):
            return _StoreState(
                history=None,
                unreadable_reason="JSON のトップレベルがオブジェクトでない",
                present=True,
            )
        try:
            history = RunHistory(
                runs=int(raw.get("runs", 0)),
                last_depth=int(raw.get("last_depth", 0)),
                last_kills=int(raw.get("last_kills", 0)),
                last_turns=int(raw.get("last_turns", 0)),
                last_cause=str(raw.get("last_cause", "")),
                best_depth=int(raw.get("best_depth", 0)),
                best_kills=int(raw.get("best_kills", 0)),
                devoured_skills=tuple(raw.get("devoured_skills") or ()),
            )
        except (TypeError, ValueError) as exc:
            return _StoreState(
                history=None, unreadable_reason=f"履歴の項目が不正: {exc}", present=True
            )
        return _StoreState(history=history, unreadable_reason="", present=True)

    # --- 提示 -------------------------------------------------------

    def startup_lines(self) -> list[str]:
        """次回起動時に提示する行。読めなかった場合も理由を必ず添える。"""
        state = self.load_state()
        if state.history is None:
            if not state.present:
                return [f"{_FIRST_RUN_PREFIX}: 記録ファイルが無い"]
            return [f"{_UNREADABLE_PREFIX}: {state.unreadable_reason}"]

        history = state.history
        return [
            f"【前回の記録】{history.runs} 回目の挑戦",
            f"  前回到達深度: {history.last_depth}（死因: {history.last_cause or '不明'}）",
            f"  前回撃破数: {history.last_kills} / 経過 {history.last_turns} ターン",
            f"  自己最高記録: 深度 {history.best_depth} / 撃破 {history.best_kills}",
            f"  喰い得たスキル: {len(history.devoured_skills)} 種",
        ]
