/**
 * 流体シミュレーション（メタボール & アルファ閾値カットオフ）
 * 血痕・毒沼・水滴の有機的融合と流動表現
 */

export class FluidRenderer {
    /**
     * @param {PIXI.Application} app
     * @param {number} width
     * @param {number} height
     */
    constructor(app, width, height) {
        this.app = app;
        this.width = width;
        this.height = height;

        this.particles = [];
        this.maxParticles = 120;

        // パーティクル用コンテナとテクスチャ
        this.particleContainer = new PIXI.Container();
        this.particleTexture = this._createParticleTexture();

        // メタボール融合用レンダーテクスチャ
        this.fluidTexture = PIXI.RenderTexture.create({
            width: this.width,
            height: this.height,
            resolution: 1
        });
        this.fluidSprite = new PIXI.Sprite(this.fluidTexture);
        this.fluidSprite.blendMode = PIXI.BLEND_MODES.NORMAL;

        // Step 36 & 37: 閾値カットオフ（Alpha Thresholding & Colorize）シェーダー
        const thresholdFrag = `
            precision mediump float;
            varying vec2 vTextureCoord;
            uniform sampler2D uSampler;

            void main(void) {
                vec4 col = texture2D(uSampler, vTextureCoord);
                
                // アルファ値が閾値を超えた領域を有機的に結合
                if (col.a > 0.45) {
                    // 滑らかなエッジ（アンチエイリアス）
                    float edge = smoothstep(0.45, 0.55, col.a);
                    
                    // 赤（血）主体のカラーリングとハイライト
                    vec3 bloodColor = vec3(0.65, 0.05, 0.08);
                    vec3 poisonColor = vec3(0.1, 0.75, 0.2);
                    vec3 waterColor = vec3(0.15, 0.45, 0.85);

                    vec3 finalColor = bloodColor;
                    if (col.g > col.r && col.g > col.b) {
                        finalColor = poisonColor;
                    } else if (col.b > col.r && col.b > col.g) {
                        finalColor = waterColor;
                    }

                    // 表面張力ハイライト
                    float spec = pow(smoothstep(0.45, 0.8, col.a), 3.0) * 0.4;
                    gl_FragColor = vec4(finalColor + vec3(spec), edge * 0.9);
                } else {
                    discard;
                }
            }
        `;

        this.thresholdFilter = new PIXI.Filter(null, thresholdFrag);
        this.fluidSprite.filters = [this.thresholdFilter];
    }

    /**
     * Step 34: 中心が濃く周辺が薄い放射状グラデーションテクスチャを生成
     * @returns {PIXI.Texture}
     */
    _createParticleTexture() {
        const size = 32;
        const canvas = document.createElement('canvas');
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext('2d');
        const cx = size / 2;
        const cy = size / 2;
        const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, cx);
        grad.addColorStop(0, 'rgba(255, 255, 255, 1)');
        grad.addColorStop(0.5, 'rgba(255, 255, 255, 0.6)');
        grad.addColorStop(1, 'rgba(255, 255, 255, 0)');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, size, size);
        return PIXI.Texture.from(canvas);
    }

    /**
     * Step 38: スプラッター（血しぶき・液体粒子）を発生
     * @param {number} x
     * @param {number} y
     * @param {string} type 'blood' | 'poison' | 'water'
     * @param {number} count
     * @param {number} speed
     */
    spawnSpatter(x, y, type = 'blood', count = 8, speed = 60.0) {
        for (let i = 0; i < count; i++) {
            if (this.particles.length >= this.maxParticles) {
                this.particles.shift();
            }

            const angle = Math.random() * Math.PI * 2;
            const spd = (0.2 + Math.random() * 0.8) * speed;
            const vx = Math.cos(angle) * spd;
            const vy = Math.sin(angle) * spd;
            const radius = 8 + Math.random() * 10;
            const maxLife = 3.0 + Math.random() * 2.0;

            const sprite = new PIXI.Sprite(this.particleTexture);
            sprite.anchor.set(0.5);
            sprite.width = radius * 2;
            sprite.height = radius * 2;

            if (type === 'poison') {
                sprite.tint = 0x00ff00;
            } else if (type === 'water') {
                sprite.tint = 0x00aaff;
            } else {
                sprite.tint = 0xff0000;
            }

            this.particleContainer.addChild(sprite);
            this.particles.push({
                x, y,
                vx, vy,
                radius,
                life: maxLife,
                maxLife,
                type,
                sprite
            });
        }
    }

    /**
     * Step 39: 物理更新（摩擦・拡散・減衰）
     * @param {number} deltaSeconds
     */
    update(deltaSeconds = 0.016) {
        for (let i = this.particles.length - 1; i >= 0; i--) {
            const p = this.particles[i];
            p.x += p.vx * deltaSeconds;
            p.y += p.vy * deltaSeconds;
            // 摩擦減衰
            p.vx *= Math.pow(0.1, deltaSeconds);
            p.vy *= Math.pow(0.1, deltaSeconds);

            p.life -= deltaSeconds;
            if (p.life <= 0) {
                this.particleContainer.removeChild(p.sprite);
                p.sprite.destroy();
                this.particles.splice(i, 1);
                continue;
            }

            // スプライト位置とサイズの同期
            const t = p.life / p.maxLife;
            p.sprite.x = p.x;
            p.sprite.y = p.y;
            p.sprite.alpha = Math.min(1.0, t * 1.5);
        }
    }

    /**
     * Step 40: レンダーテクスチャに描画
     */
    render() {
        if (this.particles.length > 0) {
            this.app.renderer.render(this.particleContainer, {
                renderTexture: this.fluidTexture,
                clear: true
            });
        } else {
            // パーティクルが無い時はクリア
            const g = new PIXI.Graphics();
            this.app.renderer.render(g, { renderTexture: this.fluidTexture, clear: true });
            g.destroy();
        }
    }

    destroy() {
        if (this.fluidTexture) this.fluidTexture.destroy();
        if (this.fluidSprite) this.fluidSprite.destroy();
        if (this.particleContainer) this.particleContainer.destroy({ children: true });
    }
}

// グローバルスコープにもエクスポート
window.FluidRenderer = FluidRenderer;
