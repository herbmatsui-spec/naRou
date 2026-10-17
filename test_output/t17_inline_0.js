
    // ==================== WEBAUDIO SOUND ENGINE ====================
    const SoundEngine = {
      ctx: null,
      enabled: false,
      bgmInterval: null,

      init() {
        if (!this.ctx) {
          const AudioContext = window.AudioContext || window.webkitAudioContext;
          this.ctx = new AudioContext();
        }
        if (this.ctx.state === 'suspended') {
          this.ctx.resume();
        }
        this.enabled = true;
        document.getElementById("btnAudioToggle").innerText = "🔊 サウンド ON";
        this.startDynamicBGM();
      },

      toggleAudio() {
        if (!this.enabled) {
          this.init();
          this.playSE("level_up");
        } else {
          this.enabled = false;
          if (this.bgmInterval) clearInterval(this.bgmInterval);
          document.getElementById("btnAudioToggle").innerText = "🔇 サウンド OFF";
        }
      },

      playSE(type) {
        if (!this.enabled || !this.ctx) return;
        const now = this.ctx.currentTime;

        if (type === "hit") {
          const osc = this.ctx.createOscillator();
          const gain = this.ctx.createGain();
          osc.type = "sawtooth";
          osc.frequency.setValueAtTime(140, now);
          osc.frequency.exponentialRampToValueAtTime(30, now + 0.12);
          gain.gain.setValueAtTime(0.3, now);
          gain.gain.exponentialRampToValueAtTime(0.01, now + 0.12);
          osc.connect(gain);
          gain.connect(this.ctx.destination);
          osc.start(now);
          osc.stop(now + 0.12);
        } else if (type === "kill") {
          const osc = this.ctx.createOscillator();
          const gain = this.ctx.createGain();
          osc.type = "triangle";
          osc.frequency.setValueAtTime(300, now);
          osc.frequency.exponentialRampToValueAtTime(80, now + 0.25);
          gain.gain.setValueAtTime(0.4, now);
          gain.gain.exponentialRampToValueAtTime(0.01, now + 0.25);
          osc.connect(gain);
          gain.connect(this.ctx.destination);
          osc.start(now);
          osc.stop(now + 0.25);
        } else if (type === "level_up") {
          [440, 554.37, 659.25, 880].forEach((freq, idx) => {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = "sine";
            osc.frequency.setValueAtTime(freq, now + idx * 0.08);
            gain.gain.setValueAtTime(0.2, now + idx * 0.08);
            gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.08 + 0.3);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(now + idx * 0.08);
            osc.stop(now + idx * 0.08 + 0.3);
          });
        } else if (type === "fanfare") {
          // 5音アルペジオ (サーバー側 sound_manager.py の fanfare と同一音列)
          [523, 659, 784, 1046, 1318].forEach((freq, idx) => {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = "square";
            osc.frequency.setValueAtTime(freq, now + idx * 0.09);
            gain.gain.setValueAtTime(0.15, now + idx * 0.09);
            gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.09 + 0.45);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(now + idx * 0.09);
            osc.stop(now + idx * 0.09 + 0.45);
          });
        }
      },

      startDynamicBGM() {
        if (this.bgmInterval) clearInterval(this.bgmInterval);
        const chords = [
          [220, 261.63, 329.63], // Am
          [174.61, 220, 261.63], // F
          [196, 246.94, 293.66], // G
          [164.81, 196, 246.94]  // Em
        ];
        let chordIdx = 0;

        this.bgmInterval = setInterval(() => {
          if (!this.enabled || !this.ctx) return;
          const chord = chords[chordIdx % chords.length];
          chordIdx++;
          const now = this.ctx.currentTime;

          chord.forEach(freq => {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = "sine";
            osc.frequency.setValueAtTime(freq * 0.5, now);
            gain.gain.setValueAtTime(0.001, now);
            gain.gain.linearRampToValueAtTime(0.03, now + 1.2);
            gain.gain.linearRampToValueAtTime(0.001, now + 3.8);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(now);
            osc.stop(now + 4.0);
          });
        }, 4000);
      }
    };

