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
