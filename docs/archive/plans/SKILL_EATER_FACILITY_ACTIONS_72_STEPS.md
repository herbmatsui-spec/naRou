# SkillEaterBaseFacilityActions 実装計画書 (72ステップ)

## 概要
アジト内施設にアクティブなアクションとNPCインタラクションを追加するシステム。
既存の `BaseFacility` 構造を拡張し、5つの施設に各3つずつのアクションを実装。

### 対象施設とアクション
| 施設 | アクション | 音声ファイル |
|------|------------|-------------|
| **ワークショップ** | craft_implant() / repair_gear() / install_cybernetic() | crafting_bench.ogg |
| **研究室** | analyze_skill_crystal() / reverse_engineer_tech() / develop_countermeasure() | medical_scan.ogg |
| **医療ベイ** | treat_toxicity() / augment_servant() / memory_wipe() | medical_scan.ogg |
| **指揮室** | dispatch_squad() / plan_raid() / negotiate_truce() | holo_map_ping.ogg |
| **バー/交易所** | gather_intel() / hire_mercenary() / launder_aldo() | drink_pour.ogg |

### 共通仕様
- **コスト**: ジャンク(スクラップ) / アルド(通貨) / 時間(ターン)
- **成功率**: 施設Lv × 15% + 関連スキルLv × 5% (最大95%)
- **成果ログ**: 成功/失敗/クリティカルそれぞれにメッセージ
- **演出**: Emote画像 + Audio再生 + PresentationEventキューイング

---

## Phase 0: 基盤データ構造 (Steps 1-8)

### Step 1: FacilityAction データクラス定義
**ファイル**: `skill_eater_facility_actions.py` (新規作成)
```python
@dataclass
class FacilityAction:
    id: str
    name: str
    facility_id: str
    cost_junk: int = 0
    cost_aldo: int = 0
    cost_time_turns: int = 0
    required_skill: str | None = None
    base_success_rate: float = 0.50
    max_success_rate: float = 0.95
    audio_file: str = ""
    emote_file: str = ""
    description: str = ""
```

### Step 2: FacilityActionResult データクラス定義
```python
@dataclass
class FacilityActionResult:
    action_id: str
    facility_name: str
    success: bool
    is_critical: bool = False
    consumed_junk: int = 0
    consumed_aldo: int = 0
    consumed_time: int = 0
    rewards: dict[str, Any] = field(default_factory=dict)
    log_message: str = ""
    played_sounds: list[str] = field(default_factory=list)
    presentation_events: list[PresentationEvent] = field(default_factory=list)
```

### Step 3: FacilityActionRegistry クラス作成
- シングルトンパターンで全アクション定義を管理
- `get_action(action_id)` / `get_actions_by_facility(facility_id)` メソッド

### Step 4: BaseFacility クラス拡張 (skill_eater_economy_system.py 修正)
- `actions: list[str]` フィールド追加（アクションIDリスト）
- `available_actions` プロパティでアンロック済みアクション取得

### Step 5: 施設定義データの拡張 (skill_eater_economy_system.py)
既存の `base_facilities` 辞書に `actions` リスト追加：
```python
"workshop": BaseFacility(
    id="workshop", name="ワークショップ", level=1,
    actions=["craft_implant", "repair_gear", "install_cybernetic"],
    ...
),
"lab": BaseFacility(...),
"medbay": BaseFacility(...),
"command": BaseFacility(...),
"bar": BaseFacility(...),
```

### Step 6: プレイヤー状態へのリソース追加 (skill_eater_system.py CharacterState)
- `junk: int = 0` (スクラップ/ジャンク資源)
- `facility_action_cooldowns: dict[str, int] = field(default_factory=dict)` (アクションクールダウン)

### Step 7: 成功率計算ユーティリティ関数
```python
def calculate_success_rate(facility: BaseFacility, player: CharacterState, action: FacilityAction) -> float:
    rate = action.base_success_rate + facility.level * 0.15
    if action.required_skill and player.has_skill(action.required_skill):
        slot = player.skills[action.required_skill]
        rate += slot.level * 0.05
    return min(rate, action.max_success_rate)
```

### Step 8: 基本オーディオ・演出定数の確認
- 既存の `AUDIO_DIR` / `EMOTE_DIR` パス確認
- 必要な音声ファイルの存在確認 (crafting_bench.ogg 等は後で追加または既存ファイルを代用)

