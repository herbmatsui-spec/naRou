# ギルド・派閥・ランキングシステム 詳細提案書
なろう系要素「ギルド・派閥・ランキングシステム」をElonaに統合するための9つの具体的提案。既存のファクションシステム（`systems.py`のFACTION_*定数、`entity.py`のfaction属性）を拡張し、ギルド加入・クエスト・ランキング報酬・派閥抗争を実現。

---

## 提案1: ギルドメンバーシップシステム

### 概要
プレイヤーはギルドに加入・脱退でき、ギルドホールを拠点として活動。ギルドごとに独自の施設・サービス・メンバー特典を持つ。

### データ構造（`data/guilds.yaml`）
```yaml
guilds:
  adventurers_guild:
    name: "冒険者ギルド"
    icon: "🗡️"
    description: "冒険の仲間を見つけ、依頼を受け取る場所"
    hall_location: "vernis"  # ギルドホールの町
    facilities:
      - "quest_board"
      - "storage"
      - "training_ground"
    membership_benefits:
      - type: "daily_quest_bonus"
        value: 0.2  # 20%増加
      - type: "item_discount"
        value: 0.1  # 10%割引
    rank_requirements:
      novice: 0
      member: 100
      veteran: 500
      officer: 2000
      leader: 5000
    max_members: 50
```

### 実装箇所
- 新規: `guild_system.py` - GuildRegistry, GuildManager, GuildData
- 既存: `entity.py` Entity に `guild_id: Optional[str]`, `guild_rank: str`, `guild_contribution: int` 追加
- 既存: `game.py` ギルドホールアクション、ギルドメニュー実装

---

## 提案2: ギルドクエストと貢献度システム

### 概要
ギルド専用クエストを消化して貢献度を獲得。貢献度に応じてランクアップし、より高度なギルド特典が解放される。

### データ構造（`data/guild_quests.yaml`）
```yaml
guild_quests:
  adventurers_guild:
    daily:
      - id: "slay_goblins"
        name: "ゴブリン退治"
        description: "近郊のゴブリンを5匹倒せ"
        requirements:
          monster_kills:
            goblin: 5
        reward:
          contribution: 50
          gold: 100
          item: "heal_herb"
    weekly:
      - id: "explore_dungeon"
        name: "ダンジョン探索"
        description: "未探索のダンジョンフロアを10階層進め"
        requirements:
          dungeon_depth: 10
        reward:
          contribution: 300
          gold: 1000
          item: "steel_ingot"
```

### 実装箇所
- 新規: `guild_quest_system.py` - GuildQuestRegistry, GuildQuestManager
- 既存: `entity.py` に `guild_quest_progress: Dict[str, int]` 追加（クエストID -> 進捗値）
- 既存: `game.py` _on_kill, advance_world でギルドクエスト進捗更新
- 既存: `advanced_systems.py` SaveSystem にギルドデータ保存追加

---

## 提案3: ギルドランクと報酬システム

### 概要
ギルド内でのランク（ノービス→メンバー→ベテラン→オフィサー→リーダー）に応じて、タイトル・スキル・アイテム報酬が得られる。ランキングボードで上位ギルドを表示。

### データ構造（`data/guild_rewards.yaml`）
```yaml
guild_rewards:
  adventurers_guild:
    rank_rewards:
      member:
        - type: "title"
          value: "guild_novice"
        - type: "skill_unlock"
          value: "guild_training"
      veteran:
        - type: "title"
          value: "guild_member"
        - type: "stat_bonus"
          value: 
            strength: 2
            agility: 2
      officer:
        - type: "exclusive_skill"
          value: "guild_command"
        - type: "facility_unlock"
          value: "private_vault"
    leaderboard_rewards:
      - rank: 1
        reward:
          type: "unique_item"
          value: "guild_master_badge"
          amount: 1
      - rank: 2-3
        reward:
          type: "gold"
          value: 5000
      - rank: 4-10
        reward:
          type: "contribution_bonus"
          value: 0.1  # 10%増加
```

### 実装箇所
- 既存: `guild_system.py` に GuildRewardManager 追加
- 既存: `title_system.py` ギルド専用タイトルを追加（データ駆動）
- 既存: `game.py` ギルドランキング表示UI（Lキー）
- 既存: `systems.py` CombatSystem でギルドボーナス適用

---

## 提案4: 派閥抗争と勢力マップシステム

### 概要
主要派閥間で勢力圏の争奪戦が発生。プレイヤーのギルドが派閥に所属している場合、抗争に参加して報酬を獲得できる。マップに勢力色が表示される。

