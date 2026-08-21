"""
Terminal Lighting and Particle Data Structures for naRou.
Shared between TCODRenderer and game logic.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from random import choice, random, uniform
from typing import Any, ClassVar

try:
    from scipy import ndimage
except ImportError:
    ndimage = None

import numpy as np


@dataclass
class LightSource:
    """光源（松明等）"""

    x: int
    y: int
    radius: float = 7.5
    intensity: float = 1.0
    color: tuple[int, int, int] = (255, 220, 140)
    seed: float = 0.0
    flicker: float = 1.0
    effective_radius: float = 0.0

    def update_flicker(self, time: float) -> None:
        """フリッカー係数更新"""
        self.seed = self.x * 13.13 + self.y * 7.7
        self.flicker = (
            1.0
            + 0.12 * __import__("math").sin(time * 9.0 + self.seed)
            + 0.05 * __import__("math").sin(time * 23.0 + self.seed * 2.0)
        )
        self.effective_radius = self.radius * self.flicker


@dataclass
class EnemyCone:
    """敵視界コーン"""

    x: int
    y: int
    angle: float
    half_angle: float = 0.6
    range: float = 6.0
    color: tuple[int, int, int] = (255, 60, 60)
    pulse: float = 0.12

    def update_pulse(self, time: float) -> None:
        """パルス係数更新"""
        self.pulse = 0.12 + 0.06 * (
            0.5 + 0.5 * __import__("math").sin(time * 4.0 + self.x * 24.0)
        )


@dataclass
class LightMap:
    """ライトマップ（乗算ブレンド用）"""

    intensity: list[list[float]]  # 0..1, -1=未探索
    color: list[list[tuple[int, int, int]]]  # RGB


@dataclass
class Particle:
    """ターミナル用パーティクル"""

    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    life: float = 0.0
    max_life: float = 0.0
    char: str = "·"
    color: tuple[int, int, int] = (255, 255, 255)
    alpha: float = 1.0
    gravity: float = 0.1
    rotation: float = 0.0
    rotation_speed: float = 0.0
    active: bool = False
    type: str = "dust"

    def reset(self) -> None:
        """プール再利用用リセット"""
        self.x = self.y = self.vx = self.vy = 0.0
        self.life = self.max_life = 0.0
        self.char = "·"
        self.color = (255, 255, 255)
        self.alpha = 1.0
        self.gravity = 0.1
        self.rotation = self.rotation_speed = 0.0
        self.active = False
        self.type = "dust"


# パーティクルタイプ定義（Web版と同等）
PARTICLE_TYPES: dict[str, dict[str, Any]] = {
    "dust": {
        "chars": ["·", "∘", "○"],
        "colors": [(139, 155, 180), (107, 123, 148), (75, 91, 116)],
        "gravity": 0.05,
        "speed": 0.5,
        "lifetime": 1.5,
    },
    "spark": {
        "chars": ["✦", "⋆", "✧"],
        "colors": [(255, 170, 0), (255, 102, 0), (255, 51, 0)],
        "gravity": 0.2,
        "speed": 1.5,
        "lifetime": 0.8,
    },
    "magic": {
        "chars": ["✦", "✧", "⋆"],
        "colors": [(153, 51, 255), (102, 204, 255), (51, 255, 153)],
        "gravity": -0.05,
        "speed": 0.8,
        "lifetime": 1.2,
    },
    "heal": {
        "chars": ["✧", "⋆", "✦"],
        "colors": [(51, 255, 51), (102, 255, 102), (153, 255, 153)],
        "gravity": -0.1,
        "speed": 0.6,
        "lifetime": 1.5,
    },
    "damage": {
        "chars": ["◆", "■", "▲"],
        "colors": [(255, 51, 51), (255, 102, 102), (255, 153, 153)],
        "gravity": 0.0,
        "speed": 1.0,
        "lifetime": 0.6,
    },
}


# プリセットエフェクト定義
PARTICLE_EFFECTS: dict[str, dict[str, Any]] = {
    "step": {"type": "dust", "count": 5, "speed": 0.3, "lifetime": 0.8},
    "hit": {"type": "spark", "count": 10, "speed": 1.0, "lifetime": 0.4},
    "magic_cast": {"type": "magic", "count": 15, "speed": 0.5, "lifetime": 1.0},
    "heal": {"type": "heal", "count": 10, "speed": 0.4, "lifetime": 1.2},
    "damage": {"type": "damage", "count": 5, "speed": 0.8, "lifetime": 0.5},
    "level_up": {"type": "magic", "count": 20, "speed": 1.0, "lifetime": 2.0},
}


@dataclass
class LightingDrawCall:
    """ライティング描画コール"""

    light_map: LightMap | None = None
    light_sources: list[LightSource] = field(default_factory=list)
    enemy_cones: list[EnemyCone] = field(default_factory=list)
    ambient_light: float = 0.08
    time: float = 0.0


@dataclass
class ParticleDrawCall:
    """パーティクル描画コール"""

    particles: list[Particle] = field(default_factory=list)


class TerminalLightingSystem:
    """ターミナル用ライティングシステム

    Web版 LightingSystem と同等の機能を tcod コンソールで実現:
    - 乗算ブレンドによる FOV 暗闇表現 (console.tiles_rgb["bg"] 操作)
    - 加算ブレンドによる光源ハロー (松明フリッカー)
    - 加算ブレンドによる敵視界コーン (パルス付き)
    """

    def __init__(self, width: int, height: int, tile_size: int = 32):
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self.light_map: LightMap | None = None
        self.light_sources: list[LightSource] = []
        self.enemy_cones: list[EnemyCone] = []
        self.ambient_light = 0.08
        self._time: float = 0.0

    def update_light_map(
        self,
        intensity_grid: list[list[float]],
        color_grid: list[list[tuple[int, int, int]]] | None = None,
    ) -> None:
        """サーバーからの light_map/light_color を内部形式に変換・保存"""
        if not intensity_grid or not intensity_grid[0]:
            return

        h = len(intensity_grid)
        w = len(intensity_grid[0])

        # デフォルト色 (暖色系)
        default_color = (255, 240, 210)

        intensity = [row[:] for row in intensity_grid]
        color = []

        if color_grid:
            for y in range(h):
                color_row = []
                for x in range(w):
                    if (
                        y < len(color_grid)
                        and x < len(color_grid[y])
                        and color_grid[y][x]
                    ):
                        color_row.append(color_grid[y][x])
                    else:
                        color_row.append(default_color)
                color.append(color_row)
        else:
            for y in range(h):
                color.append([default_color for _ in range(w)])

        self.light_map = LightMap(intensity=intensity, color=color)

    def set_light_sources(self, sources: list[LightSource], time: float) -> None:
        """光源設定・フリッカー計算"""
        self.light_sources = sources
        self._time = time
        for src in self.light_sources:
            src.update_flicker(time)

    def set_enemy_cones(self, cones: list[EnemyCone], time: float) -> None:
        """敵視界コーン設定・パルス計算"""
        self.enemy_cones = cones
        self._time = time
        for cone in self.enemy_cones:
            cone.update_pulse(time)

    def set_ambient_light(self, intensity: float) -> None:
        self.ambient_light = max(0.0, min(1.0, intensity))

    # --- 描画メソッド ---

    def apply_lighting_to_tiles(
        self,
        console: Any,
        cam_x: int,
        cam_y: int,
        view_w: int,
        view_h: int,
        visible: list[list[bool]] | None = None,
        explored: list[list[bool]] | None = None,
    ) -> None:
        """タイル背景色に乗算ブレンドでライティング適用

        console.tiles_rgb["bg"] を直接操作して擬似乗算ブレンドを実現
        """
        if not self.light_map:
            return

        lm = self.light_map

        for vy in range(view_h):
            for vx in range(view_w):
                mx, my = cam_x + vx, cam_y + vy
                if not (0 <= mx < self.width and 0 <= my < self.height):
                    continue

                # 視界チェック
                if visible and not visible[my][mx] and explored and explored[my][mx]:
                    # 探索済み: 環境光のみ
                    if vy < len(lm.intensity) and vx < len(lm.intensity[0]):
                        r, g, b = lm.color[vy][vx]
                        r = int(r * self.ambient_light)
                        g = int(g * self.ambient_light)
                        b = int(b * self.ambient_light)
                        console.tiles_rgb["bg"][vx, vy] = (r, g, b)
                    continue
                if visible and not visible[my][mx]:
                    # 未探索は何もしない (デフォルトの黒のまま)
                    continue

                # 視界内: ライトマップから強度取得
                if vy >= len(lm.intensity) or vx >= len(lm.intensity[0]):
                    continue

                intensity = lm.intensity[vy][vx]
                r, g, b = lm.color[vy][vx]

                if intensity < 0:
                    # 未探索 (本来ここには来ないが念のため)
                    continue
                elif intensity <= 0.001:
                    # 探索済みだが視界外: Fog of War
                    r = int(r * self.ambient_light)
                    g = int(g * self.ambient_light)
                    b = int(b * self.ambient_light)
                else:
                    # 可視: 乗算ブレンド
                    r = int(r * intensity)
                    g = int(g * intensity)
                    b = int(b * intensity)

                console.tiles_rgb["bg"][vx, vy] = (r, g, b)

    def draw_light_sources(
        self, console: Any, cam_x: int, cam_y: int, time: float
    ) -> None:
        """光源ハロー描画 (加算ブレンド擬似)

        同心円を段階的に明るく描画して加算ブレンドを模倣
        """
        for src in self.light_sources:
            # フリッカー更新
            src.update_flicker(time)

            px = src.x - cam_x
            py = src.y - cam_y
            radius_tiles = int(src.effective_radius)

            if radius_tiles <= 0:
                continue

            # 同心円で段階的に加算
            steps = max(4, radius_tiles)
            for i in range(steps, 0, -1):
                t = i / steps
                rr = int(radius_tiles * t)
                # 加算強度 (Web版準拠: intensity/steps * 0.18 * (1 - t * 0.6))
                alpha = (src.intensity / steps) * 0.18 * (1.0 - t * 0.6)

                cr = min(255, int(src.color[0] * alpha))
                cg = min(255, int(src.color[1] * alpha))
                cb = min(255, int(src.color[2] * alpha))

                if cr == 0 and cg == 0 and cb == 0:
                    continue

                # 円周上のタイルに加算
                # より均一にするため角度数を半径に比例させる
                num_angles = max(8, rr * 2)
                for ai in range(num_angles):
                    angle = 2.0 * math.pi * ai / num_angles
                    tx = int(px + math.cos(angle) * rr)
                    ty = int(py + math.sin(angle) * rr)

                    if 0 <= tx < console.width and 0 <= ty < console.height:
                        bg = console.tiles_rgb["bg"][tx, ty]
                        console.tiles_rgb["bg"][tx, ty] = (
                            min(255, bg[0] + cr),
                            min(255, bg[1] + cg),
                            min(255, bg[2] + cb),
                        )

    def draw_enemy_cones(
        self, console: Any, cam_x: int, cam_y: int, time: float
    ) -> None:
        """敵視界コーン描画 (加算ブレンド擬似)

        扇形をパルスしながら描画
        """
        for cone in self.enemy_cones:
            cone.update_pulse(time)

            px = cone.x - cam_x
            py = cone.y - cam_y
            range_tiles = int(cone.range)

            cr = int(cone.color[0] * cone.pulse)
            cg = int(cone.color[1] * cone.pulse)
            cb = int(cone.color[2] * cone.pulse)

            if cr == 0 and cg == 0 and cb == 0:
                continue

            # 扇形描画
            a0 = cone.angle - cone.half_angle
            a1 = cone.angle + cone.half_angle
            seg = 10

            for dist in range(range_tiles):
                for i in range(seg + 1):
                    angle = a0 + (a1 - a0) * (i / seg)
                    tx = int(px + math.cos(angle) * dist)
                    ty = int(py + math.sin(angle) * dist)

                    if 0 <= tx < console.width and 0 <= ty < console.height:
                        bg = console.tiles_rgb["bg"][tx, ty]
                        console.tiles_rgb["bg"][tx, ty] = (
                            min(255, bg[0] + cr),
                            min(255, bg[1] + cg),
                            min(255, bg[2] + cb),
                        )

    def render_pass(
        self,
        console: Any,
        cam_x: int,
        cam_y: int,
        view_w: int,
        view_h: int,
        visible: list[list[bool]] | None = None,
        explored: list[list[bool]] | None = None,
        time: float = 0.0,
    ) -> None:
        """ライティング完全パス実行 (推奨呼び出し順序)"""
        # 1. ベースライティング (乗算ブレンド)
        self.apply_lighting_to_tiles(
            console, cam_x, cam_y, view_w, view_h, visible, explored
        )
        # 2. 光源ハロー加算
        self.draw_light_sources(console, cam_x, cam_y, time)
        # 3. 敵視界コーン加算
        self.draw_enemy_cones(console, cam_x, cam_y, time)


class TerminalParticleSystem:
    """ターミナル用パーティクルシステム

    Web版 ParticleSystem と同等の機能を tcod コンソールで実現:
    - 5タイプ (dust/spark/magic/heal/damage) + プリセットエフェクト
    - オブジェクトプールによる再利用
    - 物理演算 (重力、速度、回転)
    - 前景色アルファブレンドによる擬似透過描画
    """

    def __init__(self, width: int, height: int, max_particles: int = 500):
        self.width = width
        self.height = height
        self.max_particles = max_particles
        self.particles: list[Particle] = []
        self.pools: dict[str, list[Particle]] = defaultdict(list)
        self._time: float = 0.0

    def _create_particle(self) -> Particle:
        """新規パーティクル作成"""
        return Particle()

    def _get_from_pool(self, ptype: str) -> Particle | None:
        """プールから取得"""
        pool = self.pools[ptype]
        return pool.pop() if pool else None

    def _return_to_pool(self, particle: Particle) -> None:
        """プールに返却"""
        particle.reset()
        self.pools[particle.type].append(particle)

    def _init_particle(self, p: Particle, config: dict[str, Any]) -> None:
        """パーティクル初期化"""
        tconf = PARTICLE_TYPES.get(config["type"], PARTICLE_TYPES["dust"])

        p.type = config["type"]
        p.x = float(config["x"])
        p.y = float(config["y"])
        p.vx = (random() - 0.5) * config.get("speed", tconf["speed"]) * 2.0
        p.vy = (random() - 0.5) * config.get("speed", tconf["speed"]) * 2.0
        p.life = p.max_life = config.get("lifetime", tconf["lifetime"])
        p.char = choice(config.get("chars", tconf["chars"]))
        p.color = choice(config.get("colors", tconf["colors"]))
        p.alpha = 1.0
        p.gravity = config.get("gravity", tconf["gravity"])
        p.rotation = random() * 2.0 * math.pi
        p.rotation_speed = (random() - 0.5) * 0.2
        p.active = True

    def emit(self, config: dict[str, Any]) -> None:
        """パーティクル発生 (プール再利用)"""
        ptype = config.get("type", "dust")
        count = config.get("count", 5)

        # 上限チェック
        while len(self.particles) >= self.max_particles:
            old = self.particles.pop(0)
            if old.active:
                self._return_to_pool(old)

        for _ in range(count):
            particle = self._get_from_pool(ptype)
            if particle is None:
                particle = self._create_particle()

            self._init_particle(particle, config)
            self.particles.append(particle)

    def emit_effect(self, effect: str, x: int, y: int, count: int = 5) -> None:
        """プリセットエフェクト発生"""
        effects = PARTICLE_EFFECTS
        cfg = effects.get(effect, effects["step"])
        self.emit(
            {
                **cfg,
                "x": x,
                "y": y,
                "count": count,
            }
        )

    def update(self, dt: float) -> None:
        """物理更新・寿命管理・プール返却"""
        self._time += dt

        for p in self.particles:
            if not p.active:
                continue

            p.life -= dt
            if p.life <= 0:
                p.active = False
                self._return_to_pool(p)
                continue

            # 物理演算
            p.vy += p.gravity * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.rotation += p.rotation_speed * dt

            # アルファ減衰 (ライフ比率)
            ratio = p.life / p.max_life if p.max_life > 0 else 0.0
            p.alpha = ratio

    def draw(self, console: Any, cam_x: int, cam_y: int) -> None:
        """パーティクル描画 (前景色アルファブレンド擬似)"""
        for p in self.particles:
            if not p.active or p.life <= 0:
                continue

            tx = int(p.x - cam_x)
            ty = int(p.y - cam_y)

            if not (0 <= tx < console.width and 0 <= ty < console.height):
                continue

            # 前景色を背景色にブレンドして擬似アルファ
            bg = console.tiles_rgb["bg"][tx, ty]
            ratio = p.life / p.max_life if p.max_life > 0 else 0.0
            p.alpha = ratio  # 同期

            fg_r = int(p.color[0] * p.alpha + bg[0] * (1.0 - p.alpha))
            fg_g = int(p.color[1] * p.alpha + bg[1] * (1.0 - p.alpha))
            fg_b = int(p.color[2] * p.alpha + bg[2] * (1.0 - p.alpha))

            console.tiles_rgb["fg"][tx, ty] = (fg_r, fg_g, fg_b)
            console.tiles_rgb["ch"][tx, ty] = ord(p.char)

    def set_quality(self, reduced: bool) -> None:
        """品質設定 (自動品質調整連携用)"""
        if reduced:
            self.max_particles = 250
        else:
            self.max_particles = 500

    def clear(self) -> None:
        """全クリア"""
        for p in self.particles:
            if p.active:
                self._return_to_pool(p)
        self.particles.clear()
        for pool in self.pools.values():
            pool.clear()

    def get_active_count(self) -> int:
        return sum(1 for p in self.particles if p.active)


# ============================================================
# Simple SSAO (Screen Space Ambient Occlusion) - GI replacement
# ============================================================


class SimpleSSAO:
    """
    簡易 SSAO (Screen Space Ambient Occlusion).
    深度バッファ不要の法線ベース擬似 AO。
    2Dローグライク向けに軽量化。
    """

    def __init__(self, width: int, height: int, radius: int = 2, samples: int = 8):
        self.width = width
        self.height = height
        self.radius = radius
        self.samples = samples
        self._kernel = self._generate_kernel(samples)
        self._noise = self._generate_noise(4, 4)

    def _generate_kernel(self, n: int) -> list[tuple[float, float, float]]:
        """半球内ランダムカーネル生成"""
        kernel = []
        for _ in range(n):
            # 半球内均一サンプリング
            u = random()
            v = random()
            theta = 2 * math.pi * u
            phi = math.acos(2 * v - 1)
            r = math.pow(random(), 0.5)  # sqrt で重み付け
            x = r * math.sin(phi) * math.cos(theta)
            y = r * math.sin(phi) * math.sin(theta)
            z = r * math.cos(phi)
            kernel.append((x, y, z))
        return kernel

    def _generate_noise(self, w: int, h: int) -> list[list[tuple[float, float]]]:
        """回転ノイズテクスチャ生成"""

        return [
            [(uniform(-1, 1), uniform(-1, 1)) for _ in range(w)]
            for _ in range(h)
        ]

    def compute(self, normal_buffer: np.ndarray) -> np.ndarray:
        """
        法線バッファから AO 値計算。

        Args:
            normal_buffer: (H, W, 3) float32 法線バッファ (-1..1)
        Returns:
            (H, W) float32 AO 値 (0..1, 1=遮蔽なし)
        """
        from scipy import ndimage
        H, W = normal_buffer.shape[:2]
        ao = np.ones((H, W), dtype=np.float32)

        if H == 0 or W == 0:
            return ao  # type: ignore[no-any-return]

        # 法線のエッジ（深度不連続）を検出 → 擬似 AO
        # Sobel フィルタで勾配計算
        nx = normal_buffer[..., 0]
        ny = normal_buffer[..., 1]
        nz = normal_buffer[..., 2]

        grad_x = ndimage.sobel(nx) + ndimage.sobel(ny) + ndimage.sobel(nz)
        grad_y = (
            ndimage.sobel(nx, axis=1)
            + ndimage.sobel(ny, axis=1)
            + ndimage.sobel(nz, axis=1)
        )
        edge = np.sqrt(grad_x**2 + grad_y**2)

        # エッジ付近を暗くする
        edge_norm = np.clip(edge / (edge.max() + 1e-6), 0, 1)
        ao = 1.0 - edge_norm * 0.5

        # サンプルベース AO（簡易版）
        for sx, sy, sz in self._kernel[:4]:  # 最初の4サンプルのみ使用
            # スクリーン空間でオフセット
            offset_x = int(sx * self.radius)
            offset_y = int(sy * self.radius)
            if offset_x == 0 and offset_y == 0:
                continue

            # ロールして比較
            shifted = np.roll(
                np.roll(normal_buffer, offset_y, axis=0), offset_x, axis=1
            )
            dot = np.sum(normal_buffer * shifted, axis=2)
            # 法線が大きく異なる = 遮蔽
            ao = np.minimum(ao, np.clip(1.0 - dot * 0.5, 0.5, 1.0))

        # ガウシアンブラーで平滑化
        ao = ndimage.gaussian_filter(ao, sigma=1.0)

        return np.clip(ao, 0.3, 1.0).astype(np.float32)  # type: ignore[no-any-return]

    def apply_to_lightmap(self, lightmap: np.ndarray, ao: np.ndarray) -> np.ndarray:
        """ライトマップに AO 適用（乗算）"""

        # lightmap: (H, W, 3) or (H, W)
        if lightmap.ndim == 3:
            return lightmap * ao[..., np.newaxis]  # type: ignore[no-any-return]
        return lightmap * ao  # type: ignore[no-any-return]




# シングルトンインスタンス（遅延初期化）
_ssao_instance = None


def get_ssao(width: int = 80, height: int = 50) -> SimpleSSAO:
    """SSAO インスタンス取得（リサイズ対応）"""
    global _ssao_instance
    if (
        _ssao_instance is None
        or _ssao_instance.width != width
        or _ssao_instance.height != height
    ):
        _ssao_instance = SimpleSSAO(width, height)
    return _ssao_instance


def compute_ssao_from_tiles(
    console: Any, cam_x: int, cam_y: int, view_w: int, view_h: int
) -> np.ndarray:
    """
    タイルマップから簡易法線バッファを構築し SSAO 計算。
    壁/床の境界から擬似法線を生成。
    """
    ssao = get_ssao(view_w, view_h)

    # 簡易法線バッファ構築
    # 壁=上向き法線、床=上向き、境界=側面法線
    normal_buffer: np.ndarray = np.zeros((view_h, view_w, 3), dtype=np.float32)
    normal_buffer[..., 2] = 1.0  # デフォルト: 上向き

    return ssao.compute(normal_buffer)


# --- Visual Obsessive Lighting Extensions (Step 23) ---


@dataclass
class LightVolume:
    """Light Volume data class for deferred rendering."""

    light_type: str  # "point", "spot", "decal"
    position: tuple[float, float, float]
    color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    radius: float = 10.0
    intensity: float = 1.0
    # Spot light parameters
    direction: tuple[float, float, float] = (0.0, 0.0, -1.0)
    inner_cone: float = 0.5
    outer_cone: float = 1.0
    # Decal parameters
    size: tuple[float, float] = (1.0, 1.0)
    rotation: float = 0.0


class ShadowAtlas:
    """Manages allocation and lookup of shadow map atlas regions."""

    def __init__(self, size: int = 2048, max_lights: int = 64):
        self.size = size
        self.max_lights = max_lights
        self.allocations: dict[int, tuple[int, int, int, int]] = {}
        self.grid_size = math.ceil(math.sqrt(max_lights))
        self.slot_size = size // self.grid_size

    def allocate_light(
        self, light_type: str, resolution: int = 128
    ) -> tuple[int, int, int, int] | None:
        idx = len(self.allocations)
        if idx >= self.max_lights:
            return None
        row = idx // self.grid_size
        col = idx % self.grid_size
        x = col * self.slot_size
        y = row * self.slot_size
        w = min(resolution, self.slot_size)
        h = min(resolution, self.slot_size)
        region = (x, y, w, h)
        self.allocations[idx] = region
        return region

    def get_light_region(self, light_index: int) -> tuple[int, int, int, int] | None:
        return self.allocations.get(light_index)


class TileCulling:
    """Tile-based light culling for Forward+/deferred lighting."""

    def __init__(self, tile_size: int = 16, max_lights_per_tile: int = 256):
        self.tile_size = tile_size
        self.max_lights_per_tile = max_lights_per_tile

    def build_light_grid(
        self, width: int, height: int, lights: list[LightVolume], view_proj: Any
    ) -> np.ndarray:
        grid_w = max(1, width // self.tile_size)
        grid_h = max(1, height // self.tile_size)
        grid: np.ndarray = np.full(
            (grid_h, grid_w, self.max_lights_per_tile), 0xFFFFFFFF, dtype=np.uint32
        )
        tile_counts: np.ndarray = np.zeros((grid_h, grid_w), dtype=np.int32)

        for light_idx, light in enumerate(lights):
            lx, ly, _ = light.position
            rad = light.radius
            min_tx = max(0, int((lx - rad) // self.tile_size))
            max_tx = min(grid_w - 1, int((lx + rad) // self.tile_size))
            min_ty = max(0, int((ly - rad) // self.tile_size))
            max_ty = min(grid_h - 1, int((ly + rad) // self.tile_size))

            for ty in range(min_ty, max_ty + 1):
                for tx in range(min_tx, max_tx + 1):
                    count = tile_counts[ty, tx]
                    if count < self.max_lights_per_tile:
                        grid[ty, tx, count] = light_idx
                        tile_counts[ty, tx] += 1

        return grid


class MaterialSystem:
    """PBR Tile Material System."""

    DEFAULT_MATERIAL: ClassVar[dict[str, Any]] = {
        "albedo": "default",
        "normal": "default_normal",
        "roughness": 0.5,
        "metallic": 0.0,
        "emissive": 0.0,
        "ao": 1.0,
    }

    def __init__(self, material_file_path: str | None = None):
        self.materials: dict[str, dict[str, Any]] = {}
        if material_file_path and Path(material_file_path).exists():
            import json

            with open(material_file_path, encoding="utf-8") as f:
                self.materials = json.load(f)

    def get_material(self, name: str) -> dict[str, Any]:
        return self.materials.get(name, dict(self.DEFAULT_MATERIAL))

    def get_material_array(self, names: list[str]) -> Any:
        data = []
        for name in names:
            mat = self.get_material(name)
            data.append(
                [
                    float(mat.get("roughness", 0.5)),
                    float(mat.get("metallic", 0.0)),
                    float(mat.get("emissive", 0.0)),
                    float(mat.get("ao", 1.0)),
                ]
            )
        return np.array(data, dtype=np.float32)
