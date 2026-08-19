/**
 * 動的環境干渉シェーダー & インタラクションマネージャー
 * 草木や環境タイルの風揺れ・エンティティ通過時の押し曲げ（Foliage Bending）
 */

export class InteractionManager {
    constructor() {
        this.interactors = []; // [{x, y, vx, vy, radius}]
        this.maxInteractors = 8;
        this.windTime = 0;
        this.windDirection = [1.0, 0.3];
        this.windStrength = 0.5;
    }

    /**
     * エンティティや魔法弾の干渉点を登録・更新
     * @param {Array<{x: number, y: number, vx?: number, vy?: number, radius?: number}>} list
     */
    updateInteractors(list = []) {
        this.interactors = list.slice(0, this.maxInteractors);
    }

    /**
     * 魔法弾や衝撃波の一時干渉点を追加
     * @param {number} x
     * @param {number} y
     * @param {number} vx
     * @param {number} vy
     * @param {number} radius
     */
    addTransientInteractor(x, y, vx = 0, vy = 0, radius = 24) {
        if (this.interactors.length < this.maxInteractors) {
            this.interactors.push({ x, y, vx, vy, radius });
        }
    }

    /**
     * シェーダー用 Uniform データを生成
     * @param {number} deltaSeconds
     * @returns {Object}
     */
    getUniforms(deltaSeconds = 0.016) {
        this.windTime += deltaSeconds;

        const positions = new Float32Array(this.maxInteractors * 2);
        const radii = new Float32Array(this.maxInteractors);

        for (let i = 0; i < this.maxInteractors; i++) {
            if (i < this.interactors.length) {
                positions[i * 2] = this.interactors[i].x;
                positions[i * 2 + 1] = this.interactors[i].y;
                radii[i] = this.interactors[i].radius || 20.0;
            } else {
                positions[i * 2] = -9999.0;
                positions[i * 2 + 1] = -9999.0;
                radii[i] = 0.0;
            }
        }

        return {
            uWindTime: this.windTime,
            uWindDir: this.windDirection,
            uWindStrength: this.windStrength,
            uInteractorCount: this.interactors.length,
            uInteractorPos: positions,
            uInteractorRadius: radii
        };
    }
}

/**
 * Foliage Bending 用カスタムフィルター
 */
export class FoliageFilter extends PIXI.Filter {
    constructor() {
        const vert = `
            attribute vec2 aVertexPosition;
            attribute vec2 aTextureCoord;

            uniform mat3 projectionMatrix;
            uniform float uWindTime;
            uniform vec2 uWindDir;
            uniform float uWindStrength;
            uniform int uInteractorCount;
            uniform vec2 uInteractorPos[8];
            uniform float uInteractorRadius[8];

            varying vec2 vTextureCoord;

            void main(void) {
                vTextureCoord = aTextureCoord;
                vec2 pos = aVertexPosition;

                // スプライトの上半分（UV.yが小さい部分）ほど大きく曲がる
                float bendFactor = clamp(1.0 - aTextureCoord.y, 0.0, 1.0);

                // 基本風揺れ (Sine wave + Harmonic)
                float windWave = sin(uWindTime * 3.0 + pos.x * 0.05) * 0.7 + sin(uWindTime * 6.5 + pos.y * 0.08) * 0.3;
                vec2 windOffset = uWindDir * windWave * uWindStrength * bendFactor * 4.0;
                pos += windOffset;

                // エンティティによる干渉押し出し (Interactors Push)
                for (int i = 0; i < 8; i++) {
                    if (i >= uInteractorCount) break;
                    vec2 iPos = uInteractorPos[i];
                    float iRad = uInteractorRadius[i];
                    vec2 diff = pos - iPos;
                    float dist = length(diff);
                    if (dist < iRad && dist > 0.001) {
                        float pushFactor = (1.0 - dist / iRad) * bendFactor;
                        pos += normalize(diff) * pushFactor * 12.0;
                    }
                }

                gl_Position = vec4((projectionMatrix * vec3(pos, 1.0)).xy, 0.0, 1.0);
            }
        `;

        const frag = `
            precision mediump float;
            varying vec2 vTextureCoord;
            uniform sampler2D uSampler;

            void main(void) {
                gl_FragColor = texture2D(uSampler, vTextureCoord);
            }
        `;

        super(vert, frag, {
            uWindTime: 0.0,
            uWindDir: [1.0, 0.2],
            uWindStrength: 0.5,
            uInteractorCount: 0,
            uInteractorPos: new Float32Array(16),
            uInteractorRadius: new Float32Array(8)
        });
    }

    /**
     * @param {InteractionManager} manager
     * @param {number} deltaSeconds
     */
    update(manager, deltaSeconds) {
        const u = manager.getUniforms(deltaSeconds);
        this.uniforms.uWindTime = u.uWindTime;
        this.uniforms.uWindDir = u.uWindDir;
        this.uniforms.uWindStrength = u.uWindStrength;
        this.uniforms.uInteractorCount = u.uInteractorCount;
        this.uniforms.uInteractorPos = u.uInteractorPos;
        this.uniforms.uInteractorRadius = u.uInteractorRadius;
    }
}

// グローバルスコープにもエクスポート
window.InteractionManager = InteractionManager;
window.FoliageFilter = FoliageFilter;
