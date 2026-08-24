// CanvasEngine.js - Minimal engine that composes tile, particle, fluid, lighting, and decal subsystems.
// Provides a simple game loop and helper to draw a tile‑map.

import { TileRenderer2D } from './elona_canvas_core.js';
import { ParticleSystem2D } from './ParticleSystem2D.js';
import { FluidRenderer2D } from './FluidRenderer2D.js';
import { LightingSystem2D } from './LightingSystem2D.js';
import { DecalSystem2D } from './DecalSystem2D.js';

export class CanvasEngine {
  /**
   * @param {HTMLCanvasElement} canvas - The canvas element to drive.
   * @param {Object} [options] - Subsystem configuration objects.
   */
  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    // Subsystems – allow per‑subsystem options via the options object.
    this.tileRenderer = new TileRenderer2D(canvas, options.tileRenderer);
    this.particleSystem = new ParticleSystem2D(this.ctx, options.particleSystem);
    this.fluidRenderer = new FluidRenderer2D(canvas, options.fluid);
    this.lightingSystem = new LightingSystem2D(canvas, options.lighting);
    this.decalSystem = new DecalSystem2D(canvas, options.decal);
    this.lastTime = null;
    this.running = false;
  }

  /** Load tile assets – atlas PNG and JSON definition. */
  async loadTileAssets(atlasPath, jsonPath) {
    await this.tileRenderer.load(atlasPath, jsonPath);
  }

  /** Start the animation loop. */
  start() {
    this.running = true;
    this.lastTime = performance.now();
    requestAnimationFrame(this._loop.bind(this));
  }

  /** Stop the animation loop. */
  stop() {
    this.running = false;
  }

  _loop(now) {
    const dt = (now - this.lastTime) / 1000;
    this.lastTime = now;
    this.update(dt);
    this.render();
    if (this.running) requestAnimationFrame(this._loop.bind(this));
  }

  /** Update all subsystems that require time stepping. */
  update(dt) {
    this.particleSystem.update(dt);
    if (this.fluidRenderer.update) this.fluidRenderer.update(dt);
    // Lighting and decals are static for most demos – no update needed.
  }

  /** Render the full scene in a deterministic order. */
  render() {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    // 1. Fluid background (if any)
    if (this.fluidRenderer.render) this.fluidRenderer.render();
    // 2. Tile map – caller should have drawn tiles onto the canvas before this call.
    //    We'll provide a helper method `drawMap` for that.
    // 3. Decals (persistent visual effects)
    this.decalSystem.render();
    // 4. Particles (dynamic effects)
    this.particleSystem.render();
    // 5. Lighting overlay (adds ambience and light sources)
    this.lightingSystem.render();
  }

  /** Helper to draw a tile map using the internal TileRenderer.
   * @param {string[]} mapData - Array of strings where each character maps to a tile ID.
   * @param {Object} charMap - Mapping from character to tile ID (e.g., {'#':'TR_WALL_01'}).
   */
  drawMap(mapData, charMap) {
    this.tileRenderer.clear();
    for (let y = 0; y < mapData.length; y++) {
      const line = mapData[y];
      for (let x = 0; x < line.length; x++) {
        const ch = line[x];
        const tileId = charMap[ch] || 'TR_FLOOR_01';
        this.tileRenderer.drawTile(tileId, x, y);
      }
    }
  }
}
