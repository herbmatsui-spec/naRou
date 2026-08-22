from __future__ import annotations

from typing import TYPE_CHECKING, Protocol


if TYPE_CHECKING:
    from event_bus import EventBus
    from ecs.entity import Entity
    from systems import CombatSystem, Quest, StatusEffect
    from renderer import Renderer
    from game import Engine
    from config_manager import ConfigManager
    from sound_manager import SoundManager


class IEventBus(Protocol):
    """Event bus interface."""

    def subscribe(self, event_type: str, handler) -> None: ...

    def publish(self, event_type: str, *args, **kwargs) -> None: ...

    def unsubscribe(self, event_type: str, handler) -> None: ...


class IEntity(Protocol):
    """Entity interface."""

    @property
    def id(self) -> int: ...

    @property
    def x(self) -> int: ...

    @property
    def y(self) -> int: ...

    @property
    def hp(self) -> int: ...

    @property
    def max_hp(self) -> int: ...

    def get_component(self, component_type: type): ...


class ICombatSystem(Protocol):
    """Combat system interface."""

    def calculate_melee_damage(self, attacker: IEntity, defender: IEntity, weapon: Any) -> int: ...

    def apply_damage(self, target: IEntity, damage: int) -> None: ...


class IRenderer(Protocol):
    """Renderer interface."""

    def draw_entity(self, entity: IEntity, x: int, y: int) -> None: ...

    def draw_map(self, game_map: Any) -> None: ...

    def clear(self) -> None: ...


class IEngine(Protocol):
    """Engine interface."""

    @property
    def player(self) -> IEntity: ...

    @property
    def game_map(self) -> Any: ...

    def run(self) -> None: ...

    def tick(self) -> None: ...


class IConfigManager(Protocol):
    """Config manager interface."""

    def get(self, key: str, default: Any = None) -> Any: ...

    def set(self, key: str, value: Any) -> None: ...


class ISoundManager(Protocol):
    """Sound manager interface."""

    def play_se(self, name: str, volume: float = 1.0) -> None: ...

    def play_bgm(self, name: str, volume: float = 1.0, loop: bool = True) -> None: ...
