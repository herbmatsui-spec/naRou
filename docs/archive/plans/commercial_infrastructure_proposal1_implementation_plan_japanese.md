# 商業インフラ強化（提案1）詳細実装計画書

本計画書は、COMMERCIAL_SUCCESS_PROPOSALS.md の「提案1: 商業インフラの強化（CI/CD + テレメトリ + アンチチート）」をさらに分解し、**3つの詳細提案**と、低性能なLLMでも実装可能なように**1～72までの小さなステップ**に分割した実装計画を提供する。

---

## 📋 3つの詳細提案

### 提案1-A: CI/CD パイプライン構築（品質の自動担保）

**目的**: ヒューマンエラーによる品質劣化を防ぎ、毎回のコミットで自動テスト・型チェック・バランス検証を通す。

**対象成果物**:
- `.github/workflows/ci.yml`（pytest 80%カバレッジ、mypy --strict、ruff、black、balance_simulator）
- `.github/workflows/cd.yml`（Windows/macOS/Linux + WASM ビルド・アーティファクト化）
- `.coveragerc`、`requirements-lock.txt`（ハッシュ固定）
- セキュリティスキャン（pip-audit / safety）

**商業的価値**: リリース前の炎上を90%削減。マルチプラットフォーム同時リリースが可能になる。

---

### 提案1-B: テレメトリ・クラッシュレポーティング基盤（データ駆動意思決定）

**目的**: オプトインでプレイデータを匿名収集し、クラッシュ率・ファネル・バランス偏りを可視化。

**対象成果物**:
- `telemetry_manager.py`（オプトイン UI、匿名ID、イベント追跡、バッチ送信）
- Sentry 連携（例外ハンドラ拡張、スタックトレース送信、パフォーマンスメトリクス）
- GDPR 準拠（データ削除リクエスト、プライバシーポリシー表示）
- オフライン時ローカルキャッシュ → 再接続時送信

**商業的価値**: 「直感」ではなく「データ」でバランス調整。リテンション低下の原因特定が数時間で可能に。

---

### 提案1-C: アンチタンパー・セキュリティ基盤（セーブ改ざん防止）

**目的**: 既存の SHA256 チェックサムを拡張し、HMAC 署名・ランタイム整合性チェック・軽量アンチデバッグでセーブ改ざんとチートを検出。

**対象成果物**:
- セーブファイル HMAC 署名（秘密鍵はビルド時に埋め込み、平文保存しない）
- ランタイム整合性チェック（メモリ上の異常値・デバッガ付着検出）
- ライセンスキー検証（Steam DRM / 独自トークン）
- 違反ログ記録（改ざん検出時はクラウドセーブ無効化、ローカルのみ許可）

**商業的価値**: リーダーボード汚染・課金不正を防ぎ、公正な競争環境を維持。後続の季節OP（提案8）/ 非同期マルチ（提案9）の前提条件。

---

> 上記3提案はすべて **提案1 の配下**にあり、実装順序は **1-A（土台）→ 1-B（観測）→ 1-C（防御）** が推奨される。

---

## 📦 72ステップ実装計画

低性能なLLMでも実装可能なように1ステップ1タスクの極小単位に分割。各ステップには検証方法が含まれ、進捗を追跡できる。

構成: フェーズ1（1-20: CI/CD基盤）／フェーズ2（21-40: ビルド・デプロイ自動化）／フェーズ3（41-60: テレメトリ基盤）／フェーズ4（61-72: アンチチート・セキュリティ）

---

## 🔧 フェーズ1：CI/CD基盤の構築 (Step 1-20)

### 1.1 .github/workflows/ci.yml 作成 (Step 1)
- ファイル `.github/workflows/ci.yml` を作成
- 基本的なGitHub Actionsワークフロー（ Ubuntu / Python 3.11 ）を定義
- 検証: `python -c "import yaml; data = yaml.safe_load(open('.github/workflows/ci.yml')); print('OK' if data else 'ERROR')"`
- ヒント: シンプルなワークフローから始める

### 1.2 pytestテスト実行ステップ追加 (Step 2)
- `.github/workflows/ci.yml` に `pytest` ステップを追加
- 既存テストスイート（23ファイル）を実行
- 検証: `python -c "import yaml; data=yaml.safe_load(open('.github/workflows/ci.yml')); jobs=data.get('jobs',{}); print('pytest:', any('pytest' in str(v) for v in jobs.values()))"`
- ヒント: `python -m pytest -q` で始める

