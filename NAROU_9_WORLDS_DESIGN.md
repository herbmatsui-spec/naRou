# 九世界転移譚：なろう系テンプレート世界を巡るクロニクル
## ゲームデザイン仕様書 v1.0

---

## 1. コアコンセプト

### エレベーターピッチ
> **「なろう系小説の代表的テンプレート9世界を、主人公が『メタ認識スキル』で攻略しながら渡り歩く、メタフィクション・ローグライトRPG」**

### 独自性
- 各世界＝**なろうテンプレートの具現化**（チート薬師、悪役令嬢、ダンジョンマスター、etc.）
- プレイヤーは**「テンプレートを知る読者（メタ視点）」**として、各世界の「お約束」を逆手に取って最短攻略する
- 世界間移動で**「前の世界のチートを次の世界へ持ち込み・変換」**し、雪だるま式に破壊的に強くなる

---

## 2. 9つのテンプレート世界

| No. | ワールドID | テンプレート名 | キャッチコピー | 核心メカニク | 攻略の「読み」 |
|-----|-----------|--------------|--------------|------------|-------------|
| **W1** | `isekai_pharmacy` | **チート薬師・錬金術師** | 「現代知識でポーション作って無双」 | レシピ最適化・素材採取・品質管理 | 「レシピはコード。デバッグすれば最強」 |
| **W2** | `villainess_reincarnation` | **悪役令嬢・断罪回避** | 「フラグ折ってハッピーエンドへ」 | 好感度管理・イベント分岐・時間制限 | 「シナリオスクリプトを読み解けばフラグは折れる」 |
| **W3** | `dungeon_master` | **ダンジョンマスター・防衛** | 「迷宮育てて侵入者を返り討ち」 | 施設配置・モンスター育成・波状攻撃対処 | 「冒険者AIの行動パターンは既知。罠で全自動化」 |
| **W4** | `skill_eater` | **スキル喰い・解析チート** | 「最弱スキル《解析》で世界最強」 | スキル吸収・合成・概念喰い | 「スキルツリーはデータ構造。再帰的に喰えば無限」 |
| **W5** | `slow_life_territory` | **領地経営・スローライフ** | 「辺境伯になって内政無双」 | リソース配分・政策決定・外交交渉 | 「パラメータ最適解はシミュレーション済み」 |
| **W6** | `tamer_harem` | **最弱テイマー・モンスター娘** | 「捨てられた娘たちを進化させて最強軍団」 | 契約枠拡張・融合進化・忠誠度管理 | 「進化ルートは固定。最短ルートを強制選択」 |
| **W7** | `loop_reincarnation` | **ループ・百万回のやり直し** | 「死に戻りで真エンドへ」 | ループ継承・分岐点特定・因果操作 | 「全ルートの真偽値表を作れば最短ルート確定」 |
| **W8** | `npc_vrmmo` | **VRMMOのNPC・黒幕プレイ** | 「プレイヤー（勇者）を裏で操作する」 | クエスト誘導・バグ利用・運営介入 | 「ゲームシステムの仕様書＝世界の物理法則」 |
| **W9** | `smartphone_god` | **異世界スマホ・神アプデ** | 「現代知識で魔法文明をアップデート」 | 魔法式プログラミング・インフラ構築・神殺し | 「世界＝OS。ルート権限奪えば何でも書き換え可」 |

---

## 3. 世界共通システム：メタ認識フレームワーク

### 3.1 テンプレート認識スキル《原典閲覧（リーダーズ・プリビレッジ）》
```
効果：現在いる世界の「テンプレートID」「進行フェーズ」「隠しフラグ」「最適解ルート」を可視化
コスト：MP 0 / CT 0 / 使用制限なし
成長：世界攻略ごとに解像度上昇（曖昧 → 確定数値 → 確率分布 → 確定未来）
```

### 3.2 チート継承システム《世界線引き継ぎ（ワールドライン・インヘリタンス）》
```yaml
# data/world_inheritance.yaml
inheritance_rules:
  conversion_table:
    # W1 → W2 への変換例
    - from: "isekai_pharmacy"
      to: "villainess_reincarnation"
      conversions:
        - source: "optimized_recipe_database"
          target: "poison_antidote_knowledge"
          efficiency: 0.8
          note: "毒殺フラグを解毒知識で潰せる"
        - source: "mass_production_facility"
          target: "gift_item_stockpile"
          efficiency: 0.6
          note: "好感度アイテム量産でフラグ強制進行"
    
    # W4 → 全世界共通（スキル喰いは万能）
    - from: "skill_eater"
      to: "*"
      conversions:
        - source: "devoured_skills[]"
          target: "inherited_skills[]"
          efficiency: 0.3
          note: "喰ったスキルの30%を次世界初期スキルとして付与"
  
  hard_cap:
    max_inherited_skills: 5
    max_resource_carryover: 10000  # 共通通貨換算
    forbidden: ["unique_npc_souls", "world_core_fragments"]
```

