# スキルツリー・ジョブシステム 詳細提案書

## 概要
なろう系要素「スキルツリー・ジョブシステム」をElonaに統合するための9つの具体的提案。既存のスキルシステム（`entity.py`のSkillクラス、`systems.py`のCombatSystem）を拡張し、階層型スキルツリー・ジョブチェンジ・専用スキルを実現。

---

## 提案1: 階層型スキルツリー（データ駆動型）

### 概要
スキルを「基礎→応用→極意」の3階層に構造化し、前提スキル習得で次の階層が解放されるシステム。

### データ構造（`data/skill_trees.yaml`）
```yaml
skill_trees:
  sword:
    name: "剣術"
    icon: "⚔"
    tiers:
      - id: "basic_sword"
        name: "剣の基礎"
        description: "剣を振るう基本動作を習得"
        cost: 10
        prerequisites: []
        effects:
          - type: "damage_bonus"
            value: 5
            target: "melee"
      - id: "sword_mastery"
        name: "剣術熟練"
        description: "剣の扱いに慣れ、威力が上がる"
        cost: 30
        prerequisites: ["basic_sword"]
        effects:
          - type: "damage_bonus"
            value: 15
            target: "melee"
          - type: "unlock_skill"
            skill_id: "slash"
      - id: "sword_essence"
        name: "剣の極意"
        description: "剣と一体化し、真の剣士となる"
        cost: 100
        prerequisites: ["sword_mastery"]
        effects:
          - type: "damage_bonus"
            value: 30
            target: "melee"
          - type: "crit_chance"
            value: 10
          - type: "unlock_skill"
            skill_id: "blade_dance"
```

### 実装箇所
- 新規: `skill_tree_system.py` - SkillTreeRegistry, SkillTreeManager
- 既存: `entity.py` Entity.skills に `skill_tree_progress: Dict[str, List[str]]` 追加
- 既存: `game.py` レベルアップ時にスキルポイント付与、UIでツリー表示

---

## 提案2: ジョブシステム（クラスチェンジ）

### 概要
レベル・スキル・ステータス条件を満たすとジョブチェンジ可能。ジョブごとに専用スキル・ステータス補正・装備制限を持つ。

### データ構造（`data/jobs.yaml`）
```yaml
jobs:
  novice:
    name: "見習い"
    tier: 0
    description: "冒険の第一歩を踏み出したばかり"
    stat_modifiers: {}
    equipment_restrictions: {}
    exclusive_skills: []
    unlock_conditions: {}
  
  warrior:
    name: "戦士"
    tier: 1
    description: "剣と盾を極めし前衛の達人"
    stat_modifiers:
      strength: 10
      constitution: 5
      speed: -2
    equipment_restrictions:
      can_wear_heavy_armor: true
      can_use_shield: true
    exclusive_skills:
      - "shield_bash"
      - "taunt"
      - "whirlwind"
    unlock_conditions:
      level: 10
      skills:
        basic_sword: 30
        shield: 20
      stats:
        strength: 15
  
  swordmaster:
    name: "剣聖"
    tier: 2
    description: "剣の道を極めし者、一撃必殺の剣技を操る"
    stat_modifiers:
      strength: 20
      dexterity: 15
      speed: 5
    equipment_restrictions:
      can_wear_heavy_armor: false
      can_use_katana: true
    exclusive_skills:
      - "iaijutsu"
      - "zantetsuken"
      - "musou_ken"
    unlock_conditions:
      level: 30
      job: "warrior"
      skills:
        sword_mastery: 50
        sword_essence: 30
      stats:
        strength: 25
        dexterity: 20
  
  mage:
    name: "魔法使い"
    tier: 1
    description: "魔力を操り、多彩な呪文を駆使する"
    stat_modifiers:
      intelligence: 15
      will: 10
      constitution: -5
    equipment_restrictions:
      can_use_staff: true
      armor_penalty: 0.5
    exclusive_skills:
      - "fireball"
      - "magic_shield"
      - "teleport"
    unlock_conditions:
      level: 10
      skills:
        magic_basic: 30
        mana_control: 20
      stats:
        intelligence: 15
  
  archmage:
    name: "大賢者"
    tier: 2
    description: "魔法の真理に触れし者、禁忌の呪文さえ操る"
    stat_modifiers:
      intelligence: 30
      will: 20
      mana: 50
    equipment_restrictions:
      can_use_artifact_staff: true
    exclusive_skills:
      - "meteor"
      - "time_stop"
      - "wish"
    unlock_conditions:
      level: 30
      job: "mage"
      skills:
        advanced_magic: 50
        forbidden_knowledge: 30
      stats:
        intelligence: 30
```