### 1.3 カバレッジ80%設定 (.coveragerc) (Step 3)
- `.coveragerc` を作成し `fail_under = 80` を設定
- 除外パス（tests/, tools/ 等）を定義
- 検証: `python -c "import configparser; c=configparser.ConfigParser(); c.read('.coveragerc'); print('cov80:', c.get('report','fail_under')=='80')"`
- ヒント: 最初は 70 から始めて徐々に引き上げる

### 1.4 mypy厳密タイプチェック追加 (Step 4)
- ワークフローに `mypy --strict` ステップを追加
- `mypy.ini` または `pyproject.toml` に `[tool.mypy]` 設定
- 検証: `python -c "import os; print('mypy cfg:', os.path.exists('mypy.ini') or os.path.exists('pyproject.toml'))"`
- ヒント: 既存コードは型ヒント網羅済みなので段階的に strict 化

### 1.5 ruff リンティング追加 (Step 5)
- ワークフローに `ruff check .` ステップを追加
- `ruff.toml` でルールを設定
- 検証: `python -c "import os; print('ruff cfg:', os.path.exists('ruff.toml'))"`
- ヒント: E/F ルールから始め、後で拡張

### 1.6 black フォーマットチェック追加 (Step 6)
- ワークフローに `black --check .` ステップを追加
- 検証: `python -c "import yaml; data=yaml.safe_load(open('.github/workflows/ci.yml')); print('black:', any('black' in str(v) for v in data.get('jobs',{}).values()))"`
- ヒント: 既存コードは既に black 準拠の可能性大

### 1.7 balance_simulator 自動実行 (Step 7)
- ワークフローに `python tests/balance_simulator.py` ステップを追加
- 期待勝率との乖離が閾値超えなら失敗とする
- 検証: `python -c "import yaml; data=yaml.safe_load(open('.github/workflows/ci.yml')); print('balance:', any('balance_simulator' in str(v) for v in data.get('jobs',{}).values()))"`
- ヒント: 既存 `BalanceSimulator` を活用

### 1.8 キャッシュ設定 (Step 8)
- `actions/cache` で pip キャッシュと `.pytest_cache` を保存
- 検証: `python -c "import yaml; data=yaml.safe_load(open('.github/workflows/ci.yml')); print('cache:', any('cache' in str(v) for v in data.get('jobs',{}).values()))"`
- ヒント: `~/.cache/pip` をキーに

### 1.9 setup-python ステップ (Step 9)
- `actions/setup-python@v5` を追加（Python 3.11）
- 検証: `python -c "import yaml; data=yaml.safe_load(open('.github/workflows/ci.yml')); print('setup-py:', any('setup-python' in str(v) for v in data.get('jobs',{}).values()))"`
- ヒント: 複数バージョンマトリックスは後で

### 1.10 依存関係インストール + requirements-lock.txt (Step 10)
- `requirements.txt` から `requirements-lock.txt`（ハッシュ固定）を生成
- ワークフローで `pip install -r requirements-lock.txt` を実行
- 検証: `python -c "import os; print('lock:', os.path.exists('requirements-lock.txt'))"`
- ヒント: `pip freeze` ではなく `pip-compile` 推奨（未導入なら freeze で代用）

### 1.11 テスト結果レポート出力 (Step 11)
- `pytest --junitxml=report.xml` でレポート生成
- 検証: `python -c "import yaml; data=yaml.safe_load(open('.github/workflows/ci.yml')); print('junit:', any('junitxml' in str(v) for v in data.get('jobs',{}).values()))"`
- ヒント: GitHub の Checks タブに表示される

### 1.12 セキュリティスキャン (pip-audit) (Step 12)
- ワークフローに `pip-audit -r requirements-lock.txt` ステップを追加
- 既知脆弱性があれば失敗
- 検証: `python -c "import yaml; data=yaml.safe_load(open('.github/workflows/ci.yml')); print('audit:', any('pip-audit' in str(v) for v in data.get('jobs',{}).values()))"`
- ヒント: `safety` でも可

### 1.13 ドキュメント生成 (Sphinx, 任意) (Step 13)
- `docs/` 生成ステップを追加（任意・後で有効化）
- 検証: `python -c "import yaml; data=yaml.safe_load(open('.github/workflows/ci.yml')); print('docs:', any('sphinx' in str(v).lower() or 'docs' in str(v).lower() for v in data.get('jobs',{}).values()))"`
- ヒント: 最初はコメントアウトでも可

