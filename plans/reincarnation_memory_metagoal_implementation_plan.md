# 転生の記憶とメタゴール（長期目標）詳細実装計画書

## 1. 目的と全体概要

本仕様は、プレイヤーが周回（輪廻転生）を重ねる中で、**動的に生成される「前世の記憶の欠片（Memory Fragments）」**を収集し、**周回ごとにランダム性・多様性を持つ「周回フラグ・メタゴール（Meta Goals / Challenge Progress）」**に挑むことで、永続的な恩恵・ビルド幅・未知のストーリー展開をアンロックする長期進行システムを実装します。

### ユーザー要件の反映方針
1. **記憶の欠片は動的に生成（Procedural / Dynamic Memory Fragments）**:
   - 事前定義された固定リストだけでなく、前世の冒険履歴（倒した強敵の種族、最も使ったスキル、訪れたダンジョン、死因、結んだ盟友）やワールド生成シード値から、**動的な記憶の欠片（名前、フレーバーテキスト、付与バフ/特性）**を合成・生成します。
   - 動的記憶はアーカイブされ、コレクション要素およびパッシブ恩恵（「火竜を討ちし前世の残照」「深淵を彷徨いし記憶」等）として次世代のキャラクターに還元されます。
2. **周回フラグはある程度ランダムに（Randomized / Procedural Cycle Flags & Modifiers）**:
   - 転生時に、次世代の世界やプレイヤーにランダムな「運命の制約・特異点（Cycle Modifiers / Legacy Quests）」が付与されます（例：「魔力奔流の時代：魔法威力+30%だが消費MP2倍」「孤高の誓い：ペット雇用不可だが単独時全ステータス+20%」など）。
   - 周回クリア時、プレイヤーが取ったランダムな行動や分岐選択（NPCの救済/見殺し、勢力の興亡）が `player_legacy` にランダムな因果フラグとして蓄積され、次世代のNPCの初期好感度や出現ボスに影響を与えます。

---

## 2. アーキテクチャ設計

```mermaid
flowchart TD
    subgraph Entity Components
        RC[ReincarnationComponent<br/>- collected_fragments: List[dict/str]<br/>- challenge_progress: Dict[str, int]<br/>- cycle_modifiers: List[str]]
        AC[AchievementComponent<br/>- meta_progression: Dict[str, int]<br/>- permanent_bonuses: Dict[str, float]]
        SC[StorytellerComponent<br/>- memory_fragments: List[dict]<br/>- player_legacy: Dict[str, Any]]
    end

    subgraph MetaProgressionSystem
        MFG[MemoryFragmentGenerator<br/>動的記憶の欠片生成]
        MGE[MetaGoalEvaluator<br/>長期目標 & ランダム周回フラグ評価]
        PBA[PermanentBonusApplier<br/>永続ボーナス・ステータス反映]
    end

    subgraph Game Loop & Reincarnation
        GAME[Game / Dungeon Events] -->|行動/討伐/探索| MGE
        GAME -->|強敵討伐/重要イベント| MFG
        MFG -->|動的生成| SC
        MFG -->|記憶獲得| RC
        MGE -->|目標達成| AC
        REINC[ReincarnationSystem] -->|転生実行時に前世を抽出| MFG
        REINC -->|ランダム周回フラグ生成| RC
        REINC -->|次世代へ適用| PBA
    end
```

---

## 3. コンポーネントおよびデータ定義

### 3.1 データ構造の拡張 (`components.py` / `meta_progression_system.py`)

#### 動的記憶の欠片 (Dynamic Memory Fragment)
```python
@dataclass
class MemoryFragment:
    fragment_id: str             # 一意なID (例: "frag_dragon_slayer_gen1_a8f9")
    name: str                    # 表示名 (例: "古の竜を穿ちし記憶")
    description: str             # 動的フレーバーテキスト
    generation: int              # 獲得した世代 (周回数)
    category: str                # "combat", "magic", "survival", "exploration", "social"
    buff_traits: Dict[str, float]# パッシブ補正 (例: {"fire_resist": 15.0, "str": 3.0})
    lore_snippet: str            # ストーリー/世界観の断片テキスト
    unlocked_secrets: List[str]  # 解放される隠し要素/ダンジョンID/レシピ等
```

#### ランダム周回フラグ・特異点 (Cycle Modifier / Random Meta-Goal)
```python
@dataclass
class CycleModifier:
    modifier_id: str             # "mod_mana_surge", "mod_lone_wolf", etc.
    name: str                    # 表示名 (例: "魔力奔流の兆し")
    description: str             # 説明
    target_goal: str             # 達成条件キー (例: "reach_depth_50_with_magic")
    reward_meta_points: int      # クリア時のメタポイント/解放要素
    positive_effects: Dict[str, float]
    negative_effects: Dict[str, float]
```

---

## 4. 各システムの詳細仕様

### 4.1 `MetaProgressionSystem` (`systems/meta_progression_system.py`) [新規]

