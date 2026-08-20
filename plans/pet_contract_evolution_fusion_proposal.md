# ペット契約・進化・融合システム 詳細提案書
なろう系要素「ペット契約・進化・融合システム」をElonaに統合するための9つの具体的提案。既存のペットシステム（`entity.py`のPetAIクラス、`entity.py`のpetsリスト、`game.py`の_pet_aiメソッド）を拡張し、契約絆・進化分岐・遺伝子融合による新種創造を実現。

---

## 提案1: ペット契約絆システム

### 概要
ペットとの契約レベル（絆度）を管理し、絆度に応じてペットの能力向上・特殊スキル解放・進化条件緩和を行う。契約は食事・プレゼント・共闘・長時間同行で上昇し、放置や戦闘不能で減少する。

### データ構造（`data/pet_contracts.yaml`）
```yaml
pet_contracts:
  default:
    name: "標準契約"
    icon: "🤝"
    max_bond: 1000
    bond_gain:
      feeding: 10      # エサやり時
      gift: 25         # プレゼント時
      combat_together: 5 # 1ターン共闘時
      walking: 1       # 1ターン同行時
    bond_decay:
      neglected: 2     # 1ターン放置時
      defeated: 50     # ペット戦闘不能時
      dismissed: 100   # 契約解除時
    bond_effects:
      - threshold: 200
        effects:
          - type: "stat_bonus"
            value:
              strength: 2
              agility: 2
      - threshold: 500
        effects:
          - type: "unlock_skill"
            skill_id: "loyalty_strike"
          - type: "exp_bonus"
            value: 0.1
      - threshold: 800
        effects:
          - type: "evolution_bonus"
            value: 0.5  # 進化必要経験値50%削減
          - type: "unlock_skill"
            skill_id: "guardian_bond"
```

### 実装箇所
- 新規: `pet_contract_system.py` - PetContractRegistry, PetContractManager
- 既存: `entity.py` PetAIクラスに `bond: int`, `contract_id: str` 追加
- 既存: `game.py` _pet_ai で 絆度増減・効果適用
- 既存: `game.py` アイテム使用時・戦闘時 で 絆度増加トリガー

---

## 提案2: ペット進化分岐システム

### 概要
ペットは特定条件（レベル・絆度・アイテム・場所）を満たすと複数の進化路線から選択可能。進化後は見た目・ステータス・スキルが大幅に変更され、元の種族特性を一部継承する。

### データ構造（`data/pet_evolutions.yaml`）
```yaml
pet_evolutions:
  puppy:
    name: "子犬"
    evolutions:
      - id: "hound"
        name: "猟犬"
        requirements:
          level: 15
          bond: 300
          items: ["leather", "meat"]
          location: "forest"
        stat_changes:
          strength: +5
          agility: +8
          hp: +20
        skill_changes:
          - add: ["tracking", "bite"]
          - remove: ["playful_bark"]
        evolution_bonus:
          type: "permanent_exp_bonus"
          value: 0.1
      - id: "guard_dog"
        name: "警備犬"
        requirements:
          level: 15
          bond: 400
          items: ["metal_ingot", "magic_crystal"]
          location: "town"
        stat_changes:
          strength: +10
          constitution: +5
          hp: +30
        skill_changes:
          - add: ["guard_bark", "intercept"]
          - remove: ["playful_bark"]
        evolution_bonus:
          type: "permanent_gold_find"
          value: 0.15
      - id: "magic_hound"
        name: "魔導猟犬"
        requirements:
          level: 20
          bond: 500
          items: ["magic_herb", "mana_potion"]
          location: "magic_tower"
          skills: ["magic_basic"]  # プレイヤーが魔法基礎を習得必要
        stat_changes:
          intelligence: +8
          agility: +5
          mp: +25
        skill_changes:
          - add: ["magic_bite", "mana_sense"]
          - remove: ["bite"]
        evolution_bonus:
          type: "hybrid_bonus"
          value: 
            strength: +3
            intelligence: +3
```

### 実装箇所
- 新規: `pet_evolution_system.py` - PetEvolutionRegistry, PetEvolutionManager
- 既存: `entity.py` PetAIクラスに `evolution_path: List[str]`, `evolution_stage: int` 追加
- 既存: `game.py` _pet_ai で 進化条件チェック・進化実行
- 既存: `item_system.py` 特定アイテム使用時進化トリガー追加

