# Font Documentation Index

Generated: 2026-08-19 01:07:05
Pipeline Version: 1.0.0

## Available Fonts

*No fonts found*

## Usage Guidelines

### Loading Fonts
Fonts consist of two files:
1. A PNG image containing the character atlas
2. A JSON file containing metadata and character metrics

### Rendering Text
To render text using a font atlas:
1. Load the PNG atlas as a texture
2. Parse the JSON metadata to get character metrics
3. For each character in the string, look up its UV coordinates and dimensions
4. Render textured quads for each character, advancing the cursor by the character's advance width

### Character Metrics Explained
- **x, y**: Position of character in the atlas (in pixels)
- **width, height**: Dimensions of the character glyph (in pixels)
- **u, v**: Normalized texture coordinates (0.0 to 1.0)
- **uw, vh**: Normalized texture dimensions (0.0 to 1.0)
- **bearing_x, bearing_y**: Offset from cursor to glyph origin
- **advance**: Horizontal distance to advance cursor after rendering glyph

## Related Documentation
- [Asset Pipeline Overview](../pipeline_docs.md)
- [Tileset Documentation](../tilesets/)
- [Sound Documentation](../sounds/)
- [Model Documentation](../models/)
