"""
Entity Renderer Module - Handles entity rendering with direction/state animations
"""

from __future__ import annotations

import math

import tcod

from constants import (
    INTENT_ATTACK,
    INTENT_CAST,
    INTENT_FLEE,
    INTENT_GUARD,
    INTENT_HEAL,
    INTENT_MOVE,
    VIEW_HEIGHT,
    VIEW_WIDTH,
)

# 意図アイコンの色分け (提案2)
_INTENT_COLORS = {
    INTENT_ATTACK: (255, 80, 80),
    INTENT_CAST: (200, 100, 255),
    INTENT_HEAL: (100, 255, 150),
    INTENT_FLEE: (120, 200, 255),
    INTENT_MOVE: (180, 180, 180),
    INTENT_GUARD: (120, 255, 255),
}


def render_entity_intent(console, ent, vx: int, vy: int) -> None:
    """敵の次回行動（意図）を頭上に描画 (提案2)。"""
    intent = getattr(ent, "next_intent", None)
    if not intent:
        return
    if getattr(ent, "is_player", False) or getattr(ent, "is_pet", False):
        return

    # 頭上1マス（エモートの ! は頭上に出るため、意図はその上=頭上2マスに配置）
    iy = vy - 2
    if iy < 0:
        iy = vy - 1
        if iy < 0:
            return

    glyph = intent.get("glyph", "·")
    color = _INTENT_COLORS.get(intent.get("type"), (180, 180, 180))

    # アイコン描画
    try:
        console.print(x=vx, y=iy, string=glyph, fg=color)
    except Exception:  # noqa: BLE001
        pass

    # ラベル描画（アイコンの右隣）
    label = intent.get("label", "")
    if label and 0 <= vx + 1 < VIEW_WIDTH:
        try:
            console.print(x=vx + 1, y=iy, string=label, fg=color)
        except Exception:  # noqa: BLE001
            pass


# Import new entity rendering system
from core.entity_renderer import EntityRenderer as CoreEntityRenderer
from core.entity_renderer import calculate_facing
from core.tile_atlas import TileAtlas
from render_context import RenderContext
from systems import MonsterPreset
from ui_fx_systems import DynamicLighting


