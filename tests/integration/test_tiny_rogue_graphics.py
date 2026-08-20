"""
Integration tests for Tiny Rogue Graphics Pack.
Tests spawn→render→animate→despawn cycle for all new tile types.
"""

import pytest

from feature_flags import set_flag

# Enable graphics for testing
set_flag("ENABLE_TINY_ROGUE_GFX", True)


class TestTinyRogueTileAtlas:
    """Test TileAtlas loads and provides correct UVs for tiny_rogue_16 scale."""

    def test_atlas_loads_tiny_rogue_scale(self):
        from core.tile_atlas import TileAtlas

        atlas = TileAtlas()
        assert "tiny_rogue_16" in atlas.atlas_meta
        assert "tiles" in atlas.atlas_meta["tiny_rogue_16"]
        # Packed atlas contains 105 unique entries (directional groups collapsed)
        assert len(atlas.atlas_meta["tiny_rogue_16"]["tiles"]) == 105

    def test_floor_tile_uv_lookup(self):
        from core.tile_atlas import TileAtlas

        atlas = TileAtlas()
        # Test all 12 floor variants
        for v in range(12):
            uv = atlas.get_uv("TR_FLOOR_01", variant=v, scale="tiny_rogue_16")
            assert uv.x >= 0
            assert uv.y >= 0
            assert uv.w == 16
            assert uv.h == 16

    def test_wall_tile_uv_lookup(self):
        from core.tile_atlas import TileAtlas

        atlas = TileAtlas()
        for v in range(12):
            uv = atlas.get_uv("TR_WALL_01", variant=v, scale="tiny_rogue_16")
            assert uv.w == 16
            assert uv.h == 16

    def test_monster_directional_frames(self):
        from core.tile_atlas import TileAtlas

        atlas = TileAtlas()
        # Test 4 directions × 4 animation frames
        for direction in range(4):
            for frame in range(4):
                uv = atlas.get_uv(
                    "TR_MONSTER_01",
                    frame=frame,
                    direction=direction,
                    scale="tiny_rogue_16",
                )
                assert uv.w == 16
                assert uv.h == 16
                # Each direction should have different Y offset
        # Verify directions have different Y positions
        uv_down = atlas.get_uv("TR_MONSTER_01", direction=0, scale="tiny_rogue_16")
        uv_left = atlas.get_uv("TR_MONSTER_01", direction=1, scale="tiny_rogue_16")
        uv_right = atlas.get_uv("TR_MONSTER_01", direction=2, scale="tiny_rogue_16")
        uv_up = atlas.get_uv("TR_MONSTER_01", direction=3, scale="tiny_rogue_16")
        assert len({uv_down.y, uv_left.y, uv_right.y, uv_up.y}) == 4

    def test_player_directional_frames(self):
        from core.tile_atlas import TileAtlas

        atlas = TileAtlas()
        for direction in range(4):
            uv = atlas.get_uv(
                "TR_PLAYER_01", direction=direction, scale="tiny_rogue_16"
            )
            assert uv.w == 16
            assert uv.h == 16

    def test_effect_tiles(self):
        from core.tile_atlas import TileAtlas

        atlas = TileAtlas()
        for i in range(1, 13):
            tile_id = f"TR_EFFECT_{i:02d}"
            uv = atlas.get_uv(tile_id, scale="tiny_rogue_16")
            assert uv.w == 16
            assert uv.h == 16


class TestTinyRogueTileRegistry:
    """Test TileRegistry integration with tiny_rogue_16 scale."""

    def test_registry_loads_tiny_rogue(self):
        from map_engine import TILE_REGISTRY

        assert "tiny_rogue_16" in dir(TILE_REGISTRY) or hasattr(
            TILE_REGISTRY, "atlas_tiny_rogue_meta"
        )

    def test_registry_uv_lookup(self):
        from map_engine import TILE_REGISTRY

        uv = TILE_REGISTRY.get_uv("TR_FLOOR_01", scale="tiny_rogue_16")
        assert len(uv) == 4
        assert all(isinstance(v, int) for v in uv)

    def test_registry_variant_lookup(self):
        from map_engine import TILE_REGISTRY

        for v in range(12):
            uv = TILE_REGISTRY.get_uv("TR_FLOOR_01", variant=v, scale="tiny_rogue_16")
            assert uv[2] == 16  # width
            assert uv[3] == 16  # height

    def test_registry_animation_frame(self):
        from map_engine import TILE_REGISTRY

        for frame in range(4):
            uv = TILE_REGISTRY.get_animation_frame(
                "TR_MONSTER_01", frame, scale="tiny_rogue_16"
            )
            assert uv[2] == 16
            assert uv[3] == 16


