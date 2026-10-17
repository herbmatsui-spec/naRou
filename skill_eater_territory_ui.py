"""
skill_eater_territory_ui.py
Aの世界（スキル喰い） テリトリーシステム UI統合
Phase 6: UI・可視化・統合 (Steps 63-72)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skill_eater_territory_system import (
    TERRITORY_ACTION_COSTS,
    District,
    DynamicEventType,
    TerritoryActionType,
    TerritoryController,
    TerritoryState,
)

FACTION_COLORS = {
    "midas": (220, 50, 50),
    "resistance": (50, 100, 220),
    "bank": (220, 180, 30),
    "broker": (180, 50, 180),
    "neutral": (120, 120, 120),
    "player": (50, 200, 100),
}

FACTION_ICONS = {
    "midas": "🏢",
    "resistance": "⚔️",
    "bank": "🏦",
    "broker": "💎",
    "neutral": "⚪",
    "player": "👤",
}

DISTRICT_TYPE_ICONS = {
    "industrial": "🏭",
    "slums": "🏚️",
    "corporate": "🏢",
    "underground": "🕳️",
    "residential": "🏠",
    "research": "🔬",
    "government": "🏛️",
    "park": "🌳",
    "port": "🚢",
    "abandoned": "🏚️",
    "smuggler": "🚤",
    "temple": "⛩️",
    "ruins": "🗿",
}


@dataclass
class TerritoryMapRenderer:
    territory: TerritoryState

    def get_district_display_info(self, district: District) -> dict[str, Any]:
        color = FACTION_COLORS.get(district.controlling_faction, FACTION_COLORS["neutral"])
        icon = FACTION_ICONS.get(district.controlling_faction, FACTION_ICONS["neutral"])

        dtype = self._guess_district_type(district.id)
        type_icon = DISTRICT_TYPE_ICONS.get(dtype, "📍")

        return {
            "id": district.id,
            "name": district.name,
            "faction": district.controlling_faction,
            "faction_color": color,
            "faction_icon": icon,
            "type_icon": type_icon,
            "stability": district.stability,
            "stability_bar": self._stability_bar(district.stability),
            "resource_output": district.resource_output,
            "defense_level": district.defense_level,
            "has_shop": district.exclusive_shop_unlocked,
            "has_dungeon": district.hidden_dungeon_entrance,
            "turn_controlled": district.turn_controlled,
            "sabotage_remaining": district.sabotage_remaining,
            "adjacent_count": len(district.adjacent_districts),
        }

    def _guess_district_type(self, district_id: str) -> str:
        for key in DISTRICT_TYPE_ICONS:
            if key in district_id.lower():
                return key
        return "default"

    def _stability_bar(self, stability: int) -> str:
        filled = stability // 10
        empty = 10 - filled
        return "█" * filled + "░" * empty

    def render_text_map(self) -> str:
        lines = ["=== 勢力図 ===", ""]
        for district in sorted(self.territory.districts.values(), key=lambda d: d.id):
            info = self.get_district_display_info(district)
            stability_color = self._stability_color(info["stability"])
            lines.append(
                f"{info['type_icon']} {info['name']} ({info['id']})"
            )
            lines.append(
                f"  {info['faction_icon']} 派閥: {info['faction']} | 安定度: {info['stability_bar']} {info['stability']}% | "
                f"資源: {info['resource_output']}/T | 防御: {info['defense_level']}"
            )
            if info["has_shop"]:
                lines.append("  🏪 専用ショップ解放済み")
            if info["has_dungeon"]:
                lines.append("  🏰 隠しダンジョン入口発見済み")
            if info["sabotage_remaining"] > 0:
                lines.append(f"  ⚠️ 破壊工作中 (残り {info['sabotage_remaining']}T)")
            lines.append("")
        return "\n".join(lines)

    def _stability_color(self, stability: int) -> tuple[int, int, int]:
        if stability >= 70:
            return (50, 200, 50)
        elif stability >= 40:
            return (220, 180, 30)
        else:
            return (220, 50, 50)

    def get_faction_summary(self) -> dict[str, dict[str, Any]]:
        from skill_eater_economy_system import SkillEaterEconomySystem
        economy = SkillEaterEconomySystem()
        summary = {}
        for faction_id, faction in economy.factions.items():
            districts = self.territory.get_districts_by_faction(faction_id)
            total_income = sum(self.territory.calculate_resource_output(d) for d in districts)
            summary[faction_id] = {
                "name": faction.name,
                "color": FACTION_COLORS.get(faction_id, FACTION_COLORS["neutral"]),
                "icon": FACTION_ICONS.get(faction_id, FACTION_ICONS["neutral"]),
                "district_count": len(districts),
                "total_income": total_income,
                "influence": faction.influence_points,
                "reputation": faction.reputation,
                "morale": faction.morale,
                "is_at_war": faction.is_at_war,
                "war_target": faction.war_target,
                "territory_income": faction.territory_income_per_turn,
            }
        return summary


@dataclass
class TerritoryActionPanel:
    territory: TerritoryState
    controller: TerritoryController

    def get_available_actions(self, actor_faction: str, district_id: str) -> list[dict[str, Any]]:
        district = self.territory.districts.get(district_id)
        if not district:
            return []

        actions = []
        for action_type in TerritoryActionType:
            action_class = self.controller.ACTION_CLASSES.get(action_type)
            if not action_class:
                continue
            action = action_class()
            can_exec, reason = action.can_execute(self.territory, actor_faction, district_id)
            success_rate = action.calculate_success_rate(self.territory, actor_faction, district_id) if can_exec else 0

            costs = TERRITORY_ACTION_COSTS[action_type]

            actions.append({
                "type": action_type.value,
                "name": self._action_name(action_type),
                "description": self._action_description(action_type),
                "can_execute": can_exec,
                "reason": reason,
                "success_rate": int(success_rate * 100),
                "costs": costs,
                "audio_cue": action.get_audio_cue(),
                "emote_cue": action.get_emote_cue(),
            })
        return actions

    def _action_name(self, action_type: TerritoryActionType) -> str:
        names = {
            TerritoryActionType.PATROL: "パトロール",
            TerritoryActionType.RAID: "襲撃",
            TerritoryActionType.PROPAGANDA: "プロパガンダ",
            TerritoryActionType.SABOTAGE: "破壊工作",
            TerritoryActionType.NEGOTIATE_CEASEFIRE: "停戦交渉",
        }
        return names.get(action_type, action_type.value)

    def _action_description(self, action_type: TerritoryActionType) -> str:
        descs = {
            TerritoryActionType.PATROL: "自派閥区画の安定度と資源出力を向上",
            TerritoryActionType.RAID: "敵派閥区画を武力で制圧（戦争リスクあり）",
            TerritoryActionType.PROPAGANDA: "隣接区画の住民を自派閥に誘導",
            TerritoryActionType.SABOTAGE: "敵区画の資源と防御を一時的に低下",
            TerritoryActionType.NEGOTIATE_CEASEFIRE: "戦争中の敵派閥と停戦を交渉",
        }
        return descs.get(action_type, "")

    def execute_action(self, actor_faction: str, action_type: TerritoryActionType, district_id: str, **kwargs) -> dict[str, Any]:
        result = self.controller.execute_action(actor_faction, action_type, district_id, **kwargs)
        return result.to_dict()


@dataclass
class TerritoryEventPanel:
    territory: TerritoryState

    def get_active_events_display(self) -> list[dict[str, Any]]:
        events = []
        for event in self.territory.active_events:
            events.append({
                "id": event.id,
                "name": event.name,
                "description": event.description,
                "type": event.event_type.value,
                "remaining_turns": event.remaining_turns,
                "faction_scope": event.faction_scope,
                "icon": self._event_icon(event.event_type),
                "color": self._event_color(event.event_type),
            })
        return events

    def get_event_history_display(self, limit: int = 20) -> list[dict[str, Any]]:
        history = []
        for entry in self.territory.event_history[-limit:]:
            history.append({
                "turn": entry.get("turn", 0),
                "type": entry.get("type", "unknown"),
                "description": self._history_description(entry),
            })
        return list(reversed(history))

    def _event_icon(self, event_type: DynamicEventType) -> str:
        icons = {
            DynamicEventType.FACTION_WAR: "⚔️",
            DynamicEventType.BETRAYAL: "🗡️",
            DynamicEventType.THIRD_PARTY: "👻",
            DynamicEventType.MIDAS_RAID: "🚨",
        }
        return icons.get(event_type, "📢")

    def _event_color(self, event_type: DynamicEventType) -> tuple[int, int, int]:
        colors = {
            DynamicEventType.FACTION_WAR: (220, 50, 50),
            DynamicEventType.BETRAYAL: (180, 50, 180),
            DynamicEventType.THIRD_PARTY: (100, 100, 220),
            DynamicEventType.MIDAS_RAID: (220, 100, 30),
        }
        return colors.get(event_type, (200, 200, 200))

    def _history_description(self, entry: dict[str, Any]) -> str:
        t = entry.get("type", "")
        if t == "territory_lost":
            return f"区画 {entry.get('district')} が {entry.get('old_faction')} から失陥"
        elif t == "shop_unlocked":
            return f"{entry.get('district')} で専用ショップ解放 ({entry.get('faction')})"
        elif t == "dungeon_revealed":
            return f"{entry.get('district')} で隠しダンジョン発見 ({entry.get('faction')})"
        elif t == "ceasefire_ended":
            return f"{entry.get('faction_a')} と {entry.get('faction_b')} の停戦終了"
        elif t == "event_ended":
            return f"イベント終了: {entry.get('event_name')}"
        elif t == "faction_war_ended":
            return f"派閥戦争終了: 勝者 {entry.get('winner')}, 敗者 {entry.get('loser')}"
        elif t == "third_party_defeated":
            return f"第三勢力 {entry.get('third_party')} 撃退"
        return str(entry)


def create_territory_ui(territory: TerritoryState | None = None) -> dict[str, Any]:
    territory = territory or TerritoryState.get_instance()
    controller = TerritoryController(territory)
    return {
        "map_renderer": TerritoryMapRenderer(territory),
        "action_panel": TerritoryActionPanel(territory, controller),
        "event_panel": TerritoryEventPanel(territory),
        "controller": controller,
    }


def format_district_tooltip(district: District, territory: TerritoryState) -> str:
    lines = [
        f"=== {district.name} ===",
        f"ID: {district.id}",
        f"支配派閥: {district.controlling_faction}",
        f"安定度: {district.stability}/100",
        f"資源出力: {district.resource_output}/ターン",
        f"防御レベル: {district.defense_level}",
        f"支配ターン数: {district.turn_controlled}",
    ]
    if district.exclusive_shop_unlocked:
        lines.append("🏪 専用ショップ: 解放済み")
    if district.hidden_dungeon_entrance:
        lines.append("🏰 隠しダンジョン入口: 発見済み")
    if district.sabotage_remaining > 0:
        lines.append(f"⚠️ 破壊工作中: 残り {district.sabotage_remaining} ターン")

    adjacent_names = [territory.districts.get(a, District(id="", name="")).name for a in district.adjacent_districts]
    lines.append(f"隣接区画: {', '.join(adjacent_names)}")

    actions = []
    for action_type in TerritoryActionType:
        action_class = TerritoryController.ACTION_CLASSES.get(action_type)
        if action_class:
            action = action_class()
            can_exec, _ = action.can_execute(territory, "player", district.id)
            if can_exec:
                rate = action.calculate_success_rate(territory, "player", district.id)
                actions.append(f"  {action_type.value}: 成功率 {int(rate*100)}%")
    if actions:
        lines.append("実行可能アクション:")
        lines.extend(actions)

    return "\n".join(lines)
