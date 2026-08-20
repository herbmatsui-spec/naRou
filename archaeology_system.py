"""
考古学・発掘・解読メタゲーム システム (Steps 15-24)
memory_fragments.yaml と story_endings.yaml を truth_codex 経由で連携し、
「発掘 → 収集 → 解読 → 真理到達 → プレイヤーの解釈によるエンディング分岐」のループを実装する。
"""

from __future__ import annotations

import os
import random
from typing import Any

import yaml

from core_framework import BaseSystem

try:
    from components import ReincarnationComponent
except Exception:  # 循環防止（通常は存在）
    ReincarnationComponent = None

DATA_DIR = "data"


class ArchaeologyRegistry:
    """考古学データの一元ロード・キャッシュ (Step 15)"""

    _instance: ArchaeologyRegistry | None = None

    def __new__(cls) -> ArchaeologyRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._fragments: dict[str, Any] = {}
            cls._endings: dict[str, Any] = {}
            cls._sites: dict[str, Any] = {}
            cls._keys: dict[str, Any] = {}
            cls._truths: dict[str, Any] = {}
            cls._cipher_to_key: dict[str, str] = {}
        return cls._instance

    # ---------- ロード ----------
    def load(self, data_dir: str = DATA_DIR) -> None:
        self._fragments = (
            self._load_section(data_dir, "memory_fragments.yaml", "memory_fragments")
            or {}
        )
        self._endings = (
            self._load_section(data_dir, "story_endings.yaml", "story_endings") or {}
        )
        self._sites = (
            self._load_section(data_dir, "archaeology_sites.yaml", "archaeology_sites")
            or {}
        )
        self._keys = (
            self._load_section(data_dir, "decoder_keys.yaml", "decoder_keys") or {}
        )
        self._truths = (
            self._load_section(data_dir, "truth_codex.yaml", "truth_codex") or {}
        )
        # cipher_type -> key_id マップ構築
        self._cipher_to_key = {}
        for kid, kval in self._keys.items():
            ct = kval.get("cipher_type")
            if ct:
                self._cipher_to_key[ct] = kid

    def _load_section(
        self, data_dir: str, filename: str, section: str
    ) -> dict[str, Any] | None:
        path = os.path.join(data_dir, filename)
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f).get(section, {}) or {}
        except Exception as e:
            print(f"[ArchaeologyRegistry] Failed to load {filename}: {e}")
            return None

    # ---------- 取得 ----------
    def get_fragment(self, fid: str) -> dict[str, Any] | None:
        return self._fragments.get(fid)

    def get_site(self, sid: str) -> dict[str, Any] | None:
        return self._sites.get(sid)

    def get_key(self, kid: str) -> dict[str, Any] | None:
        return self._keys.get(kid)

    def get_truth(self, tid: str) -> dict[str, Any] | None:
        return self._truths.get(tid)

    def get_ending(self, eid: str) -> dict[str, Any] | None:
        return self._endings.get(eid)

    def all_truths(self) -> dict[str, Any]:
        return dict(self._truths)

    def key_for_cipher(self, cipher_type: str) -> str | None:
        return self._cipher_to_key.get(cipher_type)

    def find_site_for_depth(self, depth: int) -> str | None:
        """指定深度で発掘可能な遺跡サイト id を1件返す (Step 26 入力フック用)
        深度範囲が重なる場合は、min_depth が最も深い（最も特化した）サイトを優先する。"""
        candidates = [
            sid
            for sid, s in self._sites.items()
            if int(s.get("min_depth", 1)) <= depth <= int(s.get("max_depth", 999))
        ]
        if not candidates:
            return None
        return max(
            candidates, key=lambda sid: int(self._sites[sid].get("min_depth", 1))
        )

    def pick_site_for_excavation(
        self, depth: int, rng: Any | None = None
    ) -> str | None:
        """発掘用サイト選出（改善③: バリエーション）。
        深度で一致する複数サイトからランダムに1件選ぶ。該当なしは None。"""
        rng = rng or random
        candidates = [
            sid
            for sid, s in self._sites.items()
            if int(s.get("min_depth", 1)) <= depth <= int(s.get("max_depth", 999))
        ]
        if not candidates:
            return None
        return rng.choice(candidates)