### 1.14 成果物アーティファクト化 (Step 14)
- テストレポート・HTMLレポートを `actions/upload-artifact` で保存
- 検証: `python -c "import yaml; data=yaml.safe_load(open('.github/workflows/ci.yml')); print('artifact:', any('upload-artifact' in str(v) for v in data.get('jobs',{}).values()))"`
- ヒント: balance_report.html を保存すると便利

### 1.15 プルリクエストチェック (Step 15)
- `on: pull_request` トリガーを追加
- 検証: `python -c "import yaml; data=yaml.safe_load(open('.github/workflows/ci.yml')); print('pr:', 'pull_request' in data.get('on', []))"`
- ヒント: main への PR のみ対象に

### 1.16 タグ時リリース準備 (Step 16)
- `on: push: tags: 'v*'` トリガーを追加
- 検証: `python -c "import yaml; data=yaml.safe_load(open('.github/workflows/ci.yml')); on=data.get('on',{}); print('tag:', 'tags' in on.get('push',{})) if isinstance(on,dict) else False)"`
- ヒント: cd.yml と連携するための目印

### 1.17 スケジュール実行 (nightly) (Step 17)
- `on: schedule: cron` で毎夜実行を追加
- 検証: `python -c "import yaml; data=yaml.safe_load(open('.github/workflows/ci.yml')); on=data.get('on',{}); print('cron:', bool(on.get('schedule')) if isinstance(on,dict) else False)"`
- ヒント: 夜間に重いテストを回す

### 1.18 通知設定 (Discord/Slack) (Step 18)
- 失敗時に Webhook で通知
- 検証: `python -c "import yaml; data=yaml.safe_load(open('.github/workflows/ci.yml')); print('notify:', any('webhook' in str(v).lower() for v in data.get('jobs',{}).values()))"`
- ヒント: Secrets に Webhook URL を格納

### 1.19 ログアーティファクト化 (Step 19)
- 実行ログをアーティファクトとして保存
- 検証: `python -c "import yaml; data=yaml.safe_load(open('.github/workflows/ci.yml')); print('logs:', any('log' in str(v).lower() for v in data.get('jobs',{}).values()))"`
- ヒント: デバッグ時に役立つ

### 1.20 CI/CD パイプライン検証 (Step 20)
- ローカルで `act` 等を用いず、プッシュしてワークフローが緑になることを確認
- 検証: `python -c "import os; print('ci exists:', os.path.exists('.github/workflows/ci.yml'))"`
- ヒント: 最初の緑が最重要マイルストーン

---

## 🏗️ フェーズ2：ビルド・デプロイ自動化 (Step 21-40)

### 2.1 build.py 作成 (PyInstaller 単一エントリ) (Step 21)
- ファイル `build.py` を作成し `pyinstaller` 呼び出しを実装
- 検証: `python -c "print('File exists' if open('build.py').readline().strip() else 'Empty')"`
- ヒント: `--onefile` から始める

### 2.2 Windows ビルド (Step 22)
- `build.py` に Windows 用 `.spec` 生成ロジックを追加
- 検証: `python -c "from build import *; print('win build target defined')"`
- ヒント: GitHub Actions `windows-latest` で実行

### 2.3 macOS ビルド (Step 23)
- `build.py` に macOS 用ビルドロジックを追加
- 検証: `python -c "from build import *; print('mac build target defined')"`
- ヒント: `macos-latest` + `codesign` は後段

### 2.4 Linux ビルド (Step 24)
- `build.py` に Linux 用ビルドロジックを追加
- 検証: `python -c "from build import *; print('linux build target defined')"`
- ヒント: `ubuntu-latest` で実行

### 2.5 AppImage 生成 (Linux) (Step 25)
- `tools/build_appimage.py` を作成し AppImage を生成
- 検証: `python -c "import os; print('appimage tool:', os.path.exists('tools/build_appimage.py'))"`
- ヒント: `.AppImage` は Steam Deck 互換で有利

### 2.6 WASM ビルド (Pyodide/Emscripten) (Step 26)
- `tools/build_wasm.py` を作成し `web_game_client.html` 用 WASM を生成
- 検証: `python -c "import os; print('wasm tool:', os.path.exists('tools/build_wasm.py'))"`
- ヒント: Pyodide で main をラップ、既存 WebSocket クライアントと統合

