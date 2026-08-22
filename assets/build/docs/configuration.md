# Asset Pipeline Configuration Reference

## Configuration File
The asset pipeline uses `asset_pipeline_config.json` for all configuration settings.

## Configuration Sections

### Directories
Specifies input and output locations for all asset types:
```json
{
  "directories": {
    "source": "assets/source",
    "output": "assets/build",
    "temp": "assets/temp",
    "cache": "assets/cache",
    "logs": "assets/logs"
  }
}
```

### Tileset Configuration
Controls tileset generation and optimization:
```json
{
  "tileset": {
    "default_size": 32,
    "sizes": [16, 32, 64],
    "padding": 1,
    "max_atlas_size": 2048,
    "formats": ["png"],
    "compression": {
      "enabled": true,
      "level": 6
    }
  }
}
```

### Font Configuration
Controls font atlas generation:
```json
{
  "font": {
    "default_size": 16,
    "sizes": [8, 16, 24, 32],
    "padding": 2,
    "character_set": "ASCII",
    "formats": ["png"]
  }
}
```

### Sound Configuration
Controls audio processing and optimization:
```json
{
  "sound": {
    "sample_rate": 44100,
    "bit_depth": 16,
    "channels": 2,
    "formats": ["ogg", "mp3"],
    "quality": {
      "music": {"bitrate": "192k", "vbr": true},
      "sfx": {"bitrate": "128k", "vbr": false}
    },
    "conversion": {
      "ogg_quality": 5,
      "mp3_quality": 2
    }
  }
}
```

### Model Configuration
Controls 3D model processing:
```json
{
  "models": {
    "formats": ["gltf", "glb", "obj"],
    "optimization": {
      "vertex_cache_optimization": true,
      "overdraw_optimization": true,
      "vertex_compression": true,
      "texture_compression": true
    },
    "validation": {
      "check_winding": true,
      "check_normals": true,
      "check_uvs": true,
      "check_materials": true
    }
  }
}
```

### Pipeline Settings
Controls overall pipeline behavior:
```json
{
  "pipeline": {
    "steps": [
      "validate_source",
      "process_tilesets",
      "process_fonts",
      "process_sounds",
      "process_models",
      "optimize_assets",
      "package_assets",
      "validate_output"
    ],
    "parallel_processing": true,
    "max_workers": 4,
    "continue_on_error": false
  }
}
```

## Environment Variables
The following environment variables can override configuration settings:
- `ASSET_PIPELINE_CONFIG`: Path to configuration file
- `ASSET_SOURCE_DIR`: Override source directory
- `ASSET_OUTPUT_DIR`: Override output directory
