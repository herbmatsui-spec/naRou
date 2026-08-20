# Asset Pack Integration Documentation

This document describes the integration of three asset packs into the naRou project:
- **Tiny Rogue** - 16x16 pixel art tiles for dungeon, monsters, items, UI
- **Audio Pack** - 51 OGG sound effects for footsteps, doors, UI, ambient
- **Emote Pack** - 256 emote sprites across 8 pixel styles + tilesheets

## Quick Start

```python
import yaml
from asset_manager import ASSET_MANAGER
from emote_system import play_emote, get_emote_frame, update_emotes

# Load config and initialize
with open("config.yaml") as f:
    config = yaml.safe_load(f)
ASSET_MANAGER.initialize(config)

# Use tiny rogue tiles
tile_path = ASSET_MANAGER.get_tiny_rogue_tile_path("tile_0001")
atlas_info = ASSET_MANAGER.get_tile_atlas_info("TR_FLOOR_01")

# Use audio SFX
footstep = ASSET_MANAGER.get_audio_sfx_by_id("se_footstep_00")
door_open = ASSET_MANAGER.get_audio_sfx_by_id("se_door_open_1")

# Play emotes
play_emote("player", "anger")
frame = get_emote_frame("player")

# Update emotes each frame
update_emotes(delta_time)
```

## Asset Structure

### Tiny Rogue Tiles (132 tiles)
```
assets/tiles/tiny_rogue/tiles/
├── tile_0000.png - tile_0011.png  # Floors (12 variants)
├── tile_0012.png - tile_0023.png  # Walls (12 variants)
├── tile_0024.png - tile_0035.png  # Wall variants (12)
├── tile_0036.png - tile_0047.png  # Decorations (12)
├── tile_0048.png - tile_0059.png  # Items (12)
├── tile_0060.png - tile_0071.png  # Monsters (12)
├── tile_0072.png - tile_0083.png  # Monster variants (12)
├── tile_0084.png - tile_0095.png  # Effects (12)
├── tile_0096.png - tile_0107.png  # UI (12)
├── tile_0108.png - tile_0119.png  # Player/NPC (12)
└── tile_0120.png - tile_0131.png  # Misc (12)
```

### Atlas Metadata
- `assets/tiles/tiny_rogue_atlas_16x16.png` - Packed atlas (509x115)
- `assets/tiles/tiny_rogue_atlas_16x16.json` - UV coordinates and animation info

### Audio SFX (51 files)
```
assets/audio/
├── footstep00.ogg - footstep09.ogg    # Footsteps (10)
├── doorOpen_1.ogg - doorOpen_2.ogg    # Door open (2)
├── doorClose_1.ogg - doorClose_4.ogg  # Door close (4)
├── bookOpen.ogg, bookClose.ogg        # Book sounds
├── bookFlip1.ogg - bookFlip3.ogg      # Page flip (3)
├── bookPlace1.ogg - bookPlace3.ogg    # Book place (3)
├── drawKnife1.ogg - drawKnife3.ogg    # Knife draw (3)
├── knifeSlice.ogg, knifeSlice2.ogg    # Knife slice (2)
├── cloth1.ogg - cloth4.ogg            # Cloth rustle (4)
├── clothBelt.ogg, clothBelt2.ogg      # Belt sounds
├── beltHandle1.ogg, beltHandle2.ogg   # Belt handle (2)
├── handleCoins.ogg, handleCoins2.ogg  # Coin handling
├── handleSmallLeather.ogg/.ogg2       # Leather handling
├── metalClick.ogg                     # Metal click
├── metalLatch.ogg                     # Metal latch
├── metalPot1.ogg - metalPot3.ogg      # Metal pot (3)
├── chop.ogg                           # Chopping
├── creak1.ogg - creak3.ogg            # Creaking (3)
└── manifest.csv                       # Category + suggested_id mapping
```

### Emote Sprites (256 files)
```
assets/emote/
├── pixel/
│   ├── style1/ - style8/              # 32 emotes per style (256 total)
│   │   ├── emote_anger.png
│   │   ├── emote_heart.png
│   │   ├── emote_question.png
│   │   ├── emote_sleep.png
│   │   └── ... (28 more per style)
│   └── style1/emote_*.png             # 32 files
├── tilesheets/
│   ├── pixel_style1.png - pixel_style8.png
│   └── vector_style1.png - vector_style8.png
└── spritesheets/                      # Empty (reserved)
```

## Configuration

Add to `config.yaml`:

```yaml
assets:
  tiny_rogue_tiles: "assets/tiles/tiny_rogue/tiles"
  tiny_rogue_atlas: "assets/tiles/tiny_rogue_atlas_16x16.png"
  tiny_rogue_atlas_meta: "assets/tiles/tiny_rogue_atlas_16x16.json"
  audio_sfx: "assets/audio"
  audio_manifest: "assets/audio/manifest.csv"
  emote_pixel: "assets/emote/pixel"
  emote_tilesheets: "assets/emote/tilesheets"
  emote_spritesheets: "assets/emote/spritesheets"
```

## API Reference

### AssetManager

