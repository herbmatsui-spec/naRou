"""
Black Market – UI Layer (Phase 5)
All visual / audio side‑effects are isolated here. Functions receive the
``BlackMarketNetwork`` instance (or the needed sub‑objects) so that the
logic layer stays UI‑free.
"""

from __future__ import annotations

from typing import Any

from naRou.skill_eater.black_market.models import BLACK_MARKET_EVENTS

# ---------------------------------------------------------------------
# Helper to retrieve paths (delegated to the network instance)
# ---------------------------------------------------------------------

def _audio_path(network, audio_file: str):
    return network._get_audio_path(audio_file)

def _emote_path(network, emote_file: str):
    return network._get_emote_path(emote_file)

# ---------------------------------------------------------------------
# UI effect functions – they mirror the methods that used to live on the
# ``BlackMarketNetwork`` class.  Each function receives the network instance
# as the first argument.
# ---------------------------------------------------------------------

def format_location_for_ui(network, location_id: str) -> dict:
    status = network.get_location_status(location_id)
    if "error" in status:
        return status
    location = network.locations[location_id]
    district_names = {
        "slum": "スラム街",
        "cyber": "サイバー地区",
        "midas_back": "ミダスタワー裏",
        "mobile": "移動型",
    }
    price_trend = "安定"
    if location.base_demand_factor > 0.1:
        price_trend = "高騰傾向"
    elif location.base_supply_factor > 0.1:
        price_trend = "下落傾向"
    return {
        "name": location.name,
        "district_name": district_names.get(location.district.value, location.district.value),
        "icon": network._get_location_icon(location_id),
        "price_trend": price_trend,
        "heat_level": network.economy.heat_level,
        "location_heat_penalty": f"{location.heat_penalty * 100:.1f}%",
        "stock_count": len(status["available_items"]),
        "unlock_progress": network._get_unlock_progress(location_id),
        "level": location.level,
        "max_level": location.max_level,
    }

def play_location_enter(network, location_id: str) -> None:
    location = network.locations.get(location_id)
    if not location:
        return
    emote, audio = BLACK_MARKET_EVENTS["ui_open"]
    network.presentation.add_event(
        emote_file=emote,
        audio_file=audio,
        message=f"《{location.name}》に接続中…",
        duration_ms=1500,
    )
    if location.is_mobile:
        pos = location.current_position
        network.presentation.add_event(
            emote_file="emote_idea.png",
            audio_file="bookOpen.ogg",
            message=f"移動型闇市場『MobileCaravan』を発見！ 現在地: {location.district.value}地区 座標: {pos}",
        )

def play_location_exit(network, location_id: str) -> None:
    location = network.locations.get(location_id)
    if not location:
        return
    network.presentation.add_event(
        emote_file="emote_cross.png",
        audio_file="doorClose_1.ogg",
        message=f"{location.name} から切断",
        duration_ms=800,
    )

def play_buy_effect(network, item: Any, quantity: int = 1, discount: float = 0) -> None:
    if item.type == "illegal_skill":
        emote, audio = "emote_cash.png", "credits_transfer.ogg"
        msg = f"違法スキル《{item.name}》を {quantity} 個入手！"
    elif item.type == "concept_crystal":
        emote, audio = "emote_heart.png", "encrypted_comms.ogg"
        msg = f"概念結晶《{item.name}》が輝く… ({quantity} 個)"
    elif item.type == "forbidden_data_chip":
        emote, audio = "emote_graph_up.png", "hologram_ui_open.ogg"
        msg = f"禁忌データ《{item.name}》を解読 ({quantity} 個)"
    else:
        emote, audio = "emote_cash.png", "credits_transfer.ogg"
        msg = f"{item.name} を {quantity} 個購入"
    if discount > 0:
        msg += f" [割引 {int(discount * 100)}%]"
    network.presentation.add_event(
        emote_file=emote,
        audio_file=audio,
        message=msg,
        duration_ms=2000,
    )

def play_sell_effect(network, item: Any, quantity: int, total_price: int, is_illegal: bool) -> None:
    if is_illegal:
        network.presentation.add_event(
            emote_file="emote_cash.png",
            audio_file="doorClose_1.ogg",
            message=f"違法スキル《{item.name}》を {quantity} 個密売完了 (獲得: {total_price} アルド, 警戒度: {network.economy.heat_level})",
            duration_ms=2000,
        )
    else:
        network.presentation.add_event(
            emote_file="emote_cash.png",
            audio_file="handleCoins.ogg",
            message=f"{item.name} を {quantity} 個売却: {total_price} アルド獲得",
            duration_ms=1500,
        )

