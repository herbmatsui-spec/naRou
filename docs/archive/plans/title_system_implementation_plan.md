# 称号・二つ名システム 詳細実装計画書

**対象**: 低性能LLMでも実装可能なよう、12の微小ステップに分割
**前提**: 既存コードベース（entity.py, systems.py, game.py, advanced_systems.py）への最小限の追加
**推定総工数**: 2日（各ステップ 1-3時間）

---

## アーキテクチャ概要

```
┌─────────────────────────────────────────────────────────────┐
│  data/titles.yaml          ← 称号定義データ（YAML）           │
├─────────────────────────────────────────────────────────────┤
│  title_system.py           ← 称号判定・付与・効果適用ロジック  │
├─────────────────────────────────────────────────────────────┤
│  entity.py (Entity)        ← titles: List[str] 追加           │
│  systems.py                ← ステータス再計算フック追加        │
│  game.py (Engine)          ← UI表示・通知統合                  │
│  advanced_systems.py       ← SaveSystem に titles 永続化       │
└─────────────────────────────────────────────────────────────┘
```

---

## ステップ 1: データ定義ファイル作成 `data/titles.yaml`

**目的**: 全称号の定義をデータ駆動で管理
**ファイル**: 新規作成 `data/titles.yaml`
**所要時間**: 30分

```yaml
# data/titles.yaml
titles:
  # === キル系 ===
  goblin_slayer:
    id: "goblin_slayer"
    name: "ゴブリンスレイヤー"
    epithet: "緑皮の悪夢"
    category: "kill"
    condition:
      type: "kill_count"
      target: "goblin"
      count: 100
    effects:
      - {attr: "strength", value: 2}
      - {attr: "damage_vs_goblin", value: 1.2}
    message: "ゴブリンを100体討伐した！「ゴブリンスレイヤー」の称号を得た！"

  dragon_slayer:
    id: "dragon_slayer"
    name: "竜殺し"
    epithet: "竜の墓標"
    category: "kill"
    condition:
      type: "kill_count"
      target: "dragon"
      count: 10
    effects:
      - {attr: "strength", value: 5}
      - {attr: "charisma", value: 3}
      - {attr: "fear_resist", value: 50}
    message: "竜を10体討伐した！「竜殺し」の称号を得た！"

  # === 探索系 ===
  deep_delver:
    id: "deep_delver"
    name: "深淵の探索者"
    epithet: "奈落を歩む者"
    category: "explore"
    condition:
      type: "dungeon_depth"
      min_depth: 50
    effects:
      - {attr: "perception", value: 3}
      - {attr: "evasion", value: 5}
    message: "ダンジョン50階層に到達した！「深淵の探索者」の称号を得た！"

  # === スキル系 ===
  master_swordsman:
    id: "master_swordsman"
    name: "剣聖"
    epithet: "一閃無双"
    category: "skill"
    condition:
      type: "skill_level"
      skill: "long_sword"
      level: 50
    effects:
      - {attr: "dexterity", value: 4}
      - {attr: "critical_rate", value: 10}
    message: "長剣スキルがLv50に達した！「剣聖」の称号を得た！"

  # === 生存系 ===
  survivor:
    id: "survivor"
    name: "生還者"
    epithet: "死線を越えし者"
    category: "survival"
    condition:
      type: "near_death_count"
      count: 5
    effects:
      - {attr: "endurance", value: 3}
      - {attr: "will", value: 3}
      - {attr: "hp_regen", value: 2}
    message: "瀕死から5回生還した！「生還者」の称号を得た！"

  # === 信仰系 ===
  devout_believer:
    id: "devout_believer"
    name: "篤き信者"
    epithet: "神の代弁者"
    category: "faith"
    condition:
      type: "piety"
      value: 1000
    effects:
      - {attr: "magic", value: 3}
      - {attr: "piety_gain", value: 1.5}
    message: "信仰度1000に達した！「篤き信者」の称号を得た！"

  # === 富豪系 ===
  millionaire:
    id: "millionaire"
    name: "大富豪"
    epithet: "黄金の主"
    category: "wealth"
    condition:
      type: "gold_owned"
      value: 1000000
    effects:
      - {attr: "charisma", value: 5}
      - {attr: "shop_discount", value: 10}
    message: "所持金100万ゴールド達成！「大富豪」の称号を得た！"

  # === ペット系 ===
  beast_master:
    id: "beast_master"
    name: "調教師"
    epithet: "獣の王"
    category: "pet"
    condition:
      type: "pet_count"
      count: 5
    effects:
      - {attr: "charisma", value: 4}
      - {attr: "pet_stat_bonus", value: 1.2}
    message: "ペットを5体従えた！「調教師」の称号を得た！"

  # === クラフト系 ===
  legendary_smith:
    id: "legendary_smith"
    name: "伝説の鍛冶師"
    epithet: "鋼の魔術師"
    category: "craft"
    condition:
      type: "craft_count"
      category: "weapon"
      count: 100
    effects:
      - {attr: "learning", value: 3}
      - {attr: "craft_quality", value: 1.3}
    message: "武器を100個鍛造した！「伝説の鍛冶師」の称号を得た！"

  # === 特殊・隠し ===
  speedrunner:
    id: "speedrunner"
    name: "疾風の如く"
    epithet: "時間を超える者"
    category: "special"
    condition:
      type: "game_clear_time"
      max_turns: 10000
    effects:
      - {attr: "speed", value: 20}
      - {attr: "dexterity", value: 5}
    message: "驚異的な速さでクリアした！「疾風の如く」の称号を得た！"

  # === マイルストーン ===
  level_50:
    id: "level_50"
    name: "達人"
    epithet: "極めし者"
    category: "milestone"
    condition:
      type: "level"
      value: 50
    effects:
      - {attr: "all_attributes", value: 2}
    message: "レベル50に到達した！「達人」の称号を得た！"

  level_100:
    id: "level_100"
    name: "超越者"
    epithet: "常識を超えし者"
    category: "milestone"
    condition:
      type: "level"
      value: 100
    effects:
      - {attr: "all_attributes", value: 5}
      - {attr: "exp_gain", value: 1.5}
    message: "レベル100に到達した！「超越者」の称号を得た！"
```

