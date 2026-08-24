# Fat Entity アンチパターン解消: ECS純粋コンポーネント指向リファクタリング (72ステップ)

> 目的: `Entity` クラス (1,500行超) に残るハードコードフィールドを全てコンポーネントへ移行し、純粋な ECS アーキテクチャを確立する。
> 制約: 低性能 LLM でも 1 ステップずつ実装・検証可能な粒度に分割。

---

## 対象ハードコードフィールド一覧 (移行マッピング)

| 分類 | フィールド | 移行先コンポーネント | 現状 |
|---|---|---|---|
| 派生ステータス | `hp`, `max_hp`, `mp`, `max_mp`, `stamina`, `max_stamina` | `BaseStatsComponent` | プロパティ委譲済みだが `__init__` で直接初期化 |
| エネルギー/ターン | `energy` | **新規** `TurnEnergyComponent` | 生フィールド |
| 戦闘一時状態 | `next_intent`, `ai_role`, `preferred_range` | **新規** `CombatIntentComponent` | 生フィールド |
| ペット関連 | `tactic`, `pets` | `PetAIComponent`, **新規** `PetComponent` | 部分委譲済み |
| 信仰システム | `god_id`, `piety`, `received_servant`, `received_artifact` | **新規** `FaithComponent` | 生フィールド |
| 突然変異/エーテル病 | `mutations`, `ether_disease_stages` | **新規** `MutationComponent` | 生フィールド |
| チュートリアル | `completed_tutorials`, `pending_tutorial_popup` | **新規** `TutorialProgressComponent` | 生フィールド |
| 属性耐性 | `base_resistances`, `weaknesses` | **新規** `ResistanceComponent` | 生フィールド + 計算ロジック |
| 経験値/レベル | `level`, `exp`, `exp_next` | `LevelComponent` | プロパティ委譲済みだが `__init__` で直接初期化 |
| スキル | `_skills` | **新規** `SkillInventoryComponent` | 生フィールド + 辞書管理 |

---

## フェーズ構成

| フェーズ | ステップ | テーマ |
|---|---|---|
| **Phase 1** | 1-12 | 基盤・新規コンポーネント作成 |
| **Phase 2** | 13-24 | Entity.__init__ からのフィールド剥離 |
| **Phase 3** | 25-36 | プロパティ委譲・後方互換レイヤー |
| **Phase 4** | 37-48 | 計算ロジック移行 |
| **Phase 5** | 49-60 | シリアライズ・デシリアライズ移行 |
| **Phase 6** | 61-72 | テスト・検証・クリーンアップ |

---

## Phase 1: 基盤・新規コンポーネント作成 (Steps 1-12)

### Step 1: TurnEnergyComponent 作成
**ファイル**: `naRou/ecs/components/components.py` に追加
```python
@dataclass
class TurnEnergyComponent:
    """ターン制御用エネルギー値 (ゲームループ核心)"""
    energy: int = 0
    speed: int = 70  # エンティティ固有の基準速度
    
    def to_dict(self) -> dict:
        return {"energy": self.energy, "speed": self.speed}
    
    @classmethod
    def from_dict(cls, data: dict) -> "TurnEnergyComponent":
        return cls(energy=data.get("energy", 0), speed=data.get("speed", 70))
```
**検証**: `python -c "from naRou.ecs.components.components import TurnEnergyComponent; c=TurnEnergyComponent(); assert c.energy==0"`

---

### Step 2: CombatIntentComponent 作成
**ファイル**: `naRou/ecs/components/components.py` に追加
```python
@dataclass
class CombatIntentComponent:
    """戦闘時の一時的意図・AIロール (描画/AI用途のみ・セーブ不要)"""
    next_intent: dict | None = None
    ai_role: str = "brute"
    preferred_range: int = 1
    
    def to_dict(self) -> dict:
        # 一時情報なのでセーブ時は既定値のみ
        return {"ai_role": self.ai_role, "preferred_range": self.preferred_range}
    
    @classmethod
    def from_dict(cls, data: dict) -> "CombatIntentComponent":
        return cls(
            ai_role=data.get("ai_role", "brute"),
            preferred_range=data.get("preferred_range", 1)
        )
```
**検証**: インスタンス化・デフォルト値確認

---

### Step 3: FaithComponent 作成
**ファイル**: `naRou/ecs/components/components.py` に追加
```python
@dataclass
class FaithComponent:
    """信仰・神システム"""
    god_id: str = "eyth"
    piety: int = 0
    received_servant: bool = False
    received_artifact: bool = False
    
    def to_dict(self) -> dict:
        return {
            "god_id": self.god_id,
            "piety": self.piety,
            "received_servant": self.received_servant,
            "received_artifact": self.received_artifact,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "FaithComponent":
        return cls(
            god_id=data.get("god_id", "eyth"),
            piety=data.get("piety", 0),
            received_servant=data.get("received_servant", False),
            received_artifact=data.get("received_artifact", False),
        )
```
**検証**: インスタンス化・シリアライズ往復確認

---

### Step 4: MutationComponent 作成
**ファイル**: `naRou/ecs/components/components.py` に追加
```python
@dataclass
class MutationComponent:
    """突然変異・エーテル病進行"""
    mutations: dict[str, int] = field(default_factory=dict)  # mutation_id -> level
    ether_disease_stages: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "mutations": dict(self.mutations),
            "ether_disease_stages": list(self.ether_disease_stages),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MutationComponent":
        return cls(
            mutations=data.get("mutations", {}),
            ether_disease_stages=data.get("ether_disease_stages", []),
        )
```
**検証**: 空・非空両ケースでシリアライズ往復

---

### Step 5: TutorialProgressComponent 作成
**ファイル**: `naRou/ecs/components/components.py` に追加
```python
@dataclass
class TutorialProgressComponent:
    """チュートリアル完了履歴・ポップアップ状態"""
    completed_tutorials: set[str] = field(default_factory=set)
    pending_tutorial_popup: dict[str, Any] | None = None
    
    def to_dict(self) -> dict:
        return {
            "completed_tutorials": list(self.completed_tutorials),
            "pending_tutorial_popup": self.pending_tutorial_popup,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TutorialProgressComponent":
        return cls(
            completed_tutorials=set(data.get("completed_tutorials", [])),
            pending_tutorial_popup=data.get("pending_tutorial_popup"),
        )
```
**検証**: set/list 変換確認

---

### Step 6: ResistanceComponent 作成
**ファイル**: `naRou/ecs/components/components.py` に追加
```python
@dataclass
class ResistanceComponent:
    """属性耐性・弱点 (基礎値のみ・装備分は別システムで合算)"""
    base_resistances: dict[str, int] = field(default_factory=dict)
    weaknesses: list[str] = field(default_factory=list)
    
    def get_resistance(self, element: str) -> int:
        return self.base_resistances.get(element, 0)
    
    def is_weak_to(self, element: str) -> bool:
        return element in self.weaknesses
    
    def to_dict(self) -> dict:
        return {
            "base_resistances": dict(self.base_resistances),
            "weaknesses": list(self.weaknesses),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ResistanceComponent":
        return cls(
            base_resistances=data.get("base_resistances", {}),
            weaknesses=data.get("weaknesses", []),
        )
```
**検証**: `get_resistance`/`is_weak_to` 動作確認