def play_route_establish_effect(network, origin_name: str, dest_name: str, risk_level: int) -> None:
    emote, audio = BLACK_MARKET_EVENTS["route_establish"]
    network.presentation.add_event(
        emote_file=emote,
        audio_file=audio,
        message=f"密輸ルート確立: {origin_name} → {dest_name} (リスク: {risk_level})",
        duration_ms=2500,
    )

def play_route_profit_effect(network, route_id: str, profit: int, total_profit: int) -> None:
    emote, audio = BLACK_MARKET_EVENTS["route_profit"]
    network.presentation.add_event(
        emote_file=emote,
        audio_file=audio,
        message=f"密輸ルート『{route_id}』から {profit} アルドの利益！ (累計: {total_profit} アルド)",
        duration_ms=2000,
    )

def play_route_detected_effect(network, route_id: str, heat_increase: int, loss: int) -> None:
    emote, audio = BLACK_MARKET_EVENTS["route_detected"]
    for i in range(3):
        network.presentation.add_event(
            emote_file=emote,
            audio_file=audio,
            message="【発覚！】" if i == 0 else "",
            duration_ms=1000,
        )
    network.presentation.add_event(
        emote_file=emote,
        audio_file=audio,
        message=f"密輸ルート『{route_id}』がミダスに察知された！ 投資損失: {loss} アルド、警戒度 +{heat_increase}",
        duration_ms=3000,
    )

def play_route_abandon_effect(network, route_id: str, recovered: int) -> None:
    emote, audio = BLACK_MARKET_EVENTS["route_abandon"]
    network.presentation.add_event(
        emote_file=emote,
        audio_file=audio,
        message=f"密輸ルート『{route_id}』を撤退 (回収: {recovered} アルド)",
        duration_ms=1500,
    )

def play_price_surge_effect(network, item_name: str, change_percent: float, current_price: int) -> None:
    if abs(change_percent) >= 20:
        emote, audio = BLACK_MARKET_EVENTS["price_surge"]
        direction = "急騰" if change_percent > 0 else "暴落"
        network.presentation.add_event(
            emote_file=emote,
            audio_file=audio,
            message=f"需給変動: 《{item_name}》が {abs(change_percent):.0f}% {direction} (現在: {current_price} アルド)",
            duration_ms=2500,
        )

def play_heat_warning_effect(network) -> None:
    if network.economy.heat_level >= 70:
        emote, audio = BLACK_MARKET_EVENTS["heat_warning"]
        network.presentation.add_event(
            emote_file=emote,
            audio_file=audio,
            message=f"⚠ 警戒度危険水域: {network.economy.heat_level}/100",
            duration_ms=2000,
        )

def play_caravan_encounter_effect(network, district: str, position: tuple[int, int]) -> None:
    emote, audio = BLACK_MARKET_EVENTS["caravan_encounter"]
    network.presentation.add_event(
        emote_file=emote,
        audio_file=audio,
        message=f"移動闇市場『MobileCaravan』を発見！ 現在地: {district}地区 座標: {position}",
        duration_ms=2500,
    )

def play_location_unlock_effect(network, location_name: str) -> None:
    emote, audio = BLACK_MARKET_EVENTS["location_unlock"]
    network.presentation.add_event(
        emote_file=emote,
        audio_file=audio,
        message=f"新たな闇市場拠点『{location_name}』が解放された！",
        duration_ms=3000,
    )

def play_location_upgrade_effect(network, location_name: str, new_level: int) -> None:
    emote, audio = BLACK_MARKET_EVENTS["location_upgrade"]
    network.presentation.add_event(
        emote_file=emote,
        audio_file=audio,
        message=f"【拠点強化】{location_name} が Lv.{new_level} に昇格！",
        duration_ms=2000,
    )
    network.audio.play_sound("metalPot1.ogg")

__all__ = [
    "format_location_for_ui",
    "play_location_enter",
    "play_location_exit",
    "play_buy_effect",
    "play_sell_effect",
    "play_route_establish_effect",
    "play_route_profit_effect",
    "play_route_detected_effect",
    "play_route_abandon_effect",
    "play_price_surge_effect",
    "play_heat_warning_effect",
    "play_caravan_encounter_effect",
    "play_location_unlock_effect",
    "play_location_upgrade_effect",
]
