"""Proposal 6-9 (Guild/Faction): roles, wars, ranking titles, faction events.

Consolidated managers for the guild/faction ranking proposal. Each manager
loads its YAML data and exposes the core logic described in the proposal.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def _load_yaml(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.warning(f"File not found: {path}")
        return {}
    except Exception as e:
        logger.error(f"Failed to load {path}: {e}")
        return {}


# ============================================================
# 提案6: Guild hierarchy & permissions
# ============================================================


class GuildRoleManager:
    def __init__(self, path: str = "data/guild_roles.yaml"):
        self._roles: dict[str, dict] = {}
        self.load(path)

    def load(self, path: str = "data/guild_roles.yaml") -> None:
        data = _load_yaml(path)
        roles_root = data.get("guild_roles", data)
        self._roles.clear()
        for group in ("default_roles", "custom_roles"):
            for rid, rdata in (roles_root.get(group, {}) or {}).items():
                self._roles[rid] = rdata
        logger.info(f"Loaded {len(self._roles)} guild roles")

    def has_permission(self, role: str | None, permission: str) -> bool:
        if role is None:
            return False
        rdata = self._roles.get(role)
        if not rdata:
            return False
        perms = rdata.get("permissions", [])
        return "all" in perms or permission in perms

    def can_promote(self, from_role: str, to_role: str) -> bool:
        rdata = self._roles.get(from_role)
        if not rdata:
            return False
        return to_role in rdata.get("promotions_to", [])

    def can_demote(self, from_role: str, to_role: str) -> bool:
        rdata = self._roles.get(from_role)
        if not rdata:
            return False
        return to_role in rdata.get("demotions_from", [])


# ============================================================
# 提案7: Guild wars & alliances
# ============================================================


@dataclass
class GuildWarState:
    attacker: str
    defender: str
    eliminations: int = 0
    territory: list[str] = field(default_factory=list)
    quest_progress: int = 0
    allied_with: list[str] = field(default_factory=list)


class GuildWarManager:
    def __init__(self, path: str = "data/guild_wars.yaml"):
        self._conditions: list[dict] = []
        self._alliance_benefits: list[str] = []
        self.load(path)

    def load(self, path: str = "data/guild_wars.yaml") -> None:
        data = _load_yaml(path)
        self._conditions = data.get("guild_war_conditions", {}).get(
            "victory_conditions", []
        )
        self._alliance_benefits = data.get("guild_war_conditions", {}).get(
            "alliance_benefits", []
        )
        logger.info(f"Loaded {len(self._conditions)} war victory conditions")

    def is_victory(self, state: GuildWarState) -> bool:
        for cond in self._conditions:
            ctype = cond.get("type")
            target = cond.get("target")
            if ctype == "member_eliminations":
                if state.eliminations < int(target):
                    return False
            elif ctype == "territory_control":
                if not all(t in state.territory for t in target):
                    return False
            elif ctype == "quest_completion":
                needed = target.get("count", 0)
                if state.quest_progress < needed:
                    return False
            else:
                return False
        return True

    def form_alliance(self, state: GuildWarState, guild_id: str) -> None:
        if guild_id not in state.allied_with:
            state.allied_with.append(guild_id)


# ============================================================
# 提案8: Ranking titles
# ============================================================


class RankingTitleManager:
    def __init__(self, path: str = "data/ranking_titles.yaml"):
        self._data: dict[str, list[dict]] = {}
        self.load(path)

    def load(self, path: str = "data/ranking_titles.yaml") -> None:
        self._data = _load_yaml(path).get("ranking_titles", {})
        logger.info(f"Loaded ranking titles for: {list(self._data.keys())}")

    def title_for_rank(self, category: str, rank: int) -> dict | None:
        for entry in self._data.get(category, []):
            lo, hi = entry.get("rank_range", [0, 0])
            if lo <= rank <= hi:
                return entry
        return None

    def grant_title(self, player, category: str, rank: int) -> str | None:
        entry = self.title_for_rank(category, rank)
        if entry is None:
            return None
        title = entry["title"]
        if title not in player.ranking_titles:
            player.ranking_titles.append(title)
        return title

    def aggregate_effects(self, player) -> dict[str, Any]:
        """Sum stat/bonus effects from all held ranking titles."""
        out: dict[str, Any] = {"stat_bonus": {}, "bonuses": {}}
        for title in player.ranking_titles:
            # find entry by title across categories
            for entries in self._data.values():
                for e in entries:
                    if e.get("title") == title:
                        for eff in e.get("effects", []):
                            if eff.get("type") == "stat_bonus":
                                for k, v in (eff.get("value") or {}).items():
                                    out["stat_bonus"][k] = out["stat_bonus"].get(
                                        k, 0
                                    ) + int(v)
                            else:
                                key = eff.get("type")
                                out["bonuses"][key] = out["bonuses"].get(
                                    key, 0
                                ) + float(eff.get("value", 0))
        return out


# ============================================================
# 提案9: Faction storylines & events
# ============================================================


class FactionEventManager:
    def __init__(self, path: str = "data/faction_events.yaml"):
        self._events: dict[str, list[dict]] = {}
        self.load(path)

    def load(self, path: str = "data/faction_events.yaml") -> None:
        self._events = _load_yaml(path).get("faction_events", {})
        logger.info(f"Loaded faction events for: {list(self._events.keys())}")

    def available_events(self, faction: str, reputation: dict[str, int]) -> list[dict]:
        out = []
        for ev in self._events.get(faction, []):
            reqs = ev.get("requirements", {})
            rep_req = reqs.get("faction_reputation", {})
            ok = all(reputation.get(f, 0) >= v for f, v in rep_req.items())
            if ok:
                out.append(ev)
        return out

    def complete_event(
        self, player, faction: str, event_id: str, choice_id: str
    ) -> dict:
        for ev in self._events.get(faction, []):
            if ev.get("id") != event_id:
                continue
            choice = next(
                (c for c in ev.get("choices", []) if c.get("id") == choice_id), None
            )
            if choice is None:
                return {}
            # record completion
            if event_id not in player.completed_faction_events:
                player.completed_faction_events.append(event_id)
            # apply reputation consequences
            cons = choice.get("consequences", {})
            for f, delta in cons.get("faction_reputation", {}).items():
                player.faction_reputation[f] = player.faction_reputation.get(
                    f, 0
                ) + int(delta)
            rewards = cons.get("rewards", [])
            return {"rewards": rewards, "consequences": cons}
        return {}
