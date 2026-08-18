/**
 * WebGL2 Renderer for Elona Scene Demos
 * Three.js r160+ with WebGL2 context
 */

import * as THREE from 'three';

export interface TileDefinition {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  variants: number;
  animated: boolean;
  frames: number;
  fps: number;
  directions: number;
}

export interface TilesetData {
  tile_size: number;
  atlas_width: number;
  atlas_height: number;
  tiles: Record<string, TileDefinition>;
}

export interface SceneGridData {
  title: string;
  desc: string;
  icon: string;
  grid: string[][];
  log: string;
}

export class WebGLRenderer {
  private renderer: THREE.WebGLRenderer;
  private scene: THREE.Scene;
  private camera: THREE.OrthographicCamera;
  private tilesetTexture: THREE.Texture | null = null;
  private tilesetData: TilesetData | null = null;
  private tileMeshes: THREE.Mesh[] = [];
  private gridSize = 10;
  private tileSize = 1.0;
  private animationTime = 0;
  private animationId: number | null = null;

  constructor(container: HTMLElement, width: number = 820, height: number = 600) {
    // Create WebGL2 renderer
    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      preserveDrawingBuffer: true,
      powerPreference: 'high-performance'
    });
    
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.0;
    
    // Force WebGL2
    const gl = this.renderer.getContext() as WebGL2RenderingContext;
    if (!gl) {
      throw new Error('WebGL2 not supported');
    }
    console.log('WebGL2 Context:', gl.getParameter(gl.VERSION));
    
    container.appendChild(this.renderer.domElement);
    
    // Create scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x030712);
    
    // Orthographic camera for tile grid
    const aspect = width / height;
    const frustumSize = this.gridSize * this.tileSize;
    this.camera = new THREE.OrthographicCamera(
      -frustumSize * aspect / 2,
      frustumSize * aspect / 2,
      frustumSize / 2,
      -frustumSize / 2,
      -100,
      100
    );
    this.camera.position.set(0, 0, 50);
    this.camera.lookAt(0, 0, 0);
    
    // Ambient light
    const ambientLight = new THREE.AmbientLight(0x404060, 0.5);
    this.scene.add(ambientLight);
    
    // Directional light for 3D feel
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(5, 10, 7);
    this.scene.add(dirLight);
    
    // Load tileset
    this.loadTileset();
  }

  private async loadTileset(): Promise<void> {
    try {
      // Load texture atlas
      const textureLoader = new THREE.TextureLoader();
      this.tilesetTexture = await textureLoader.loadAsync('/assets/tiles/tileset_32x32.png');
      this.tilesetTexture.magFilter = THREE.NearestFilter;
      this.tilesetTexture.minFilter = THREE.NearestFilter;
      this.tilesetTexture.colorSpace = THREE.SRGBColorSpace;
      
      // Load tileset definition
      const response = await fetch('/assets/tiles/tileset_32x32.json');
      this.tilesetData = await response.json();
      
      console.log('Tileset loaded:', Object.keys(this.tilesetData.tiles).length, 'tiles');
    } catch (error) {
      console.error('Failed to load tileset:', error);
    }
  }

  private getTileUV(tileId: string, variant: number = 0, frame: number = 0, direction: number = 0): THREE.Vector4 | null {
    if (!this.tilesetData || !this.tilesetTexture) return null;
    
    const tileDef = this.tilesetData.tiles[tileId];
    if (!tileDef) return null;
    
    const atlasWidth = this.tilesetData.atlas_width;
    const atlasHeight = this.tilesetData.atlas_height;
    const tileWidth = tileDef.width;
    const tileHeight = tileDef.height;
    
    // Calculate UV coordinates in atlas
    let u = tileDef.x;
    let v = tileDef.y;
    
    // Handle variants (horizontal)
    if (tileDef.variants > 1) {
      u += (variant % tileDef.variants) * tileWidth;
    }
    
    // Handle animation frames (horizontal after variants)
    if (tileDef.animated && tileDef.frames > 1) {
      u += (frame % tileDef.frames) * tileWidth * Math.max(1, tileDef.variants);
    }
    
    // Handle directions (vertical)
    if (tileDef.directions > 1) {
      v += (direction % tileDef.directions) * tileHeight;
    }
    
    // Normalize to 0-1
    const u0 = u / atlasWidth;
    const v0 = 1.0 - (v + tileHeight) / atlasHeight; // Flip V for Three.js
    const u1 = (u + tileWidth) / atlasWidth;
    const v1 = 1.0 - v / atlasHeight;
    
    return new THREE.Vector4(u0, v0, u1, v1);
  }

  private emojiToTileId(emoji: string): { tileId: string; variant: number; animated: boolean } {
    // Map emojis to tileset IDs
    const emojiMap: Record<string, { tileId: string; variant: number; animated: boolean }> = {
      '🧱': { tileId: 'TILE_WALL', variant: 0, animated: false },
      '▫️': { tileId: 'TILE_FLOOR', variant: 0, animated: false },
      '🧙': { tileId: 'PLAYER', variant: 0, animated: true },
      '👧': { tileId: 'PET', variant: 0, animated: true },
      '📦': { tileId: 'ITEM_GOLD', variant: 0, animated: true },
      '🛏️': { tileId: 'ITEM_ARMOR', variant: 0, animated: false },
      '🚪': { tileId: 'TILE_STAIRS_DOWN', variant: 0, animated: true },
      '🍻': { tileId: 'ITEM_POTION', variant: 0, animated: false },
      '🧑‍🌾': { tileId: 'ENEMY_GOBLIN', variant: 0, animated: true },
      '💂': { tileId: 'ENEMY_GOBLIN', variant: 1, animated: true },
      '🐕': { tileId: 'PET', variant: 1, animated: true },
      '🐌': { tileId: 'ENEMY_GOBLIN', variant: 2, animated: true },
      '🍮': { tileId: 'ENEMY_GOBLIN', variant: 3, animated: true },
      '🗡️': { tileId: 'ITEM_WEAPON', variant: 0, animated: false },
      '👹': { tileId: 'ENEMY_GOBLIN', variant: 0, animated: true },
      '👺': { tileId: 'ENEMY_GOBLIN', variant: 1, animated: true },
      '💀': { tileId: 'DECOR_BLOOD', variant: 0, animated: false },
      '⏬': { tileId: 'TILE_STAIRS_DOWN', variant: 0, animated: true },
      '💥': { tileId: 'EFFECT_MAGIC', variant: 0, animated: true },
      '⛩️': { tileId: 'DECOR_TORCH', variant: 0, animated: true },
      '🕊️': { tileId: 'EFFECT_MAGIC', variant: 1, animated: true },
      '✨': { tileId: 'EFFECT_MAGIC', variant: 2, animated: true },
      '🍞': { tileId: 'ITEM_FOOD', variant: 0, animated: false },
      '💎': { tileId: 'ITEM_GOLD', variant: 0, animated: true },
      '🎻': { tileId: 'ITEM_WEAPON', variant: 1, animated: false },
      '🎶': { tileId: 'EFFECT_MAGIC', variant: 3, animated: true },
      '🪙': { tileId: 'ITEM_GOLD', variant: 0, animated: true },
      '🪨': { tileId: 'TILE_WALL', variant: 1, animated: false },
      '⛏️': { tileId: 'ITEM_WEAPON', variant: 2, animated: false },
      '🔥': { tileId: 'DECOR_TORCH', variant: 0, animated: true },
      '🔨': { tileId: 'ITEM_WEAPON', variant: 3, animated: false },
      '🛡️': { tileId: 'ITEM_ARMOR', variant: 0, animated: false },
      '🥋': { tileId: 'ITEM_ARMOR', variant: 1, animated: false },
      '🍳': { tileId: 'ITEM_POTION', variant: 1, animated: false },
      '🍖': { tileId: 'ITEM_FOOD', variant: 1, animated: false },
      '🌿': { tileId: 'ITEM_POTION', variant: 2, animated: false },
      '🥗': { tileId: 'ITEM_FOOD', variant: 2, animated: false },
      '🧀': { tileId: 'ITEM_FOOD', variant: 3, animated: false },
      '🏆': { tileId: 'ITEM_GOLD', variant: 1, animated: true },
      '🆚': { tileId: 'EFFECT_MAGIC', variant: 4, animated: true },
      '🌾': { tileId: 'TILE_FLOOR', variant: 1, animated: false },
      '🐄': { tileId: 'PET', variant: 2, animated: true },
      '🐑': { tileId: 'PET', variant: 3, animated: true },
      '🥚': { tileId: 'ITEM_FOOD', variant: 4, animated: false },
      '🥛': { tileId: 'ITEM_POTION', variant: 3, animated: false },
      '🚜': { tileId: 'ITEM_WEAPON', variant: 4, animated: false },
      '🧬': { tileId: 'EFFECT_MAGIC', variant: 5, animated: true },
      '🤖': { tileId: 'ENEMY_GOBLIN', variant: 4, animated: true },
      '🧪': { tileId: 'ITEM_POTION', variant: 4, animated: false },
      '🦾': { tileId: 'ITEM_ARMOR', variant: 2, animated: false },
      '⚡': { tileId: 'EFFECT_MAGIC', variant: 0, animated: true },
      '🌪️': { tileId: 'EFFECT_MAGIC', variant: 1, animated: true },
      '☣️': { tileId: 'DECOR_BLOOD', variant: 1, animated: false },
      '🏚️': { tileId: 'TILE_WALL', variant: 2, animated: false },
      '🗝️': { tileId: 'ITEM_WEAPON', variant: 5, animated: false },
      '🦹': { tileId: 'ENEMY_GOBLIN', variant: 5, animated: true },
      '💰': { tileId: 'ITEM_GOLD', variant: 2, animated: true },
      '🎭': { tileId: 'EFFECT_MAGIC', variant: 2, animated: true },
      '📘': { tileId: 'ITEM_ARMOR', variant: 3, animated: false },
      '🔮': { tileId: 'EFFECT_MAGIC', variant: 3, animated: true },
      '📜': { tileId: 'ITEM_FOOD', variant: 5, animated: false },
      '✨': { tileId: 'EFFECT_MAGIC', variant: 4, animated: true },
      '🧙‍♂️': { tileId: 'PLAYER', variant: 1, animated: true },
      '🎰': { tileId: 'EFFECT_MAGIC', variant: 5, animated: true },
      '🎲': { tileId: 'ITEM_GOLD', variant: 3, animated: true },
      '🃏': { tileId: 'ITEM_POTION', variant: 5, animated: false },
      '🎣': { tileId: 'ITEM_WEAPON', variant: 6, animated: false },
      '🌊': { tileId: 'TILE_WATER', variant: 0, animated: true },
      '🐟': { tileId: 'PET', variant: 4, animated: true },
      '⛵': { tileId: 'ITEM_ARMOR', variant: 4, animated: false },
      '🥾': { tileId: 'ITEM_ARMOR', variant: 5, animated: false },
      '🗿': { tileId: 'TILE_WALL', variant: 3, animated: false },
      '🦖': { tileId: 'ENEMY_GOBLIN', variant: 6, animated: true },
      '👑': { tileId: 'ITEM_GOLD', variant: 4, animated: true },
      '📮': { tileId: 'TILE_WALL', variant: 4, animated: false },
      '⚖️': { tileId: 'ITEM_WEAPON', variant: 7, animated: false },
      '👮': { tileId: 'ENEMY_GOBLIN', variant: 7, animated: true },
      '🌋': { tileId: 'DECOR_TORCH', variant: 1, animated: true },
      '🐉': { tileId: 'ENEMY_GOBLIN', variant: 8, animated: true },
      '🔥': { tileId: 'DECOR_TORCH', variant: 0, animated: true },
      '🌠': { tileId: 'EFFECT_MAGIC', variant: 6, animated: true },
      '💫': { tileId: 'EFFECT_MAGIC', variant: 7, animated: true },
      '🧞': { tileId: 'ENEMY_GOBLIN', variant: 9, animated: true },
      '🪄': { tileId: 'ITEM_WEAPON', variant: 8, animated: false },
      '🍾': { tileId: 'ITEM_POTION', variant: 6, animated: true },
      '🥂': { tileId: 'ITEM_POTION', variant: 7, animated: true },
      '🎩': { tileId: 'ITEM_ARMOR', variant: 6, animated: false },
      '💃': { tileId: 'PET', variant: 5, animated: true },
      '🍰': { tileId: 'ITEM_FOOD', variant: 6, animated: false },
      '🎁': { tileId: 'ITEM_GOLD', variant: 5, animated: true },
      '🎆': { tileId: 'EFFECT_MAGIC', variant: 8, animated: true },
      '🎉': { tileId: 'EFFECT_MAGIC', variant: 9, animated: true },
      '🏰': { tileId: 'TILE_WALL', variant: 5, animated: false },
      '💖': { tileId: 'EFFECT_MAGIC', variant: 10, animated: true },
    };
    
    return emojiMap[emoji] || { tileId: 'TILE_FLOOR', variant: 0, animated: false };
  }

  public renderScene(sceneData: SceneGridData): void {
    // Clear existing meshes
    this.tileMeshes.forEach(mesh => {
      this.scene.remove(mesh);
      mesh.geometry.dispose();
      if (mesh.material instanceof THREE.Material) {
        mesh.material.dispose();
      }
    });
    this.tileMeshes = [];
    
    if (!this.tilesetTexture || !this.tilesetData) {
      console.warn('Tileset not loaded yet');
      return;
    }
    
    const grid = sceneData.grid;
    const rows = grid.length;
    const cols = grid[0]?.length || 0;
    
    // Create instanced mesh for better performance
    const geometry = new THREE.PlaneGeometry(this.tileSize, this.tileSize);
    const material = new THREE.MeshStandardMaterial({
      map: this.tilesetTexture,
      transparent: true,
      alphaTest: 0.1,
      side: THREE.DoubleSide,
      depthWrite: true,
    });
    
    const count = rows * cols;
    const instancedMesh = new THREE.InstancedMesh(geometry, material, count);
    instancedMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    
    const dummy = new THREE.Object3D();
    const uvBuffer: number[] = [];
    
    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        const index = row * cols + col;
        const emoji = grid[row][col];
        const { tileId, variant, animated } = this.emojiToTileId(emoji);
        
        // Position
        const x = (col - (cols - 1) / 2) * this.tileSize;
        const y = ((rows - 1) / 2 - row) * this.tileSize;
        dummy.position.set(x, y, 0);
        dummy.updateMatrix();
        instancedMesh.setMatrixAt(index, dummy.matrix);
        
        // UV coordinates
        const uv = this.getTileUV(tileId, variant, 0, 0);
        if (uv) {
          uvBuffer.push(uv.x, uv.y, uv.z, uv.w, animated ? 1 : 0, 0, 0, 0);
        } else {
          uvBuffer.push(0, 0, 1, 1, 0, 0, 0, 0);
        }
      }
    }
    
    // Set custom UV attribute
    const uvAttribute = new THREE.InstancedBufferAttribute(new Float32Array(uvBuffer), 8);
    instancedMesh.geometry.setAttribute('instanceUV', uvAttribute);
    
    // Custom shader for atlas UV
    instancedMesh.material = new THREE.ShaderMaterial({
      uniforms: {
        map: { value: this.tilesetTexture },
        time: { value: 0 },
        tileSize: { value: new THREE.Vector2(this.tilesetData.tile_size, this.tilesetData.tile_size) },
        atlasSize: { value: new THREE.Vector2(this.tilesetData.atlas_width, this.tilesetData.atlas_height) },
      },
      vertexShader: `
        attribute vec4 instanceUV;
        varying vec2 vUv;
        varying float vAnimated;
        
        void main() {
          vUv = uv;
          vAnimated = instanceUV.w;
          
          vec3 transformed = position;
          mat4 mvMatrix = modelViewMatrix * instanceMatrix;
          gl_Position = projectionMatrix * mvMatrix * vec4(transformed, 1.0);
        }
      `,
      fragmentShader: `
        uniform sampler2D map;
        uniform float time;
        uniform vec2 tileSize;
        uniform vec2 atlasSize;
        varying vec2 vUv;
        varying float vAnimated;
        
        void main() {
          // instanceUV contains: u0, v0, u1, v1, animated, frameOffset, dirOffset, _
          // But we need to pass it differently...
          // For now, use a simpler approach with vertex shader passing
          vec2 atlasCoord = vUv;
          vec4 color = texture2D(map, atlasCoord);
          
          // Pulse animation for animated tiles
          float alpha = color.a;
          if (vAnimated > 0.5) {
            float pulse = sin(time * 3.0) * 0.15 + 0.85;
            alpha *= pulse;
          }
          
          gl_FragColor = vec4(color.rgb, alpha);
        }
      `,
      transparent: true,
      alphaTest: 0.1,
      depthWrite: true,
    });
    
    this.scene.add(instancedMesh);
    this.tileMeshes.push(instancedMesh);
    
    // Store reference for animation
    (instancedMesh as any)._uvBuffer = uvBuffer;
    (instancedMesh as any)._grid = grid;
    (instancedMesh as any)._cols = cols;
    (instancedMesh as any)._rows = rows;
  }

  public animate(): void {
    this.animationTime += 1/60;
    
    // Update animated materials
    this.tileMeshes.forEach(mesh => {
      if (mesh.material && 'uniforms' in mesh.material) {
        (mesh.material as any).uniforms.time.value = this.animationTime;
      }
    });
    
    this.renderer.render(this.scene, this.camera);
    
    this.animationId = requestAnimationFrame(() => this.animate());
  }

  public stop(): void {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
  }

  public dispose(): void {
    this.stop();
    this.tileMeshes.forEach(mesh => {
      this.scene.remove(mesh);
      mesh.geometry.dispose();
      if (mesh.material instanceof THREE.Material) {
        mesh.material.dispose();
      }
    });
    this.renderer.dispose();
    if (this.tilesetTexture) {
      this.tilesetTexture.dispose();
    }
  }

  public getRenderer(): THREE.WebGLRenderer {
    return this.renderer;
  }

  public getScene(): THREE.Scene {
    return this.scene;
  }

  public getCamera(): THREE.OrthographicCamera {
    return this.camera;
  }

  public setSize(width: number, height: number): void {
    this.renderer.setSize(width, height);
    const aspect = width / height;
    const frustumSize = this.gridSize * this.tileSize;
    this.camera.left = -frustumSize * aspect / 2;
    this.camera.right = frustumSize * aspect / 2;
    this.camera.top = frustumSize / 2;
    this.camera.bottom = -frustumSize / 2;
    this.camera.updateProjectionMatrix();
  }
}

// Scene loader utility
export async function loadSceneData(filename: string): Promise<SceneGridData> {
  const response = await fetch(`/demos/${filename}`);
  const html = await response.text();
  
  // Parse the HTML to extract scene data
  // This is a simplified parser for the generated HTML format
  const titleMatch = html.match(/<title>Elona Scene Demo - (.*?)<\/title>/);
  const descMatch = html.match(/<p class="text-xs text-slate-400">(.*?)<\/p>/);
  const iconMatch = html.match(/<span class="text-3xl">(.*?)<\/span>/);
  const logMatch = html.match(/<span class="text-yellow-300 font-medium">📜 (.*?)<\/span>/);
  
  // Extract grid from the HTML
  const gridMatches = html.matchAll(/<div class="tile[^"]*">(.*?)<\/div>/g);
  const grid: string[][] = [];
  let row: string[] = [];
  
  for (const match of gridMatches) {
    row.push(match[1]);
    if (row.length === 10) {
      grid.push(row);
      row = [];
    }
  }
  
  return {
    title: titleMatch?.[1] || 'Unknown Scene',
    desc: descMatch?.[1] || '',
    icon: iconMatch?.[1] || '🏡',
    grid,
    log: logMatch?.[1] || ''
  };
}