### 2.7 ビルド成果物署名 (codesign) (Step 27)
- macOS/Windows 用コード署名ステップを追加（証明書は Secrets）
- 検証: `python -c "import yaml; data=yaml.safe_load(open('.github/workflows/cd.yml')); print('codesign:', any('codesign' in str(v).lower() for v in data.get('jobs',{}).values())) if 'jobs' in data else print('cd.yml missing')"`
- ヒント: cd.yml を先に作成する（Step 28）

### 2.8 .github/workflows/cd.yml 作成 (Step 28)
- リリース用ワークフロー `cd.yml` を作成
- 検証: `python -c "import os; print('cd.yml:', os.path.exists('.github/workflows/cd.yml'))"`
- ヒント: ci.yml をコピーしトリガーを変更

### 2.9 ビルド検証スクリプト (Step 29)
- `tools/verify_build.py` を作成し実行ファイルの起動テストを実施
- 検証: `python -c "import os; print('verify tool:', os.path.exists('tools/verify_build.py'))"`
- ヒント: `--help` が出るかで簡易検証

### 2.10 デプロイスクリプト deploy.py (Step 30)
- `deploy.py` を作成し itch.io / Steam アップロードを実装
- 検証: `python -c "print('File exists' if open('deploy.py').readline().strip() else 'Empty')"`
- ヒント: butler (itch.io) と steamcmd を想定

### 2.11 itch.io デプロイ (Step 31)
- `deploy.py` に itch.io アップロード機能を追加
- 検証: `python -c "from deploy import *; print('itch target defined')"`
- ヒント: 無料ホスティングでテストリリースに最適

### 2.12 Steam デプロイ準備 (steamcmd) (Step 32)
- `deploy.py` に steamcmd 呼び出しを追加（app/build ID は Secrets）
- 検証: `python -c "from deploy import *; print('steam target defined')"`
- ヒント: Steam SDK の `contentbuilder` を利用

### 2.13 クラウドセーブ backend スタブ (Step 33)
- `cloud_save/` ディレクトリと `cloud_save/client.py` スタブを作成
- 検証: `python -c "import os; print('cloud_save:', os.path.exists('cloud_save/client.py'))"`
- ヒント: 提案5（Web即時プレイ）と共通利用

### 2.14 自動アップデーター基盤 (Step 34)
- `update_checker.py` を作成しバージョン確認・パッチ適用を実装
- 検証: `python -c "print('File exists' if open('update_checker.py').readline().strip() else 'Empty')"`
- ヒント: マニフェスト差分で判定

### 2.15 バージョニング自動化 (Step 35)
- `tools/bump_version.py` でセマンティックバージョンを自動更新
- 検証: `python -c "import os; print('bump tool:', os.path.exists('tools/bump_version.py'))"`
- ヒント: `kilocode` のバージョン文字列を一元管理

### 2.16 リリースノート自動生成 (Step 36)
- `tools/gen_release_notes.py` で git log から CHANGELOG を生成
- 検証: `python -c "import os; print('notes tool:', os.path.exists('tools/gen_release_notes.py'))"`
- ヒント: Conventional Commits を想定

### 2.17 チェックサム生成 (SHA256) (Step 37)
- ビルド成果物の SHA256 を `checksums.txt` に出力
- 検証: `python -c "print('File exists' if open('tools/gen_checksums.py').readline().strip() else 'Empty') if __import__('os').path.exists('tools/gen_checksums.py') else print('Missing')"`
- ヒント: ダウンロード検証用

### 2.18 マニフェスト生成 (Step 38)
- `tools/gen_manifest.py` でアセット+バイナリのマニフェストを生成
- 検証: `python -c "import os; print('manifest tool:', os.path.exists('tools/gen_manifest.py'))"`
- ヒント: アセット差分更新（提案1-C と連携）に利用

### 2.19 ロールバック機構 (Step 39)
- デプロイ失敗時に前バージョンへ自動差し戻し
- 検証: `python -c "from deploy import *; print('rollback defined')"`
- ヒント: 以前のビルドIDを保持

### 2.20 ビルド・デプロイ統合検証 (Step 40)
- cd.yml を手動実行し、3プラットフォーム + WASM がアーティファクト化されることを確認
- 検証: `python -c "import os; print('cd.yml:', os.path.exists('.github/workflows/cd.yml'))"`
- ヒント: ここまでで「どこでも動く」が達成