class EntityRenderer:
    """エンティティ描画専用クラス（新システム統合版）"""

    # クラスレベルでCoreEntityRendererを共有
    _core_renderer: CoreEntityRenderer = None
    _tile_atlas: TileAtlas = None
    _anim_time: float = 0.0

    @classmethod
    def _get_core_renderer(cls, context: RenderContext) -> CoreEntityRenderer:
        if cls._core_renderer is None:
            cls._tile_atlas = TileAtlas(default_scale="32")
            cls._core_renderer = CoreEntityRenderer(cls._tile_atlas)
        return cls._core_renderer

    @classmethod
    def _get_tile_id(cls, ent) -> str:
        """エンティティからTileDef IDを決定"""
        from feature_flags import is_enabled

        # Tiny Rogueグラフィックが無効な場合は従来のタイルを使用
        if not is_enabled("ENABLE_TINY_ROGUE_GFX"):
            if ent.is_player:
                return "PLAYER"
            elif ent.is_pet:
                return "PET"
            else:
                return "ENEMY_GOBLIN"

        if ent.is_player:
            return "PLAYER"
        elif ent.is_pet:
            if is_enabled("ENABLE_TINY_ROGUE_GFX"):
                pet_type = getattr(ent, "pet_type", None)
                return MonsterPreset.PET_TILE_MAP.get(pet_type, "PET")
            return "PET"
        elif hasattr(ent, "monster_type") and ent.monster_type:
            return MonsterPreset.MONSTER_TILE_MAP.get(ent.monster_type, "ENEMY_GOBLIN")
        else:
            return "ENEMY_GOBLIN"

    @classmethod
    def render(
        cls,
        console: tcod.console.Console,
        context: RenderContext,
        cam_x: int,
        cam_y: int,
        light_sources: list,
    ) -> None:
        """エンティティ描画のメインエントリポイント（新システム統合）"""
        tick = context.frame_count
        dt = 1 / 60  # 固定タイムステップ

        core_renderer = cls._get_core_renderer(context)

        # アニメーション時間更新
        cls._anim_time += dt

        for ent in context.entities:
            if context.game_map.visible[ent.x][ent.y] and ent.hp > 0:
                vx = ent.x - cam_x
                vy = ent.y - cam_y
                if 0 <= vx < VIEW_WIDTH and 0 <= vy < VIEW_HEIGHT:
                    # TileDef ID決定
                    tile_id = cls._get_tile_id(ent)

                    # 向き計算
                    dx = ent.x - ent.prev_x if hasattr(ent, "prev_x") else 0
                    dy = ent.y - ent.prev_y if hasattr(ent, "prev_y") else 0

                    # 移動検知で向き更新
                    if dx != 0 or dy != 0:
                        ent.facing = calculate_facing(dx, dy)
                        ent.moving = True
                    else:
                        ent.moving = False

                    # 向き取得（デフォルト: 下）
                    facing = getattr(ent, "facing", 0)

                    # 状態判定
                    state = "idle"
                    is_attacking = False
                    if getattr(ent, "attacking", False):
                        state = "attack"
                        is_attacking = True
                        ent.attack_timer = 0.5
                    elif getattr(ent, "attack_timer", 0) > 0:
                        ent.attack_timer -= dt
                        state = "attack"
                        if ent.attack_timer <= 0:
                            state = "idle"
                    elif ent.hp <= 0:
                        state = "dead"
                    elif ent.moving:
                        state = "walk"
                    else:
                        state = "idle"

                    # 現在位置を前フレーム用に保存
                    ent.prev_x = ent.x
                    ent.prev_y = ent.y

                    # エンティティID取得・登録
                    if not hasattr(ent, "_render_id"):
                        ent._render_id = core_renderer.register_entity(
                            tile_id, ent.x, ent.y, facing, state
                        )

                    # CoreEntityRendererで状態更新
                    core_renderer.update_entity(
                        ent._render_id, ent.x, ent.y, facing, state, is_attacking, dt
                    )

                    # サブイメージ取得・描画
                    sub_image = core_renderer.get_subimage(ent._render_id)
                    if sub_image:
                        # 呼吸アニメ (bounce)
                        bounce = math.sin(cls._anim_time * 4 + ent.x) * 1.5
                        draw_vy = vy + int(bounce)

                        # ライティング適用
                        base_ent_col = ent.color
                        lit_col, intensity = DynamicLighting.calculate_tile_lighting(
                            ent.x, ent.y, base_ent_col, light_sources
                        )
                        if not ent.is_player and not ent.is_pet and intensity < 0.3:
                            # 敵のシルエット表示
                            # ティントで暗くする
                            pass

                        # ティント適用して描画
                        console.draw_semigraphics(sub_image, vx, draw_vy)

                        # 提案2: 敵の意図を頭上に描画
                        render_entity_intent(console, ent, vx, vy)
                    else:
                        # フォールバック: 文字描画
                        char_to_draw = ent.char
                        if (ent.is_player or ent.is_pet) and (tick % 120 == 1):
                            char_to_draw = "o" if ent.char == "@" else ent.char

                        base_ent_col = ent.color
                        lit_col, intensity = DynamicLighting.calculate_tile_lighting(
                            ent.x, ent.y, base_ent_col, light_sources
                        )
                        if not ent.is_player and not ent.is_pet and intensity < 0.3:
                            ent_col = (70, 70, 90)
                        else:
                            ent_col = lit_col
                        console.print(x=vx, y=vy, string=char_to_draw, fg=ent_col)

                        # 提案2: 敵の意図を頭上に描画
                        render_entity_intent(console, ent, vx, vy)