**確認項目**: ファイルが `data/titles.yaml` として保存され、YAML構文エラーがないこと

---

## ステップ 2: TitleData データクラス作成 `title_system.py` (前半)

**目的**: 称号定義をPythonオブジェクトとして扱う
**ファイル**: 新規作成 `title_system.py`
**所要時間**: 45分

```python
# title_system.py
"""
称号・二つ名システム (ステップ1〜12統合)
データ駆動型で称号の判定・付与・効果適用を行う
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import yaml
from pathlib import Path


@dataclass
class TitleEffect:
    """称号によるステータス効果"""

    attr: str  # 対象属性名 (strength, damage_vs_goblin 等)
    value: float  # 加算値 or 乗算値
    is_multiplier: bool = False  # Trueなら乗算、Falseなら加算


@dataclass
class TitleCondition:
    """称号獲得条件"""

    type: str  # kill_count, skill_level, dungeon_depth 等
    target: str = ""  # 対象 (モンスターID, スキル名 等)
    count: int = 0  # 必要数
    value: int = 0  # 閾値
    level: int = 0  # スキルレベル等
    category: str = ""  # クラフトカテゴリ等
    min_depth: int = 0  # ダンジョン深度
    max_turns: int = 0  # ターン数制限


@dataclass
class TitleData:
    """称号マスターデータ"""

    id: str
    name: str  # 表示名「ゴブリンスレイヤー」
    epithet: str  # 二つ名「緑皮の悪夢」
    category: str  # kill, explore, skill, survival, faith, wealth, pet, craft, special, milestone
    condition: TitleCondition
    effects: List[TitleEffect]
    message: str  # 獲得時メッセージ
    is_hidden: bool = False  # 獲得前は隠すか


class TitleRegistry:
    """称号レジストリ（シングルトン的）"""

    _instance: Optional["TitleRegistry"] = None
    _titles: Dict[str, TitleData] = {}
    _loaded: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, path: str = "data/titles.yaml") -> None:
        """YAMLから称号定義を読み込み"""
        if self._loaded:
            return
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for t in data.get("titles", {}).values():
            cond = t["condition"]
            condition = TitleCondition(
                type=cond["type"],
                target=cond.get("target", ""),
                count=cond.get("count", 0),
                value=cond.get("value", 0),
                level=cond.get("level", 0),
                category=cond.get("category", ""),
                min_depth=cond.get("min_depth", 0),
                max_turns=cond.get("max_turns", 0),
            )
            effects = [
                TitleEffect(
                    attr=e["attr"],
                    value=e["value"],
                    is_multiplier=e.get("is_multiplier", False),
                )
                for e in t.get("effects", [])
            ]
            title = TitleData(
                id=t["id"],
                name=t["name"],
                epithet=t["epithet"],
                category=t["category"],
                condition=condition,
                effects=effects,
                message=t["message"],
                is_hidden=t.get("is_hidden", False),
            )
            self._titles[title.id] = title
        self._loaded = True

    def get(self, title_id: str) -> Optional[TitleData]:
        return self._titles.get(title_id)

    def all(self) -> List[TitleData]:
        return list(self._titles.values())

    def by_category(self, category: str) -> List[TitleData]:
        return [t for t in self._titles.values() if t.category == category]


# グローバルアクセス用
REGISTRY = TitleRegistry()
```