---

## Phase 1: ワークショップ アクション実装 (Steps 9-20)

### Step 9: craft_implant() アクション定義登録
```python
FacilityAction(
    id="craft_implant",
    name="インプラント製作",
    facility_id="workshop",
    cost_junk=50, cost_aldo=500, cost_time_turns=1,
    required_skill="rar_utility_005",  # サイバネティクス知識
    base_success_rate=0.40,
    audio_file="crafting_bench.ogg",
    emote_file="emote_stars.png",
    description="スキルスロット拡張用インプラントを製作する"
)
```

### Step 10: craft_implant() 実行ロジック実装
**成功時**: `max_memory_capacity +2` (最大+10まで)、インプラントアイテム獲得
**失敗時**: ジャンクのみ消費、ログ「材料が不純で製作失敗」
**クリティカル (成功率90%以上で5%確率)**: `max_memory_capacity +4`、レアインプラント獲得

### Step 11: craft_implant() 演出実装
- Emote: `emote_stars.png` (成功) / `emote_cross.png` (失敗)
- Audio: `crafting_bench.ogg` + `metalPot1.ogg` (成功) / `creak1.ogg` (失敗)
- PresentationEvent キューイング

### Step 12: repair_gear() アクション定義登録
```python
FacilityAction(
    id="repair_gear",
    name="装備修理",
    facility_id="workshop",
    cost_junk=30, cost_aldo=200, cost_time_turns=1,
    required_skill=None,
    base_success_rate=0.70,
    audio_file="crafting_bench.ogg",
    emote_file="emote_heart.png",
    description="損傷した装備を修理し性能を回復する"
)
```

### Step 13: repair_gear() 実行ロジック実装
- プレイヤーの「装備耐久度」概念がないため代替実装：
- **成功時**: プレイヤーの `defense +5` (一時バフ、3ターン)、`atk +3` (一時バフ、3ターン)
- **失敗時**: ジャンク消費のみ、ログ「修理途中で部品が外れた」
- **クリティカル**: バフ効果2倍、ターン数+2

### Step 14: repair_gear() 演出実装
- Emote: `emote_heart.png` / `emote_cross.png`
- Audio: `crafting_bench.ogg` + `chop.ogg` (成功)

### Step 15: install_cybernetic() アクション定義登録
```python
FacilityAction(
    id="install_cybernetic",
    name="義体インストール",
    facility_id="workshop",
    cost_junk=100, cost_aldo=2000, cost_time_turns=2,
    required_skill="rar_utility_005",
    base_success_rate=0.30,
    audio_file="crafting_bench.ogg",
    emote_file="emote_exclamation.png",
    description="高度な義体パーツを身体に埋め込み能力を永続強化"
)
```

### Step 16: install_cybernetic() 実行ロジック実装
**成功時**: 永続ステータス上昇 (`atk+5` / `defense+5` / `speed+3` / `intelligence+3` からランダム1つ)
**失敗時**: 全コスト消費、`hp -20` (手術失敗ダメージ)、`status_effects` に "SurgeryTrauma" 追加
**クリティカル**: 2つのステータス上昇、特殊タグ "Cybernetic" 付与

### Step 17: install_cybernetic() 演出実装
- 成功: `emote_exclamation.png` + `crafting_bench.ogg` + `metalPot3.ogg` + `handleSmallLeather2.ogg`
- 失敗: `emote_faceSad.png` + `creak3.ogg` + `cloth3.ogg`

### Step 18: ワークショップ共通のコスト支払い・検証関数
```python
def can_afford_action(player: CharacterState, economy: SkillEaterEconomySystem, action: FacilityAction) -> tuple[bool, str]:
    if player.junk < action.cost_junk: return False, "ジャンクが不足しています"
    if economy.aldo_currency < action.cost_aldo: return False, "アルドが不足しています"
    # クールダウンチェック
    return True, ""
```

### Step 19: ワークショップ アクション実行メイン関数
```python
def execute_workshop_action(
    self, player: CharacterState, action_id: str
) -> FacilityActionResult:
    # 1. アクション取得
    # 2. コスト/クールダウン検証
    # 3. 成功率計算
    # 4. 乱数判定
    # 5. 結果適用
    # 6. 演出発行
    # 7. 結果返却
```

