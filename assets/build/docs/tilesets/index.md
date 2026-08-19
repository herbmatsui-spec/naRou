# Tileset Documentation Index

Generated: 2026-08-19 01:07:05
Pipeline Version: 1.0.0

## Available Tilesets

*No tilesets found*

## Usage Guidelines

### Loading Tilesets
Tilesets consist of two files:
1. A PNG image containing the tile atlas
2. A JSON file containing metadata and tile coordinates

### Rendering Tiles
To render a specific tile from a tileset:
1. Look up the tile's UV coordinates in the JSON metadata
2. Use those coordinates to sample the appropriate region from the PNG atlas
3. Render the textured quad to the screen

### Tile Coordinate System
- U, V coordinates are normalized (0.0 to 1.0)
- U Width and V Height represent the tile's size in UV space
- Origin (0,0) is typically at the bottom-left or top-left depending on engine convention

## Related Documentation
- [Asset Pipeline Overview](../pipeline_docs.md)
- [Font Documentation](../fonts/)
- [Sound Documentation](../sounds/)
- [Model Documentation](../models/)
