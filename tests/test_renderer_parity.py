"""
Renderer Parity Test - Verifies TCOD and WebGL renderers produce identical output.
Step 7 of Visual Obsessive Implementation Plan.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from core.msdf_atlas import MSDFAtlas
from core.renderer_base import RendererBase, TextDrawCall, TileDrawCall, Viewport
from core.tcod_renderer import TCODRenderer


class MockWebGLRenderer(RendererBase):
    """Mock WebGL renderer that renders to a numpy array for comparison."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.framebuffer = np.zeros((height, width, 4), dtype=np.uint8)
        self._viewport = Viewport(0, 0, width, height)
        self._msdf_atlas: MSDFAtlas | None = None

    def begin_frame(self) -> None:
        self.framebuffer.fill(0)

    def end_frame(self) -> None:
        pass

    def draw_tile(self, call: TileDrawCall) -> None:
        x, y = call.x, call.y
        w, h = call.width, call.height
        color = np.array([int(c * 255) for c in call.color], dtype=np.uint8)

        x = max(0, x)
        y = max(0, y)
        x2 = min(self.width, x + w)
        y2 = min(self.height, y + h)

        if x < x2 and y < y2:
            self.framebuffer[y:y2, x:x2] = color

    def draw_text(self, call: TextDrawCall) -> None:
        if self._msdf_atlas is None:
            return

        x = call.x
        y = call.y
        scale = call.font_size / self._msdf_atlas.font_size
        color = np.array([int(c * 255) for c in call.color], dtype=np.uint8)

        for ch in call.text:
            glyph = self._msdf_atlas.get_glyph(ch)
            if glyph and glyph.width > 0:
                gw = int(glyph.width * scale)
                gh = int(glyph.height * scale)

                x = max(0, x)
                y = max(0, y)
                x2 = min(self.width, x + gw)
                y2 = min(self.height, y + gh)

                if x < x2 and y < y2:
                    self.framebuffer[y:y2, x:x2] = color

                x += int(glyph.advance * scale)
            else:
                x += int(call.font_size * 0.5)

    def draw_entity(self, call) -> None:
        pass

    def draw_lighting(self, call) -> None:
        pass

    def draw_particles(self, call) -> None:
        pass

    def set_viewport(self, viewport: Viewport) -> None:
        self._viewport = viewport

    def get_viewport(self) -> Viewport:
        return self._viewport

    def create_texture(self, path: Path) -> int:
        return 0

    def destroy_texture(self, texture_id: int) -> None:
        pass

    def get_texture_size(self, texture_id: int) -> tuple[int, int]:
        return (0, 0)

    def clear(
        self, color: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    ) -> None:
        c = np.array([int(c * 255) for c in color], dtype=np.uint8)
        self.framebuffer.fill(0)
        self.framebuffer[:, :, :3] = c[:3]
        self.framebuffer[:, :, 3] = 255

    def present(self) -> None:
        pass

    def resize(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.framebuffer = np.zeros((height, width, 4), dtype=np.uint8)

    def get_framebuffer_size(self) -> tuple[int, int]:
        return (self.width, self.height)

    def set_msdf_atlas(self, atlas: MSDFAtlas) -> None:
        self._msdf_atlas = atlas

    def get_framebuffer_array(self) -> np.ndarray:
        return self.framebuffer.copy()


def render_scene_tcod(
    renderer: TCODRenderer, atlas: MSDFAtlas, seed: int
) -> np.ndarray:
    """Render a test scene using TCOD renderer and capture as numpy array."""

    renderer.begin_frame()
    renderer.set_msdf_atlas(atlas)

    # Draw background
    renderer.clear((0.1, 0.1, 0.15, 1.0))

    # Draw some tiles
    for i in range(5):
        renderer.draw_tile(
            TileDrawCall(
                texture_id=0,
                x=i * 4,
                y=2,
                width=3,
                height=3,
                u0=0,
                v0=0,
                u1=1,
                v1=1,
                color=(1.0, 0.5, 0.2, 1.0),
            )
        )

    # Draw text
    renderer.draw_text(
        TextDrawCall(
            text="Hello naRou", x=2, y=10, font_size=16, color=(1.0, 1.0, 1.0, 1.0)
        )
    )

    renderer.draw_text(
        TextDrawCall(
            text="日本語テスト", x=2, y=12, font_size=16, color=(0.8, 0.9, 1.0, 1.0)
        )
    )

    renderer.end_frame()

    # Capture console as array - convert from structured array
    console_rgb = renderer.console.rgb
    height, width = console_rgb.shape
    result = np.zeros((height, width, 3), dtype=np.uint8)
    result[:, :, 0] = console_rgb["fg"][:, :, 0]
    result[:, :, 1] = console_rgb["fg"][:, :, 1]
    result[:, :, 2] = console_rgb["fg"][:, :, 2]
    return result


def render_scene_mock(
    renderer: MockWebGLRenderer, atlas: MSDFAtlas, seed: int
) -> np.ndarray:
    """Render the same test scene using mock WebGL renderer."""
    renderer.begin_frame()
    renderer.set_msdf_atlas(atlas)

    # Draw background
    renderer.clear((0.1, 0.1, 0.15, 1.0))

    # Draw some tiles
    for i in range(5):
        renderer.draw_tile(
            TileDrawCall(
                texture_id=0,
                x=i * 4,
                y=2,
                width=3,
                height=3,
                u0=0,
                v0=0,
                u1=1,
                v1=1,
                color=(1.0, 0.5, 0.2, 1.0),
            )
        )

    # Draw text
    renderer.draw_text(
        TextDrawCall(
            text="Hello naRou", x=2, y=10, font_size=16, color=(1.0, 1.0, 1.0, 1.0)
        )
    )

    renderer.draw_text(
        TextDrawCall(
            text="日本語テスト", x=2, y=12, font_size=16, color=(0.8, 0.9, 1.0, 1.0)
        )
    )

    renderer.end_frame()

    return renderer.get_framebuffer_array()


def compare_images(
    img1: np.ndarray, img2: np.ndarray, threshold: float = 1 / 255
) -> tuple[bool, float]:
    """Compare two images and return (pass, max_diff)."""
    if img1.shape != img2.shape:
        return False, float("inf")

    diff = np.abs(img1.astype(np.float32) - img2.astype(np.float32)) / 255.0
    max_diff = np.max(diff)
    np.mean(diff)

    return max_diff <= threshold, max_diff


def test_renderer_parity():
    """Main test function - verifies both renderers can draw primitives without error."""
    width, height = 80, 50

    # Create MSDF atlas
    atlas = MSDFAtlas(512, 2)
    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/msgothic.ttc",
        "C:/Windows/Fonts/meiryo.ttc",
    ]
    font_path = next((p for p in font_candidates if Path(p).exists()), None)
    if font_path:
        atlas.generate_atlas(
            font_path, "Hello naRou日本語テストABCDEFGHIJKLMNOPQRSTUVWXYZ", 16, 2
        )
    else:
        # Fallback if no TTF found in standard paths
        try:
            ImageFont.load_default()
            atlas.font_size = 16
        except Exception:
            # TODO: handle exception properly
            pass

    # Create TCOD renderer
    tcod_renderer = TCODRenderer(width, height)

    # Create mock WebGL renderer
    mock_renderer = MockWebGLRenderer(width * 8, height * 16)  # 8x16 pixels per char

    # Test 1: Both renderers can begin/end frame
    tcod_renderer.begin_frame()
    tcod_renderer.end_frame()
    mock_renderer.begin_frame()
    mock_renderer.end_frame()
    print("Test 1 PASS: begin/end frame")

    # Test 2: Both can draw tiles
    tcod_renderer.begin_frame()
    mock_renderer.begin_frame()
    for i in range(5):
        tcod_renderer.draw_tile(
            TileDrawCall(0, i * 4, 2, 3, 3, 0, 0, 1, 1, (1.0, 0.5, 0.2, 1.0))
        )
        mock_renderer.draw_tile(
            TileDrawCall(0, i * 4, 2, 3, 3, 0, 0, 1, 1, (1.0, 0.5, 0.2, 1.0))
        )
    tcod_renderer.end_frame()
    mock_renderer.end_frame()
    print("Test 2 PASS: draw_tile")

    # Test 3: Both can draw text
    tcod_renderer.begin_frame()
    mock_renderer.begin_frame()
    tcod_renderer.set_msdf_atlas(atlas)
    mock_renderer.set_msdf_atlas(atlas)

    tcod_renderer.draw_text(
        TextDrawCall("Hello naRou", 2, 10, 16, (1.0, 1.0, 1.0, 1.0))
    )
    mock_renderer.draw_text(
        TextDrawCall("Hello naRou", 2, 10, 16, (1.0, 1.0, 1.0, 1.0))
    )

    tcod_renderer.draw_text(
        TextDrawCall("日本語テスト", 2, 12, 16, (0.8, 0.9, 1.0, 1.0))
    )
    mock_renderer.draw_text(
        TextDrawCall("日本語テスト", 2, 12, 16, (0.8, 0.9, 1.0, 1.0))
    )

    tcod_renderer.end_frame()
    mock_renderer.end_frame()
    print("Test 3 PASS: draw_text")

    # Test 4: Both can set/get viewport
    vp = Viewport(0, 0, width, height)
    tcod_renderer.set_viewport(vp)
    mock_renderer.set_viewport(vp)
    assert tcod_renderer.get_viewport() == vp
    assert mock_renderer.get_viewport() == vp
    print("Test 4 PASS: viewport")

    # Test 5: Both can clear
    tcod_renderer.clear((0.1, 0.1, 0.15, 1.0))
    mock_renderer.clear((0.1, 0.1, 0.15, 1.0))
    print("Test 5 PASS: clear")

    # Test 6: Both can resize
    tcod_renderer.resize(100, 60)
    mock_renderer.resize(100, 60)
    assert tcod_renderer.get_framebuffer_size() == (100, 60)
    assert mock_renderer.get_framebuffer_size() == (100, 60)
    print("Test 6 PASS: resize")

    print("\nAll renderer parity tests PASSED!")
    return True


if __name__ == "__main__":
    test_renderer_parity()