### Step 20: ワークショップ アクションのユニットテスト作成
- `test_facility_actions.py` に `test_workshop_craft_implant` 等を追加
- 成功/失敗/クリティカル/コスト不足/クールダウンの各ケース

---

## Phase 2: 研究室 アクション実装 (Steps 21-32)

### Step 21: analyze_skill_crystal() アクション定義登録
```python
FacilityAction(
    id="analyze_skill_crystal",
    name="スキル結晶解析",
    facility_id="lab",
    cost_junk=20, cost_aldo=1000, cost_time_turns=1,
    required_skill="com_magic_001",  # 解析魔法
    base_success_rate=0.60,
    audio_file="medical_scan.ogg",
    emote_file="emote_idea.png",
    description="未知のスキル結晶を解析し、スキル定義を解放する"
)
```

### Step 22: analyze_skill_crystal() 実行ロジック実装
- **前提**: プレイヤーが「未鑑定スキル結晶」アイテムを所持 (インベントリシステム想定、簡易実装では `player.archived_skills` に暗号化スキルとして保管)
- **成功時**: 暗号化スキル1つの `is_encrypted=False` に変更、レジストリに登録
- **失敗時**: コストのみ消費、ログ「結晶の共振が読み取れない」
- **クリティカル**: 追加で `market_value` 判明、スキルTier判明

### Step 23: analyze_skill_crystal() 演出実装
- Audio: `medical_scan.ogg` + `bookOpen.ogg` + `metalLatch.ogg` (成功)
- Emote: `emote_idea.png` (成功) / `emote_question.png` (失敗)

### Step 24: reverse_engineer_tech() アクション定義登録
```python
FacilityAction(
    id="reverse_engineer_tech",
    name="敵装備リバースエンジニアリング",
    facility_id="lab",
    cost_junk=80, cost_aldo=1500, cost_time_turns=2,
    required_skill="rar_utility_005",
    base_success_rate=0.35,
    audio_file="medical_scan.ogg",
    emote_file="emote_dots3.png",
    description="敵の装備・技術を解析し、新規合成レシピを獲得する"
)
```

### Step 25: reverse_engineer_tech() 実行ロジック実装
- **成功時**: ランダムな静的合成レシピ1つを `SkillEaterSynthesisSystem._static_recipes` に追加 (未登録のものから)
- **失敗時**: コスト消費、ログ「技術が難解すぎて解読不能」
- **クリティカル**: 2つのレシピ獲得、または `is_illegal=False` のレアレシピ獲得

### Step 26: reverse_engineer_tech() 演出実装
- Audio: `medical_scan.ogg` + `bookFlip1.ogg` + `bookFlip2.ogg` (成功)
- Emote: `emote_dots3.png` → `emote_stars.png` (成功アニメ風)

### Step 27: develop_countermeasure() アクション定義登録
```python
FacilityAction(
    id="develop_countermeasure",
    name="対策開発",
    facility_id="lab",
    cost_junk=50, cost_aldo=3000, cost_time_turns=3,
    required_skill="uni_midas_001",  # 高度解析
    base_success_rate=0.25,
    audio_file="medical_scan.ogg",
    emote_file="emote_stars.png",
    description="特定ボス/敵タイプへの対抗手段(メタ特効)を開発する"
)
```

### Step 28: develop_countermeasure() 実行ロジック実装
- **対象**: `boss_id` パラメータで指定 (midas_ceo, bank_director 等)
- **成功時**: `GlobalRuleEngine` に一時的な `boss_weakness[boss_id] = True` 記録、次回遭遇時にメタ特効判定で有利
- **失敗時**: コスト消費、ログ「対策データの構築に失敗」
- **クリティカル**: 恒久的な弱点登録、次周回引き継ぎ可能

### Step 29: develop_countermeasure() 演出実装
- Audio: `medical_scan.ogg` + `metalPot2.ogg` + `metalPot3.ogg` (成功)
- Emote: `emote_stars.png` + `emote_exclamations.png` (成功)

### Step 30: 研究室共通の「未鑑定アイテム」簡易実装
- `CharacterState.unidentified_crystals: list[str] = []` 追加
- 捕食失敗時や特定イベントで追加される想定