1. **`generate_dynamic_fragment(player: Entity, trigger_type: str, context: dict) -> MemoryFragment`**:
   - プレイヤーの現世代での実績（直前の戦闘内容、使用頻度トップの武器、現在のカルマ、ダンジョン深度など）をサンプリング。
   - テンプレート辞書（Prefix, Root, Suffix, Lore）と乱数シードを組み合わせて、唯一無二の「記憶の欠片」を動的に生成。
   - `StorytellerComponent.memory_fragments` および `ReincarnationComponent.collected_fragments` に追加。

2. **`roll_random_cycle_modifiers(reincarnation_count: int, seed: int = None) -> List[CycleModifier]`**:
   - 転生時に2〜3個のランダムな周回目標・特異点候補をプロシージャル生成/抽選。
   - プレイヤーが転生UIまたは初期設定で選択可能（あるいは転生時に自動決定）。

3. **`evaluate_meta_goals(player: Entity, event_name: str, event_data: dict)`**:
   - 複数周回で累積する長期目標（例：「全10属性の記憶をコンプリートする」「累計ダンジョン深度1000F踏破」「5世代連続でカルマ善を維持」など）の進行を更新。
   - 達成時に `AchievementComponent.permanent_bonuses` へ永続ボーナスを加算。

4. **`apply_all_permanent_bonuses(player: Entity)`**:
   - 収集された全記憶の欠片の `buff_traits` と、メタゴール達成による `permanent_bonuses` を集計。
   - プレイヤーの基本ステータス（HP, MP, 各種耐性, 攻撃力, 経験値倍率など）に合算適用。

### 4.2 `ReincarnationSystem` (`systems/reincarnation_system.py`) [改修]

1. **前世の総括と動的記憶の最終生成**:
   - 死亡時または転生選択時に、その周回の「生涯の要約（最も高かった能力、討伐数、代表的な行動）」から最高位の「前世の結晶記憶」を1つ動的に生成して遺産に追加。
2. **ランダム因果フラグの継承 (`player_legacy`)**:
   - 前世で倒した勢力、救ったNPCなどのフラグを確率的に歪ませて次世代へ引き継ぎ（例：前世で盗賊ギルドを壊滅させた場合、次世代で「盗賊の残党から敵視されるが、市民からの初期好感度+20」などのランダム因果が発生）。
3. **メタ進行データの保持**:
   - `SaveSystem` と連携し、次世代のキャラクターへ `collected_fragments`, `meta_progression`, `permanent_bonuses`, `challenge_progress` を欠落なく引き継ぎ。

### 4.3 `Game` (`game.py`) / UI [統合]

1. **記憶獲得演出**:
   - ボス討伐や特定の古代遺物調査時に「【記憶の残照】〇〇の記憶が蘇った！」というメッセージとバフ適用通知。
2. **ステータス・メタ画面への反映**:
   - ステータス表示や詳細メニューにおいて、獲得済みの「記憶の欠片」一覧と適用中の永続パッシブボーナスを閲覧可能にする。

---

## 5. 実装ステップ計画

```markdown
- [ ] Phase 1: データモデルと動的生成エンジンの実装
  - `systems/meta_progression_system.py` の作成
  - 動的記憶の欠片生成ロジック (`MemoryFragmentGenerator`) の実装
  - ランダム周回フラグ・特異点生成ロジックの実装
- [ ] Phase 2: メタゴール評価と永続ボーナス計算の実装
  - 長期目標（累積討伐、属性コンプリート、世代連鎖など）の判定処理
  - パッシブボーナスのステータス反映ロジック (`apply_all_permanent_bonuses`)
- [ ] Phase 3: 転生システム (`ReincarnationSystem`) および `SaveSystem` との連携
  - 転生時の動的遺産生成・因果フラグ変調・ステータス初期化
  - セーブ＆ロード時のデータ互換性保証 (`DEFAULT_FIELD_FACTORIES` 連携)
- [ ] Phase 4: `game.py` へのイベントフックと演出統合
  - ゲーム内アクション（探索、討伐、古代碑文調査）からのトリガー
- [ ] Phase 5: 単体・統合テストの作成と検証
  - `tests/test_meta_progression.py` 新設
  - 転生テスト (`tests/test_reincarnation_system.py`) の拡充
```

---

## 6. テスト・検証計画

1. **動的記憶生成テスト**:
   - 様々なシチュエーション（魔法使いビルド、戦士ビルド、悪人プレイ等）で適切なフレーバーとバフを持つ記憶の欠片が動的に生成されること。
2. **周回フラグ＆因果継承テスト**:
   - 転生を複数回実行し、`collected_fragments` が蓄積され、永続ボーナスが正しく加算・累積されること。
   - ランダムな周回フラグ（Cycle Modifiers）が世代ごとに変動して適用されること。
3. **セーブ/ロード互換性テスト**:
   - 生成された動的記憶（辞書/クラス）がJSONシリアライズ・デシリアライズ後も破損せず復元できること。
4. **既存テストスイートの全パス確認**:
   - リファクタリング済みの全テストが100%成功を維持すること。