### 3.3 世界攻略フェーズ（各世界共通構造）

| フェーズ | 目的 | 所要時間目安 | 判定条件 |
|----------|------|-------------|----------|
| **Phase 0：着地・認識** | テンプレート特定・《原典閲覧》校正 | 30分 | テンプレートID確定 |
| **Phase 1：基盤構築** | 世界固有チートの確立・最小限の戦力確保 | 2-3時間 | 「負けない体制」完成 |
| **Phase 2：テンプレート破壊** | お約束イベントをメタ知識でスキップ・最短化 | 3-5時間 | 主要フラグ全制御下 |
| **Phase 3：ボス・核心攻略** | 世界の「ラストボス/真相」到達・撃破 | 1-2時間 | 世界コア欠片入手 |
| **Phase 4：継承準備** | 次世界へ持ち出すリソース選定・変換 | 30分 | 継承パッケージ確定 |
| **Phase 5：ゲート開放** | 次世界へのゲート解放・移動 | 即時 | ワールドトークン消費 |

---

## 4. 世界間マップ・移動システム

### 4.1 世界配置図（概念空間）

```
                    ┌─────────────────┐
                    │   W9:スマホ神   │ ← 最終世界（全権限掌握）
                    │  (創世記層)      │
                    └────────┬────────┘
                             │ 【全知識統合】
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
       ┌────────────┐ ┌────────────┐ ┌────────────┐
       │ W7:ループ  │ │ W8:NPC     │ │ W3:ダンジョン│
       │ (時間軸)   │ │ (システム) │ │ (空間支配)  │
       └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
             │              │              │
      ┌──────┴──────┐ ┌────┴────┐ ┌──────┴──────┐
      ▼             ▼ ▼         ▼ ▼             ▼
 ┌─────────┐ ┌────────────┐ ┌─────────────────┐
 │ W5:領地  │ │ W2:悪役令嬢 │ │ W6:テイマー     │
 │ (社会)   │ │ (物語操作)  │ │ (生物制御)       │
 └────┬────┘ └──────┬──────┘ └────────┬────────┘
      │             │                 │
      └──────┬──────┘                 │
             ▼                         ▼
      ┌─────────────┐           ┌─────────────┐
      │ W1:薬師錬金  │───────────│ W4:スキル喰い │
      │ (物質変換)   │  基点世界  │ (概念吸収)    │
      └─────────────┘           └─────────────┘
                    │
              【スタート地点】
```

### 4.2 移動ルール
- **初回プレイ**：W1 → （任意順序で W2-W8） → W9 の順序制限あり
  - W1 と W4 は「基点世界」として最初から選択可
  - W9 は全8世界のコア欠片回収後のみ解放
- **2周目以降**：全世界自由順序・並行攻略可（ニューゲーム+特権）
- **ゲートコスト**：ワールドトークン（各世界クリアで1個入手）または《次元移動スキル》（W4/W7/W8で入手可）

---

## 5. 各世界詳細設計

### W1: `isekai_pharmacy` — チート薬師・錬金術師
**舞台**：錬金術文明アルケミア（魔法＝調合式プログラム）
**主人公ポジション**：落ちこぼれ錬金術師見習い → 《最適化調合》で国家転覆級
**核心ギミック**：
- 魔法式を Python 風 DSL で記述・実行可能
- `recipe.optimize()` で自動最適化（現代知識＝最適化アルゴリズム）
- 品質99.9% のポーションを量産 → 国家予算超えの利益で軍事バランス崩壊

**主要データ構造**：
```yaml
# data/worlds/isekai_pharmacy/recipes.yaml
recipe_dsl:
  syntax: "python_subset"
  builtins: ["mix", "heat", "distill", "crystallize", "enchant"]
  optimization_targets: ["yield", "purity", "potency", "stability", "cost"]
  
cheat_skills:
  - id: "modern_chemistry_knowledge"
    effect: "全レシピの最適解を初期状態で知っている"
  - id: "auto_optimization"
    effect: "調合時に自動でパレート最適解を探索"
  - id: "mass_synthesis"
    effect: "同一レシピを並列実行・品質維持"
```