---

### Step 7: SkillInventoryComponent 作成
**ファイル**: `naRou/ecs/components/components.py` に追加
```python
@dataclass
class SkillInventoryComponent:
    """スキル所持・経験値管理 (既存 Skill クラス使用)"""
    skills: dict[str, Skill] = field(default_factory=dict)
    
    def ensure_default_skills(self, is_player_or_pet: bool) -> None:
        if not self.skills and is_player_or_pet:
            self.skills = {
                "martial_arts": Skill("格闘"),
                "short_sword": Skill("短剣"),
                "long_sword": Skill("長剣"),
                "evasion": Skill("回避"),
                "shield": Skill("盾"),
                "magic_cast": Skill("詠唱"),
                "healing": Skill("治癒"),
                "meditation": Skill("瞑想"),
                "faith": Skill("信仰"),
                "mining": Skill("採掘"),
                "fishing": Skill("釣り"),
                "cooking": Skill("料理"),
                "farming": Skill("栽培"),
                "performance": Skill("演奏"),
                "pickpocket": Skill("窃盗"),
                "anatomy": Skill("解剖学"),
                "negotiation": Skill("交渉"),
            }
    
    def gain_exp(self, skill_key: str, amount: int) -> list[str]:
        logs = []
        if skill_key not in self.skills:
            return logs
        skill = self.skills[skill_key]
        growth = int(amount * (skill.potential / 100.0))
        skill.experience += max(1, growth)
        needed = skill.level * 20
        while skill.experience >= needed:
            skill.experience -= needed
            skill.level += 1
            skill.potential = max(10, skill.potential - 2)
            needed = skill.level * 20
            logs.append(f"【{skill.name}】が Lv{skill.level} に成長した！")
        return logs
    
    def to_dict(self) -> dict:
        return {
            "skills": {
                k: {"name": s.name, "level": s.level, "experience": s.experience, "potential": s.potential}
                for k, s in self.skills.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SkillInventoryComponent":
        comp = cls()
        for sk_key, sk_dict in data.get("skills", {}).items():
            if sk_key in comp.skills:
                comp.skills[sk_key].level = sk_dict.get("level", 1)
                comp.skills[sk_key].experience = sk_dict.get("experience", 0)
                comp.skills[sk_key].potential = sk_dict.get("potential", 100)
        return comp
```
**検証**: デフォルトスキル生成・経験値加算・シリアライズ往復

---

### Step 8: PetComponent 作成 (petsリスト移管用)
**ファイル**: `naRou/ecs/components/components.py` に追加
```python
@dataclass
class PetComponent:
    """ペット一覧・召喚管理 (Entity 参照を保持)"""
    pets: list["Entity"] = field(default_factory=list)  # 前方参照
    
    def to_dict(self) -> dict:
        # ペットは個別にセーブされるためここでは ID のみ or 空
        return {"pet_count": len(self.pets)}
    
    @classmethod
    def from_dict(cls, data: dict) -> "PetComponent":
        return cls(pets=[])  # 実体復元は別プロセスで
```
**検証**: 空リスト初期化・追加/削除動作

---

### Step 9: BaseStatsComponent 補強 (派生ステータス計算式内包)
**ファイル**: `naRou/ecs/components/components.py` 既存 `BaseStatsComponent` を拡張
```python
@dataclass
class BaseStatsComponent:
    """基礎ステータス (HP/MP/Stamina 含む派生値計算も内包)"""
    hp: int = 10
    max_hp: int = 10
    mp: int = 10
    max_mp: int = 10
    stamina: int = 50
    max_stamina: int = 50
    
    # 計算式を静的メソッドとして保持 (Entity 属性参照のため)
    @staticmethod
    def calculate_max_hp(attributes, level: int, god_id: str) -> int:
        god_bonus = 10 if god_id == "jure" else 0
        base = attributes.endurance * 2 + attributes.strength + (level * 5) + god_bonus
        return max(10, base)
    
    @staticmethod
    def calculate_max_mp(attributes, level: int, god_id: str) -> int:
        god_bonus = 15 if god_id == "itzpalt" else 0
        base = attributes.magic * 2 + attributes.will + (level * 4) + god_bonus
        return max(10, base)
    
    @staticmethod
    def calculate_max_stamina(attributes) -> int:
        return max(50, attributes.endurance + attributes.will * 2)
    
    def recalculate(self, entity) -> None:
        """Entity 参照を受け取り全派生値再計算"""
        from naRou.ecs.components.components import AttributesComponent, LevelComponent, FaithComponent
        attrs = entity.get_component(AttributesComponent)
        level_comp = entity.get_component(LevelComponent)
        faith = entity.get_component(FaithComponent)
        
        self.max_hp = self.calculate_max_hp(attrs, level_comp.level, faith.god_id)
        self.max_mp = self.calculate_max_mp(attrs, level_comp.level, faith.god_id)
        self.max_stamina = self.calculate_max_stamina(attrs)
        
        self.hp = min(self.hp, self.max_hp)
        self.mp = min(self.mp, self.max_mp)
        self.stamina = min(self.stamina, self.max_stamina)
    
    def to_dict(self) -> dict:
        return {
            "hp": self.hp, "max_hp": self.max_hp,
            "mp": self.mp, "max_mp": self.max_mp,
            "stamina": self.stamina, "max_stamina": self.max_stamina,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "BaseStatsComponent":
        return cls(
            hp=data.get("hp", 10), max_hp=data.get("max_hp", 10),
            mp=data.get("mp", 10), max_mp=data.get("max_mp", 10),
            stamina=data.get("stamina", 50), max_stamina=data.get("max_stamina", 50),
        )
```
**検証**: 計算式が既存 `Entity.calculate_max_hp` 等と同一結果になること確認

---

### Step 10: LevelComponent 補強 (初期値設定ロジック追加)
**ファイル**: `naRou/ecs/components/components.py` 既存 `LevelComponent` を拡張
```python
@dataclass
class LevelComponent:
    """レベル・経験値・スキルポイント"""
    level: int = 1
    exp: int = 0
    exp_next: int = 100
    skill_points: int = 0
    total_skill_points_earned: int = 0
    
    def initialize_for_new_entity(self) -> None:
        """新規エンティティ用初期化"""
        self.level = 1
        self.exp = 0
        self.exp_next = 100
        self.skill_points = 0
        self.total_skill_points_earned = 0
    
    def to_dict(self) -> dict:
        return {
            "level": self.level, "exp": self.exp, "exp_next": self.exp_next,
            "skill_points": self.skill_points, "total_skill_points_earned": self.total_skill_points_earned,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "LevelComponent":
        return cls(
            level=data.get("level", 1), exp=data.get("exp", 0), exp_next=data.get("exp_next", 100),
            skill_points=data.get("skill_points", 0), total_skill_points_earned=data.get("total_skill_points_earned", 0),
        )
```
**検証**: `initialize_for_new_entity()` 呼び出し後の値確認

---

