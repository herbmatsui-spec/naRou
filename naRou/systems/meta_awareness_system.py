"""Meta awareness system module.

Handles Reader's Privilege (<原典閲覧>) and future prediction mechanics.
"""

from typing import Any, Dict, Optional


class MetaAwarenessSystem:
    """Core meta-awareness system providing foresight and future branch prediction."""

    _instance: Optional["MetaAwarenessSystem"] = None

    @classmethod
    def get_instance(cls) -> "MetaAwarenessSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self.awareness_level: int = 1

    def trigger_flash_forward(self, scenario_id: str) -> Dict[str, Any]:
        """Generates future prediction branch data."""
        timeline_data = self.get_worst_future_timeline(scenario_id)
        return {
            "scenario_id": scenario_id,
            "prediction_type": "WORST_CASE_TIMELINE",
            "active": True,
            "timeline": timeline_data,
        }

    def get_worst_future_timeline(self, scenario_id: str) -> Dict[str, Any]:
        """Returns textual data of catastrophic timeline if firing was avoided."""
        return {
            "timeline_id": "TIMELINE_MIDAS_EMPLOYEE_DEATH",
            "warning_level": "FATAL_100%",
            "forecast_events": [
                "DAY 3: 残業時間200時間突破。《解析》の過剰酷使で脳神経焼き切れ。",
                "DAY 14: スキル搾取契約発動。保有魔力をすべて吸い出される。",
                "DAY 30: 完全なHusk（廃人化）。スラム廃棄処分。",
            ],
            "optimal_avoidance_action": "ACCEPT_DISMISSAL_AND_ESCAPE",
        }

    # --- Template intervention methods (Phase B) ---

    def trigger_template_scan(
        self, target: Any, presentation: Any = None
    ) -> list[dict[str, Any]]:
        """Scan target for template scenario flags. Returns list of detected templates."""
        flags = getattr(target, "scenario_flags", {})
        detected = []
        for archetype, weight in flags.items():
            if weight >= 0.3:  # threshold
                detected.append({"archetype": archetype, "weight": weight})
        if presentation and detected:
            # Emit detection event
            archetypes = ", ".join(d["archetype"] for d in detected)
            presentation.add_event(
                emote_file="emote_exclamations.png",
                audio_file="bookFlip3.ogg",
                message=f"《原典閲覧》テンプレ反応検出: {archetypes}",
                duration_ms=1500,
                event_type="secret_discover",
            )
        return detected

    def get_reading_depth(self) -> int:
        """Return reading depth based on awareness_level: 1=surface, 2=branches, 3=full."""
        if self.awareness_level >= 6:
            return 3
        elif self.awareness_level >= 3:
            return 2
        return 1

    def get_exploit_windows(self, template: Any, depth: int) -> list[Any]:
        """Return exploit windows available at given reading depth."""
        windows = getattr(template, "exploit_windows", [])
        return [w for w in windows if w.tier <= depth]

    def apply_deep_read_cost(self, player: Any, depth: int) -> None:
        """Apply karma/exposure cost for deep reading."""
        if depth >= 3:
            # Cost: law_chaos -1, exposure +1
            from naRou.systems.karma_system import KarmaManager

            km = KarmaManager()
            km.update_karma(player, "template_deep_read", 1)
