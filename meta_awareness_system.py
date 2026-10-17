"""Meta awareness system module.

Handles Reader's Privilege (<原典閲覧>) and future prediction mechanics.
"""

from typing import Any, Dict, List, Optional


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

    def get_reading_depth(self) -> int:
        """Calculate reading depth based on awareness level.

        Depth tiers:
        - Level 1-2: Depth 1
        - Level 3-5: Depth 2
        - Level 6+: Depth 3
        """
        if self.awareness_level >= 6:
            return 3
        elif self.awareness_level >= 3:
            return 2
        return 1

    def trigger_template_scan(
        self,
        target: Any,
        presentation: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """Scan target for template flags above threshold.

        Args:
            target: Object with scenario_flags dict mapping archetype -> probability
            presentation: Optional presentation system to emit events

        Returns:
            List of detected archetypes with probability >= 0.5
        """
        flags = getattr(target, "scenario_flags", {})
        threshold = 0.5
        detected = []

        for archetype, probability in flags.items():
            if probability >= threshold:
                detected.append({"archetype": archetype, "probability": probability})

        if detected and presentation and hasattr(presentation, "add_event"):
            archetypes = ", ".join(d["archetype"] for d in detected)
            presentation.add_event(
                event_type="secret_discover",
                message=f"テンプレ反応検出: {archetypes}",
            )

        return detected

    def get_exploit_windows(self, template: Any, depth: int) -> List[Any]:
        """Get exploit windows filtered by reading depth.

        Args:
            template: Template object with exploit_windows list
            depth: Reading depth (1-3)

        Returns:
            List of exploit windows up to the given depth
        """
        windows = getattr(template, "exploit_windows", [])
        return windows[:depth]

    def apply_deep_read_cost(self, player: Any, depth: int) -> None:
        """Apply karma and exposure cost for deep reading.

        Args:
            player: Player entity with karma_law_chaos and template_exposure attributes
            depth: Reading depth (cost only applied for depth >= 3)
        """
        if depth < 3:
            return

        # Apply cost: -1 karma law/chaos, +1 template exposure
        if hasattr(player, "karma_law_chaos"):
            player.karma_law_chaos -= 1
        if hasattr(player, "template_exposure"):
            player.template_exposure += 1