### Step 11: 既存コンポーネントの to_dict/from_dict 実装補完
**対象**: `TitleComponent`, `GuildFactionComponent`, `AchievementComponent`, `ReincarnationComponent`, `SkillTreeJobComponent`, `SkillFusionComponent`, `StorytellerComponent`, `ProceduralQuestComponent`, `ArchaeologyComponent`, `AffectionComponent`, `PetProfileComponent`, `EmoteComponent`, `PetAIComponent`, `BaseStatsComponent` (Step 9), `LevelComponent` (Step 10), `AttributesComponent` (既存実装済み), `EconomyComponent`, `StatusEffectsComponent`, `HuskInventoryComponent`
**作業**: 不足分の `to_dict`/`from_dict` を全て実装 (dataclass の `__dict__` 利用で簡易実装可)
**検証**: 各コンポーネントで `comp.to_dict()` → `Comp.from_dict(...)` ラウンドトリップテスト

---

### Step 12: components/__init__.py に新規コンポーネント export 追加
**ファイル**: `naRou/ecs/components/__init__.py`
```python
from .components import (
    # 既存...
    TurnEnergyComponent,
    CombatIntentComponent,
    FaithComponent,
    MutationComponent,
    TutorialProgressComponent,
    ResistanceComponent,
    SkillInventoryComponent,
    PetComponent,
)
```
**検証**: `from naRou.ecs.components import TurnEnergyComponent, FaithComponent, ...` で import 成功

---

## Phase 2: Entity.__init__ からのフィールド剥離 (Steps 13-24)

### Step 13: `energy` フィールド剥離 → TurnEnergyComponent
**ファイル**: `naRou/ecs/entity.py`
- `__init__` 内の `self.energy = 0` を削除
- `_init_components()` 内で `self.components[TurnEnergyComponent] = TurnEnergyComponent(speed=self.speed)` を追加
- `speed` は TurnEnergyComponent にも保持 (ゲームループで参照)
**検証**: `entity.get_component(TurnEnergyComponent).energy == 0` 確認

---

### Step 14: `next_intent`/`ai_role`/`preferred_range` 剥離 → CombatIntentComponent
**ファイル**: `naRou/ecs/entity.py`
- `__init__` 内の 3行 (`self.next_intent = None`, `self.ai_role = ...`, `self.preferred_range = ...`) を削除
- `_init_components()` 内で `self.components[CombatIntentComponent] = CombatIntentComponent(ai_role=self._default_ai_role(name))` を追加
- `_default_ai_role` メソッドは一旦残す (Step 47 で移動)
**検証**: `entity.get_component(CombatIntentComponent).ai_role` が名前から正しく判定されること

---

### Step 15: `tactic` フィールド剥離 → PetAIComponent 完全委譲
**ファイル**: `naRou/ecs/entity.py`
- `__init__` 内の `self.tactic = PetAI.TACTIC_ASSAULT` を削除
- `PetAIComponent` に `tactic` フィールド追加 (Step 1 で未追加なら追加)
- `_init_components()` で `PetAIComponent()` 初期化時にデフォルト設定
**検証**: `entity.get_component(PetAIComponent).tactic == "assault"`

---

### Step 16: 信仰フィールド剥離 → FaithComponent
**ファイル**: `naRou/ecs/entity.py`
- `__init__` 内の 4行 (`god_id`, `piety`, `received_servant`, `received_artifact`) を削除
- `_init_components()` 内で `self.components[FaithComponent] = FaithComponent()` を追加 (デフォルト値使用)
**検証**: `entity.get_component(FaithComponent).god_id == "eyth"`

---

### Step 17: 突然変異/エーテル病フィールド剥離 → MutationComponent
**ファイル**: `naRou/ecs/entity.py`
- `__init__` 内の `self.mutations = {}`, `self.ether_disease_stages = []` を削除
- `_init_components()` 内で `self.components[MutationComponent] = MutationComponent()` を追加
**検証**: 空辞書・空リストで初期化されること

---

### Step 18: チュートリアルフィールド剥離 → TutorialProgressComponent
**ファイル**: `naRou/ecs/entity.py`
- `__init__` 内の `self.completed_tutorials = set()`, `self.pending_tutorial_popup = None` を削除
- `_init_components()` 内で `self.components[TutorialProgressComponent] = TutorialProgressComponent()` を追加
**検証**: 空セット・None で初期化されること

---

### Step 19: 属性耐性/弱点フィールド剥離 → ResistanceComponent
**ファイル**: `naRou/ecs/entity.py`
- `__init__` 内の `self.base_resistances = {}`, `self.weaknesses = []` を削除 (現在は `_init_components` 内行 182-183)
- `_init_components()` 内で `self.components[ResistanceComponent] = ResistanceComponent()` を追加
**検証**: `entity.get_component(ResistanceComponent).base_resistances == {}`

---

### Step 20: `_skills` フィールド剥離 → SkillInventoryComponent
**ファイル**: `naRou/ecs/entity.py`
- `__init__` 内の `_skills` 初期化ブロック (行 102-105) を削除
- `_init_components()` 内で:
  ```python
  skill_comp = SkillInventoryComponent()
  skill_comp.ensure_default_skills(self.is_player or self.is_pet)
  self.components[SkillInventoryComponent] = skill_comp
  ```
- `_init_default_skills` メソッドは一旦残す (Step 48 で移動)
**検証**: プレイヤー/ペットでデフォルトスキル17種が生成されること

---

### Step 21: `pets` フィールド剥離 → PetComponent
**ファイル**: `naRou/ecs/entity.py`
- `__init__` 内の `self.pets = []` を削除
- `_init_components()` 内で `self.components[PetComponent] = PetComponent()` を追加
**検証**: `entity.get_component(PetComponent).pets == []`

---

### Step 22: 派生ステータス直接代入剥離 → BaseStatsComponent 初期化
**ファイル**: `naRou/ecs/entity.py`
- `__init__` 末尾の 6行 (`self.max_hp = ...`, `self.hp = ...`, `self.max_mp = ...`, `self.mp = ...`, `self.max_stamina = ...`, `self.stamina = ...`) を削除
- `_init_components()` 終了後、`BaseStatsComponent` を取得し初期計算実行:
  ```python
  stats = self.get_component(BaseStatsComponent)
  stats.recalculate(self)  # Step 9 で実装したメソッド
  ```
- `_apply_init_attributes()` 実行後に行うこと (属性値確定後)
**検証**: 作成直後の entity で `entity.hp == entity.max_hp > 0` 等

---

### Step 23: レベル/経験値直接代入剥離 → LevelComponent 初期化
**ファイル**: `naRou/ecs/entity.py`
- `__init__` 内の `self.level = 1`, `self.exp = 0`, `self.exp_next = 100` を削除
- `_init_components()` 後、`LevelComponent` を取得し `initialize_for_new_entity()` 呼び出し
**検証**: `entity.level == 1`, `entity.exp == 0`, `entity.exp_next == 100`

---

### Step 24: `_apply_init_attributes` / `_init_components` 整理・新構成対応
**ファイル**: `naRou/ecs/entity.py`
- `_init_components()` を全コンポーネント登録に更新 (Phase 1 で作成した 6つ + 既存含む全 20+ 種)
- `_apply_init_attributes()` は属性値適用のみに専念 (ベース値保存ロジックは残す)
- 不要になった import (`DEFAULT_GOD_ID`, `KITER_PREFERRED_RANGE`, `AI_ROLE_KITER` 等) を整理
- 型ヒント `T` 等未使用なら削除
**検証**: 
- `Entity()` インスタンス化エラーなし
- 全コンポーネントが `entity.components` に登録されていること
- 既存テスト通過 (`python -m pytest tests/ -x -q`)

