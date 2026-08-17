# スキル合成・進化システム 詳細提案書

## 概要
スキル合成・進化システムは、プレイヤーが同じ系統のスキルを組み合わせてより強力な上位スキルを作り出し、さらに覚醒進化させて究極の形にまで発展させるシステムです。これにより、スキルのカスタマイズ性と戦略的深みが大幅に向上し、長期的なスキル育成の楽しさが提供されます。

## 9つの提案詳細

### 1. 基本スキル融合システム
**データ構造（`data/skill_fusion.yaml`）**
```yaml
fusion_recipes:
  fireball_fusion:
    name: "ファイアボール融合"
    description: "ファイアボール × 2 → メガファイア"
    inputs:
      - skill_id: "fireball"
        count: 2
    output:
      skill_id: "mega_fire"
      level: 1
    requirements:
      player_level: 20
      skill_levels:
        fireball: 10
    success_rate: 0.75  # 75% の成功率
    failure_penalty:    # 失敗時のペナルティ
      skill_experience_loss: 0.1  # 10% の経験値ロス
      material_loss: true
```

**実装箇所**
- `entity.py` に スキル合成用の一時保存フィールド追加
- `skill_fusion_system.py` 新規ファイル作成（SkillFusionData, SkillFusionRegistry, SkillFusionManager クラス）
- `game.py` の スキルメニューまたは特定アイテム使用で スキル融合UIを表示
- `advanced_systems.py` の SaveSystem に スキル融合データの保存/読み込み追加

### 2. 同系統スキル連鎖進化
**データ構造（`data/skill_evolution.yaml`）**
```yaml
evolution_chains:
  sword_mastery:
    name: "剣の熟達進化"
    description: "剣スキルの段階的進化チェーン"
    stages:
      - id: "sword_novice"
        name: "剣の初心者"
        unlock_condition: "skill_level >= 1"
        bonuses: {accuracy: 0.05}
      - id: "sword_apprentice"
        name: "剣の見習い"
        unlock_condition: "skill_level >= 10 AND evolved_from: sword_novice"
        bonuses: {accuracy: 0.1, critical_chance: 0.02}
      - id: "sword_expert"
        name: "剣の達人"
        unlock_condition: "skill_level >= 20 AND evolved_from: sword_apprentice"
        bonuses: {accuracy: 0.15, critical_chance: 0.05, attack_speed: 0.1}
      - id: "sword_master"
        name: "剣の達人"
        unlock_condition: "skill_level >= 30 AND evolved_from: sword_expert"
        bonuses: {accuracy: 0.2, critical_chance: 0.1, attack_speed: 0.15, damage: 0.1}
```

**実装箇所**
- `entity.py` に スキル進化状態用フィールド追加（`skill_evolution: Dict[str, str] = field(default_factory=dict)`）
- `skill_evolution_system.py` 新規ファイル作成
- `game.py` の スキルレベルアップ処理で 進化条件をチェックし自動進化
- スキルUIで 現在の進化段階と次の進化条件を表示

### 3. 覚醒スキルシステム
**データ構造（`data/skill_awakening.yaml`）**
```yaml
awakenings:
  dragon_slaying_awakening:
    name: "竜殺しの覚醒"
    description: "ドラゴンスレイヤースキルの覚醒形態"
    base_skill: "dragon_slaying"
    requirements:
      skill_level: 50
      dragon_kills: 100
      specific_items: 
        - item_id: "dragon_heart"
          count: 1
        - item_id: "dragon_scale_armor"
          count: 1
    awakened_skill:
      skill_id: "dragon_slaying_awakened"
      name: "覚醒・竜殺し"
      description: "竜の血を宿した究極の竜殺し技"
      bonuses: 
        damage_vs_dragon: 2.0  # 竜に対して2倍ダメージ
        area_of_effect: 2      # 範囲が2マスに拡大
        mana_cost_reduction: 0.3 # マナ消費30%削減
    visual_effect: "dragon_aura"  # 覚醒時の視覚効果
    passive_effects: 
      - "dragon_sense"  # 近くの竜を感知する能力
```

