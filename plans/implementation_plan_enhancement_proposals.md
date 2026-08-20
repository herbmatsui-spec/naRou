# 実装計画書の完成度向上のための9つの提案

既に作成された各システムの実装計画書（タイトルシステム、スキルツリージョブシステム、ギルド派閥ランキングシステム、ペット契約進化融合システム、実績トロフィーシステム、輪廻転生システム、スキル合成進化システム、ダンジョンワールドストーリーテラー）について、さらに完成度を高くするための具体的な改善提案を9つ提示します。

## 1. エラーハンドリングとロギングの標準化
### 提案内容
各システムの実装計画に、統一されたエラーハンドリングパターンとロギングメカニズムを組み込む。

### 具体的改善点
- すべてのYAML読み込み関数に、`FileNotFoundError`, `YAMLError`, `KeyError` などの具体例外を捕捉し、適切なフォールバックまたはエラーメッセージを出力
- ロガーのインジェクションパターンを統一し、`logging.getLogger(__name__)` を使用した構造化ログ出力
- エラーレベル別に分類（DEBUG, INFO, WARNING, ERROR, CRITICAL）し、設定ファイルでログレベルを調整可能にする
- 重要な操作（セーブ/ロード、データ変更など）には必ずログ出力を追加

### 実装例
```python
import logging

logger = logging.getLogger(__name__)


def load_yaml_safe(filepath: str, default=None):
    try:
        with open(filepath, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning(f"YAML file not found: {filepath}. Using default.")
        return default or {}
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error in {filepath}: {e}")
        return default or {}
```

### 期待効果
- デバッグ容易性の向上
- 予期しない入力やファイル欠如時のクラッシュ防止
- 運用時の問題特定が容易になる

## 2. 単体テストと統合テストの組み込み
### 提案内容
各実装ステップに、対応する単体テストケースの作成を含め、継続的インテグレーションの基盤を作る。

### 具体的改善点
- 各システムごとに `tests/` ディレクトリ下にテストファイルを作成（例: `tests/test_title_system.py`）
- 基本的な機能（データロード、条件チェック、状態変更など）に対するアサーションを書く
- フィクスチャーを使用して共通のテストセットアップを作る
- エッジケース（境界値、異常入力）もテスト対象に含める
- CI/CD パイプラインでのテスト自動実行を想定した構造

### 実装例（タイトルシステムのテスト）
```python
import pytest
from title_system import TitleRegistry, TitleManager
from entity import Entity


def test_title_loading():
    registry = TitleRegistry()
    registry.load("data/titles.yaml")
    assert len(registry.all()) > 0
    assert "goblin_slayer" in registry.all()


def test_title_condition_check():
    player = Entity()
    player.kill_counts = {"goblin": 15}
    registry = TitleRegistry()
    registry.load("data/titles.yaml")
    title_data = registry.get("goblin_slayer")
    manager = TitleManager()
    assert manager.check_condition(player, title_data.condition) == True
```

### 期待効果
- リグレッション防止
- リファクタリング時の安全性向上
- 新規開発者のオンボーディングが容易になる

## 3. 設定可能なバランシングパラメータの外部化
### 提案内容
ハードコードされた数値や閾値をすべてYAML設定ファイルに移動し、ゲームバランス調整をプログラム変更不要で可能にする。

### 具体的改善点
- すべての「マジックナンバー」を `data/game_balance.yaml` などの中央設定ファイルに移動
- タイトル取得条件の数値、スキルポイント必要量、イベント発生確率などを外部化
- 設定ファイルにはコメントとデフォルト値、推奨範囲を記述
- 設定変更時のホットリロード機能を開発時用に実装（オプション）

### 実装例
```yaml
# data/game_balance.yaml
title_requirements:
  goblin_slayer:
    kill_count: 15  # 変更可能：初期値15
    time_limit_days: null  # null=無制限
  dragon_slayer:
    kill_count: 3
    required_items: ["dragon_slayer_sword"]

skill_points:
  level_up_base: 10
  level_up_per_level: 2
  max_per_level: 20

event_probabilities:
  blood_moon: 0.05  # 5% annual chance
  harvest_festival: 1.0  # 100% yearly
```

### 期待効果
- ゲームデザイナーがプログラマー介入なくバランス調整可能
- プレイテスト後の迅速な調整が可能になる
- モッドコミュニティへの提供が容易になる

## 4. パフォーマンス最適化とプロファイリングフック
### 提案内容
実装計画にパフォーマンス考慮事項とプロファイリングのためのフックを組み込む。

### 具体的改善点
- 高頻度呼び出しされる関数（フレームごとのチェックなど）に対して計測フラグを追加
- オプションでプロファイリングデータをファイルに出力する機能
- アルゴリズム計算量の見直し（O(n²) → O(n log n) などの改善余地を指摘）
- キャッシュ戦略の導入検討（頻繁にアクセスするデータのキャッシュ）
- 不要なオブジェクト生成の削減とオブジェクトプールの検討

