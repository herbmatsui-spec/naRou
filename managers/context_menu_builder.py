"""ContextMenuBuilder: builds context-sensitive action candidates.

Extracted from Engine.open_context_menu (game.py).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from constants import CAT_FOOD, TILE_WALL
from ui_fx_systems import ContextAction

if TYPE_CHECKING:
    from game import Engine


class ContextMenuBuilder:
    """Generates the list of context actions available at the player's position."""

    def build_actions(self, engine: "Engine") -> list[ContextAction]:
        actions: list[ContextAction] = []
        px, py = engine.player.x, engine.player.y

        # 1. 足元のアイテム
        ground_items = engine.entity_manager.get_items_at(px, py)
        for itm in ground_items:
            actions.append(ContextAction(f"拾う: {itm.display_name}", "pickup", "pickup_item", itm))
            if itm.category == CAT_FOOD:
                actions.append(
                    ContextAction(f"食べる: {itm.display_name}", "eat", "eat_ground", itm)
                )

        # 2. 隣接するNPC
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = px + dx, py + dy
            ent = engine.get_entity_at(nx, ny)
            if ent and ent not in (engine.player, engine.pet):
                actions.append(
                    ContextAction(f"話す / 調べる: {ent.name}", "talk", "talk_target", ent)
                )
            elif ent == engine.pet:
                actions.append(ContextAction("シエルの荷物を見る", "pet_inv", "open_pet_inv", ent))

        # 3. 祭壇
        if (px, py) == engine.altar_pos:
            actions.append(ContextAction("神に祈る", "pray", "pray", None))
            actions.append(ContextAction("祭壇に供物を捧げる", "offer", "offer_altar", None))

        # 4. 採取ポイント
        for node in engine.entity_manager.resource_nodes:
            if abs(node.x - px) + abs(node.y - py) <= 1 and not node.depleted:
                actions.append(
                    ContextAction(
                        f"採取する ({node.node_type})",
                        "harvest",
                        "harvest_resource",
                        node,
                    )
                )
                break

        # 5. 壁掘り
        can_mine = any(
            engine.game_map.is_in_bounds(px + dx, py + dy)
            and engine.game_map.tiles[px + dx][py + dy] == TILE_WALL
            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]
        )
        if can_mine:
            actions.append(ContextAction("隣の壁を掘る", "mine", "mine_wall", None))

        return actions