### 実装箇所
- 新規: `job_system.py` - JobRegistry, JobManager
- 既存: `entity.py` Entity に `job: str`, `job_level: int`, `previous_jobs: List[str]` 追加
- 既存: `entity.py` recalculate_stats() でジョブ補正適用
- 既存: `game.py` ジョブチェンジUI、レベルアップ時判定

---

## 提案3: ジョブ専用スキル（エクスクルーシブスキル）

### 概要
特定ジョブのみ習得可能な強力スキル。ジョブチェンジで失うが、マスターすると「継承スキル」として永続化。

### データ構造（`data/exclusive_skills.yaml`）
```yaml
exclusive_skills:
  shield_bash:
    name: "シールドバッシュ"
    job: "warrior"
    type: "active"
    mp_cost: 10
    cooldown: 3
    description: "盾で敵を殴打し、スタンさせる"
    effects:
      - type: "damage"
        formula: "str * 1.5"
      - type: "status"
        effect: "stun"
        duration: 2
        chance: 0.7
    inherit_chance: 0.3  # マスター時の継承確率
  
  iaijutsu:
    name: "居合術"
    job: "swordmaster"
    type: "active"
    mp_cost: 20
    cooldown: 5
    description: "鞘から抜く瞬間に極限の一撃を放つ"
    effects:
      - type: "damage"
        formula: "dex * 3 + str"
      - type: "crit_guaranteed"
      - type: "ignore_defense"
    inherit_chance: 0.2
  
  meteor:
    name: "メテオ"
    job: "archmage"
    type: "active"
    mp_cost: 100
    cooldown: 10
    description: "隕石を呼び寄せ、広範囲を焼き尽くす"
    effects:
      - type: "aoe_damage"
        radius: 5
        formula: "int * 5"
        element: "fire"
      - type: "status"
        effect: "burn"
        duration: 5
    inherit_chance: 0.1
```

### 実装箇所
- 既存: `skill_tree_system.py` に ExclusiveSkillManager 追加
- 既存: `entity.py` に `mastered_exclusive_skills: List[str]`, `inherited_skills: List[str]` 追加
- 既存: `systems.py` CombatSystem に専用スキル処理追加

---

## 提案4: スキル融合・派生システム

### 概要
異なるスキルツリーのスキルを組み合わせて新スキルを生成。「剣術×魔法＝魔剣術」のようななろう系定番要素。

### データ構造（`data/skill_fusion.yaml`）
```yaml
fusions:
  spellblade:
    name: "魔剣術"
    description: "剣に魔力を宿し、属性斬撃を放つ"
    required_skills:
      - "sword_mastery"
      - "magic_basic"
    result_skills:
      - "elemental_slash"
      - "mana_blade"
    bonus_effects:
      - type: "elemental_damage"
        value: 20
  
  holy_knight:
    name: "聖騎士"
    description: "信仰と剣技を融合、聖なる剣を振るう"
    required_skills:
      - "sword_mastery"
      - "faith_basic"
    required_job: "warrior"
    required_god: "jure"
    result_skills:
      - "holy_slash"
      - "divine_shield"
    bonus_effects:
      - type: "damage_vs_undead"
        value: 50
      - type: "heal_on_kill"
        value: 10
  
  shadow_assassin:
    name: "影の暗殺者"
    description: "隠密と短剣術を極め、闇に溶け込む"
    required_skills:
      - "dagger_mastery"
      - "stealth_mastery"
    required_job: "rogue"
    result_skills:
      - "shadow_step"
      - "assassinate"
    bonus_effects:
      - type: "crit_chance"
        value: 25
      - type: "backstab_multiplier"
        value: 3.0
```

