
    (function () {
      var overlay = document.getElementById('title-overlay');
      var btnNew = document.getElementById('btnTitleNew');
      var btnContinue = document.getElementById('btnTitleContinue');
      var started = false;

      // タイトル表示中はゲーム入力 (sendAction) を無効化する
      window.__narouTitleActive = true;

      // オープニングカットシーン: README Phase 0「転落と覚醒 (Betrayal & Awakening)」準拠
      var OPENING_SEQUENCE = [
        { text: "巨大企業都市『バベルタワー』──若きエリート監査官は、上層部の不正を暴こうとしていた。", background: "#0b0d1c", duration: 3600 },
        { text: "だが待ち受けていたのは罠。権限を永久剥奪され、深度700mの廃棄スラム街へと投棄される。", background: "#151019", duration: 3600 },
        { text: "暗黒の底で、最底辺の廃棄スキル《基礎解析》が目覚める。解析し、暴き、生き延びよ。", background: "#1c1206", duration: 3600 },
        { text: "──追捕犬の包囲網を潜り抜け、生存のための逃走劇が今、始まる。", background: "#000000", duration: 3200 }
      ];

      function dismissTitle() {
        if (started) return;
        started = true;
        window.__narouTitleActive = false;
        overlay.style.opacity = '0';
        setTimeout(function () { overlay.style.display = 'none'; }, 820);
      }

      function playOpening() {
        // 既存 CutsceneDirector (demos/lib/CutsceneDirector.js) を利用
        var Director = window.CutsceneDirector;
        if (!Director) {
          console.warn('CutsceneDirector が未読込のためオープニングをスキップします');
          return Promise.resolve();
        }
        var director = new Director({ fadeMs: 700, autoAdvanceMs: 3600 });
        return director.play(OPENING_SEQUENCE);
      }

      // はじめから: フェードアウト → オープニングカットシーン → ゲーム開始
      btnNew.addEventListener('click', function () {
        dismissTitle();
        setTimeout(playOpening, 820);
      });

      // 続きから: タイトルから直接ゲームへ復帰 (カットシーンなし)
      btnContinue.addEventListener('click', dismissTitle);

      // 続きからボタンの有効化判定: 既存のセーブ読み込みAPIは未整備のため、
      // 進行中セッション (/api/state に player が存在) を取得できたら「復帰可能」とみなす。
      // 取得できない (バックエンド未起動/プレイヤー未生成) 場合はボタンを無効化したままにする。
      fetch('/api/state')
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (state) {
          if (state && state.player && !state.error) {
            btnContinue.disabled = false;
            btnContinue.style.color = '#ffd700';
            btnContinue.style.borderColor = '#ffd700';
            btnContinue.style.cursor = 'pointer';
            btnContinue.title = '前回の冒険から再開する';
          }
        })
        .catch(function () { /* 無効のまま */ });
    })();
  