---

## Phase 3: プロパティ委譲・後方互換レイヤー (Steps 25-36)

### Step 25: `hp`/`max_hp` プロパティ → BaseStatsComponent 完全委譲
**ファイル**: `naRou/ecs/entity.py`
- 既存プロパティ (行 310-324) を以下に書き換え:
```python
@property
def hp(self) -> int:
    return self.get_component(BaseStatsComponent).hp

@hp.setter
def hp(self, val: int):
    self.get_component(BaseStatsComponent).hp = val

@property
def max_hp(self) -> int:
    return self.get_component(BaseStatsComponent).max_hp

@max_hp.setter
def max_hp(self, val: int):
    self.get_component(BaseStatsComponent).max_hp = val
```
**検証**: `entity.hp = 50; assert entity.hp == 50` / `entity.max_hp = 100; assert entity.max_hp == 100`

---

### Step 26: `mp`/`max_mp` プロパティ → BaseStatsComponent 完全委譲
**ファイル**: `naRou/ecs/entity.py`
- 既存プロパティ (行 326-340) を同様に書き換え
**検証**: `entity.mp = 30; assert entity.mp == 30`

---

### Step 27: `stamina`/`max_stamina` プロパティ → BaseStatsComponent 完全委譲
**ファイル**: `naRou/ecs/entity.py`
- 既存にプロパティがなければ新規追加 (現在は生フィールドアクセス)
- `BaseStatsComponent` に `stamina`/`max_stamina` フィールド存在確認 (Step 9 で追加済み)
```python
@property
def stamina(self) -> int:
    return self.get_component(BaseStatsComponent).stamina

@stamina.setter
def stamina(self, val: int):
    self.get_component(BaseStatsComponent).stamina = val

@property
def max_stamina(self) -> int:
    return self.get_component(BaseStatsComponent).max_stamina

@max_stamina.setter
def max_stamina(self, val: int):
    self.get_component(BaseStatsComponent).max_stamina = val
```
**検証**: `entity.stamina = 60; assert entity.stamina == 60`

---

### Step 28: `energy` プロパティ → TurnEnergyComponent へ委譲
**ファイル**: `naRou/ecs/entity.py`
- 新規プロパティ追加:
```python
@property
def energy(self) -> int:
    return self.get_component(TurnEnergyComponent).energy

@energy.setter
def energy(self, val: int):
    self.get_component(TurnEnergyComponent).energy = val

@property
def speed(self) -> int:
    return self.get_component(TurnEnergyComponent).speed

@speed.setter
def speed(self, val: int):
    self.get_component(TurnEnergyComponent).speed = val
```
- `__init__` の `self.speed = speed` は TurnEnergyComponent 初期化に渡すよう Step 13 で修正済み
**検証**: `entity.energy = 100; assert entity.energy == 100`

---

### Step 29: `tactic` プロパティ → PetAIComponent へ委譲
**ファイル**: `naRou/ecs/entity.py`
- 既存の生フィールドアクセスをプロパティ化:
```python
@property
def tactic(self) -> str:
    return self.get_component(PetAIComponent).tactic

@tactic.setter
def tactic(self, val: str):
    self.get_component(PetAIComponent).tactic = val
```
- `PetAIComponent` に `tactic: str = "assault"` フィールド追加確認 (Step 15 で実施)
**検証**: `entity.tactic = "defend"; assert entity.tactic == "defend"`

---

### Step 30: 信仰フィールドプロパティ → FaithComponent へ委譲
**ファイル**: `naRou/ecs/entity.py`
- `god_id`, `piety`, `received_servant`, `received_artifact` の 4プロパティ追加:
```python
@property
def god_id(self) -> str:
    return self.get_component(FaithComponent).god_id

@god_id.setter
def god_id(self, val: str):
    self.get_component(FaithComponent).god_id = val

@property
def piety(self) -> int:
    return self.get_component(FaithComponent).piety

@piety.setter
def piety(self, val: int):
    self.get_component(FaithComponent).piety = val

@property
def received_servant(self) -> bool:
    return self.get_component(FaithComponent).received_servant

@received_servant.setter
def received_servant(self, val: bool):
    self.get_component(FaithComponent).received_servant = val

@property
def received_artifact(self) -> bool:
    return self.get_component(FaithComponent).received_artifact

@received_artifact.setter
def received_artifact(self, val: bool):
    self.get_component(FaithComponent).received_artifact = val
```
**検証**: 各プロパティの get/set 動作確認

---

### Step 31: 突然変異/エーテル病プロパティ → MutationComponent へ委譲
**ファイル**: `naRou/ecs/entity.py`
```python
@property
def mutations(self) -> dict[str, int]:
    return self.get_component(MutationComponent).mutations

@mutations.setter
def mutations(self, val: dict[str, int]):
    self.get_component(MutationComponent).mutations = val

@property
def ether_disease_stages(self) -> list[str]:
    return self.get_component(MutationComponent).ether_disease_stages

@ether_disease_stages.setter
def ether_disease_stages(self, val: list[str]):
    self.get_component(MutationComponent).ether_disease_stages = val
```
**検証**: `entity.mutations["fire"] = 2; assert entity.mutations["fire"] == 2`

---

### Step 32: チュートリアルプロパティ → TutorialProgressComponent へ委譲
**ファイル**: `naRou/ecs/entity.py`
```python
@property
def completed_tutorials(self) -> set[str]:
    return self.get_component(TutorialProgressComponent).completed_tutorials

@completed_tutorials.setter
def completed_tutorials(self, val: set[str]):
    self.get_component(TutorialProgressComponent).completed_tutorials = val

@property
def pending_tutorial_popup(self) -> dict[str, Any] | None:
    return self.get_component(TutorialProgressComponent).pending_tutorial_popup

@pending_tutorial_popup.setter
def pending_tutorial_popup(self, val: dict[str, Any] | None):
    self.get_component(TutorialProgressComponent).pending_tutorial_popup = val
```
**検証**: セット操作・ポップアップ設定動作確認

---

### Step 33: 属性耐性/弱点プロパティ → ResistanceComponent へ委譲
**ファイル**: `naRou/ecs/entity.py`
```python
@property
def base_resistances(self) -> dict[str, int]:
    return self.get_component(ResistanceComponent).base_resistances

@base_resistances.setter
def base_resistances(self, val: dict[str, int]):
    self.get_component(ResistanceComponent).base_resistances = val

@property
def weaknesses(self) -> list[str]:
    return self.get_component(ResistanceComponent).weaknesses

@weaknesses.setter
def weaknesses(self, val: list[str]):
    self.get_component(ResistanceComponent).weaknesses = val
```
- 既存メソッド `get_elemental_resistance`/`is_weak_to` は Step 46 で移動予定
**検証**: 耐性値設定・取得動作確認

---

