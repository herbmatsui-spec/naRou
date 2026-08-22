// AnimationController for managing entity animations
export class AnimationController {
    constructor(pixiApp, textureAtlas) {
        this.app = pixiApp;
        this.textureAtlas = textureAtlas;
        this.activeAnimations = new Map(); // entityId -> animation
        this.animationTime = 0;
        this.animationClock = 0;
        this.frameTimes = {};
    }

    // Update all animations
    update(deltaTime) {
        this.animationTime += deltaTime;
        this.animationClock = Math.floor(this.animationTime * 10) % 4; // 4 frames for walk cycle

        for (const [entityId, anim] of this.activeAnimations) {
            if (anim.state === 'running') {
                anim.frameTime += deltaTime;
                if (anim.frameTime >= anim.frameDuration) {
                    anim.frameTime = 0;
                    anim.frame = (anim.frame + 1) % anim.frames;
                }
            }
        }
    }

    // Start animation for an entity
    startAnimation(entityId, animationData) {
        const entity = animationData.entityData;
        const frames = entity.frames || 4;
        const directions = entity.directions || 1;
        const fps = entity.fps || 4;
        const loop = animationData.loop !== false;

        const animation = {
            entityId: entityId,
            type: animationData.type || 'idle',
            frame: 0,
            frameTime: 0,
            frameDuration: 1 / fps,
            direction: animationData.direction || 0,
            state: 'running',
            loop: loop,
            frames: frames,
            directions: directions
        };

        this.activeAnimations.set(entityId, animation);
        return animation;
    }

    // Get current frame for entity
    getCurrentFrame(entityId) {
        const animation = this.activeAnimations.get(entityId);
        if (!animation || animation.state === 'paused' || animation.state === 'stopped') {
            return null;
        }

        const frame = animation.frame;
        const direction = animation.direction;
        const tileSize = animation.entityData?.tileSize || 32;

        // Calculate texture coordinates from atlas
        const textureKey = `${entityId}_anim_${animation.type}_${direction}_${frame}`;
        const texture = this.textureAtlas.getTexture(textureKey);

        if (!texture) {
            // Fallback: create colored rectangle
            return this._createFallbackTexture(frame, direction, tileSize);
        }

        return {
            texture: texture,
            x: direction * tileSize,
            y: frame * tileSize,
            width: tileSize,
            height: tileSize
        };
    }

    // Create fallback colored rectangle for missing textures
    _createFallbackTexture(frame, direction, size) {
        const canvas = document.createElement('canvas');
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext('2d');

        // Color based on animation type and frame
        const colors = this._getColorsForAnimationType('idle');
        ctx.fillStyle = colors[frame % colors.length];
        ctx.fillRect(0, 0, size, size);

        // Add simple pattern based on frame
        ctx.strokeStyle = 'rgba(0,0,0,0.3)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(size, size);
        ctx.stroke();

        const texture = PIXI.Texture.from(canvas);

        return {
            texture: texture,
            x: direction * size,
            y: frame * size,
            width: size,
            height: size
        };
    }

    // Get colors for animation type
    _getColorsForAnimationType(type) {
        const colorMap = {
            'idle': ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD'],
            'walk': ['#FF8E8E', '#4DD4C4', '#45C7D1', '#97CEB4', '#FFEEB7', '#DFA0DD'],
            'attack': ['#FF4757', '#FF6B6B', '#FF8E8E', '#FFA2A2'],
            'hit': ['#FFD700', '#FFA500', '#FF4500', '#DC143C'],
            'die': ['#8B0000', '#FF0000', '#FF4500', '#FF6347', '#FF8C00']
        };
        return colorMap[type] || colorMap['idle'];
    }

    // Update entity animation state
    updateAnimation(entityId, newState, direction = 0) {
        const animation = this.activeAnimations.get(entityId);
        if (!animation) {
            return;
        }

        if (newState === 'hit') {
            // Hit animation: single frame, then return to previous state
            animation.frame = 0;
            animation.frameTime = 0;
            animation.state = 'hit';
            setTimeout(() => {
                animation.state = 'running';
            }, 200);
        } else if (newState === 'die') {
            // Death animation
            animation.state = 'die';
            animation.frame = 0;
            animation.frameDuration = 0.2;
        } else if (newState === 'idle' || newState === 'walk' || newState === 'attack') {
            animation.type = newState;
            animation.frame = 0;
            animation.frameTime = 0;
            animation.state = 'running';
            animation.direction = direction;
        }
    }

    // Stop animation for an entity
    stopAnimation(entityId) {
        const animation = this.activeAnimations.get(entityId);
        if (animation) {
            animation.state = 'stopped';
            this.activeAnimations.delete(entityId);
        }
    }

    // Clear all animations
    clear() {
        for (const animation of this.activeAnimations.values()) {
            animation.state = 'stopped';
        }
        this.activeAnimations.clear();
    }
}

// Export for browser global
window.AnimationController = AnimationController;