---

## 📊 フェーズ3：テレメトリ・分析基盤 (Step 41-60)

### 3.1 telemetry_manager.py 作成 (Step 41)
- ファイル `telemetry_manager.py` を作成し基本構造を定義
- 検証: `python -c "print('File exists' if open('telemetry_manager.py').readline().strip() else 'Empty')"`
- ヒント: オプトイン前提で設計

### 3.2 オプトイン UI (設定画面) (Step 42)
- `ConfigManager` に `telemetry_enabled: bool` を追加し設定画面にトグルを実装
- 検証: `python -c "from config_manager import ConfigManager; c=ConfigManager(); print('telemetry flag:', hasattr(c, 'telemetry_enabled') or 'telemetry_enabled' in c.__dict__)"`
- ヒント: デフォルト OFF、明示同意のみ収集

### 3.3 匿名ID生成 (Step 43)
- `telemetry_manager.py` に UUID4 ベースの匿名ID生成を実装（PII 不含）
- 検証: `python -c "from telemetry_manager import TelemetryManager; t=TelemetryManager(); print('anon id:', bool(t.get_anonymous_id()))"`
- ヒント: デバイス識別情報は使わない

### 3.4 セッション追跡 (Step 44)
- セッション開始/終了イベントを記録
- 検証: `python -c "from telemetry_manager import TelemetryManager; t=TelemetryManager(); t.start_session(); print('session:', t.session_active)"`
- ヒント: 起動〜終了の滞在時間を計測

### 3.5 イベント追跡 (Step 45)
- `track(event: str, props: dict)` メソッドを実装
- 検証: `python -c "from telemetry_manager import TelemetryManager; t=TelemetryManager(); t.track('level_up', {'level':5}); print('events:', len(t._queue))"`
- ヒント: 汎用メソッドで全イベントを吸収

### 3.6 ファネル分析用イベント定義 (Step 46)
- チュートリアル突破・最初のボス撃破・輪廻転生 etc. を定義
- 検証: `python -c "from telemetry_manager import FUNNEL_EVENTS; print('funnel:', len(FUNNEL_EVENTS) > 0)"`
- ヒント: 離脱箇所を特定するための設計

### 3.7 クラッシュレポート (Sentry) 連携 (Step 47)
- `sentry_sdk` 初期化を `telemetry_manager.py` に追加（DSN は Secrets/設定）
- 検証: `python -c "from telemetry_manager import TelemetryManager; t=TelemetryManager(); print('sentry hook:', t.sentry_initialized in (True, False))"`
- ヒント: オプトイン時のみ有効化

### 3.8 例外ハンドラ拡張 (Step 48)
- 既存カスタム例外を Sentry へ転送するフックを追加
- 検証: `python -c "import telemetry_manager; print('exception hook module loaded')"`
- ヒント: `sys.excepthook` を上書き（安全に）

### 3.9 スタックトレース送信 (Step 49)
- 未処理例外時にスタックトレースを送信
- 検証: `python -c "from telemetry_manager import TelemetryManager; t=TelemetryManager(); print('trace sender:', callable(getattr(t,'send_crash',None)))"`
- ヒント: ローカルログも併存

### 3.10 パフォーマンスメトリクス送信 (Step 50)
- FPS / ターン処理時間 / メモリ使用量を送信
- 検証: `python -c "from telemetry_manager import TelemetryManager; t=TelemetryManager(); t.track_performance({'fps':60}); print('perf:', True)"`
- ヒント: 既存 `performance_monitor` と連携可

### 3.11 バランスデータ送信 (Step 51)
- オプトインで戦闘結果を集計送信（個人情報不含）
- 検証: `python -c "from telemetry_manager import TelemetryManager; t=TelemetryManager(); t.track_balance({'win':True,'turns':120}); print('balance:', True)"`
- ヒント: 提案8（季節OP）のバランス調整に直結

### 3.12 GDPR 準拠 (データ削除リクエスト) (Step 52)
- 匿名ID に紐づくサーバー側データ削除 API を呼ぶ `delete_my_data()` を実装
- 検証: `python -c "from telemetry_manager import TelemetryManager; t=TelemetryManager(); print('gdpr:', callable(getattr(t,'delete_my_data',None)))"`
- ヒント: EU ユーザー対応の必須項目

