from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import json
import math


@dataclass
class GlyphMetrics:
    advance: float
    bearing_x: float
    bearing_y: float
    width: int
    height: int
    u0: float
    v0: float
    u1: float
    v1: float


class MSDFAtlas:
    def __init__(self, atlas_size: int = 4096, padding: int = 2):
        self.atlas_size = atlas_size
        self.padding = padding
        self.texture: Optional[np.ndarray] = None
        self.glyphs: Dict[str, GlyphMetrics] = {}
        self.font_size: int = 0
        self.chars: str = ""

    def generate_atlas(self, font_path: str, chars: str, size: int, padding: int = 2) -> None:
        self.font_size = size
        self.chars = chars
        self.padding = padding

        pil_font = ImageFont.truetype(font_path, size)
        
        glyphs_data = []
        max_width = 0
        max_height = 0

        for ch in chars:
            bbox = pil_font.getbbox(ch)
            if bbox:
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                max_width = max(max_width, w)
                max_height = max(max_height, h)
                
                img = Image.new('L', (w + padding * 2, h + padding * 2), 0)
                draw = ImageDraw.Draw(img)
                draw.text((padding - bbox[0], padding - bbox[1]), ch, font=pil_font, fill=255)
                
                sdf = self._compute_sdf(img)
                pixels = np.stack([sdf] * 4, axis=-1).astype(np.float32) / 255.0
                
                advance = pil_font.getlength(ch)
                bearing_x = -bbox[0]
                bearing_y = h + bbox[1]
                
                glyphs_data.append((ch, pixels, advance, bearing_x, bearing_y, w, h))
            else:
                glyphs_data.append((ch, None, 0, 0, 0, 0, 0))

        cols = int(math.sqrt(len(chars))) + 1
        rows = (len(chars) + cols - 1) // cols
        cell_w = max_width + padding * 2
        cell_h = max_height + padding * 2
        
        atlas_w = min(cols * cell_w, self.atlas_size)
        atlas_h = min(rows * cell_h, self.atlas_size)
        
        cols = atlas_w // cell_w
        rows = atlas_h // cell_h
        
        self.texture = np.zeros((atlas_h, atlas_w, 4), dtype=np.float32)
        
        x = 0
        y = 0
        for ch, pixels, advance, bearing_x, bearing_y, w, h in glyphs_data:
            if pixels is not None:
                dst_x = x * cell_w + padding
                dst_y = y * cell_h + padding
                
                self.texture[dst_y:dst_y+h, dst_x:dst_x+w] = pixels[:h, :w]
                
                u0 = dst_x / atlas_w
                v0 = dst_y / atlas_h
                u1 = (dst_x + w) / atlas_w
                v1 = (dst_y + h) / atlas_h
                
                self.glyphs[ch] = GlyphMetrics(
                    advance=advance,
                    bearing_x=bearing_x,
                    bearing_y=bearing_y,
                    width=w,
                    height=h,
                    u0=u0, v0=v0, u1=u1, v1=v1
                )
            else:
                self.glyphs[ch] = GlyphMetrics(
                    advance=0, bearing_x=0, bearing_y=0,
                    width=0, height=0, u0=0, v0=0, u1=0, v1=0
                )
            
            x += 1
            if x >= cols:
                x = 0
                y += 1

    def _compute_sdf(self, img: Image.Image) -> np.ndarray:
        arr = np.array(img, dtype=np.float32)
        h, w = arr.shape
        
        inside = arr > 128
        if not np.any(inside) or not np.any(~inside):
            return np.full((h, w), 128, dtype=np.float32)
        
        from scipy.ndimage import distance_transform_edt
        dist_in = distance_transform_edt(inside)
        dist_out = distance_transform_edt(~inside)
        sdf = dist_out - dist_in
        
        max_dist = max(np.max(dist_in), np.max(dist_out))
        if max_dist > 0:
            sdf = 128 + (sdf / max_dist) * 127
        else:
            sdf = np.full((h, w), 128, dtype=np.float32)
        
        return np.clip(sdf, 0, 255)

    def get_glyph(self, ch: str) -> Optional[GlyphMetrics]:
        return self.glyphs.get(ch)

    def get_texture_array(self) -> np.ndarray:
        if self.texture is None:
            raise RuntimeError("Atlas not generated")
        return self.texture

    def save_atlas(self, texture_path: str, meta_path: str) -> None:
        if self.texture is None:
            raise RuntimeError("Atlas not generated")
        
        img = Image.fromarray((self.texture * 255).astype(np.uint8), 'RGBA')
        img.save(texture_path)
        
        meta = {
            "atlas_size": self.atlas_size,
            "font_size": self.font_size,
            "padding": self.padding,
            "chars": self.chars,
            "glyphs": {
                ch: {
                    "advance": gm.advance,
                    "bearing_x": gm.bearing_x,
                    "bearing_y": gm.bearing_y,
                    "width": gm.width,
                    "height": gm.height,
                    "u0": gm.u0, "v0": gm.v0, "u1": gm.u1, "v1": gm.v1
                }
                for ch, gm in self.glyphs.items()
            }
        }
        with open(meta_path, 'w') as f:
            json.dump(meta, f, indent=2)

    @classmethod
    def load_atlas(cls, texture_path: str, meta_path: str) -> 'MSDFAtlas':
        with open(meta_path, 'r') as f:
            meta = json.load(f)
        
        atlas = cls(meta["atlas_size"], meta["padding"])
        atlas.font_size = meta["font_size"]
        atlas.chars = meta["chars"]
        
        img = Image.open(texture_path)
        atlas.texture = np.array(img, dtype=np.float32) / 255.0
        
        for ch, gm in meta["glyphs"].items():
            atlas.glyphs[ch] = GlyphMetrics(
                advance=gm["advance"],
                bearing_x=gm["bearing_x"],
                bearing_y=gm["bearing_y"],
                width=gm["width"],
                height=gm["height"],
                u0=gm["u0"], v0=gm["v0"], u1=gm["u1"], v1=gm["v1"]
            )
        
        return atlas