/**
 * スクリーンシェイクシステム
 * ダメージや爆発などの効果で画面を振動させる
 */
export class ScreenShake {
    /**
     * @param {PIXI.Container} targetContainer - シェイク対象のコンテナ
     * @param {number} intensity - シェイクの強度（ピクセル）
     * @param {number} duration - シェイクの持続時間（秒）
     */
    constructor(targetContainer, intensity = 5, duration = 0.5) {
        this.targetContainer = targetContainer;
        this.intensity = intensity;
        this.duration = duration;

        // シェイク状態
        this.isShaking = false;
        this.shakeTime = 0;
        this.shakeIntensity = 0;
        this.originalPosition = { x: 0, y: 0 };

        // 減衰パターン
        this.decayPattern = 'exponential'; // 'linear', 'exponential', 'smooth'

        // ノイズ生成用
        this.seed = Math.random() * 1000;
    }

    /**
     * シェイクを開始
     * @param {number} intensity - オプション：強度を上書き
     * @param {number} duration - オプション：持続時間を上書き
     */
    start(intensity, duration) {
        this.shakeIntensity = intensity !== undefined ? intensity : this.intensity;
        this.shakeDuration = duration !== undefined ? duration : this.duration;
        this.shakeTime = this.shakeDuration;
        this.isShaking = true;

        // 元の位置を保存
        this.originalPosition = {
            x: this.targetContainer.x,
            y: this.targetContainer.y
        };

        // ノイズシードをリセット
        this.seed = Math.random() * 1000;
    }

    /**
     * シェイクを停止
     */
    stop() {
        this.isShaking = false;
        this.shakeTime = 0;

        // 元の位置に戻す
        this.targetContainer.x = this.originalPosition.x;
        this.targetContainer.y = this.originalPosition.y;
    }

    /**
     * シェイクを更新
     * @param {number} deltaTime - 経過時間（秒）
     */
    update(deltaTime) {
        if (!this.isShaking) return;

        this.shakeTime -= deltaTime;

        if (this.shakeTime <= 0) {
            this.stop();
            return;
        }

        // 経過時間の割合（0.0 - 1.0）
        const elapsed = 1.0 - (this.shakeTime / this.shakeDuration);

        // 減衰計算
        let decay;
        switch (this.decayPattern) {
            case 'linear':
                decay = 1.0 - elapsed;
                break;
            case 'exponential':
                decay = Math.exp(-elapsed * 4);
                break;
            case 'smooth':
            default:
                decay = Math.cos(elapsed * Math.PI / 2);
                break;
        }

        // 現在の強度
        const currentIntensity = this.shakeIntensity * decay;

        // ノイズオフセットを生成
        const offsetX = this._noise(this.seed) * currentIntensity * 2 - currentIntensity;
        const offsetY = this._noise(this.seed + 1) * currentIntensity * 2 - currentIntensity;

        // 位置を適用
        this.targetContainer.x = this.originalPosition.x + offsetX;
        this.targetContainer.y = this.originalPosition.y + offsetY;

        // シードを更新（次フレームのノイズを変える）
        this.seed += 0.1;
    }

    /**
     * 疑似ノイズ関数
     * @param {number} x - 入力値
     * @returns {number} 0.0 - 1.0 のノイズ値
     */
    _noise(x) {
        const n = Math.sin(x * 12.9898 + 78.233) * 43758.5453;
        return n - Math.floor(n);
    }

    /**
     * プリセットシェイクを実行
     * @param {string} preset - プリセット名 ('light', 'medium', 'heavy', 'explosion')
     */
    shake(preset) {
        const presets = {
            'light': { intensity: 2, duration: 0.2 },
            'medium': { intensity: 5, duration: 0.4 },
            'heavy': { intensity: 10, duration: 0.6 },
            'explosion': { intensity: 15, duration: 0.8 }
        };

        const config = presets[preset] || presets['medium'];
        this.start(config.intensity, config.duration);
    }

    /**
     * 減衰パターンを設定
     * @param {string} pattern - 減衰パターン ('linear', 'exponential', 'smooth')
     */
    setDecayPattern(pattern) {
        this.decayPattern = pattern;
    }

    /**
     * デフォルト強度を設定
     * @param {number} intensity - 強度（ピクセル）
     */
    setIntensity(intensity) {
        this.intensity = intensity;
    }

    /**
     * デフォルト持続時間を設定
     * @param {number} duration - 持続時間（秒）
     */
    setDuration(duration) {
        this.duration = duration;
    }

    /**
     * シェイク中かどうか
     * @returns {boolean} シェイク中フラグ
     */
    getIsShaking() {
        return this.isShaking;
    }

    /**
     * シェイクの残り時間
     * @returns {number} 残り時間（秒）
     */
    getRemainingTime() {
        return this.isShaking ? this.shakeTime : 0;
    }
}

// グローバルスコープにもエクスポート（後方互換性のため）
window.ScreenShake = ScreenShake;
