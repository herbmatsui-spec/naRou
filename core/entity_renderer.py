"""
Entity Renderer for naRou.
Manages entity animations and rendering for tcod terminal.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List, Any
import math

from core.tile_atlas import TileAtlas, TileUV


@dataclass
class EntityAnimState:
    """エンティティごとのアニメーション状態"""
    entity_id: int              # ユニークID
    tile_id: str                # TileDef ID ("PLAYER", "PET", "ENEMY_GOBLIN"等)
    x: int
    y: int
    direction: int = 0          # 0:下, 1:左, 2:右, 3:上
    state: str = "idle"         # "idle", "walk", "attack", "dead"
    frame: int = 0
    timer: float = 0.0
    fps: int = 10
    loop: bool = True
    attack_timer: float = 0.0   # 攻撃アニメ強制再生用
    atlas: TileAtlas = None

    def update(self, dt: float, new_direction: int, new_state: str, 
               is_attacking: bool = False) -> bool:
        """状態更新・フレーム進行。Trueならフレーム変化"""
        # 向き更新
        self.direction = new_direction
        
        # 死亡状態は最優先で適用
        if new_state == "dead":
            self.state = "dead"
            self.loop = False
            self.attack_timer = 0.0
        # 攻撃状態の強制処理
        elif is_attacking:
            # 攻撃トリガー: タイマーリセット、状態をattackに
            if self.state != "attack":
                self.frame = 0
                self.timer = 0.0
            self.state = "attack"
            self.attack_timer = 0.5  # 0.5秒間attack状態を維持
            self.loop = False
        elif self.attack_timer > 0:
            # 攻撃タイマーが残っている間はattack状態維持
            self.attack_timer -= dt
            if self.attack_timer <= 0 and self.state == "attack":
                self.state = "idle"
                self.loop = True
        else:
            # 攻撃中でない場合のみ状態更新
            self.state = new_state
        
        # フレーム進行
        self.timer += dt
        frame_time = 1.0 / self.fps if self.fps > 0 else 1.0
        if self.timer >= frame_time:
            self.timer = 0.0
            td = self.atlas.defs.get(self.tile_id)
            if td:
                max_frames = td.frames
                self.frame = (self.frame + 1) % max_frames
                if not self.loop and self.frame == 0:
                    # ワンショットアニメ終了
                    if self.state == "attack":
                        self.state = "idle"
                        self.loop = True
                    elif self.state == "dead":
                        # 死亡アニメ終了後は非表示
                        pass
            return True
        return False

    def get_uv(self, scale: str = "32") -> TileUV:
        """現在のフレームUV取得"""
        return self.atlas.get_uv(
            self.tile_id, variant=0, frame=self.frame,
            direction=self.direction, state=self.state, scale=scale
        )


class EntityRenderer:
    """エンティティ描画管理（tcod用）"""
    
    def __init__(self, tile_atlas: TileAtlas):
        self.tile_atlas = tile_atlas
        self.entity_anims: Dict[int, EntityAnimState] = {}  # entity_id -> state
        self._subimage_cache: Dict[Tuple, Any] = {}
        self._next_entity_id = 1
    
    def register_entity(self, tile_id: str, x: int, y: int, 
                        direction: int = 0, state: str = "idle") -> int:
        """新規エンティティ登録、ID返却"""
        eid = self._next_entity_id
        self._next_entity_id += 1
        
        td = self.tile_atlas.defs.get(tile_id)
        fps = td.fps if td else 10
        
        # 死亡状態はループしない
        loop = state != "dead"
        
        self.entity_anims[eid] = EntityAnimState(
            entity_id=eid, tile_id=tile_id, x=x, y=y,
            direction=direction, state=state, atlas=self.tile_atlas, fps=fps, loop=loop
        )
        return eid
    
    def update_entity(self, eid: int, x: int, y: int, 
                      direction: int, state: str, is_attacking: bool = False, dt: float = 1/60) -> None:
        """位置・状態更新"""
        anim = self.entity_anims.get(eid)
        if anim:
            anim.x, anim.y = x, y
            anim.update(dt, direction, state, is_attacking)
    
    def remove_entity(self, eid: int) -> None:
        self.entity_anims.pop(eid, None)
    
    def get_subimage(self, eid: int) -> Optional[Any]:
        """tcod用サブイメージ取得"""
        anim = self.entity_anims.get(eid)
        if not anim:
            return None
        
        key = (anim.tile_id, anim.frame, anim.direction, anim.state)
        if key in self._subimage_cache:
            return self._subimage_cache[key]
        
        # UV取得 → マスター画像から切り出し
        uv = anim.get_uv("32")
        master_path = self.tile_atlas.get_master_image_path(anim.tile_id, "32")
        if not master_path or not master_path.exists():
            return None
        
        # 画像切り出し
        import tcod.image
        import numpy as np
        master_arr = tcod.image.load(master_path.as_posix())  # (height, width, 4)
        sub_arr = master_arr[uv.y:uv.y+uv.h, uv.x:uv.x+uv.w]
        sub = tcod.image.Image(sub_arr.shape[1], sub_arr.shape[0])
        for py in range(uv.h):
            for px in range(uv.w):
                rgba = sub_arr[py, px]
                # put_pixel expects RGB (3 values), not RGBA
                sub.put_pixel(px, py, (rgba[0], rgba[1], rgba[2]))
        
        self._subimage_cache[key] = sub
        return sub
    
    def get_all_entities(self) -> List[Tuple[int, EntityAnimState]]:
        return list(self.entity_anims.items())
    
    def clear_cache(self) -> None:
        self._subimage_cache.clear()


# 向き計算ヘルパー
def calculate_facing(dx: int, dy: int) -> int:
    """移動ベクトルから向き(0:下,1:左,2:右,3:上)を計算"""
    if abs(dx) > abs(dy):
        return 2 if dx > 0 else 1  # 右 or 左
    else:
        return 0 if dy > 0 else 3  # 下 or 上


def calculate_facing_to_target(ent_x: int, ent_y: int, target_x: int, target_y: int) -> int:
    """ターゲットへの向き計算"""
    return calculate_facing(target_x - ent_x, target_y - ent_y)