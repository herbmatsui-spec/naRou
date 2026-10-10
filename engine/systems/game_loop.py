"""
Game Loop - Handles world advancement, turn processing, and run summary extracted from Engine.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from constants import COLOR_GOLD_YELLOW, GameState
from run_history import RunHistoryStore
from run_summary import (
    CAUSE_COMBAT,
    CAUSE_HUNGER,
    CAUSE_UNKNOWN,
    GAME_OVER_TITLE,
    RunSummary,
)
from sound_manager import SoundManager

if TYPE_CHECKING:
    from game import Engine

logger = logging.getLogger(__name__)


class GameLoopHandler:
    """Handles world advancement, death/run-end state, and run summary/history."""

    def __init__(self, engine: "Engine"):
        self.engine = engine

    def _end_run_if_player_dead(self) -> bool:
        """死亡を判定して run を終了させる (docs/compose/spec/run-end-state.md [S2.1])

        判定を turn 進行の入口に置くことで、攻撃元の種類に依存せず死を捕捉する。
        既に GAME_OVER のときは何もせず True を返す (冪等)。
        """
        engine = self.engine
        if engine.game_state_machine.current == "game_over":
            return True
        if engine.player.hp > 0:
            return False

        # 統一死亡ハンドラを経由して GAME_OVER へ遷移
        self._on_player_death()
        engine.run_summary = self._build_run_summary()
        self._present_run_summary(engine.run_summary)
        self._record_run_history(engine.run_summary)
        return True

    def _record_harm_cause(self, cause: str) -> None:
        """観測した死因を、その観測時点の HP と対で記録する"""
        engine = self.engine
        engine._harm_cause = cause
        engine._harm_cause_hp = engine.player.hp

    def _observed_harm_cause(self) -> str:
        """記録した死因を返す。記録後に原因不明のダメージを受けていれば CAUSE_UNKNOWN にする

        死因の観測点は turn 進行中の `advance_world` と自分の行動の 2 か所だけ
        ([S3] 細分類は対象外)。トラップのように `_harm_cause` を触らないダメージは
        観測点の間で発生するため、前の turn の観測を死因として引きずると順序依存の
        表示になる。記録した時点から HP が変わっていれば、致命的になるまでの間に
        原因を観測できていないので、観測の無い死として扱う。
        旧セーブは __init__ を通らず pickle 復元されるため getattr で読む。
        """
        engine = self.engine
        if getattr(engine, "_harm_cause_hp", None) != engine.player.hp:
            return CAUSE_UNKNOWN
        return getattr(engine, "_harm_cause", CAUSE_UNKNOWN)

    def _build_run_summary(self) -> RunSummary:
        """run summary を組み立てる。値は既存の state から引く ([S2.1] 追跡機構を増やさない)"""
        engine = self.engine
        clock = engine.time_system.world_clock
        # 件数と id は同じ state から同時に引く。別々に数えると必ずずれる。
        skills = engine.game_state_data.world_a_data.get("skills", ())
        devoured = tuple(str(skill_id) for skill_id in skills)
        return RunSummary(
            depth=engine.dungeon_level,
            kills=sum(engine.player.kill_counts.values()),
            devoured_skills=len(devoured),
            turns=engine.turns,
            cause=self._observed_harm_cause(),
            elapsed_minutes=clock.total_ticks // clock.config.ticks_per_minute,
            devoured_skill_ids=devoured,
        )

    def _present_run_summary(self, summary: RunSummary) -> None:
        """run summary をログへ提示する (画面描画は render の game_over 分岐)"""
        engine = self.engine
        engine.log(GAME_OVER_TITLE, (255, 50, 50), level="WARNING")
        for line in summary.format_lines():
            engine.log(line, COLOR_GOLD_YELLOW, level="WARNING")

    def _record_run_history(self, summary: RunSummary) -> None:
        """終了した run を履歴へ書き出す ([S2.1] 次回起動で提示する)

        死亡の処理を止めないため、書けなかった旨をログに留めて飲み込む。
        履歴は補助情報であり、run の終了そのものを失敗させない。
        """
        engine = self.engine
        try:
            RunHistoryStore().record(summary)
        except Exception:
            logger.exception("Failed to record run history: %s", summary)
            engine.log(
                "【記録失敗】今回の戦績を履歴に残せませんでした", (255, 160, 80), level="WARNING"
            )

    def _present_run_history(self) -> None:
        """前回の run の記録を起動時のログへ提示する ([S2.1])

        新しい UI は作らず、起動時に既に流れているログへ並べる。
        履歴が無い (初回起動) / 読めない (破損) 場合も store 側が理由を文面にする。
        """
        engine = self.engine
        for line in RunHistoryStore().startup_lines():
            engine.log(line, COLOR_GOLD_YELLOW, level="INFO")

    def _on_player_death(self) -> None:
        """プレイヤー死亡時の統一ハンドラ。

        - GameStateMachine 経由で "game_over" へ遷移
        - ログ出力
        - PersistenceManager があればセーブ
        """
        engine = self.engine
        engine.game_state_machine.transition("game_over")
        # 旧互換プロパティも更新 (render 等が参照するため)
        engine.game_state_data.current_state = GameState.GAME_OVER
        engine.game_state_data.game_state = "game_over"
        engine.log("【死亡】力尽きた……", (255, 30, 30), level="ERROR")
        # PersistenceManager があれば自動セーブ（死の直前状態を記録）
        try:
            from managers.persistence_manager import PersistenceManager

            PersistenceManager().save(engine)
        except Exception:
            pass

    def advance_world(self) -> None:
        """速度Tick制による全NPCターン処理 (GameplayPackage 経由)

        死亡判定を turn 進行の入口に集約する ([S2.1])。GAME_OVER 後は世界も turn も進めない。
        """
        engine = self.engine
        if self._end_run_if_player_dead():
            return

        # 死因の区分は turn 進行中の観測点で行う ([S3] 細分類は対象外)
        hp_before = engine.player.hp
        engine.gameplay_loop(engine.kernel, engine).advance_world()
        if engine.player.hp < hp_before:
            self._record_harm_cause(CAUSE_HUNGER if engine.survival.hunger <= 0 else CAUSE_COMBAT)

        # 以下は Engine 固有の処理（自然回復、世界ニュース、オートセーブ等）
        # 自然回復は SurvivalSystem.pass_turn で実行済み（ステップ18）
        # プレイヤー出血状態をチェック
        player_bleeding = any(
            getattr(e, "effect_type", getattr(e, "type", getattr(e, "name", ""))) == "bleeding"
            for e in engine.player.status_effects
        )

        # 勝利条件チェック (Step 19)
        if engine.check_win_condition():
            return

        # 動的サウンドスケープ: 危機状態のBGM判定 (Step 7.3)
        if hasattr(engine, "player") and engine.player:
            SoundManager.bgm_manager.check_crisis_trigger(engine.player.hp, engine.player.max_hp)

        # オートセーブ: 50ターンごと (ステップ71) — PersistenceManager に委譲
        from managers.persistence_manager import PersistenceManager

        PersistenceManager().autosave_if_due(engine)

        # === 世界ニュース・称号・ジョブ・スキルツリー・ギルド (WorldNewsManager に委譲) ===
        from managers.world_news_manager import WorldNewsManager

        WorldNewsManager().advance(engine)

        # === 派閥影響力定期変動 (FactionManager に委譲) ===
        from managers.faction_manager import FactionManager

        FactionManager().update_influence(engine)

        # === ペット絆度 & 進化チェック (PetBondManager に委譲) ===
        from managers.pet_bond_manager import PetBondManager

        PetBondManager().update_turn_bond(engine)

        # 浮遊テキスト & パーティクル & 通知 & 画面シェイクの更新 (Phase 6, 7, UX強化)
        engine.floating_texts = [ft for ft in engine.floating_texts if ft.update()]
        engine.particles = [pt for pt in engine.particles if pt.update()]
        if hasattr(engine, "notification_manager"):
            engine.notification_manager.update()
        if hasattr(engine, "screen_shake"):
            engine.screen_shake.update()

        engine.game_map.compute_fov(engine.player.x, engine.player.y, radius=8)

    def update(self, delta_time: float = 1.0) -> None:
        """ゲームロジック更新 (描画を行わない)"""
        engine = self.engine
        # ターン処理
        if hasattr(engine, "turn_queue") and engine.turn_queue:
            engine.turn_queue.process(engine, delta_time)

        # システム更新
        if hasattr(engine, "systems_coordinator"):
            engine.systems_coordinator.update_all(engine, delta_time)

        # FX更新
        if hasattr(engine, "fx_manager"):
            engine.fx_manager.update(delta_time)

        # チュートリアル更新
        if hasattr(engine, "tutorial_manager"):
            engine.tutorial_manager.update(delta_time)

        # 通知更新
        if hasattr(engine, "notification_manager"):
            engine.notification_manager.update(delta_time)

        # アニメーションタイル更新
        if hasattr(engine, "game_map"):
            engine.game_map.update_animations(delta_time)

        # turn counter は advance_world() のみで増やす (vsync の毎フレーム呼び出しでは進めない)
