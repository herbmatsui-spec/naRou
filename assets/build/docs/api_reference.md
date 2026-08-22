# Asset Pipeline API Reference

## Overview
This document describes the programmatic interfaces available for working with the naRou asset pipeline.

## Core Modules

### Asset Pipeline Manager
The main interface for coordinating asset processing operations.

```javascript
// Example usage (conceptual - actual implementation language may vary)
const pipeline = new AssetPipelineManager(config);

async function buildAssets() {{
    try {{
        await pipeline.validateSource();
        await pipeline.processTilesets();
        await pipeline.processFonts();
        await pipeline.processSounds();
        await pipeline.processModels();
        await pipeline.optimizeAssets();
        await pipeline.packageAssets();
        await pipeline.validateOutput();
        console.log("Asset pipeline completed successfully!");
    }} catch (error) {{
        console.error("Asset pipeline failed:", error);
        throw error;
    }}
}}
```

### Asset Types
Each asset type has specific interfaces for loading and usage:

#### Tilesets
```javascript
// Loading a tileset
const tileset = await assetLoader.loadTileset("tileset_grassland");

// Getting tile UV coordinates
const uv = tileset.getTileUV(42); // Tile index 42
const sprite = new Sprite(tileset.texture, uv.u, uv.v, uv.width, uv.height);
```

#### Fonts
```javascript
// Loading a font
const font = await assetLoader.loadFont("font_ui_16pt");

// Rendering text
const renderer = new FontRenderer(font);
renderer.renderText("Hello, World!", 100, 100, 24);
```

#### Sounds
```javascript
// Loading a sound
const sound = await assetLoader.loadSound("sound_explosion_01");

// Playing a sound
const audio = audioManager.playSound("sound_explosion_01", {{ volume: 0.8, loop: false }});
```

#### Models
```javascript
// Loading a model
const model = await assetLoader.loadModel("model_character_hero");

// Rendering a model
const transform = new Transform();
transform.position.set(0, 1.5, 0);
transform.rotation.y = Math.PI / 4; // 90 degrees
renderer.renderModel(model, transform);
```

## Error Handling
All pipeline methods return promises that reject with detailed error information:
- `ValidationError`: Asset failed validation checks
- `ProcessingError`: Error during asset processing
- `IOError`: Error reading/writing files
- `ConfigurationError`: Invalid or missing configuration

## Events
The pipeline emits events during processing:
- `asset_processed`: Fired when an individual asset is processed
- `stage_completed`: Fired when a pipeline stage completes
- `pipeline_completed`: Fired when the entire pipeline finishes
- `pipeline_failed`: Fired when the pipeline encounters an error

## Configuration Access
Configuration can be accessed through the pipeline's config property:
```javascript
const maxAtlasSize = pipeline.config.tileset.max_atlas_size;
const workerCount = pipeline.config.pipeline.max_workers;
```

        ]