---

## 提案3: ペット遺伝子融合・新種創造システム

### 概要
2体以上のペットの遺伝子を融合させて全く新しい種族のペットを創造可能。親の特性・スキル・見た目を組み合わせ、稀に珍しい変異種が発生。融合には特別な施設・アイテム・契約レベルが必要。

### データ構造（`data/pet_fusion.yaml`）
```yaml
pet_fusion:
  fusion_recipes:
    - id: "dragon_hound"
      name: "ドラゴンハウンド"
      icon: "🐉🐕"
      description: "猛々しい猟犬と幼龍の遺伝子を融合"
      required_pets:
        - "hound"      # 進化後猟犬
        - "drake"      # 幼龍
      required_bond: [400, 350]  # 各ペットの最低契約度
      required_level: [20, 15]
      required_items: ["dragon_scale", "magic_crystal", "philosophers_stone"]
      required_facility: "alchemy_lab"
      result_pet: "dragon_hound"
      inheritance_rate: 0.7  # 親特性継承率
      mutation_chance: 0.1   # 突然変異率
      stat_template:
        strength: 18
        agility: 16
        constitution: 14
        intelligence: 10
        hp: 120
        mp: 40
      skill_inheritance:
        - from: "hound"
          skills: ["tracking", "bite"]
          rate: 0.8
        - from: "drake"
          skills: ["fire_breath", "wing_flutter"]
          rate: 0.6
      possible_mutations:
        - type: "ice_breath"
          chance: 0.3
          replaces: "fire_breath"
        - type: "two_heads"
          chance: 0.1
          effects:
            - type: "attack_bonus"
              value: 0.2
            - type: "hp_bonus"
              value: 0.15
    - id: "unicorn_pegasus"
      name: "ユニコーンペガサス"
      icon: "🦄🪽"
      description: "聖なる角と天馬の翼を併せ持つ神獣"
      required_pets:
        - "unicorn"
        - "pegasus"
      required_bond: [500, 500]
      required_level: [25, 25]
      required_items: ["holy_water", "feather_of_angel", "unicorn_horn"]
      required_facility: "shrine"
      result_pet: "unicorn_pegasus"
```

### 実装箇所
- 新規: `pet_fusion_system.py` - PetFusionRegistry, PetFusionManager
- 既存: `entity.py` に `pet_fusion_history: List[Dict]` 追加（融合記録）
- 既存: `game.py` 融合施設利用時・特別アイテム使用時 トリガー追加
- 既存: `advanced_systems.py` SaveSystem に融合履歴・新種データ保存

---

## 提案4: ペット血統・遺伝システム

### 概要
ペットには血統値が存在し、親の優れた特性を子孫に遺伝させることができる。血統はブリーディングによって強化され、特定の血統線は特別なスキルや外観を持つ。転生時にも一部の血統ボーナスを引き継げる。

### データ構造（`data/pet_bloodlines.yaml`）
```yaml
pet_bloodlines:
  royal_line:
    name: "王族血統"
    icon: "👑"
    description: "王族に仕える伝統的な血統。知性と忠誠が高い"
    stat_bonuses:
      intelligence: +5
      loyalty_gain: +0.2  # 絆度増加率
    exclusive_skills:
      - "royal_command"
      - "noble_presence"
    inheritance_priority: 1.0  # 高優先度で遺伝
    rarity: "legendary"
  hunter_line:
    name: "狩猟血統"
    icon: "🎯"
    description: "狩猟を生業とする血統。追跡と攻撃に長ける"
    stat_bonuses:
      agility: +8
      perception: +5
    exclusive_skills:
      - "tracking_master"
      - "precise_shot"
    inheritance_priority: 0.8
    rarity: "rare"
  magic_line:
    name: "魔法血統"
    icon: "🔮"
    description: "魔法使いの使い魔として育てられた血統。魔力が豊か"
    stat_bonuses:
      intelligence: +10
      mp: +30
    exclusive_skills:
      - "mana_sense"
      - "spell_amplify"
    inheritance_priority: 0.9
    rarity: "epic"
```

