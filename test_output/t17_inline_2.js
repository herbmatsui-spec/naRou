
    (function () {
      // Step 55: WebGPU / WebGL2 / Canvas2D レンダラ選択
      var rendererSelected = "unknown";
      var webgl2Supported = false;
      var webgpuSupported = false;

      // WebGPU 検出
      if ('gpu' in navigator) {
        webgpuSupported = true;
      }

      // WebGL2 検出（簡易テスト）
      try {
        var testCanvas = document.createElement('canvas');
        var gl = testCanvas.getContext('webgl2', { alpha: false, antialias: false });
        webgl2Supported = !!gl;
      } catch (e) { /* ignore */ }

      // Step 56: サーバーに選択レンダラを通知（Fetch API POST）
      function reportRenderer(renderer) {
        rendererSelected = renderer;
        fetch('/api/capabilities', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ selected: renderer })
        }).catch(function () { /* サーバー通信失敗は無視 */ });
        window.__selectedRenderer = renderer; // デバッグ用
      }

      // 初期化時にレンダラ決定と通知
      if (webgpuSupported) {
        reportRenderer('webgpu');
      } else if (webgl2Supported) {
        reportRenderer('webgl2');
      } else {
        reportRenderer('canvas2d');
      }

      // Step 58: タッチイベントハンドラ（移動/待機にマップ）
      var touchStartX = 0, touchStartY = 0;
      var THRESHOLD = 30; // px
      document.addEventListener('touchstart', function (e) {
        if (e.touches.length === 1) {
          var t = e.touches[0];
          touchStartX = t.clientX;
          touchStartY = t.clientY;
        }
      }, { passive: true });
      document.addEventListener('touchend', function (e) {
        if (e.changedTouches.length === 1) {
          var t = e.changedTouches[0];
          var dx = t.clientX - touchStartX;
          var dy = t.clientY - touchStartY;
          if (Math.abs(dx) > THRESHOLD || Math.abs(dy) > THRESHOLD) {
            // スワイプ判定（Step 60）
            if (Math.abs(dx) > Math.abs(dy)) {
              if (dx > 0) { /* 右 */ dispatchKey('d'); }
              else { /* 左 */ dispatchKey('a'); }
            } else {
              if (dy > 0) { /* 下 */ dispatchKey('s'); }
              else { /* 上 */ dispatchKey('w'); }
            }
          } else {
            // タップは待機扱い（Step 58）
            dispatchKey('.');
          }
        }
      }, { passive: true });

      // キーディスパッチヘルパー（既存の key ハンドラへ送信）
      function dispatchKey(key) {
        var evt = new KeyboardEvent('keydown', { key: key });
        document.dispatchEvent(evt);
      }

      // Step 59: D-pad ボタン（タッチ／クリック） -> キー送信
      document.querySelectorAll('#dpad button[data-dir]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var dir = this.getAttribute('data-dir');
          var map = { up: 'w', down: 's', left: 'a', right: 'd', wait: '.' };
          if (map[dir]) { dispatchKey(map[dir]); }
        });
      });

      // Step 61: レスポンシブ対応（CSS で主に対応、必要なら canvas サイズ調整）
      function adjustCanvasSize() {
        var canvas = document.getElementById('gameCanvas');
        if (!canvas) return;
        // 画面幅に応じてスケール（CSS が主だが、必要なら JS でも調整可）
        // ここでは CSS 側で flex 等に任せる
      }
      window.addEventListener('resize', adjustCanvasSize);
      adjustCanvasSize();

      // Step 63: 自動再接続（簡易版：API エラー時にリトライ）
      var apiRetryDelay = 2000; // ms
      function fetchWithRetry(url, opts) {
        return fetch(url, opts).catch(function (err) {
          console.warn('API fetch failed, retrying:', url, err);
          return new Promise(function (resolve) {
            setTimeout(function () {
              resolve(fetchWithRetry(url, opts));
            }, apiRetryDelay);
          });
        });
      }
      // 実際のアプリでは個別 fetch 呼び出しをラップするが、ここではデモとして関数を公開
      window.fetchWithRetry = fetchWithRetry;

      // Step 64: FPS ベースの自動品質低下（簡易実装）
      var fps = 60, frameCount = 0, lastTime = performance.now();
      var qualityReduced = false;
      function updateFPS() {
        var now = performance.now();
        frameCount++;
        if (now - lastTime >= 1000) {
          fps = Math.round((frameCount * 1000) / (now - lastTime));
          frameCount = 0;
          lastTime = now;
          if (fps < 30 && !qualityReduced) {
            // 例：パーティクル数を半分に（実際のゲームでは別途実装要）
            console.warn('Low FPS (' + fps + '): consider reducing quality');
            qualityReduced = true;
          } else if (fps >= 40 && qualityReduced) {
            qualityReduced = false;
          }
        }
      }
      // ゲームループに組み込む想定（ここではタイマーでデモ）
      setInterval(updateFPS, 250);

      // Step 65: ライトモードトグル（簡易：シェーダー系フラグを window に公開）
      window.__liteMode = false;
      window.toggleLiteMode = function () {
        window.__liteMode = !window.__liteMode;
        console.log('Lite mode:', window.__liteMode);
      };

      // Step 57: ローディング画面非表示（リソース読み込み完了時）
      // 実際のゲームではロード完了イベントをここに組み込む
      window.addEventListener('load', function () {
        var loading = document.getElementById('loading-overlay');
        if (loading) { loading.style.display = 'none'; }
      });

    })();
  