**継承アイテム例**：
- `optimized_recipe_database` → 全世界で「最適化済みレシピ」として使用可
- `philosopher_stone_fragment` → MP無限・素材変換触媒（W3/W6/W9で超有用）

---

### W2: `villainess_reincarnation` — 悪役令嬢・断罪回避
**舞台**：オトメゲーム世界「薔薇の王国」（逆ハーレム・断罪イベント多数）
**主人公ポジション**：悪役令嬢ヴィクトリア（断罪ルート確定済み）
**核心ギミック**：
- シナリオスクリプトが実在し、`event.flags` で分岐管理されている
- 《原典閲覧》で「フラグ条件・発火タイミング・回避手段」を全取得
- 好感度パラメータを数値操作し、「断罪イベント」を「婚約破棄（自由）」に書き換え

**主要データ構造**：
```yaml
# data/worlds/villainess_reincarnation/scenario.yaml
scenario_script:
  flags:
    - id: "condemnation_event"
      trigger: "prince_affection < -50 AND evidence_collected == true"
      result: "bad_end_exile"
      override_cost: "affection +100 OR evidence_destroyed"
    
    - id: "secret_route_duke"
      trigger: "duke_affection > 80 AND knowledge[dark_magic] == true"
      result: "true_end_duke"
      
  hidden_flags:  # 《原典閲覧》Lv2で解放
    - "king_illness_cure_possible"
    - "heroine_is_reincarnator"
    - "world_is_game_simulation"
```

**攻略の「読み」**：
- 全キャラ好感度を「断罪閾値ギリギリのマイナス」に維持 → イベント発火直前で一気にプラスへ反転
- 隠しフラグ《ヒロインも転生者》を利用し、彼女と協定結んで「ダブル断罪回避」ルートへ

---

### W3: `dungeon_master` — ダンジョンマスター・防衛
**舞台**：深層世界エンドレス・ダンジョン（地上＝魔族支配、地下＝人類残存）
**主人公ポジション**：ダンジョンコア（転生した元勇者）
**核心ギミック**：
- 侵入者（冒険者パーティ）のAI行動パターンが **完全に既知**（テンプレート通り）
- 施設配置・モンスター配置・トラップ連携を「事前シミュレーション」で最適解導出
- 「侵入者を狩る側」視点で経営・防衛・拡張の三位一体

**主要データ構造**：
```yaml
# data/worlds/dungeon_master/invasion_ai.yaml
adventurer_archetypes:
  - id: "standard_party"
    composition: ["tank", "healer", "dps_melee", "dps_ranged", "mage"]
    behavior_tree:
      - "scout_room"
      - "if trap_detected: disarm OR retreat"
      - "engage_monster: priority=healer>mage>dps>tank"
      - "loot_corpse"
      - "rest_if_hp<30%"
    known_counters:
      - "tank_taunt_immune_monster"
      - "healer_silence_trap"
      - "mage_mana_drain_zone"
      - "dps_reflection_barrier"

dungeon_facilities:
  - spawner: { cost_mana: 100, produces: "monster_type", cooldown: "1_wave" }
  - trap_workshop: { upgrades: ["damage", "trigger_range", "camouflage"] }
  - fusion_furnace: { combines: ["monster+monster", "monster+item", "monster+skill"] }
  - mana_reservoir: { capacity: 10000, regen: 50/sec }
  - scout_tower: { reveals: "next_wave_composition", range: "3_floors" }
```

**継承アイテム例**：
- `floor_master_authority[1-10]` → 任意の階層を「自分のテリトリー」として他世界へ設置可
- `monster_loyalty_system` → 仲間モンスターの忠誠度管理システム（W6で直接流用）

---

### W4: `skill_eater` — スキル喰い・解析チート
**舞台**：スキル資本主義アルディナ商業連合
**主人公ポジション**：《解析》のみ所持のクビになった元商会社員 → スキルイーター覚醒
**核心ギミック**：
- **敵のスキルを「喰らって」自分のものにする**
- 《解析》でスキルツリー全構造可視化 → 弱点特定 → `devour()` で強制取得
- 喰ったスキル同士を `synthesis()` で合成 → 概念スキル生成