### 実装箇所
- 新規: `pet_bloodline_system.py` - PetBloodlineRegistry, PetBloodlineManager
- 既存: `entity.py` PetAIクラスに `bloodline: Optional[str]`, `bloodline_purity: float` 追加
- 既存: `game.py` ペット生成時・ブリーディング時 血統決定ロジック追加
- 既存: `advanced_systems.py` SaveSystem に血統データ保存
- 既存: `reincarnation_system.py` 転生時血統ボーナス引継ぎ追加（後で実装）

---

## 提案5: ペットシナジー・コンボシステム

### 概要
プレイヤーとペット、または複数のペットが特定のスキルを連続で使用すると、強力なコンボエフェクトが発動する。コンボは時間窓内でのスキル組み合わせで判定され、属性合成や追加効果が得られる。

### データ構造（`data/pet_synergy.yaml`）
```yaml
pet_synergy:
  combos:
    - id: "flame_pounce"
      name: "炎炎跳び"
      description: "ペットの炎属性攻撃直後にプレイヤーがジャンプ攻撃"
      participants: ["pet", "player"]
      skill_sequence: ["fire_bite", "jump_attack"]
      window: 3  # 3ターン以内
      effects:
        - type: "aoe_damage"
          radius: 2
          formula: "(pet.str + player.dex) * 1.5"
          element: "fire"
        - type: "status"
          effect: "burn"
          duration: 3
        - type: "bond_bonus"
          value: 15  # 絆度増加
    - id: "guardian_wall"
      name: "守護の壁"
      description: "ペットがガード姿勢をとり、プレイヤーがその背後で魔法詠唱"
      participants: ["pet", "player"]
      skill_sequence: ["guard_stance", "magic_cast"]
      window: 5
      effects:
        - type: "shield"
          value: "(pet.con * 2) + (player.int * 1.5)"
          duration: 2
        - type: "spell_power_bonus"
          value: 0.3
        - type: "bond_bonus"
          value: 10
    - id: "pack_hunt"
      name: "群れ狩り"
      description: "複数のペットが連携して同じ敵を攻撃"
      min_participants: 2
      max_participants: 4
      skill_sequence: ["pack_coordinate", "rush_attack"]  # 全員が同じスキル
      window: 2
      effects:
        - type: "damage_multiplier"
          value: 1.0 + (participant_count * 0.2)  # 参加者1人あたり20%増加
        - type: "crit_chance_bonus"
          value: participant_count * 5
        - type: "bond_bonus"
          value: participant_count * 5
```

### 実装箇所
- 新規: `pet_synergy_system.py` - PetSynergyManager
- 既存: `entity.py` に `recent_pet_skills: List[Tuple[str, int]]` 追加（スキルID, ターン数）- ペット用
- 既存: `entity.py` に `recent_player_pet_skills: List[Tuple[str, int, str]]` 追加（スキルID, ターン数, 参加者種別）
- 既存: `systems.py` CombatSystem で スキル使用時にコンボ判定・発動
- 既存: `game.py` _pet_ai で ペットスキル使用記録

---

## 提案6: ペット装備・ギアシステム

### 概要
ペット専用の装備品（首輪・鎧・武器・アクセサリー）を装着可能。装備品はステータス補正・スキル追加・特殊効果を持ち、ペットの契約度やレベルに応じて装備可能な品質が変わる。強化・錬金・カスタマイズも可能。

### データ構造（`data/pet_equipment.yaml`）
```yaml
pet_equipment:
  collars:
    - id: "basic_collar"
      name: "基本の首輪"
      icon: "🔗"
      required_bond: 0
      required_level: 1
      effects:
        - type: "stat_bonus"
          value:
            hp: +5
    - id: "magic_collar"
      name: "魔法の首輪"
      icon: "🔷"
      required_bond: 200
      required_level: 10
      effects:
        - type: "stat_bonus"
          value:
            mp: +15
            intelligence: +3
        - type: "skill_unlock"
          skill_id: "magic_affinity"
  armor:
    - id: "leather_barding"
      name: "革の馬鎧"
      icon: "🛡️"
      required_bond: 150
      required_level: 12
      effects:
        - type: "stat_bonus"
          value:
            defense: +8
            agility: -2  # 重さによるデメリット
        - type: "skill_unlock"
          skill_id: "defensive_posture"
    - id: "dragon_scale_barding"
      name: "龍の鱗鎧"
      icon: "🐉🛡️"
      required_bond: 500
      required_level: 25
      effects:
        - type: "stat_bonus"
          value:
            defense: +25
            fire_resistance: +30
        - type: "skill_unlock"
          skill_id: "scale_shield"
  weapons:
    - id: "pet_claws"
      name: "ペットの爪"
      icon: "⚔️"
      required_bond: 0
      required_level: 1
      effects:
        - type: "stat_bonus"
          value:
            attack: +3
        - type: "skill_unlock"
          skill_id: "scratch"
    - id: "enchanted_fang"
      name: "魔法の牙"
      icon: "🦷✨"
      required_bond: 300
      required_level: 18
      effects:
        - type: "stat_bonus"
          value:
            attack: +12
            intelligence: +5
        - type: "skill_unlock"
          skill_id: "magic_bite"
```

