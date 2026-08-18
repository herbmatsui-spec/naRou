from __future__ import annotations
import os
import shutil
import gzip
import pickle
import hashlib
from typing import Any, Tuple, Optional, Dict
from exceptions import SaveDataCorruptedError
from components import (
    TitleComponent, GuildFactionComponent, AchievementComponent,
    ReincarnationComponent, SkillTreeJobComponent, SkillFusionComponent,
    StorytellerComponent, ProceduralQuestComponent
)


class SaveSystem:
    """gzip+pickleによる完全なセーブシステム（ECSコンポーネント完全対応・SHA256チェックサム・自動バックアップ・世代管理）"""
    SAVE_PATH = "savegame.bin"
    CURRENT_VERSION = "2.0.0"
    SUPPORTED_VERSIONS = {"1.0.0", "1.1.0", "1.2.0", "2.0.0"}
    MAX_BACKUPS = 3

    # 後方互換性用フィールド定義 (旧セーブデータ復元および静的検証用)
    DEFAULT_FIELD_FACTORIES = {
        # リスト型
        'titles': list, 'title_notifications': list, 'pets': list,
        'pet_fusion_history': list, 'achievements': list, 'unique_items_obtained': list,
        'special_items_combo': list, 'achievement_notifications': list,
        'legacy_skills': list, 'unlocked_reincarnation_dungeons': list,
        'collected_fragments': list, 'awakened_skills': list, 'equipped_skills': list,
        'inheritable_skills': list, 'story_choices_made': list, 'memory_fragments': list,
        'active_world_events': list, 'completed_storylines': list,
        'available_storylines': list, 'story_notifications': list,
        'previous_jobs': list, 'mastered_jobs': list, 'mastered_exclusive_skills': list,
        'inherited_skills': list, 'completed_faction_events': list, 'ranking_titles': list,
        'cycle_modifiers': list, 'legacy_records': list,
        # 集合型
        'dungeon_floors_visited': set, 'completed_tutorials': set,
        # None/文字列
        'equipped_title': lambda: None, 'current_choice_prompt': lambda: None,
        'pending_tutorial_popup': lambda: None,
        'world_state_version': lambda: "1.0", 'last_festival_check': lambda: "",
        'guild_id': lambda: None, 'guild_role': lambda: None, 'guild_rank': lambda: "none",
        'job': lambda: "novice", 'save_version': lambda: "2.0.0",
        # 辞書型
        'kill_counts': dict, 'craft_counts': dict, 'achievement_progress': dict,
        'achievement_timers': dict, 'monster_killed_types': dict, 'permanent_bonuses': dict,
        'meta_progression': dict, 'favor': dict, 'inheritance_selection': dict,
        'challenge_progress': dict, 'skill_fusion_materials': dict, 'skill_evolution': dict,
        'skill_traits': dict, 'skill_specialization': dict, 'fusion_chain_progress': dict,
        'skill_archive_progress': dict, 'story_flags': dict, 'story_variables': dict,
        'player_legacy': dict, 'character_relationships': dict, 'ending_progress': dict,
        'skill_tree_progress': dict, 'faction_reputation': dict, 'guild_quest_progress': dict,
        'excavated_sites': list, 'collected_fragments': list, 'decoded_fragments': list,
        'owned_keys': list, 'reached_truths': list, 'leaned_endings': dict, 'interpretation_notes': dict,
        'decoder_hints_seen': list,
        # 数値型
        'karma_law_chaos': int, 'karma_good_evil': int, 'reincarnation_count': int,
        'max_dungeon_depth': int, 'near_death_count': int, 'total_turns': int, 'gold': int,
        'social_points': int, 'weekly_play_time': int, 'total_level_earned': int,
        'play_time_seconds': int, 'friend_helps': int, 'skill_points': int,
        'total_skill_points_earned': int, 'job_level': lambda: 1, 'job_exp': int,
        'guild_contribution': int
    }

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
        if not player:
            return

        # ECSコンポーネントコンテナの存在を確認
        if not hasattr(player, 'components') or not isinstance(player.components, dict):
            player.components = {}

        # 各コンポーネントの初期化/補完
        for comp_cls in [TitleComponent, GuildFactionComponent, AchievementComponent,
                         ReincarnationComponent, SkillTreeJobComponent, SkillFusionComponent,
                         StorytellerComponent, ProceduralQuestComponent]:
            if comp_cls not in player.components:
                player.components[comp_cls] = comp_cls()

        # 旧属性へのフォールバック担保
        for field_name, factory in cls.DEFAULT_FIELD_FACTORIES.items():
            if not hasattr(player, field_name):
                setattr(player, field_name, factory())

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

            # [32 bytes SHA256] + [compressed gzip payload]
            with open(cls.SAVE_PATH, "wb") as f:
                f.write(checksum + compressed)

            return f"セーブ完了！ ({len(compressed)} bytes, チェックサム検証済, 圧縮率{100 - int(len(compressed)/len(pickled)*100)}%)"
        except Exception as e:
            return f"セーブ失敗: {e}"

    @classmethod
    def load(cls, allow_backup_recovery: bool = True) -> Tuple[Optional[Any], str]:
        """チェックサム検証 + バージョン互換性検証 + バックアップ自動リカバリ (Step 4.1, 4.2, 4.3)"""
        if not os.path.exists(cls.SAVE_PATH):
            return None, "セーブデータが見つかりません。"
        
        try:
            with open(cls.SAVE_PATH, "rb") as f:
                data = f.read()

            if len(data) < 32:
                raise SaveDataCorruptedError("セーブデータが破損しています（サイズ不正）。")

            checksum = data[:32]
            payload = data[32:]

            # チェックサム検証
            expected_checksum = hashlib.sha256(payload).digest()
            if checksum != expected_checksum:
                # 従来形式 (チェックサムなし) との互換フォールバック
                try:
                    loaded_engine = pickle.loads(gzip.decompress(data))
                except Exception:
                    raise SaveDataCorruptedError("セーブデータのチェックサムが一致しません（データ改ざんまたは破損）。")
            else:
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
        migrated_data = MigrationManager.migrate(data)

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


class MigrationManager:
    """セーブデータバージョン移行マネージャー (Step 29, 30, 31)"""
    @classmethod
    def migrate(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        version = data.get("save_version", "1.0.0")
        if version == "1.0.0":
            data = cls.migrate_v1_to_v2(data)
        return data

    @classmethod
    def migrate_v1_to_v2(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """v1.0.0 -> v2.0.0 スキーマ移行 (Step 30)"""
        data["save_version"] = "2.0.0"
        if "player" in data and data["player"]:
            p = data["player"]
            if "components" not in p:
                p["components"] = {}
        return data

