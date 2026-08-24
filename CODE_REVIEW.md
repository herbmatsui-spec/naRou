# naRou Roguelike プロジェクト - 包括的コードレビューレポート

## 目次
1. [アーキテクチャ概要と強み](#1-アーキテクチャ概要と強み)
2. [コアシステム詳細レビュー](#2-コアシステム詳細レビュー)
3. [データ管理とスキーマ検証](#3-データ管理とスキーマ検証)
4. [テストカバレッジ分析](#4-テストカバレッジ分析)
5. [定数とマジックナンバー](#5-定数とマジックナンバー)
6. [フロントエンド/デモ実装の整合性](#6-フロントエンドデモ実装の整合性)
7. [スキルシステム詳細レビュー](#7-スキルシステム詳細レビュー)
8. [アイテム生成システム](#8-アイテム生成システム)
9. [ローカライゼーションシステム](#9-ローカライゼーションシステム)
10. [包括的改善提案](#10-包括的改善提案)
11. [総評](#11-総評)

---

## 1. アーキテクチャ概要と強み

### 1.1 全体アーキテクチャ
プロジェクトは **ECS (Entity Component System)** + **Manager パターン** + **Repository パターン** のハイブリッドアーキテクチャを採用しています。`ARCHITECTURE.md` によると、以下のレイヤー構造になっています：

```
Engine (Facade) → Managers (9 modules) → Entity (ECS) → Systems
```

**8つのパッケージ** によるモジュール分割：
- `core` - 基盤システム
- `gameplay` - ゲームプレイロジック
- `character` - キャラクター関連
- `social` - ソーシャル機能
- `meta` - メタ進行
- `world` - ワールドシステム
- `narrative` - 物語システム
- `platform` - プラットフォーム固有

### 1.2 主な技術的強み

| 領域 | 実装内容 | 評価 |
|------|----------|------|
| **ECS実装** | `Entity` クラス (1701行) に20+ コンポーネント型、完全な `to_dict`/`from_dict` シリアライゼーション | ⭐⭐⭐⭐⭐ |
| **Repositoryパターン** | `InMemoryRepository` + `CachedRepository` (LRU 128)、インデックス付きクエリ (`MonsterRepository`) | ⭐⭐⭐⭐⭐ |
| **スキーマ駆動データ** | Pydantic生成モデル + JSON Schema検証、寛容ローディングフォールバック | ⭐⭐⭐⭐ |
| **イベントバス** | Pub/Sub パターン、例外分離、グローバルインスタンス | ⭐⭐⭐⭐ |
| **多言語対応** | 6言語 (en/ja/ko/zh-cn/zh-tw)、ネストキー平坦化、検証・比較ツール | ⭐⭐⭐⭐⭐ |
| **時間システム** | `WorldClock`、4フェーズ (DAWN/DAY/DUSK/NIGHT)、NPC/施設レジストリ | ⭐⭐⭐⭐ |
| **スキルシステム** | 融合/進化/覚醒/継承/共鳴/特殊化/転移の7メカニクス | ⭐⭐⭐⭐⭐ |

---

## 2. コアシステム詳細レビュー

### 2.1 ECS エンティティシステム (`naRou/ecs/entity.py`, `naRou/ecs/components/components.py`)

**良い点:**
- 20種類以上の `@dataclass` コンポーネントが適切に分離されている
- `AttributesComponent` と `Attributes` (レガシー互換) の二重定義は移行期の妥協として理解可能
- 全コンポーネントに `to_dict`/`from_dict` 実装済み → セーブ/ロード完全対応
- `CombatIntentComponent` は「描画/AI用途のみ・セーブ不要」と明記され責務が明確

**懸念点:**
```python
# entity.py:56-132 __init__ が巨大 (76行)
# 1701行の単一クラス → 責務過多の兆候
# プロパティ委譲パターンでコンポーネントアクセスしているが、全50+プロパティ
```

**推奨:** `Entity` を複数のミックスインクラスやファサードに分割検討

### 2.2 戦闘システム (`naRou/systems/combat_system.py`, `naRou/managers/combat_manager.py`)

**実装範囲 (447行):**
- 属性ダメージ計算 (`calc_element_damage`)
- 呪文成功率計算 (`calc_spell_success`) - 知力/呪文レベル/装備補正
- 近接攻撃 + 属性 + 出血付与 (`calculate_melee_attack`)
- AoE 処理 (`apply_aoe`) - ビーム/円形/フレンドリーファイア
- 状態異常処理 (`process_status_effects`) - ティック処理/自然治癒
- エクスクルーシブスキル (Step 62) - 専用実行パス

**良い点:**
- 静的メソッド中心でステートレス → テスト容易
- `publish_damage_event`/`publish_kill_event` でイベントバス連携
- 定数 `EXCLUSIVE_SKILLS` でデータ駆動

**懸念点:**
```python
# combat_system.py:107-224 calculate_melee_attack が 117行の巨大メソッド
# try/except で広範囲を包む → エラー隠蔽リスク
# Element enum 依存だが constants.py に定義 (循環参照リスク)
```

### 2.3 エンジンとマネージャー (`naRou/engine/engine.py`, `naRou/managers/`)

**現状:**
- `Engine` クラス **2601行** - 依然としてゴッドクラス傾向
- 50+ の `@property` setter/getter で状態管理
- 9つのマネージャーモジュールに分離済み (良い進捗)

**マネージャー分離状況:**
| マネージャー | 行数 | 責務 |
|-------------|------|------|
| `combat_manager.py` | 65行 | キル報酬処理のみ (薄い) |
| `faction_manager.py` | - | 派閥戦争 |
| `persistence_manager.py` | - | セーブ/ロード |
| `pet_bond_manager.py` | - | ペット絆 |
| `skill_reward_manager.py` | - | スキル報酬 |
| `world_news_manager.py` | - | 世界ニュース |
| `context_menu_builder.py` | - | コンテキストメニュー |

**推奨:** `Engine` からさらにロジックをマネージャーへ移譲し、Engine を純粋なファサード/オーケストレーターに

---

## 3. データ管理とスキーマ検証

### 3.1 DataManager (`naRou/data_manager.py` - 537行)

**アーキテクチャ:**
```
DataManager (BaseSystem)
├── 14 Repository インスタンス (items, monsters, skills, spells, ...)
├── JSON Schema バリデーション (jsonschema library)
├── 寛容ローディング (_build_quests_tolerant, _build_dungeon_themes_tolerant)
└── ファクトリメソッド (create_item, create_monster, get_random_*)
```

**良い点:**
- リポジトリパターンでデータアクセス抽象化
- `validate_all_data()` で全データ整合性チェック可能
- Pydantic モデルによる実行時型安全性

**懸念点:**
```python
# data_manager.py:269-309 寛容ローディングがスキーマ検証をバイパス
# "tolerant" = スキーマ不一致でもデフォルト値で続行 → データ品質低下リスク
# 14リポジトリを直接インスタンス変数保持 → 依存関係の爆発
```

### 3.2 リポジトリ実装 (`data/repositories/base.py`, `data/repositories/monster.py`)

**実装品質: 高**
- `Repository` Protocol でインターフェース定義
- `InMemoryRepository` - ジェネリック実装、フィルタクエリ対応
- `CachedRepository` - LRUキャッシュ (デフォルト128)、`_build_indexes` フック
- `MonsterRepository` - レベル/派閥/AIタイプの3インデックス実装

### 3.3 スキーマと生成モデル (`data/schemas/monster/monster.json`, `data/generated/monster/monster.py`)

**スキーマ品質:**
- `$defs` で `drop_entry`、`ai_type` を再利用可能定義
- `pattern` 制約で ID 形式強制 (`^[a-z_][a-z0-9_]*$`)
- `additionalProperties: false` で厳格モード

**生成モデル:**
- `pydantic.dataclasses` 使用 (通常の dataclass 互換)
- `DropEntry`、`AiType` enum、`MonsterDefinition` 完全生成
- バリデーションロジック組み込み済み

---

## 4. テストカバレッジ分析

### 4.1 既存テストファイル (7ファイル確認)

| テストファイル | 対象 | 行数 | カバレッジ領域 |
|--------------|------|------|--------------|
| `test_repositories.py` | 全リポジトリ | 282行 | アイテム/モンスター/スキル/呪文/融合/クエスト/派閥/実績/称号/職業/神/ダンジョン/ギルド |
| `test_architecture_refactor.py` | ECS/セーブロード | 124行 | コンポーネント初期化/委譲、後方互換、DialogueManager |
| `test_core_framework.py` | 幾何/経路探索 | 52行 | Point演算、Bresenham、A* |
| `test_entity.py` | Entity | 50行 | コンポーネント委譲、to_dict/from_dict ラウンドトリップ、JSON直列化 |
| `test_event_bus.py` | EventBus | 41行 | 購読/発行/解除、例外分離、購読者なし安全性 |
| `test_fov.py` | FOV/ライティング | 107行 | 再帰シャドウキャスト、視線、光量減衰、壁遮蔽、トーチ色調、環境光 |
| `test_enemy_intent_formation.py` | AI意図/陣形 | 485行 | 意図計算(ATTACK/CAST/MOVE/FLEE/HEAL)、AIロール、陣形戦術、難易度スケール |

### 4.2 カバレッジのギャップ

**未テスト/薄い領域:**
- 統合テスト (Engine + 全システム連携)
- E2E テスト (ゲームループ全体)
- パフォーマンスベンチマーク
- `Engine` クラスの巨大メソッド群 (`advance_world`, `render`, `_on_kill` 等)
- `DataManager` の寛容ローディングパス
- フロントエンド連携 (WebGL/Canvas デモ)

---

## 5. 定数とマジックナンバー (`naRou/constants.py` - 494行)

**整理済み項目:**
- `Element` enum (12属性: NONE/FIRE/ICE/LIGHTNING/HOLY/DARK/POISON/ACID/PHYSICAL/MIND/SOUND/LIGHT)
- `GameState` enum (12状態)
- `AIRole` enum (BRUTE/KITER/FLANKER/SUPPORT/TACTICAL/BOSS)
- `AIIntent` enum (IDLE/MOVE/ATTACK/CAST/FLEE/HEAL/BUFF/SUMMON/INTERACT)
- `FormationTactic` enum (NONE/KITE/FLANK/SPREAD/PINCER/SURROUND)

**残存マジックナンバー例:**
```python
# 散在する閾値・係数が定数化されていない箇所多数
# 例: combat_system.py のダメージ計算係数、item_generator.py の品質ロール確率等
```

---

## 6. フロントエンド/デモ実装の整合性

### 6.1 デモファイル構成 (`demos/`)

| デモファイル | 技術スタック | 目的 | Python連携 |
|------------|-------------|------|-----------|
| `full_demo.html` | Canvas + WebGL (ParticleSystem, FluidRenderer, LightingSystem, DecalSystem) | 統合グラフィックスショーケース | 非連携 (スタンドアロン) |
| `canvas_refactor_demo.html` | TileRenderer2D + TileAtlas | タイルレンダリング検証 | 非連携 |
| `demo_skill_eater_showcase.html` | ASCII Terminal Simulator (Vanilla JS) | スキルイーター機能デモ | 非連携 |
| `scene_01-24_*.html` | 各種 Canvas/WebGL | 24シーン機能別デモ | 非連携 |
| `skill_eater_cinematic_demo.html` | Canvas + シネマティック演出 | ストーリーデモ | 非連携 |

### 6.2 共通ライブラリ (`demos/lib/`)

```
AnimationController.js  - アニメーション制御
BoidSystem.js          - 群れ行動 (Flocking)
DecalSystem.js         - デカール描画 (足跡、血痕等)
EnvironmentShader.js   - 環境シェーダー
FluidRenderer.js       - 流体シミュレーション描画
LightingSystem.js      - 動的ライティング (FOV連携想定)
ParticleSystem.js      - パーティクルエフェクト
PostProcessManager.js  - ポストプロセス (ブルーム、色収差等)
ScreenShake.js         - 画面揺れ
TextureAtlas.js        - テクスチャアトラス管理
TileAtlas.js           - タイルアトラス (tiny_rogue アセット対応)
```

**評価:** ライブラリ品質は高いが、**Python エンジンとのデータ連携インターフェースが存在しない**

### 6.3 整合性の課題

```javascript
// full_demo.html:13-60 - 完全に独立したレンダリングパイプライン
// Python側の Engine.render() / render_to_text() とデータ共有なし
// 双方向同期: ゲームステート → フロントエンド のパイプライン欠如
```

**推奨アーキテクチャ:**
```
Python Engine (Game State) 
    ↓ WebSocket / WASM / REST
TypeScript Game Client (Shared Types via JSON Schema)
    ↓
CanvasEngine / TileRenderer2D (demos/lib/*)
```

---

## 7. スキルシステム詳細レビュー

### 7.1 7大メカニクス実装状況

| メカニクス | ファイル | 実装状況 | データファイル |
|-----------|---------|---------|--------------|
| **融合** | `skill_fusion.yaml`, `skill_fusion_chains.yaml` | 完成 | 定義ベース |
| **進化** | `skill_evolution.yaml` | 完成 | 段階的成長 |
| **覚醒** | `skill_awakening.yaml` | 完成 | 条件解放型 |
| **継承** | `skill_inheritance.yaml` | 完成 | 親子関係 |
| **共鳴** | `skill_resonance.yaml` | 完成 | 組み合わせボーナス |
| **特殊化** | `skill_specialization.yaml` | 完成 | 分岐進化 |
| **転移** | `skill_transfer.yaml` | 完成 | スキル移植 |

### 7.2 実装品質評価 (`naRou/systems/skill_eater_synthesis_system.py` 等)

**良い点:**
- データ駆動設計: 全メカニクスが YAML 定義で拡張可能
- `SkillFusionComponent` (ECS) でランタイム状態管理
- 合成/進化/覚醒の前提条件チェックロジック実装済み

**懸念点:**
```python
# skill_eater_synthesis_system.py 等が複数ファイルに分散
# 統合ファサード (SkillEaterSystem) が存在しない → 利用側が複雑
# toxicity (毒性) 管理、概念結晶、時空ヴォールト等の独自システムが追加され肥大化傾向
```

---

## 8. アイテム生成システム (`naRou/systems/item_generator.py` - 300行)

### 8.1 実装内容

```python
class ItemGenerator:
    def roll_quality(self, dungeon_level: int, luck_bonus: float) -> str
    def get_enchant_count(self, quality: str) -> int
    def generate_enchantments_for_item(self, item_def, quality, dungeon_level) -> list[EnchantmentInstance]
    def create_item(self, item_id, quality, dungeon_level, x, y) -> Item
    def generate_random_item(self, floor_level, x, y) -> Item
```

### 8.2 品質システム

| 品質 | 確率 (基底) | エンチャント数 | ダンジョンレベル補正 |
|------|------------|--------------|-------------------|
| common | ~50% | 0 | - |
| uncommon | ~25% | 1 | +level * 0.02 |
| rare | ~15% | 2 | +level * 0.03 |
| epic | ~7% | 3 | +level * 0.05 |
| legendary | ~3% | 4 | +level * 0.08 |

### 8.3 評価

**良い点:**
- `luck_bonus` パラメータで運ステータス連携
- ダンジョンレベルによるパワースケーリング実装
- エンチャント候補をカテゴリ別に定義 (`enchantments.yaml`)

**懸念点:**
```python
# item_generator.py:91-94 candidate_enchants がハードコード配列
# → データ駆動化されていない (enchantments.yaml 参照すべき)
# 品質ロール確率がマジックナンバー (constants.py へ移動推奨)
```

---

## 9. ローカライゼーションシステム (`naRou/localization_manager.py` - 444行)

### 9.1 実装詳細

```python
class LocalizationManager:
    # 6言語対応: en, ja, ko, zh-cn, zh-tw
    # YAML ファイル読み込み → フラット化 (dot notation)
    # フォールバックチェーン: 要求言語 → fallback → en
    # 検証機能: 欠落キー検出、言語間比較、統計取得
```

### 9.2 データ構造 (`data/text/*.yaml`)

```yaml
# data/text/ja.yaml 例
ui:
  inventory:
    title: "インベントリ"
    empty: "空です"
  combat:
    hit: "{attacker}は{target}に{damage}のダメージを与えた！"
```

**フラット化後:** `ui.inventory.title`, `ui.combat.hit`

### 9.3 評価

**優秀な実装:**
- `flatten_dict` でネスト対応
- `validate()` で全言語の欠落キー検出 (CI統合可能)
- `compare_languages()` で翻訳進捗管理
- `get_text_with_fallback()` で安全な取得
- グローバルインスタンス + 依存性注入両対応

**改善点:**
- インターポレーション (`{variable}`) の型安全性なし
- 複数形対応 (CLDR plural rules) 未実装
- 文脈依存翻訳 (context) 未サポート

---

## 10. 包括的改善提案

### 10.1 リファクタリング優先度マトリクス

| 優先度 | 対象 | 理由 | 推定工数 |
|--------|------|------|---------|
| **P0 (即時)** | `Engine` クラス分割 (2601行 → 複数マネージャー) | 保守性・テスト性・並行開発阻害 | 2-3週間 |
| **P0 (即時)** | 寛容ローディング除去 / 厳格スキーマ検証必須化 | データ品質・バグ温床 | 1週間 |
| **P1 (短期)** | `Entity` クラス分割 (1701行 → Mixin/ファサード) | 単一責務原則違反 | 1-2週間 |
| **P1 (短期)** | `calculate_melee_attack` 分割 (117行 → 複数メソッド) | 認知負荷・テスト困難 | 3-5日 |
| **P2 (中期)** | マジックナンバー全廃 (`constants.py` 集約) | 保守性・バランス調整容易化 | 1週間 |
| **P2 (中期)** | フロントエンド連携インターフェース設計 | Web版展開の前提 | 2-3週間 |
| **P3 (長期)** | 統合テスト/E2Eテスト基盤構築 | リグレッション防止 | 継続的 |

### 10.2 技術的負債カタログ

```markdown
## 負債項目 (抜粋)

1. **Engine ゴッドクラス** - 2601行、50+プロパティ、ゲームロジック混在
2. **Entity ゴッドクラス** - 1701行、全コンポーネントアクセサ保持
3. **寛容ローディング** - スキーマ検証バイパス、本番データ汚染リスク
4. **グローバル EventBus** - シングルトン、テスト汚染、依存関係隠蔽
5. **循環参照リスク** - constants.py (Element等) ←→ combat_system.py
6. **ハードコード配列** - item_generator.py エンチャント候補等
7. **型ヒント不完全** - 多くのメソッドで Any、Optional 未指定
8. **ドキュメント不足** - パブリックAPIの docstring 欠如多数
```

### 10.3 テスト戦略推奨

```yaml
# 推奨テストピラミッド
unit_tests:          # 現状: 7ファイル → 目標: 全モジュール 80%+ カバレッジ
  - 既存テスト拡充 (Engine, DataManager, CombatSystem 等)
  - プロパティベーステスト (hypothesis) でエッジケース検出

integration_tests:   # 新規作成
  - Engine + 全システム起動テスト
  - セーブ/ロード ラウンドトリップ (全エンティティタイプ)
  - データロード → ゲームプレイ → セーブ フロー

e2e_tests:           # 新規作成 (Playwright / pytest-asyncio)
  - 主要ユーザーシナリオ (ダンジョン探索、戦闘、クラフト等)
  - パフォーマンス回帰テスト (ターン処理時間、メモリ)

property_tests:      # 新規
  - A* 経路探索の最適性
  - アイテム生成の確率分布
  - 戦闘ダメージ計算の不変条件
```

### 10.4 CI/CD 統合提案

```yaml
# .github/workflows/ci.yml 推奨構成
jobs:
  lint:
    - ruff check .
    - mypy --strict naRou/
  test:
    - pytest --cov=naRou --cov-fail-under=80
    - pytest tests/integration/ (新規)
  schema_validation:
    - python -m naRou.data_validation data/ data/schemas/
  localization:
    - python -c "from naRou.localization_manager import LocalizationManager; lm=LocalizationManager(); assert lm.validate()['missing_keys'] == {}"
  frontend:
    - npm run lint (demos/ 配下)
    - npm run typecheck (TypeScript 化推奨)
```

### 10.5 アーキテクチャ進化ロードマップ

```
Phase 1 (現在〜1ヶ月):  安定化
├── Engine/Entity 分割着手
├── 寛容ローディング除去
├── 型ヒント完全化 (mypy strict)
└── 単体テスト 80% 達成

Phase 2 (1-3ヶ月):    モジュール化
├── パッケージ境界強化 (circular import 解消)
├── DI コンテナ導入 (naRou/di_container.py 活用)
├── フロントエンド API 設計 (WebSocket/JSON-RPC)
└── 統合テスト基盤

Phase 3 (3-6ヶ月):    スケーラビリティ
├── WASM 移植検討 (Pyodide / wasm-pack)
├── マルチプレイヤー基盤 (WebRTC / WebSocket)
├── モッドシステム正式化 (naRou/mods/ 拡張)
└── パフォーマンスプロファイリング自動化
```

---

## 11. 総評

### 総合スコア: **A- (優秀、改善余地あり)**

| 評価軸 | スコア | コメント |
|--------|--------|----------|
| アーキテクチャ設計 | A | ECS+Manager+Repository の明確な分離、8パッケージ構成 |
| 実装品質 | A- | 型安全性高い、データ駆動、シリアライゼーション完備 |
| テストカバレッジ | B+ | 単体テスト充実、統合/E2E未整備 |
| ドキュメント | B | ARCHITECTURE.md 等設計ドキュメントあり、API ドック不足 |
| 保守性 | B | ゴッドクラス残存、マジックナンバー散在 |
| 拡張性 | A | プラグイン/モッド対応、データ定義ベース拡張 |
| 国際化 | A | 6言語、検証ツール、フォールバック完備 |

### 最大の強み
> **「データ駆動 + 型安全 + ECS」の三位一体** により、コンテンツ追加 (モンスター、アイテム、スキル、クエスト) がコード変更なしで可能。商用ローグライクとして十分な拡張基盤。

### 最大のリスク
> **`Engine` / `Entity` のゴッドクラス化** が継続すると、機能追加ごとに複雑度が指数的に増大し、バグ修正・リファクタリングコストが爆発する。

### 即座に着手すべきアクション
1. `Engine` から `WorldManager`、`TurnManager`、`RenderManager` 等を抽出
2. `data_manager.py` の寛容ローディングを削除し、CI でスキーマ検証必須化
3. `constants.py` に散在する閾値・係数を全て定数化
4. 統合テストスイートの雛形作成 (GitHub Actions 統合)

---

**レビュー完了** - 全6タスク完了。詳細な個別ファイル指摘が必要な場合は、特定モジュールを指定して追加レビュー可能です。