### 実装箇所
- 新規: `pet_equipment_system.py` - PetEquipmentRegistry, PetEquipmentManager
- 既存: `entity.py` PetAIクラスに `equipment: Dict[str, str]` 追加（スロット -> アイテムID）
- 既存: `item_system.py` ペット装備アイテムタイプ・ステータス定義追加
- 既存: `game.py` ペットとの交流時装備メニュー追加
- 既存: `systems.py` CombatSystem で ペット装備効果適用
- 既存: `advanced_systems.py` SaveSystem に ペット装備データ保存

---

## 提案7: ペット訓練・忠誠度システム

### 概要
ペットは訓練によって特定のスキルや行動パターンを習得可能。訓練には時間と専用施設が必要で、忠誠度が高いほど訓練効率が上がる。訓練科目には従軍・護衛・狩猟・魔法補助・芸などがあり、修了後に称号や特別スキルが得られる。

### データ構造（`data/pet_training.yaml`）
```yaml
pet_training:
  courses:
    - id: "combat_training"
      name: "戦闘訓練"
      icon: "⚔️"
      description: "基本的な戦闘技術と命令従従性を習得"
      required_bond: 100
      required_level: 5
      duration: 500  # 必要ターン数
      facilities: ["training_ground"]
      rewards:
        - type: "skill_unlock"
          value: ["basic_commands", "attack_on_sight"]
        - type: "stat_bonus"
          value:
            strength: +3
            agility: +3
        - type: "title"
          value: "trained_companion"
    - id: "magic_training"
      name: "魔法補助訓練"
      icon: "🔮📚"
      description: "魔法詠唱の補助や魔力探知を学ぶ"
      required_bond: 300
      required_level: 15
      required_skills: ["magic_basic"]  # プレイヤー側の必要スキル
      duration: 800
      facilities: ["magic_tower", "library"]
      rewards:
        - type: "skill_unlock"
          value: ["mana_sense", "spell_assist"]
        - type: "stat_bonus"
          value:
            intelligence: +5
            mp: +20
        - type: "title"
          value: "arcane_assistant"
    - id: "hunting_training"
      name: "狩猟訓練"
      icon: "🎯🐾"
      description: "追跡・罠仕掛け・獲物処理を学ぶ"
      required_bond: 200
      required_level: 10
      duration: 600
      facilities: ["forest", "hunting_lodge"]
      rewards:
        - type: "skill_unlock"
          value: ["tracking", "trap_setting", "skinning"]
        - type: "stat_bonus"
          value:
            agility: +8
            perception: +5
        - type: "title"
          value: "master_hunter"
```

### 実装箇所
- 新規: `pet_training_system.py` - PetTrainingRegistry, PetTrainingManager
- 既存: `entity.py` PetAIクラスに `training_progress: Dict[str, int]` 追加（コースID -> 進捗%）
- 既存: `entity.py` に `completed_pet_training: List[str]` 追加（修了コースリスト）
- 既存: `game.py` 訓練施設利用時 トレーニング進行・完了チェック追加
- 既存: `advanced_systems.py` SaveSystem に 訓練データ保存
- 既存: `title_system.py` ペット訓練称号データ追加

---

## 提案8: ペットギルド・フェローシップシステム

### 概要
プレイヤーはペット専用のギルドまたはフェローシップを結成可能。ペットギルドではペット同士の交流・共同訓練・情報交換が行われ、ギルドレベルに応じて特別な施設・サービス・ボーナスが解放される。ペット同士の契約や友好度も管理される。