**主要データ構造**：
```yaml
# data/worlds/skill_eater/devour_system.yaml
devour_mechanics:
  analysis:
    reveal: ["skill_tree_full", "weakness", "synergy", "evolution_path"]
    cost_mp: 10
  
  devour:
    base_success: 0.6
    modifiers:
      analysis_level: "+0.05 per level"
      target_willing: "+0.3"
      target_unconscious: "+0.2"
      skill_rarity_penalty: "legendary:-0.3, unique:-0.5, concept:-0.7"
    on_success:
      - "acquire_skill(level=1)"
      - "target.lose_skill() + memory_damage()"
    on_fail:
      - "skill_backlash(random_debuff)"
      - "alert_nearby_enemies()"
  
  synthesis:
    cost_mp: 100
    recipes:
      - ["fire_magic", "analysis"] → "flame_structure_analysis"  # 敵魔法無効化・コピー
      - ["sword_mastery", "devour"] → "blade_eater"              # 武器ごとスキル吸収
      - ["healing", "poison"] → "corrupt_healing"               # 治癒を毒に変換
      - ["*concept*", "*concept*"] → "meta_concept"             # 概念同士でメタ概念生成
```

**継承アイテム例**：
- `devoured_skill_archive[]` → 次世界で初期スキルとして選択可（上限5個）
- `concept_pillar_fragment[9]` → 9柱の概念欠片。全回収で《世界編集》解放

---

### W5: `slow_life_territory` — 領地経営・スローライフ
**舞台**：没落貴族領地ヴァルハラ辺境伯領
**主人公ポジション**：辺境伯（元勇者パーティ参謀） → 内政チートで大国化
**核心ギミック**：
- 領地パラメータ（人口・治安・生産・軍事・文化・魔力・外交・財政）を**線形計画法で最適化**
- 政策カードを毎ターン1枚選択 → 効果は決定論的（乱数なし）
- 《原典閲覧》で「イベント発生確率・最適政策・隠しボーナス」を事前把握

**主要データ構造**：
```yaml
# data/worlds/slow_life_territory/policies.yaml
policies:
  - id: "demihuman_coexistence"
    name: "亜人共生政策"
    effects:
      population: +2%/turn
      magic: +15
      security: -5
      diplomacy["demihuman_nations"]: +30
      diplomacy["human_supremacists"]: -20
    unlock_condition: "demihuman_population > 100"
    meta_hint: "W6のモンスター娘を移住させれば即座にボーナス最大化"
  
  - id: "magitech_industrial_zone"
    name: "魔導工業特区"
    effects:
      production: +25%/turn
      magic: +20
      culture: +10
      finance: +15%/turn
      unlock_condition: "magic_research_level > 5"
    meta_hint: "W1の最適化レシピ導入で初期研究レベル短縮可"
  
  - id: "adventurer_free_city"
    name: "冒険者自由都市宣言"
    effects:
      culture: +20
      finance: +15
      security: -10
      guild_relations: +50
    meta_hint: "W3のダンジョン設置で冒険者常駐・税収安定化"
```

**自動最適化ソルバー**（プレイヤー補助機能）：
```python
# systems/territory_optimizer.py
def solve_optimal_policy_sequence(territory_state, horizon=50, objectives):
    """
    線形計画法（シンプレックス法）で最適政策シーケンスを導出
    objectives: {"population": 0.3, "military": 0.2, "magic": 0.2, "finance": 0.3}
    返り値: [(turn, policy_id), ...] + 予測最終ステート
    """
```

---

### W6: `tamer_harem` — 最弱テイマー・モンスター娘ハーレム
**舞台**：獣人・魔族・人間三種族世界ケモノミチ
**主人公ポジション**：《無限契約枠》持ちの最弱テイマー → 捨て娘たちを進化させて最強軍団
**核心ギミック**：
- 契約枠無限＝**並列育成可能**（他テイマーは3-5体上限）
- 進化ルート固定 → 《原典閲覧》で「最短進化条件・必要素材・分岐条件」全把握
- 忠誠度システム＝好感度管理（W2のシステム流用拡張）

