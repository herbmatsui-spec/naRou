"""Property delegation helpers for ECS component-backed attributes."""

from __future__ import annotations

from typing import Any, Callable, TypeVar

T = TypeVar("T")


def delegate(
    component_getter: Callable[["object"], Any],
    attr: str,
) -> property:
    """Build a get/set property that proxies *attr* on a component.

    Args:
        component_getter: Callable returning the component instance.
        attr: Attribute name on that component to proxy.
    """

    def getter(self: object) -> Any:
        return getattr(component_getter(self), attr)

    def setter(self: object, val: Any) -> None:
        setattr(component_getter(self), attr, val)

    return property(getter, setter)