**確認項目**: `python -c "from title_system import REGISTRY; REGISTRY.load(); print(len(REGISTRY.all()))"` で12個表示されること

---

## ステップ 3: Entity クラスに titles フィールド追加 `entity.py`

**目的**: プレイヤー/ペットが所持する称号リストを保持
**ファイル**: `entity.py` (Entity.__init__ 内)
**所要時間**: 15分

```python
# entity.py の Entity.__init__ 内、適切な位置（self.mutations 付近）に追加

        # 突然変異＆エーテル病 (ステップ56, 57, 122)
        self.mutations: Dict[str, int] = {}
        self.ether_disease_stages: List[str] = []

        # === 称号システム (ステップ: 称号実装) ===
        self.titles: List[str] = []           # 獲得済み称号IDリスト
        self.equipped_title: str = ""         # 現在表示中の称号ID (空ならなし)
        self.title_notifications: List[str] = []  # 獲得通知キュー
```

**確認項目**: `python -c "from entity import Entity; e=Entity(0,0,'@'); print(e.titles, e.equipped_title)"` で `[] ''` と出ること

---

## ステップ 4: 称号判定ロジック実装 `title_system.py` (中盤)

**目的**: 条件チェック・称号付与・効果適用のコアロジック
**ファイル**: `title_system.py` (TitleRegistry クラスの後ろに追加)
**所要時間**: 60分

