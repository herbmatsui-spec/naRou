
    (function () {
      // URL の ?a11y= を /api/tokens に渡して色覚トークンを上書き (Step 43)
      var params = new URLSearchParams(location.search);
      var a11y = params.get('a11y');
      var tokensUrl = '/api/tokens' + (a11y ? ('?a11y=' + encodeURIComponent(a11y)) : '');
      fetch(tokensUrl)
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data && data.tokens) {
            document.documentElement.style.setProperty('--font-scale', (data.font_scale || 1.0));
          }
        })
        .catch(function () {});

      // チュートリアル手順を取得し、最初の1ステップをオーバーレイ表示 (Step 39)
      fetch('/api/tutorial')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var steps = (data && data.steps) || [];
          if (!steps.length) return;
          var overlay = document.getElementById('tutorial-overlay');
          var textEl = document.getElementById('tutorial-text');
          var nextBtn = document.getElementById('tutorial-next');
          var idx = 0;
          function show() { textEl.textContent = ('チュートリアル ' + (idx + 1) + '/' + steps.length + ': ' + steps[idx].text); }
          show();
          overlay.style.display = 'block';
          nextBtn.addEventListener('click', function () {
            if (idx < steps.length - 1) { idx++; show(); }
            else { overlay.style.display = 'none'; }
          });
        })
        .catch(function () {});
    })();
  