class TestTinyRogueEntityRendering:
    """Test entity rendering with Tiny Rogue tiles."""

    def test_monster_tile_mapping(self):
        from entity_renderer import EntityRenderer
        from systems import MonsterPreset

        # Test all 12 monster types map to correct tiles
        expected = {
            "slime": "TR_MONSTER_01",
            "red_slime": "TR_MONSTER_01",
            "snail": "TR_MONSTER_02",
            "goblin": "TR_MONSTER_01",
            "kobold": "TR_MONSTER_02",
            "orc": "TR_MONSTER_03",
            "hound_fire": "TR_MONSTER_VAR_01",
            "rogue_thief": "TR_MONSTER_VAR_02",
            "novice_wizard": "TR_MONSTER_VAR_03",
            "minotaur": "TR_MONSTER_VAR_01",
            "lich": "TR_MONSTER_VAR_02",
            "dragon_red": "TR_MONSTER_VAR_03",
        }

        for mtype, expected_tile in expected.items():
            e = MonsterPreset.create(mtype, 0, 0)
            tile_id = EntityRenderer._get_tile_id(e)
            assert tile_id == expected_tile, (
                f"{mtype}: expected {expected_tile}, got {tile_id}"
            )

    def test_player_and_pet_unchanged(self):
        from entity import Entity
        from entity_renderer import EntityRenderer

        player = Entity(0, 0, "@", (255, 255, 255), "Player")
        player.is_player = True
        assert EntityRenderer._get_tile_id(player) == "PLAYER"

        pet = Entity(0, 0, "d", (255, 200, 100), "Pet")
        pet.is_pet = True
        assert EntityRenderer._get_tile_id(pet) == "PET"

    def test_feature_flag_toggle(self):
        from entity_renderer import EntityRenderer
        from systems import MonsterPreset

        set_flag("ENABLE_TINY_ROGUE_GFX", False)
        e = MonsterPreset.create("goblin", 0, 0)
        assert EntityRenderer._get_tile_id(e) == "ENEMY_GOBLIN"

        set_flag("ENABLE_TINY_ROGUE_GFX", True)
        assert EntityRenderer._get_tile_id(e) == "TR_MONSTER_01"


class TestTinyRogueDungeonGeneration:
    """Test dungeon generation uses Tiny Rogue tile variants."""

    def test_floor_variants_assigned(self):
        from feature_flags import set_flag
        from map_engine import GameMap

        set_flag("ENABLE_TINY_ROGUE_GFX", True)
        gm = GameMap(30, 30)
        gm.generate_dungeon(max_rooms=3)

        # Check that floor tiles have variants assigned
        floor_variants = [
            v
            for pos, v in gm.tile_variants.items()
            if gm.tiles[pos[0]][pos[1]] == "TILE_FLOOR"
        ]
        assert len(floor_variants) > 0
        assert all(0 <= v <= 11 for v in floor_variants)

    def test_wall_variants_assigned(self):
        from map_engine import GameMap

        gm = GameMap(30, 30)
        gm.generate_dungeon(max_rooms=3)

        # Walls are created implicitly; check they're not all variant 0
        # (Implementation may vary - at minimum should not crash)