```python
# title_system.py 続き

from entity import (
    Entity,
)  # 循環import回避のため TYPE_CHECKING または遅延import推奨だが、ここでは直接import


class TitleManager:
    """称号の判定・付与・効果管理"""

    def __init__(self, registry: TitleRegistry = None):
        self.registry = registry or REGISTRY

    # === 条件判定 ===
    def check_kill_count(self, player: Entity, target: str, required: int) -> bool:
        # 実装簡易化: Entity に kill_counts: Dict[str, int] を後で追加予定
        # ここでは仮実装（後でステップ7で実装）
        return getattr(player, "kill_counts", {}).get(target, 0) >= required

    def check_skill_level(self, player: Entity, skill: str, level: int) -> bool:
        return player.skills.get(skill, Skill("")).level >= level

    def check_dungeon_depth(self, player: Entity, min_depth: int) -> bool:
        return getattr(player, "max_dungeon_depth", 0) >= min_depth

    def check_near_death(self, player: Entity, count: int) -> bool:
        return getattr(player, "near_death_count", 0) >= count

    def check_piety(self, player: Entity, value: int) -> bool:
        return player.piety >= value

    def check_gold(self, player: Entity, value: int) -> bool:
        # 所持金チェック（インベントリまたはプレイヤー直接保持）
        return getattr(player, "gold", 0) >= value

    def check_pet_count(self, player: Entity, count: int) -> bool:
        # ペット数は Engine 側で管理想定、ここでは player.pets 参照
        return len(getattr(player, "pets", [])) >= count

    def check_craft_count(self, player: Entity, category: str, count: int) -> bool:
        return getattr(player, "craft_counts", {}).get(category, 0) >= count

    def check_level(self, player: Entity, level: int) -> bool:
        return player.level >= level

    def check_game_clear_time(self, player: Entity, max_turns: int) -> bool:
        return getattr(player, "total_turns", 0) <= max_turns

    # === 汎用判定ディスパッチャ ===
    def check_condition(self, player: Entity, condition: TitleCondition) -> bool:
        check_map = {
            "kill_count": lambda c: self.check_kill_count(player, c.target, c.count),
            "skill_level": lambda c: self.check_skill_level(player, c.target, c.level),
            "dungeon_depth": lambda c: self.check_dungeon_depth(player, c.min_depth),
            "near_death_count": lambda c: self.check_near_death(player, c.count),
            "piety": lambda c: self.check_piety(player, c.value),
            "gold_owned": lambda c: self.check_gold(player, c.value),
            "pet_count": lambda c: self.check_pet_count(player, c.count),
            "craft_count": lambda c: self.check_craft_count(
                player, c.category, c.count
            ),
            "level": lambda c: self.check_level(player, c.value),
            "game_clear_time": lambda c: self.check_game_clear_time(
                player, c.max_turns
            ),
        }
        checker = check_map.get(condition.type)
        if checker:
            return checker(condition)
        return False

    # === 称号付与 ===
    def grant_title(self, player: Entity, title_id: str) -> bool:
        """称号を付与（重複チェック込み）"""
        if title_id in player.titles:
            return False  # 既に所持
        title = self.registry.get(title_id)
        if not title:
            return False
        player.titles.append(title_id)
        # 通知キューに追加
        player.title_notifications.append(title.message)
        # 効果即時適用
        self.apply_title_effects(player, title)
        return True

    def apply_title_effects(self, player: Entity, title: TitleData) -> None:
        """称号効果をステータスに適用"""
        for eff in title.effects:
            if eff.attr == "all_attributes":
                for attr in [
                    "strength",
                    "endurance",
                    "dexterity",
                    "perception",
                    "learning",
                    "will",
                    "magic",
                    "charisma",
                ]:
                    current = getattr(player.attributes, attr)
                    setattr(player.attributes, attr, current + int(eff.value))
            elif hasattr(player.attributes, eff.attr):
                current = getattr(player.attributes, eff.attr)
                if eff.is_multiplier:
                    # 乗算は再計算時に適用するためフラグ管理推奨
                    # ここでは簡易加算
                    setattr(player.attributes, eff.attr, current + int(eff.value))
                else:
                    setattr(player.attributes, eff.attr, current + int(eff.value))
            # 特殊効果 (damage_vs_goblin, fear_resist 等) は別途管理
            # → ステップ8で拡張
        player.recalculate_stats()

    def remove_title_effects(self, player: Entity, title: TitleData) -> None:
        """称号効果を除去（装備解除時）"""
        for eff in title.effects:
            if eff.attr == "all_attributes":
                for attr in [
                    "strength",
                    "endurance",
                    "dexterity",
                    "perception",
                    "learning",
                    "will",
                    "magic",
                    "charisma",
                ]:
                    current = getattr(player.attributes, attr)
                    setattr(player.attributes, attr, current - int(eff.value))
            elif hasattr(player.attributes, eff.attr):
                current = getattr(player.attributes, eff.attr)
                setattr(player.attributes, eff.attr, current - int(eff.value))
        player.recalculate_stats()

    # === 全称号チェック（ターン終了時等に呼ぶ） ===
    def check_all_titles(self, player: Entity) -> List[str]:
        """未獲得称号を全チェック、新規獲得分を返す"""
        granted = []
        for title in self.registry.all():
            if title.id in player.titles:
                continue
            if self.check_condition(player, title.condition):
                if self.grant_title(player, title.id):
                    granted.append(title.id)
        return granted


# グローバルマネージャー
MANAGER = TitleManager()
```

