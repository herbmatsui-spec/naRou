"""
Elona Masterpiece Edition - Archaeology & Decoder System (Phase 5, Steps 25-48)
Handles ancient memory fragments, glyph text obfuscation, dynamic translation, and key unlocks.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from naRou.data_manager import DataManager

if TYPE_CHECKING:
    from naRou.ecs.entity import Entity


GLYPH_CHARS = ["⟁", "⌖", "⏃", "⏚", "⟒", "⟟", "☉", "⟡", "⌬", "⌁", "✦", "✧", "※"]
PUNCTUATION_CHARS = set(" 。、，！？!?…\n\t「」『』（）()【】:：-—")


def obfuscate_text(translated_text: str, glyph_script: str = "", decode_ratio: float = 0.0) -> str:
    """
    日本語を含むテキストを、解読率(0.0〜1.0)に応じてグリフ記号に部分置換する (Step 30 & Step 46)
    - マルチバイト文字を安全に扱い、文字化けクラッシュを防止。
    - decode_ratio >= 1.0 の場合は完全にクリアな日本語を返す。
    - decode_ratio <= 0.0 の場合はグリフ文字のみを返す。
    """
    if not translated_text:
        return glyph_script or ""

    if decode_ratio >= 1.0:
        return translated_text

    # 解読率 0.0 の場合はすべてグリフ化
    if decode_ratio <= 0.0:
        result_chars = []
        for i, ch in enumerate(translated_text):
            if ch in PUNCTUATION_CHARS:
                result_chars.append(ch)
            else:
                glyph_idx = (i * 7 + 3) % len(GLYPH_CHARS)
                result_chars.append(GLYPH_CHARS[glyph_idx])
        return "".join(result_chars)

    # 0.0 < decode_ratio < 1.0: 決定論的ハッシュで一部文字を開示
    result_chars = []
    text_len = len(translated_text)

    for i, ch in enumerate(translated_text):
        if ch in PUNCTUATION_CHARS:
            result_chars.append(ch)
            continue

        # 文字位置とテキストに基づく疑似乱数ハッシュ
        char_hash = int(hashlib.md5(f"{i}_{ch}".encode("utf-8")).hexdigest()[:6], 16) / 0xFFFFFF
        if char_hash < decode_ratio:
            result_chars.append(ch)
        else:
            glyph_idx = (i * 11 + int(decode_ratio * 100)) % len(GLYPH_CHARS)
            result_chars.append(GLYPH_CHARS[glyph_idx])

    return "".join(result_chars)


class ArchaeologyDecoderSystem:
    """考古学・暗号解読管理システム"""

    def __init__(self, data_manager: DataManager | None = None, data_dir: str = "data"):
        self.data_manager = data_manager or DataManager()
        self.data_dir = Path(data_dir)
        self.memory_fragments: dict[str, dict[str, Any]] = {}
        self.decoder_keys: dict[str, dict[str, Any]] = {}
        self.load_data()

    def load_data(self) -> None:
        """YAMLデータの読み込み (Step 25)"""
        frag_path = self.data_dir / "memory_fragments.yaml"
        if frag_path.exists():
            with open(frag_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
                self.memory_fragments = raw.get("memory_fragments", {})

        key_path = self.data_dir / "decoder_keys.yaml"
        if key_path.exists():
            with open(key_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
                self.decoder_keys = raw.get("decoder_keys", {})

    def get_fragment_state(self, entity: Entity, fragment_id: str) -> dict[str, Any] | None:
        """指定フラグメントの解読状態を取得 (Step 30, 31)"""
        frag = self.memory_fragments.get(fragment_id)
        if not frag:
            return None

        cipher_type = frag.get("cipher_type", "")
        arch = getattr(entity, "archaeology", None)
        owned_keys = getattr(arch, "owned_keys", []) if arch else []
        decoded_fragments = getattr(arch, "decoded_fragments", []) if arch else []
        gauge = getattr(arch, "decipherment_gauge", 0) if arch else 0

        # 対応する鍵を持っているか判定
        matching_key_id = None
        has_key = False
        for k_id, k_data in self.decoder_keys.items():
            if k_data.get("cipher_type") == cipher_type:
                matching_key_id = k_id
                if k_id in owned_keys:
                    has_key = True
                break

        # 解読率の算出
        if fragment_id in decoded_fragments or has_key:
            decode_ratio = 1.0
        else:
            # ゲージによる部分解読 (最大60%まで)
            decode_ratio = min(0.60, (gauge / 100.0) * 0.60)

        translated_text = frag.get("translated_text", "")
        glyph_script = frag.get("glyph_script", "")
        displayed_text = obfuscate_text(translated_text, glyph_script, decode_ratio)

        return {
            "id": fragment_id,
            "name": frag.get("name", fragment_id),
            "description": frag.get("description", ""),
            "cipher_type": cipher_type,
            "glyph_script": glyph_script,
            "translated_text": translated_text,
            "displayed_text": displayed_text,
            "decode_ratio": round(decode_ratio, 2),
            "is_decoded": decode_ratio >= 1.0,
            "has_key": has_key,
            "matching_key_id": matching_key_id,
            "decoder_hint": frag.get("decoder_hint", ""),
            "truth_link": frag.get("truth_link", ""),
        }

    def collect_fragment(self, entity: Entity, fragment_id: str) -> tuple[bool, str]:
        """フラグメントの発見・収集 (Step 29)"""
        frag = self.memory_fragments.get(fragment_id)
        if not frag:
            return False, f"記憶フラグメント '{fragment_id}' が存在しません。"

        arch = getattr(entity, "archaeology", None)
        if not arch:
            return False, "エンティティに考古学コンポーネントがありません。"

        if fragment_id not in arch.collected_fragments:
            arch.collected_fragments.append(fragment_id)
            arch.decipherment_gauge = min(100, arch.decipherment_gauge + 20)
            msg = f"📜 古代の記憶断片【{frag.get('name', fragment_id)}】を発見しました！ (解読知識 +20%)"
        else:
            msg = f"📜 【{frag.get('name', fragment_id)}】を再度確認しました。"

        return True, msg

    def unlock_decoder_key(self, entity: Entity, key_id: str) -> tuple[bool, str]:
        """デコーダー鍵の獲得・適用 (Step 29, 37)"""
        key_data = self.decoder_keys.get(key_id)
        if not key_data:
            return False, f"デコーダー鍵 '{key_id}' が存在しません。"

        arch = getattr(entity, "archaeology", None)
        if not arch:
            return False, "エンティティに考古学コンポーネントがありません。"

        if key_id not in arch.owned_keys:
            arch.owned_keys.append(key_id)

        cipher_type = key_data.get("cipher_type", "")
        newly_decoded = []

        # 対応する言語族の収集済みフラグメントを完全解読
        for f_id in arch.collected_fragments:
            frag = self.memory_fragments.get(f_id)
            if frag and frag.get("cipher_type") == cipher_type:
                if f_id not in arch.decoded_fragments:
                    arch.decoded_fragments.append(f_id)
                    newly_decoded.append(frag.get("name", f_id))

        if newly_decoded:
            summary = ", ".join(newly_decoded)
            msg = f"🗝️ 【{key_data.get('name', key_id)}】を獲得しました！【{summary}】の解読に成功しました！"
        else:
            msg = f"🗝️ 【{key_data.get('name', key_id)}】を獲得しました！（言語: {cipher_type}）"

        return True, msg

    def get_all_fragments_state(self, entity: Entity) -> list[dict[str, Any]]:
        """全フラグメントの現在状態を取得 (UI・API用) (Step 31, 39)"""
        results = []
        for frag_id in self.memory_fragments.keys():
            state = self.get_fragment_state(entity, frag_id)
            if state:
                arch = getattr(entity, "archaeology", None)
                collected = frag_id in getattr(arch, "collected_fragments", []) if arch else False
                state["collected"] = collected
                results.append(state)
        return results

    def get_archive_history(self, entity: Entity) -> list[dict[str, Any]]:
        """解読アーカイブ（収集済み一覧）を取得 (Step 39, 40)"""
        arch = getattr(entity, "archaeology", None)
        if not arch:
            return []

        history = []
        for f_id in arch.collected_fragments:
            state = self.get_fragment_state(entity, f_id)
            if state:
                history.append(state)
        return history