// ==================== PIXI.JS WEBGL RENDER ENGINE ====================
    const canvas = document.getElementById("gameCanvas");

    // モジュールロード待機
    function waitForModules(callback, maxAttempts = 50) {
      let attempts = 0;
      const check = () => {
        attempts++;
        if (window.LightingSystem && window.ParticleSystem &&
            window.PostProcessManager && window.ScreenShake && window.TextureAtlas &&
            window.InteractionManager && window.FoliageFilter && window.FluidRenderer &&
            window.DecalSystem && window.BoidSystem) {
          callback();
        } else if (attempts < maxAttempts) {
          setTimeout(check, 100);
        } else {
          console.error('Module loading timeout');
        }
      };
      check();
    }

    // 2Dフォールバック初期化（WebGL2が利用できない場合）
    function init2DFallback() {
        console.log('Initializing 2D Canvas fallback...');
        const ctx2d = canvas.getContext('2d');
        if (!ctx2d) return;

        // 簡易的な2Dレンダリングループ
        function render2D() {
            ctx2d.fillStyle = '#0a0b10';
            ctx2d.fillRect(0, 0, canvas.width, canvas.height);

            if (!gameState) {
                ctx2d.fillStyle = '#8b9bb4';
                ctx2d.font = '16px var(--font-main)';
                ctx2d.textAlign = 'center';
                ctx2d.fillText('サーバーに接続中……', canvas.width / 2, canvas.height / 2);
            } else {
                // 簡易マップ描画
                const map = gameState.map || [];
                const viewH = map.length;
                const viewW = viewH > 0 ? map[0].length : 0;
                const TILE_SIZE = 24;
                const offsetX = Math.max(0, (canvas.width - viewW * TILE_SIZE) / 2);
                const offsetY = Math.max(0, (canvas.height - viewH * TILE_SIZE) / 2);

                for (let y = 0; y < viewH; y++) {
                    for (let x = 0; x < viewW; x++) {
                        const ch = map[y][x];
                        const px = offsetX + x * TILE_SIZE;
                        const py = offsetY + y * TILE_SIZE;
                        ctx2d.fillStyle = ch === '#' ? '#333' : ch === '>' ? '#f00' : '#1a1a2e';
                        ctx2d.fillRect(px, py, TILE_SIZE, TILE_SIZE);
                    }
                }

                // プレイヤー描画
                if (gameState.player) {
                    const p = gameState.player;
                    const px = offsetX + p.x * TILE_SIZE + TILE_SIZE/2;
                    const py = offsetY + p.y * TILE_SIZE + TILE_SIZE/2;
                    ctx2d.fillStyle = '#0f0';
                    ctx2d.beginPath();
                    ctx2d.arc(px, py, TILE_SIZE/3, 0, Math.PI*2);
                    ctx2d.fill();
                }
            }
            requestAnimationFrame(render2D);
        }
        render2D();
    }

    waitForModules(() => {

    // PixiJSアプリケーションの初期化（WebGL2）
    let pixiApp = null;
    let use2DFallback = false;

    try {
        pixiApp = new PIXI.Application({
            view: canvas,
            width: canvas.width,
            height: canvas.height,
            backgroundColor: 0x000000,
            resolution: window.devicePixelRatio || 1,
            autoDensity: true,
            preferWebGL: true,
            forceCanvas: false
        });
    } catch (error) {
        console.error('WebGL2 initialization failed:', error);
        document.getElementById('gl-error-overlay').style.display = 'flex';
        use2DFallback = true;
        init2DFallback();
        return;
    }

    // レイヤー分離のためのコンテナを作成
    const backgroundLayer = new PIXI.Container();
    const tileLayer = new PIXI.Container();
    const entityLayer = new PIXI.Container();
    const effectLayer = new PIXI.Container();

    // Step 49 & 50: 永続的デカールシステム (DecalSystem) の初期化
    const decalSystem = new DecalSystem(pixiApp, canvas.width, canvas.height);
    backgroundLayer.addChild(decalSystem.sprite);

    // Step 18: 環境干渉 & Foliage フィルターの初期化
    const interactionManager = new InteractionManager();
    const foliageFilter = new FoliageFilter();
    tileLayer.filters = [foliageFilter];

    // Step 35: 流体シミュレーション (FluidRenderer) の初期化
    const fluidRenderer = new FluidRenderer(pixiApp, canvas.width, canvas.height);
    effectLayer.addChild(fluidRenderer.fluidSprite);

    // Step 57: 自律飛行群れパーティクル (BoidSystem) の初期化
    const boidSystem = new BoidSystem(pixiApp, effectLayer, canvas.width, canvas.height, 40);

    // 背景グラフィックを作成（濃紫で塗りつぶし）
    const backgroundGraphics = new PIXI.Graphics();
    function updateBackground() {
        backgroundGraphics.clear();
        backgroundGraphics.beginFill(0x0a0b10); // 濃紫 (#0a0b10)
        backgroundGraphics.drawRect(0, 0, pixiApp.screen.width, pixiApp.screen.height);
        backgroundGraphics.endFill();
    }
    // 初期背景を描画
    updateBackground();
    backgroundLayer.addChild(backgroundGraphics);

    // T11 案5/案8: フロアテーマ別戦闘バックドロップ & ワールドマップオーバーレイ (Mキー)
    const battleBackdrop = window.BattleBackdrop ? new BattleBackdrop(pixiApp, backgroundLayer, canvas.width, canvas.height) : null;
    const worldMapOverlay = window.WorldMapOverlay ? new WorldMapOverlay(pixiApp) : null;

    // ステージにレイヤーを追加（下から上へ）
    pixiApp.stage.addChild(backgroundLayer);
    pixiApp.stage.addChild(tileLayer);
    pixiApp.stage.addChild(entityLayer);
    pixiApp.stage.addChild(effectLayer);

    // ライティングシステムを初期化
    const viewW = 40;
    const viewH = 24;
    const TILE_SIZE = 24;
    const lightingSystem = new LightingSystem(
        pixiApp,
        tileLayer,
        viewW * TILE_SIZE,
        viewH * TILE_SIZE
    );

    // パーティクルシステムを初期化
    const particleSystem = new ParticleSystem(pixiApp, effectLayer);

    // T16 案6: 天候パーティクルシステムを初期化 (effectLayer 直下の専用レイヤー)
    const weatherLayer = new PIXI.Container();
    pixiApp.stage.addChildAt(weatherLayer, pixiApp.stage.getChildIndex(effectLayer));
    const weatherSystem = (typeof WeatherSystem !== "undefined") ? new WeatherSystem(pixiApp, weatherLayer) : null;

    // ポストプロセスマネージャーを初期化
    const postProcessManager = new PostProcessManager(pixiApp);
    pixiApp.stage.addChild(postProcessManager.getEffectsContainer());

    // スクリーンシェイクを初期化
    const screenShake = new ScreenShake(pixiApp.stage, 5, 0.5);

    // カットシーン演出ディレクターを初期化 (FF6案6: DOMオーバーレイ式)
    const cutsceneDirector = (typeof CutsceneDirector !== "undefined") ? new CutsceneDirector() : null;

    // T18 案3: ボス戦専用演出ディレクター (PIXI DOM併用) を初期化
    // FF6_BOSS アトラスはバックグラウンドで事前ロードし、失敗時はフォールバック描画に切り替わる
    const bossDirector = (typeof BossBattleDirector !== "undefined") ? new BossBattleDirector(pixiApp) : null;
    if (bossDirector) bossDirector.init();

    // リサイズ処理
    function resize() {
        const width = window.innerWidth;
        const height = window.innerHeight;
        pixiApp.renderer.resize(width, height);
        // 背景グラフィックもリサイズに合わせて更新
        updateBackground();
    }
    window.addEventListener('resize', resize);
    // 初期リサイズ
    resize();

    // テクスチャアトラス
    let tileAtlas = null;
    let tileAnimCache = {};      // 静的タイルアニメーションキャッシュ
    let entityAnimCache = {};    // エンティティアニメーションキャッシュ

    // TileAtlasの初期化
    async function initTileAtlas() {
        try {
            // アトラス画像をロード
            const atlasImage = new Image();
            atlasImage.src = 'demos/assets/font_atlas.png';

            await new Promise((resolve, reject) => {
                atlasImage.onload = resolve;
                atlasImage.onerror = reject;
            });

            // Step 10: ノーマルマップ画像をロード
            const normalAtlasImage = new Image();
            normalAtlasImage.src = 'demos/assets/normal_atlas.png';
            await new Promise((resolve) => {
                normalAtlasImage.onload = resolve;
                normalAtlasImage.onerror = () => {
                    console.warn('Normal atlas not found, skipping');
                    resolve();
                };
            });

            // アトラスメタデータをロード
            const metadataResponse = await fetch('demos/assets/font_atlas.json');
            const metadata = await metadataResponse.json();

            // PixiJSテクスチャを作成
            const baseTexture = new PIXI.BaseTexture(atlasImage);
            tileAtlas = new TextureAtlas(baseTexture, metadata);

            if (normalAtlasImage.complete && normalAtlasImage.naturalWidth > 0) {
                const normalBaseTexture = new PIXI.BaseTexture(normalAtlasImage);
                tileAtlas.loadNormalMap(normalBaseTexture);
                if (lightingSystem && lightingSystem.normalMapFilter) {
                    lightingSystem.normalMapFilter.uniforms.uNormalSampler = normalBaseTexture;
                    tileLayer.filters = [lightingSystem.normalMapFilter];
                }
            }

            // タイル文字と色のマッピング（テクスチャアトラスを使用）
            let tileTextures = {
                '#': tileAtlas.getTexture('#'),
                '.': tileAtlas.getTexture('.'),
                '>': tileAtlas.getTexture('>'),
                ' ': tileAtlas.getTexture(' '),
                '⛩️': tileAtlas.getTexture('⛩️')
            };

            console.log('Texture atlas and normal maps loaded successfully');
        } catch (error) {
            console.error('Failed to load TileAtlas:', error);
        }
    }

    // タイル描画用ヘルパー: マップ配列からタイルIDを解決
    function getTileDefId(mapTile) {
        // マップから送られてくる文字をTileDef IDにマッピング
        const map = {
            '#': 'TILE_WALL',
            '.': 'TILE_FLOOR',
            '>': 'TILE_STAIRS_DOWN',
            '<': 'TILE_STAIRS_UP',
            '~': 'TILE_WATER',
            '^': 'TILE_TRAP',
            '⛩️': 'TILE_FLOOR',  // 祭壇は床扱い
            // T11 案1: FF6風テライン（サーバーはタイルID文字列を送るため同一IDへマップ）
            'TILE_FF6_WALL_STONE': 'TILE_FF6_WALL_STONE',
            'TILE_FF6_WALL_IRON': 'TILE_FF6_WALL_IRON',
            'TILE_FF6_WALL_BLUE': 'TILE_FF6_WALL_BLUE',
            'TILE_FF6_FLOOR_COBBLE': 'TILE_FF6_FLOOR_COBBLE',
            'TILE_FF6_FLOOR_MOSS': 'TILE_FF6_FLOOR_MOSS',
            'TILE_FF6_FLOOR_WOOD': 'TILE_FF6_FLOOR_WOOD',
            'TILE_FF6_WATER': 'TILE_FF6_WATER',
            'TILE_FF6_LAVA': 'TILE_FF6_LAVA',
            'TILE_FF6_GRASS': 'TILE_FF6_GRASS',
            'TILE_FF6_FLOWER': 'TILE_FF6_FLOWER',
            'TILE_DOOR_CLOSED': 'TILE_DOOR_CLOSED',
            'TILE_DOOR_OPEN': 'TILE_DOOR_OPEN',
        };
        return map[mapTile] || 'TILE_FLOOR';
    }

    // タイル描画用ヘルパー: アニメーションタイルかどうか判定
    function isAnimatedTile(tileId) {
        const td = tileAtlas?.defs[tileId];
        return td && td.animated;
    }

    // 向き計算ヘルパー (0:下, 1:左, 2:右, 3:上)
    function calculateFacing(dx, dy) {
        if (Math.abs(dx) > Math.abs(dy)) {
            return dx > 0 ? 2 : 1;
        } else {
            return dy > 0 ? 0 : 3;
        }
    }

    // 前フレーム位置から向き推定
    function estimateFacing(ent, prevEntities) {
        if (!prevEntities) return ent.facing || 0;
        const prev = prevEntities.find(e => e.id === ent.id || (e.world_x === ent.world_x && e.world_y === ent.world_y));
        if (!prev) return ent.facing || 0;
        const dx = ent.x - prev.x;
        const dy = ent.y - prev.y;
        if (dx === 0 && dy === 0) return ent.facing || 0;
        return calculateFacing(dx, dy);
    }

    // エンティティごとの攻撃タイマー管理
    const entityAttackTimers = new Map(); // entity_id -> { timer, duration }

    // T18 案3: ボス種別判定 (monster_type ベース。void_boss 等の *_boss をボス扱いとする)
    const BOSS_MONSTER_TYPES = ["void_boss"];
    function isBossEntity(ent) {
      if (!ent || ent.is_player || ent.is_pet) return false;
      if (BOSS_MONSTER_TYPES.includes(ent.monster_type)) return true;
      return typeof ent.monster_type === "string" && ent.monster_type.endsWith("_boss");
    }

    // 汎用エンティティTileDef ID解決
    function getEntityTileId(ent) {
        if (ent.is_player) return "PLAYER";
        if (ent.is_pet) return "PET";
        // T18 案3: ボスは FF6_BOSS TileDef (64x64) を優先 (アトラスに未定義の種別は従来描画へフォールバック)
        if (isBossEntity(ent) && tileAtlas && tileAtlas.defs && tileAtlas.defs["FF6_BOSS"]) {
            return "FF6_BOSS";
        }
        // 将来的に種別対応:
        // if (ent.monster_type) return MONSTER_TYPE_MAP[ent.monster_type] || "ENEMY_GOBLIN";
        return "ENEMY_GOBLIN";
    }

    // T18 案3: ボス出現 → 入場演出 / HPバー更新 / 消滅 → 撃破演出 の追跡
    // (サーバーは可視 & hp>0 のエンティティのみ送信するため、ボスが一覧から消えたら撃破扱いとする)
    let activeBossId = null; // 表示中ボスの識別子 (null = ボス不在)
    function updateBossDirectorState() {
      if (!bossDirector) return;
      const ents = gameState.entities || gameState.enemies || [];
      const boss = ents.find(isBossEntity);
      if (boss) {
        const bid = boss.id || `${boss.world_x},${boss.world_y}`;
        if (activeBossId === null) {
          // ボスが視界に入った最初のフレームで入場演出
          activeBossId = bid;
          bossDirector.playEntrance(boss.name || "？？？");
        } else if (activeBossId === bid) {
          bossDirector.updateBossHp(boss.hp, boss.max_hp);
        }
      } else if (activeBossId !== null) {
        // 前フレームまで存在したボスが消えた → 撃破演出
        activeBossId = null;
        bossDirector.onDefeated();
      }
    }

    function updateEntityAttackState(ent) {
        // サーバーから attack_timer が来ていれば優先
        if (ent.attack_timer > 0) {
            const id = ent.id || `${ent.world_x},${ent.world_y}`;
            entityAttackTimers.set(id, { timer: ent.attack_timer, duration: 0.5 });
            return true;
        }
        return false;
    }

    // TileAtlas初期化
    initTileAtlas();

    // パフォーマンス監視
    let lastFrameTime = performance.now();
    let frameCount = 0;
    let fps = 60;
    let qualityReduced = false;

    function monitorPerformance() {
        const now = performance.now();
        const dt = now - lastFrameTime;
        lastFrameTime = now;
        fps = Math.round(1000 / dt);
        frameCount++;

        if (frameCount % 60 === 0) {
            console.log(`FPS: ${fps}, Draw calls: ${pixiApp.renderer.drawCount || 'N/A'}`);
        }

        if (fps < 30 && !qualityReduced) {
            qualityReduced = true;
            console.warn('Performance low, reducing quality');
            if (particleSystem) particleSystem.maxParticles = 250;
            if (postProcessManager) postProcessManager.setBloomEnabled(false);
            if (tileAtlas) {
                for (const anim of tileAtlas.animatedSpriteCache.values()) {
                    anim.animationSpeed *= 0.5;
                }
            }
        } else if (fps > 50 && qualityReduced) {
            qualityReduced = false;
            console.log('Performance recovered, restoring quality');
            if (particleSystem) particleSystem.maxParticles = 500;
            if (postProcessManager) postProcessManager.setBloomEnabled(true);
            if (tileAtlas) {
                for (const anim of tileAtlas.animatedSpriteCache.values()) {
                    anim.animationSpeed *= 2;
                }
            }
        }
    }

    let gameState = null;
    let animTime = 0;
    let prevPlayerPos = null;
    let prevPlayerHp = null;
    let prevPlayerLevel = null; // レベルアップ差分検知用 (FF6案9)

    // ==================== 打撃感フィードバック (T17案4) ====================
    // 「命中→揺れ→ヒットストップ→赤ビネット」の統合パターン
    const HIT_FEEDBACK_CRIT_THRESHOLD = 20; // クリティカル判定のダメージ閾値
    const HIT_STOP_TIME_SCALE = 0.05;       // ヒットストップ中の時間スケール
    const HIT_STOP_MIN = 0.06;              // ヒットストップ最短時間 (秒)
    const HIT_STOP_MAX = 0.09;              // ヒットストップ最長時間 (秒)
    const VIGNETTE_BASE = 0.4;              // 通常時のビネット強度
    let hitStopTimer = 0.0;                 // ヒットストップ残り時間 (秒)
    let frameDt = 0.016;                    // ヒットストップ適用済みの直近フレームdt (秒)
    let lastSpellFxId = 0;                  // 消費済み詠唱イベントID (spell_fx重複再生防止)
    const prevEnemyHpMap = new Map();       // エンティティID → 前フレームHP (与ダメ検知用)

    /**
     * 被弾・与弾共通の打撃感フィードバックを適用する
     * 揺れ＋ヒットストップ＋赤ビネットを強度に応じて一括で発火する
     * @param {number} intensity - 強度 (0.2〜1.5、クリティカルや被弾で増加)
     */
    function applyHitFeedback(intensity = 1.0) {
      const strength = Math.max(0.2, Math.min(1.5, intensity));
      // 揺れ: 強度に応じてプリセットを使い分け
      screenShake.shake(strength >= 1.0 ? 'heavy' : strength >= 0.7 ? 'medium' : 'light');
      // ヒットストップ: 時間スケールを一時的に0.05倍 (60-90ms)
      hitStopTimer = Math.min(HIT_STOP_MAX, HIT_STOP_MIN + strength * 0.02);
      // 赤ビネット: 一時的に強度を上げ、一定時間後にベースへ戻す
      if (postProcessManager.setVignetteIntensity) {
        postProcessManager.setVignetteIntensity(Math.min(1.0, VIGNETTE_BASE + strength * 0.3));
        setTimeout(() => {
          postProcessManager.setVignetteIntensity(VIGNETTE_BASE);
        }, 400);
      }
    }

    function render() {
      animTime += 0.05;

      // パフォーマンス監視
      monitorPerformance();

      // パーティクルシステムを更新 (ヒットストップ適用済みdt)
      particleSystem.update(frameDt);

      // ポストプロセスを更新 (ヒットストップ適用済みdt)
      postProcessManager.update(frameDt);

      // T11 案5: バックドロップ更新（星の瞬き・リサイズ追従）
      if (battleBackdrop) battleBackdrop.update(frameDt);

      // スクリーンシェイクを更新 (ヒットストップ中は静止してから揺れる)
      screenShake.update(frameDt);

      if (!gameState) {
        // サーバーに接続中... をDOMオーバーレイで表示（Canvas 2Dコンテキストを使用しない）
        if (!document.getElementById('loading-overlay')) {
            const overlay = document.createElement('div');
            overlay.id = 'loading-overlay';
            overlay.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.8);color:#8b9bb4;font:16px var(--font-main);z-index:50;pointer-events:none;';
            overlay.textContent = 'サーバーに接続中……';
            document.getElementById('viewportPanel').appendChild(overlay);
        }
        return;
    } else {
        // 接続完了時はローディングオーバーレイを削除
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) loadingOverlay.remove();
    }
        // T18 案3: ボス出現/HP更新/撃破の追跡 (タイル描画より先に実行し、後段で例外が出ても演出を担保)
        updateBossDirectorState();
        // Clear layers each frame (except background which is static)
        tileLayer.removeChildren();
        entityLayer.removeChildren();
        effectLayer.removeChildren();

        const map = gameState.map || [];
        const lightMap = gameState.light_map || [];
        const lightColor = gameState.light_color || [];
        const lightSources = gameState.light_sources || [];
        const enemyCones = gameState.enemy_cones || [];
        const viewH = map.length;
        const viewW = viewH > 0 ? map[0].length : 0;

        // 画面中央オフセット
        const offsetX = Math.max(0, (canvas.width - viewW * TILE_SIZE) / 2);
        const offsetY = Math.max(0, (canvas.height - viewH * TILE_SIZE) / 2);

        // Step 5 & 8: 霧密度 (Fog Density) の同期
        window.fogDensity = gameState.fog_density !== undefined ? gameState.fog_density : 0.35;

        // ライティングシステムを更新（乗算ブレンド＋松明フリッカー＋敵視界コーン＋GI/フォグ）
        lightingSystem.updateLightMap(lightMap, lightColor);
        lightingSystem.setLightSources(lightSources, animTime);
        lightingSystem.setEnemyCones(enemyCones, animTime);
        if (lightingSystem.updateSDF && gameState.raw_tiles) {
            const blockedGrid = gameState.raw_tiles.map(row => row.map(t => (t === '#' ? 1 : 0)));
            lightingSystem.updateSDF(blockedGrid);
        }
        if (lightingSystem.renderGI) {
            lightingSystem.renderGI(animTime);
        }
        if (lightingSystem.updateNormalLighting && gameState.player) {
            const playerPx = offsetX + (gameState.player.x + 0.5) * TILE_SIZE;
            const playerPy = offsetY + (gameState.player.y + 0.5) * TILE_SIZE;
            lightingSystem.updateNormalLighting(playerPx, playerPy);
        }
        lightingSystem.applyLighting(pixiApp.stage);

        // Step 19 & 21: 環境干渉 (Foliage Bending) の Interactor 更新
        if (interactionManager && foliageFilter) {
            const interactors = [];
            if (gameState.player) {
                interactors.push({
                    x: offsetX + (gameState.player.x + 0.5) * TILE_SIZE,
                    y: offsetY + (gameState.player.y + 0.5) * TILE_SIZE,
                    radius: 28.0
                });
            }
            if (Array.isArray(gameState.entities)) {
                for (const ent of gameState.entities.slice(0, 7)) {
                    interactors.push({
                        x: offsetX + (ent.x + 0.5) * TILE_SIZE,
                        y: offsetY + (ent.y + 0.5) * TILE_SIZE,
                        radius: 22.0
                    });
                }
            }
            interactionManager.updateInteractors(interactors);
            foliageFilter.update(interactionManager, 0.016);
        }

        // 深度別カラーグレーディング（ポストプロセス）
        if (postProcessManager && postProcessManager.setColorGrade) {
            postProcessManager.setColorGrade(gameState.dungeon_level || 0);
        }

        // 1. タイル描画 (床・壁・階段) - TileAtlas使用
        // T11 案5: ダンジョン階層からバックドロップのテーマを切り替え
        if (battleBackdrop) battleBackdrop.setTheme(gameState.dungeon_level || 0);
        // T16 案6: フロアテーマ連動の天候 (dungeon_themes.yaml のテーマ名から判定、差分検知付き)
        if (weatherSystem) weatherSystem.setWeatherForLevel(gameState.dungeon_level || 0);
        for (let y = 0; y < viewH; y++) {
          for (let x = 0; x < viewW; x++) {
            const mapTile = map[y][x];
            const tileId = getTileDefId(mapTile);
            const light = lightMap[y] ? lightMap[y][x] : 0;

            const px = offsetX + x * TILE_SIZE;
            const py = offsetY + y * TILE_SIZE;

            // オートタイルバリアント計算（壁・床のみ）
            let variant = 0;
            if (tileId === "TILE_WALL" || tileId === "TILE_FLOOR") {
              variant = tileAtlas.calculateNeighborMask(map, x, y, tileId);
            }

            // アニメーションタイル判定
            const td = tileAtlas.defs[tileId];
            let sprite;
            if (td && td.animated) {
              // アニメーションスプライト作成・キャッシュ
              const animKey = `${tileId}_${variant}_${td.states?.[0]||'idle'}_${td.fps}`;
              if (!tileAnimCache[animKey]) {
                tileAnimCache[animKey] = tileAtlas.createAnimatedSprite(tileId, { variant, fps: td.fps });
              }
              sprite = tileAnimCache[animKey];
              sprite.x = px; sprite.y = py;
              if (sprite.parent !== tileLayer) tileLayer.addChild(sprite);
            } else {
              // 静的スプライト
              sprite = tileAtlas.createSprite(tileId, { variant });
              sprite.x = px; sprite.y = py;
              tileLayer.addChild(sprite);
            }
          }
        }

        // 2. エンティティ描画 (プレイヤー・ペット・モンスター) - TileAtlasアニメーションスプライト使用
        const entities = gameState.entities || [];
        const player = gameState.player;

        // プレイヤーの移動パーティクル & 足跡デカール
        if (player && prevPlayerPos) {
          const dx = player.x - prevPlayerPos.x;
          const dy = player.y - prevPlayerPos.y;
          if (dx !== 0 || dy !== 0) {
            // 移動時にほこりのパーティクルを発生
            particleSystem.emitEffect('step',
              offsetX + player.x * TILE_SIZE,
              offsetY + player.y * TILE_SIZE,
              3
            );
            // Step 54: 足跡スタンプを地面に焼き付け
            if (decalSystem) {
              decalSystem.stampFootprint(
                offsetX + (player.x + 0.5) * TILE_SIZE,
                offsetY + (player.y + 0.5) * TILE_SIZE,
                dx, dy
              );
            }
          }
        }

        // プレイヤーのHP変化パーティクル
        if (player && prevPlayerHp !== null) {
          if (player.hp < prevPlayerHp) {
            // ダメージを受けた
            particleSystem.emitEffect('damage',
              offsetX + player.x * TILE_SIZE,
              offsetY + player.y * TILE_SIZE,
              5
            );
            // ダメージ数を浮上表示（改善案5: クラストグル制御の例）
            const dmg = prevPlayerHp - player.hp;
            showFloatText(`-${dmg}`,
              offsetX + player.x * TILE_SIZE,
              offsetY + player.y * TILE_SIZE - 28,
              '#ff6b6b');
            // T17案4: 命中→揺れ→ヒットストップ→赤ビネットの統合パターン
            // (dmgが閾値以上のクリティカル時は強度増)
            applyHitFeedback(dmg >= HIT_FEEDBACK_CRIT_THRESHOLD ? 1.0 : 0.6);

            // Step 38: 血痕流体パーティクルを散布
            if (fluidRenderer) {
                fluidRenderer.spawnSpatter(
                    offsetX + (player.x + 0.5) * TILE_SIZE,
                    offsetY + (player.y + 0.5) * TILE_SIZE,
                    'blood', 8, 70.0
                );
            }
            // Step 27 & 46: 衝撃波とダメージ色収差 (色収差はダメージ量に連動)
            if (postProcessManager) {
                postProcessManager.triggerDamageDistortion(dmg >= HIT_FEEDBACK_CRIT_THRESHOLD ? 1.2 : 0.8);
                postProcessManager.addShockwave(
                    offsetX + (player.x + 0.5) * TILE_SIZE,
                    offsetY + (player.y + 0.5) * TILE_SIZE,
                    140, 0.45
                );
            }
          } else if (player.hp > prevPlayerHp) {
            // 回復した
            particleSystem.emitEffect('heal',
              offsetX + player.x * TILE_SIZE,
              offsetY + player.y * TILE_SIZE,
              8
            );
          }
        }

        // プレイヤーのレベルアップ検知 (FF6案9: 光の柱演出)
        if (player && prevPlayerLevel !== null && player.level > prevPlayerLevel) {
          // 金色のマジックパーティクルが上昇する光の柱
          particleSystem.emitEffect('level_up',
            offsetX + player.x * TILE_SIZE,
            offsetY + player.y * TILE_SIZE,
            10
          );
          showFloatText('LEVEL UP!',
            offsetX + player.x * TILE_SIZE,
            offsetY + player.y * TILE_SIZE - 40,
            '#ffd700');
          if (postProcessManager) {
            postProcessManager.addShockwave(
              offsetX + (player.x + 0.5) * TILE_SIZE,
              offsetY + (player.y + 0.5) * TILE_SIZE,
              160, 0.6
            );
          }
          SoundEngine.playSE('fanfare');
        }

        // プレイヤー位置を記録
        if (player) {
          prevPlayerPos = { x: player.x, y: player.y };
          prevPlayerHp = player.hp;
          prevPlayerLevel = player.level;
        }

        // 前フレームエンティティ保存（向き推定用）
        const prevEntities = entities.map(e => ({...e}));

        // 呪文詠唱エフェクト (T17案2: サーバーのspell_fxイベントをemitSpellの多層魔法として再生)
        // イベントIDは単調増加するため、未消費のものだけ再生してポーリング重複を防ぐ
        if (Array.isArray(gameState.spell_fx)) {
          gameState.spell_fx.forEach(sfx => {
            if (sfx.id > lastSpellFxId) {
              lastSpellFxId = sfx.id;
              particleSystem.emitSpell(sfx.element || 'magic',
                offsetX + (sfx.x + 0.5) * TILE_SIZE,
                offsetY + (sfx.y + 0.5) * TILE_SIZE
              );
            }
          });
        }

        // 与ダメ検知: 敵のHP減少時に小さめのヒットフィードバック (T17案4)
        if (Array.isArray(entities)) {
          const aliveKeys = new Set();
          for (const ent of entities) {
            if (ent.is_player || ent.is_pet) continue;
            const entKey = ent.id !== undefined ? ent.id : `${ent.world_x},${ent.world_y}`;
            aliveKeys.add(entKey);
            const prevHp = prevEnemyHpMap.get(entKey);
            if (prevHp !== undefined && ent.hp < prevHp && ent.hp > 0) {
              // 与ダメ側: 小さめのヒットフィードバック＋デジタルヒット
              applyHitFeedback(0.5);
              if (postProcessManager) postProcessManager.triggerDamageDistortion(0.5);
            }
            prevEnemyHpMap.set(entKey, ent.hp);
          }
          // 存在しなくなったエンティティの記録を掃除
          for (const entKey of prevEnemyHpMap.keys()) {
            if (!aliveKeys.has(entKey)) prevEnemyHpMap.delete(entKey);
          }
        }

        entities.forEach(ent => {
          const px = offsetX + ent.x * TILE_SIZE;
          const py = offsetY + ent.y * TILE_SIZE;

          // 息遣いアニメーション
          const bounce = Math.sin(animTime * 4 + ent.x) * 1.5;

          // エンティティのTileDef ID決定
          let tileId = getEntityTileId(ent);

          const td = tileAtlas.defs[tileId];
          if (!td) return;

          // 向き決定: サーバー優先 → 推定
          const dir = ent.facing !== undefined ? ent.facing : estimateFacing(ent, prevEntities);

          // 状態決定: サーバー優先 → 推定
          let state = ent.state || "idle";
          const isAttacking = state === "attack";

          // 攻撃タイマー管理
          if (isAttacking) {
              const id = ent.id || `${ent.world_x},${ent.world_y}`;
              entityAttackTimers.set(id, { timer: 0.5, duration: 0.5 });
}

           // 攻撃中は強制的にattack状態維持
          const attackInfo = entityAttackTimers.get(ent.id || `${ent.world_x},${ent.world_y}`);
          if (attackInfo) {
              state = "attack";
              attackInfo.timer -= 1/60;
              if (attackInfo.timer <= 0) {
                  entityAttackTimers.delete(ent.id || `${ent.world_x},${ent.world_y}`);
                  state = "idle";
              }
          } else if (ent.hp <= 0) {
              state = "dead";
          } else if (ent.moving || (ent.vx !== 0 || ent.vy !== 0)) {
              state = "walk";
          }

          // アニメーションキー: tileId_direction_state
          const animKey = `${tileId}_${dir}_${state}`;
          if (!entityAnimCache[animKey]) {
              const loop = state !== "attack" && state !== "dead";
              const fps = state === "attack" ? 12 : td.fps;
              entityAnimCache[animKey] = tileAtlas.createAnimatedSprite(tileId, {
                  direction: dir, state, fps, loop
              });
          }
          const sprite = entityAnimCache[animKey];

          // 攻撃・死亡アニメは最初から再生
          if ((state === "attack" || state === "dead") && !sprite._playing) {
              sprite.gotoAndPlay(0);
              sprite._playing = true;
              sprite.onComplete = () => {
sprite._playing = false;
                   if (state === "dead") sprite.visible = false;
               };
           }

           sprite.x = px;
          sprite.y = py + bounce;
          entityLayer.addChild(sprite);

          // HPバー（プレイヤーとペット以外のエンティティに対して）
          if (!ent.is_player && !ent.is_pet && ent.max_hp > 0) {
            const hpRatio = Math.max(0, Math.min(1, ent.hp / ent.max_hp));

            // HPバーの背景
            const hpBarBg = new PIXI.Graphics();
            hpBarBg.beginFill(0x000000, 0.6);
            hpBarBg.drawRect(-TILE_SIZE * 0.5 + 2, -TILE_SIZE * 0.5 - 4, TILE_SIZE - 4, 3);
            hpBarBg.endFill();
            hpBarBg.x = px;
            hpBarBg.y = py + bounce;
            entityLayer.addChild(hpBarBg);

            // HPバーの前景
            const hpColor = hpRatio > 0.5 ? 0x2ecc71 : hpRatio > 0.2 ? 0xf39c12 : 0xe74c3c;
            const hpBarFg = new PIXI.Graphics();
            hpBarFg.beginFill(hpColor);
            hpBarFg.drawRect(-TILE_SIZE * 0.5 + 2, -TILE_SIZE * 0.5 - 4, (TILE_SIZE - 4) * hpRatio, 3);
            hpBarFg.endFill();
            hpBarFg.x = px;
            hpBarFg.y = py + bounce;
            entityLayer.addChild(hpBarFg);
          }
        });

        // 3. アイテム描画 - TileAtlas使用
        // 品質色マッピング
        const qualityColors = {
          'common': 0xcccccc,
          'uncommon': 0x33ff33,
          'rare': 0x3366ff,
          'epic': 0x9933ff,
          'legendary': 0xffaa00
        };

        const items = gameState.items || [];
        items.forEach(item => {
          const px = offsetX + item.x * TILE_SIZE;
          const py = offsetY + item.y * TILE_SIZE;

          // アイテムのTileDef ID決定
          let tileId = "ITEM_POTION";
          if (item.tile_id && tileAtlas.defs[item.tile_id]) {
            tileId = item.tile_id;
          } else if (item.char === '$' || item.char === '💰') {
            tileId = "ITEM_GOLD";
          } else if (item.char === ')') {
            tileId = "ITEM_WEAPON";
          } else if (item.char === '[') {
            tileId = "ITEM_ARMOR";
          }

          const td = tileAtlas.defs[tileId];
          if (!td) return;

          let sprite;
          if (td.animated) {
            const animKey = `${tileId}_idle_${td.fps}`;
            if (!tileAnimCache[animKey]) {
              tileAnimCache[animKey] = tileAtlas.createAnimatedSprite(tileId, { fps: td.fps });
            }
            sprite = tileAnimCache[animKey];
            sprite.x = px; sprite.y = py;
            if (sprite.parent !== entityLayer) entityLayer.addChild(sprite);
          } else {
            sprite = tileAtlas.createSprite(tileId, {
                variant: item.variant || 0,
                tint: qualityColors[item.quality] || 0xffffff
            });
            sprite.x = px; sprite.y = py;
            entityLayer.addChild(sprite);
          }
        });

        // TODO: エフェクト描画（パーティクル、ライティング等）
      }
      // レンダリングはPixiJSが自動的に行うため、requestAnimationFrameは不要
    }

    // ==================== T16 案1: ATB風行動順バー ====================
    // プレイヤー / ペット / 直近敵 3 体の行動順を 5 セグメントの擬似ゲージで表示する。
    // サーバ state の entities に速度・AP は含まれないため、名前から決定論的に
    // 擬似速度を算出し、クライアント側でゲージを進行させる。
    const ATB_SEGMENT_COUNT = 5;
    const atbState = { key: '', fills: [], gauges: [] };

    function atbPseudoSpeed(name) {
      // 名前の文字コード和から決定論的な擬似速度係数 (60..140) を作る
      let sum = 0;
      for (let i = 0; i < name.length; i++) sum += name.charCodeAt(i);
      return 60 + (sum % 81);
    }

    function updateAtbBar(state, dt) {
      const bar = document.getElementById('ff6AtbBar');
      if (!bar || !state) return;

      const player = state.player;
      const entities = Array.isArray(state.entities) ? state.entities : [];
      const pet = entities.find(e => e.is_pet) || null;
      const enemies = entities
        .filter(e => !e.is_player && !e.is_pet)
        .map(e => ({ e, dist: player ? (e.x - player.x) ** 2 + (e.y - player.y) ** 2 : 0 }))
        .sort((a, b) => a.dist - b.dist)
        .slice(0, 3)
        .map(o => o.e);

      const actors = [];
      if (player) actors.push({ name: player.name || 'プレイヤー', kind: 'player' });
      if (pet) actors.push({ name: pet.name || 'ペット', kind: 'pet' });
      for (const e of enemies) actors.push({ name: e.name || e.char || '敵', kind: 'enemy' });
      while (actors.length < ATB_SEGMENT_COUNT) actors.push(null); // 空スロット
      actors.length = ATB_SEGMENT_COUNT;

      // エンティティ構成が変わったときだけ DOM を再構築する
      const key = actors.map(a => (a ? `${a.kind}:${a.name}` : '-')).join('|');
      if (key !== atbState.key) {
        atbState.key = key;
        bar.innerHTML = '';
        atbState.fills = [];
        atbState.gauges = actors.map(a => (a ? 0.15 + Math.random() * 0.45 : 0));
        actors.forEach(a => {
          const seg = document.createElement('div');
          seg.className = 'ff6-atb-segment' + (a ? ` ff6-atb-segment--${a.kind}` : '');
          const fill = document.createElement('div');
          fill.className = 'ff6-atb-fill';
          seg.appendChild(fill);
          bar.appendChild(seg);
          atbState.fills.push(a ? fill : null);
        });
      }

      // 擬似 ATB 進行: 速度係数に応じてゲージを溜め、満タンで行動完了→次ターンへ
      for (let i = 0; i < ATB_SEGMENT_COUNT; i++) {
        const a = actors[i];
        const fill = atbState.fills[i];
        if (!a || !fill) continue;
        atbState.gauges[i] += (atbPseudoSpeed(a.name) / 60) * dt * 0.35;
        if (atbState.gauges[i] >= 1) atbState.gauges[i] = 0;
        fill.style.width = `${Math.min(100, atbState.gauges[i] * 100)}%`;
      }
    }

    // PixiJSのtickerでレンダリングループを開始
    pixiApp.ticker.add((delta) => {
      const rawDt = delta / 60.0;
      let dt = rawDt;
      // T17案4: ヒットストップ中は時間スケールを0.05倍に低下 (打撃の瞬間を静止させる)
      if (hitStopTimer > 0) {
        hitStopTimer -= rawDt;
        dt = rawDt * HIT_STOP_TIME_SCALE;
      }
      frameDt = dt;
      if (fluidRenderer) {
          fluidRenderer.update(dt);
          fluidRenderer.render();
      }
      if (postProcessManager) {
          postProcessManager.update(dt);
      }
      if (boidSystem) {
          const playerPos = gameState && gameState.player ? {
              x: (gameState.player.x + 0.5) * TILE_SIZE,
              y: (gameState.player.y + 0.5) * TILE_SIZE
          } : null;
          boidSystem.update(dt, playerPos, gameState ? gameState.light_sources : []);
      }
      // T16 案6: 天候パーティクルを更新
      if (weatherSystem) weatherSystem.update(dt);
      // T16 案1: ATB風行動順バーを更新 (擬似計算)
      updateAtbBar(gameState, dt);
      render();
    });

    // Step 68: UIボタンの波紋クリック（Ripple）エフェクト初期化
    document.addEventListener('click', (e) => {
      const btn = e.target.closest('.hotbar-btn, .tab-btn, .dpad-btn, .audio-btn');
      if (btn) {
        const circle = document.createElement('span');
        const diameter = Math.max(btn.clientWidth, btn.clientHeight);
        const radius = diameter / 2;
        const rect = btn.getBoundingClientRect();
        circle.style.width = circle.style.height = `${diameter}px`;
        circle.style.left = `${e.clientX - rect.left - radius}px`;
        circle.style.top = `${e.clientY - rect.top - radius}px`;
        circle.classList.add('ripple-effect');
        const oldRipple = btn.getElementsByClassName('ripple-effect')[0];
        if (oldRipple) oldRipple.remove();
        btn.appendChild(circle);
        setTimeout(() => circle.remove(), 500);
      }
    });

    // ==================== アニメーション制御の例（改善案5） ====================
    // クラスの付加・削除でトランジションを制御し、アイテム獲得・ダメージ表示を
    // 浮上（.float-up）させてから要素を削除する。
    function showFloatText(text, x, y, color = '#ffd700') {
      const el = document.createElement('div');
      el.className = 'float-up';
      el.textContent = text;
      el.style.position = 'fixed';
      el.style.left = `${x}px`;
      el.style.top = `${y}px`;
      el.style.color = color;
      el.style.pointerEvents = 'none';
      el.style.zIndex = 2000;
      el.style.fontWeight = '700';
      document.body.appendChild(el);
      // 連続発生時にもトランジションを再起動するため、一度削除して再付与
      el.classList.remove('float-up');
      void el.offsetHeight; // リフロー強制
      el.classList.add('float-up');
      setTimeout(() => {
        el.classList.remove('float-up');
        el.remove();
      }, 350); // --animation-duration-slow と同等
    }

    // ==================== STATE SYNC & API ====================
    async function fetchState() {
      try {
        const res = await fetch("/api/state");
        if (res.ok) {
          gameState = await res.json();
          consumePendingEvents(gameState);
          updateUI(gameState);
        }
      } catch (err) {
        console.error("State sync failed:", err);
      }
    }

    // pending_events消費: サーバー発の演出イベントをクライアント演出へ振り分け (FF6案6)
    // レベルアップ演出は prevPlayerLevel 差分検知が担うため、ここではカットシーンのみ処理する
    function consumePendingEvents(state) {
      if (!Array.isArray(state.pending_events) || state.pending_events.length === 0) return;
      for (const ev of state.pending_events) {
        if (ev && ev.type === "cutscene" && cutsceneDirector &&
            Array.isArray(ev.sequence) && ev.sequence.length > 0) {
          cutsceneDirector.play(ev.sequence);
        }
      }
    }
    setInterval(fetchState, 300);
    fetchState();

    async function sendAction(actionName, payload = {}) {
      // T18 案5: タイトル画面/オープニング表示中はゲーム入力を無効化する
      if (window.__narouTitleActive) return;
      try {
        const res = await fetch("/api/action", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: actionName, ...payload })
        });
        if (res.ok) {
          gameState = await res.json();
          updateUI(gameState);
          SoundEngine.playSE("hit");
        }
      } catch (err) {
        console.error("Action dispatch failed:", err);
      }
    }

    // ==================== UI UPDATE ====================
    function updateUI(state) {
      if (!state || !state.player) return;
      const p = state.player;
      const pet = state.pet;

      // Header Chips
      document.getElementById("chipFloor").innerText = `階層: B${state.dungeon_level || 1}F`;
      document.getElementById("chipGold").innerText = `💰 ${p.gold} G`;
      document.getElementById("chipPlatinum").innerText = `💎 ${p.platinum} P`;
      document.getElementById("chipKarma").innerText = `⚖️ 善悪: ${p.karma}`;

      // Player Vitals
      document.getElementById("hudPlayerName").innerText = `${p.name} (Lv.${p.level} ${p.job})`;
      const hpPct = Math.max(0, Math.min(100, (p.hp / p.max_hp) * 100));
      document.getElementById("barHP").style.width = `${hpPct}%`;
      document.getElementById("valHP").innerText = `${p.hp}/${p.max_hp}`;

      const mpPct = Math.max(0, Math.min(100, (p.mp / p.max_mp) * 100));
      document.getElementById("barMP").style.width = `${mpPct}%`;
      document.getElementById("valMP").innerText = `${p.mp}/${p.max_mp}`;

      const hungerPct = Math.max(0, Math.min(100, (p.hunger / 2000) * 100));
      document.getElementById("barHunger").style.width = `${hungerPct}%`;
      document.getElementById("valHunger").innerText = p.hunger > 1500 ? "満腹" : p.hunger > 800 ? "普通" : "空腹";

      // Pet Vitals
      if (pet && pet.name) {
        document.getElementById("hudPetName").innerText = `妹分『${pet.name}』`;
        const petHpPct = Math.max(0, Math.min(100, (pet.hp / pet.max_hp) * 100));
        document.getElementById("barPetHP").style.width = `${petHpPct}%`;
        document.getElementById("valPetHP").innerText = `${pet.hp}/${pet.max_hp}`;
        document.getElementById("valPetTactic").innerText = `指示: ${pet.tactic || 'バランス'}`;
      }

      // Inventory List (品質をレアリティ色クラスにマッピング)
      const invContainer = document.getElementById("inventoryList");
      const rarityByQuality = { bad: 'common', normal: 'uncommon', good: 'rare', miracle: 'epic', god: 'legendary' };
      if (state.inventory && state.inventory.length > 0) {
        invContainer.innerHTML = state.inventory.map(item => {
          const rarity = rarityByQuality[item.quality] ?? 'common';
          return `
            <div class="item-entry ${item.equipped ? 'equipped' : ''} rarity-${rarity}">
              <span class="font-main ${rarity}">${item.char} ${item.name}</span>
              <span class="font-caption" style="color: var(--color-text-muted);">${item.weight}s</span>
            </div>
          `;
        }).join("");
      } else {
        invContainer.innerHTML = `<div style="color: var(--text-muted); text-align: center;">荷物は空です</div>`;
      }

      // Stats Tab
      if (p.attributes) {
        const statsEl = document.getElementById("statsContent");
        statsEl.innerHTML = `
          <div>腕力 (STR): <b>${p.attributes.str}</b></div>
          <div>耐久 (END): <b>${p.attributes.end}</b></div>
          <div>器用 (DEX): <b>${p.attributes.dex}</b></div>
          <div>感覚 (PER): <b>${p.attributes.per}</b></div>
          <div>習得 (LER): <b>${p.attributes.ler}</b></div>
          <div>意志 (WIL): <b>${p.attributes.wil}</b></div>
          <div>魔力 (MAG): <b>${p.attributes.mag}</b></div>
          <div>魅力 (CHA): <b>${p.attributes.cha}</b></div>
          <div style="grid-column: span 2; margin-top: 6px; color: #ffd700;">信仰: ${p.god} (信仰度: ${p.piety})</div>
        `;
      }

      // Quests Tab
      const questEl = document.getElementById("questList");
      if (state.quests && state.quests.length > 0) {
        questEl.innerHTML = state.quests.map(q => `
          <div class="item-entry" style="${q.completed ? 'opacity: 0.6;' : ''}">
            <div>
              <div style="font-weight: 600;">${q.title}</div>
              <div style="font-size: 0.7rem; color: var(--text-muted);">${q.target}: ${q.current}/${q.needed}</div>
            </div>
            <div style="color: #ffd700;">+${q.reward_gold}G</div>
          </div>
        `).join("");
      } else {
        questEl.innerHTML = `<div style="color: var(--text-muted); text-align: center;">受領中の依頼はありません</div>`;
      }

      // Logs
      const logContainer = document.getElementById("logContainer");
      if (state.logs) {
        logContainer.innerHTML = state.logs.map(log => `
          <div class="log-entry ${log.level || 'INFO'} font-mono">${log.text}</div>
        `).join("");
      }
    }

    function switchTab(tabId) {
      document.querySelectorAll(".tab-content").forEach(el => {
        el.style.display = "none";
        el.classList.remove("spring-anim");
      });
      document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));
      const targetEl = document.getElementById(tabId);
      if (targetEl) {
        targetEl.style.display = "block";
        targetEl.classList.add("spring-anim");
      }
      if (window.event && window.event.target) {
        window.event.target.classList.add("active");
      }
    }

    // ==================== KEYBOARD CONTROLS ====================
    window.addEventListener("keydown", (e) => {
      // T11 案8: Mキーでワールドマップオーバーレイ / Escで閉じる
      if (worldMapOverlay) {
        if (e.code === "KeyM") { e.preventDefault(); worldMapOverlay.toggle(); return; }
        if (e.code === "Escape" && worldMapOverlay.isOpen()) { worldMapOverlay.close(); return; }
      }
      const keyMap = {
        "ArrowUp": "up", "KeyW": "up", "Numpad8": "up",
        "ArrowDown": "down", "KeyS": "down", "Numpad2": "down",
        "ArrowLeft": "left", "KeyA": "left", "Numpad4": "left",
        "ArrowRight": "right", "KeyD": "right", "Numpad6": "right",
        "Numpad7": "up_left", "Numpad9": "up_right",
        "Numpad1": "down_left", "Numpad3": "down_right",
        "Space": "wait", "Numpad5": "wait",
        "KeyG": "pickup",
        "KeyF": "cast_fireball",
        "KeyQ": "use_potion",
        "KeyP": "pray"
      };

      if (keyMap[e.code]) {
        e.preventDefault();
        sendAction(keyMap[e.code]);
      }
    });
    });

    // ==================== THEME MANAGER ====================
    // Persists the selected visual theme (dark / light / high-contrast /
    // colorblind / sepia) and applies it via <html data-theme="...">.
    const ThemeManager = (() => {
      const STORAGE_KEY = 'narou-theme';
      const VALID = ['dark', 'light', 'high-contrast', 'colorblind', 'sepia'];
      const root = document.documentElement;

      function current() {
        return root.dataset.theme || 'dark';
      }

      function apply(theme) {
        if (!VALID.includes(theme)) theme = 'dark';
        root.dataset.theme = theme;
        try { localStorage.setItem(STORAGE_KEY, theme); } catch (e) {}
        document.querySelectorAll('#themeSwitch button').forEach((btn) => {
          const active = btn.dataset.themeValue === theme;
          btn.setAttribute('aria-pressed', active ? 'true' : 'false');
        });
      }

      function init() {
        let saved = 'dark';
        try { saved = localStorage.getItem(STORAGE_KEY) || 'dark'; } catch (e) {}
        apply(saved);
        const sw = document.getElementById('themeSwitch');
        if (sw) {
          sw.addEventListener('click', (e) => {
            const btn = e.target.closest('button[data-theme-value]');
            if (btn) apply(btn.dataset.themeValue);
          });
        }
      }

      return { apply, current, init };
    })();
    ThemeManager.init();
  