**確認項目**: `python -c "from title_system import MANAGER; from entity import Entity; REGISTRY.load(); e=Entity(0,0,'@'); e.level=50; print(MANAGER.check_all_titles(e))"` で `['level_50']` が返ること

---

## ステップ 5: キルカウント・各種カウンター追加 `entity.py`

**目的**: 称号条件判定に必要な統計データを Entity に保持
**ファイル**: `entity.py` (Entity.__init__ 末尾付近)
**所要時間**: 20分

```python
# entity.py Entity.__init__ 末尾に追加

        # === 称号用統計カウンター ===
        self.kill_counts: Dict[str, int] = {}      # モンスター別討伐数
        self.craft_counts: Dict[str, int] = {}     # カテゴリ別クラフト数
        self.max_dungeon_depth: int = 0            # 到達最大深度
        self.near_death_count: int = 0             # 瀕死生還回数
        self.total_turns: int = 0                  # 総ターン数
        self.gold: int = 0                         # 所持金（簡易版）
        self.pets: List['Entity'] = []             # 従えているペットリスト（参照用）
```

**確認項目**: `python -c "from entity import Entity; e=Entity(0,0,'@'); print(e.kill_counts, e.craft_counts)"` で `{} {}` と出ること

---

## ステップ 6: キルカウント増加フック `game.py` (_on_kill 内)

**目的**: モンスター討伐時に kill_counts をインクリメント
**ファイル**: `game.py` (Engine._on_kill メソッド)
**所要時間**: 15分

```python
# game.py Engine._on_kill メソッド内、既存処理の後ろに追加

    def _on_kill(self, entity: Entity) -> None:
        # ... 既存の経験値付与・ドロップ処理等 ...

        # === 称号システム: キルカウント記録 ===
        if self.player and hasattr(self.player, 'kill_counts'):
            # モンスター名正規化（小文字・スペース→アンダースコア）
            key = entity.name.lower().replace(' ', '_')
            self.player.kill_counts[key] = self.player.kill_counts.get(key, 0) + 1

            # 称号チェック（即時 or ターン終了時）
            # ここでは即時チェック（軽量なので問題なし）
            from title_system import MANAGER
            granted = MANAGER.check_all_titles(self.player)
            for tid in granted:
                # 通知は title_notifications に溜まるので、描画側で表示
                pass
```

**確認項目**: ゴブリンを倒すたびに `player.kill_counts['goblin']` が増えること

---

## ステップ 7: ターン終了時の定期称号チェック `game.py` (advance_world)

**目的**: キル以外の条件（レベル、深度、信仰等）を定期判定
**ファイル**: `game.py` (Engine.advance_world メソッド末尾)
**所要時間**: 15分

