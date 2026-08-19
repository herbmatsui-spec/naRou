"""Proposal 8: Skill Synergy / Combo System.

Detects when a sequence of recently-used skills matches a defined synergy
combo and returns the resulting effects.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
import yaml
import logging


logger = logging.getLogger(__name__)


@dataclass
class SynergyEffect:
    type: str
    radius: int = 0
    formula: str = ""
    element: str = ""
    effect: str = ""
    duration: int = 0
    count: int = 0
    stats_multiplier: float = 0.0


@dataclass
class Synergy:
    id: str
    name: str
    skills: List[str]
    window: int
    effects: List[SynergyEffect] = field(default_factory=list)


class SkillSynergyManager:
    """Loads synergy definitions and evaluates combos from recent skill use."""

    def __init__(self, path: str = "data/skill_synergy.yaml"):
        self._synergies: Dict[str, Synergy] = {}
        self.load(path)

    def load(self, path: str = "data/skill_synergy.yaml") -> None:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Synergy file not found: {path}")
            return
        except Exception as e:
            logger.error(f"Failed to load synergies: {e}")
            return

        self._synergies.clear()
        for sid, sdata in (data or {}).get('synergies', {}).items():
            effects = [
                SynergyEffect(
                    type=e.get('type', ''),
                    radius=int(e.get('radius', 0)),
                    formula=e.get('formula', ''),
                    element=e.get('element', ''),
                    effect=e.get('effect', ''),
                    duration=int(e.get('duration', 0)),
                    count=int(e.get('count', 0)),
                    stats_multiplier=float(e.get('stats_multiplier', 0.0)),
                )
                for e in sdata.get('effect', [])
            ]
            self._synergies[sid] = Synergy(
                id=sid,
                name=sdata.get('name', ''),
                skills=list(sdata.get('skills', [])),
                window=int(sdata.get('window', 1)),
                effects=effects,
            )
        logger.info(f"Loaded {len(self._synergies)} synergies")

    def all(self) -> Dict[str, Synergy]:
        return self._synergies.copy()

    def register_skill_use(self, player, skill_id: str, turn: int) -> None:
        """Record a skill use (requires player.recent_skills)."""
        if not hasattr(player, "recent_skills"):
            player.recent_skills = []
        player.recent_skills.append((skill_id, turn))

    def evaluate(self, player, turn: int) -> List[Synergy]:
        """Return synergies whose skill set is fully present within the window."""
        recent = getattr(player, "recent_skills", [])
        triggered: List[Synergy] = []
        for syn in self._synergies.values():
            # Gather skill ids used within the window
            recent_ids = [
                sid for (sid, t) in recent
                if turn - t <= syn.window
            ]
            if all(s in recent_ids for s in syn.skills):
                triggered.append(syn)
        return triggered