### データ構造（`data/factions.yaml`）
```yaml
factions:
  kingdom_garde:
    name: "ガルド王国"
    color: [0, 100, 200]  # RGB
    territories: ["vernis", "palmia", "pael"]
    allied_factions: ["church_of_lumiest"]
    rival_factions: ["shadow_hand"]
    influence: 80
  church_of_lumiest:
    name: "ルミエスト教会"
    color: [255, 215, 0]
    territories: ["lesimas", "noyel"]
    allied_factions: ["kingdom_garde"]
    rival_factions: ["cult_of_zaebos"]
    influence: 70
  shadow_hand:
    name: "シャドウハンド"
    color: [50, 50, 50]
    territories: ["derphy"]
    allied_factions: ["cult_of_zaebos"]
    rival_factions: ["kingdom_garde"]
    influence: 60
```

### 実装箇所
- 新規: `faction_war_system.py` - FactionRegistry, FactionWarManager
- 既存: `game.py` advance_world で派閥影響力変動・抗争イベント発生
- 既存: `map_engine.py` 描画時に派閥色でタイルを着色
- 既存: `entity.py` に `faction_reputation: Dict[str, int]` 追加（派閥ID -> 評判値）
- 既存: `ui_fx_systems.py` 派閥抗争エフェクト追加

---

## 提案5: ギルドスキルと共有能力システム

### 概要
ギルドレベルが上がると、全メンバーに共有スキルが解放される。ギルドスキルは経験値ボーナス・アイテムドロップ率上昇など、メンバー全員に適用されるパッシブ効果。

### データ構造（`data/guild_skills.yaml`）
```yaml
guild_skills:
  adventurers_guild:
    unlock_conditions:
      guild_level: 2  # ギルドホールアップグレード必要
    skills:
      - id: "guild_lore"
        name: "ギルドの知識"
        description: "ギルドに所属していると経験値獲得率が上がる"
        type: "passive"
        effects:
          - type: "exp_bonus"
            value: 0.15
            target: "all"
      - id: "guild_storage"
        name: "ギルドの財宝"
        description: "ギルド共有倉庫の容量が増加し、アイテム劣化が遅くなる"
        type: "passive"
        effects:
          - type: "storage_capacity_bonus"
            value: 50
          - type: "rot_resistance"
            value: 0.2
      - id: "guild_network"
        name: "ギルドのネットワーク"
        description: "遠隔地からギルド倉庫へのアイテム預け入れが可能になる"
        type: "active"
        cost: 10
        cooldown: 600  # 10分間隔
        effects:
          - type: "remote_storage_access"
```

### 実装箇所
- 新規: `guild_skill_system.py` - GuildSkillRegistry, GuildSkillManager
- 既存: `entity.py` recalculate_stats() でギルドスキル効果適用
- 既存: `inventory.py` ギルド共有倉庫クラス追加
- 既存: `game.py` ギルドスキル習得UI（ギルドホール内で）
- 既存: `advanced_systems.py` SaveSystem にギルドスキルデータ保存

---

## 提案6: ギルド階層と権限システム

### 概要
ギルド内で役職（メンバー・長老・幹部・ guildmaster）を設定可能。役職によってギルド設定変更・メンバー追放・資金引き出しなどの権限が異なる。不適切な役職行動はギルド内評判に影響。

### データ構造（`data/guild_roles.yaml`）
```yaml
guild_roles:
  default_roles:
    member:
      permissions: []
      promotions_to: ["elder"]
      demotions_from: []
    elder:
      permissions: ["invite_members", "view_vault"]
      promotions_to: ["officer"]
      demotions_from: ["member"]
    officer:
      permissions: ["kick_members", "manage_quests", "withdraw_funds"]
      promotions_to: ["guildmaster"]
      demotions_from: ["elder"]
    guildmaster:
      permissions: ["all"]
      promotions_to: []
      demotions_from: ["officer"]
  custom_roles:
    # ギルドマスターがカスタム役職を作成可能
    recruiter:
      permissions: ["invite_members", "view_members"]
      promotions_to: []
      demotions_from: []
    treasurer:
      permissions: ["view_funds", "withdraw_funds", "manage_tax"]
      promotions_to: []
      demotions_from: []
```

### 実装箇所
- 新規: `guild_role_system.py` - GuildRoleRegistry, GuildRoleManager
- 既存: `entity.py` に `guild_role: Optional[str]` 追加
- 既存: `game.py` ギルド管理メニュー（役職任命・権限設定）
- 既存: `guild_system.py` ギルド操作時に権限チェック追加
- 既存: `advanced_systems.py` SaveSystem にギルド役職データ保存