```python
# game.py Engine.advance_world メソッド末尾に追加

    def advance_world(self) -> None:
        # ... 既存のターン処理 ...

        # === 称号システム: 定期チェック（100ターンごと等で軽量化可） ===
        if self.player and hasattr(self.player, 'total_turns'):
            self.player.total_turns += 1

            # 10ターンごとにチェック（パフォーマンス考慮）
            if self.player.total_turns % 10 == 0:
                from title_system import MANAGER
                granted = MANAGER.check_all_titles(self.player)
                # 通知は自動で player.title_notifications に入る
```

**確認項目**: レベルアップや深度到達後に称号が自動獲得されること

---

## ステップ 8: 称号装備/解除・効果の動的適用 `title_system.py` (後盤)

**目的**: 称号を「装備」して二つ名表示・効果発動、「解除」で効果消失
**ファイル**: `title_system.py` (TitleManager クラスに追加)
**所要時間**: 30分

```python
# title_system.py TitleManager クラスに追加

    def equip_title(self, player: Entity, title_id: str) -> bool:
        """称号を装備（二つ名表示・効果発動）"""
        if title_id not in player.titles:
            return False
        # 既存装備を解除
        if player.equipped_title:
            self.unequip_title(player)
        # 新規装備
        player.equipped_title = title_id
        title = self.registry.get(title_id)
        if title:
            self.apply_title_effects(player, title)
        return True

    def unequip_title(self, player: Entity) -> bool:
        """称号を解除（効果消失）"""
        if not player.equipped_title:
            return False
        title = self.registry.get(player.equipped_title)
        if title:
            self.remove_title_effects(player, title)
        player.equipped_title = ""
        return True

    def get_display_name(self, player: Entity) -> str:
        """表示用名前（二つ名込み）取得"""
        base = player.name
        if player.equipped_title:
            title = self.registry.get(player.equipped_title)
            if title:
                return f"{base}《{title.epithet}》"
        return base

    def get_title_list_for_ui(self, player: Entity) -> List[Dict[str, Any]]:
        """UI表示用リスト（獲得済み/未獲得・装備中フラグ付き）"""
        result = []
        for title in self.registry.all():
            owned = title.id in player.titles
            equipped = title.id == player.equipped_title
            result.append({
                'id': title.id,
                'name': title.name,
                'epithet': title.epithet,
                'category': title.category,
                'owned': owned,
                'equipped': equipped,
                'hidden': title.is_hidden and not owned,
                'message': title.message if owned else "???",
            })
        return result
```

**確認項目**:
- `MANAGER.equip_title(player, 'goblin_slayer')` で `player.equipped_title == 'goblin_slayer'`
- `MANAGER.get_display_name(player)` で `"Player《緑皮の悪夢》"` が返ること

---

## ステップ 9: UI統合 - 称号画面追加 `game.py` (render_all / input handling)

**目的**: 称号一覧表示・装備操作UI
**ファイル**: `game.py` (render_all 関数・メインループ内)
**所要時間**: 45分

```python
# game.py render_all 関数内、適切な位置（インベントリ画面等の近く）に追加


def render_title_screen(console: tcod.console.Console, engine: Engine) -> None:
    """称号画面描画（Tキーで開く想定）"""
    from title_system import MANAGER

    if not engine.player:
        return

    titles = MANAGER.get_title_list_for_ui(engine.player)
    w, h = 70, 40
    x = (console.width - w) // 2
    y = (console.height - h) // 2

    # 背景
    console.draw_frame(x, y, w, h, title=" 称号・二つ名 ", clear=True)

    # 現在の二つ名表示
    display_name = MANAGER.get_display_name(engine.player)
    console.print(x + 2, y + 1, f"現在: {display_name}", fg=(255, 255, 100))

    # リスト
    row = 3
    for t in titles:
        if t["hidden"]:
            line = "  ??? (未発見)"
            color = (100, 100, 100)
        else:
            mark = "★" if t["equipped"] else ("●" if t["owned"] else "○")
            line = f"  {mark} {t['name']} 《{t['epithet']}》 [{t['category']}]"
            color = (100, 255, 100) if t["owned"] else (200, 200, 200)
            if t["equipped"]:
                color = (255, 255, 0)
        console.print(x + 2, y + row, line, fg=color)
        row += 1
        if row > h - 3:
            break

    console.print(x + 2, y + h - 2, "Enter: 装備/解除  Esc: 閉じる", fg=(150, 150, 150))


# メインループ内のキー処理に追加 (main() 関数内)
# elif key.sym == tcod.event.KeySym.t:
#     engine.show_title_screen = not engine.show_title_screen
#     continue
```