### 実装箇所
- 新規: `skill_fusion_system.py` - FusionRegistry, FusionManager
- 既存: `entity.py` に `fused_skills: List[str]` 追加
- 既存: `game.py` 融合UI、条件判定

---

## 提案5: スキル進化・覚醒システム

### 概要
スキルを極限まで鍛えると「覚醒」し、効果が質的に変化。使用回数・レベル・特定条件でトリガー。

### データ構造（`data/skill_awakening.yaml`）
```yaml
awakenings:
  fireball:
    name: "ファイアボール覚醒：プロミネンス"
    base_skill: "fireball"
    condition:
      type: "usage_count"
      value: 500
    effects:
      - type: "replace_skill"
        new_skill: "prominence"
      - type: "add_effect"
        effect: "burn_ground"
        duration: 5
  
  slash:
    name: "斬撃覚醒：無双斬り"
    base_skill: "slash"
    condition:
      type: "critical_kills"
      value: 100
    effects:
      - type: "replace_skill"
        new_skill: "musou_zangeki"
      - type: "add_effect"
        effect: "multi_hit"
        count: 3
  
  heal:
    name: "ヒール覚醒：女神の祝福"
    base_skill: "heal"
    condition:
      type: "total_healing"
      value: 10000
    effects:
      - type: "replace_skill"
        new_skill: "goddess_blessing"
      - type: "add_effect"
        effect: "auto_revive"
        chance: 0.1
```

### 実装箇所
- 既存: `skill_tree_system.py` に AwakeningManager 追加
- 既存: `entity.py` に `skill_usage_counts: Dict[str, int]`, `awakened_skills: List[str]` 追加
- 既存: `systems.py` スキル使用時にカウント更新・覚醒判定

---

## 提案6: パッシブスキル・常時効果システム

### 概要
アクティブスキルとは別に、習得するだけで常時発動するパッシブスキル。ステータス補正・耐性・特殊効果を持つ。

### データ構造（`data/passive_skills.yaml`）
```yaml
passive_skills:
  iron_body:
    name: "鉄の肉体"
    tree: "constitution"
    tier: 2
    cost: 20
    prerequisites: ["basic_constitution"]
    effects:
      - type: "max_hp_bonus"
        value: 50
      - type: "physical_resistance"
        value: 10
      - type: "knockback_resistance"
        value: 0.5
  
  mana_efficiency:
    name: "魔力効率化"
    tree: "magic"
    tier: 2
    cost: 20
    prerequisites: ["magic_basic"]
    effects:
      - type: "mp_cost_reduction"
        value: 0.2
      - type: "mp_regen_bonus"
        value: 2
  
  lucky_find:
    name: "幸運な発見"
    tree: "luck"
    tier: 3
    cost: 50
    prerequisites: ["fortune_favor"]
    effects:
      - type: "item_find_rate"
        value: 0.3
      - type: "rare_drop_rate"
        value: 0.15
      - type: "trap_detection"
        value: 5
  
  death_defiance:
    name: "死者の抗い"
    tree: "survival"
    tier: 3
    cost: 100
    prerequisites: ["survivor_instinct"]
    effects:
      - type: "auto_revive"
        chance: 0.05
        hp_percent: 0.3
      - type: "death_exp_bonus"
        value: 2.0
```

### 実装箇所
- 既存: `skill_tree_system.py` に PassiveSkillManager 追加
- 既存: `entity.py` recalculate_stats() でパッシブ効果集計適用
- 既存: `systems.py` SurvivalSystem, CombatSystem でパッシブ効果参照

---

## 提案7: スキル継承・輪廻転生ボーナス