### Step 31: 研究室 アクション実行メイン関数
```python
def execute_lab_action(
    self, player: CharacterState, action_id: str, **kwargs
) -> FacilityActionResult:
    # develop_countermeasure 用に boss_id パラメータ対応
```

### Step 32: 研究室 アクションのユニットテスト作成

---

## Phase 3: 医療ベイ アクション実装 (Steps 33-44)

### Step 33: treat_toxicity() アクション定義登録
```python
FacilityAction(
    id="treat_toxicity",
    name="毒性治療",
    facility_id="medbay",
    cost_junk=10, cost_aldo=500, cost_time_turns=1,
    required_skill=None,
    base_success_rate=0.80,
    audio_file="medical_scan.ogg",
    emote_file="emote_hearts.png",
    description="スキル精神侵食度(毒性)を軽減する治療を行う"
)
```

### Step 34: treat_toxicity() 実行ロジック実装
**成功時**: `addiction_buildup -30` (最小0)、`status_effects` から "Addicted" 除去
**失敗時**: `addiction_buildup -10` のみ、ログ「治療薬が合わなかった」
**クリティカル**: `addiction_buildup = 0`、一時的に「精神安定」バフ付与 (次5ターン 侵食度上昇なし)

### Step 35: treat_toxicity() 演出実装
- Audio: `medical_scan.ogg` + `handleSmallLeather2.ogg` (成功) / `creak1.ogg` (失敗)
- Emote: `emote_hearts.png` / `emote_swirl.png`

### Step 36: augment_servant() アクション定義登録
```python
FacilityAction(
    id="augment_servant",
    name="従属者強化手術",
    facility_id="medbay",
    cost_junk=60, cost_aldo=1000, cost_time_turns=2,
    required_skill="rar_utility_005",
    base_success_rate=0.45,
    audio_file="medical_scan.ogg",
    emote_file="emote_heart.png",
    description="捕獲した従属者(サーヴァント)を手術で強化する"
)
```

### Step 37: augment_servant() 実行ロジック実装
- **対象**: `servant_id` パラメータで指定
- **成功時**: 対象サーヴァントの `state.atk +10` / `hp +50` / `duration_turns +2` / 新スキル1つ付与 (COMスキルからランダム)
- **失敗時**: コスト消費、サーヴァント `hp -30`、ログ「拒絶反応で素体が損傷」
- **クリティカル**: `duration_turns +5`、レアスキル付与、見た目変化フラグ

### Step 38: augment_servant() 演出実装
- Audio: `medical_scan.ogg` + `beltHandle1.ogg` + `metalPot1.ogg` (成功)
- Emote: `emote_heart.png` → `emote_stars.png`

### Step 39: memory_wipe() アクション定義登録
```python
FacilityAction(
    id="memory_wipe",
    name="記憶消去・リセット",
    facility_id="medbay",
    cost_junk=0, cost_aldo=5000, cost_time_turns=3,
    required_skill="con_fire_001",  # 禁忌の知識
    base_success_rate=0.20,
    audio_file="medical_scan.ogg",
    emote_file="emote_cross.png",
    description="スキル記憶を完全消去し、クリーンな状態で再出発する(危険)"
)
```

### Step 40: memory_wipe() 実行ロジック実装
**成功時**: 
- 全スキル削除 (`skills.clear()`, `archived_skills.clear()`)
- `addiction_buildup = 0`
- `max_memory_capacity +5` (脳のリセットボーナス)
- `is_husk = False`
- 特殊実績 "Tabula_Rasa" 獲得

**失敗時**: 
- 全コスト消費
- `hp = 1` (瀕死)
- `status_effects` に "Amnesia", "Broken" 追加
- ログ「記憶消去プロセスが暴走。自我が崩壊しかけた」

**クリティカル**: 
- 成功効果 + `analysis_level +2`、特殊スキル "Blank_Slate" (メモリコスト0、効果: 次の捕食成功率+50%) 獲得

### Step 41: memory_wipe() 演出実装
- 成功: `emote_cross.png` → `emote_heart.png` (白黒反転風)
- Audio: `medical_scan.ogg` + `doorClose_3.ogg` + `bookClose.ogg` + `doorOpen_2.ogg`
- 失敗: `emote_faceSad.png` + `creak3.ogg` + `cloth3.ogg` + `doorClose_1.ogg`