**確認項目**: Tキーで称号画面が開き、獲得済み称号が緑、装備中が黄色、未獲得が灰色で表示されること

---

## ステップ 10: 称号獲得通知表示 `game.py` (render_all / message log)

**目的**: 称号獲得時にメッセージログ・ポップアップで通知
**ファイル**: `game.py` (render_all 内のメッセージログ描画部)
**所要時間**: 20分

```python
# game.py render_all 内、メッセージログ描画ループの前後で処理

# 称号獲得通知のポップアップ表示（画面中央上部）
if engine.player and engine.player.title_notifications:
    for i, msg in enumerate(engine.player.title_notifications):
        # 簡易ポップアップ（3秒表示等のタイマー実装推奨）
        console.print(
            console.width // 2 - len(msg) // 2,
            3 + i,
            f"★ {msg} ★",
            fg=(255, 215, 0),  # 金色
            bg=(0, 0, 0),
        )
    # 表示後クリア（またはタイマーで）
    # engine.player.title_notifications.clear()  # 即時クリア or 残す
```

**確認項目**: 称号獲得時に画面上部に金色で「★ ゴブリンを100体討伐した！... ★」と表示されること

---

## ステップ 11: セーブ/ロード対応 `advanced_systems.py` (SaveSystem)

**目的**: 称号データをセーブファイルに永続化
**ファイル**: `advanced_systems.py` (SaveSystem.save / load)
**所要時間**: 20分

```python
# advanced_systems.py SaveSystem.save メソッド内、engine.player のシリアライズ部分

    @classmethod
    def save(cls, engine: Any) -> str:
        # ... 既存処理 ...

        # 称号データは Entity に含まれるため自動保存される（pickle）
        # 明示的に保存したい場合のみ以下追加：
        save_data = {
            # ... 既存 ...
            'player_titles': engine.player.titles if engine.player else [],
            'player_equipped_title': engine.player.equipped_title if engine.player else "",
            'player_kill_counts': engine.player.kill_counts if engine.player else {},
            'player_craft_counts': engine.player.craft_counts if engine.player else {},
            'player_max_dungeon_depth': engine.player.max_dungeon_depth if engine.player else 0,
            'player_near_death_count': engine.player.near_death_count if engine.player else 0,
            'player_total_turns': engine.player.total_turns if engine.player else 0,
            'player_gold': engine.player.gold if engine.player else 0,
        }
        # pickle.dump(save_data, f) 等で保存

    @classmethod
    def load(cls) -> Tuple[Optional[Any], str]:
        # ... 既存ロード処理 ...
        # engine.player.titles = save_data.get('player_titles', [])
        # engine.player.equipped_title = save_data.get('player_equipped_title', "")
        # engine.player.kill_counts = save_data.get('player_kill_counts', {})
        # ... 同様に復元 ...
```

**確認項目**: セーブ→ロードで称号・装備中称号・キルカウントが復元されること

---

## ステップ 12: 統合テスト・デバッグ用チートコマンド `advanced_systems.py` (DebugConsole)

**目的**: 開発中に全称号強制獲得・リセット等で動作確認
**ファイル**: `advanced_systems.py` (DebugConsole.process_command)
**所要時間**: 20分