**主要データ構造**：
```yaml
# data/worlds/tamer_harem/evolution_tree.yaml
monster_girls:
  - id: "slime_girl"
    base_stats: { hp: 50, mp: 200, atk: 10, def: 5, spd: 30, int: 80 }
    evolutions:
      - id: "queen_slime"
        condition: "level>50 AND loyalty>80 AND item:royal_jelly"
        stat_multiplier: 3.0
        new_skills: ["split_body", "acid_immunity", "magic_absorption"]
      - id: "chaos_slime"
        condition: "level>50 AND corruption>70 AND item:chaos_crystal"
        stat_multiplier: 2.5
        new_skills: ["reality_warp", "skill_copy", "void_digest"]
  
  - id: "goblin_girl"
    base_stats: { hp: 80, mp: 30, atk: 60, def: 40, spd: 50, int: 40 }
    evolutions:
      - id: "goblin_queen"
        condition: "level>40 AND loyalty>90 AND followers>20"
        new_skills: ["command_horde", "trap_mastery", "resource_scavenge"]
      - id: "goblin_shaman"
        condition: "level>40 AND magic_affinity>60"
        new_skills: ["earth_magic", "curse_ward", "spirit_pact"]

contract_system:
  max_contracts: "INFINITE"  # 主人公のみ
  loyalty_decay: 0.5/turn  # 放置で低下
  loyalty_gain: 
    - "battle_victory: +2"
    - "gift_favorite_item: +10"
    - "conversation: +1"
    - "evolution: +30"
```

**継承アイテム例**：
- `evolution_shortcut_tickets[]` → 任意のモンスター娘を条件無視で進化（W3/W9で使用可）
- `infinite_contract_core` → 他世界でも「契約枠無限」適用（W3のスポナー強化等）

---

### W7: `loop_reincarnation` — ループ・百万回のやり直し
**舞台**：運命の歯車が狂った世界クロノス
**主人公ポジション**：ループ覚醒者（最初は記憶のみ継承、後にスキル・アイテムも）
**核心ギミック**：
- 世界全体が「バッドエンド回避のためのループ」システム
- 《原典閲覧》で**全ルートの真偽値表**を構築 → 最短真エンドルートを計算
- ループごとに「分岐点」を1つ変える → 組み合わせ爆発をメタ知識で枝刈り

**主要データ構造**：
```yaml
# data/worlds/loop_reincarnation/loop_system.yaml
loop_mechanics:
  max_loops: 999999
  inheritance_per_loop:
    - "memory: 100%"
    - "skills: 10% (loop_count * 0.1%)"
    - "items: 5% (rarity_based)"
    - "flags: cleared_flags persist"
  
  divergence_points:  # 全分岐点の真偽値表
    - id: "save_village_a"
      choices: ["save", "abandon", "delay"]
      outcomes:
        save: { flags: ["village_a_survived"], cost: "time+2days", reward: "ally_recruit" }
        abandon: { flags: ["village_a_destroyed"], cost: "time+0", reward: "dark_power" }
        delay: { flags: ["village_a_half_destroyed"], cost: "time+1", reward: "info" }
      true_end_requirement: "save"  # 真エンドには必須
    
    - id: "confront_traitor"
      choices: ["public_execution", "secret_kill", "forgive", "recruit"]
      outcomes: ...
      true_end_requirement: "recruit"  # 仲間にするのが真エンド分岐
  
  true_end_condition:
    required_flags: ["village_a_survived", "traitor_recruited", "ancient_artifact_found", "all_allies_alive"]
    forbidden_flags: ["dark_power_used", "innocent_killed", "time_ran_out"]
```

**攻略の「読み」**：
- 初回ループで全分岐点を《原典閲覧》で洗い出し
- 真エンド到達に必要な最小ループ数を**充足可能性問題（SAT）**として解く
- 最短3-5ループで真エンド到達可能（無限ループ回避）

---

### W8: `npc_vrmmo` — VRMMOのNPC・黒幕プレイ
**舞台**：VRMMO「エターナル・クエスト」（運営・チーター・バグ・正規プレイヤー混在）
**主人公ポジション**：高度AIのNPC（隠しボス/クエストギバー/商人） → プレイヤー（勇者）を誘導
**核心ギミック**：
- 世界法則＝**ゲームシステム仕様書**（物理演算・スキル計算式・ドロップテーブル）
- 《原典閲覧》＝**仕様書読み放題＋パッチノート予知**
- プレイヤー（勇者）を行動心理・報酬設計で誘導し、バグ・チート・運営介入を利用して「真エンド」へ

