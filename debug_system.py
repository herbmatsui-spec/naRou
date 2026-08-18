"""
Debug and Wish System Module
"""

from __future__ import annotations
from typing import Dict, List, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from entity import Entity
    from item_system import Inventory


class WishParser:
    """テキスト入力から願いを解析するパーサー"""
    ITEM_KEYWORDS: Dict[str, str] = {
        "剣": "longsword", "sword": "longsword",
        "short": "shortsword", "短剣": "shortsword",
        "shield": "shield", "盾": "shield",
        "potion": "potion_heal", "ポーション": "potion_heal", "回復": "potion_heal",
        "bread": "bread", "パン": "bread",
        "book": "book_fire", "魔法書": "book_fire",
    }
    GOLD_KEYWORDS = ["gold", "お金", "金", "gold", "ゴールド"]
    SKILL_KEYWORDS = ["skill", "スキル", "経験"]

    @classmethod
    def parse(cls, text: str, player: "Entity", inventory: "Inventory", survival: Any) -> str:
        from item_system import create_sample_item
        text_lower = text.strip().lower()

        # Gold
        for kw in cls.GOLD_KEYWORDS:
            if kw in text_lower:
                amount = 1000
                survival.gold += amount
                return f"金貨が空から降り注いだ！ +{amount}G 獲得！"

        # Skill
        for kw in cls.SKILL_KEYWORDS:
            if kw in text_lower:
                for sk in player.skills.values():
                    sk.level += 2
                return "全スキルが2レベル上昇した！"

        # HP
        if "hp" in text_lower or "ヒール" in text_lower:
            player.hp = player.max_hp
            player.mp = player.max_mp
            return "HPとMPが全回復した！"

        # Item
        for kw, preset_name in cls.ITEM_KEYWORDS.items():
            if kw in text_lower:
                itm = create_sample_item(preset_name)
                itm.quality = "神器"
                itm.hit_bonus += 5
                itm.dmg_bonus += 5
                ok, msg = inventory.add_item(itm)
                return msg if ok else "インベントリがいっぱい！"

        return "願いは解釈できなかった…（入力: " + text + "）"


class UniqueItemManager:
    """ユニークアイテムの重複出現防止"""
    def __init__(self):
        self._spawned: set = set()

    def can_spawn(self, unique_id: str) -> bool:
        return unique_id not in self._spawned

    def register(self, unique_id: str) -> None:
        self._spawned.add(unique_id)

    def save(self) -> List[str]:
        return list(self._spawned)

    def load(self, data: List[str]) -> None:
        self._spawned = set(data)


class DebugConsole:
    """開発者用デバッグコンソール"""
    def __init__(self):
        self.enabled = True
        self.input_buffer = ""
        self.active = False

    def process_command(self, cmd: str, engine: Any) -> str:
        cmd = cmd.strip().lower()
        if cmd == "heal":
            engine.player.hp = engine.player.max_hp
            engine.player.mp = engine.player.max_mp
            return "HP・MP全快！"
        elif cmd == "levelup":
            for l in engine.player.gain_exp(engine.player.exp_next):
                pass
            return f"レベルアップ！ 現在Lv{engine.player.level}"
        elif cmd == "gold":
            engine.survival.gold += 5000
            return "金貨5000枚追加！"
        elif cmd == "killall":
            removed = 0
            for e in list(engine.entities):
                if e not in (engine.player, engine.pet):
                    e.hp = 0
                    engine.entities.remove(e)
                    removed += 1
            return f"{removed}体の敵を全滅させた！"
        elif cmd.startswith("item "):
            item_name = cmd[5:]
            from item_system import create_sample_item
            itm = create_sample_item(item_name)
            ok, msg = engine.inventory.add_item(itm)
            return msg
        elif cmd == "ether":
            engine.survival.ether_disease = 0
            return "エーテル病を治療した！"
        elif cmd == "titles":
            from title_system import MANAGER
            granted = MANAGER.check_all_titles(engine.player)
            if granted:
                return f"称号チェック実行: {', '.join(granted)} を獲得！"
            else:
                return "新しい称号はありません。"
        elif cmd == "titlelist":
            from title_system import REGISTRY
            REGISTRY.load()
            p = engine.player
            earned = [REGISTRY.get(t).name for t in p.titles if REGISTRY.get(t)]
            return f"獲得済み: {', '.join(earned) if earned else '(なし)'} / 装備中: {p.equipped_title or '(なし)'}"
        return f"不明なコマンド: {cmd}   (heal/levelup/gold/killall/item <名前>/ether/titles/titlelist)"