### 概要
転生（ニューゲーム+）時に、マスターしたスキル・ジョブを「継承」し、次周でボーナスとして開始できる。

### データ構造（`data/skill_inheritance.yaml`）
```yaml
inheritance:
  rules:
    - name: "ジョブ継承"
      condition: "job_mastered"
      effect:
        type: "start_with_job"
        value: "previous_job"
      cost: 5  # 継承ポイント消費
    
    - name: "スキル継承"
      condition: "skill_mastered"
      effect:
        type: "start_with_skill"
        value: "skill_id"
      cost: 3
    
    - name: "覚醒スキル継承"
      condition: "skill_awakened"
      effect:
        type: "start_with_awakened_skill"
        value: "skill_id"
      cost: 10
    
    - name: "ステータス継承"
      condition: "level_100"
      effect:
        type: "base_stat_bonus"
        value: 10
      cost: 20
  
  inheritance_points:
    base: 10
    per_10_levels: 2
    per_mastered_job: 5
    per_awakened_skill: 10
```

### 実装箇所
- 新規: `reincarnation_system.py` - InheritanceManager
- 既存: `advanced_systems.py` SaveSystem に継承データ保存追加
- 既存: `game.py` 新規ゲーム開始時の継承選択UI

---

## 提案8: スキルシナジー・コンボシステム

### 概要
特定スキルの組み合わせ使用で追加効果発動。「ファイアボール→風魔法＝火炎竜巻」のようなコンボ。

### データ構造（`data/skill_synergy.yaml`）
```yaml
synergies:
  fire_tornado:
    name: "火炎竜巻"
    skills: ["fireball", "wind_blade"]
    window: 3  # ターン数
    effect:
      - type: "aoe_damage"
        radius: 3
        formula: "(int + dex) * 2"
        element: "fire_wind"
      - type: "status"
        effect: "burn"
        duration: 3
  
  holy_nova:
    name: "ホーリーノヴァ"
    skills: ["holy_slash", "heal"]
    window: 2
    effect:
      - type: "heal_allies"
        radius: 5
        formula: "will * 3"
      - type: "damage_enemies"
        radius: 5
        formula: "str * 2"
        element: "holy"
  
  shadow_clone:
    name: "影分身の術"
    skills: ["shadow_step", "dagger_throw"]
    window: 1
    effect:
      - type: "summon_clone"
        count: 3
        duration: 5
        stats_multiplier: 0.5
```

### 実装箇所
- 新規: `skill_synergy_system.py` - SynergyManager
- 既存: `entity.py` に `recent_skills: List[Tuple[str, int]]` 追加（スキルID, ターン数）
- 既存: `systems.py` CombatSystem でシナジー判定・発動

---

## 提案9: スキル習得ビジュアライゼーション・UI

### 概要
スキルツリーを視覚的に表示し、習得進捗・前提関係・ジョブ解放条件を一目で把握できるUI。

### UI仕様
```
┌─ 剣術ツリー ────────────────────────────────────┐
│ [●] 剣の基礎 (Lv.3/3)  ★習得済み                │
│   └─ 効果: 近接ダメージ +5                      │
│                                                 │
│ [●] 剣術熟練 (Lv.2/5)  ▓▓░░░░░░░░ 40%          │
│   ├─ 前提: 剣の基礎 ★                          │
│   └─ 効果: 近接ダメージ +15, 斬撃解放           │
│                                                 │
│ [○] 剣の極意 (Lv.0/10) ░░░░░░░░░░  0%          │
│   ├─ 前提: 剣術熟練 (Lv.5必要) 🔒              │
│   └─ 効果: 近接ダメージ +30, 会心+10%, 無双斬り│
│                                                 │
│ 💡 ジョブ「戦士」解放条件:                      │
│    - Lv.10以上  ✓                              │
│    - 剣の基礎 Lv.3  ✓                          │
│    - 盾スキル Lv.2  ▓▓░░░░░░░░ 40%             │
│    - 腕力 15以上  ✓                            │
└────────────────────────────────────────────────┘
```