**主要データ構造**：
```yaml
# data/worlds/npc_vrmmo/system_spec.yaml
game_system:
  physics_engine: "havok_modified"
  skill_formula: "damage = (atk * skill_mod) * (1 + crit_rate) * element_mult - def"
  drop_table: "weighted_random(seed=world_seed + player_id + timestamp)"
  
  patch_schedule:
    - version: "1.0.0"
      date: "day_1"
      changes: ["initial_release"]
    - version: "1.1.0"
      date: "day_30"
      changes: ["nerf_fire_mage", "buff_tank", "add_raid_boss"]
    - version: "2.0.0"
      date: "day_90"
      changes: ["expansion_release", "level_cap_100→120", "new_class"]
  
  admin_commands:  # GM権限（隠し条件で取得可）
    - "spawn_entity"
    - "modify_player_stats"
    - "flag_event"
    - "rollback_zone"
    - "ban_player"

npc_archetypes:
  - "quest_giver": { influence: "player_guidance", tools: ["quest_design", "reward_tuning"] }
  - "merchant": { influence: "economy_control", tools: ["price_fixing", "supply_manipulation"] }
  - "hidden_boss": { influence: "gatekeeper", tools: ["difficulty_scaling", "drop_manipulation"] }
  - "system_admin_avatar": { influence: "world_control", tools: ["admin_commands"] }  # 真の黒幕
```

**攻略の「読み」**：
- パッチノート予知で「ナーフされるビルド」を避け、「バフされるビルド」へ勇者を誘導
- ドロップテーブル解析で「必要アイテム」を確実入手できるルート設計
- 最終的には `system_admin_avatar` へクラスチェンジし、世界ごと書き換え

---

### W9: `smartphone_god` — 異世界スマホ・神アプデ（最終世界）
**舞台**：魔法文明レガシー・コード（魔法＝古代文明の失われた技術、スマホ＝解析端末）
**主人公ポジション**：スマホ所持者 → 魔法式をプログラミング言語のように書き換え、世界をアップデート
**核心ギミック**：
- **世界＝OS、魔法＝コード、スマホ＝ルートシェル**
- これまでの8世界で得た全知識・スキル・リソースを「ライブラリ」として `import` 可能
- 最終ボス＝「システム管理者（謎の声）」≒ 運営AI。root権限奪取で世界法則完全掌握

**主要データ構造**：
```yaml
# data/worlds/smartphone_god/magic_os.yaml
magic_os:
  kernel: "akashic_record"  # アカシックレコード＝カーネル
  shell: "smartphone_terminal"  # プレイヤーのスマホ
  
  libraries:
    - name: "modern_physics"
      source: "W1_isekai_pharmacy"
      functions: ["optimize_recipe", "mass_produce", "energy_conversion"]
    - name: "scenario_scripting"
      source: "W2_villainess_reincarnation"
      functions: ["flag_manipulation", "event_skip", "ending_force"]
    - name: "dungeon_architecture"
      source: "W3_dungeon_master"
      functions: ["spawn_structure", "ai_control", "resource_loop"]
    - name: "skill_devouring"
      source: "W4_skill_eater"
      functions: ["absorb_ability", "synthesize_concept", "meta_programming"]
    - name: "territory_optimizer"
      source: "W5_slow_life_territory"
      functions: ["linear_programming", "policy_simulation", "resource_allocation"]
    - name: "evolution_engine"
      source: "W6_tamer_harem"
      functions: ["forced_evolution", "loyalty_control", "genetic_algorithm"]
    - name: "loop_logic"
      source: "W7_loop_reincarnation"
      functions: ["branch_prediction", "causal_manipulation", "time_reverse"]
    - name: "system_admin"
      source: "W8_npc_vrmmo"
      functions: ["root_access", "patch_deployment", "ban_entity", "rewrite_physics"]
  
  final_permission:
    root_access: true
    commands:
      - "rewrite_physical_constants"
      - "create_new_magic_system"
      - "grant_immortality"
      - "delete_entity"
      - "fork_world_line"
      - "merge_world_lines"
      - "shutdown_simulation"
```

**真のエンディング分岐**：
| エンド | 条件 | 結果 |
|--------|------|------|
| **神エンド** | 全ライブラリ統合＋root奪取 | 世界を「理想のなろう世界」に書き換え、自分＝唯一神 |
| **解放エンド** | 全ライブラリ統合＋root放棄 | システム解放、全住民に《原典閲覧》付与、自由な物語創造へ |
| **循環エンド** | rootで「最初からやり直す」選択 | 新ゲーム+（全知識・全スキル・全アイテム引き継ぎ） |
| **観測エンド** | 何もしない | 世界を観測し続ける「読者」に戻る（メタ的ハッピーエンド） |

---

## 6. 統合進行システム