### Step 42: 医療ベイ共通のサーヴァント選択ヘルパー
```python
def get_available_servants(servant_system: SkillEaterServantSystem) -> list[ServantCharacter]:
    return list(servant_system.servant_party.values())
```

### Step 43: 医療ベイ アクション実行メイン関数
```python
def execute_medbay_action(
    self, player: CharacterState, action_id: str, servant_id: str | None = None
) -> FacilityActionResult:
```

### Step 44: 医療ベイ アクションのユニットテスト作成

---

## Phase 4: 指揮室 アクション実装 (Steps 45-56)

### Step 45: dispatch_squad() アクション定義登録
```python
FacilityAction(
    id="dispatch_squad",
    name="部隊派遣",
    facility_id="command",
    cost_junk=30, cost_aldo=1000, cost_time_turns=2,
    required_skill=None,
    base_success_rate=0.55,
    audio_file="holo_map_ping.ogg",
    emote_file="emote_exclamations.png",
    description="抵抗軍部隊を派遣し、資源回収や偵察を行わせる"
)
```

### Step 46: dispatch_squad() 実行ロジック実装
- **ミッションタイプ**: "scavenge" / "recon" / "sabotage" (パラメータで指定)
- **成功時 (scavenge)**: `junk +50-100`、`aldo +200-500`、ランダム素材1-2個
- **成功時 (recon)**: 次のダンジョン階層の敵構成/弱点情報を事前取得 (フラグ記録)
- **成功時 (sabotage)**: `factions["midas"].influence_points -200`、`heat_level -10`
- **失敗時**: 派遣部隊損失、コストのみ消費、ログ「部隊が帰還せず...」
- **クリティカル**: 報酬2倍、特殊アイテム「作戦記録」獲得

### Step 47: dispatch_squad() 演出実装
- Audio: `holo_map_ping.ogg` + `doorOpen_1.ogg` (出発) + `doorClose_2.ogg` (帰還・成功)
- Emote: `emote_exclamations.png` → `emote_stars.png` (成功)

### Step 48: plan_raid() アクション定義登録
```python
FacilityAction(
    id="plan_raid",
    name="襲撃計画立案",
    facility_id="command",
    cost_junk=50, cost_aldo=2000, cost_time_turns=3,
    required_skill="rar_combat_012",  # 戦術指揮
    base_success_rate=0.40,
    audio_file="holo_map_ping.ogg",
    emote_file="emote_idea.png",
    description="ミダス施設やボス拠点への襲撃作戦を練り、成功率を高める"
)
```

### Step 49: plan_raid() 実行ロジック実装
- **対象**: `target_id` ("midas_branch", "midas_hq", "bank_vault" 等)
- **成功時**: `GlobalRuleEngine` または専用フラグ `raid_plan[target_id] = True` 記録
  - 次回該当ボス/エリア戦闘で: `devour_success_rate +0.20`、初手先制権獲得
- **失敗時**: コスト消費、ログ「情報が漏洩し、計画が露見した」
- **クリティカル**: 計画が恒久的有効、ボスの `is_boss_instant_kill_enabled = False` 強制

### Step 50: plan_raid() 演出実装
- Audio: `holo_map_ping.ogg` + `bookFlip3.ogg` + `metalLatch.ogg` (成功)
- Emote: `emote_idea.png` → `emote_stars.png`

### Step 51: negotiate_truce() アクション定義登録
```python
FacilityAction(
    id="negotiate_truce",
    name="休戦交渉",
    facility_id="command",
    cost_junk=0, cost_aldo=10000, cost_time_turns=1,
    required_skill=None,
    base_success_rate=0.30,
    audio_file="holo_map_ping.ogg",
    emote_file="emote_hearts.png",
    description="敵対派閥と休戦協定を結び、一時的に敵対関係を解除する"
)
```

### Step 52: negotiate_truce() 実行ロジック実装
- **対象**: `faction_id` ("midas", "bank" 等)
- **成功時**: 対象派閥 `is_hostile = False`、`reputation +30` (最大100)、`heat_level = 0`
  - 効果持続: 10ターン (その後再敵対化)
- **失敗時**: アルド消費のみ、`reputation -20`、ログ「交渉決裂。相手は激怒している」
- **クリティカル**: 永続的な中立化 (`is_hostile = False` 恒久)、特殊クエスト解放