**実装箇所**
- `entity.py` に 覚醒スキル状態用フィールド追加（`awakened_skills: List[str] = field(default_factory=list)`）
- `skill_awakening_system.py` 新規ファイル作成
- `game.py` の 特定条件達成時（ボス撃破、アイテム収集等）で 覚醒クエストを提示
- 覚醒スキル発動時に 特別な視覚・音響効果を再生
- 覚醒状態での スキル挙動変更を実装

### 4. スキル特性転移システム
**データ構造（`data/skill_transfer.yaml`）**
```yaml
transfer_traits:
  critical_boost:
    name: "クリティカル強化転移"
    description: "クリティカル関連の特性を別スキルに転移"
    source_traits: ["critical_chance", "critical_damage"]
    target_skills: ["sword_skills", "axe_skills"]  # 転移可能なスキルカテゴリ
    transfer_ratio: 0.5  # 50% の特性値を転移
    cost: 
      skill_points: 100
      rare_materials: 
        - item_id: "philosophers_stone"
          count: 1
    irreversible: true  # 一度転移すると元に戻せない
```

**実装箇所**
- `entity.py` に スキル特性データ用フィールド追加（スキルごとのカスタムボーナスを保存）
- `skill_transfer_system.py` 新規ファイル作成
- `game.py` の スキル詳細画面で 特性転移オプションを表示
- 転移実行時に 元スキルから特性を抽出し、対象スキルに付与
- 転移後の バランス調整（元スキルの弱体化等）

### 5. スキル共鳴システム（同装備スキルボーナス）
**データ構造（`data/skill_resonance.yaml`）**
```yaml
resonance_sets:
  flame_knight_set:
    name: "炎の騎士セット"
    description: "炎属性スキルを3つ以上装備すると共鳴発動"
    required_skills: ["fireball", "flame_sword", "fire_wall"]
    min_count: 3
    resonance_effects:
      - name: "炎の共鳴"
        description: "炎属性スキルの威力と持続時間が増加"
        bonuses:
          fire_damage: 0.25
          duration: 0.2
          mana_cost: -0.15
      - name: "炎のオーラ"
        description: "周囲の敵に継続ダメージを与える"
        effect: 
          type: "damage_over_time"
          damage: 5
          interval: 2
          radius: 3
    visual_effect: "flame_aura"
```

**実装箇所**
- `entity.py` に 現在装備中のスキルセットを追跡するフィールド追加
- `skill_resonance_system.py` 新規ファイル作成
- `game.py` の スキル装備/解除時に 共鳴条件をチェックし効果を適用/解除
- 共鳴効果適用時の バフ・デバフ管理システム連携
- UIで 共鳴状態と必要スキルの進捗を表示

### 6. スキル継承システム（転生時のスキル引き継ぎ）
**データ構造（`data/skill_inheritance.yaml`）**
```yaml
inheritance_rules:
  bloodline_skills:
    name: "血統スキル継承"
    description: "特殊な血統を持つキャラクターは固有スキルを継承可能"
    inheritance_type: "bloodline"  # 血統、メンター、自己開発等
    eligible_skills: ["dragon_blood", "phoenix_flare", "celestial_light"]
    inheritance_rate: 0.3  # 30% の確率で継承
    level_bonus: 0.5  # 継承時のレベルボーナス（継承スキルは+50% レベルで開始）
    requirements:
      specific_achievements: 
        - "ancient_hero"
        - "bloodline_discovery"
```

**実装箇所**
- `entity.py` に 継承可能スキルリスト用フィールド追加（`inheritable_skills: List[str] = field(default_factory=list)`）
- `skill_inheritance_system.py` 新規ファイル作成（転生システムと連携）
- 転生時に 血統や実績に基づいて 継承可能スキルを決定
- 継承スキルは 元のレベルの一定割合で開始（レベル0ではない）
- UIで 継承可能スキルと継承確率を表示

### 7. スキル分離・専門化システム
**データ構造（`data/skill_specialization.yaml`）**
```yaml
specialization_paths:
  fireball_specialization:
    name: "ファイアボール専門化パス"
    description: "ファイアボールを特定方向に専門化"
    base_skill: "fireball"
    branches:
      - id: "fireball_rapid"
        name: "連射ファイアボール"
        description: "発射速度重視のファイアボール"
        requirements:
          skill_level: 25
          specific_usage: 
            use_count: 500  # 500回使用
            time_limit: 3600  # 1時間以内
        bonuses:
          cast_time: -0.4
          mana_cost: 0.1  # ややコスト増加だが速度が大きく上昇
      - id: "fireball_impact"
        name: "衝撃ファイアボール"
        description: "威力重視のファイアボール"
        requirements:
          skill_level: 25
          stat_requirements:
            strength: 15
        bonuses:
          damage: 0.5
          area_of_effect: 0.3
          cast_time: 0.2  # やや遅くなるが威力が大きく上昇
```