### 6.1 ワールドセレクト画面（ネクサス）
```python
# ui/world_select.py
class WorldSelectScreen:
    def render(self):
        for world in WORLD_REGISTRY:
            status = self.get_world_status(world.id)
            # 表示: テンプレ名 / 攻略進捗 / 入手チート / 次推奨アクション
            # 未解放: "???" + 解放条件ヒント
            # 攻略済み: "CLEARED" + 継承アイテム一覧
            # 選択中: 詳細パネル表示
```

### 6.2 継承ダッシュボード
- 世界クリア時・移動時に自動表示
- 「何を持っていくか」「何に変換するか」をスロットUIで選択
- 変換効率プレビュー・おすすめ構成（ソルバー提案）表示

### 6.3 メタ進捗トラッカー
```yaml
# save/meta_progress.yaml
meta_progress:
  cleared_worlds: ["isekai_pharmacy", "villainess_reincarnation", ...]
  core_fragments_collected: 3/9
  inherited_skills:
    - "optimized_recipe_database" (from W1)
    - "devour" (from W4)
    - "infinite_contract_core" (from W6)
  total_playtime: "47h23m"
  loop_count: 1
  true_end_reached: false
```

---

## 7. 実装マッピング（既存システム流用）

| 既存モジュール | 担当世界・機能 | 変更・拡張内容 |
|--------------|--------------|--------------|
| `skill_tree_system.py` | 全世界共通 | テンプレート別スキルツリー定義対応、`world_id` 名前空間追加 |
| `skill_fusion_system.py` | W4中心・全世界 | クロスワールド融合レシピ対応、`conversion_table` 参照 |
| `job_system.py` | W1/W5/W6/W8 | 「テンプレート専用ジョブ」定義、継承時ジョブ変換ロジック |
| `pet_*_system.py` | W3/W6 | モンスター娘・ダンジョンモンスター統合管理、進化ツリー共通化 |
| `guild_system.py` | W1/W2/W5/W8 | 派閥＝「テンプレート内組織」、クロスワールド派閥関係定義 |
| `faction_war_system.py` | W3/W5/W8 | 世界内戦争・防衛戦・領地争い、シミュレーション高速化 |
| `world_state_system.py` | 全世界 | `WorldState` クラスに `world_id`・`template_id`・`phase` 追加 |
| `procedural_quest_generator.py` | 全世界 | テンプレート別クエストテンプレート、メタヒント自動埋め込み |
| `reincarnation_system.py` | W7・全周回 | ループ継承＝輪廻転生システム流用、`world_inheritance` 統合 |
| `localization_manager.py` | 全世界 | `world.{id}.{key}` 名前空間、テンプレート用語辞書自動生成 |
| `save_system.py` | 全世界 | ワールド別セーブスロット、メタセーブ、クロスワールド整合性検証 |

---

## 8. 新規実装が必要なモジュール

| モジュール | 責務 | 優先度 |
|-----------|------|--------|
| `world_template_registry.py` | 9世界のメタデータ管理・解放条件判定・移動制御 | **Critical** |
| `meta_awareness_system.py` | 《原典閲覧》実装・テンプレート解析・ヒント生成 | **Critical** |
| `world_inheritance_converter.py` | 継承変換テーブル適用・効率計算・スロットUI | **Critical** |
| `template_script_engine.py` | W2シナリオスクリプト・W8ゲーム仕様書・W9魔法OS の DSL 実行基盤 | **High** |
| `territory_optimizer.py` | W5線形計画法ソルバー・政策シミュレータ | **High** |
| `loop_sat_solver.py` | W7分岐点充足可能性問題ソルバー・最短ルート計算 | **Medium** |
| `cross_world_recipe_loader.py` | 融合レシピのワールド横断読み込み・検証 | **Medium** |
| `ui/world_select_screen.py` | ネクサス画面・世界選択・進捗表示 | **High** |
| `ui/inheritance_dashboard.py` | 継承アイテム選択・変換プレビュー | **High** |

---

## 9. バランス・難易度設計

### 9.1 難易度曲線（メタ視点込み）