### Step 34: `skills` プロパティ → SkillInventoryComponent へ委譲
**ファイル**: `naRou/ecs/entity.py`
- 既存プロパティ (行 1243-1251) を書き換え:
```python
@property
def skills(self) -> dict[str, Skill]:
    return self.get_component(SkillInventoryComponent).skills

@skills.setter
def skills(self, value: dict[str, Skill]):
    self.get_component(SkillInventoryComponent).skills = value
```
**検証**: `entity.skills["new_skill"] = Skill("新スキル"); assert "new_skill" in entity.skills`

---

### Step 35: `pets` プロパティ → PetComponent へ委譲
**ファイル**: `naRou/ecs/entity.py`
```python
@property
def pets(self) -> list["Entity"]:
    return self.get_component(PetComponent).pets

@pets.setter
def pets(self, val: list["Entity"]):
    self.get_component(PetComponent).pets = val
```
**検証**: `entity.pets.append(pet); assert pet in entity.pets`

---

### Step 36: `level`/`exp`/`exp_next`/`skill_points` プロパティ → LevelComponent 完全委譲
**ファイル**: `naRou/ecs/entity.py`
- 既存プロパティ (行 351-389) が既に `LevelComponent` へ委譲されていることを確認
- 不足分 (`exp_next` 等) があれば追加
- 重複定義 (SkillTreeJobComponent 側にも `skill_points` あり 行 778-783) を整理:
  - `LevelComponent.skill_points` を唯一のソースとする
  - `SkillTreeJobComponent.skill_points` プロパティは `LevelComponent` へ委譲するよう修正
**検証**: 
- `entity.level = 5; assert entity.level == 5`
- `entity.exp = 50; assert entity.exp == 50`
- `entity.skill_points` が両コンポーネントで同期

---

## Phase 4: 計算ロジック移行 (Steps 37-48)

### Step 37: `calculate_max_hp` → BaseStatsComponent 静的メソッド化 (完了済み確認)
**ファイル**: `naRou/ecs/components/components.py` (Step 9 で実装済み)
- `BaseStatsComponent.calculate_max_hp(attributes, level, god_id)` として実装済み
- `Entity.calculate_max_hp()` メソッド (行 1253-1258) を削除
- 呼び出し箇所を `BaseStatsComponent.calculate_max_hp(...)` に書き換え
**検証**: 同一入力で同一出力になること確認

---

### Step 38: `calculate_max_mp` → BaseStatsComponent 静的メソッド化 (完了済み確認)
**ファイル**: `naRou/ecs/components/components.py` (Step 9 で実装済み)
- `Entity.calculate_max_mp()` メソッド (行 1260-1263) を削除
**検証**: 同一入力で同一出力

---

### Step 39: `calculate_max_stamina` → BaseStatsComponent 静的メソッド化 (完了済み確認)
**ファイル**: `naRou/ecs/components/components.py` (Step 9 で実装済み)
- `Entity.calculate_max_stamina()` メソッド (行 1265-1266) を削除
**検証**: 同一入力で同一出力

---

### Step 40: `recalculate_stats` → BaseStatsComponent.recalculate(entity) へ移動
**ファイル**: `naRou/ecs/entity.py` 行 1268-1301 → `naRou/ecs/components/components.py`
- `Entity.recalculate_stats()` メソッド全体を削除
- `BaseStatsComponent.recalculate(self, entity)` (Step 9 で実装済み) を使用
- 呼び出し箇所: `entity.get_component(BaseStatsComponent).recalculate(entity)`
- パッシブスキルボーナス適用部分 (行 1284-1297) は Step 45 で別途移動
**検証**: レベルアップ・装備変更後にステータス正しく再計算されること

---

### Step 41: `gain_exp` → LevelComponent.gain_exp(entity, amount) へ移動
**ファイル**: `naRou/ecs/entity.py` 行 1303-1343 → `naRou/ecs/components/components.py` (LevelComponent にメソッド追加)
```python
# LevelComponent に追加
def gain_exp(self, entity, amount: int) -> list[str]:
    logs = []
    self.exp += amount
    # ジョブ経験値ボーナス: 獲得経験値の10%を加算
    job_exp_gain = max(1, int(amount * 0.10))
    # JobComponent 側で処理するためイベント発行 or 直接呼び出し
    # ここではログのみ返す
    while self.exp >= self.exp_next:
        self.exp -= self.exp_next
        self.level += 1
        # 属性成長処理 (Step 44 で分離)
        # スキルポイント付与
        sp_gain = 5
        self.skill_points += sp_gain
        self.total_skill_points_earned += sp_gain
        logs.append(f"{entity.name}はレベル {self.level} に上がった！ (+{sp_gain}SP)")
    return logs
```
- `Entity.gain_exp()` を削除し、`entity.get_component(LevelComponent).gain_exp(entity, amount)` に置換
- 属性成長ロジック (行 1313-1332) は Step 44 へ
**検証**: 経験値獲得→レベルアップ→SP付与・ログ出力のフロー動作確認

---

### Step 42: `gain_skill_exp` → SkillInventoryComponent.gain_exp(skill_key, amount) へ移動
**ファイル**: `naRou/ecs/entity.py` 行 1345-1359 → `naRou/ecs/components/components.py` (Step 7 で実装済み)
- `Entity.gain_skill_exp()` メソッドを削除
- 呼び出し箇所を `entity.get_component(SkillInventoryComponent).gain_exp(skill_key, amount)` に置換
**検証**: スキル経験値獲得→レベルアップ→潜在能力低下のフロー動作確認

---

### Step 43: `pray_to_god` → FaithComponent.pray(entity) へ移動
**ファイル**: `naRou/ecs/entity.py` 行 1361-1372 → `naRou/ecs/components/components.py` (FaithComponent にメソッド追加)
```python
# FaithComponent に追加
def pray(self, entity) -> tuple[bool, str]:
    from naRou.god_system import GodInfo
    from naRou.ecs.components.components import BaseStatsComponent
    
    if self.god_id == "eyth":
        return False, "あなたは特定の神を信仰していない。"
    if self.piety < 50:
        return False, "神はあなたの祈りにまだ耳を傾けてくれない…(信仰度が不足)"
    
    stats = entity.get_component(BaseStatsComponent)
    stats.hp = stats.max_hp
    stats.mp = stats.max_mp
    self.piety = max(0, self.piety - 30)
    god_name = GodInfo.GODS[self.god_id]["name"]
    return True, f"神【{god_name}】の御手があなたを包み込み、傷と魔力が全快した！"
```
- `Entity.pray_to_god()` を削除し、`entity.get_component(FaithComponent).pray(entity)` に置換
**検証**: 信仰度50以上で全快・信仰度減少、未満で失敗メッセージ

---

