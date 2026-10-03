"""run summary — 死亡した run の集計 (docs/compose/spec/run-end-state.md [S2.1])

[S2.1]「集計の実装は既存の state から引ける値のみを使い、新たな追跡機構を増やさない」ため、
各値は Engine が死亡判定した時点で，既存の state から引き出したスナップショットである。

死因は毒・窒息・落下などの細分類を避け ([S3])、原因の性質だけを区別する軽量な区分に留める。
"""

from __future__ import annotations

from dataclasses import dataclass

# 死亡時に画面とログへ出す見出し。従来 NPC 攻撃分岐が出していた 1 行を引き継ぐ。
GAME_OVER_TITLE = "★あなたは力尽きた… 【GAME OVER】"

# 死因の軽量な区分 ([S3] 細分類は対象外)
CAUSE_COMBAT = "戦闘"  # turn 進行中の被害 (NPC・モンスター攻撃、状態異常など)
CAUSE_HUNGER = "飢え"  # 飢餓ダメージ
CAUSE_SELF = "自傷"  # 自分の行動に起因する減少 (詠唱反動、観客の投石など)
CAUSE_UNKNOWN = "不明"  # 上記以外の減少 (トラップなど)


@dataclass(frozen=True)
class RunSummary:
    """1 回の run の集計 (死亡時のスナップショット)"""

    depth: int
    kills: int
    devoured_skills: int
    turns: int
    cause: str
    elapsed_minutes: int

    def format_lines(self) -> list[str]:
        """ログと画面へ提示する行を返す"""
        return [
            f"到達深度: {self.depth}",
            f"撃破数: {self.kills}",
            f"喰い得スキル: {self.devoured_skills} 種",
            f"経過ターン: {self.turns}",
            f"経過時間: {self.elapsed_minutes} 分",
            f"死因: {self.cause}",
        ]