```python
from asset_manager import ASSET_MANAGER

# Initialize (call once at startup)
ASSET_MANAGER.initialize(config)

# Tiny Rogue Tiles
ASSET_MANAGER.get_tiny_rogue_tile_path("tile_0001")  # -> "assets/tiles/tiny_rogue/tiles/tile_0001.png"
ASSET_MANAGER.get_tile_atlas_info("TR_FLOOR_01")      # -> {"x": 0, "y": 0, "width": 16, "height": 16, "animated": False, ...}
ASSET_MANAGER.get_tile_atlas_info_or_fallback("MISSING", "TR_FLOOR_01")  # With fallback
ASSET_MANAGER.list_tiny_rogue_tiles()                 # -> ["tile_0000", "tile_0001", ...]

# Audio SFX
ASSET_MANAGER.get_audio_sfx_path("footstep00")        # -> "assets/audio/footstep00.ogg"
ASSET_MANAGER.get_audio_sfx_by_id("se_footstep_00")   # -> "assets/audio/footstep00.ogg"
ASSET_MANAGER.get_audio_sfx_or_fallback("MISSING")    # With fallback
ASSET_MANAGER.list_audio_sfx()                        # -> ["footstep00", "doorOpen_1", ...]

# Emote Sprites
ASSET_MANAGER.get_emote_sprite_path("style1/emote_anger")  # -> "assets/emote/pixel/style1/emote_anger.png"
ASSET_MANAGER.get_emote_sprite_or_fallback("MISSING")      # With fallback
ASSET_MANAGER.list_emote_sprites()                         # -> ["style1/emote_anger", "style1/emote_heart", ...]
```

### EmoteSystem

```python
from emote_system import EMOTE_SYSTEM, play_emote, get_emote_frame, update_emotes

# Play emote on entity
play_emote("entity_id", "anger")      # Returns True if successful
play_emote("entity_id", "heart")
play_emote("entity_id", "sleep")      # Loops automatically

# Get current frame
frame = get_emote_frame("entity_id")  # Returns sprite path or None

# Check if playing
is_playing = EMOTE_SYSTEM.is_playing("entity_id")

# Stop emote
from emote_system import stop_emote
stop_emote("entity_id")

# Update all emotes (call each frame)
update_emotes(delta_time)

# List available emotes
EMOTE_SYSTEM.get_available_emotes()
# -> ['anger', 'exclamation', 'question', 'idea', 'heart', 'heart_broken', 
#     'sleep', 'laugh', 'sad', 'happy', 'angry_face', 'alert', 'music', 
#     'star', 'dots', 'sweat', 'swirl', 'cash']
```

## Available Emotes

| Emote | Pattern | FPS | Duration | Loop |
|-------|---------|-----|----------|------|
| anger | emote_anger | 10 | 0.5s | No |
| exclamation | emote_exclamation | 8 | 0.6s | No |
| question | emote_question | 8 | 0.6s | No |
| idea | emote_idea | 6 | 1.0s | No |
| heart | emote_heart | 4 | 1.5s | No |
| heart_broken | emote_heartBroken | 4 | 1.5s | No |
| sleep | emote_sleep | 2 | 2.0s | **Yes** |
| laugh | emote_laugh | 10 | 0.8s | No |
| sad | emote_faceSad | 4 | 1.0s | No |
| happy | emote_faceHappy | 4 | 1.0s | No |
| angry_face | emote_faceAngry | 4 | 1.0s | No |
| alert | emote_alert | 12 | 0.4s | No |
| music | emote_music | 6 | 1.2s | No |
| star | emote_star | 8 | 0.8s | No |
| dots | emote_dots1 | 4 | 1.0s | No |
| sweat | emote_drop | 6 | 0.8s | No |
| swirl | emote_swirl | 8 | 1.0s | No |
| cash | emote_cash | 8 | 0.8s | No |

## Scripts

### Resize Assets
```bash
python scripts/resize_assets.py assets/tiles/tiny_rogue/tiles output/tiles_32x32 --size 32
```

### Convert Audio
```bash
python scripts/convert_audio.py assets/audio output/audio_mp3 --format mp3
```

### Generate Previews
```bash
python scripts/generate_previews.py
# Output: output/previews/index.html, tiles.html, audio.html, emotes.html
```

## Testing

Run unit tests:
```bash
python -m pytest tests/unit/test_asset_integration.py -v
```

Run integration tests:
```bash
python -m pytest tests/integration/test_tiny_rogue_graphics.py -v
```

## Fallback Behavior

All lookup methods provide safe fallbacks:
- `get_tile_atlas_info_or_fallback()` returns TR_FLOOR_01
- `get_audio_sfx_or_fallback()` returns se_footstep_00
- `get_emote_sprite_or_fallback()` returns style1/emote_anger

Missing assets log warnings but don't crash.

## Entity Integration

Entities now have emote state properties:
```python
entity.emote_state    # Current emote name or None
entity.emote_timer    # Playback timer
entity.emote_frame    # Current frame index
```

## Previews

Open `output/previews/index.html` in a browser to view:
- **tiles.html** - All 132 tiles with atlas coordinates
- **audio.html** - All 51 sounds with play buttons
- **emotes.html** - All 256 emote sprites organized by style

## License

Asset packs are used under their respective licenses. See individual asset directories for license files.