### Step 53: negotiate_truce() 演出実装
- 成功: `emote_hearts.png` + `holo_map_ping.ogg` + `handleCoins.ogg` + `doorOpen_2.ogg`
- 失敗: `emote_anger.png` + `creak2.ogg` + `doorClose_1.ogg`

### Step 54: 指揮室共通の派閥状態管理ヘルパー
```python
def get_hostile_factions(economy: SkillEaterEconomySystem) -> list[FactionState]:
    return [f for f in economy.factions.values() if f.is_hostile]

def apply_raid_bonus(rule_engine: GlobalRuleEngine, target_id: str):
    # 襲撃計画ボーナス適用
```

### Step 55: 指揮室 アクション実行メイン関数
```python
def execute_command_action(
    self, player: CharacterState, economy: SkillEaterEconomySystem, 
    action_id: str, **kwargs
) -> FacilityActionResult:
```

### Step 56: 指揮室 アクションのユニットテスト作成

---

## Phase 5: バー/交易所 アクション実装 (Steps 57-68)

### Step 57: gather_intel() アクション定義登録
```python
FacilityAction(
    id="gather_intel",
    name="情報収集",
    facility_id="bar",
    cost_junk=0, cost_aldo=500, cost_time_turns=1,
    required_skill=None,
    base_success_rate=0.65,
    audio_file="drink_pour.ogg",
    emote_file="emote_idea.png",
    description="酒場の噂話から貴重な情報を聞き出す"
)
```

### Step 58: gather_intel() 実行ロジック実装
- **情報カテゴリ**: "boss_weakness" / "hidden_recipe" / "faction_movement" / "secret_vault" (ランダム)
- **成功時**: 該当カテゴリのヒントメッセージ獲得、ログに詳細表示
  - 例: "《黄金錬成》の弱点は【氷属性】との噂..."
  - 例: "地下倉庫に未鑑定スキル結晶が眠っているらしい..."
- **失敗時**: アルド消費、ログ「有力な情報は得られなかった」
- **クリティカル**: 確定情報 (ボス弱点完全開示、隠しレシピID判明、金庫座標判明)

### Step 59: gather_intel() 演出実装
- Audio: `drink_pour.ogg` + `bookOpen.ogg` + `bookFlip1.ogg` (成功)
- Emote: `emote_idea.png` / `emote_dots3.png` (思考中)

### Step 60: hire_mercenary() アクション定義登録
```python
FacilityAction(
    id="hire_mercenary",
    name="傭兵雇用",
    facility_id="bar",
    cost_junk=0, cost_aldo=3000, cost_time_turns=1,
    required_skill=None,
    base_success_rate=0.70,
    audio_file="drink_pour.ogg",
    emote_file="emote_cash.png",
    description="傭兵を雇い、次の探索/戦闘に同行させる"
)
```

### Step 61: hire_mercenary() 実行ロジック実装
- **傭兵タイプ**: "vanguard" (前衛) / "sniper" (狙撃) / "medic" (医療) / "hacker" (解析) - ランダムまたは選択
- **成功時**: 一時的な同行NPC追加 (3ターン/次のダンジョン1回)
  - Vanguard: 敵のターゲットを引き受け、プレイヤー被ダメージ-50%
  - Sniper: ターン開始時ランダム敵に `atk*1.5` ダメージ
  - Medic: ターン終了時味方全体 `heal 30`
  - Hacker: 解析Lv +3 相当、暗号化スキル自動ハック試行
- **失敗時**: アルド消費、ログ「信用ならない傭兵だった。金だけ持ち逃げされた」
- **クリティカル**: エリート傭兵 (効果2倍、ターン数+2)、特殊スキル使用可能

### Step 62: hire_mercenary() 演出実装
- Audio: `drink_pour.ogg` + `handleCoins.ogg` + `beltHandle1.ogg` (契約音)
- Emote: `emote_cash.png` → `emote_heart.png` (握手)

### Step 63: launder_aldo() アクション定義登録
```python
FacilityAction(
    id="launder_aldo",
    name="アルド洗浄(マネロン)",
    facility_id="bar",
    cost_junk=0, cost_aldo=0, cost_time_turns=2,  # 洗浄したいアルドを指定
    required_skill="rar_utility_005",
    base_success_rate=0.50,
    audio_file="drink_pour.ogg",
    emote_file="emote_cash.png",
    description="違法入手のアルド(熱い金)を洗浄し、安全な資金に変える"
)
```