**実装箇所**
- `entity.py` に スキル専門化状態用フィールド追加（`skill_specialization: Dict[str, str] = field(default_factory=dict)`）
- `skill_specialization_system.py` 新規ファイル作成
- `game.py` の スキル使用統計を追跡し、 特定条件達成で 専門化オプションを提示
- 専門化選択時に 元スキルの能力を再分配（トレードオフの実装）
- 専門化スキルは 元スキルとは別スキルとして扱われ、 独立してレベルアップ可能

### 8. スキル融合連鎖システム（多段階融合）
**データ構造（`data/skill_fusion_chains.yaml`）**
```yaml
fusion_chains:
  ultimate_dragon_slayer:
    name: "究極竜殺し融合連鎖"
    description: "複数段階を経て究極の竜殺しスキルを創造"
    stages:
      - stage: 1
        name: "竜の牙の融合"
        inputs:
          - skill_id: "fang_strike"
            count: 3
          - item_id: "dragon_fang"
            count: 1
        output:
          skill_id: "dragon_fang_strike"
          level: 1
        requirements:
          player_level: 30
      - stage: 2
        name: "竜の鱗の強化"
        inputs:
          - skill_id: "dragon_fang_strike"
            count: 2
          - item_id: "dragon_scale"
            count: 2
        output:
          skill_id: "dragon_scale_fang_strike"
          level: 1
        requirements:
          player_level: 40
          previous_stage_clear: true
      - stage: 3
        name: "竜の心臓の融合"
        inputs:
          - skill_id: "dragon_scale_fang_strike"
            count: 2
          - item_id: "dragon_heart"
            count: 1
        output:
          skill_id: "ultimate_dragon_slayer"
          level: 1
        requirements:
          player_level: 50
          previous_stage_clear: true
          special_condition: "full_moon"  # 特殊条件（満月時のみ）
```

**実装箇所**
- `entity.py` に 融合連鎖進捗用フィールド追加（`fusion_chain_progress: Dict[str, int] = field(default_factory=dict)`）
- `skill_fusion_chain_system.py` 新規ファイル作成
- `game.py` の 融合素材収集時やスキル使用時に 連鎖進捗を更新
- 各ステージクリア時に 中間スキルを付与し、次のステージを解放
- 最終ステージ達成時に 究極スキルを付与し、 特別な称号や報酬を付与

### 9. スキル融合アーカイブシステム（スキル図鑑）
**データ構造（`data/skill_archive.yaml`）**
```yaml
archive_categories:
  elemental_spells:
    name: "元素魔法アーカイブ"
    description: "火・水・風・土の元素系スキルの収集記録"
    skills: ["fireball", "ice_shard", "wind_cutter", "earth_shield"]
    completion_rewards:
      title: "元素マスター"
      stat_bonus: {magic: 10, mana: 100}
      unique_effect: "elemental_affinity_all"  # 全元素に対する親和性
    archive_entries:
      fireball:
        description: "基本的な火属性攻撃呪文"
        historical_note: "古代の魔道士が発見した最初の攻撃魔法"
        rarity: "common"
      ice_shard:
        description: "氷の鋭い破片を飛ばす攻撃呪文"
        historical_note: "北方の氷河地帯で発展した防衛魔法の応用"
        rarity: "uncommon"
```

**実装箇所**
- `entity.py` に スキルアーカイブ進捗用フィールド追加（`skill_archive_progress: Dict[str, bool] = field(default_factory=dict)`）
- `skill_archive_system.py` 新規ファイル作成
- `game.py` の 新規スキル習得時や アーカイブ条件達成時に エントリーを解放
- アーカイブUIで スキルの歴史・伝説・収集状況を表示
- カテゴリコンプリート時に 特別な称号・ステータスボーナス・ユニーク効果を付与
- アーカイブ進捗に基づく スキル発見確率の上昇（レアスキルが見つかりやすくなる）