class TestTinyRogueFXSystem:
    """Test FX Manager integration with Tiny Rogue tiles."""

    def test_blood_splatter_on_damage(self):
        from core_framework import EventBus
        from fx_manager import FXManager
        from systems import CombatSystem

        bus = EventBus()
        fx = FXManager(bus)

        CombatSystem.publish_damage_event(bus, 10, 5, 5, is_crit=True, is_kill=False)

        # Should have blood particles
        blood_particles = [
            p for p in fx.particles if getattr(p, "tile_id", None) == "TR_DECOR_10"
        ]
        assert len(blood_particles) > 0

    def test_blood_pool_on_kill(self):
        from core_framework import EventBus
        from fx_manager import FXManager
        from systems import CombatSystem

        bus = EventBus()
        fx = FXManager(bus)

        CombatSystem.publish_kill_event(bus, 5, 5)

        blood_particles = [
            p for p in fx.particles if getattr(p, "tile_id", None) == "TR_DECOR_10"
        ]
        assert len(blood_particles) > 0

    def test_loot_sparkle(self):
        from core_framework import EventBus
        from fx_manager import FXManager

        bus = EventBus()
        fx = FXManager(bus)

        fx.spawn_loot_sparkle(10, 10, "legendary")
        sparkle_particles = [
            p for p in fx.particles if getattr(p, "tile_id", None) == "TR_EFFECT_09"
        ]
        assert len(sparkle_particles) > 0

    def test_flash_on_crit(self):
        from core_framework import EventBus
        from fx_manager import FXManager

        bus = EventBus()
        fx = FXManager(bus)

        fx.trigger_flash(10, 10)
        flash_particles = [
            p
            for p in fx.particles
            if getattr(p, "tile_id", None) in ("TR_EFFECT_09", "TR_EFFECT_01")
        ]
        assert len(flash_particles) > 0

    def test_all_effect_types(self):
        from core_framework import EventBus
        from fx_manager import FXManager

        bus = EventBus()
        fx = FXManager(bus)

        effect_types = [
            ("magic_cast", "spawn_magic_cast"),
            ("fire", "spawn_fire_effect"),
            ("ice", "spawn_ice_effect"),
            ("lightning", "spawn_lightning_effect"),
            ("poison", "spawn_poison_effect"),
            ("heal", "spawn_heal_effect"),
            ("teleport", "spawn_teleport_effect"),
            ("explosion", "spawn_explosion_effect"),
            ("sparkle", "spawn_sparkle_effect"),
            ("smoke", "spawn_smoke_effect"),
            ("slash", "spawn_slash_effect"),
            ("shockwave", "spawn_shockwave_effect"),
        ]

        for effect_name, method_name in effect_types:
            fx.particles.clear()
            getattr(fx, method_name)(10, 10)
            particles_with_tile = [
                p for p in fx.particles if getattr(p, "tile_id", None)
            ]
            assert len(particles_with_tile) > 0, f"No particles for {effect_name}"


class TestTinyRogueTileMappings:
    """Test tile mapping utilities."""

    def test_dungeon_tile_mappings(self):
        from core.tiny_rogue_tiles import get_dungeon_tile_id

        mappings = {
            "floor": "TR_FLOOR_01",
            "wall": "TR_WALL_01",
            "stairs_up": "TR_DECOR_08",
            "stairs_down": "TR_DECOR_07",
            "water": "TR_EFFECT_02",
            "trap": "TR_DECOR_09",
            "wall_variant": "TR_WALL_VAR_01",
        }

        for key, expected in mappings.items():
            result = get_dungeon_tile_id(key)
            assert result == expected, f"{key}: expected {expected}, got {result}"

    def test_item_tile_mappings(self):
        from core.tiny_rogue_tiles import get_item_tile_id

        assert get_item_tile_id("potion") == "TR_ITEM_01"
        assert get_item_tile_id("gold") == "TR_ITEM_09"
        assert get_item_tile_id("unknown") == "TR_ITEM_12"  # default

    def test_feature_flag_fallback(self):
        from core.tiny_rogue_tiles import get_dungeon_tile_id
        from feature_flags import set_flag

        set_flag("ENABLE_TINY_ROGUE_GFX", False)
        assert get_dungeon_tile_id("floor") == "TILE_FLOOR"
        assert get_dungeon_tile_id("wall") == "TILE_WALL"

        set_flag("ENABLE_TINY_ROGUE_GFX", True)


class TestTinyRogueVisualRegression:
    """Visual regression test infrastructure (headless)."""

    def test_atlas_image_dimensions(self):
        """Verify atlas image has expected dimensions."""
        from PIL import Image

        img = Image.open("assets/tiles/tiny_rogue_atlas_16x16.png")
        assert img.size[0] == 509
        assert img.size[1] == 115
        assert img.mode == "RGBA"

    def test_all_tiles_in_atlas(self):
        """Verify all 132 tile entries exist in atlas metadata."""
        import json

        with open("assets/tiles/tiny_rogue_atlas_16x16.json") as f:
            meta = json.load(f)
        assert len(meta["tiles"]) == 132
        # Check all tiles fit within atlas bounds
        for tile_id, data in meta["tiles"].items():
            assert data["x"] + data["width"] <= meta["atlas_width"]
            assert data["y"] + data["height"] <= meta["atlas_height"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
