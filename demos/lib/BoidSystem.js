/**
 * 物理ベース群れシミュレーション（Boids アルゴリズム）
 * ダンジョン内に漂う発光羽虫・環境パーティクルの自律行動
 */

export class BoidSystem {
    /**
     * @param {PIXI.Application} app
     * @param {PIXI.Container} container
     * @param {number} width
     * @param {number} height
     * @param {number} count
     */
    constructor(app, container, width, height, count = 40) {
        this.app = app;
        this.container = new PIXI.Container();
        container.addChild(this.container);
        this.width = width;
        this.height = height;

        this.boids = [];
        this.maxSpeed = 45.0;
        this.maxForce = 40.0;
        this.perceptionRadius = 48.0;

        // 個体の初期化
        for (let i = 0; i < count; i++) {
            const boid = {
                x: Math.random() * width,
                y: Math.random() * height,
                vx: (Math.random() - 0.5) * this.maxSpeed,
                vy: (Math.random() - 0.5) * this.maxSpeed,
                ax: 0,
                ay: 0,
                color: [220, 255, 140],
                size: 2 + Math.random() * 2,
                glowPhase: Math.random() * Math.PI * 2
            };

            const g = new PIXI.Graphics();
            boid.graphics = g;
            this.container.addChild(g);
            this.boids.push(boid);
        }
    }

    /**
     * Step 58, 59, 60, 61, 63: Boids物理更新
     * @param {number} deltaSeconds
     * @param {{x: number, y: number}} [playerPos]
     * @param {Array<{x: number, y: number}>} [lightSources]
     */
    update(deltaSeconds = 0.016, playerPos = null, lightSources = []) {
        for (const b of this.boids) {
            let sepX = 0, sepY = 0, sepCount = 0;
            let aliX = 0, aliY = 0, aliCount = 0;
            let cohX = 0, cohY = 0, cohCount = 0;

            for (const other of this.boids) {
                if (other === b) continue;
                const dx = b.x - other.x;
                const dy = b.y - other.y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < this.perceptionRadius && dist > 0.001) {
                    // Step 58: 分離（Separation）
                    sepX += (dx / dist) / dist;
                    sepY += (dy / dist) / dist;
                    sepCount++;

                    // Step 59: 整列（Alignment）
                    aliX += other.vx;
                    aliY += other.vy;
                    aliCount++;

                    // Step 60: 結合（Cohesion）
                    cohX += other.x;
                    cohY += other.y;
                    cohCount++;
                }
            }

            b.ax = 0;
            b.ay = 0;

            if (sepCount > 0) {
                b.ax += (sepX / sepCount) * 120.0;
                b.ay += (sepY / sepCount) * 120.0;
            }
            if (aliCount > 0) {
                b.ax += ((aliX / aliCount) - b.vx) * 0.8;
                b.ay += ((aliY / aliCount) - b.vy) * 0.8;
            }
            if (cohCount > 0) {
                const targetX = (cohX / cohCount) - b.x;
                const targetY = (cohY / cohCount) - b.y;
                b.ax += targetX * 0.5;
                b.ay += targetY * 0.5;
            }

            // Step 61: プレイヤーからの反発（Repulsion）
            if (playerPos) {
                const pdx = b.x - playerPos.x;
                const pdy = b.y - playerPos.y;
                const pdist = Math.sqrt(pdx * pdx + pdy * pdy);
                if (pdist < 70.0 && pdist > 0.001) {
                    b.ax += (pdx / pdist) * (70.0 - pdist) * 8.0;
                    b.ay += (pdy / pdist) * (70.0 - pdist) * 8.0;
                }
            }

            // Step 63: 光源への誘引（Attraction）
            if (lightSources && lightSources.length > 0) {
                const ls = lightSources[0];
                const ldx = ls.x - b.x;
                const ldy = ls.y - b.y;
                const ldist = Math.sqrt(ldx * ldx + ldy * ldy);
                if (ldist < 200.0 && ldist > 15.0) {
                    b.ax += (ldx / ldist) * 15.0;
                    b.ay += (ldy / ldist) * 15.0;
                }
            }

            // 速度・位置更新
            b.vx += b.ax * deltaSeconds;
            b.vy += b.ay * deltaSeconds;
            const spd = Math.sqrt(b.vx * b.vx + b.vy * b.vy);
            if (spd > this.maxSpeed) {
                b.vx = (b.vx / spd) * this.maxSpeed;
                b.vy = (b.vy / spd) * this.maxSpeed;
            }

            b.x += b.vx * deltaSeconds;
            b.y += b.vy * deltaSeconds;

            // 画面端ループ
            if (b.x < 0) b.x = this.width;
            else if (b.x > this.width) b.x = 0;
            if (b.y < 0) b.y = this.height;
            else if (b.y > this.height) b.y = 0;

            // Step 62: 描画更新 (光の明滅)
            b.glowPhase += deltaSeconds * 3.0;
            const glow = 0.5 + 0.5 * Math.sin(b.glowPhase);
            b.graphics.clear();
            b.graphics.beginFill(0xe0ff88, 0.4 + glow * 0.5);
            b.graphics.drawCircle(b.x, b.y, b.size);
            b.graphics.beginFill(0xffffff, 0.8 * glow);
            b.graphics.drawCircle(b.x, b.y, b.size * 0.5);
            b.graphics.endFill();
        }
    }

    destroy() {
        if (this.container) this.container.destroy({ children: true });
    }
}

// グローバルスコープにもエクスポート
window.BoidSystem = BoidSystem;
