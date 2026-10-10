"""Meta intervention template event generator and intervention engine."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from naRou.skill_eater.skill_eater_template_model import ExploitWindow, TemplateData


@dataclass
class TemplateEvent:
    """Active template event during exploration."""
    template_id: str
    archetype: str
    context: str
    faction: str
    difficulty: float
    route_steps: list
    exploit_windows: list[ExploitWindow]
    turn_spawned: int


@dataclass
class InterventionAction:
    """Player's intervention action against a template event."""
    tier: int  # 1=surface, 2=structural, 3=ontological
    window_id: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class InterventionResult:
    """Result of an intervention attempt."""
    success: bool
    completeness: float  # 0.0-1.0
    karma_gained: int
    stolen_skill: str | None = None
    unique_skill_granted: str | None = None
    exposure_gained: int = 0
    karma_good_evil_change: int = 0
    message: str = ""


class TemplateEventGenerator:
    """Generates procedural template events during exploration."""

    def __init__(self, templates: dict[str, TemplateData], rng: random.Random | None = None):
        self.templates = templates
        self.rng = rng or random.Random()
        self.active_events: list[TemplateEvent] = []

        # Context -> archetype weights
        self.context_weights: dict[str, list[tuple[str, float]]] = {
            "slum": [("expel", 0.4), ("betray", 0.25), ("credit_steal", 0.2), ("genius_discrimination", 0.15)],
            "guild": [("expel", 0.35), ("betray", 0.25), ("credit_steal", 0.2), ("genius_discrimination", 0.2)],
            "noble_quarter": [("engagement_break", 0.35), ("credit_steal", 0.3), ("servant_conversion", 0.2), ("genius_discrimination", 0.15)],
            "dungeon_entrance": [("betray", 0.35), ("expel", 0.3), ("credit_steal", 0.2), ("servant_conversion", 0.15)],
        }
        self.faction_weights: dict[str, list[tuple[str, float]]] = {
            "slum": [("outlaw", 0.4), ("guild", 0.3), ("merchant", 0.2), ("guard", 0.1)],
            "guild": [("guild", 0.5), ("merchant", 0.3), ("outlaw", 0.1), ("guard", 0.1)],
            "noble_quarter": [("noble", 0.5), ("guard", 0.3), ("merchant", 0.2)],
            "dungeon_entrance": [("outlaw", 0.4), ("guild", 0.3), ("merchant", 0.2), ("guard", 0.1)],
        }

    def _roll_seed(self, context: str) -> tuple[str, str]:
        """Roll archetype and faction for given context."""
        archetype_choices = self.context_weights.get(context, [("expel", 1.0)])
        faction_choices = self.faction_weights.get(context, [("outlaw", 1.0)])

        archetype = self._weighted_choice(archetype_choices)
        faction = self._weighted_choice(faction_choices)
        return archetype, faction

    def _weighted_choice(self, choices: list[tuple[str, float]]) -> str:
        """Choose from weighted list."""
        total = sum(w for _, w in choices)
        r = self.rng.random() * total
        accum = 0.0
        for choice, weight in choices:
            accum += weight
            if r <= accum:
                return choice
        return choices[-1][0]

    def _find_template(self, archetype: str, context: str) -> TemplateData | None:
        """Find a template matching archetype and context."""
        for tpl in self.templates.values():
            if tpl.archetype == archetype and context in tpl.contexts:
                return tpl
        return None

    def build_route(self, template: TemplateData) -> list:
        """Build route steps from template."""
        return template.route_steps

    def extract_windows(self, template: TemplateData) -> list[ExploitWindow]:
        """Extract exploit windows from template."""
        return template.exploit_windows

    def compute_difficulty(self, windows: list[ExploitWindow], loop_count: int = 1) -> float:
        """Compute difficulty based on windows and loop count."""
        if not windows:
            return 1.0
        # Base difficulty from inverse of success rates
        base = sum(1.0 / max(0.01, w.base_success) for w in windows) / len(windows)
        # Loop modifier: easier with more loops
        loop_mod = 1.0 / (1.0 + 0.1 * (loop_count - 1))
        return base * loop_mod

    def maybe_spawn(self, context: str, current_turn: int, loop_count: int = 1, spawn_chance: float = 0.5) -> TemplateEvent | None:
        """Try to spawn a template event."""
        if self.rng.random() > spawn_chance:
            return None

        archetype, faction = self._roll_seed(context)
        template = self._find_template(archetype, context)
        if not template:
            return None

        route = self.build_route(template)
        windows = self.extract_windows(template)
        difficulty = self.compute_difficulty(windows, loop_count)

        event = TemplateEvent(
            template_id=template.id,
            archetype=template.archetype,
            context=context,
            faction=faction,
            difficulty=difficulty,
            route_steps=route,
            exploit_windows=windows,
            turn_spawned=current_turn,
        )
        self.active_events.append(event)
        return event