### Step 44: レベルアップ時属性成長ロジック分離
**ファイル**: `naRou/ecs/entity.py` 行 1313-1332 → `naRou/ecs/components/components.py` (LevelComponent + AttributesComponent)
- `LevelComponent` に `apply_level_up_attribute_growth(entity)` メソッド追加:
```python
def apply_level_up_attribute_growth(self, entity) -> list[str]:
    from naRou.ecs.components.components import AttributesComponent
    import random
    
    attrs = entity.get_component(AttributesComponent)
    base_attrs = entity.get_component(AttributesComponent)  # _base_attributes は AttributesComponent に移行済み
    
    attr_pool = ["strength", "endurance", "dexterity", "perception", 
                 "learning", "will", "magic", "charisma"]
    grown = random.sample(attr_pool, 2)
    logs = []
    for chosen in grown:
        current = getattr(attrs, chosen)
        setattr(attrs, chosen, current + 1)
        # ベース値も更新 (AttributesComponent 内に base_values 保持推奨)
        logs.append(f"{chosen} が上昇した！")
    return logs
```
- `Entity.gain_exp()` 内の属性成長ブロックを削除し、レベルアップ時にこのメソッド呼び出し
**検証**: レベルアップ時にランダム2属性が+1されること

---

### Step 45: パッシブスキルボーナス適用移動
**ファイル**: `naRou/ecs/entity.py` 行 1284-1297 → 専用システムまたは SkillTreeJobComponent
- `Entity.recalculate_stats()` 内のパッシブスキル集計ロジックを削除
- `SkillTreeJobComponent` または新規 `PassiveBonusSystem` に `aggregate_bonuses(entity)` 実装
- `BaseStatsComponent.recalculate()` 内でボーナス適用:
```python
def recalculate(self, entity) -> None:
    # ... 既存計算 ...
    # パッシブボーナス適用
    from naRou.ecs.components.components import SkillTreeJobComponent
    job_comp = entity.get_component(SkillTreeJobComponent)
    bonuses = job_comp.aggregate_passive_bonuses(entity)
    if "max_hp_bonus" in bonuses:
        self.max_hp += int(bonuses["max_hp_bonus"])
        self.hp = min(self.hp, self.max_hp)
    if "mp_regen_bonus" in bonuses:
        entity.passive_mp_regen = bonuses["mp_regen_bonus"]
```
**検証**: パッシブスキル習得時に HP上限・MP再生等が正しく反映されること

---

### Step 46: `get_elemental_resistance`/`is_weak_to` → ResistanceComponent へ移動
**ファイル**: `naRou/ecs/entity.py` 行 228-238 → `naRou/ecs/components/components.py` (Step 6 で実装済み)
- `Entity.get_elemental_resistance()` / `is_weak_to()` を削除
- `ResistanceComponent.get_resistance(element)` / `is_weak_to(element)` を使用
- 装備耐性合算ロジック (行 231-233) はインベントリシステム側で行い、結果を `ResistanceComponent` に反映する設計に変更
**検証**: 耐性値取得・弱点判定が正しく動作

---

### Step 47: `_default_ai_role` → CombatIntentComponent / AIシステムへ移動
**ファイル**: `naRou/ecs/entity.py` 行 1211-1220 → `naRou/ecs/components/components.py` (CombatIntentComponent にクラスメソッド追加)
```python
# CombatIntentComponent に追加
@classmethod
def determine_ai_role(cls, name: str) -> tuple[str, int]:
    from naRou.constants import AI_ROLE_BRUTE, AI_ROLE_FLANKER, AI_ROLE_KITER, KITER_PREFERRED_RANGE
    n = name or ""
    if any(k in n for k in ("弓", "魔", "術", "caster", "Mage", "Archer")):
        return AI_ROLE_KITER, KITER_PREFERRED_RANGE
    if any(k in n for k in ("騎", "騎士", "knight", "Knight")):
        return AI_ROLE_FLANKER, 1
    return AI_ROLE_BRUTE, 1
```
- `Entity._default_ai_role()` を削除
- `CombatIntentComponent` 初期化時 (Step 14) に `ai_role, preferred_range = CombatIntentComponent.determine_ai_role(name)` で設定
**検証**: モンスター名から正しい AIロール・射程が判定されること

---

### Step 48: `_init_default_skills` → SkillInventoryComponent.ensure_default_skills へ移動 (完了済み確認)
**ファイル**: `naRou/ecs/entity.py` 行 1222-1241 → `naRou/ecs/components/components.py` (Step 7 で実装済み)
- `Entity._init_default_skills()` メソッドを削除
- Step 20 で `SkillInventoryComponent.ensure_default_skills()` 呼び出し済み
**検証**: プレイヤー/ペット作成時にデフォルトスキル17種が生成されること

---

## Phase 5: シリアライズ・デシリアライズ移行 (Steps 49-60)

### Step 49: `to_dict` コンポーネント部分解・各コンポーネント `to_dict` 呼び出し化
**ファイル**: `naRou/ecs/entity.py` 行 1374-1453
- 現在の `to_dict()` 内で手動で各フィールドを辞書化している部分を削除
- 代わりにコンポーネント辞書をループして各コンポーネントの `to_dict()` を呼び出し:
```python
def to_dict(self) -> dict[str, Any]:
    data: dict[str, Any] = {
        "x": self.x, "y": self.y, "char": self.char, "color": list(self.color),
        "name": self.name, "is_player": self.is_player, "is_pet": self.is_pet,
        "speed": self.speed,  # TurnEnergyComponent.speed も参照可能
        "energy": self.get_component(TurnEnergyComponent).energy,
        "components": {},
    }
    # 各コンポーネントの to_dict() を統一的に呼び出し
    for comp_type, comp in self.components.items():
        comp_name = comp_type.__name__
        if hasattr(comp, 'to_dict') and callable(getattr(comp, 'to_dict')):
            data["components"][comp_name] = comp.to_dict()
        else:
            # フォールバック (Step 11 で全コンポーネント実装済みなら不要)
            data["components"][comp_name] = {k: v for k, v in comp.__dict__.items() if not callable(v)}
    return data
```
**検証**: `entity.to_dict()` 実行時、全コンポーネントデータが `components` キー以下に格納されること

---

### Step 50: `from_dict` コンポーネント部分解・各コンポーネント `from_dict` 呼び出し化
**ファイル**: `naRou/ecs/entity.py` 行 1455-1526
- 現在の手動復元ロジックを削除
- コンポーネント辞書をループして各コンポーネントの `from_dict()` を呼び出し:
```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Entity:
    # 基本フィールドのみでインスタンス生成
    attrs = Attributes.from_dict(data.get("attributes", {}))
    ent = cls(
        x=data.get("x", 0), y=data.get("y", 0),
        char=data.get("char", "@"), color=tuple(data.get("color", [255,255,255])),
        name=data.get("name", "Unknown"), is_player=data.get("is_player", False),
        is_pet=data.get("is_pet", False), speed=data.get("speed", 70),
        attributes=attrs,
    )
    # コンポーネント復元
    comp_data_dict = data.get("components", {})
    for comp_type, comp in ent.components.items():
        comp_name = comp_type.__name__
        if comp_name in comp_data_dict:
            if hasattr(comp_type, 'from_dict') and callable(getattr(comp_type, 'from_dict')):
                new_comp = comp_type.from_dict(comp_data_dict[comp_name])
                comp.__dict__.update(new_comp.__dict__)
            else:
                for k, v in comp_data_dict[comp_name].items():
                    setattr(comp, k, v)
    return ent
```
**検証**: `Entity.from_dict(entity.to_dict())` で同等エンティティ復元

---

