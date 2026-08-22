from __future__ import annotations

from feature_flags import set_flag

set_flag("ENABLE_TINY_ROGUE_GFX", True)

from core_framework import EventBus
from fx_manager import FXManager

bus = EventBus()
fx = FXManager(bus)

# Test tile effect spawning
fx.spawn_magic_cast(10, 10)
fx.spawn_fire_effect(10, 10)
fx.spawn_ice_effect(10, 10)
fx.spawn_lightning_effect(10, 10)
fx.spawn_poison_effect(10, 10)
fx.spawn_heal_effect(10, 10)
fx.spawn_teleport_effect(10, 10)
fx.spawn_explosion_effect(10, 10)
fx.spawn_sparkle_effect(10, 10)
fx.spawn_smoke_effect(10, 10)
fx.spawn_slash_effect(10, 10, (1, 0))
fx.spawn_shockwave_effect(10, 10)

print("Particles spawned:", len(fx.particles))
for p in fx.particles[:5]:
    print("  tile_id: {}, char: {}, color: {}".format(getattr(p, "tile_id", None), p.char, p.color))

# Test with feature flag disabled
set_flag("ENABLE_TINY_ROGUE_GFX", False)
fx2 = FXManager(bus)
fx2.spawn_fire_effect(10, 10)
print("Disabled particles:", len(fx2.particles))
for p in fx2.particles[:3]:
    print("  tile_id: {}, char: {}".format(getattr(p, "tile_id", None), p.char))