### 実装例
```python
import time
from functools import wraps

def profile_if_enabled(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if getattr(wrapper, 'profiling_enabled', False):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            logger.debug(f"{func.__name__} took {end-start:.4f}s")
            return result
        return func(*args, **kwargs)
    return wrapper

# 使用例
@profile_if_enabled
def check_all_titles(self, player: 'Entity') -> List[str]:
    # 実装...
```

### 期待効果
- パフォーマンスボトルネックの早期発見
- 最適化の優先順位付けが容易になる
- 将来のスケーラビリティ向上のための基盤作り

## 5. 拡張性とプラグインアーキテクチャの考慮
### 提案内容
将来的な拡張やMODサポートを視野に入れた、プラグイン可能なアーキテクチャ設計を提案。

### 具体的改善点
- 各システムのコアロジックをインターフェイスまたは抽象基底クラスで定義
- 追加機能はプラグインとして別ファイルで実装し、ローダーで動的に読み込む
- YAMLベースの拡張ポイントを提供（カスタム条件、カスタム効果など）
- イベント駆動アーキテクチャをより徹底させ、カスタムイベントの登録可能にする
- MOD開発者向けのドキュメントテンプレートを提供

### 実装例（プラグインローダーの概念）
```python
# plugin_system.py
import importlib
import os


class PluginManager:
    def __init__(self):
        self.plugins = []

    def load_plugins_from_directory(self, directory: str):
        for filename in os.listdir(directory):
            if filename.endswith(".py") and not filename.startswith("_"):
                module_name = filename[:-3]
                module = importlib.import_module(f"{directory}.{module_name}")
                if hasattr(module, "register_plugin"):
                    module.register_plugin(self)
```

### 期待効果
- コアゲームエンジンへの影響を最小限に抑えて機能追加可能
- MODコミュニティの活性化促進
- 長期的な保守性と柔軟性の向上

## 6. クロスプラットフォーム互換性とエンコーディング対応
### 提案内容
異なるオペレーティングシステムや言語環境でも動作するよう、ファイルパス処理とエンコーディングを統一。

### 具体的改善点
- すべてのファイルパス操作に `os.path` または `pathlib.Path` を使用し、OS固有の区切り文字に依存しない
- YAMLファイルの読み書き時に必ず `encoding='utf-8'` を指定
- Windows固有の改行コード（\r\n）とUnix系（\n）の両方を適切に処理
- Unicode文字（絵文字、日本語など）の取り扱いをテスト対象に含める
- 設定ファイルにはBOMなしUTF-8を推奨し、検証スクリプトを提供

### 実装例
```python
from pathlib import Path


def get_data_file_path(filename: str) -> Path:
    return Path("data") / filename


def load_yaml_universal(filepath: Path):
    with filepath.open(encoding="utf-8") as f:
        return yaml.safe_load(f)
```

### 期待効果
- Windows, Linux, macOSでの動作保証
- 国際化（i18n）への移行が容易になる
- ファイル共有時の文字化け問題防止

## 7. ドキュメンテーションとコードコメントの標準化
### 提案内容
実装計画に加えて、実際のコードに対するドキュメンテーション基準を設ける。

### 具体的改善点
- すべての公開クラスとメソッドにGoogleスタイルまたはNumPyスタイルの docstring を付与
- タイプヒントを徹底し、IDEのサポートを最大化
- 複雑なアルゴリズムやビジネスロジックにはインラインコメントで説明を追加
- 公開APIではない内部ヘルパー関数には `_` プレフィックスと簡潔なコメント
- アーキテクチャ決定の理由（なぜこの設計にしたか）を設計ドキュメントに残す
- 例として、各システムの「設計哲学」セクションを追加

### 実装例
```python
class TitleManager:
    """キャラクターの称号状態を管理するクラス。
    
    Attributes:
        registry (TitleRegistry): 称号定義のレジストリ
        _cache (Dict[str, bool]): 条件チェック結果のキャッシュ
        
    Example:
        >>> manager = TitleManager()
        >>> manager.grant_title(player, "goblin_slayer")
        >>> "goblin_slayer" in player.titles
        True
    """
    
    def __init__(self, registry: TitleRegistry):
        """TitleManagerを初期化。
        
        Args:
            registry: 称号データを提供するレジストリインスタンス
        """
        self.registry = registry
        self._cache = {}
    
    def grant_title(self, player: Entity, title_id: str) -> bool:
        """プレイヤーに称号を付与する。
        
        Args:
            player: 称号を付与対象のキャラクター
            title_id: 付与する称号のID
            
        Returns:
            bool: 付与に成功した場合True、すでに所持している場合False
            
        Note:
            このメソッドは内部で _apply_title_effects() を呼び出し、
            ステータス変更を適用する。
        """
        # 実装...
```

### 期待効果
- 新規開発者の理解速度向上
- IDEによる自動補完とエラーチェックの向上
- 将来のメンテナンスコスト削減
- 外部ドキュメント生成ツール（Sphinx等）との連携が容易になる

## 8. バージョン管理とスキーマ移行戦略
### 提案内容
データファイル（YAML）のスキーマ変更に対応するためのバージョン管理と移行メカニズムを組み込む。

