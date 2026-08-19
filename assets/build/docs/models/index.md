# Model Documentation Index

Generated: 2026-08-19 01:07:05
Pipeline Version: 1.0.0

## Available Models

*No models found*

## Usage Guidelines

### Loading Models
Model assets can be loaded using:
- **Graphics Libraries**: THREE.js, Babylon.js, WebGL-native code
- **Game Engines**: Unity, Unreal Engine, Godot, CryEngine
- **Custom Loaders**: For proprietary or specialized formats

### Model Optimization
For better performance in games:
1. **Level of Detail (LOD)**: Create multiple versions of models at different detail levels
2. **Mesh Compression**: Use techniques like Draco compression for glTF
3. **Texture Atlas**: Combine multiple textures into atlases to reduce draw calls
4. **Instancing**: Render multiple copies of the same model efficiently
5. **Culling**: Frustum, occlusion, and distance culling to avoid rendering invisible models

### Format Recommendations
- **Web Applications**: Use glTF/.glb for best compatibility and performance
- **Game Engines**: Use engine-native formats or FBX for maximum feature support
- **Archival/Exchange**: Use OBJ or FBX for maximum compatibility
- **3D Printing**: Use STL for printable models

## Related Documentation
- [Asset Pipeline Overview](../pipeline_docs.md)
- [Tileset Documentation](../tilesets/)
- [Font Documentation](../fonts/)
- [Sound Documentation](../sounds/)