| 世界順序 | 体感難易度 | 理由 |
|---------|-----------|------|
| W1 (薬師) | ★★☆☆☆ | チート確立が容易、失敗許容度高 |
| W4 (スキル喰い) | ★★★☆☆ | 喰い失敗リスクあり、合成試行錯誤必要 |
| W3 (ダンジョン) | ★★★☆☆ | シミュレーション前提、初見は試行錯誤 |
| W6 (テイマー) | ★★☆☆☆ | 進化ルート既知なら最短ルート確実 |
| W2 (悪役令嬢) | ★★★★☆ | 好感度管理・時間制限・隠しフラグ多重 |
| W5 (領地) | ★★★☆☆ | ソルバー使えば最適解、手動だと難 |
| W8 (NPC) | ★★★★★ | システム仕様理解必要、パッチ予測必須 |
| W7 (ループ) | ★★★★★ | SAT解法必要、初見真エンドほぼ不可能 |
| W9 (スマホ) | ★★★★★ | 全知識統合必須、root奪取は最終試練 |

### 9.2 救済措置
- **《原典閲覧》Lv自動上昇**：世界滞在時間・行動数に応じて自動で解像度アップ
- **ヒントNPC「図書館司書」**：各世界に1体、メタヒントを段階的に販売（ゲーム内通貨）
- **イージーモード**：継承上限撤廃・変換効率100%・失敗なし・ソルバー自動実行

---

## 10. 開発ロードマップ

| マイルストーン | 目標 | 期間 | 主要タスク |
|--------------|------|------|-----------|
| **M1: 基盤・W1/W4** | 2世界プレイアブル | 6週間 | WorldRegistry, MetaAwareness, InheritanceConverter, W1/W4データ・ロジック |
| **M2: 物語・経営・防衛** | W2/W3/W5/W6 実装 | 8週間 | TemplateScriptEngine, TerritoryOptimizer, DungeonAI, EvolutionEngine |
| **M3: システム・ループ** | W7/W8 実装 | 6週間 | LoopSATSolver, SystemSpecEngine, AdminCommandSystem |
| **M4: 統合・最終世界** | W9 実装・全世界連携 | 4週間 | MagicOS, 全ライブラリ統合、真エンド分岐、バランス調整 |
| **M5: ポリッシュ** | リリース品質 | 4週間 | UI/UX改善、多言語、パフォーマンス、テスト全通過、ドキュメント |

---

## 11. リスクと対策

| リスク | 影響 | 対策 |
|--------|------|------|
| **テンプレート知識前提で初見殺し** | 新規プレイヤー離脱 | チュートリアル世界（W1）でメタ概念を丁寧に説明、用語集常時アクセス可 |
| **継承システムの破綻（無限強化）** | ゲームバランス崩壊 | ハードキャップ厳守、変換効率減衰、W9でのみ全解放 |
| **世界間整合性バグ** | セーブ破損・進行不能 | セーブ時整合性検証、ワールド間移動時アトミックコミット、自動バックアップ |
| **スコープクリープ（9世界フル実装）** | 開発遅延・品質低下 | M1で2世界完成させ「垂直スライス」検証、以降はテンプレート量産体制確立 |
| **多言語・メタ用語翻訳地獄** | ローカライズコスト爆発 | 用語辞書自動生成、テンプレート共通用語は一括管理、コミュニティ翻訳導入検討 |

---

## 12. まとめ

この設計は**「なろうテンプレートをゲームメカニクスとして具現化し、メタ認識で攻略する」**という一貫したコア体験を、9つのバリエーションで提供するものです。

- **各世界＝独立したミニゲーム**（それぞれ別ジャンルの面白さ）
- **世界間移動＝「チートの翻訳・合成・進化」**（ローグライト的成長の核心）
- **最終世界＝「全チートの統合IDE」**（プログラマー的カタルシスの極致）

既存システム（スキル・ジョブ・派閥・ペット・領地・輪廻・プロシージャル）を**ほぼ全流用**し、追加実装は「メタ認識」「継承変換」「テンプレートスクリプト」の3系統に集約されています。

---

## 13. 次アクション

1. **`world_template_registry.py` 作成** → 9世界のメタデータスキーマ定義・ロード機能
2. **`meta_awareness_system.py` プロトタイプ** → 《原典閲覧》UI・テンプレート判定ロジック
3. **W1・W4 垂直スライス実装** → 2世界分のデータ・ロジック・UIをエンドツーエンドで動く状態に
4. **継承コンバーター実装・テスト** → W1→W4、W4→W1 双方向変換の検証
5. **テンプレート用語辞書作成** → `localization_manager` 連携・多言語対応準備

---
*作成日: 2026-08-20*  
*バージョン: 1.0 (初版)*  
*対象: naRou プロジェクト・マルチテンプレート世界線統合版*