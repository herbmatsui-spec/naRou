"""
Render System - Handles the main graphical render pipeline extracted from Engine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from constants import COLOR_GOLD_YELLOW, MAP_HEIGHT, MAP_WIDTH, VIEW_HEIGHT, VIEW_WIDTH
from run_summary import GAME_OVER_TITLE

if TYPE_CHECKING:
    from game import Engine


class RenderSystemHandler:
    """Handles the tcod render pipeline: lighting, particles, and context rendering."""

    def __init__(self, engine: "Engine"):
        self.engine = engine

    def render(self, console: Any) -> None:
        """描画処理 (ゲームロジックを含まない)"""
        engine = self.engine
        if engine.game_state_data.game_state == "skill_tree":
            from ui_fx_systems import format_skill_tree_display

            skill_tree_text = format_skill_tree_display(engine.skill_tree_registry)
            y = 1
            for line in skill_tree_text.splitlines():
                console.print(x=1, y=y, string=line, fg=(255, 255, 255))
                y += 1
            return
        if engine.game_state_data.game_state == "job":
            from ui_fx_systems import format_job_display

            job_text = format_job_display(engine.job_registry, engine.player)
            y = 1
            for line in job_text.splitlines():
                console.print(x=1, y=y, string=line, fg=(255, 255, 255))
                y += 1
            return
        if engine.game_state_data.game_state == "cutscene":
            # FF6案6: カットシーン簡易分岐 (全画面暗転 + テロップ行表示)。
            # 設定済みの復帰ターンを過ぎたら通常プレイへ戻す。
            revert_turn = getattr(engine, "cutscene_revert_turn", None)
            if revert_turn is not None and getattr(engine, "turns", 0) >= revert_turn:
                engine.game_state_data.game_state = "play"
                engine.cutscene_telop = []
                return
            telop_lines = getattr(engine, "cutscene_telop", [])
            console.clear(bg=(0, 0, 0))
            y = max(2, console.height // 2 - len(telop_lines))
            for line in telop_lines:
                console.print(x=2, y=y, string=line, fg=(255, 215, 0), bg=(0, 0, 0))
                y += 2
            return
        if engine.game_state_data.game_state == "game_over":
            console.print(x=1, y=1, string=GAME_OVER_TITLE, fg=(255, 50, 50))
            summary = getattr(engine, "run_summary", None)
            y = 2
            for line in summary.format_lines() if summary else []:
                console.print(x=1, y=y, string=line, fg=COLOR_GOLD_YELLOW)
                y += 1
            return

        # Use new TCODRenderer with lighting and particle systems
        from core.tcod_renderer import TCODRenderer

        # Create or reuse renderer
        if not hasattr(engine, "_tcod_renderer") or engine._tcod_renderer is None:
            engine._tcod_renderer = TCODRenderer(console.width, console.height)
            # Use the existing console
            engine._tcod_renderer.console = console
            engine._tcod_renderer.context = None  # Will use console directly

        renderer = engine._tcod_renderer

        # Frame time for lighting/particles
        if hasattr(engine, "_last_render_time"):
            import time

            time.time() - engine._last_render_time
        engine._last_render_time = time.time() if "time" in dir() else 0

        renderer.begin_frame()

        # Camera
        cam_x = max(
            0,
            min(MAP_WIDTH - VIEW_WIDTH, engine.game_state_data.player.x - VIEW_WIDTH // 2),
        )
        cam_y = max(
            0,
            min(
                MAP_HEIGHT - VIEW_HEIGHT,
                engine.game_state_data.player.y - VIEW_HEIGHT // 2,
            ),
        )

        # Prepare lighting data
        import math

        from core.lighting import EnemyCone, LightMap, LightSource

        # Light map from game_map
        light_map = None
        if hasattr(engine.game_state_data, "game_map"):
            gm = engine.game_state_data.game_map
            # Build light map from visible/explored
            intensity_grid = []
            color_grid = []
            for y in range(VIEW_HEIGHT):
                my = cam_y + y
                intensity_row = []
                color_row = []
                for x in range(VIEW_WIDTH):
                    mx = cam_x + x
                    if 0 <= mx < MAP_WIDTH and 0 <= my < MAP_HEIGHT:
                        if gm.visible[my][mx]:
                            intensity_row.append(1.0)
                            color_row.append((255, 240, 210))
                        elif gm.explored[my][mx]:
                            intensity_row.append(0.0)
                            color_row.append((40, 42, 55))
                        else:
                            intensity_row.append(-1.0)
                            color_row.append((0, 0, 0))
                    else:
                        intensity_row.append(-1.0)
                        color_row.append((0, 0, 0))
                intensity_grid.append(intensity_row)
                color_grid.append(color_row)

            light_map = LightMap(intensity=intensity_grid, color=color_grid)

        # Light sources (player lantern, torches, altar)
        light_sources = []
        p = engine.game_state_data.player
        # Player lantern
        light_sources.append(
            LightSource(x=p.x, y=p.y, radius=7.5, intensity=1.0, color=(255, 240, 210))
        )
        # Torches on map
        if hasattr(engine, "game_map") and hasattr(engine.game_map, "torches"):
            for tx, ty in engine.game_map.torches:
                light_sources.append(
                    LightSource(x=tx, y=ty, radius=7.5, intensity=0.8, color=(255, 180, 100))
                )
        # Altar
        if hasattr(engine.game_state_data, "altar_pos"):
            ax, ay = engine.game_state_data.altar_pos
            if 0 <= ax < MAP_WIDTH and 0 <= ay < MAP_HEIGHT:
                light_sources.append(
                    LightSource(x=ax, y=ay, radius=4.0, intensity=0.8, color=(100, 200, 255))
                )

        # Enemy cones
        enemy_cones = []
        for ent in engine.entity_manager.get_entities():
            if (
                not ent.is_player
                and ent.hp > 0
                and engine.game_state_data.game_map.visible[ent.x][ent.y]
            ):
                ang = math.atan2(p.y - ent.y, p.x - ent.x)
                enemy_cones.append(
                    EnemyCone(
                        x=ent.x,
                        y=ent.y,
                        angle=ang,
                        half_angle=0.6,
                        range=6.0,
                        color=(255, 60, 60),
                    )
                )

        # Particles from fx_manager
        particles = []
        if hasattr(engine, "fx_manager") and hasattr(engine.fx_manager, "particles"):
            for pt in engine.fx_manager.particles:
                particles.append(
                    type(
                        "Particle",
                        (),
                        {
                            "type": "dust",  # default
                            "x": float(pt.x),
                            "y": float(pt.y),
                            "life": getattr(pt, "life", 5),
                            "max_life": getattr(pt, "life", 5),
                            "color": pt.color,
                            "char": pt.char,
                        },
                    )()
                )

        # Send lighting/particle data to renderer
        from core.renderer_base import LightingDrawCall, ParticleDrawCall

        renderer.draw_lighting(
            LightingDrawCall(
                light_map=light_map,
                light_sources=light_sources,
                enemy_cones=enemy_cones,
                ambient_light=0.08,
                time=getattr(engine, "_render_time", 0.0),
            )
        )
        renderer.draw_particles(ParticleDrawCall(particles=particles))

        # Update render time
        if not hasattr(engine, "_render_time"):
            engine._render_time = 0.0
        engine._render_time += 1.0 / 60.0

        # Execute render passes in correct order:
        # 1. Lighting pass (base + additive) - BEFORE tile/entity rendering
        renderer.render_lighting_pass(
            cam_x,
            cam_y,
            VIEW_WIDTH,
            VIEW_HEIGHT,
            visible=engine.game_state_data.game_map.visible,
            explored=engine.game_state_data.game_map.explored,
            time=engine._render_time,
        )

        # 2. Delegate to RenderSystem for map/items/entities (they will draw on top of lit background)
        from render_context import RenderContext
        from render_system import RenderSystem

        render_context = RenderContext(
            game_map=engine.game_state_data.game_map,
            player=engine.game_state_data.player,
            pet=engine.game_state_data.pet,
            entities=engine.entity_manager.get_entities(),
            items_on_ground=engine.entity_manager.items_on_ground,
            resource_nodes=engine.entity_manager.resource_nodes,
            survival=engine.game_state_data.survival,
            floating_texts=engine.fx_manager.floating_texts,
            particles=engine.fx_manager.particles,
            look_cursor=engine.look_cursor,
            game_state=engine.game_state_data.game_state,
            time_system=engine.time_system,
            dungeon_level=engine.game_state_data.dungeon_level,
            msg_log=engine.msg_log,
            fx_manager=engine.fx_manager,
            notification_manager=engine.notification_manager,
            achievement_notifications=getattr(
                engine.game_state_data.player, "achievement_notifications", []
            ),
            current_weather=getattr(engine, "current_weather", "fog"),
            casting_spell=getattr(engine, "casting_spell", None),
            frame_count=getattr(engine, "frame_count", 0),
            inventory_target=engine.inventory_target,
            inventory_tab=engine.inventory_tab,
            inventory_cursor=engine.inventory_cursor,
            pet_inventory=engine.game_state_data.pet_inventory,
            altar_pos=engine.game_state_data.altar_pos,
            localization_manager=engine.localization_manager,
            world_a_data=engine.game_state_data.world_a_data,
            toxicity_manager=engine.skill_eater_toxicity_manager,
            skill_eater_combat_system=engine.skill_eater_combat_system,
            color_vision_mode=engine.config_mgr.get("accessibility.color_vision") or "none",
            last_scan_result=getattr(engine, "last_scan_result", None),
        )
        RenderSystem.render_all(console, render_context)

        # 3. Particle pass (topmost layer)
        renderer.render_particles_pass(cam_x, cam_y)

        # End frame
        renderer.end_frame(1 / 60)