### データ構造（`data/pet_guilds.yaml`）
```yaml
pet_guilds:
  default_guild:
    name: "冒険者ペットギルド"
    icon: "🐾🏰"
    description: "冒険者とそのペットたちの集う場所"
    max_members: 10  # 同時に預けられるペット数
    facilities:
      - "pet_hotel"
      - "training_area"
      - "social_park"
    guild_level_requirements:
      1: 0
      2: 500  # 総絆度
      3: 1500 # 総絆度 + 特定ペット種別
      4: 3000 # 総絆度 + 進化ペット数
    guild_buffers:
      - threshold: 2
        effects:
          - type: "bond_gain_bonus"
            value: 0.1  # 全員の絆度増加10%アップ
      - threshold: 3
        effects:
          - type: "exp_bonus"
            value: 0.05  # ペット経験値5%アップ
          - type: "heal_rate_bonus"
            value: 0.1  # 自然回復10%アップ
      - threshold: 4
        effects:
          - type: "rare_fusion_access"
          value: true  # 珍しい融合レシピ解放
```

### 実装箇所
- 新規: `pet_guild_system.py` - PetGuildRegistry, PetGuildManager
- 既存: `entity.py` に `pet_guild_id: Optional[str]`, `pet_guild_role: Optional[str]` 追加
- 既存: `game.py` ペットギルド施設利用時・ペット預け入れ時 トリガー追加
- 既存: `advanced_systems.py` SaveSystem に ペットギルドデータ保存
- 既存: `ui_fx_systems.py` ペットギルドUI・エフェクト追加

---

## 提案9: ペットレガシー・転生ボーナスシステム

### 概要
プレイヤーが転生（ニューゲーム+）時に、高レベル・高絆度・特殊進化を遂げたペットのレガシーを引き継ぐことができる。引き継げるものは血統ボーナス・特別スキル・外観・契約度の一部で、転生初期から強力なペットを仲間にできる。

### データ構造（`data/pet_legacy.yaml`）
```yaml
pet_legacy:
  legacy_transfer:
    - type: "bloodline_bonus"
      condition: "max_bond_1000"
      effect:
        type: "start_with_bloodline_purity"
        value: 0.3  # 転生開始時に血統純度30%で開始
      cost: 10  # レガシーポイント消費
    - type: "evolved_form"
      condition: "has_evolved_pet"
      effect:
        type: "start_with_evolved_form"
        value: "last_evolution"  # 最後の進化形で開始
      cost: 15
    - type: "legacy_skill"
      condition: "mastered_pet_skill"
      effect:
        type: "start_with_skill"
        value: "last_mastered_skill"  # 最後のマスタースキルを習得状態で開始
      cost: 8
    - type: "appearance_trait"
      condition: "rare_mutation"
      effect:
        type: "start_with_trait"
        value: "last_mutation"  # 最後の突然変異特性を引き継ぐ
      cost: 12
    - type: "bond_headstart"
      condition: "avg_bond_above_500"
      effect:
        type: "start_with_bond"
        value: 200  # 転生開始時の初期絆度
      cost: 6
  legacy_points:
    base: 20
    per_10_levels: 3
    per_max_bond_1000: 5
    per_evolved_pet: 8
    per_legendary_pet: 15
```

### 実装箇所
- 新規: `pet_legacy_system.py` - PetLegacyRegistry, PetLegacyManager
- 既存: `entity.py` に `pet_legacy_flags: Dict[str, bool]` 追加（レガシー条件達成記録）
- 既存: `advanced_systems.py` SaveSystem に レガシー関連データ保存
- 既存: `game.py` 新規ゲーム開始時 ペットレガシー選択UI追加
- 既存: `reincarnation_system.py` 転生処理に ペットレガシー適用ロジック追加
- 既存: `title_system.py` ペットレガシー称号データ追加（例: "レガシーブリーダー"）

---

## 実装優先度マトリクス

| 提案 | 優先度 | 工数見積 | 依存関係 | なろう度 |
|------|--------|----------|----------|----------|
| 1. ペット契約絆システム | P0 | 3日 | 既存ペットシステム | ★★★★★ |
| 2. ペット進化分岐システム | P0 | 4日 | 提案1 | ★★★★★ |
| 3. ペット遺伝子融合・新種創造 | P1 | 4日 | 提案1,2 | ★★★★★ |
| 4. ペット血統・遺伝システム | P1 | 3日 | 提案1 | ★★★★☆ |
| 5. ペットシナジー・コンボシステム | P1 | 3日 | 提案1 | ★★★★☆ |
| 6. ペット装備・ギアシステム | P2 | 3日 | 提案1 | ★★★★☆ |
| 7. ペット訓練・忠誠度システム | P2 | 3日 | 提案1 | ★★★★☆ |
| 8. ペットギルド・フェローシップシステム | P2 | 4日 | 提案1 | ★★★★☆ |
| 9. ペットレガシー・転生ボーナスシステム | P2 | 3日 | 提案1,8 | ★★★★★ |