REGISTRY = ArchaeologyRegistry()


class ArchaeologyManager(BaseSystem):
    """考古学ループの進行・判定管理 (Steps 16-23)"""

    def __init__(self, registry: ArchaeologyRegistry | None = None):
        super().__init__("archaeology_manager")
        self.registry = registry or REGISTRY
        if not self.registry._fragments:
            self.registry.load()

    # ---------- Step 16: 発掘ドロップ解決 ----------
    def resolve_excavation(
        self, site_id: str, rng: Any | None = None
    ) -> tuple[str | None, str | None]:
        """遺跡サイトから断片と鍵を重み付き抽選 (fragment_id, key_id)"""
        site = self.registry.get_site(site_id)
        if not site:
            return None, None
        rng = rng or random
        frag_pool = site.get("fragment_pool", {}) or {}
        key_pool = site.get("decoder_key_pool", {}) or {}
        frag_id = self._weighted_choice(frag_pool, rng)
        key_id = self._weighted_choice(key_pool, rng)
        return frag_id, key_id

    def _weighted_choice(self, pool: dict[str, int], rng: Any) -> str | None:
        if not pool:
            return None
        total = sum(pool.values())
        if total <= 0:
            return None
        r = rng.random() * total
        cum = 0
        for k, w in pool.items():
            cum += w
            if r < cum:
                return k
        return list(pool.keys())[-1]

    # ---------- Step 17: 収集 ----------
    def collect_fragment(
        self, player: Any, fragment_id: str, engine: Any | None = None
    ) -> bool:
        """生断片を収集（重複排除）し、StorytellerComponent の memory_fragments とも連携"""
        comp = player.archaeology
        if fragment_id in comp.collected_fragments:
            return False
        comp.collected_fragments.append(fragment_id)
        comp.decipherment_gauge += 1
        frag = self.registry.get_fragment(fragment_id)
        # 他システム連携: 既存 memory_fragments リストにも名前を同期
        if frag:
            name = frag.get("name", fragment_id)
            if name not in player.memory_fragments:
                player.memory_fragments.append(name)
            # メタ進行・実績 (Step 30): ReincarnationComponent の collected_fragments へも dict で同期
            try:
                reinc_comp = player.get_component(ReincarnationComponent)
                if not any(
                    f.get("fragment_id") == fragment_id
                    for f in reinc_comp.collected_fragments
                    if isinstance(f, dict)
                ):
                    reinc_comp.collected_fragments.append(
                        {
                            "fragment_id": fragment_id,
                            "name": name,
                            "category": frag.get("cipher_type", ""),
                        }
                    )
            except Exception:
                pass
        if engine and hasattr(engine, "log"):
            engine.log(
                f"⛏【発掘】記憶の欠片『{frag.get('name', fragment_id) if frag else fragment_id}』を出土した！",
                (255, 215, 0),
            )
        return True

    # ---------- Step 18: デコーダー鍵 ----------
    def acquire_key(self, player: Any, key_id: str, engine: Any | None = None) -> bool:
        comp = player.archaeology
        if key_id in comp.owned_keys:
            return False
        comp.owned_keys.append(key_id)
        key = self.registry.get_key(key_id)
        if engine and hasattr(engine, "log"):
            engine.log(
                f"🗝【鍵】『{key.get('name', key_id) if key else key_id}』を手に入れた。",
                (180, 220, 255),
            )
        # 改善③: 後から鍵を得たとき、既収集の未解読断片を自動解読し直す
        self.recheck_decoding(player, engine)
        return True

    def recheck_decoding(self, player: Any, engine: Any | None = None) -> list[str]:
        """所有鍵で解読可能になった未解読断片を一括解読（改善③: 遅延解読）"""
        newly = []
        for fid in list(player.archaeology.collected_fragments):
            if fid not in player.archaeology.decoded_fragments:
                if self.decode_fragment(player, fid, engine):
                    newly.append(fid)
        return newly

    def has_key_for_cipher(self, player: Any, cipher_type: str) -> bool:
        key_id = self.registry.key_for_cipher(cipher_type)
        if not key_id:
            return False
        return key_id in player.archaeology.owned_keys

    # ---------- Step 29: 効果音ヘルパ ----------
    @staticmethod
    def _play_se(engine: Any | None, name: str) -> None:
        try:
            from sound_manager import SoundManager

            SoundManager.play_se(name)
        except Exception:
            pass

    # ---------- Step 19: 解読 ----------
    def decode_fragment(
        self, player: Any, fragment_id: str, engine: Any | None = None
    ) -> bool:
        """対応する言語族の鍵を所有していれば解読。未所持ならヒントのみ提示。"""
        comp = player.archaeology
        if fragment_id in comp.decoded_fragments:
            return False
        frag = self.registry.get_fragment(fragment_id)
        if not frag:
            return False
        cipher = frag.get("cipher_type", "")
        if not self.has_key_for_cipher(player, cipher):
            hint = frag.get("decoder_hint", "手がかりを探せ")
            # 改善③: 未解読ヒント（気づき）を蓄積
            if hint and hint not in player.archaeology.decoder_hints_seen:
                player.archaeology.decoder_hints_seen.append(hint)
            if engine and hasattr(engine, "log"):
                engine.log(
                    f"❓【未解読】『{frag.get('name', fragment_id)}』の文字は読めない…（{hint}）",
                    (200, 200, 160),
                )
            return False
        comp.decoded_fragments.append(fragment_id)
        if engine and hasattr(engine, "log"):
            engine.log(
                f"📜【解読】『{frag.get('name', fragment_id)}』の暗号が解かれた！",
                (150, 255, 180),
            )
        self._play_se(engine, "level_up")
        # 解読が進めば真理到達を評価
        self.check_truth_progress(player, engine)
        return True

    # ---------- Step 20/21: 真理到達 ----------
    def check_truth_progress(self, player: Any, engine: Any | None = None) -> list[str]:
        """解読済み断片から到達可能な真理ノードを評価し、新規到達を記録"""
        comp = player.archaeology
        decoded = set(comp.decoded_fragments)
        newly = []
        for tid, t in self.registry.all_truths().items():
            if tid in comp.reached_truths:
                continue
            required = t.get("required_decoded_fragments", []) or []
            if required and decoded.issuperset(set(required)):
                comp.reached_truths.append(tid)
                newly.append(tid)
                if engine and hasattr(engine, "log"):
                    engine.log(
                        f"🌟【真理到達】『{t.get('name', tid)}』の全貌が見えた！",
                        (255, 240, 120),
                    )
                self._play_se(engine, "victory")
        return newly

    # ---------- Step 22: エンディング候補提示 ----------
    def suggest_endings(self, player: Any) -> list[tuple[str, str]]:
        """到達済み真理ノードから候補エンディング (truth_id, ending_id) を収集"""
        comp = player.archaeology
        out: list[tuple[str, str]] = []
        for tid in comp.reached_truths:
            t = self.registry.get_truth(tid)
            if not t:
                continue
            for eid in t.get("candidate_endings", []) or []:
                out.append((tid, eid))
        return out

    def get_available_endings(self, player: Any) -> list[str]:
        """解釈が記録され、考古学経由で到達可能なエンディング id 一覧"""
        comp = player.archaeology
        return list(comp.leaned_endings.values())

    # ---------- 改善①: エンディング実解決パイプライン ----------
    def is_ending_reachable(self, player: Any, ending_id: str) -> bool:
        """到達済み真理に対して、そのエンディングへ寄った解釈が記録されているか"""
        return ending_id in self.get_available_endings(player)

    def trigger_ending(
        self, player: Any, ending_id: str, engine: Any | None = None
    ) -> bool:
        """story_endings.yaml の unlock_conditions を実際に満たし、エンディング到達を発生させる（改善①）"""
        if not self.is_ending_reachable(player, ending_id):
            if engine and hasattr(engine, "log"):
                engine.log(
                    "そのエンディングはまだ考古学の解釈から到達していない。",
                    (200, 120, 120),
                )
            return False
        ending = self.registry.get_ending(ending_id)
        # データ駆動で unlock_conditions の各トークンを story_flags に True で書き込み（本当に満たす）
        for cond in ending.get("unlock_conditions", []) if ending else []:
            player.story_flags[cond] = True
        player.story_flags[f"ending_{ending_id}_unlocked_by_archaeology"] = True
        # エンディング進行度を記録（StorytellerComponent.ending_progress）
        try:
            player.ending_progress[ending_id] = max(
                int(player.ending_progress.get(ending_id, 0)), 1
            )
        except Exception:
            pass
        if engine and hasattr(engine, "log"):
            scene = ending.get("ending_scene", "") if ending else ""
            engine.log(
                f"🏁【エンディング到達】『{ending.get('name', ending_id) if ending else ending_id}』（幕: {scene}）に辿り着いた！",
                (255, 230, 120),
            )
        self._play_se(engine, "victory")
        return True

    def trigger_available_endings(
        self, player: Any, engine: Any | None = None
    ) -> list[str]:
        """解釈済みエンディングを全て発生させる"""
        triggered = []
        for eid in self.get_available_endings(player):
            if self.trigger_ending(player, eid, engine):
                triggered.append(eid)
        return triggered

    # ---------- Step 23: 解釈による分岐記録 ----------
    def interpret_truth(
        self,
        player: Any,
        truth_id: str,
        ending_id: str,
        note: str = "",
        engine: Any | None = None,
    ) -> bool:
        """プレイヤーの解釈（寄り先エンディング）を記録し、story_endings への接続フラグをセット"""
        comp = player.archaeology
        if truth_id not in comp.reached_truths:
            if engine and hasattr(engine, "log"):
                engine.log("その真理にはまだ到達していない。", (200, 120, 120))
            return False
        t = self.registry.get_truth(truth_id)
        candidates = t.get("candidate_endings", []) if t else []
        if ending_id not in candidates:
            if engine and hasattr(engine, "log"):
                engine.log(
                    "そのエンディングはこの真理の候補ではない。", (200, 120, 120)
                )
            return False
        comp.leaned_endings[truth_id] = ending_id
        if note:
            comp.interpretation_notes[truth_id] = note
        # story_endings との接続: 考古学がこのエンディングを解放したことを他システムへ通知
        player.story_flags[f"ending_{ending_id}_unlocked_by_archaeology"] = True
        if engine and hasattr(engine, "log"):
            ending = self.registry.get_ending(ending_id)
            engine.log(
                f"💭【解釈】『{t.get('name', truth_id) if t else truth_id}』を『{ending.get('name', ending_id) if ending else ending_id}』の視点で読んだ。",
                (220, 200, 255),
            )
        self._play_se(engine, "level_up")
        # 改善①: 解釈＝即エンディング到達（story_endings の unlock_conditions を実際に満たす）
        self.trigger_ending(player, ending_id, engine)
        return True

    # ---------- Step 32/33: 出力 ----------
    def export_ledger(self, player: Any) -> dict[str, Any]:
        """解釈台帳（interpretation ledger）を辞書で出力"""
        comp = player.archaeology
        return {
            "collected_fragments": list(comp.collected_fragments),
            "decoded_fragments": list(comp.decoded_fragments),
            "reached_truths": list(comp.reached_truths),
            "leaned_endings": dict(comp.leaned_endings),
            "interpretation_notes": dict(comp.interpretation_notes),
            "decoder_hints_seen": list(comp.decoder_hints_seen),
        }

    def export_share_summary(self, player: Any) -> str:
        """コミュニティ共有用サマリーテキストを生成"""
        comp = player.archaeology
        lines = ["# 私の到達した真実（考古学メタゲーム）", ""]
        for tid in comp.reached_truths:
            t = self.registry.get_truth(tid)
            name = t.get("name", tid) if t else tid
            ending_id = comp.leaned_endings.get(tid, "(未解釈)")
            ending = self.registry.get_ending(ending_id)
            ending_name = ending.get("name", ending_id) if ending else ending_id
            note = comp.interpretation_notes.get(tid, "")
            lines.append(f"- 真理『{name}』→ 解釈: 『{ending_name}』")
            if note:
                lines.append(f"  > {note}")
        if len(comp.reached_truths) == 0:
            lines.append("（まだいずれの真理にも到達していません）")
        if comp.decoder_hints_seen:
            lines.append("")
            lines.append("## 蓄積された手がかり（未解読ヒント）")
            for h in comp.decoder_hints_seen:
                lines.append(f"- 💡 {h}")
        return "\n".join(lines)
