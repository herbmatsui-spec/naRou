"""
Step-Based Tutorial System Module (T28 案3)
ステップ制チュートリアルの進行管理。

data/tutorial.yaml の 8 ステップ (移動→攻撃→拾う→深度解析X→喰らいV→呪文→
セーブ→ダンジョン探索開始) を順番に案内し、各ステップの達成条件
(condition) を検知して進行する。

条件検知は 3 系統:
  1. EventBus 購読   : 既存発行イベント (EVENT_ON_MOVE / entity_killed) を
                        購読して検知 (engine 側の変更ゼロ)。
  2. engine 通知     : engine.notify_tutorial_event() 経由の最小フック
                        (input_actions.py の動詞 / web_server.py)。
  3. フラグ監視      : engine 参照のフラグ・状態を update() で監視
                        (インベントリ差分 / セーブファイル mtime / 階層)。

進行状態は player.completed_tutorials に同期してセーブ/ロードで保持される
(既存 popup 型ガイド ui_fx_systems.TutorialManager とは ID 空間が分離)。
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from event_bus import EVENT_ON_MOVE, event_bus

logger = logging.getLogger(__name__)

# 既定のステップ定義ファイル (CWD 相対。tutorial_guides.yaml 等と同一規約)
DEFAULT_TUTORIAL_PATH = "data/tutorial.yaml"

# EventBus イベント名 → チュートリアル達成条件 ID の対応表
# (EVENT_ON_MOVE は packages/gameplay/package.py、entity_killed は
#  CombatSystem.publish_kill_event が既存で発行している)
BUS_EVENT_TO_CONDITION = {
    EVENT_ON_MOVE: "player_moved",
    "entity_killed": "enemy_defeated",
}

# engine 参照フラグ監視で検知する条件 ID
FLAG_CONDITIONS = ("item_picked", "scan_used", "save_used", "dungeon_descended")

# ダンジョン探索開始 (階段降下) 判定に使う最低階層
DUNGEON_DESCENT_LEVEL = 2


@dataclass
class TutorialStep:
    """チュートリアル 1 ステップ分の定義"""

    step_id: str
    title: str
    message: str
    condition: str
    reward_hint: str = ""


class TutorialManager:
    """ステップ制チュートリアルの進行管理 (T28 案3)

    現在ステップの保持、達成条件の判定、進行、完了判定、スキップを担う。
    Engine へは attach(engine) で接続し、Engine.update() から update(engine)、
    入力フックから notify_event() が呼ばれることを想定する。
    """

    def __init__(self, file_path: str = DEFAULT_TUTORIAL_PATH):
        self.file_path = file_path
        self.steps: list[TutorialStep] = []
        self.current_index: int = 0
        self.skipped: bool = False
        self.engine: Any = None
        self._subscribed: bool = False
        # フラグ監視用スナップショット (_on_step_enter で更新)
        self._inventory_items: list[Any] = []
        self._save_mtime: float | None = None
        self._load_steps()

    # ------------------------------------------------------------------
    # 定義ロード
    # ------------------------------------------------------------------
    def _load_steps(self) -> None:
        """data/tutorial.yaml からステップ定義を読み込む。"""
        import yaml

        self.steps = []
        if not os.path.exists(self.file_path):
            logger.warning("チュートリアル定義が見つかりません: %s", self.file_path)
            return
        try:
            with open(self.file_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for raw in data.get("tutorial_steps", []) or []:
                self.steps.append(
                    TutorialStep(
                        step_id=str(raw.get("step_id", "")),
                        title=str(raw.get("title", "")),
                        message=str(raw.get("message", "")),
                        condition=str(raw.get("condition", "")),
                        reward_hint=str(raw.get("reward_hint", "")),
                    )
                )
        except Exception:
            logger.exception("チュートリアル定義の読み込みに失敗: %s", self.file_path)
            self.steps = []

    # ------------------------------------------------------------------
    # Engine 接続
    # ------------------------------------------------------------------
    def attach(self, engine: Any) -> None:
        """Engine に接続し、保存済み進行の復元と EventBus 購読を行う。"""
        self.engine = engine
        self._sync_with_player(engine)
        self._subscribe_bus()
        self._on_step_enter(engine)

    def _subscribe_bus(self) -> None:
        """移動・撃破イベントを購読する (subscribe は同一コールバックを重複登録しない)。"""
        try:
            for bus_event, callback in self._bus_bindings():
                event_bus.subscribe(bus_event, callback)
            self._subscribed = True
        except Exception:
            logger.exception("チュートリアルのイベント購読に失敗")
            self._subscribed = False

    def _unsubscribe_bus(self) -> None:
        """EventBus 購読を解除する。"""
        try:
            for bus_event, callback in self._bus_bindings():
                event_bus.unsubscribe(bus_event, callback)
        except Exception:
            logger.exception("チュートリアルのイベント購読解除に失敗")
        self._subscribed = False

    def _bus_bindings(self) -> list[tuple[str, Any]]:
        """購読するイベントとコールバックの対応 (条件↔イベント対応表に基づく)。"""
        condition_to_callback = {
            "player_moved": self._on_player_move,
            "enemy_defeated": self._on_entity_killed,
        }
        bindings = []
        for bus_event, condition in BUS_EVENT_TO_CONDITION.items():
            callback = condition_to_callback.get(condition)
            if callback is not None:
                bindings.append((bus_event, callback))
        return bindings

    def _on_player_move(self, data: Any = None) -> None:
        """EVENT_ON_MOVE 購読コールバック (プレイヤー移動)。"""
        self.notify_event("player_moved")

    def _on_entity_killed(self, data: Any = None) -> None:
        """entity_killed 購読コールバック (撃破)。"""
        self.notify_event("enemy_defeated")

    def __setstate__(self, state: dict) -> None:
        """セーブデータ復元後の再接続フラグ初期化。

        EventBus への購読はグローバルシングルトン側に残るため、
        ロード直後の update() で張り直させる。
        """
        self.__dict__.update(state)
        self._subscribed = False

    # ------------------------------------------------------------------
    # 進行状態
    # ------------------------------------------------------------------
    @property
    def current_step(self) -> TutorialStep | None:
        """現在進行中のステップ (完了時は None)。"""
        if 0 <= self.current_index < len(self.steps):
            return self.steps[self.current_index]
        return None

    def current_condition(self) -> str:
        """現在ステップの達成条件 ID (ステップ未定義時は空文字)。"""
        step = self.current_step
        return step.condition if step else ""

    def is_completed(self) -> bool:
        """全ステップ完了 (またはスキップ) 済みか。"""
        return self.skipped or self.current_index >= len(self.steps)

    def completed_step_ids(self) -> list[str]:
        """達成済みステップの ID リスト (Web 表示用)。"""
        return [step.step_id for step in self.steps[: self.current_index]]

    def skip(self) -> None:
        """チュートリアルをスキップして全ステップ完了扱いにする。"""
        if self.is_completed():
            return
        self.skipped = True
        self.current_index = len(self.steps)
        engine = self.engine
        player = getattr(engine, "player", None)
        if player is not None and hasattr(player, "completed_tutorials"):
            player.completed_tutorials.update(step.step_id for step in self.steps)
        if engine is not None and hasattr(engine, "log"):
            engine.log(
                "📚【チュートリアル】スキップしました。操作は [?] ヘルプで確認できます。",
                (180, 220, 255),
                level="INFO",
            )

    # ------------------------------------------------------------------
    # 条件検知
    # ------------------------------------------------------------------
    def notify_event(self, event_name: str, engine: Any = None) -> bool:
        """達成イベント通知 (入力フック / engine ブリッジから呼ばれる)。

        現在ステップの条件と一致したら進行し True を返す。
        """
        if engine is not None:
            self.engine = engine
        if self.is_completed():
            return False
        step = self.current_step
        if step is None or step.condition != event_name:
            return False
        self._advance(engine or self.engine)
        return True

    def update(self, engine: Any) -> None:
        """毎フレームのフラグ監視 (Engine.update から呼ばれる)。

        セーブ/ロード後も動くよう engine 参照と EventBus 購読を自己修復し、
        player.completed_tutorials から進行を同期してからフラグ条件を判定する。
        """
        self.engine = engine
        if not self._subscribed:
            self._subscribe_bus()
        self._sync_with_player(engine)
        if self.is_completed():
            return
        self._check_flag_conditions(engine)

    def _check_flag_conditions(self, engine: Any) -> None:
        """engine 参照のフラグ・状態から達成条件を判定する。"""
        condition = self.current_condition()
        if condition not in FLAG_CONDITIONS:
            return
        met = False
        if condition == "item_picked":
            met = self._check_item_picked(engine)
        elif condition == "scan_used":
            # 《解析》実行で engine.last_scan_result が設定される
            # (skill_eater_system.execute_scan)。キー通知がない場合の補助判定。
            met = getattr(engine, "last_scan_result", None) is not None
        elif condition == "save_used":
            met = self._check_save_used()
        elif condition == "dungeon_descended":
            met = getattr(engine, "dungeon_level", 1) >= DUNGEON_DESCENT_LEVEL
        if met:
            self._advance(engine)

    def _check_item_picked(self, engine: Any) -> bool:
        """ステップ開始時と比べてインベントリに新しいアイテムが増えたか。"""
        inventory = getattr(engine, "inventory", None)
        if inventory is None:
            return False
        known = {id(itm) for itm in self._inventory_items}
        return any(id(itm) not in known for itm in inventory.items)

    def _check_save_used(self) -> bool:
        """セーブファイルの mtime がステップ開始時より新しくなったか。"""
        try:
            from save_system import SaveSystem

            mtime = os.path.getmtime(SaveSystem.SAVE_PATH)
        except (OSError, ImportError):
            return False
        return self._save_mtime is not None and mtime > self._save_mtime

    # ------------------------------------------------------------------
    # 進行処理
    # ------------------------------------------------------------------
    def _advance(self, engine: Any) -> None:
        """現在ステップを達成済みにして次ステップへ進む。"""
        step = self.current_step
        if step is None:
            return
        self.current_index += 1
        self._persist_progress(engine, step)
        self._on_step_enter(engine)
        self._log_progress(engine, step)
        if self.is_completed():
            self._log_completion(engine)

    def _persist_progress(self, engine: Any, step: TutorialStep) -> None:
        """達成ステップを player.completed_tutorials へ同期 (セーブ保持用)。"""
        player = getattr(engine, "player", None)
        if player is not None and hasattr(player, "completed_tutorials"):
            player.completed_tutorials.add(step.step_id)

    def _sync_with_player(self, engine: Any) -> None:
        """保存済み進行 (player.completed_tutorials) を復元する (巻き戻しはしない)。"""
        player = getattr(engine, "player", None)
        completed = getattr(player, "completed_tutorials", None)
        if not completed:
            return
        while (
            self.current_index < len(self.steps)
            and self.steps[self.current_index].step_id in completed
        ):
            self.current_index += 1
            self._on_step_enter(engine)

    def _on_step_enter(self, engine: Any) -> None:
        """ステップ開始時のフラグ監視スナップショットを取得する。"""
        self._inventory_items = []
        self._save_mtime = None
        if engine is None or self.is_completed():
            return
        condition = self.current_condition()
        if condition == "item_picked":
            inventory = getattr(engine, "inventory", None)
            if inventory is not None:
                # 強参照で保持して id 再利用による誤判定を防ぐ
                self._inventory_items = list(inventory.items)
        elif condition == "save_used":
            try:
                from save_system import SaveSystem

                self._save_mtime = os.path.getmtime(SaveSystem.SAVE_PATH)
            except (OSError, ImportError):
                self._save_mtime = None

    def _log_progress(self, engine: Any, step: TutorialStep) -> None:
        """✅ 進行ログと次ステップのガイドを表示する。"""
        if engine is None or not hasattr(engine, "log"):
            return
        engine.log(
            f"✅【チュートリアル {self.completed_count()}/{len(self.steps)}】"
            f"『{step.title}』達成！",
            (100, 255, 100),
            level="SUCCESS",
        )
        nxt = self.current_step
        if nxt is not None:
            engine.log(f"📖【次のステップ】{nxt.title}: {nxt.message}", (120, 220, 255))
            self._notify_popup(engine, nxt)
        elif not self.skipped:
            engine.log(
                "🎉【チュートリアル】全ステップ完了！ダンジョン探索を楽しんでください！",
                (255, 215, 0),
                level="SUCCESS",
            )

    def _log_completion(self, engine: Any) -> None:
        """完了時の最終ログ (スキップ時を除く)。"""
        if self.skipped or engine is None or not hasattr(engine, "log"):
            return
        engine.log(
            "🎉【チュートリアル】お疲れさま！基本操作はバッチリです。冒険の幕開け！",
            (255, 215, 0),
            level="SUCCESS",
        )
        self._notify_popup(
            engine,
            TutorialStep(
                step_id="tutorial_complete",
                title="チュートリアル完了",
                message="基本操作マスター！深層を目指して探索を続けよう。",
                condition="none",
                reward_hint="深層 B10F で輪廻転生が視野に入る",
            ),
        )

    def _notify_popup(self, engine: Any, step: TutorialStep) -> None:
        """通知マネージャー経由でポップアップ表示 (存在する場合のみ)。"""
        notifier = getattr(engine, "notification_manager", None)
        if notifier is None or not hasattr(notifier, "notify"):
            return
        try:
            notifier.notify(
                title=f"📚 チュートリアル: {step.title}",
                message=step.message,
                category="tutorial",
                color=(120, 220, 255),
                duration=40,
            )
        except Exception:
            logger.exception("チュートリアル通知の表示に失敗")

    def completed_count(self) -> int:
        """達成済みステップ数。"""
        return min(self.current_index, len(self.steps))

    # ------------------------------------------------------------------
    # Web 連携
    # ------------------------------------------------------------------
    def get_state(self) -> dict[str, Any]:
        """web_server._serialize_engine_state 用の状態スナップショット。"""
        step = self.current_step
        return {
            "enabled": bool(self.steps) and not self.is_completed(),
            "current_step": self.completed_count(),
            "total_steps": len(self.steps),
            "step_id": step.step_id if step else "",
            "title": step.title if step else "",
            "message": step.message if step else "",
            "reward_hint": step.reward_hint if step else "",
            "completed": self.is_completed() and not self.skipped,
            "skipped": self.skipped,
            "done_steps": self.completed_step_ids(),
        }