---

## 提案7: ギルド戦争と同盟システム

### 概要
ギルド同士が宣戦布告し、ギルド戦争を開始できる。勝利条件（メンバー撃破数・領土支配・クエスト完了）を達成したギルドが報酬を獲得。同盟を結んで共同作戦も可能。

### データ構造（`data/guild_wars.yaml`）
```yaml
guild_war_conditions:
  victory_conditions:
    - type: "member_eliminations"
      target: 50  # 敵ギルドメンバーを50人倒す
    - type: "territory_control"
      target: ["derphy"]  # 特定ダンジョンを完全支配
    - type: "quest_completion"
      target: 
        guild_quest: "defend_stronghold"
        count: 10
  alliance_benefits:
    - type: "shared_vault_access"
    - type: "joint_quest_availability"
    - type: "mutual_defense_pact"
```

### 実装箇所
- 新規: `guild_war_system.py` - GuildWarRegistry, GuildWarManager
- 既存: `game.py` advance_world でギルド戦争状態更新・勝利条件チェック
- 既存: `_on_kill` で ギルド戦争殺害数カウント
- 既存: `ui_fx_systems.py` ギルド戦争エフェクト・マップ表示追加
- 既存: `advanced_systems.py` SaveSystem にギルド戦争データ保存

---

## 提案8: ランキングタイトルと称号システム

### 概要
個人・ギルド・派閥のランキング順位に応じて特別な称号が付与される。称号はステータスボーナスや特殊効果を持ち、ランキング変動で獲得・喪失を繰り返す。

### データ構造（`data/ranking_titles.yaml`）
```yaml
ranking_titles:
  individual:
    - rank_range: [1, 1]  # 1位のみ
      title: "world_champion"
      name: "世界チャンピオン"
      effects:
        - type: "stat_bonus"
          value:
            strength: 10
            agility: 10
            intelligence: 10
        - type: "drop_rate_bonus"
          value: 0.5
    - rank_range: [2, 3]
      title: "elite_warrior"
      name: "エリートウォリアー"
      effects:
        - type: "stat_bonus"
          value:
            strength: 5
          type: "crit_chance"
          value: 5
  guild:
    - rank_range: [1, 3]
      title: "top_guild"
      name: "上位ギルド"
      effects:
        - type: "guild_exp_bonus"
          value: 0.2
        - type: "member_capacity_bonus"
          value: 10
  faction:
    - rank_range: [1, 1]
      title: "dominant_faction"
      name: "優勢派閥"
      effects:
        - type: "faction_influence_bonus"
          value: 0.15
        - type: "territory_gain_rate"
          value: 0.1
```

### 実装箇所
- 既存: `title_system.py` ランキング専用タイトルデータ追加
- 既存: `game.py` ランキング計算・タイトル付与ロジック（毎日0時更新）
- 既存: `entity.py` に `ranking_titles: List[str]` 追加（付与中のランキングタイトル）
- 既存: `advanced_systems.py` SaveSystem にランキングタイトルデータ保存
- 既存: `ui_fx_systems.py` ランキング変動エフェクト追加

---

## 提案9: ファクションストーリーラインとイベントシステム

### 概要
特定のファクションに高評価・所属していると、派閥専用ストーリーライン・イベントが発生。イベント完了で派閥独自のアイテム・スキル・ロアが解放される。選択によって他派閥との関係が変化する。

### データ構造（`data/faction_events.yaml`）
```yaml
faction_events:
  church_of_lumiest:
    - id: "heresy_trial"
      name: "異端審問"
      description: "教会に異端の噂が広がった。真相を究明せよ"
      requirements:
        faction_reputation:
          church_of_lumiest: 75
      choices:
        - id: "innocent"
          text: "無実を主張する"
          consequences:
            faction_reputation:
              church_of_lumiest: +20
              shadow_hand: -10
            rewards:
              - type: "skill_unlock"
                value: "divine_protection"
              - type: "item"
                value: "holy_symbol"
        - id: "guilty"
          text: "有罪を認めて懺悔する"
          consequences:
            faction_reputation:
              church_of_lumiest: +10
            rewards:
              - type: "title"
                value: "penitent"
              - type: "item"
                value: "blessed_vestment"
  shadow_hand:
    - id: "infiltration_mission"
      name: "潜入作戦"
      description: "王城に潜入し、機密文書を盗み出せ"
      requirements:
        faction_reputation:
          shadow_hand: 80
          stealth_skill: 50
      effects:
        - type: " dungeon_generate"
          value: "shadow_infiltration"
        - type: "time_limit"
          value: 600  # 10分制限
      rewards:
        - type: "unique_item"
          value: "shadow_documents"
        - type: "faction_reputation_bonus"
          value: 
            shadow_hand: +50
            kingdom_garde: -30
```

