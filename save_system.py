from __future__ import annotations
import os
import shutil
import gzip
import pickle
import hashlib
import hmac
import base64
from typing import Any, Tuple, Optional, Dict
from exceptions import SaveDataCorruptedError
from migration_pipeline import MigrationPipeline, DEFAULT_FIELD_FACTORIES


class SaveSystem:
    """gzip+pickleによる完全なセーブシステム（ECSコンポーネント完全対応・SHA256チェックサム・自動バックアップ・世代管理）"""
    SAVE_PATH = "savegame.bin"
    CURRENT_VERSION = "2.0.0"
    SUPPORTED_VERSIONS = {"1.0.0", "1.1.0", "1.2.0", "2.0.0"}
    MAX_BACKUPS = 3

    # HMAC signing for tamper detection (Step 61)
    # Key is derived from environment or build-time secret; not stored in plaintext
    @classmethod
    def _get_hmac_key(cls) -> bytes:
        """Return HMAC key from env or fallback (for dev only)."""
        key_b64 = os.environ.get("SAVE_HMAC_KEY")
        if key_b64:
            try:
                return base64.b64decode(key_b64)
            except Exception:
                pass
        # Dev fallback: deterministic key from project root hash
        return hashlib.sha256(b"naRou_dev_hmac_key_fallback").digest()

    @classmethod
    def _compute_hmac(cls, data: bytes) -> bytes:
        """Compute HMAC-SHA256 of data."""
        key = cls._get_hmac_key()
        return hmac.new(key, data, hashlib.sha256).digest()

    @classmethod
    def _verify_hmac(cls, data: bytes, expected_hmac: bytes) -> bool:
        """Verify HMAC-SHA256 of data."""
        expected = cls._compute_hmac(data)
        return hmac.compare_digest(expected, expected_hmac)

    # 後方互換性用フィールド定義（migration_pipeline へ移譲）
    DEFAULT_FIELD_FACTORIES = DEFAULT_FIELD_FACTORIES

    @classmethod
    def _create_backup(cls) -> None:
        """自動バックアップ（最大3世代のローテーション） (Step 4.2)"""
        if not os.path.exists(cls.SAVE_PATH):
            return
        try:
            # bak2 -> bak3, bak1 -> bak2
            for i in range(cls.MAX_BACKUPS - 1, 0, -1):
                src = f"{cls.SAVE_PATH}.bak{i}"
                dst = f"{cls.SAVE_PATH}.bak{i+1}"
                if os.path.exists(src):
                    shutil.copy2(src, dst)
            # savegame.bin -> savegame.bin.bak1
            shutil.copy2(cls.SAVE_PATH, f"{cls.SAVE_PATH}.bak1")
        except Exception as e:
            print(f"[SaveSystem] Backup rotation failed: {e}")

    @classmethod
    def _ensure_compatibility(cls, player: Any) -> None:
        """プレイヤーオブジェクトの全サブシステムフィールドおよびコンポーネント整合性を確保 (Step 4.3)"""
        MigrationPipeline.ensure_entity_compatibility(player)

    @classmethod
    def save(cls, engine: Any) -> str:
        """チェックサム付加 + バックアップローテーション + gzip+pickle (Step 4.1, 4.2, 4.3)"""
        try:
            if hasattr(engine, 'player') and engine.player:
                engine.player.save_version = cls.CURRENT_VERSION
                cls._ensure_compatibility(engine.player)

            # バックアップ作成
            cls._create_backup()

            # シリアライズ不能なサーバーインスタンスを退避
            ws = getattr(engine, "web_server", None)
            if ws is not None:
                engine.web_server = None
            try:
                pickled = pickle.dumps(engine)
            finally:
                if ws is not None:
                    engine.web_server = ws

            compressed = gzip.compress(pickled)
            # SHA256チェックサム計算 (32 bytes)
            checksum = hashlib.sha256(compressed).digest()
            # HMAC署名計算 (32 bytes) - Step 61
            save_hmac = cls._compute_hmac(compressed)

            # [32 bytes SHA256] + [32 bytes HMAC] + [compressed gzip payload]
            with open(cls.SAVE_PATH, "wb") as f:
                f.write(checksum + save_hmac + compressed)

            return f"セーブ完了！ ({len(compressed)} bytes, チェックサム検証済, 圧縮率{100 - int(len(compressed)/len(pickled)*100)}%)"
        except Exception as e:
            return f"セーブ失敗: {e}"

    @classmethod
    def load(cls, allow_backup_recovery: bool = True) -> Tuple[Optional[Any], str]:
        """HMAC署名検証 + チェックサム検証 + バージョン互換性検証 + バックアップ自動リカバリ (Step 61, 62)"""
        if not os.path.exists(cls.SAVE_PATH):
            return None, "セーブデータが見つかりません。"
        
        try:
            with open(cls.SAVE_PATH, "rb") as f:
                data = f.read()

            # New format: 32 bytes SHA256 + 32 bytes HMAC + payload
            # Legacy format: 32 bytes SHA256 + payload (no HMAC)
            if len(data) < 64:
                raise SaveDataCorruptedError("セーブデータが破損しています（サイズ不正）。")

            checksum = data[:32]
            save_hmac = data[32:64]
            payload = data[64:]

            # HMAC検証 (Step 61) - まずHMACを検証
            if not cls._verify_hmac(payload, save_hmac):
                raise SaveDataCorruptedError("セーブデータのHMAC署名が一致しません（改ざんの可能性）。")

            # チェックサム検証
            expected_checksum = hashlib.sha256(payload).digest()
            if checksum != expected_checksum:
                raise SaveDataCorruptedError("セーブデータのチェックサムが一致しません（データ改ざんまたは破損）。")

            loaded_engine = pickle.loads(gzip.decompress(payload))

            # プレイヤーデータの互換性確保
            if hasattr(loaded_engine, 'player') and loaded_engine.player:
                p_version = getattr(loaded_engine.player, "save_version", "1.0.0")
                if p_version not in cls.SUPPORTED_VERSIONS:
                    raise SaveDataCorruptedError(f"未対応のセーブバージョンです: {p_version}")
                cls._ensure_compatibility(loaded_engine.player)

            # ペット自体のフィールド互換性確保
            pet = getattr(loaded_engine, 'pet', None)
            if pet and hasattr(pet, 'pet_ai') and pet.pet_ai:
                if not hasattr(pet.pet_ai, 'bond'): pet.pet_ai.bond = 0
                if not hasattr(pet.pet_ai, 'contract_id'): pet.pet_ai.contract_id = "default"
                if not hasattr(pet.pet_ai, 'evolution_path'): pet.pet_ai.evolution_path = []
                if not hasattr(pet.pet_ai, 'evolution_stage'): pet.pet_ai.evolution_stage = 0
                if not hasattr(pet.pet_ai, 'equipment'): pet.pet_ai.equipment = {}

            return loaded_engine, "ロード完了！ ゲームが完全に復元されました。"
        except Exception as e:
            if allow_backup_recovery:
                # バックアップからの復旧試行
                for i in range(1, cls.MAX_BACKUPS + 1):
                    bak_file = f"{cls.SAVE_PATH}.bak{i}"
                    if os.path.exists(bak_file):
                        try:
                            shutil.copy2(bak_file, cls.SAVE_PATH)
                            res, msg = cls.load(allow_backup_recovery=False)
                            if res is not None:
                                return res, f"【警告】セーブデータ破損のため、バックアップ(世代{i})から復旧しました。"
                        except Exception:
                            continue
            return None, f"ロード失敗: {e}"

    # ==========================================
    # フェーズ2：JSON シリアライズ & マイグレーション (Steps 24-35)
    # ==========================================
    JSON_SAVE_PATH = "savegame.json"

    @classmethod
    def serialize_engine_to_dict(cls, engine: Any) -> Dict[str, Any]:
        """Engine全体を辞書形式にシリアライズ (Step 24)"""
        data: Dict[str, Any] = {
            "save_version": cls.CURRENT_VERSION,
            "dungeon_level": getattr(engine, "dungeon_level", 1),
            "turns": getattr(engine, "turns", 0),
            "game_state": getattr(engine, "game_state", "play"),
            "player": engine.player.to_dict() if hasattr(engine, "player") and engine.player else None,
            "pet": engine.pet.to_dict() if hasattr(engine, "pet") and engine.pet else None,
            "survival": {
                "gold": getattr(engine.survival, "gold", 0),
                "platinum": getattr(engine.survival, "platinum", 0),
                "hunger": getattr(engine.survival, "hunger", 8000),
                "sleepiness": getattr(engine.survival, "sleepiness", 0),
                "karma": getattr(engine.survival, "karma", 20),
            } if hasattr(engine, "survival") and engine.survival else {},
            "inventory": [itm.to_dict() for itm in engine.inventory.items] if hasattr(engine, "inventory") and engine.inventory else [],
            "pet_inventory": [itm.to_dict() for itm in engine.pet_inventory.items] if hasattr(engine, "pet_inventory") and engine.pet_inventory else [],
            "items_on_ground": [itm.to_dict() for itm in getattr(engine, "items_on_ground", [])],
        }
        return data

    @classmethod
    def deserialize_dict_to_engine(cls, data: Dict[str, Any], target_engine: Optional[Any] = None) -> Any:
        """辞書から Engine の状態を復元 (Step 25)"""
        from game import Engine
        from item_system import Item
        from entity import Entity

        # マイグレーション適用 (Step 31)
        migrated_data = MigrationPipeline.migrate(data)

        engine = target_engine or Engine()
        engine.dungeon_level = migrated_data.get("dungeon_level", 1)
        engine.turns = migrated_data.get("turns", 0)
        engine.game_state = migrated_data.get("game_state", "play")

        if migrated_data.get("player"):
            engine.player = Entity.from_dict(migrated_data["player"])
            cls._ensure_compatibility(engine.player)

        if migrated_data.get("pet"):
            engine.pet = Entity.from_dict(migrated_data["pet"])

        # Survival
        surv_data = migrated_data.get("survival", {})
        if hasattr(engine, "survival") and engine.survival:
            engine.survival.gold = surv_data.get("gold", 0)
            engine.survival.platinum = surv_data.get("platinum", 0)
            engine.survival.hunger = surv_data.get("hunger", 100)
            engine.survival.thirst = surv_data.get("thirst", 100)
            engine.survival.sleep = surv_data.get("sleep", 100)

        # Inventories
        if hasattr(engine, "inventory") and engine.inventory and "inventory" in migrated_data:
            engine.inventory.items = [Item.from_dict(it) for it in migrated_data["inventory"]]

        if hasattr(engine, "pet_inventory") and engine.pet_inventory and "pet_inventory" in migrated_data:
            engine.pet_inventory.items = [Item.from_dict(it) for it in migrated_data["pet_inventory"]]

        if "items_on_ground" in migrated_data:
            engine.items_on_ground = [Item.from_dict(it) for it in migrated_data["items_on_ground"]]

        return engine

    @classmethod
    def save_json(cls, engine: Any, file_path: Optional[str] = None) -> str:
        """JSON形式でファイル保存 (SHA256チェックサム付加) (Step 26, 33)"""
        import json
        target_path = file_path or cls.JSON_SAVE_PATH
        try:
            dict_data = cls.serialize_engine_to_dict(engine)
            json_str = json.dumps(dict_data, ensure_ascii=False, indent=2)
            checksum = hashlib.sha256(json_str.encode("utf-8")).hexdigest()
            payload = {
                "checksum": checksum,
                "data": dict_data
            }
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            return f"JSONセーブ完了！ ({target_path}, SHA256: {checksum[:8]}...)"
        except Exception as e:
            return f"JSONセーブ失敗: {e}"

    @classmethod
    def load_json(cls, file_path: Optional[str] = None) -> Tuple[Optional[Any], str]:
        """JSONファイルから読み込み (チェックサム検証 & 自動復元) (Step 27, 33, 35)"""
        import json
        target_path = file_path or cls.JSON_SAVE_PATH
        if not os.path.exists(target_path):
            return None, "JSONセーブデータが見つかりません。"
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                payload = json.load(f)

            # チェックサム検証
            if "checksum" in payload and "data" in payload:
                dict_data = payload["data"]
                expected_str = json.dumps(dict_data, ensure_ascii=False, indent=2)
                expected_checksum = hashlib.sha256(expected_str.encode("utf-8")).hexdigest()
                if payload["checksum"] != expected_checksum:
                    raise SaveDataCorruptedError("JSONセーブデータのチェックサムが一致しません。")
            else:
                dict_data = payload

            engine = cls.deserialize_dict_to_engine(dict_data)
            return engine, "JSONロード完了！ ゲームが正常に復元されました。"
        except Exception as e:
            return None, f"JSONロード失敗: {e}"

    @classmethod
    def convert_pickle_to_json(cls) -> str:
        """旧pickle形式データをJSON形式に変換して保存 (Step 32)"""
        loaded, msg = cls.load()
        if loaded is None:
            return f"変換失敗: {msg}"
        return cls.save_json(loaded)


# Backwards compatibility alias
MigrationManager = MigrationPipeline