### 具体的改善点
- すべてのYAMLデータファイルに `schema_version` フィールドを追加
- データローダー時にスキラバージョンをチェックし、必要に応じて移行関数を実行
- 移行関数は累積的に適用可能に設計（v1→v2→v3 の順に適用）
- 移行不可能な変更については明確なエラーメッセージと手動介入ガイドを提供
- セーブデータにも同様のバージョン管理を適用し、下位互換性を維持

### 実装例（スキマバージョン付きYAML）
```yaml
# data/titles.yaml
schema_version: 2
titles:
  goblin_slayer:
    id: goblin_slayer
    name: "ゴブリンスレイヤー"
    # v2から追加されたフィールド
    hidden_until: null  # 特定条件でのみ表示される称号
```

### 実装例（移行ロジック）
```python
def migrate_titles_v1_to_v2(data: dict) -> dict:
    """v1 スキマのタイトルデータを v2 に移行"""
    if data.get("schema_version", 1) >= 2:
        return data  # すでにv2以上

    migrated = data.copy()
    migrated["schema_version"] = 2

    for title_data in migrated.get("titles", {}).values():
        # v1には hidden_until がなかったのでデフォルト値を設定
        if "hidden_until" not in title_data:
            title_data["hidden_until"] = None

    return migrated


# ローダーでの使用例
def load_with_migration(filepath: str, migration_funcs: List[Callable]) -> dict:
    raw_data = load_yaml_safe(filepath)
    current_version = raw_data.get("schema_version", 1)

    for version, func in enumerate(migration_funcs, start=2):
        if current_version < version:
            raw_data = func(raw_data)

    return raw_data
```

### 期待効果
- データフォーマットの進化に柔軟に対応可能
- アップデート時のセーブデータ互換性問題を防止
- 長期運用におけるデータ保守性の向上
- モッド作成者にも明確なアップグレードパスを提供

## 9. ユーザビリティとアクセシビリティへの配慮
### 提案内容
ゲーム内UIとプレイヤー体験において、アクセシビリティと使いやすさを考慮した設計を組み込む。

### 具体的改善点
- 色覚多様性への配慮：色のみに依存しない表示方法（アイコン＋テキスト、パターン違いなど）
- フォントサイズ調整可能オプションの検討
- キーボードナビゲーションの完全サポート（マウス不要での全操作可能）
- スクリーンリーダー対応のための適切な ARIA ラベル相当の仕組み
- ツールチップとヘルプシステムの統一設計
- ゲームスピード調整オプション（アクション間隔、メッセージ表示時間など）
- 認知的負荷軽減のための情報段階的開示（重要情報は即座に表示、詳細はオプションで表示）

### 実装例（UI要素のアクセシビリティ考慮）
```yaml
# data/story_ui.yaml
accessibility_options:
  color_blind_mode:
    enabled: false
    alternative_indicators: ["shape", "pattern", "text_label"]
  font_size:
    small: 12
    medium: 16  # デフォルト
    large: 20
    extra_large: 24
  screen_reader_support:
    enabled: true
    describe_images: true
    announce_changes: "polite"  # assertive, polite, off
```

### 実装例（色覚考慮の表示ロジック）
```python
def get_title_display_color(title_id: str, is_equipped: bool) -> Tuple[int, int, int]:
    """色覚多様性に配慮した表示色を返す。
    
    色だけでなく、境界線の太さやアイコンの形状でも区別できるようにする。
    """
    base_color = TITLE_COLORS.get(title_id, (255, 255, 255))
    
    if is_equipped:
        # equipped 状態では境界線を太くする（色以外での区別）
        return base_color, 3  # (color, border_width)
    else:
        return base_color, 1
```

### 期待効果
- より広いプレイヤーベースへの対応
- ゲームの評価とレビューでのアクセシビリティ得点向上
- 法規制への準拠（一部地域でのアクセシビリティ要件）
- 長期的なプレイヤー満足度とリテンション率向上

## 実装優先度と依存関係
これらの提案は、すでに作成された実装計画書に後から追加することも、新たな実装を開始する際に最初から組み込むことも可能です。

### 推奨導入順序
1. **エラーハンドリングとロギングの標準化** - 早期に導入すると後のデバッグが容易になる
2. **単体テストと統合テストの組み込み** - リグレッション防止のため早めに
3. **設定可能なバランシングパラメータの外部化** - ゲームバランス調整のため中盤で
4. **ドキュメンテーションとコードコメントの標準化** - チーム開発時のために随時
5. **クロスプラットフォーム互換性とエンコーディング対応** - 基礎的だが重要
6. **パフォーマンス最適化とプロファイリングフック** - 最適化は後段階で
7. **拡張性とプラグインアーキテクチャの考慮** - 将来を見据えて中盤から
8. **バージョン管理とスキーマ移行戦略** - データファイルが増えてきたら導入
9. **ユーザビリティとアクセシビリティへの配慮** - UI実装後に最終調整として

これらの9つの提案を実装計画書に組み込むことにより、単なる機能実装レベルを超えて、保守性・拡張性・品質が高いプロフェッショナルレベルのゲームエンジン基盤を構築することができます。