### 実装箇所
- 新規: `faction_event_system.py` - FactionEventRegistry, FactionEventManager
- 既存: `game.py` advance_world で ファクションイベント発生チェック
- 既存: `entity.py` に `completed_faction_events: List[str]` 追加
- 既存: `ui_fx_systems.py` ファクションイベントUI・エフェクト追加
- 既存: `advanced_systems.py` SaveSystem にファクションイベントデータ保存

---

## 実装優先度マトリクス

| 提案 | 優先度 | 工数見積 | 依存関係 | なろう度 |
|------|--------|----------|----------|----------|
| 1. ギルドメンバーシップシステム | P0 | 3日 | 既存ファクション | ★★★★★ |
| 2. ギルドクエストと貢献度システム | P0 | 4日 | 提案1 | ★★★★★ |
| 3. ギルドランクと報酬システム | P1 | 3日 | 提案1,2 | ★★★★☆ |
| 4. 派閥抗争と勢力マップシステム | P1 | 4日 | 既存ファクション | ★★★★☆ |
| 5. ギルドスキルと共有能力システム | P1 | 3日 | 提案1 | ★★★★☆ |
| 6. ギルド階層と権限システム | P2 | 3日 | 提案1 | ★★★☆☆ |
| 7. ギルド戦争と同盟システム | P2 | 4日 | 提案1,4 | ★★★★☆ |
| 8. ランキングタイトルと称号システム | P1 | 2日 | 提案3 (称号システム) | ★★★★☆ |
| 9. ファクションストーリーラインとイベントシステム | P2 | 3日 | 提案4,8 | ★★★★★ |

---

## 既存コードとの統合ポイント

### entity.py への追加フィールド
```python
@dataclass
class Entity:
    # ... 既存フィールド ...
    
    # ギルド関連
    guild_id: Optional[str] = None
    guild_rank: str = "none"
    guild_contribution: int = 0
    guild_role: Optional[str] = None
    
    # ファクション関連
    faction_reputation: Dict[str, int] = field(default_factory=dict)
    completed_faction_events: List[str] = field(default_factory=list)
    ranking_titles: List[str] = field(default_factory=list)
    
    # クエスト・進行関連
    guild_quest_progress: Dict[str, int] = field(default_factory=dict)  # quest_id -> progress
```

### 統合フロー
1. **ギルドホール入場時** (`game.py:talk_to_neighbor` でギルドホール判定) → ギルドメニュー表示
2. **ギルドクエスト進行時** (`game.py:_on_kill`, `advance_world`) → ギルドクエスト進捗更新 → 貢献度加算
3. **ランキング更新時** (`game.py:advance_world` の日付変わりチェック) → ランキング計算 → タイトル付与/剥奪
4. **派閥抗争判定時** (`game.py:advance_world` の定期チェック) → 派閥影響力変動 → 抵抗イベント発生
5. **ギルド戦争状態時** (`game.py:_on_kill`, `advance_world`) → 戦争殺害数カウント → 勝利条件チェック
6. **ファクションイベント発生時** (`game.py:advance_world`) → 条件チェック → イベント提示
7. **ステータス再計算時** (`entity.py:recalculate_stats`) → ギルドスキル・ファクションボーナス・ランキングタイトル効果適用
8. **セーブ/ロード時** (`advanced_systems.py:SaveSystem`) → 全ギルド・ファクション・ランキングデータ永続化

---

## 次のステップ

この提案書に基づき、以下の順序で実装計画書（12ステップ分割）を作成可能：

1. **Step 1-2**: 基本データファイル作成（guilds.yaml, factions.yaml）
2. **Step 3**: Entity拡張（ギルド・ファクション関連フィールド追加）
3. **Step 4**: GuildRegistry/Manager実装
4. **Step 5**: FactionRegistry/Manager実装
5. **Step 6**: ギルドクエスト・貢献度システム実装
6. **Step 7**: ギルドランキング・報酬システム実装
7. **Step 8**: ギルドスキル・共有能力システム実装
9. **Step 9**: ギルド階層・権限システム実装
10. **Step 10**: ギルド戦争・同盟システム実装
11. **Step 11**: ランキングタイトル・ファクションイベントシステム実装
12. **Step 12**: セーブ/ロード統合・UI実装・テスト