### Step 51: TurnEnergyComponent シリアライズ実装確認
**ファイル**: `naRou/ecs/components/components.py` (Step 1 で実装済み)
- `to_dict()`: `{"energy": self.energy, "speed": self.speed}`
- `from_dict()`: 両フィールド復元
**検証**: ラウンドトリップテスト `comp.to_dict() -> TurnEnergyComponent.from_dict(...)`

---

### Step 52: CombatIntentComponent シリアライズ実装確認
**ファイル**: `naRou/ecs/components/components.py` (Step 2 で実装済み)
- `to_dict()`: 一時情報 `next_intent` 除外、`ai_role`/`preferred_range` のみ
- `from_dict()`: 両フィールド復元、`next_intent` は None
**検証**: ラウンドトリップテスト

---

### Step 53: FaithComponent シリアライズ実装確認
**ファイル**: `naRou/ecs/components/components.py` (Step 3 で実装済み)
- 4フィールド全て `to_dict`/`from_dict` 対応
**検証**: ラウンドトリップテスト

---

### Step 54: MutationComponent シリアライズ実装確認
**ファイル**: `naRou/ecs/components/components.py` (Step 4 で実装済み)
- `mutations` (dict), `ether_disease_stages` (list) 対応
- set/list 変換注意
**検証**: ラウンドトリップテスト

---

### Step 55: TutorialProgressComponent シリアライズ実装確認
**ファイル**: `naRou/ecs/components/components.py` (Step 5 で実装済み)
- `completed_tutorials` (set -> list), `pending_tutorial_popup` (dict/None) 対応
**検証**: ラウンドトリップテスト

---

### Step 56: ResistanceComponent シリアライズ実装確認
**ファイル**: `naRou/ecs/components/components.py` (Step 6 で実装済み)
- `base_resistances` (dict), `weaknesses` (list) 対応
**検証**: ラウンドトリップテスト

---

### Step 57: SkillInventoryComponent シリアライズ実装確認
**ファイル**: `naRou/ecs/components/components.py` (Step 7 で実装済み)
- `skills` 辞書を `{key: {name, level, experience, potential}}` 形式で出力
- `from_dict` で既存 Skill インスタンスに値復元
**検証**: ラウンドトリップテスト (スキルレベル・経験値・潜在能力が保持)

---

### Step 58: PetComponent シリアライズ実装確認
**ファイル**: `naRou/ecs/components/components.py` (Step 8 で実装済み)
- `pets` リストは Entity 参照のため ID のみ or 空で保存 (実体は別セーブ)
- `to_dict()`: `{"pet_count": len(self.pets)}`
**検証**: ペット数保存・復元時空リスト

---

### Step 59: BaseStatsComponent シリアライズ実装確認
**ファイル**: `naRou/ecs/components/components.py` (Step 9 で実装済み)
- `hp`, `max_hp`, `mp`, `max_mp`, `stamina`, `max_stamina` 6フィールド
**検証**: ラウンドトリップテスト

---

### Step 60: LevelComponent シリアライズ実装確認
**ファイル**: `naRou/ecs/components/components.py` (Step 10 で実装済み)
- `level`, `exp`, `exp_next`, `skill_points`, `total_skill_points_earned` 5フィールド
**検証**: ラウンドトリップテスト

---

## Phase 6: テスト・検証・クリーンアップ (Steps 61-72)

### Step 61: 単体テスト - 新規コンポーネント各種
**ファイル**: `tests/test_ecs_new_components.py` (新規作成)
- `TurnEnergyComponent`: 初期化・energy加減算・シリアライズ
- `CombatIntentComponent`: 初期化・AIロール判定・シリアライズ
- `FaithComponent`: 信仰度加減算・祈り実行・シリアライズ
- `MutationComponent`: 突然変異追加/削除・エーテル病進行・シリアライズ
- `TutorialProgressComponent`: 完了追加・ポップアップ設定・シリアライズ
- `ResistanceComponent`: 耐性設定・弱点判定・シリアライズ
- `SkillInventoryComponent`: デフォルト生成・経験値加算・レベルアップ・シリアライズ
- `PetComponent`: ペット追加/削除・シリアライズ
**実行**: `python -m pytest tests/test_ecs_new_components.py -v`

---

### Step 62: 単体テスト - Entity プロパティ委譲網羅
**ファイル**: `tests/test_entity_property_delegation.py` (新規作成)
- 全プロパティ (`hp`, `mp`, `stamina`, `energy`, `tactic`, `god_id`, `piety`, `mutations`, `skills`, `pets`, `level`, `exp`, `base_resistances`, `weaknesses`, `completed_tutorials`, 等) について:
  - getter でコンポーネント値取得
  - setter でコンポーネント値更新
  - 直接フィールドアクセス (`entity._components[Comp].field`) と同期
**実行**: `python -m pytest tests/test_entity_property_delegation.py -v`

---

### Step 63: 統合テスト - Entity フルライフサイクル
**ファイル**: `tests/test_entity_lifecycle.py` (新規作成)
```python
def test_entity_full_lifecycle():
    # 1. 作成
    entity = Entity(name="Test", is_player=True)
    assert entity.hp == entity.max_hp > 0
    assert entity.level == 1
    assert entity.god_id == "eyth"
    
    # 2. 経験値獲得・レベルアップ
    logs = entity.get_component(LevelComponent).gain_exp(entity, 1000)
    assert entity.level > 1
    assert entity.skill_points > 0
    
    # 3. スキル成長
    skill_logs = entity.get_component(SkillInventoryComponent).gain_exp("martial_arts", 500)
    assert entity.skills["martial_arts"].level > 1
    
    # 4. 信仰変更・祈り
    entity.piety = 100
    entity.god_id = "jure"
    success, msg = entity.get_component(FaithComponent).pray(entity)
    assert success
    assert entity.hp == entity.max_hp
    
    # 5. セーブ/ロード
    data = entity.to_dict()
    entity2 = Entity.from_dict(data)
    assert entity2.name == entity.name
    assert entity2.level == entity.level
    assert entity2.skills["martial_arts"].level == entity.skills["martial_arts"].level
    assert entity2.piety == entity.piety
```
**実行**: `python -m pytest tests/test_entity_lifecycle.py -v`

---

### Step 64: 既存テストスイート全実行・回帰確認
**コマンド**: `python -m pytest tests/ -x -q`
- 全テスト通過を確認
- 失敗するテストがあれば原因特定・修正 (別ステップで対応)
**合格基準**: 既存テスト 0 失敗

---

### Step 65: Entity クラスから未使用 import・デッドコード削除
**ファイル**: `naRou/ecs/entity.py`
- 未使用 import 削除: `DEFAULT_GOD_ID`, `KITER_PREFERRED_RANGE`, `AI_ROLE_KITER`, `AI_ROLE_BRUTE`, `AI_ROLE_FLANKER`, `random` (使用箇所移動済みなら), `logging` (使用残なら残す), `delegate` (使用残なら残す), `GodInfo` (FaithComponent に移動済みなら削除), `field` (dataclass 使用残なら残す), `Any`, `TypeVar` 等
- 未使用メソッド削除: `calculate_max_hp`, `calculate_max_mp`, `calculate_max_stamina`, `recalculate_stats`, `gain_exp`, `gain_skill_exp`, `pray_to_god`, `_default_ai_role`, `_init_default_skills`, `_apply_init_attributes` (中身空なら)
- 未使用フィールド初期化コード削除確認
**検証**: `ruff check naRou/ecs/entity.py` で未使用 import エラーなし