### 実装箇所
- 新規: `ui_skill_tree.py` - SkillTreeRenderer
- 既存: `game.py` render_all() にスキルツリー画面追加（Sキー）
- 既存: `ui_fx_systems.py` にツリーアニメーション追加

---

## 実装優先度マトリクス

| 提案 | 優先度 | 工数見積 | 依存関係 | なろう度 |
|------|--------|----------|----------|----------|
| 1. 階層型スキルツリー | P0 | 3日 | なし | ★★★★★ |
| 2. ジョブシステム | P0 | 4日 | 提案1 | ★★★★★ |
| 3. ジョブ専用スキル | P1 | 2日 | 提案2 | ★★★★★ |
| 4. スキル融合 | P1 | 3日 | 提案1,2 | ★★★★☆ |
| 5. スキル覚醒 | P2 | 2日 | 提案1 | ★★★★☆ |
| 6. パッシブスキル | P1 | 2日 | 提案1 | ★★★☆☆ |
| 7. 継承・輪廻転生 | P2 | 3日 | 提案2,5 | ★★★★★ |
| 8. シナジー・コンボ | P2 | 2日 | 提案1,3 | ★★★★☆ |
| 9. UIビジュアライゼーション | P1 | 3日 | 提案1,2 | ★★★☆☆ |

---

## 既存コードとの統合ポイント

### entity.py への追加フィールド
```python
@dataclass
class Entity:
    # ... 既存フィールド ...
    
    # スキルツリー関連
    skill_tree_progress: Dict[str, List[str]] = field(default_factory=dict)  # tree_id -> [unlocked_skill_ids]
    skill_points: int = 0
    total_skill_points_earned: int = 0
    
    # ジョブ関連
    job: str = "novice"
    job_level: int = 1
    job_exp: int = 0
    previous_jobs: List[str] = field(default_factory=list)
    mastered_jobs: List[str] = field(default_factory=list)
    
    # 専用・継承スキル
    mastered_exclusive_skills: List[str] = field(default_factory=list)
    inherited_skills: List[str] = field(default_factory=list)
    fused_skills: List[str] = field(default_factory=list)
    awakened_skills: List[str] = field(default_factory=list)
    
    # パッシブ・シナジー
    learned_passive_skills: List[str] = field(default_factory=list)
    recent_skills: List[Tuple[str, int]] = field(default_factory=list)  # (skill_id, turn)
    
    # 継承ポイント
    inheritance_points: int = 0
```

### 統合フロー
1. **レベルアップ時** (`entity.py:gain_exp`) → スキルポイント付与
2. **スキル使用時** (`systems.py:CombatSystem.cast_spell`) → 使用カウント更新、覚醒判定、シナジー判定
3. **ターン経過時** (`game.py:advance_world`) → ジョブ経験値加算、ジョブチェンジ判定
4. **ステータス再計算時** (`entity.py:recalculate_stats`) → ジョブ補正、パッシブ効果、装備補正を統合適用
5. **セーブ/ロード時** (`advanced_systems.py:SaveSystem`) → 全スキルツリー・ジョブデータ永続化

---

## 次のステップ

この提案書に基づき、以下の順序で実装計画書（12ステップ分割）を作成可能：

1. **Step 1-2**: データファイル作成（skill_trees.yaml, jobs.yaml）
2. **Step 3**: Entity拡張（フィールド追加）
3. **Step 4**: SkillTreeRegistry/Manager実装
4. **Step 5**: JobRegistry/Manager実装
5. **Step 6**: スキルポイント・習得ロジック
6. **Step 7**: ジョブチェンジ判定・適用
7. **Step 8**: 専用スキル・継承システム
8. **Step 9**: スキル融合・覚醒システム
9. **Step 10**: パッシブ・シナジーシステム
10. **Step 11**: UI実装（スキルツリー画面、ジョブ画面）
11. **Step 12**: セーブ/ロード統合・テスト