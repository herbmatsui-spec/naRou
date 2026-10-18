"""
店舗経済システム (T40 案B)

店舗在庫の管理とアイテム購入処理 (価格計算 / 所持金支払い / 購入ログ) を担う。

購入価格は次の順で乗算して決定する (乗算順序は経済バランスに直結するため固定):

    購入価格 = round(基本価格 × (1 + 派閥物価補正) × カルマ店価格倍率)

1. 派閥物価補正: FactionWarData.price_modifier
   (戦争勝利派閥 = 負 = 割引 / 敗北派閥 = 正 = 高騰, R4-A)。
   プレイヤーの拠点派閥 (faction_reputation が最大の正の評判を持つ派閥) の
   補正を適用し、拠点派閥が無ければ 0.0。
2. カルマ店価格倍率: KarmaManager.get_shop_price_modifier (R4-C)。
   善行段階 = 割引 / 悪行段階 = 割増。将来の割引要素を追加する場合も
   この乗算順序を維持すること。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from faction_war_system import REGISTRY as FACTION_WAR_REGISTRY
from faction_war_system import FactionWarRegistry
from karma_system import KarmaManager

logger = logging.getLogger(__name__)

# 購入失敗種別 (PurchaseResult.error に設定される)
ERROR_UNKNOWN_ITEM = "unknown_item"
ERROR_OUT_OF_STOCK = "out_of_stock"
ERROR_INSUFFICIENT_GOLD = "insufficient_gold"


def resolve_player_faction(player: Any) -> str | None:
    """プレイヤーの拠点派閥 ID を解決する (拠点派閥が無ければ None)。

    faction_reputation (派閥 ID → 評判) のうち最も評判の高い派閥を拠点とみなす。
    評判が 1 件も無い、または全て負の値の場合は拠点派閥なしと扱う。
    """
    reputation = getattr(player, "faction_reputation", None)
    if not reputation:
        return None
    best_id, best_rep = max(reputation.items(), key=lambda kv: kv[1])
    if best_rep <= 0:
        return None
    return best_id


def get_faction_price_modifier(
    player: Any,
    registry: FactionWarRegistry | None = None,
) -> tuple[str | None, float]:
    """拠点派閥の物価補正を取得する。

    Args:
        player: faction_reputation を持つオブジェクト
        registry: 派閥抗争レジストリ (既定は faction_war_system.REGISTRY)。
                  呼び出し前に load 済みであること (production では
                  packages/social/package.py がロードする)。

    Returns:
        (拠点派閥 ID or None, 物価補正)。派閥未所属 / レジストリに存在しない
        派閥の場合は補正 0.0。
    """
    reg = registry if registry is not None else FACTION_WAR_REGISTRY
    faction_id = resolve_player_faction(player)
    if faction_id is None:
        return None, 0.0
    faction = reg.get(faction_id)
    if faction is None:
        return faction_id, 0.0
    return faction_id, float(faction.price_modifier)


@dataclass
class PurchasePrice:
    """購入価格の計算結果と内訳

    乗算順序: base_price → × (1 + faction_price_modifier) → × karma_price_modifier
    """

    base_price: int
    faction_id: str | None
    faction_price_modifier: float
    price_after_faction: float
    karma_stage_id: str
    karma_stage_name: str
    karma_price_modifier: float
    final_price: int

    def to_log_parts(self) -> str:
        """購入ログ用の価格内訳文字列を生成する。"""
        faction_label = self.faction_id if self.faction_id else "無所属"
        return (
            f"基本{self.base_price}G → 派閥[{faction_label}] "
            f"{self.faction_price_modifier:+.1%} → {round(self.price_after_faction)}G "
            f"→ カルマ[{self.karma_stage_name}] ×{self.karma_price_modifier:.2f} "
            f"→ {self.final_price}G"
        )


def calculate_purchase_price(
    base_price: int,
    player: Any = None,
    faction_registry: FactionWarRegistry | None = None,
    karma_manager: KarmaManager | None = None,
) -> PurchasePrice:
    """基本価格に派閥物価補正とカルマ店価格倍率を適用した購入価格を計算する。

    乗算順序 (固定): 基本価格 × (1 + 派閥物価補正) × カルマ店価格倍率

    Args:
        base_price: 商品の基本価格 (data/items.yaml の base_value 等)
        player: karma_good_evil / faction_reputation を持つオブジェクト
                (None なら補正なしの中立扱い)
        faction_registry: 派閥抗争レジストリ (既定は faction_war_system.REGISTRY)
        karma_manager: カーママネージャ (既定は karma_system.KarmaManager())

    Returns:
        内訳を含む PurchasePrice
    """
    if player is None:
        player = {}
    karma_mgr = karma_manager if karma_manager is not None else KarmaManager()
    faction_id, faction_modifier = get_faction_price_modifier(player, faction_registry)
    price_after_faction = base_price * (1.0 + faction_modifier)
    good_evil = int(getattr(player, "karma_good_evil", 0) or 0)
    stage = karma_mgr.get_stage(good_evil)
    final_price = int(round(price_after_faction * stage.shop_price_modifier))
    return PurchasePrice(
        base_price=base_price,
        faction_id=faction_id,
        faction_price_modifier=faction_modifier,
        price_after_faction=price_after_faction,
        karma_stage_id=stage.id,
        karma_stage_name=stage.name,
        karma_price_modifier=stage.shop_price_modifier,
        final_price=final_price,
    )


@dataclass
class StockEntry:
    """店舗在庫 1 件分"""

    item_id: str
    item: Any  # 商品テンプレート (name / base_value を持つ Item 互換オブジェクト)
    base_price: int
    count: int


@dataclass
class PurchaseResult:
    """購入処理の結果 (価格内訳を含む)

    error は失敗種別 (ERROR_* 定数)。成功時は None。
    """

    ok: bool
    message: str
    error: str | None = None
    item_id: str = ""
    price: PurchasePrice | None = None
    total_gold: int = 0
    remaining_stock: int = 0


class Shop:
    """店舗 (在庫管理と購入処理)

    在庫減算と所持金減算が購入処理の中核。購入した Item を購入口に
    渡す (インベントリへの移動は呼び出し側の責務)。
    """

    def __init__(self, name: str = "雑貨屋"):
        self.name = name
        self._stock: dict[str, StockEntry] = {}
        # 購入ログ (価格内訳付き)。購入のたびに末尾へ追加される
        self.purchase_log: list[dict[str, Any]] = []

    def stock_item(
        self,
        item: Any,
        count: int = 1,
        item_id: str | None = None,
        base_price: int | None = None,
    ) -> None:
        """商品を在庫へ登録する (同一キーの再登録は在庫数を加算)。

        Args:
            item: 商品テンプレート (base_price 未指定時は base_value を基本価格とする)
            count: 在庫数
            item_id: 在庫キー (既定は item.name)
            base_price: 基本価格の上書き (既定は item.base_value)
        """
        key = item_id if item_id is not None else str(getattr(item, "name", ""))
        price = int(base_price if base_price is not None else getattr(item, "base_value", 0))
        entry = self._stock.get(key)
        if entry is None:
            self._stock[key] = StockEntry(item_id=key, item=item, base_price=price, count=count)
        else:
            entry.count += count

    def get_stock_count(self, item_id: str) -> int:
        """指定商品の在庫数を返す (未登録は 0)。"""
        entry = self._stock.get(item_id)
        return entry.count if entry is not None else 0

    def quote(self, item_id: str, player: Any = None, count: int = 1) -> PurchaseResult:
        """購入価格の見積もりを返す (在庫引落しと所持金支払いは行わない)。"""
        entry = self._stock.get(item_id)
        if entry is None:
            return PurchaseResult(
                False,
                f"{self.name}に『{item_id}』という商品はない。",
                error=ERROR_UNKNOWN_ITEM,
                item_id=item_id,
            )
        price = calculate_purchase_price(entry.base_price, player)
        total = price.final_price * count
        return PurchaseResult(
            True,
            f"{entry.item.name} ×{count} の見積もり: {total}G ({price.to_log_parts()})",
            item_id=item_id,
            price=price,
            total_gold=total,
            remaining_stock=entry.count,
        )

    def buy(
        self,
        item_id: str,
        gold_holder: Any,
        player: Any = None,
        count: int = 1,
        engine: Any = None,
    ) -> PurchaseResult:
        """商品を購入する (在庫確認 → 価格計算 → 所持金支払い → 在庫減算 → 購入ログ)。

        Args:
            item_id: 在庫キー
            gold_holder: gold 属性を持つ所持金ホルダー (survival 等(item_system.identify と同一契約))
            player: 拠点派閥 / カルマの参照先 (gold_holder と同一オブジェクトでも良い)
            count: 購入数
            engine: 購入ログを message_log へ流す先 (log() を持つオブジェクト, 省略可)

        Returns:
            PurchaseResult (失敗時は ok=False と error 種別、所持金/在庫は変化しない)
        """
        if not hasattr(gold_holder, "gold"):
            raise ValueError("gold_holder must have 'gold' attribute")

        entry = self._stock.get(item_id)
        if entry is None:
            return PurchaseResult(
                False,
                f"{self.name}に『{item_id}』という商品はない。",
                error=ERROR_UNKNOWN_ITEM,
                item_id=item_id,
            )
        if entry.count < count:
            return PurchaseResult(
                False,
                f"『{entry.item.name}』の在庫が足りない (在庫 {entry.count} / 要求 {count})。",
                error=ERROR_OUT_OF_STOCK,
                item_id=item_id,
                remaining_stock=entry.count,
            )

        price = calculate_purchase_price(entry.base_price, player)
        total = price.final_price * count
        if gold_holder.gold < total:
            return PurchaseResult(
                False,
                f"ゴールドが足りない ({total}G 必要 / 所持 {gold_holder.gold}G)。",
                error=ERROR_INSUFFICIENT_GOLD,
                item_id=item_id,
                price=price,
                total_gold=total,
                remaining_stock=entry.count,
            )

        gold_holder.gold -= total
        entry.count -= count

        message = f"【購入】{entry.item.name} ×{count} = {total}G ({price.to_log_parts()})"
        self.purchase_log.append(
            {
                "shop": self.name,
                "item_id": item_id,
                "item_name": entry.item.name,
                "count": count,
                "base_price": price.base_price,
                "faction_id": price.faction_id,
                "faction_price_modifier": price.faction_price_modifier,
                "price_after_faction": round(price.price_after_faction, 2),
                "karma_stage_id": price.karma_stage_id,
                "karma_stage_name": price.karma_stage_name,
                "karma_price_modifier": price.karma_price_modifier,
                "final_price": price.final_price,
                "total_gold": total,
            }
        )
        logger.info(message)
        log = getattr(engine, "log", None) if engine is not None else None
        if callable(log):
            log(message, (255, 215, 0), level="SUCCESS")

        return PurchaseResult(
            True,
            message,
            item_id=item_id,
            price=price,
            total_gold=total,
            remaining_stock=entry.count,
        )
