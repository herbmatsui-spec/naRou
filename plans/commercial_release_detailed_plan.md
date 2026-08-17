# 商用化レベル昇華昇華：超詳細実装計画書 (Steps 1-72)

本計画書は、現在の高度なプロトタイプを「商用製品」レベルに引き上げるためのものです。低性能なLLMでも迷わず実装できるよう、1ステップ1タスクの極小単位に分割しています。

---

## 📦 フェーズ1：アーキテクチャの再構築 (Step 1-20)
**目的: God Object (`Engine`) を解体し、保守性と拡張性を商用レベルに引き上げる。**

### 1.1 SystemManager の導入 (Step 1-7)
- [x] Step 1: `systems_manager.py` を新規作成し、`SystemManager` クラスを定義する。
- [x] Step 2: `SystemManager` に `systems: Dict[str, Any]` 辞書を実装し、システムの登録/取得メソッドを作成する。
- [x] Step 3: `game.py` の `Engine.__init__` 内で `SystemManager` をインスタンス化する。
- [x] Step 4: `SkillTreeManager` と `JobManager` を `SystemManager` に登録する。
- [x] Step 5: `GuildManager` と `FactionWarManager` を `SystemManager` に登録する。
- [x] Step 6: `Engine` 内の直接参照を `self.systems_mgr.get("skill_tree_manager")` 形式に段階的に置換する。
- [x] Step 7: `Engine` クラスから不要になった個別のマネージャー変数宣言を削除する。

### 1.2 責任の分離とモジュール化 (Step 8-15)
- [x] Step 8: `Engine` 内の「初期化ロジック」を `Engine.setup_systems()` メソッドに抽出する。
- [x] Step 9: `Engine` 内の「メインループ更新ロジック」を `Engine.update()` メソッドに集約する。
- [x] Step 10: `Engine` 内の「描画呼び出しロジック」を `Engine.render()` メソッドに集約する。
- [x] Step 11: `game.py` の `Engine` クラスから、特定のシステムに依存しすぎているヘルパー関数を各システムクラスへ移動する。
- [x] Step 12: `core_framework.py` に `BaseSystem` 基底クラスを作成し、`initialize()` と `update()` メソッドを定義する。
- [x] Step 13: 各マネージャークラスに `BaseSystem` を継承させる。
- [x] Step 14: `SystemManager` が `BaseSystem` の `initialize()` を一括で呼び出す仕組みを実装する。
- [x] Step 15: `SystemManager` が `BaseSystem` の `update()` を一括で呼び出す仕組みを実装する。

### 1.3 依存関係の整理 (Step 16-20)
- [x] Step 16: 循環参照が発生しているインポートを `TYPE_CHECKING` ブロックに移動する。
- [x] Step 17: `constants.py` に商用レベルのバージョン管理 (`VERSION = "1.0.0"`) を追加する。
- [x] Step 18: `Engine` の `__init__` を整理し、依存関係の注入 (Dependency Injection) 形式に変更する。
- [x] Step 19: `main.py` で `Engine` を生成する際の引数を整理する。
- [x] Step 20: リファクタリング後の `Engine` が正常に起動し、ゲームプレイが可能か検証する。

---

## 💾 フェーズ2：データ永続化の商用化 (Step 21-35)
**目的: `pickle` 依存を脱却し、長期的なデータ互換性とセキュリティを確保する。**

### 2.1 シリアライズ形式の移行準備 (Step 21-27)
- [x] Step 21: `save_system.py` に `to_dict()` メソッドを `Entity` クラスに実装する。
- [x] Step 22: `Item` クラスに `to_dict()` メソッドを実装する。
- [x] Step 23: `Attributes` クラスに `to_dict()` メソッドを実装する。
- [x] Step 24: `SaveSystem` に `serialize_engine_to_dict()` メソッドを実装し、`Engine` 全体を辞書形式に変換する。
- [x] Step 25: `SaveSystem` に `deserialize_dict_to_engine()` メソッドを実装し、辞書から `Engine` を復元する。
- [x] Step 26: `json` モジュールを使用して、辞書データをファイルに書き出す `save_json()` を実装する。
- [x] Step 27: `json` モジュールを使用して、ファイルから辞書を読み込む `load_json()` を実装する。

### 2.2 互換性レイヤーの構築 (Step 28-32)
- [x] Step 28: `save_version` フィールドを JSON データに含める。
- [x] Step 29: `MigrationManager` クラスを新規作成する。
- [x] Step 30: `MigrationManager` に `migrate_v1_to_v2()` のようなバージョン移行関数を定義する。
- [x] Step 31: ロード時に `save_version` をチェックし、必要に応じて `MigrationManager` を通す処理を実装する。
- [x] Step 32: 旧 `pickle` 形式のデータを JSON 形式に変換して保存し直す「コンバーター」を実装する。

### 2.3 セキュリティと検証の強化 (Step 33-35)
- [x] Step 33: JSON 保存時にも SHA256 チェックサムを付与する仕組みを実装する。
- [x] Step 34: セーブデータの暗号化（簡易的な XOR または AES）を検討し、実装する。
- [x] Step 35: JSON 形式でのセーブ/ロードが、既存の `pickle` 形式と同等に動作することを検証する。

