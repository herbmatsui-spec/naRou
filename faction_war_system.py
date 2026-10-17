"""
派閥抗争システム (ファクションウォー)
派閥データの管理・影響力変動計算・抗争条件判定・影響力適用
Steps 52-58
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ecs.entity import Entity

import yaml

from protocols import MemoryRegistryProtocol

# Phase 2 連携：遅延インポート
try:
    from npc_memory_system import GLOBAL_MEMORY_REGISTRY, MemoryImportance, MemoryType

    _HAS_NPC_MEMORY = True
except ImportError:
    GLOBAL_MEMORY_REGISTRY = None
    MemoryType = None
    MemoryImportance = None
    _HAS_NPC_MEMORY = False


@dataclass
class FactionWarData:
    """派閥抗争マスターデータ (Step 53)"""

    id: str
    name: str
    color: list[int] = field(default_factory=lambda: [255, 255, 255])
    territories: list[str] = field(default_factory=list)
    allied_factions: list[str] = field(default_factory=list)
    rival_factions: list[str] = field(default_factory=list)
    influence: int = 50
    # 戦争勝敗で変動する物価補正 (負=安価, 正=高騰)。 shop 等の価格計算が参照する
    price_modifier: float = 0.0


class FactionWarRegistry:
    """派閥抗争レジストリ (シングルトン) (Steps 54, 55)"""

    _instance: FactionWarRegistry | None = None
    _factions: dict[str, FactionWarData] = {}
    _loaded: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._factions = {}
            cls._loaded = False
        return cls._instance

    def load(self, path: str = "data/faction_war.yaml") -> None:
        """YAMLから派閥抗争定義をロード (Step 55)"""
        if self._loaded:
            return
        p = Path(path)
        if not p.exists():
            self._loaded = True
            return

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            fw_data = data.get("faction_war_conditions", {})
            for fid, f_dict in fw_data.items():
                faction = FactionWarData(
                    id=fid,
                    name=f_dict.get("name", fid),
                    color=f_dict.get("color") or [255, 255, 255],
                    territories=f_dict.get("territories") or [],
                    allied_factions=f_dict.get("allied_factions") or [],
                    rival_factions=f_dict.get("rival_factions") or [],
                    influence=f_dict.get("influence", 50),
                    price_modifier=float(f_dict.get("price_modifier", 0.0)),
                )
                self._factions[fid] = faction
            self._loaded = True
        except Exception:
            logger.exception("Unhandled exception")
            # TODO: handle exception properly
            self._loaded = True

    def get(self, faction_id: str) -> FactionWarData | None:
        """特定派閥抗争データを取得 (Step 54)"""
        return self._factions.get(faction_id)

    def all(self) -> dict[str, FactionWarData]:
        """すべての派閥抗争データ辞書を返す (Step 54)"""
        return self._factions


REGISTRY = FactionWarRegistry()


# =============================================================================
# 派閥戦争ライフサイクル (T36 案A: 開戦 → 進行 → 決着 → 結果反映)
# =============================================================================

# 戦争ゲージの決着閾値 (+で攻撃側優勢, -で防衛側優勢)
WAR_GAUGE_LIMIT = 100.0
# 開戦に必要な影響力差 (ライバル関係にある派閥間で戦力差が開くと開戦)
WAR_START_INFLUENCE_DIFF = 20
# 戦況の自然変動を行う間隔 (ターン)
WAR_PROGRESS_INTERVAL = 10
# 1 回の自然変動量の上限 (影響力差 / 10 をクランプ)
WAR_MAX_DRIFT = 3.0
# 派閥 NPC 撃破のゲージ変動
WAR_KILL_GAUGE = 5.0
# 拠点級 (ボス) 撃破・拠点攻防の戦果ゲージ変動
WAR_BOSS_GAUGE = 20.0
# 善意/悪行のゲージ変動
WAR_DEED_GAUGE = 2.0
# 既定の戦争期間 (ターン)。期間満了時はゲージ優勢側の勝利
WAR_DURATION_TURNS = 500
# 終戦後、同じ派閥ペアが自動再開戦するまでのクールダウン (ターン)
WAR_RESTART_COOLDOWN_TURNS = 200
# 勝利派閥の影響力ボーナス
WAR_END_INFLUENCE_WIN = 10
# 敗北派閥の影響力ペナルティ
WAR_END_INFLUENCE_LOSS = 15
# 物価補正の戦後変動幅 (勝利=割引, 敗北=高騰)
WAR_END_PRICE_SHIFT = 0.1
# 物価補正のクランプ範囲
WAR_PRICE_MODIFIER_MIN = -0.5
WAR_PRICE_MODIFIER_MAX = 0.5
# プレイヤー貢献 → 評判変換の 1 派閥あたり上限
WAR_END_REP_CAP = 10


@dataclass
class FactionWar:
    """進行中の派閥戦争 1 件の状態

    gauge は +WAR_GAUGE_LIMIT で攻撃側の決定的勝利、
    -WAR_GAUGE_LIMIT で防衛側の決定的勝利を表す。
    """

    attacker_id: str
    defender_id: str
    start_turn: int = 0
    gauge: float = 0.0
    duration_turns: int = WAR_DURATION_TURNS
    status: str = "active"  # "active" | "ended"
    winner_id: str | None = None
    end_turn: int | None = None
    # プレイヤーの戦争への貢献量 (派閥 ID → 正=後押し / 負=妨害)。終戦時に評判へ変換
    player_contributions: dict[str, int] = field(default_factory=dict)
    # 最後にゲージの自然変動を適用したターン
    last_progress_turn: int = 0

    @property
    def war_key(self) -> str:
        """派閥ペアの正規キー (重複開戦防止に使用)"""
        return "&".join(sorted((self.attacker_id, self.defender_id)))

    def other_side(self, faction_id: str) -> str | None:
        """戦争に参加しているもう一方の派閥 ID (参加していなければ None)"""
        if faction_id == self.attacker_id:
            return self.defender_id
        if faction_id == self.defender_id:
            return self.attacker_id
        return None

    def involves(self, faction_id: str) -> bool:
        """指定派閥がこの戦争に参加しているか"""
        return faction_id in (self.attacker_id, self.defender_id)


class FactionWarManager:
    """派閥抗争管理マネージャー (Steps 56-58)"""

    def __init__(
        self,
        registry: FactionWarRegistry | None = None,
        memory_registry: MemoryRegistryProtocol | None = None,
    ):
        self.registry = registry or REGISTRY
        self.memory_registry = memory_registry or (
            GLOBAL_MEMORY_REGISTRY if _HAS_NPC_MEMORY else None
        )
        # 進行中/終了済みの戦争 (war_key → FactionWar)
        self.wars: dict[str, FactionWar] = {}

    def calculate_influence_change(self, faction_id: str, game_state: Any = None) -> int:
        """影響力の自然変動量を計算 (Step 57)"""
        faction = self.registry.get(faction_id)
        if not faction:
            return 0
        # 領土数による影響力補正 (+1/領土)
        territory_bonus = len(faction.territories)
        # 同盟数によるプラス影響
        ally_bonus = len(faction.allied_factions)
        # ライバル存在による牽制
        rival_penalty = len(faction.rival_factions)
        change = territory_bonus + ally_bonus - rival_penalty
        return max(-5, min(5, change))

    def check_war_conditions(self, faction1_id: str, faction2_id: str) -> bool:
        """2つの派閥間で抗争が発生する条件をチェック (Step 58)"""
        f1 = self.registry.get(faction1_id)
        f2 = self.registry.get(faction2_id)
        if not f1 or not f2:
            return False
        # ライバル関係にあるか
        return bool(faction2_id in f1.rival_factions or faction1_id in f2.rival_factions)

    def apply_influence_effects(self, faction_id: str, change: int) -> None:
        """影響力変動を適用 (Step 56)"""
        faction = self.registry.get(faction_id)
        if not faction:
            return
        faction.influence = max(0, min(100, faction.influence + change))

        # Phase 2 連携：派閥影響力変動を NPC 記憶に記録
        if self.memory_registry and change != 0:
            for mgr in self.memory_registry.all_managers().values():
                # 同派閥 NPC に記録
                if getattr(mgr.npc, "faction_id", None) == faction_id:
                    importance = (
                        MemoryImportance.SIGNIFICANT
                        if (MemoryImportance and abs(change) > 5)
                        else (MemoryImportance.NOTABLE if MemoryImportance else None)
                    )
                    mgr.record_reputation_event(
                        subject_id=faction_id,
                        event_type="faction_influence_change",
                        delta=change,
                        source="faction_system",
                        importance=importance,
                    )

    # Phase 2 連携メソッド
    def get_faction_reputation_for_gate(self, player: Entity, faction_id: str) -> int:
        """ReputationGate 用派閥評判値取得（0-100 -> -100 to 100）"""
        faction = self.registry.get(faction_id)
        if not faction:
            return -50
        # 派閥影響力 0-100 を -100 to 100 にマッピング
        # プレイヤーの faction_reputation も加味
        player_rep = player.faction_reputation.get(faction_id, 0)
        return (faction.influence - 50) + player_rep

    def get_all_faction_reputations(self, player: Entity) -> dict[str, int]:
        """全派閥評判取得（噂伝播・評判ゲート用）"""
        result = {}
        for fid in self.registry.all():
            result[fid] = self.get_faction_reputation_for_gate(player, fid)
        return result

    def apply_rumor_influence(
        self,
        faction_id: str,
        delta: int,
        source: str = "rumor",
    ) -> bool:
        """噂伝播による派閥影響力変動（Phase 2 Step 6 連携）"""
        faction = self.registry.get(faction_id)
        if not faction:
            return False
        old = faction.influence
        faction.influence = max(0, min(100, faction.influence + delta))
        return faction.influence != old

    def get_rumor_spread_modifier(self, from_faction: str, to_faction: str) -> float:
        """噂伝播修正値取得（同盟=+0.2, 敵対=-0.3, 中立=0）"""
        if from_faction == to_faction:
            return 0.2
        f1 = self.registry.get(from_faction)
        f2 = self.registry.get(to_faction)
        if not f1 or not f2:
            return 0.0
        if self.check_war_conditions(from_faction, to_faction):
            return -0.3
        if to_faction in f1.allied_factions:
            return 0.2
        return 0.0

    # ------------------------------------------------------------------
    # 派閥戦争ライフサイクル (T36 案A)
    # ------------------------------------------------------------------

    def get_active_war(self, faction_id: str) -> FactionWar | None:
        """指定派閥が参加中の戦争を取得 (複数ある場合は最初の 1 件)"""
        for war in self.wars.values():
            if war.status == "active" and war.involves(faction_id):
                return war
        return None

    def get_active_wars(self) -> list[FactionWar]:
        """進行中の全戦争を取得"""
        return [w for w in self.wars.values() if w.status == "active"]

    def get_war(self, faction1_id: str, faction2_id: str) -> FactionWar | None:
        """2 派閥間の戦争を取得 (終了済みを含む)"""
        key = "&".join(sorted((faction1_id, faction2_id)))
        return self.wars.get(key)

    def start_war(
        self,
        attacker_id: str,
        defender_id: str,
        start_turn: int = 0,
        duration_turns: int = WAR_DURATION_TURNS,
    ) -> FactionWar | None:
        """派閥戦争を開始する (クエスト等からの手動開戦も可)

        同一派閥間・未登録派閥・同一ペアの重複開戦は拒否し None を返す。
        ライバル関係や影響力差の条件判定は _maybe_start_wars 側で行う。
        """
        if attacker_id == defender_id:
            return None
        if not self.registry.get(attacker_id) or not self.registry.get(defender_id):
            return None
        key = "&".join(sorted((attacker_id, defender_id)))
        if key in self.wars and self.wars[key].status == "active":
            return None
        war = FactionWar(
            attacker_id=attacker_id,
            defender_id=defender_id,
            start_turn=start_turn,
            duration_turns=duration_turns,
            last_progress_turn=start_turn,
        )
        self.wars[key] = war
        return war

    def progress_wars(
        self,
        current_turn: int = 0,
        player: Entity | None = None,
    ) -> list[dict[str, Any]]:
        """派閥戦争を現在ターンまで進行させる

        1. 開戦判定 (ライバル関係 & 影響力差が閾値以上)
        2. 進行中戦争のゲージ自然変動 (WAR_PROGRESS_INTERVAL 間隔)
        3. 決着判定 → 終戦処理と結果反映

        戻り値: ログ/FX 表示用のイベント辞書リスト
        (type: "war_started" | "war_ended", message/color/level/effects を含む)
        """
        events: list[dict[str, Any]] = []
        events.extend(self._maybe_start_wars(current_turn))
        for war in list(self.wars.values()):
            if war.status != "active":
                continue
            self._advance_gauge(war, current_turn)
            winner_id, reason = self.determine_winner(war, current_turn)
            if winner_id is not None or reason == "draw":
                ended = self.end_war(war, current_turn, player)
                if ended is not None:
                    events.append(ended)
        return events

    def _maybe_start_wars(self, current_turn: int) -> list[dict[str, Any]]:
        """開戦条件を満たしたライバル派閥ペアに宣戦布告させる"""
        events: list[dict[str, Any]] = []
        fids = sorted(self.registry.all().keys())
        for i, f1 in enumerate(fids):
            for f2 in fids[i + 1:]:
                past = self.get_war(f1, f2)
                if past is not None:
                    if past.status == "active":
                        continue
                    # 終戦直後の再開戦はクールダウンで抑制する
                    if (
                        past.end_turn is not None
                        and current_turn - past.end_turn < WAR_RESTART_COOLDOWN_TURNS
                    ):
                        continue
                if not self.check_war_conditions(f1, f2):
                    continue
                a = self.registry.get(f1)
                b = self.registry.get(f2)
                if a is None or b is None:
                    continue
                diff = a.influence - b.influence
                if abs(diff) < WAR_START_INFLUENCE_DIFF:
                    continue
                attacker_id, defender_id = (f1, f2) if diff > 0 else (f2, f1)
                war = self.start_war(attacker_id, defender_id, start_turn=current_turn)
                if war is None:
                    continue
                attacker = self.registry.get(attacker_id)
                defender = self.registry.get(defender_id)
                events.append(
                    {
                        "type": "war_started",
                        "war": war,
                        "message": (
                            f"⚔️【派閥戦争】{attacker.name}が{defender.name}に宣戦布告！"
                        ),
                        "color": (255, 140, 60),
                        "level": "WARNING",
                        "floating_text": (f"{attacker.name} vs {defender.name}", (255, 140, 60)),
                    }
                )
        return events

    def _advance_gauge(self, war: FactionWar, current_turn: int) -> None:
        """戦争ゲージの自然変動を適用する (WAR_PROGRESS_INTERVAL 間隔)"""
        elapsed = current_turn - war.last_progress_turn
        if elapsed < WAR_PROGRESS_INTERVAL:
            return
        ticks = int(elapsed // WAR_PROGRESS_INTERVAL)
        war.last_progress_turn += ticks * WAR_PROGRESS_INTERVAL
        attacker = self.registry.get(war.attacker_id)
        defender = self.registry.get(war.defender_id)
        if not attacker or not defender:
            return
        # 影響力差 (10 あたり +1) を 1 変動量の上限でクランプ
        drift = max(-WAR_MAX_DRIFT, min(WAR_MAX_DRIFT, (attacker.influence - defender.influence) / 10.0))
        war.gauge += drift * ticks

    def determine_winner(
        self,
        war: FactionWar,
        current_turn: int,
    ) -> tuple[str | None, str | None]:
        """勝敗を判定する

        戻り値: (勝者派閥 ID, 判定理由)。理由は
        "decisive" (ゲージ決着) | "duration" (期間満了・優勢側勝利) | "draw" (停戦) | None (継続)。
        勝者なし + "draw" が停戦、勝者なし + None が戦争継続を表す。
        """
        if war.status != "active":
            return None, None
        if war.gauge >= WAR_GAUGE_LIMIT:
            return war.attacker_id, "decisive"
        if war.gauge <= -WAR_GAUGE_LIMIT:
            return war.defender_id, "decisive"
        if current_turn >= war.start_turn + war.duration_turns:
            if war.gauge > 0:
                return war.attacker_id, "duration"
            if war.gauge < 0:
                return war.defender_id, "duration"
            return None, "draw"
        return None, None

    def end_war(
        self,
        war: FactionWar,
        current_turn: int = 0,
        player: Entity | None = None,
    ) -> dict[str, Any] | None:
        """戦争を終結させ、勝利派閥の領土/物価/影響力/評判に結果を反映する

        停戦 (draw) の場合は派閥側の変動は行わない。
        二重終結時は None を返す。
        """
        if war.status == "ended":
            return None
        winner_id, reason = self.determine_winner(war, current_turn)
        war.status = "ended"
        war.winner_id = winner_id
        war.end_turn = current_turn

        attacker = self.registry.get(war.attacker_id)
        defender = self.registry.get(war.defender_id)
        attacker_name = attacker.name if attacker else war.attacker_id
        defender_name = defender.name if defender else war.defender_id

        if winner_id is None:
            # 停戦: 派閥側の変動なし、プレイヤー貢献は無効化
            war.player_contributions.clear()
            return {
                "type": "war_ended",
                "war": war,
                "winner_id": None,
                "reason": "draw",
                "message": f"🕊️【派閥戦争】{attacker_name}と{defender_name}は停戦に至った。",
                "effects": [],
                "color": (150, 200, 255),
                "level": "INFO",
                "floating_text": ("停戦", (150, 200, 255)),
            }

        winner = self.registry.get(winner_id)
        loser_id = war.other_side(winner_id) or ""
        loser = self.registry.get(loser_id)
        effects = self._apply_war_results(war, winner, loser, player)
        winner_name = winner.name if winner else winner_id
        loser_name = loser.name if loser else loser_id
        winner_color = tuple(winner.color) if winner else (255, 215, 0)
        return {
            "type": "war_ended",
            "war": war,
            "winner_id": winner_id,
            "loser_id": loser_id,
            "reason": reason,
            "message": f"🏳️【派閥戦争終結】{winner_name}が{loser_name}との戦争に勝利した！",
            "effects": effects,
            "color": winner_color,
            "level": "SUCCESS",
            "floating_text": (f"{winner_name}勝利！", winner_color),
        }

    def _apply_war_results(
        self,
        war: FactionWar,
        winner: FactionWarData | None,
        loser: FactionWarData | None,
        player: Entity | None,
    ) -> list[str]:
        """終戦結果を派閥データとプレイヤー評判へ反映し、説明文リストを返す"""
        effects: list[str] = []
        if winner is not None:
            self.apply_influence_effects(winner.id, WAR_END_INFLUENCE_WIN)
            winner.price_modifier = max(
                WAR_PRICE_MODIFIER_MIN, winner.price_modifier - WAR_END_PRICE_SHIFT
            )
            effects.append(f"{winner.name}の影響力が高まり、物価が下がった。")
        if loser is not None:
            self.apply_influence_effects(loser.id, -WAR_END_INFLUENCE_LOSS)
            loser.price_modifier = min(
                WAR_PRICE_MODIFIER_MAX, loser.price_modifier + WAR_END_PRICE_SHIFT
            )
            effects.append(f"{loser.name}は影響力を失い、物価が高騰した。")
            # 敗北派閥が複数領土を持つ場合は 1 領土が勝利派閥へ移る
            if winner is not None and len(loser.territories) > 1:
                captured = loser.territories[-1]
                loser.territories.remove(captured)
                winner.territories.append(captured)
                effects.append(f"領土「{captured}」は{winner.name}の支配下に置かれた。")
        effects.extend(self._convert_player_contributions(war, player))
        return effects

    def _convert_player_contributions(
        self,
        war: FactionWar,
        player: Entity | None,
    ) -> list[str]:
        """プレイヤーの戦争貢献を派閥評判へ変換する (1 貢献 = 評判 1, 上限付き)"""
        lines: list[str] = []
        if player is None or not hasattr(player, "faction_reputation"):
            war.player_contributions.clear()
            return lines
        for fid in sorted(war.player_contributions):
            contrib = war.player_contributions[fid]
            if contrib == 0:
                continue
            faction = self.registry.get(fid)
            if faction is None:
                continue
            delta = max(-WAR_END_REP_CAP, min(WAR_END_REP_CAP, contrib))
            player.faction_reputation[fid] = player.faction_reputation.get(fid, 0) + delta
            lines.append(f"{faction.name}からの評価が{delta:+d}変動した。")
        war.player_contributions.clear()
        return lines

    # --- プレイヤー影響フック (combat_system 等の既存イベントから呼ばれる) ---

    def record_kill(self, victim_faction_id: str, boss: bool = False) -> float:
        """派閥 NPC の撃破を戦況へ反映する

        撃破された派閥の対戦側にゲージが傾き、対戦側へのプレイヤー貢献として
        記録される。ボス級は拠点攻防級の戦果として大きく反映する。
        戦争が進行していない場合は 0.0 を返す。
        """
        war = self.get_active_war(victim_faction_id)
        if war is None:
            return 0.0
        shift = WAR_BOSS_GAUGE if boss else WAR_KILL_GAUGE
        victim_on_attacker_side = victim_faction_id == war.attacker_id
        delta = -shift if victim_on_attacker_side else shift
        war.gauge += delta
        beneficiary = war.other_side(victim_faction_id)
        if beneficiary is not None:
            war.player_contributions[beneficiary] = (
                war.player_contributions.get(beneficiary, 0) + 1
            )
        return delta

    def record_deed(self, faction_id: str, good: bool, amount: int = 1) -> float:
        """善意/悪行を戦況へ反映する

        good=True は当該派閥の戦力を後押しし、False は削ぐ。
        戦争が進行していない場合は 0.0 を返す。
        """
        side_delta = (WAR_DEED_GAUGE if good else -WAR_DEED_GAUGE) * amount
        return self._shift_gauge(
            faction_id, side_delta, amount if good else -amount
        )

    def record_territory_battle(
        self,
        faction_id: str,
        success: bool,
        amount: int = 1,
    ) -> float:
        """拠点攻防の成否を戦況へ反映する

        派閥戦争クエスト (data/faction_war_quests.yaml) の前線/拠点目標の
        達成時に呼び出すことを想定する。success=True は当該派閥側の戦果と
        してゲージを押し上げる。
        """
        side_delta = (WAR_BOSS_GAUGE if success else -WAR_BOSS_GAUGE) * amount
        return self._shift_gauge(
            faction_id, side_delta, amount if success else -amount
        )

    def _shift_gauge(
        self,
        faction_id: str,
        side_delta: float,
        contribution: int,
    ) -> float:
        """当該派閥の立場 (攻撃/防衛側) に合わせてゲージと貢献を反映する共通処理"""
        war = self.get_active_war(faction_id)
        if war is None:
            return 0.0
        delta = side_delta if faction_id == war.attacker_id else -side_delta
        war.gauge += delta
        war.player_contributions[faction_id] = (
            war.player_contributions.get(faction_id, 0) + contribution
        )
        return delta

    def get_faction_status(self) -> list[dict[str, Any]]:
        """Web 配信用の派閥状態スナップショットを返す (影響力/領土/物価/開戦状態)"""
        status: list[dict[str, Any]] = []
        for fid, faction in self.registry.all().items():
            war = self.get_active_war(fid)
            entry: dict[str, Any] = {
                "id": fid,
                "name": faction.name,
                "influence": faction.influence,
                "territories": list(faction.territories),
                "color": list(faction.color),
                "price_modifier": round(faction.price_modifier, 3),
                "at_war": war is not None,
            }
            if war is not None:
                enemy_id = war.other_side(fid) or ""
                enemy = self.registry.get(enemy_id)
                entry["war"] = {
                    "enemy_id": enemy_id,
                    "enemy_name": enemy.name if enemy else enemy_id,
                    "is_attacker": fid == war.attacker_id,
                    # 正値=自陣営 (攻撃側) 優勢
                    "gauge": round(war.gauge, 1),
                    "start_turn": war.start_turn,
                    "duration_turns": war.duration_turns,
                }
            status.append(entry)
        return status