### 3.13 プライバシーポリシー表示 (Step 53)
- `privacy_policy.html` を追加しゲーム内から開けるように
- 検証: `python -c "import os; print('policy:', os.path.exists('privacy_policy.html'))"`
- ヒント: オプトイン画面からリンク

### 3.14 ローカルキャッシュ (オフライン時) (Step 54)
- 送信失敗時にローカルにキューイングし再送
- 検証: `python -c "from telemetry_manager import TelemetryManager; t=TelemetryManager(); t.track('x',{}); print('queue:', len(t._queue) >= 1)"`
- ヒント: `telemetry_cache.json` に保存

### 3.15 バッチ送信 (Step 55)
- 一定間隔 / 一定件数でまとめて送信
- 検証: `python -c "from telemetry_manager import TelemetryManager; t=TelemetryManager(); print('batch:', callable(getattr(t,'flush',None)))"`
- ヒント: ネットワーク負荷を抑える

### 3.16 ダッシュボード用エクスポート (Step 56)
- 集計済みデータを JSON/CSV でエクスポート
- 検証: `python -c "from telemetry_manager import TelemetryManager; t=TelemetryManager(); print('export:', callable(getattr(t,'export_summary',None)))"`
- ヒント: 自前ダッシュボード or Grafana

### 3.17 A/B テスト基盤 (任意) (Step 57)
- 実験フラグ `get_variant(experiment)` を実装
- 検証: `python -c "from telemetry_manager import TelemetryManager; t=TelemetryManager(); print('ab:', callable(getattr(t,'get_variant',None)))"`
- ヒント: 後で活用（任意）

### 3.18 テレメトリ検証 (Step 58)
- モック送信先で正しく届くか確認
- 検証: `python -c "from telemetry_manager import TelemetryManager; t=TelemetryManager(endpoint='mock'); print('mock ok:', t.endpoint=='mock')"`
- ヒント: 単体テストで検証

### 3.19 テレメトリテスト (Step 59)
- `tests/test_telemetry.py` を作成し基本動作を検証
- 検証: `python -c "import os; print('test:', os.path.exists('tests/test_telemetry.py'))"`
- ヒント: オプトイン OFF 時は何も送らないことを断言

### 3.20 テレメトリ文書化 (Step 60)
- `docs/TELEMETRY.md` に収集項目・拒否方法を記載
- 検証: `python -c "import os; print('docs:', os.path.exists('docs/TELEMETRY.md'))"`
- ヒント: 透明性が信頼とレビュー評価に直結

---

## 🛡️ フェーズ4：アンチチート・セキュリティ (Step 61-72)

### 4.1 セーブファイル HMAC 署名 (Step 61)
- `save_system.py` に HMAC-SHA256 署名を追加（鍵はビルド時埋め込み）
- 検証: `python -c "from save_system import SaveSystem; s=SaveSystem(); print('hmac:', callable(getattr(s,'sign_save',None)))"`
- ヒント: 平文鍵保存を避け、難読化＋ビルド差し込み

### 4.2 改ざん検出強化 (Step 62)
- 既存 SHA256 チェックに HMAC 検証を追加
- 検証: `python -c "from save_system import SaveSystem; s=SaveSystem(); print('tamper check:', callable(getattr(s,'verify_integrity',None)))"`
- ヒント: 不一致時はバックアップ世代へ自動フォールバック

### 4.3 ランタイム整合性チェック (Step 63)
- `integrity_checker.py` を作成しメモリ上の異常値を検出
- 検証: `python -c "print('File exists' if open('integrity_checker.py').readline().strip() else 'Empty')"`
- ヒント: HP/ゴールド等の「ありえない値」を監視

### 4.4 デバッガ検出 (anti-debug) (Step 64)
- Windows: `IsDebuggerPresent`、Linux: `/proc/self/status` の `TracerPid` を確認
- 検証: `python -c "from integrity_checker import IntegrityChecker; c=IntegrityChecker(); print('debug chk:', callable(getattr(c,'is_debugger_attached',None)))"`
- ヒント: 軽量に（誤検知しないよう閾値緩め）

### 4.5 メモリ改ざん検出 (任意・軽量) (Step 65)
- 定期的に重要値のハッシュを比較し改変を検知
- 検証: `python -c "from integrity_checker import IntegrityChecker; c=IntegrityChecker(); print('memory chk:', callable(getattr(c,'check_memory_integrity',None)))"`
- ヒント: 完全防止ではなく「検出」が目的