---

## ⚖️ フェーズ3：バランス検証の自動化 (Step 36-48)
**目的: 数値的な破綻を排除し、商用ゲームとしての品質基準を設ける。**

### 3.1 シミュレーターの高度化 (Step 36-42)
- [x] Step 36: `tests/balance_simulator.py` に `BattleScenario` クラスを実装する。
- [x] Step 37: シナリオ定義（例：Lv1プレイヤー vs Lv1スライム 100回戦）を YAML で記述可能にする。
- [x] Step 38: `simulate_scenario()` メソッドを実装し、シナリオに基づいた自動戦闘を実行する。
- [x] Step 39: 戦闘中の全ログをキャプチャし、ダメージ分布を解析する機能を実装する。
- [x] Step 40: 「期待される勝率」を定義し、実測値との乖離を検出するアラート機能を実装する。
- [x] Step 41: 複数のスキル組み合わせをランダムに生成し、異常なダメージが出る組み合わせを探索する。
- [x] Step 42: シミュレーション結果を HTML レポートとして出力する機能を実装する。

### 3.2 バランス基準の策定 (Step 43-48)
- [x] Step 43: `data/balance_standards.yaml` を作成し、レベルごとの想定HP/攻撃力の基準値を定義する。
- [x] Step 44: `BalanceChecker` クラスを実装し、YAMLデータが基準値から大きく逸脱していないか検証する。
- [x] Step 45: スキルの「コスト対効果」を数値化し、極端に効率の良いスキルを検出する。
- [x] Step 46: アイテムの価格と性能の相関をチェックし、経済破綻のリスクを検出する。
- [x] Step 47: 転生後のステータス上昇率が指数関数的に増大していないか検証する。
- [x] Step 48: 全ての検証を `pytest` のテストケースとして統合し、一括実行可能にする。

---

## 🎨 フェーズ4：UX/UIの商用レベルへの昇華 (Step 49-62)
**目的: 「操作して心地よい」と感じさせるポリッシュを適用する。**

### 4.1 インターフェースの洗練 (Step 49-55)
- [x] Step 49: `web_game_client.html` の CSS を整理し、モダンなダークテーマのカラーパレットを再定義する。
- [x] Step 50: 全てのボタンにホバー・クリック時のアニメーション（スケール変更、色変化）を統一して適用する。
- [x] Step 51: ログウィンドウに「フィルタ機能」（例：戦闘のみ、システムのみ）を実装する。
- [x] Step 52: 重要な通知（レベルアップ等）に専用の演出アニメーションを実装する。
- [x] Step 53: `GaugeBar` に、変動時の「残像エフェクト」を実装する。
- [x] Step 54: マップ描画の `DynamicLighting` の計算負荷を最適化し、描画ラグをゼロにする。
- [x] Step 55: レスポンシブデザインを強化し、異なる画面解像度でもレイアウトが崩れないようにする。

### 4.2 没入感の演出 (Step 56-62)
- [x] Step 56: `sound_manager.py` に BGM のクロスフェード機能を実装する。
- [x] Step 57: 環境音（アンビエント）のレイヤー再生機能を実装する。
- [x] Step 58: プレイヤーの行動（歩行、攻撃、アイテム使用）に合わせた微細なSEのバリエーションを実装する。
- [x] Step 59: `MessageLog` に、感情表現（絵文字や色使い）を動的に変更する仕組みを導入する。
- [x] Step 60: 画面揺れ (`ScreenShake`) の強度をイベントの重要度に応じて可変にする。
- [x] Step 61: チュートリアルガイドの表示タイミングを、プレイヤーの行動履歴に基づいて最適化する。
- [x] Step 62: 全てのUI要素にツールチップ（ホバー時の説明）を実装する。

---

## 🚀 フェーズ5：最終品質保証とリリース準備 (Step 63-72)
**目的: 致命的なバグをゼロにし、商用リリース可能な状態にする。**

### 5.1 ストレステストと最適化 (Step 63-67)
- [x] Step 63: 100時間相当の高速ターン回しを行い、メモリリークが発生しないか監視する。
- [x] Step 64: 大量のアイテムを所持した状態でのセーブ/ロード時間を計測し、最適化する。
- [x] Step 65: `config_manager.py` のキャッシュ機構を導入し、YAMLロード時間を短縮する。
- [x] Step 66: `tcod` の描画更新頻度を最適化し、CPU使用率を低減する。
- [x] Step 67: ネットワーク遅延を擬似的に発生させ、Webクライアントの挙動が安定しているか検証する。

### 5.2 最終検証とドキュメント (Step 68-72)
- [x] Step 68: 全ての `tests/` 内のテストケースをパスさせる。
- [x] Step 69: `README.md` を商用製品向けに書き換え、インストール・操作ガイドを整備する。
- [x] Step 70: `requirements.txt` のバージョンを固定し、環境再現性を完全に確保する。
- [x] Step 71: 最終的なゲームバランスの微調整を行い、`balance_report.json` で合格を確認する。
- [x] Step 72: 全てのステップが完了したことを確認し、商用リリースビルドを作成する。
