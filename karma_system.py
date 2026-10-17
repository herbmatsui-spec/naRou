"""
カーマシステム

秩序↔混沌 / 善↔悪 の二軸カルマを管理し、行動イベントの反映と
段階 (大善/善/中立/悪/大悪) ごとの実効的影響を提供する (T39 案C)。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
import os
from dataclasses import dataclass, field
from typing import Any

import yaml


@dataclass
class KarmaStage:
    """カルマ段階定義 (善悪値の区間と実効的影響)"""

    id: str
    name: str
    min_good_evil: int  # この段階に含まれる最小の善悪値 (降順で最初に満たす段階が適用)
    shop_price_modifier: float  # 店価格倍率 (1.0 = 変動なし, 小さいほど割引)
    npc_reaction: str  # 段階到達時に表示する NPC の反応説明
    epilogue_flag: str  # エピローグ分岐フラグ
    color: tuple[int, int, int] = (200, 200, 200)


# 段階境界: 大善 >= 50 / 善 20..49 / 中立 -19..19 / 悪 -49..-20 / 大悪 <= -50
DEFAULT_STAGES: list[KarmaStage] = [
    KarmaStage(
        id="saint",
        name="大善",
        min_good_evil=50,
        shop_price_modifier=0.8,
        npc_reaction="人々は敬意をもってあなたを見つめ、店は笑顔で安くしてくれる。",
        epilogue_flag="epilogue_saint",
        color=(120, 255, 160),
    ),
    KarmaStage(
        id="good",
        name="善",
        min_good_evil=20,
        shop_price_modifier=0.9,
        npc_reaction="多くの人があなたに好意を抱いている。",
        epilogue_flag="epilogue_good",
        color=(160, 220, 255),
    ),
    KarmaStage(
        id="neutral",
        name="中立",
        min_good_evil=-19,
        shop_price_modifier=1.0,
        npc_reaction="人々はいつも通りに接してくる。",
        epilogue_flag="epilogue_neutral",
        color=(200, 200, 200),
    ),
    KarmaStage(
        id="evil",
        name="悪",
        min_good_evil=-49,
        shop_price_modifier=1.15,
        npc_reaction="人々はあなたを警戒し、店は疑いの目で値をつり上げる。",
        epilogue_flag="epilogue_evil",
        color=(255, 170, 120),
    ),
    KarmaStage(
        id="demon",
        name="大悪",
        min_good_evil=-50,
        shop_price_modifier=1.3,
        npc_reaction="誰もがあなたを忌み嫌い、衛兵が指名手配の目で追う。",
        epilogue_flag="epilogue_demon",
        color=(255, 90, 90),
    ),
]


def _parse_stages(raw: Any) -> list[KarmaStage]:
    """YAML の stages セクションから KarmaStage リストを生成 (失敗時は既定値)。"""
    try:
        stages = [
            KarmaStage(
                id=str(d["id"]),
                name=str(d["name"]),
                min_good_evil=int(d["min_good_evil"]),
                shop_price_modifier=float(d.get("shop_price_modifier", 1.0)),
                npc_reaction=str(d.get("npc_reaction", "")),
                epilogue_flag=str(d.get("epilogue_flag", "")),
                color=tuple(d.get("color", (200, 200, 200))),
            )
            for d in raw
        ]
        return stages if stages else list(DEFAULT_STAGES)
    except Exception:
        logger.exception("カルマ段階定義の解析に失敗したため既定値を使用します")
        return list(DEFAULT_STAGES)


@dataclass
class KarmaData:
    """カーマデータクラス"""

    id: str
    name: str
    description: str
    alignment_ranges: dict[str, dict[str, Any]]
    actions: dict[str, dict[str, int]]
    reincarnation_effects: dict[str, Any]
    stages: list[KarmaStage] = field(default_factory=lambda: list(DEFAULT_STAGES))


class KarmaRegistry:
    """カーマレジストリ（シングルトン的）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data: dict[str, KarmaData] = {}
        return cls._instance

    def load(self, path: str = "data/karma.yaml") -> None:
        """YAMLファイルからカーマデータを読み込み"""
        self._data.clear()
        alignment_ranges = {
            "law_chaos": {"range": [-100, 100], "neutral": 0},
            "good_evil": {"range": [-100, 100], "neutral": 0},
            "exposure": {"range": [0, 100], "neutral": 0},
        }
        actions = {
            "help_innocent": {"law_chaos": 5, "good_evil": 10},
            "defeat_monster": {"law_chaos": 0, "good_evil": 1},
            "donate_to_temple": {"law_chaos": 1, "good_evil": 2},
            "steal": {"law_chaos": -1, "good_evil": -2},
            "murder_innocent": {"law_chaos": -2, "good_evil": -5},
            # T39 案C: イベントフックから参照される善悪行動
            "attack_innocent": {"law_chaos": -1, "good_evil": -2},
            "attack_gwen": {"law_chaos": -3, "good_evil": -15},
            "relief_wounded": {"law_chaos": 1, "good_evil": 2},
            "spare_enemy": {"law_chaos": 1, "good_evil": 2},
            "template_deep_read": {"law_chaos": -1, "good_evil": 0, "exposure": 1},
            "template_intervene_t1": {"law_chaos": 0, "good_evil": 0, "exposure": 1},
            "template_intervene_t2": {"law_chaos": -2, "good_evil": -2, "exposure": 3},
            "template_intervene_t3": {"law_chaos": -5, "good_evil": -5, "exposure": 10},
        }
        stages = list(DEFAULT_STAGES)
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    raw = yaml.safe_load(f)
                if raw and "karma" in raw:
                    k = raw["karma"]
                    if "alignment" in k:
                        alignment_ranges = k["alignment"]
                    if "actions" in k:
                        actions.update(k["actions"])
                    if "stages" in k:
                        stages = _parse_stages(k["stages"])
            except Exception:
                logger.exception("Unhandled exception")

        default_data = KarmaData(
            id="default",
            name="デフォルトカーマ",
            description="基本的なカーマシステム",
            alignment_ranges=alignment_ranges,
            actions=actions,
            reincarnation_effects={"stat_bonus": 5},
            stages=stages,
        )
        self._data["default"] = default_data

    def all(self) -> dict[str, KarmaData]:
        """全カーマデータを取得"""
        return self._data.copy()

    def get(self, karma_id: str = "default") -> KarmaData | None:
        """特定のカーマデータを取得"""
        return self._data.get(karma_id or "default")