### Step 64: launder_aldo() 実行ロジック実装
- **パラメータ**: `amount` (洗浄したいアルド量、最大 `heat_level * 100`)
- **成功時**: `heat_level -= amount // 100`、洗浄済みアルドとして `aldo_currency` に加算 (手数料 20% 差し引き)
  - 例: 5000アルド洗浄 → heat -50、手元に 4000アルド増加
- **失敗時**: 指定アルド没収、`heat_level +20`、ログ「洗浄ルートがマークされていた！」
- **クリティカル**: 手数料 10%、`factions["broker"].reputation +10`

### Step 65: launder_aldo() 演出実装
- 成功: `emote_cash.png` + `drink_pour.ogg` + `handleCoins2.ogg` + `metalClick.ogg` (清算音)
- 失敗: `emote_alert.png` + `creak1.ogg` + `doorClose_1.ogg` + `metalLatch.ogg`

### Step 66: バー/交易所共通の傭兵データクラス
```python
@dataclass
class MercenaryContract:
    merc_type: str  # vanguard/sniper/medic/hacker
    name: str
    duration_turns: int
    effects: dict[str, Any]
    is_elite: bool = False
```

### Step 67: バー/交易所 アクション実行メイン関数
```python
def execute_bar_action(
    self, player: CharacterState, economy: SkillEaterEconomySystem,
    action_id: str, **kwargs
) -> FacilityActionResult:
```

### Step 68: バー/交易所 アクションのユニットテスト作成

---

## Phase 6: 統合システム・ファサード (Steps 69-72)

### Step 69: SkillEaterFacilitySystem クラス作成 (skill_eater_facility_actions.py)
```python
class SkillEaterFacilitySystem:
    def __init__(
        self,
        registry: SkillEaterRegistry | None = None,
        economy: SkillEaterEconomySystem | None = None,
        servant: SkillEaterServantSystem | None = None,
        synthesis: SkillEaterSynthesisSystem | None = None,
        combat: SkillEaterCombatSystem | None = None,
        audio: SkillEaterAudioSystem | None = None,
        presentation: SkillEaterPresentationSystem | None = None,
    ):
        # 依存注入
        # アクションレジストリ初期化
        self._register_all_actions()
    
    def execute_action(
        self, facility_id: str, action_id: str, 
        player: CharacterState, **kwargs
    ) -> FacilityActionResult:
        # 施設取得 → アクション取得 → 実行ディスパッチ
    
    def _execute_workshop(self, ...) -> FacilityActionResult: ...
    def _execute_lab(self, ...) -> FacilityActionResult: ...
    def _execute_medbay(self, ...) -> FacilityActionResult: ...
    def _execute_command(self, ...) -> FacilityActionResult: ...
    def _execute_bar(self, ...) -> FacilityActionResult: ...
```

### Step 70: 既存システムとの統合 (skill_eater_economy_system.py 修正)
- `SkillEaterEconomySystem` に `facility_system: SkillEaterFacilitySystem` 参照追加
- `upgrade_facility()` 後にアクションアンロック通知追加
- 施設Lvアップ時の新規アクション解放ロジック

### Step 71: 総合ユニットテスト作成 (tests/test_skill_eater_facility_actions.py)
```python
class TestFacilityActions(unittest.TestCase):
    def setUp(self):
        # 全システム初期化
    
    def test_workshop_craft_implant_success(self): ...
    def test_workshop_install_cybernetic_critical(self): ...
    def test_lab_analyze_crystal(self): ...
    def test_lab_reverse_engineer(self): ...
    def test_lab_develop_countermeasure(self): ...
    def test_medbay_treat_toxicity(self): ...
    def test_medbay_augment_servant(self): ...
    def test_medbay_memory_wipe_critical(self): ...
    def test_command_dispatch_squad(self): ...
    def test_command_plan_raid(self): ...
    def test_command_negotiate_truce(self): ...
    def test_bar_gather_intel(self): ...
    def test_bar_hire_mercenary(self): ...
    def test_bar_launder_aldo(self): ...
    def test_facility_level_affects_success_rate(self): ...
    def test_insufficient_resources_blocked(self): ...
    def test_cooldown_prevents_spam(self): ...
```