---

## 既存コードとの統合ポイント

### entity.py への追加・変更フィールド
```python
# PetAIクラス内（既存クラスの拡張）
class PetAI:
    # ... 既存フィールド ...
    bond: int = 0  # 契約絆度 (0-1000)
    contract_id: str = "default"  # 現在の契約タイプ
    evolution_path: List[str] = field(default_factory=list)  # 進化履歴
    evolution_stage: int = 0  # 現在の進化段階
    bloodline: Optional[str] = None  # 血統タイプ
    bloodline_purity: float = 0.0  # 血統純度 (0.0-1.0)
    equipment: Dict[str, str] = field(default_factory=dict)  # スロット -> アイテムID
    recent_pet_skills: List[Tuple[str, int]] = field(
        default_factory=list
    )  # (スキルID, ターン数)
    training_progress: Dict[str, int] = field(default_factory=list)  # コースID -> 進捗%


# Entityクラス内
class Entity:
    # ... 既存フィールド ...
    pets: List["Entity"] = field(default_factory=list)  # 既存フィールドを拡張使用
    pet_fusion_history: List[Dict] = field(default_factory=list)  # 融合記録
    completed_pet_training: List[str] = field(default_factory=list)  # 修了コース
    pet_guild_id: Optional[str] = None  # 所属ペットギルド
    pet_guild_role: Optional[str] = None  # ギルド内役職
    pet_legacy_flags: Dict[str, bool] = field(
        default_factory=dict
    )  # レガシー条件フラグ
```

### 統合フロー
1. **ペットとのインタラクション時** (`game.py:talk_to_neighbor` で ペット判定) → 絆度増加・プレゼント効果適用
2. **ペットと共闘時** (`game.py:_pet_ai` と 戦闘処理) → 絆度増加・経験値共有・コンボ判定
3. **ペット訓練施設利用時** (`game.py:施設特有アクション`) → トレーニング進行・完了チェック・報酬付与
4. **ペット進化条件チェック時** (`game.py:_pet_ai` の定期チェック) → 進化可能判定・進化実行・外観変更
5. **ペット融合施設利用時** (`game.py:融合施設アクション`) → 融合条件判定・新種創造・親ペット消去
6. **ペット装備変更時** (`game.py:ペットとの交流メニュー`) → 装備・外装変更・ステータス再計算
7. **ペットギルド施設利用時** (`game.py:ペットギルド特有アクション`) → ギルド貢献度増加・施設解放・ギルドバフ適用
8. **転生時** (`reincarnation_system.py:転生処理`) → ペットレガシー評価・引き継ぎ選択・初期状態設定
9. **ステータス再計算時** (`entity.py:recalculate_stats`) → ペット装備・契約・血統・ギルド効果をペットステータスに適用
10. **セーブ/ロード時** (`advanced_systems.py:SaveSystem`) → 全ペット関連データ（絆度・進化・血統・装備・履歴等）永続化

---

## 次のステップ

この提案書に基づき、以下の順序で実装計画書（12ステップ分割）を作成可能：

1. **Step 1-2**: 基本データファイル作成（pet_contracts.yaml, pet_evolutions.yaml）
2. **Step 3**: Entity拡張（ペット関連フィールド追加・PetAIクラス拡張）
3. **Step 4**: PetContractRegistry/Manager実装
4. **Step 5**: PetEvolutionRegistry/Manager実装
5. **Step 6**: PetFusionRegistry/Manager実装
6. **Step 7**: PetBloodlineRegistry/Manager実装
7. **Step 8**: PetSynergyシステム実装
8. **Step 9**: PetEquipmentシステム実装
9. **Step 10**: PetTrainingシステム実装
10. **Step 11**: PetGuild・PetLegacyシステム実装
11. **Step 12**: ゲームループ統合・セーブ/ロード対応・UI実装・テスト