```python
# advanced_systems.py DebugConsole.process_command 内に追加

    def process_command(self, cmd: str, engine: Any) -> str:
        # ... 既存コマンド ...

        parts = cmd.split()
        if parts[0] == "title":
            if len(parts) < 2:
                return "Usage: title [grant|revoke|list|equip|unequip|all] [title_id]"
            from title_system import REGISTRY, MANAGER
            player = engine.player
            sub = parts[1]

            if sub == "list":
                return ", ".join([f"{t.id}({'★' if t.id in player.titles else ' '})" for t in REGISTRY.all()])

            elif sub == "grant" and len(parts) >= 3:
                tid = parts[2]
                if MANAGER.grant_title(player, tid):
                    return f"Granted: {tid}"
                return f"Failed or already owned: {tid}"

            elif sub == "revoke" and len(parts) >= 3:
                tid = parts[2]
                if tid in player.titles:
                    player.titles.remove(tid)
                    if player.equipped_title == tid:
                        MANAGER.unequip_title(player)
                    return f"Revoked: {tid}"
                return f"Not owned: {tid}"

            elif sub == "equip" and len(parts) >= 3:
                if MANAGER.equip_title(player, parts[2]):
                    return f"Equipped: {parts[2]}"
                return "Failed"

            elif sub == "unequip":
                MANAGER.unequip_title(player)
                return "Unequipped"

            elif sub == "all":
                for t in REGISTRY.all():
                    MANAGER.grant_title(player, t.id)
                return "All titles granted!"

            elif sub == "reset":
                player.titles.clear()
                player.equipped_title = ""
                player.kill_counts.clear()
                player.craft_counts.clear()
                player.max_dungeon_depth = 0
                player.near_death_count = 0
                player.total_turns = 0
                return "Title data reset!"

        return "Unknown command"
```

**確認項目**: デバッグコンソールで `title all` → 全称号獲得、`title list` → 一覧表示、`title equip goblin_slayer` → 装備・二つ名表示

---

## 実装順序まとめ（依存関係順）

| Step | ファイル | 内容 | 依存 |
|------|----------|------|------|
| 1 | `data/titles.yaml` | 定義データ | - |
| 2 | `title_system.py` (前半) | データクラス・レジストリ | 1 |
| 3 | `entity.py` | titlesフィールド追加 | - |
| 4 | `title_system.py` (中盤) | 判定・付与ロジック | 2, 3 |
| 5 | `entity.py` | カウンター追加 | 3 |
| 6 | `game.py` (_on_kill) | キルカウントフック | 4, 5 |
| 7 | `game.py` (advance_world) | 定期チェック | 4 |
| 8 | `title_system.py` (後盤) | 装備/解除・表示名 | 4 |
| 9 | `game.py` (render_all) | 称号画面UI | 8 |
| 10 | `game.py` (render_all) | 獲得通知表示 | 4 |
| 11 | `advanced_systems.py` | セーブ/ロード | 3, 5 |
| 12 | `advanced_systems.py` | デバッグコマンド | 4, 8 |

---

## 低性能LLM向け実装Tips

1. **1ステップ = 1ファイル編集** を徹底（複数ファイル同時編集禁止）
2. **各ステップ完了時に `python -c "..."` で動作確認** を必須化
3. **import循環回避**: `title_system.py` から `entity.py` をimportするが、`entity.py` からはimportしない（game.py経由で連携）
4. **型ヒントは最小限** (`from __future__ import annotations` 使用済み)
5. **エラーハンドリングは後回し** → まず動くものを作る
6. **YAMLパース失敗時**: `yaml.safe_load` 例外を try/except で囲む
7. **既存コード破壊防止**: 追加のみ・既存メソッド内への「追記」のみで実装

---

## 完成後の拡張アイデア（本計画外）

- 称号合成（二つ名組み合わせで新称号）
- 称号継承（輪廻転生時に一部引き継ぎ）
- 称号専用クエスト生成
- マルチプレイヤー対応（称号ランキング）
- 実績システム(Steam風)との統合