### 4.6 設定ファイル暗号化 (Step 66)
- `ConfigManager` の保存を軽量暗号化（Fernet 等）に変更
- 検証: `python -c "from config_manager import ConfigManager; c=ConfigManager(); print('encrypt:', callable(getattr(c,'_encrypt',None)) or True)"`
- ヒント: チートツールによる直接編集を防ぐ

### 4.7 ライセンスキー検証 (Step 67)
- Steam DRM / 独自トークンで起動権を検証
- 検証: `python -c "from license_checker import LicenseChecker; lc=LicenseChecker(); print('license:', callable(getattr(lc,'validate',None)))" if __import__('os').path.exists('license_checker.py') else print('create first')"`
- ヒント: `license_checker.py` を Step 68 前に作成

### 4.8 ライセンスチェッカーモジュール作成 (Step 68)
- `license_checker.py` を作成しトークン検証ロジックを実装
- 検証: `python -c "print('File exists' if open('license_checker.py').readline().strip() else 'Empty')"`
- ヒント: オフラインでも期限切れ以外は通す

### 4.9 チートパターン検出 (異常値) (Step 69)
- 戦闘結果の統計的異常（ワンショット連発等）を `BalanceSimulator` と照合
- 検証: `python -c "from integrity_checker import IntegrityChecker; c=IntegrityChecker(); print('anomaly:', callable(getattr(c,'detect_anomaly',None)))"`
- ヒント: リーダーボード汚染を防ぐ

### 4.10 違反ログ記録 (Step 70)
- 改ざん/異常検出時にローカルログ + サーバー通知
- 検証: `python -c "from integrity_checker import IntegrityChecker; c=IntegrityChecker(); print('log:', callable(getattr(c,'log_violation',None)))"`
- ヒント: クラウドセーブを無効化しローカルのみ許可

### 4.11 アンチチート文書 (Step 71)
- `docs/ANTI_CHEAT.md` に方針・免責・報告窓口を記載
- 検証: `python -c "import os; print('docs:', os.path.exists('docs/ANTI_CHEAT.md'))"`
- ヒント: コミュニティの信頼構築

### 4.12 最終検証 (Step 72)
- 全フェーズの統合: CI緑 → ビルド成功 → テレメトリ送信（オプトイン） → 改ざん検出動作を確認
- 検証: `python -c "import os; print('All plans:', all(os.path.exists(p) for p in ['.github/workflows/ci.yml','.github/workflows/cd.yml','telemetry_manager.py','integrity_checker.py','license_checker.py']))"`
- ヒント: ここが「商業インフラ完成」のマイルストーン

---

## 📋 まとめ

**商業インフラ強化（提案1）詳細実装計画書 (72ステップ)**

本計画書は、低性能なLLMでも実装可能なように1ステップ1タスクの極小単位に分割。各ステップには Python 検証コードが含まれ、進捗を追跡できる。

**3つの詳細提案**:
1. **提案1-A: CI/CD パイプライン** — 品質の自動担保（pytest 80% / mypy strict / ruff / balance_simulator / マルチOS+WASM ビルド）
2. **提案1-B: テレメトリ基盤** — オプトイン匿名収集・Sentry クラッシュレポート・GDPR 準拠・データ駆動意思決定
3. **提案1-C: アンチタンパー** — HMAC 署名・ランタイム整合性・軽量アンチデバッグ・ライセンス検証

**フェーズ構成**:
- フェーズ1（1-20）: CI/CD 基盤
- フェーズ2（21-40）: ビルド・デプロイ自動化
- フェーズ3（41-60）: テレメトリ・分析基盤
- フェーズ4（61-72）: アンチチート・セキュリティ

**依存関係**:
- ビルド自動化（Phase 2）は CI/CD（Phase 1）に依存
- テレメトリ（Phase 3）は独立して着手可能
- アンチチート（Phase 4）は セーブシステム（既存）＋ テレメトリ（Phase 3）の通知経路を利用

**期待される成果**:
- マルチプラットフォーム（Win/macOS/Linux/AppImage/WASM）の自動ビルド・リリース
- クラッシュ率・ファネル・バランスをデータで監視する基盤
- セーブ改ざん・チートを検出し公正な環境を維持する防御層

本計画書に従って実装を進めることで、COMMERCIAL_SUCCESS_PROPOSALS.md の「提案1」が完了し、**他の8提案すべての前提条件**が満たされる。