## 実装優先度マトリクス

| 優先度 | システム | 説明 | 実装難易度 |
|--------|----------|------|------------|
| 高 | 基本スキル融合システム | スキル合成の核となるメカニクス | 中 |
| 高 | 同系統スキル連鎖進化 | スキルの自然な成長感を提供 | 中 |
| 中 | 覚醒スキルシステム | スキルの劇的な進化を体験させる | 中 |
| 中 | スキル特性転移システム | スキルのカスタマイズ性を高める | 中 |
| 中 | スキル共鳴システム | スキル組み合わせの戦略性を追加 | 中 |
| 低 | スキル継承システム | 転生システムとの連携（転生実装後） | 高 |
| 中 | スキル分離・専門化システム | スキルの使い道を広げる | 中 |
| 低 | スキル融合連鎖システム | 長期的な目標設定を提供 | 高 |
| 低 | スキル融合アーカイブシステム | 収集要素とロリー要素 | 中 |

## entity.py への追加フィールド

```python
@dataclass
class Entity:
    # ... existing fields ...
    # スキル合成・進化システム
    skill_fusion_materials: Dict[str, int] = field(default_factory=dict)  # 融合素材一時保存
    skill_evolution: Dict[str, str] = field(default_factory=dict)  # スキルID: 現在の進化段階
    awakened_skills: List[str] = field(default_factory=list)  # 覚醒済みスキルリスト
    skill_traits: Dict[str, Dict[str, float]] = field(default_factory=dict)  # スキルID: {特性名: 値}
    equipped_skills: List[str] = field(default_factory=list)  # 現在装備中のスキル
    inheritable_skills: List[str] = field(default_factory=list)  # 継承可能スキルリスト
    skill_specialization: Dict[str, str] = field(default_factory=dict)  # スキルID: 専門化パス
    fusion_chain_progress: Dict[str, int] = field(default_factory=dict)  # 融合連鎖ID: 現在ステージ
    skill_archive_progress: Dict[str, bool] = field(default_factory=dict)  # アーカイブエントリーID: 解放済みか
```

## 統合フロー

1. プレイヤーがスキルを使用したり、素材を収集したりする
2. `game.py` の各種処理で スキル使用回数・素材収集数・レベル等を更新
3. 特定条件達成時に:
   - スキル融合UIが利用可能になる（十分な素材とレベルがある場合）
   - スキル進化条件が満たされる（自動または手動で進化可能）
   - 覚醒クエストが提示される（条件達成時）
   - スキル共鳴条件が満たされる（装備スキルセット変更時）
   - スキル専門化オプションが提示される（使用統計達成時）
   - スキル融合連鎖の進捗が更新される（素材収集時）
   - スキルアーカイブエントリーが解放される（新規スキル習得時）
4. プレイヤーが UI から 各種操作を選択:
   - スキル融合: 素材を消費して新しいスキルを取得
   - スキル進化: スキルポイントを消費して進化段階を上げる
   - 覚醒: 特定アイテムを消費して覚醒スキルを取得
   - スキル特性転移: スキルポイントと素材を消費して特性を転移
   - スキル専門化: 専門化パスを選択してスキルを分離
   - スキル融合連鎖: 次のステージの素材を収集して進行
5. 各操作時に:
   - 該当システムが 変更を適用（スキル追加・削除・変更・ボーナス付与等）
   - UIで 結果を表示（成功/失敗エフェクト）
   - 必要に応じて 視覚・音響特別効果を再生
6. `advanced_systems.py` の SaveSystem で スキル合成・進化データを保存
7. スキルUIで 現在のスキル状態・進化段階・覚醒状態等を表示
8. 戦闘時に:
   - 進化段階ボーナスが適用される
   - 覚醒スキルの特別効果が発動される
   - スキル特性が参照される
   - スキル共鳴効果が適用される
   - スキル専門化による能力変更が反映される

## 次のステップ

1. 「スキル合成・進化システムの詳細な実装計画書を作成して　低性能なLLMでも実装可能なように１～７２までの小さなステップに分割して」
   - 本提案書を基に、72段階の細かい実装手順に分割した計画書を作成