---

### Step 66: 循環インポート解消
**確認箇所**: 
- `entity.py` → `components.py` (OK: 一方向)
- `components.py` → `entity.py` (NG: 前方参照 `Entity` 使用箇所)
- `PetComponent.pets: list["Entity"]` は `TYPE_CHECKING` ガードで回避
- `BaseStatsComponent.recalculate(entity)` 引数型ヒントを `TYPE_CHECKING` で `Entity` import
- `LevelComponent.gain_exp(entity)` 等も同様
- `FaithComponent.pray(entity)` 等も同様
**修正**: `from __future__ import annotations` 既にあり、文字列アノテーションで回避確認
**検証**: `python -c "import naRou.ecs.entity; import naRou.ecs.components.components"` エラーなし

---

### Step 67: 型ヒント・mypy チェック通過
**コマンド**: `python -m mypy naRou/ecs/entity.py naRou/ecs/components/components.py --strict`
- 型エラー 0 を目標
- `Entity` 前方参照、`Component` 型変数、`get_component` 戻り値型等調整
**合格基準**: mypy エラー 0

---

### Step 68: ruff/lint チェック通過
**コマンド**: `ruff check naRou/ecs/entity.py naRou/ecs/components/components.py`
- 全ルール通過 (未使用変数、インポート順序、行長等)
- `ruff format` でフォーマット統一
**合格基準**: lint エラー 0

---

### Step 69: パフォーマンス計測
**ファイル**: `tests/test_entity_performance.py` (新規作成)
```python
import time
from naRou.ecs.entity import Entity

def test_entity_creation_performance():
    start = time.perf_counter()
    for _ in range(10000):
        Entity(name="PerfTest")
    elapsed = time.perf_counter() - start
    print(f"10000 entities: {elapsed:.3f}s ({elapsed/10000*1e6:.1f}µs/entity)")
    assert elapsed < 1.0  # 目安: 1秒以内

def test_component_access_performance():
    entity = Entity(name="PerfTest")
    start = time.perf_counter()
    for _ in range(100000):
        _ = entity.hp
        _ = entity.level
        _ = entity.get_component(BaseStatsComponent)
    elapsed = time.perf_counter() - start
    print(f"100000 accesses: {elapsed:.3f}s")
    assert elapsed < 0.5
```
**実行**: `python -m pytest tests/test_entity_performance.py -v -s`
**目標**: リファクタ前比 2倍以内のオーバーヘッド

---

### Step 70: ドキュメント更新
**ファイル**: `docs/ecs_architecture.md` (新規/更新)
- ECSアーキテクチャ概要図
- コンポーネント一覧表 (用途・主要フィールド・メソッド)
- Entity クラスの役割 (コンテナ・委譲のみ)
- 移行ガイド: 旧コード (`entity.hp`) → 新コード (`entity.get_component(BaseStatsComponent).hp`) 対応表
- セーブデータ形式変更メモ
**追加**: `CHANGELOG.md` にリファクタリング概要記載

---

### Step 71: CHANGELOG.md 更新
**ファイル**: `CHANGELOG.md`
```markdown
## [Unreleased] - Fat Entity Refactor
### Refactored
- Eliminated "Fat Entity" anti-pattern: migrated 20+ hardcoded fields from Entity class to dedicated ECS components
- New components: TurnEnergyComponent, CombatIntentComponent, FaithComponent, MutationComponent, TutorialProgressComponent, ResistanceComponent, SkillInventoryComponent, PetComponent
- Enhanced existing components: BaseStatsComponent (derived stat calculation), LevelComponent (initialization logic)
- All calculation logic moved from Entity to component/system layer
- Serialization/deserialization now component-based
- Full backward compatibility via property delegation layer
### Performance
- Entity creation/access overhead < 2x baseline (within acceptable range)
```
**検証**: 変更履歴が正確

---

### Step 72: 最終確認・完了宣言
**チェックリスト**:
- [ ] Phase 1-5 全ステップ完了
- [ ] Step 61-71 全ステップ完了・検証済み
- [ ] 既存テストスイート 100% 通過
- [ ] mypy/ruff エラー 0
- [ ] パフォーマンス許容範囲内
- [ ] ドキュメント・CHANGELOG 更新済み
- [ ] セーブデータ互換性確認済み (または移行スクリプト用意済み)

**完了コマンド**: 
```bash
python -m pytest tests/ -x -q && python -m mypy naRou/ecs/ --strict && ruff check naRou/ecs/
```
全て通れば **Fat Entity リファクタリング完了** 🎉

---

## 付録: 実装時の注意事項・Tips

### 低性能LLM向け実装フロー (各ステップ共通)
```bash
# 1. 計画確認
cat plans/fat_entity_refactor_72_steps.md | grep -A 20 "Step XX:"

# 2. 対象ファイル読み込み
# (Read tool で該当箇所確認)

# 3. 変更実施 (最小限・単一責任)

# 4. 即時検証
python -c "from naRou.ecs.entity import Entity; e=Entity(); print(e.hp, e.level, e.god_id)"

# 5. テスト実行
python -m pytest tests/ -x -q

# 6. リンター
ruff check naRou/ecs/entity.py naRou/ecs/components/components.py

# 7. 次ステップへ
```

### よくある落とし穴
1. **循環インポート**: `entity.py` と `components.py` 相互参照 → 文字列アノテーション (`"Entity"`) と `TYPE_CHECKING` で回避
2. **プロパティ setter 再帰**: `@property` + `@x.setter` 内で `self.x = val` 書かない (無限ループ)
3. **デフォルト値 mutable**: `field(default_factory=dict/list/set)` 必須
4. **セーブデータ互換**: 旧形式ロード時、不足コンポーネントはデフォルト初期化で対応
5. **パッシブボーナス二重適用**: `recalculate` 呼び出し頻度に注意 (レベルアップ時のみ等)

### 依存関係グラフ (簡易)
```
Entity (container)
  ├── TurnEnergyComponent
  ├── CombatIntentComponent
  ├── AttributesComponent
  ├── BaseStatsComponent  ← depends on AttributesComponent, LevelComponent, FaithComponent
  ├── LevelComponent
  ├── FaithComponent
  ├── MutationComponent
  ├── TutorialProgressComponent
  ├── ResistanceComponent
  ├── SkillInventoryComponent
  ├── PetComponent
  ├── PetAIComponent
  ├── AffectionComponent
  ├── PetProfileComponent
  ├── EmoteComponent
  ├── TitleComponent
  ├── GuildFactionComponent
  ├── AchievementComponent
  ├── ReincarnationComponent
  ├── SkillTreeJobComponent
  ├── SkillFusionComponent
  ├── StorytellerComponent
  ├── ProceduralQuestComponent
  ├── ArchaeologyComponent
  ├── EconomyComponent
  ├── StatusEffectsComponent
  └── HuskInventoryComponent
```

---

**計画書作成完了** - `E:\narou4\plans\fat_entity_refactor_72_steps.md`