class InterventionEngine:
    """Executes player interventions against template events."""

    TIER_MULTIPLIERS = {1: 1.0, 2: 2.5, 3: 6.0}
    COMPLETENESS_TIERS = {
        0: 0.3,   # 0-39%
        40: 1.0,  # 40-69%
        70: 1.8,  # 70-89%
        90: 2.6,  # 90-99%
        100: 4.0, # 100%
    }

    def __init__(
        self,
        registry: Any,
        presentation: Any,
        rule_engine: Any,
        meta_state: Any,
        rng: random.Random | None = None,
        templates: dict | None = None,
    ):
        self.registry = registry
        self.templates = templates or {}
        self.presentation = presentation
        self.rule_engine = rule_engine
        self.meta_state = meta_state
        self.rng = rng or random.Random()

    def roll_success(self, window: ExploitWindow, difficulty: float) -> bool:
        """Roll for intervention success."""
        base = window.base_success
        # Difficulty reduces success chance
        chance = base / max(0.1, difficulty)
        return self.rng.random() < chance

    def compute_completeness(self, event: TemplateEvent, executed_windows: list[str]) -> float:
        """Compute how completely the template was destroyed (0.0-1.0)."""
        total_windows = len(event.exploit_windows)
        if total_windows == 0:
            return 1.0
        completed = len([w for w in event.exploit_windows if w.id in executed_windows])
        return completed / total_windows

    def calc_karma(self, reward: Any, tier: int, completeness: float) -> int:
        """Calculate karma reward based on tier and completeness."""
        base = reward.karma_t1 if tier == 1 else reward.karma_t2
        # Find multiplier from completeness tier
        multiplier = 1.0
        for threshold, mult in sorted(self.COMPLETENESS_TIERS.items()):
            if completeness * 100 >= threshold:
                multiplier = mult
        return int(base * multiplier * self.TIER_MULTIPLIERS.get(tier, 1.0))

    def execute_t1(self, event: TemplateEvent, window: ExploitWindow, player: Any) -> InterventionResult:
        """Execute T1 surface intervention (buy cheap, etc.)."""
        # Simulate gold cost
        gold_cost = window.req_gold
        if hasattr(player, "gold") and player.gold < gold_cost:
            return InterventionResult(False, 0, 0, message="所持金不足")
        if hasattr(player, "gold"):
            player.gold -= gold_cost

        # Grant stolen skill
        template = self.templates.get(event.template_id)
        stolen = template.reward.stealable_skill if template else None
        if stolen and hasattr(player, "add_skill"):
            player.add_skill(stolen)

        completeness = 0.5  # T1 only hits first window
        karma = self.calc_karma(template.reward if template else None, 1, completeness)

        return InterventionResult(
            success=True,
            completeness=completeness,
            karma_gained=karma,
            stolen_skill=stolen,
            exposure_gained=1,
            message=f"T1介入成功: {window.id} を実行、{stolen or 'なし'} を入手"
        )

    def execute_t2(self, event: TemplateEvent, window: ExploitWindow, player: Any) -> InterventionResult:
        """Execute T2 structural intervention (reverse pride, etc.)."""
        # Require specific skill
        for req in window.req_skill:
            if not (hasattr(player, "has_skill") and player.has_skill(req)):
                return InterventionResult(False, 0, 0, message=f"必要スキル不足: {req}")

        # Flip target's scenario flag
        target = getattr(event, "target_npc", None)
        if target and hasattr(target, "scenario_flags"):
            # Reverse the flag that drove the template
            for flag in target.scenario_flags:
                if flag.startswith(event.archetype):
                    target.scenario_flags[flag] = -target.scenario_flags[flag]
                    break

        template = self.templates.get(event.template_id)
        completeness = 0.8
        karma = self.calc_karma(template.reward if template else None, 2, completeness)

        return InterventionResult(
            success=True,
            completeness=completeness,
            karma_gained=karma,
            exposure_gained=3,
            karma_good_evil_change=-2,
            message=f"T2介入成功: {event.archetype} 構造を書き換えた"
        )

    def execute_t3(self, event: TemplateEvent, window: ExploitWindow, player: Any) -> InterventionResult:
        """Execute T3 ontological intervention (erase template from world)."""
        # Requires massive karma
        if self.meta_state.total_karma_points < 5000:
            return InterventionResult(False, 0, 0, message="因果ポイント不足（5000必要）")

        # Call GlobalRuleEngine to erase template weight
        rule_name = f"template_weight_{event.template_id}"
        success, msg, cost = self.rule_engine.override_rule(
            rule_name=rule_name,
            value=0.0,
            cost_type="KARMA",
            available_karma=self.meta_state.total_karma_points,
        )
        if not success:
            return InterventionResult(False, 0, 0, message=msg)

        template = self.templates.get(event.template_id)
        completeness = 1.0
        karma = self.calc_karma(template.reward if template else None, 3, completeness)

        return InterventionResult(
            success=True,
            completeness=completeness,
            karma_gained=karma,
            exposure_gained=10,
            karma_good_evil_change=-5,
            message=f"T3介入成功: {event.archetype} テンプレを世界から消滅させた"
        )

    def execute(
        self,
        event: TemplateEvent,
        action: InterventionAction,
        player: Any,
        loop_count: int = 1,
    ) -> InterventionResult:
        """Main entry point for intervention."""
        # Find window
        window = next((w for w in event.exploit_windows if w.id == action.window_id), None)
        if not window:
            return InterventionResult(False, 0, 0, message="無効な介入窓")

        # Check tier requirement
        if window.tier > action.tier:
            return InterventionResult(False, 0, 0, message=f"この窓は Tier {window.tier} 以上が必要")

        # Roll success
        if not self.roll_success(window, event.difficulty):
            # Failure: template completes, player complicit
            return self._handle_failure(event, player)

        # Execute by tier
        if action.tier == 1:
            return self.execute_t1(event, window, player)
        elif action.tier == 2:
            return self.execute_t2(event, window, player)
        elif action.tier == 3:
            return self.execute_t3(event, window, player)
        else:
            return InterventionResult(False, 0, 0, message="無効なTier")

    def _handle_failure(self, event: TemplateEvent, player: Any) -> InterventionResult:
        """Handle failed intervention."""
        # Template completes, player marked as complicit
        if hasattr(player, "karma_good_evil"):
            player.karma_good_evil -= 5
        if hasattr(player, "template_exposure"):
            player.template_exposure += 5
        return InterventionResult(
            success=False,
            completeness=0.0,
            karma_gained=0,
            exposure_gained=5,
            karma_good_evil_change=-5,
            message=f"介入失敗: {event.archetype} が定形通り完遂、共犯扱いに"
        )

    def apply_rewards(self, player: Any, result: InterventionResult, event: TemplateEvent) -> None:
        """Apply intervention rewards to player and meta state."""
        if not result.success:
            return

        # Add karma to meta state
        self.meta_state.total_karma_points += result.karma_gained

        # Track devoured template
        self.meta_state.devoured_template_counts[event.archetype] = (
            self.meta_state.devoured_template_counts.get(event.archetype, 0) + 1
        )

        # Apply exposure
        if hasattr(player, "template_exposure"):
            player.template_exposure += result.exposure_gained

        # Apply good/evil change
        if hasattr(player, "karma_good_evil") and result.karma_good_evil_change:
            player.karma_good_evil += result.karma_good_evil_change

        # Grant unique skill if high completeness
        if result.completeness >= 0.7 and result.unique_skill_granted:
            if hasattr(player, "add_skill"):
                player.add_skill(result.unique_skill_granted)

        # Emit presentation event
        tier_names = {1: "表面", 2: "構造", 3: "存在"}
        self.presentation.add_event(
            emote_file="emote_stars.png",
            audio_file="fanfare.ogg",
            message=f"テンプレ粉砕({tier_names.get(1, '')}) 完全性{int(result.completeness*100)}% 因果+{result.karma_gained}",
            duration_ms=2000,
            event_type="bounty_complete",
        )
