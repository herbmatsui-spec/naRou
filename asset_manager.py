"""
Asset Manager Module
Manages assets (images, sounds, stories) for world events.
"""

from __future__ import annotations

import csv
import json
import logging
import os
from pathlib import Path

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[ASSET] %(levelname)s: %(message)s'))
    logger.addHandler(handler)


class AssetManager:
    def __init__(self, base_path: str = "assets"):
        self.base_path = base_path
        self.event_assets_path = os.path.join(base_path, "events")
        # アセットのキャッシュ
        self._asset_cache: dict[str, str] = {}
        self._tiny_rogue_tiles: dict[str, str] = {}
        self._audio_sfx: dict[str, str] = {}
        self._emote_sprites: dict[str, str] = {}
        self._tiny_rogue_atlas_meta: dict | None = None
        self._audio_manifest: list[dict] | None = None
        self._initialized = False

    def initialize(self, config: dict | None = None) -> None:
        """Initialize asset manager with config paths."""
        if self._initialized:
            return
        if config and "assets" in config:
            assets = config["assets"]
            self._load_tiny_rogue_tiles(assets.get("tiny_rogue_tiles", "assets/tiles/tiny_rogue/tiles"))
            self._load_tiny_rogue_atlas_meta(assets.get("tiny_rogue_atlas_meta", "assets/tiles/tiny_rogue_atlas_16x16.json"))
            self._load_audio_sfx(assets.get("audio_sfx", "assets/audio"), assets.get("audio_manifest", "assets/audio/manifest.csv"))
            self._load_emote_sprites(
                assets.get("emote_pixel", "assets/emote/pixel"),
                assets.get("emote_tilesheets", "assets/emote/tilesheets"),
                assets.get("emote_spritesheets", "assets/emote/spritesheets")
            )
            logger.info(f"AssetManager initialized: {len(self._tiny_rogue_tiles)} tiles, "
                       f"{len(self._audio_sfx)} audio, {len(self._emote_sprites)} emote sprites")
        else:
            logger.warning("No assets config provided, AssetManager not fully initialized")
        self._initialized = True

    def _load_tiny_rogue_tiles(self, tiles_dir: str) -> None:
        """Load all tiny rogue tile file paths."""
        tiles_path = Path(tiles_dir)
        if tiles_path.exists():
            for ext in ("*.png", "*.jpg", "*.jpeg"):
                for file_path in tiles_path.glob(ext):
                    self._tiny_rogue_tiles[file_path.stem] = str(file_path)
            logger.debug(f"Loaded {len(self._tiny_rogue_tiles)} tiny rogue tiles from {tiles_dir}")
        else:
            logger.warning(f"Tiny rogue tiles directory not found: {tiles_dir}")

    def _load_tiny_rogue_atlas_meta(self, meta_path: str) -> None:
        """Load tiny rogue atlas metadata JSON."""
        path = Path(meta_path)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                self._tiny_rogue_atlas_meta = json.load(f)
            tile_count = len(self._tiny_rogue_atlas_meta.get("tiles", {}))
            logger.debug(f"Loaded tiny rogue atlas metadata: {tile_count} tiles from {meta_path}")
        else:
            logger.warning(f"Tiny rogue atlas metadata not found: {meta_path}")

    def _load_audio_sfx(self, audio_dir: str, manifest_path: str) -> None:
        """Load audio SFX files and manifest."""
        audio_path = Path(audio_dir)
        if audio_path.exists():
            for ext in ("*.ogg", "*.wav", "*.mp3"):
                for file_path in audio_path.glob(ext):
                    self._audio_sfx[file_path.stem] = str(file_path)
            logger.debug(f"Loaded {len(self._audio_sfx)} audio SFX from {audio_dir}")
        else:
            logger.warning(f"Audio directory not found: {audio_dir}")

        manifest_file = Path(manifest_path)
        if manifest_file.exists():
            with open(manifest_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self._audio_manifest = list(reader)
            logger.debug(f"Loaded audio manifest: {len(self._audio_manifest)} entries")
        else:
            logger.warning(f"Audio manifest not found: {manifest_path}")

    def _load_emote_sprites(self, pixel_dir: str, tilesheets_dir: str, spritesheets_dir: str) -> None:
        """Load emote sprites from pixel, tilesheets, and spritesheets directories."""
        for base_dir in [pixel_dir, tilesheets_dir, spritesheets_dir]:
            path = Path(base_dir)
            if path.exists():
                for ext in ("*.png", "*.jpg", "*.jpeg"):
                    for file_path in path.rglob(ext):
                        # Use relative path from base as key
                        rel_key = file_path.relative_to(path).as_posix().replace(".png", "")
                        self._emote_sprites[rel_key] = str(file_path)
                logger.debug(f"Loaded emote sprites from {base_dir}")
            else:
                logger.warning(f"Emote directory not found: {base_dir}")
        logger.info(f"Total emote sprites loaded: {len(self._emote_sprites)}")

    # --- Event Asset Methods (existing) ---
    def get_event_asset_path(self, event_id: str, asset_type: str, asset_name: str) -> str | None:
        """
        イベント固有のアセットパスを取得する。
        :param event_id: イベントID
        :param asset_type: アセットタイプ (例: "image", "sound", "story")
        :param asset_name: アセット名 (ファイル名)
        :return: フルパスまたはNone
        """
        path = os.path.join(self.event_assets_path, event_id, asset_type, asset_name)
        if os.path.exists(path):
            return path
        return None

    def get_event_image_path(self, event_id: str, image_name: str) -> str | None:
        """イベント画像のパスを取得する"""
        return self.get_event_asset_path(event_id, "image", image_name)

    def get_event_sound_path(self, event_id: str, sound_name: str) -> str | None:
        """イベントサウンドのパスを取得する"""
        return self.get_event_asset_path(event_id, "sound", sound_name)

    def get_event_story_path(self, event_id: str, story_name: str) -> str | None:
        """イベントストーリーのパスを取得する"""
        return self.get_event_asset_path(event_id, "story", story_name)

    def list_event_assets(self, event_id: str) -> dict[str, list[str]]:
        """
        イベントのすべてのアセットをリストする。
        :param event_id: イベントID
        :return: {asset_type: [asset_names, ...]}
        """
        event_dir = os.path.join(self.event_assets_path, event_id)
        if not os.path.isdir(event_dir):
            return {}
        assets = {}
        for asset_type in os.listdir(event_dir):
            type_dir = os.path.join(event_dir, asset_type)
            if os.path.isdir(type_dir):
                assets[asset_type] = [
                    f for f in os.listdir(type_dir) if os.path.isfile(os.path.join(type_dir, f))
                ]
        return assets

    # --- Tiny Rogue Tile Methods ---
    def get_tiny_rogue_tile_path(self, tile_name: str) -> str | None:
        """Get path to a tiny rogue tile by stem name (e.g., 'tile_0001')."""
        path = self._tiny_rogue_tiles.get(tile_name)
        if path is None:
            logger.warning(f"Tiny rogue tile not found: {tile_name}")
        return path

    def get_tiny_rogue_atlas_meta(self) -> dict | None:
        """Get the tiny rogue atlas metadata."""
        return self._tiny_rogue_atlas_meta

    def get_tile_atlas_info(self, tile_id: str) -> dict | None:
        """Get atlas coordinate info for a tile ID (e.g., 'TR_FLOOR_01')."""
        if self._tiny_rogue_atlas_meta and "tiles" in self._tiny_rogue_atlas_meta:
            info = self._tiny_rogue_atlas_meta["tiles"].get(tile_id)
            if info is None:
                logger.warning(f"Tile atlas info not found for: {tile_id}")
            return info
        return None

    def get_tile_atlas_info_or_fallback(self, tile_id: str, fallback_id: str = "TR_FLOOR_01") -> dict:
        """Get atlas coordinate info with fallback to a default tile."""
        info = self.get_tile_atlas_info(tile_id)
        if info is None:
            logger.warning(f"Using fallback tile '{fallback_id}' for missing '{tile_id}'")
            info = self.get_tile_atlas_info(fallback_id)
        return info or {"x": 0, "y": 0, "width": 16, "height": 16, "animated": False, "frames": 1, "fps": 1, "directions": 1, "variants": 1}

    def list_tiny_rogue_tiles(self) -> list[str]:
        """List all available tiny rogue tile names."""
        return list(self._tiny_rogue_tiles.keys())

    # --- Audio SFX Methods ---
    def get_audio_sfx_path(self, sfx_name: str) -> str | None:
        """Get path to an audio SFX by stem name."""
        path = self._audio_sfx.get(sfx_name)
        if path is None:
            logger.warning(f"Audio SFX not found: {sfx_name}")
        return path

    def get_audio_sfx_by_id(self, suggested_id: str) -> str | None:
        """Get audio path by suggested_id from manifest."""
        if self._audio_manifest:
            for entry in self._audio_manifest:
                if entry.get("suggested_id") == suggested_id:
                    stem = entry["filename"].replace(".ogg", "").replace(".wav", "")
                    path = self._audio_sfx.get(stem)
                    if path is None:
                        logger.warning(f"Audio file for suggested_id '{suggested_id}' not found")
                    return path
        logger.warning(f"Audio manifest entry not found for suggested_id: {suggested_id}")
        return None

    def get_audio_sfx_or_fallback(self, suggested_id: str, fallback_id: str = "se_footstep_00") -> str | None:
        """Get audio SFX by suggested_id with fallback."""
        path = self.get_audio_sfx_by_id(suggested_id)
        if path is None:
            logger.warning(f"Using fallback audio '{fallback_id}' for missing '{suggested_id}'")
            path = self.get_audio_sfx_by_id(fallback_id)
        return path

    def list_audio_sfx(self) -> list[str]:
        """List all available audio SFX names."""
        return list(self._audio_sfx.keys())

    def get_audio_manifest(self) -> list[dict] | None:
        """Get the full audio manifest."""
        return self._audio_manifest

    # --- Emote Sprite Methods ---
    def get_emote_sprite_path(self, emote_name: str) -> str | None:
        """Get path to an emote sprite by relative name."""
        path = self._emote_sprites.get(emote_name)
        if path is None:
            logger.warning(f"Emote sprite not found: {emote_name}")
        return path

    def get_emote_sprite_or_fallback(self, emote_name: str, fallback_name: str = "style1/emote_anger") -> str | None:
        """Get emote sprite path with fallback."""
        path = self.get_emote_sprite_path(emote_name)
        if path is None:
            logger.warning(f"Using fallback emote '{fallback_name}' for missing '{emote_name}'")
            path = self.get_emote_sprite_path(fallback_name)
        return path

    def list_emote_sprites(self) -> list[str]:
        """List all available emote sprite names."""
        return list(self._emote_sprites.keys())

    def get_emote_tilesheet_path(self, style_name: str) -> str | None:
        """Get path to an emote tilesheet (e.g., 'pixel_style1')."""
        path = self._emote_sprites.get(style_name)
        if path is None:
            logger.warning(f"Emote tilesheet not found: {style_name}")
        return path


ASSET_MANAGER = AssetManager()