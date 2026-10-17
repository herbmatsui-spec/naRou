"""FactionManager: encapsulates faction reputation and influence updates.

Extracted from Engine._on_kill and Engine.advance_world (game.py).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ecs.entity import Entity
    from game import Engine


class FactionManager:
    """Updates faction reputation on kills, influence over time, and war lifecycle."""

    def update_kill_reputation(self, engine: "Engine", entity: "Entity") -> None:
        """Increment kingdom reputation when the player kills an enemy (Step 63)."""
        if hasattr(engine.player, "faction_reputation"):
            engine.player.faction_reputation["kingdom_garde"] = (
                engine.player.faction_reputation.get("kingdom_garde", 0) + 1
            )
        # T36 案A: 撃破を派閥戦争の戦況へ反映
        self._record_war_kill(engine, entity)

    def update_influence(self, engine: "Engine") -> None:
        """Periodic faction influence fluctuation (Step 62) and war progression."""
        # T36 案A: 派閥戦争の進行 (開戦判定/ゲージ変動/終戦処理)
        self.update_wars(engine)

        from constants import FACTION_INFLUENCE_INTERVAL

        if engine.turns % FACTION_INFLUENCE_INTERVAL == 0:
            registry = getattr(engine, "faction_war_registry", None)
            manager = getattr(engine, "faction_war_manager", None)
            if registry and manager:
                for fid in registry.all():
                    chg = manager.calculate_influence_change(fid, engine)
                    manager.apply_influence_effects(fid, chg)

    # ------------------------------------------------------------------
    # 派閥戦争連携 (T36 案A)
    # ------------------------------------------------------------------

    def update_wars(self, engine: "Engine") -> None:
        """派閥戦争を進行させ、開戦/終結イベントをログと FX へ反映する (T36 案A)"""
        war_manager = self._get_war_manager(engine)
        if war_manager is None:
            return
        events = war_manager.progress_wars(
            getattr(engine, "turns", 0), getattr(engine, "player", None)
        )
        if not isinstance(events, list):
            return
        for ev in events:
            self._present_war_event(engine, ev)

    def _record_war_kill(self, engine: "Engine", entity: "Entity") -> None:
        """撃破を派閥戦争の戦況へ反映する (T36 案A プレイヤー影響フック)

        - 派閥 NPC の撃破: その派閥の対戦側にゲージが傾く (ボス級は拠点攻防級の戦果)
        - 派閥外の敵対モンスターの撃破: プレイヤー支持派閥の戦果として加算
        - 非敵対 (is_hostile=False) の対象は戦果に含めない
        """
        war_manager = self._get_war_manager(engine)
        if war_manager is None:
            return
        victim_faction = getattr(entity, "faction_id", None)
        if victim_faction:
            boss = bool(
                getattr(entity, "is_boss", False) or getattr(entity, "unique_boss", False)
            )
            war_manager.record_kill(victim_faction, boss=boss)
            if getattr(entity, "is_hostile", None) is False:
                # 非武装勢力への手出しは悪行として戦況を削ぐ
                war_manager.record_deed(victim_faction, good=False, amount=1)
            return
        if getattr(entity, "is_hostile", True) is False:
            return
        player = getattr(engine, "player", None)
        if player is None or not hasattr(player, "faction_reputation"):
            return
        patron_id = self._get_patron_faction(player, war_manager)
        if patron_id:
            war_manager.record_deed(patron_id, good=True, amount=1)

    @staticmethod
    def _get_patron_faction(player: "Entity", war_manager: Any) -> str | None:
        """プレイヤーが最も評判の高い派閥 ID を返す (評判未登録なら None)"""
        best_id: str | None = None
        best_val = 0
        for fid, val in dict(player.faction_reputation).items():
            if war_manager.registry.get(fid) is None:
                continue
            if val > best_val:
                best_id, best_val = fid, val
        return best_id

    @staticmethod
    def _get_war_manager(engine: "Engine") -> Any | None:
        """Kernel から派閥戦争マネージャーを取得する (未登録時は None)"""
        kernel = getattr(engine, "kernel", None)
        if kernel is None or not kernel.has_system("faction_war_manager"):
            return None
        return kernel.get_system("faction_war_manager")

    def _present_war_event(self, engine: "Engine", ev: Any) -> None:
        """戦争イベントをログ / FloatingText / 通知へ反映する"""
        if not isinstance(ev, dict):
            return
        message = ev.get("message", "")
        color = ev.get("color", (230, 230, 230))
        level = ev.get("level", "INFO")
        log = getattr(engine, "log", None)
        if callable(log):
            log(message, color, level=level)
            for line in ev.get("effects", []):
                log(str(line), (220, 220, 220))
        floating = ev.get("floating_text")
        player = getattr(engine, "player", None)
        if floating and player is not None:
            from ui_fx_systems import FloatingText

            engine.floating_texts.append(
                FloatingText(floating[0], player.x, player.y - 1.0, floating[1])
            )