# グローバルレジストリインスタンス
REGISTRY = KarmaRegistry()


class KarmaManager:
    """カーマ管理クラス"""

    def __init__(self, registry: KarmaRegistry | None = None):
        self.registry = registry or REGISTRY

    def update_karma(self, player: Any, action: str, amount: int = 1) -> tuple[int, int, int]:
        """カーマを更新（露見度も含む）"""
        karma_data = self.registry.get("default")
        if not karma_data:
            return (
                getattr(player, "karma_law_chaos", 0),
                getattr(player, "karma_good_evil", 0),
                getattr(player, "template_exposure", 0),
            )

        action_data = karma_data.actions.get(action, {"law_chaos": 0, "good_evil": 0, "exposure": 0})
        law_chaos_change = action_data.get("law_chaos", 0) * amount
        good_evil_change = action_data.get("good_evil", 0) * amount
        exposure_change = action_data.get("exposure", 0) * amount

        player.karma_law_chaos += law_chaos_change
        player.karma_good_evil += good_evil_change
        player.template_exposure = getattr(player, "template_exposure", 0) + exposure_change

        # 範囲制限
        law_chaos_range = karma_data.alignment_ranges.get("law_chaos", {}).get("range", [-100, 100])
        good_evil_range = karma_data.alignment_ranges.get("good_evil", {}).get("range", [-100, 100])
        exposure_range = karma_data.alignment_ranges.get("exposure", {}).get("range", [0, 100])

        player.karma_law_chaos = max(
            law_chaos_range[0], min(law_chaos_range[1], player.karma_law_chaos)
        )
        player.karma_good_evil = max(
            good_evil_range[0], min(good_evil_range[1], player.karma_good_evil)
        )
        player.template_exposure = max(
            exposure_range[0], min(exposure_range[1], player.template_exposure)
        )
        return player.karma_law_chaos, player.karma_good_evil, player.template_exposure

    def get_stage(self, good_evil: int) -> KarmaStage:
        """善悪値からカルマ段階を判定する (降順で最初に条件を満たす段階)。"""
        karma_data = self.registry.get("default")
        stages = karma_data.stages if karma_data and karma_data.stages else DEFAULT_STAGES
        for stage in sorted(stages, key=lambda s: s.min_good_evil, reverse=True):
            if good_evil >= stage.min_good_evil:
                return stage
        return stages[-1] if stages else DEFAULT_STAGES[-1]

    @staticmethod
    def get_stage_name(good_evil: int) -> str:
        """善悪値に対応する段階名を返す (Web配信などの軽量参照用)。"""
        return KarmaManager().get_stage(good_evil).name

    def get_shop_price_modifier(self, good_evil: int) -> float:
        """カルマ段階に応じた店価格倍率を返す (善: 割引, 悪: 割増)。"""
        return self.get_stage(good_evil).shop_price_modifier

    def get_npc_reaction(self, good_evil: int) -> str:
        """カルマ段階に応じたNPCの反応説明を返す。"""
        return self.get_stage(good_evil).npc_reaction

    def apply_action(
        self, player: Any, action: str, engine: Any = None, amount: int = 1
    ) -> KarmaStage:
        """行動イベントをカルマへ反映し、段階変化と実効的影響を適用する。

        combat_system / gameplay / pet_system / entity_system の各イベントフック
        から呼ばれる。update_karma() に加え以下を行う:
        - 善悪値を survival.karma (スカラー版カルマ) へ同期
        - 段階名を player.karma_stage へ、エピローグ分岐フラグを
          player.epilogue_karma_flag へ設定
        - 段階が変化した場合はログで通知 (TCOD/Web 共通の message_log 経由)
        """
        old_stage = self.get_stage(getattr(player, "karma_good_evil", 0) or 0)
        self.update_karma(player, action, amount)
        new_stage = self.get_stage(player.karma_good_evil)

        survival = getattr(engine, "survival", None) if engine is not None else None
        if survival is not None and hasattr(survival, "karma"):
            survival.karma = player.karma_good_evil

        player.karma_stage = new_stage.name
        player.epilogue_karma_flag = new_stage.epilogue_flag

        if new_stage.id != old_stage.id:
            self._notify_stage_change(old_stage, new_stage, engine)
        return new_stage

    def _notify_stage_change(
        self, old_stage: KarmaStage, new_stage: KarmaStage, engine: Any
    ) -> None:
        """段階変化をログへ通知する (悪化時は WARNING レベル)。"""
        level = "INFO" if new_stage.min_good_evil >= 0 else "WARNING"
        msg = f"【カルマ】{old_stage.name} → {new_stage.name}。{new_stage.npc_reaction}"
        log = getattr(engine, "log", None) if engine is not None else None
        if callable(log):
            log(msg, new_stage.color, level=level)

    def get_karma_bonuses(self, player: Any) -> dict[str, Any]:
        """カーマボーナスを取得"""
        return {"stat_bonus": 5}
