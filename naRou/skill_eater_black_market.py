"""
Shim module for the black market system.
It re‑exports the logic class and mixes in UI helpers defined in
``naRou.skill_eater.black_market.logic`` and ``naRou.skill_eater.black_market.ui``.
The original monolithic implementation has been split; this shim preserves the
original import path used by the rest of the codebase.
"""

# Import the pure‑logic class
from naRou.skill_eater.black_market.logic import BlackMarketNetwork as _LogicNetwork

# Import UI helper functions
from naRou.skill_eater.black_market.ui import (
    format_location_for_ui,
    play_location_enter,
    play_location_exit,
    play_buy_effect,
    play_sell_effect,
    play_route_establish_effect,
    play_route_profit_effect,
    play_route_detected_effect,
    play_route_abandon_effect,
    play_price_surge_effect,
    play_heat_warning_effect,
    play_caravan_encounter_effect,
    play_location_unlock_effect,
    play_location_upgrade_effect,
)

# Create a subclass that adds UI methods delegating to the imported helpers.
class BlackMarketNetwork(_LogicNetwork):
    def format_location_for_ui(self, location_id: str) -> dict:
        return format_location_for_ui(self, location_id)

    def play_location_enter(self, location_id: str) -> None:
        play_location_enter(self, location_id)

    def play_location_exit(self, location_id: str) -> None:
        play_location_exit(self, location_id)

    def play_buy_effect(self, item, quantity: int = 1, discount: float = 0) -> None:
        play_buy_effect(self, item, quantity, discount)

    def play_sell_effect(self, item, quantity: int, total_price: int, is_illegal: bool) -> None:
        play_sell_effect(self, item, quantity, total_price, is_illegal)

    def play_route_establish_effect(self, origin_name: str, dest_name: str, risk_level: int) -> None:
        play_route_establish_effect(self, origin_name, dest_name, risk_level)

    def play_route_profit_effect(self, route_id: str, profit: int, total_profit: int) -> None:
        play_route_profit_effect(self, route_id, profit, total_profit)

    def play_route_detected_effect(self, route_id: str, heat_increase: int, loss: int) -> None:
        play_route_detected_effect(self, route_id, heat_increase, loss)

    def play_route_abandon_effect(self, route_id: str, recovered: int) -> None:
        play_route_abandon_effect(self, route_id, recovered)

    def play_price_surge_effect(self, item_name: str, change_percent: float, current_price: int) -> None:
        play_price_surge_effect(self, item_name, change_percent, current_price)

    def play_heat_warning_effect(self) -> None:
        play_heat_warning_effect(self)

    def play_caravan_encounter_effect(self, district: str, position: tuple[int, int]) -> None:
        play_caravan_encounter_effect(self, district, position)

    def play_location_unlock_effect(self, location_name: str) -> None:
        play_location_unlock_effect(self, location_name)

    def play_location_upgrade_effect(self, location_name: str, new_level: int) -> None:
        play_location_upgrade_effect(self, location_name, new_level)