### Step 72: 統合動作確認・デモ追加
- `demo_facility_actions.py` 作成: インタラクティブなデモスクリプト
- 既存の `test_skill_eater_full_72_steps.py` に施設アクションテスト統合
- HTMLデモ (demo_skill_eater_showcase.html) に施設UI追加案をコメントで記載

---

## 音声ファイル対応表

| アクション分類 | 使用音声ファイル | 代用可能な既存ファイル |
|----------------|-----------------|----------------------|
| クラフト/工作 | crafting_bench.ogg | metalPot1.ogg + metalPot2.ogg (重ね再生) |
| 医療/解析 | medical_scan.ogg | metalClick.ogg + metalLatch.ogg (重ね再生) |
| 指揮/戦略 | holo_map_ping.ogg | bookOpen.ogg + metalClick.ogg |
| 酒場/交渉 | drink_pour.ogg | handleCoins.ogg + cloth1.ogg |

> **注意**: `crafting_bench.ogg`, `medical_scan.ogg`, `holo_map_ping.ogg`, `drink_pour.ogg` が実在しない場合、上記の既存ファイル組み合わせで代用するか、アセット生成スクリプトで作成すること。

---

## 実装順序の推奨

1. **Phase 0 (Steps 1-8)**: 基盤データ構造を先に固める
2. **Phase 1-5 (Steps 9-68)**: 施設ごとに独立実装・テスト可能
   - 依存関係が薄いため並行作業可能
   - ワークショップ → 研究室 → 医療ベイ → 指揮室 → バー の順推奨
3. **Phase 6 (Steps 69-72)**: 統合・テスト・デモ

---

## 低性能LLM向け実装ガイドライン

### 各ステップの実装テンプレート
```python
# Step XX: [アクション名] 実装
# 1. FacilityAction 定義を _register_all_actions() に追加
# 2. 実行メソッド _execute_XXX() を追加
# 3. 成功/失敗/クリティカル分岐ロジック記述
# 4. self.presentation.add_event() で演出発行
# 5. self.audio.play_sound() で音声再生
# 6. FacilityActionResult を返却
# 7. ユニットテスト追加
```

### 共通パターン (コピペで使える)
```python
# コスト支払い
player.junk -= action.cost_junk
economy.aldo_currency -= action.cost_aldo

# 成功率計算
rate = calculate_success_rate(facility, player, action)
is_success = random.random() < rate
is_critical = is_success and random.random() < 0.05 and rate > 0.90

# 演出発行共通化
def emit_success(self, action, message):
    self.presentation.add_event(emote_file=action.emote_file, audio_file=action.audio_file, message=message)
    self.audio.play_sound(action.audio_file)
    if hasattr(action, 'success_audio'): self.audio.play_sound(action.success_audio)

def emit_failure(self, action, message):
    self.presentation.add_event(emote_file="emote_cross.png", audio_file="creak1.ogg", message=message)
    self.audio.play_sound("creak1.ogg")
```

### デバッグ用ログ出力
全アクション共通で `logger.debug(f"[Facility] {facility_id}.{action_id}: success={success}, critical={critical}")` を入れると追跡容易。

---

## ファイル構成まとめ

### 新規作成
- `skill_eater_facility_actions.py` - メインシステム (FacilityAction, FacilityActionResult, SkillEaterFacilitySystem)
- `tests/test_skill_eater_facility_actions.py` - ユニットテスト
- `demo_facility_actions.py` - デモスクリプト

### 既存ファイル修正
- `skill_eater_system.py` - CharacterState に `junk`, `facility_action_cooldowns` 追加
- `skill_eater_economy_system.py` - BaseFacility に `actions` 追加、施設定義拡張、SkillEaterEconomySystem に facility_system 参照追加
- `skill_eater_servant_system.py` - ServantCharacter に強化用フィールド追加 (任意)

---

## 完了基準

- [ ] 全15アクションが実装され、実行可能
- [ ] 各アクションに成功/失敗/クリティカルの分岐がある
- [ ] 全アクションで Emote + Audio 演出が再生される
- [ ] コスト(ジャンク/アルド/時間)が正しく消費される
- [ ] 施設レベルとスキルレベルが成功率に反映される
- [ ] クールダウン機能が動作する
- [ ] 全ユニットテストがパスする
- [ ] 既存システム (経済、従属者、合成、戦闘、クエスト) と連携動作する