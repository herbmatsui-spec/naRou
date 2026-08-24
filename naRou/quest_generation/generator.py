"""Procedural quest generator engine (Steps 19-33)."""
from __future__ import annotations

import hashlib
import logging
import random
from typing import TYPE_CHECKING, Any

from .models import (
    DifficultyTier,
    GeneratedQuest,
    NPCQuestTheme,
    QuestArchetype,
    QuestObjectiveSpec,
    RewardTable,
    StageSetting,
)
from .registry import REGISTRY, QuestGenerationRegistry

if TYPE_CHECKING:
    from naRou.dungeon_quest_feedback import DungeonGenerationFeedback
    from naRou.ecs.entity import Entity

logger = logging.getLogger(__name__)


class ProceduralQuestGenerator:
    """プロシージャルクエスト生成器 (Steps 19-33)"""

    def __init__(self, registry: QuestGenerationRegistry | None = None):
        self.registry = registry or REGISTRY
        self._pet_quest_templates: dict[str, Any] = {}

    # Step 19: シード決定論ヘルパー
    def _seeded_rng(self, *keys: Any) -> random.Random:
        """(seed, *keys) から決定論的乱数を生成 (Step 19)"""
        base = "|".join(str(k) for k in keys)
        digest = hashlib.sha256(base.encode("utf-8")).hexdigest()
        return random.Random(int(digest[:16], 16))

    # Step 20: コア合成
    def _compose(
        self,
        source_type: str,
        archetype: QuestArchetype,
        difficulty: DifficultyTier,
        reward: RewardTable,
        setting: StageSetting,
        seed: int,
        npc_id: str | None = None,
    ) -> GeneratedQuest:
        """アーキタイプ × 難易度 × 報酬 × 舞台 を合成 (Step 20)"""
        rng = self._seeded_rng(
            source_type,
            archetype.id,
            difficulty.id,
            reward.id,
            setting.id,
            npc_id or "",
            seed,
        )

        # Step 21: タイトル/説明文の自動生成
        enemy = rng.choice(setting.enemy_pool) if setting.enemy_pool else "monster"
        item = rng.choice(reward.item_pool) if reward.item_pool else "material"
        boss = setting.enemy_pool[-1] if setting.enemy_pool else "boss"
        # Step 11: 日本語表示名への差し替え（target_id は照合用に英語IDのまま）
        enemy_disp = self.registry.get_display_name("enemy", enemy)
        item_disp = self.registry.get_display_name("item", item)
        boss_disp = self.registry.get_display_name("enemy", boss)
        setting_disp = self.registry.get_display_name("stage", setting.id) or setting.name

        # Step 22: 目的オブジェクト自動生成（難易度補正）
        required_count = self._compute_required_count(archetype, difficulty, setting, rng)
        objective = self._build_objective(
            archetype,
            enemy,
            item,
            boss,
            required_count,
            enemy_disp,
            item_disp,
            boss_disp,
        )

        # Step 23: 報酬合成
        final_reward = self._compose_reward(difficulty, reward, rng)

        title = archetype.title_template.format(
            setting=setting_disp,
            archetype=archetype.name,
            enemy=enemy_disp,
            item=item_disp,
            boss=boss_disp,
            required_count=required_count,
        )
        desc = archetype.desc_template.format(
            setting=setting_disp,
            archetype=archetype.name,
            enemy=enemy_disp,
            item=item_disp,
            boss=boss_disp,
            required_count=required_count,
            hazard=setting.hazard,
            flavor=setting.flavor,
        )

        recommended_level = int((difficulty.level_range[0] + difficulty.level_range[1]) / 2)

        return GeneratedQuest(
            quest_id=f"gen_{source_type}_{seed & 0xFFFFFFFF:x}_{archetype.id}_{difficulty.id}_{reward.id}_{setting.id}",
            title=title,
            description=desc,
            source_type=source_type,
            archetype_id=archetype.id,
            difficulty_id=difficulty.id,
            reward_id=reward.id,
            setting_id=setting.id,
            npc_id=npc_id,
            seed=seed,
            recommended_level=recommended_level,
            objectives=[objective],
            reward=final_reward,
            expires=0,
        )

    def _compute_required_count(
        self,
        archetype: QuestArchetype,
        difficulty: DifficultyTier,
        setting: StageSetting,
        rng: random.Random,
    ) -> int:
        base = 4 * archetype.base_complexity
        val = base * difficulty.enemy_multiplier * difficulty.objective_complexity
        if archetype.objective_type == "explore":
            val *= setting.depth_modifier
        val *= setting.environmental_modifier
        count = max(1, round(val * rng.uniform(0.9, 1.1)))
        return count

    def _build_objective(
        self,
        archetype: QuestArchetype,
        enemy: str,
        item: str,
        boss: str,
        required_count: int,
        enemy_disp: str = "",
        item_disp: str = "",
        boss_disp: str = "",
    ) -> QuestObjectiveSpec:
        # target_id は照合用に英語IDのまま保持し、表示文のみ日本語化
        e_disp = enemy_disp or enemy
        i_disp = item_disp or item
        b_disp = boss_disp or boss
        otype = archetype.objective_type
        if otype == "kill":
            target_id = enemy
            desc = f"{e_disp}を{required_count}体討伐"
            if archetype.id == "boss_hunt":
                target_id = boss
                desc = f"{b_disp}を討ち取れ"
                required_count = 1
        elif otype == "collect":
            target_id = item
            desc = f"{i_disp}を{required_count}個採取"
        elif otype == "explore":
            target_id = "depth"
            desc = f"{required_count}階層まで踏破"
        elif otype == "escort":
            target_id = "client"
            desc = f"依頼主を{required_count}回の遭遇から守護"
        elif otype == "rescue":
            target_id = "captive"
            desc = f"囚われし者を{required_count}名救出"
        elif otype == "delivery":
            target_id = item
            desc = f"{i_disp}を届先へ運ぶ"
            required_count = 1
        else:
            target_id = "target"
            desc = "任務を遂行"
        return QuestObjectiveSpec(
            objective_id=f"{archetype.id}_obj",
            description=desc,
            target_type=otype,
            target_id=target_id,
            required_count=required_count,
        )

    def _compose_reward(
        self, difficulty: DifficultyTier, reward: RewardTable, rng: random.Random
    ) -> dict[str, Any]:
        gold = int(
            rng.randint(reward.gold_range[0], reward.gold_range[1]) * difficulty.enemy_multiplier
        )
        exp = int(
            rng.randint(reward.exp_range[0], reward.exp_range[1]) * difficulty.objective_complexity
        )
        items = []
        if reward.item_pool and rng.random() < 0.85:
            items.append(rng.choice(reward.item_pool))
        bonus = dict(reward.bonus)
        return {"gold": gold, "exp": exp, "items": items, "bonus": bonus}

    def generate_pet_quest(
        self, player: Entity | None = None, seed: int | None = None
    ) -> GeneratedQuest | None:
        """ペット関連クエストを生成 (Step 29-30)"""
        if player is None or not self._pet_quest_templates:
            return None
        from naRou.pet_quest_analyzer import analyze_active_pet

        pet_profile = analyze_active_pet(player)
        if pet_profile is None:
            return None
        # ペットの種族と契約タイプにマッチするテンプレートを検索
        matched_templates = []
        for template in self._pet_quest_templates:
            # ワイルドカード "*" をサポート
            species_match = (
                template.get("pet_species") == pet_profile.species
                or template.get("pet_species") == "*"
            )
            contract_match = (
                template.get("pet_contract_type") == pet_profile.contract_type
                or template.get("pet_contract_type") == "*"
            )
            if species_match and contract_match:
                matched_templates.append(template)
        if not matched_templates:
            return None
        # ランダムにテンプレートを選択
        if seed is None:
            seed = random.randint(0, 10**9)
        rng = random.Random(seed)
        template = rng.choice(matched_templates)
        # テンプレートからクエストを生成
        # ここでは簡易的に、テンプレートのフィールドを使用してクエストを生成する
        # 実際には、アーキタイプ、難易度、報酬、ステージなどを決定する必要がある
        # 簡易実装として、デフォルトのアーキタイプなどを使用する
        # ここで、探索タイプのクエストを生成する例を示す
        objective_type = template.get("objective_type", "explore")
        # アーキタイプを目的タイプから見つける
        archetype_id = None
        for aid, archetype in self._archetypes.items():
            if archetype.objective_type == objective_type:
                archetype_id = aid
                break
        if archetype_id is None:
            archetype_id = "explore"  # デフォルト
        archetype = self.get_archetype(archetype_id)
        if archetype is None:
            return None
        # 難易度をプレイヤーレベルに基づいて選択
        player_level = getattr(player, "level", 1)
        difficulty = self._pick_difficulty_for_level(player_level, rng=rng)
        if difficulty is None:
            difficulty = self.get_difficulty("normal")
        if difficulty is None:
            return None
        # 報酬をデフォルトから選択
        reward_id = next(iter(self._rewards.keys())) if self._rewards else "gold"
        reward = self.get_reward(reward_id)
        if reward is None:
            return None
        # 舞台をデフォルトから選択
        setting_id = next(iter(self._settings.keys())) if self._settings else "forest"
        setting = self.get_setting(setting_id)
        if setting is None:
            return None
        # NPC IDはなし
        npc_id = None
        # クエストを合成
        return self._compose("pet_related", archetype, difficulty, reward, setting, seed, npc_id)

    # ---- 共通: 難易度帯の選択 ----
    def _pick_difficulty_for_level(
        self,
        player_level: int,
        min_id: str | None = None,
        max_id: str | None = None,
        rng: random.Random | None = None,
    ) -> DifficultyTier:
        order = self.registry.difficulty_order()
        if min_id:
            while order and order[0] != min_id:
                order.pop(0)
        if max_id and max_id in order:
            idx = order.index(max_id)
            order = order[: idx + 1]
        cand: list[DifficultyTier] = []
        for did in order:
            t = self.registry.get_difficulty(did)
            if t:
                cand.append(t)
        if not cand:
            return self.registry.get_difficulty("normal") or DifficultyTier()
        for t in cand:
            if t.level_range[0] <= player_level <= t.level_range[1]:
                return t
        below = [t for t in cand if t.level_range[1] < player_level]
        if below:
            return below[-1]
        return cand[0]

    # ---- Step 24, 25: 依頼ボード ----
    def generate_board_quest(
        self,
        player: Entity | None = None,
        seed: int | None = None,
        archetype_id: str | None = None,
        difficulty_id: str | None = None,
    ) -> GeneratedQuest:
        """依頼ボード用クエスト1件を生成 (Step 24)"""
        if seed is None:
            seed = random.randint(0, 10**9)
        rng = self._seeded_rng("board", seed)

        cfg = self.registry.board_config()
        weights = cfg.get("type_weights", {})
        if archetype_id and archetype_id in self.registry.all_archetypes():
            arch = self.registry.get_archetype(archetype_id)
        else:
            arch = self._weighted_choice(list(self.registry.all_archetypes().items()), weights, rng)
        if arch is None:
            arch = QuestArchetype()

        player_level = int(getattr(player, "level", 1)) if player else 1
        if difficulty_id and difficulty_id in self.registry.all_difficulties():
            diff = self.registry.get_difficulty(difficulty_id)
        else:
            diff = self._pick_difficulty_for_level(
                player_level, cfg.get("min_difficulty"), cfg.get("max_difficulty"), rng
            )
        if diff is None:
            diff = DifficultyTier()

        reward = self._pick_reward_for_difficulty(diff, rng)
        setting = (
            rng.choice(list(self.registry.all_settings().values()))
            if self.registry.all_settings()
            else StageSetting()
        )
        return self._compose("board", arch, diff, reward, setting, seed)

    def generate_board_pool(
        self, player: Entity | None = None, count: int | None = None
    ) -> list[GeneratedQuest]:
        """依頼ボード用クエスト複数生成＋重複排除 (Step 25)"""
        cfg = self.registry.board_config()
        max_active = count or int(cfg.get("max_active", 8))
        quests: list[GeneratedQuest] = []
        seen_keys = set()
        attempts = 0
        # まず通常のボードクエストを生成するループ
        while len(quests) < max_active and attempts < max_active * 20:
            attempts += 1
            q = self.generate_board_quest(player)
            # 報酬ティアのみ異なる同一見た目クエストを排除し、掲示板を視覚的に多様に保つ
            key = (q.archetype_id, q.difficulty_id, q.setting_id, q.title)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            quests.append(q)
        # その後、ペット関連クエストを追加しようとする
        pet_attempts = 0
        while len(quests) < max_active and pet_attempts < max_active * 5:
            pet_attempts += 1
            pet_q = self.generate_pet_quest(player)
            if pet_q is None:
                continue
            key = (
                pet_q.archetype_id,
                pet_q.difficulty_id,
                pet_q.setting_id,
                pet_q.title,
            )
            if key in seen_keys:
                continue
            seen_keys.add(key)
            quests.append(pet_q)
        return quests

    # ---- Step 28-30: ランダムダンジョン探索 ----
    def generate_dungeon_quest(
        self,
        player: Entity | None = None,
        seed: int | None = None,
        theme_id: str | None = None,
    ) -> GeneratedQuest:
        """ランダムダンジョン探索クエストを生成 (Step 28)"""
        if seed is None:
            seed = random.randint(0, 10**9)
        rng = self._seeded_rng("dungeon", seed)

        theme = None
        try:
            from naRou.procedural_dungeon_generator import REGISTRY as DT_REG

            if theme_id:
                theme = DT_REG.get(theme_id)
            elif player is not None:
                from naRou.procedural_dungeon_generator import ProceduralDungeonGenerator

                gen = ProceduralDungeonGenerator(DT_REG)
                theme = gen.select_theme_by_story(player)
        except Exception as e:
            logger.warning("Failed to select dungeon theme by story: %s", e)
            theme = None

        setting = None
        if theme is not None:
            setting = self.registry.get_setting(theme.theme_id) or self.registry.get_setting("cave")
        if setting is None:
            setting = (
                rng.choice(list(self.registry.all_settings().values()))
                if self.registry.all_settings()
                else StageSetting()
            )

        # ダンジョン目的: 探索 または ボス討伐 (Step 29)
        arch = (
            self.registry.get_archetype("explore")
            or self.registry.get_archetype("boss_hunt")
            or QuestArchetype()
        )
        if rng.random() < 0.4:
            arch = self.registry.get_archetype("boss_hunt") or arch

        player_level = int(getattr(player, "level", 1)) if player else 1
        diff = self._pick_difficulty_for_level(player_level, None, None, rng)
        reward = self._pick_reward_for_difficulty(diff, rng)
        # Step 30: 舞台×テーマ合成
        return self._compose("dungeon", arch, diff, reward, setting, seed)

    # ---- Step 18-21: ダンジョン同期クエスト生成 (Phase 5) ----
    def generate_dungeon_synced_quest(
        self,
        spec_id: str,
        quest_id: str,
        title: str,
        description: str,
        player: Entity | None = None,
        seed: int | None = None,
        objective_mapping: dict[str, str] | None = None,
    ) -> GeneratedQuest:
        """ダンジョン同期クエストを生成 (Phase 5 Step 21)

        1. DungeonSpec を読み込み
        2. generate_from_spec でダンジョン生成
        3. フィードバックで目的を同期
        4. GeneratedQuest を返す
        """
        if seed is None:
            seed = random.randint(0, 10**9)
        rng = self._seeded_rng("dungeon_synced", spec_id, quest_id, seed)

        # 仕様読み込み
        spec = self._load_dungeon_spec(spec_id)
        if spec is None:
            # フォールバック: 通常のダンジョンクエスト生成
            return self.generate_dungeon_quest(player, seed)

        # 目的マッピング（デフォルト）
        if objective_mapping is None:
            objective_mapping = {
                "reach_boss": "boss_room_coords",
                "explore_floors": "generated_floors",
                "count_rooms": "total_rooms",
                "find_entrance": "entrance_coords",
                "defeat_boss": "boss_room_id",
            }

        # パイプライン実行
        try:
            from naRou.dungeon_quest_feedback import DungeonQuestPipeline
            from naRou.procedural_dungeon_generator import REGISTRY as DT_REG
            from naRou.procedural_dungeon_generator import ProceduralDungeonGenerator

            generator = ProceduralDungeonGenerator(DT_REG)
            pipeline = DungeonQuestPipeline(generator)
            result = pipeline.generate_synced_quest_dungeon(
                spec_id, quest_id, player, objective_mapping
            )
        except Exception as e:
            logger.warning(
                "Failed to generate synced quest dungeon for spec %s: %s. Falling back to standard dungeon quest.",
                spec_id,
                e,
            )
            return self.generate_dungeon_quest(player, seed)

        generated = result["generated"]
        feedback: DungeonGenerationFeedback = result["feedback"]

        # アーキタイプ選択（ボス討伐または探索）
        arch = self.registry.get_archetype("explore") or QuestArchetype()
        if rng.random() < 0.4:
            arch = self.registry.get_archetype("boss_hunt") or arch

        # 難易度・報酬・舞台
        player_level = int(getattr(player, "level", 1)) if player else 1
        diff = self._pick_difficulty_for_level(player_level, None, None, rng)
        reward = self._pick_reward_for_difficulty(diff, rng)

        # 舞台設定（ダンジョンテーマに合わせる）
        setting = None
        theme_id = (
            getattr(generated.get("theme"), "theme_id", "")
            if hasattr(generated.get("theme"), "theme_id")
            else generated.get("theme_id", "")
        )
        if theme_id:
            setting = self.registry.get_setting(theme_id) or self.registry.get_setting("cave")
        if setting is None:
            setting = (
                rng.choice(list(self.registry.all_settings().values()))
                if self.registry.all_settings()
                else StageSetting()
            )

        # クエスト合成
        quest = self._compose("dungeon_synced", arch, diff, reward, setting, seed)

        # クエスト情報を上書き
        quest.quest_id = quest_id
        quest.title = title
        quest.description = description
        quest.source_type = "dungeon_synced"

        # フィードバックに基づいて目的を更新
        if feedback and hasattr(feedback, "generated_floors"):
            # オブジェクトマッピングに基づいて目的の説明と必要数を更新
            for obj in quest.objectives:
                if obj.objective_id in objective_mapping:
                    mapping_key = objective_mapping[obj.objective_id]
                    if mapping_key == "generated_floors":
                        obj.required_count = feedback.generated_floors
                        obj.description = f"{feedback.generated_floors}階層まで探索"
                    elif mapping_key == "total_rooms":
                        obj.required_count = feedback.total_rooms
                        obj.description = f"{feedback.total_rooms}部屋を探索"
                    elif mapping_key == "boss_room_coords":
                        # ボス部屋座標は見つかったかどうか（0または1）
                        obj.required_count = 1 if feedback.boss_room_coords else 0
                        obj.description = "ボス部屋を見つける"
                    elif mapping_key == "boss_room_id":
                        obj.required_count = 1 if feedback.boss_room_id else 0
                        obj.description = "ボス部屋を特定"
                    elif mapping_key == "entrance_coords":
                        obj.required_count = 1 if feedback.entrance_coords else 0
                        obj.description = "入口を見つける"
                    elif mapping_key == "exit_coords":
                        obj.required_count = 1 if feedback.exit_coords else 0
                        obj.description = "出口を見つける"

        # フィードバック情報を報酬に追加（デバッグ用）
        quest.reward["dungeon_feedback"] = {
            "spec_id": spec.spec_id,
            "generated_floors": feedback.generated_floors,
            "total_rooms": feedback.total_rooms,
            "boss_room_found": feedback.boss_room_coords is not None,
        }

        return quest

    def _load_dungeon_spec(self, spec_id: str):
        """ダンジョン仕様読み込み（YAMLから）"""
        try:
            import os

            import yaml

            spec_path = "data/quest_dungeon_specs.yaml"
            if os.path.exists(spec_path):
                with open(spec_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                spec_data = data.get("dungeon_specs", {}).get(spec_id)
                if spec_data:
                    from naRou.quest_dungeon_spec import build_dungeon_spec_from_yaml

                    return build_dungeon_spec_from_yaml(spec_data)
        except Exception as e:
            logger.warning("Failed to load dungeon spec %s from yaml: %s", spec_id, e)
        return None

    def generate_npc_quest(
        self,
        npc_id: str,
        npc_type: str,
        player: Entity | None = None,
        seed: int | None = None,
    ) -> GeneratedQuest | None:
        """NPC個別クエストを生成 (Step 31)"""
        if seed is None:
            seed = random.randint(0, 10**9)
        rng = self._seeded_rng("npc", seed)

        theme = self.registry.get_npc_theme(npc_type)
        if theme is None:
            return None

        # Step 32: 友好度ゲート
        if player is not None and theme.relationship_gate > 0:
            rel_level = self._get_relationship_level(player, npc_id)
            if rel_level < theme.relationship_gate:
                return None

        pool = [self.registry.get_archetype(a) for a in theme.quest_pool]
        pool = [a for a in pool if a is not None]
        arch = (
            rng.choice(pool)
            if pool
            else (self.registry.get_archetype("delivery") or QuestArchetype())
        )

        player_level = int(getattr(player, "level", 1)) if player else 1
        diff = self._pick_difficulty_for_level(player_level, None, None, rng)
        reward = self._pick_reward_for_difficulty(diff, rng)

        # Step 33: 個別フレーバー付与
        setting = (
            rng.choice(list(self.registry.all_settings().values()))
            if self.registry.all_settings()
            else StageSetting()
        )
        quest = self._compose("npc", arch, diff, reward, setting, seed, npc_id=npc_id)
        # Apply NPC theme flavor
        if theme.flavor:
            formatted_flavor = theme.flavor.format(npc=npc_id)
            quest.description = formatted_flavor + " " + quest.description
        return quest

    # ---- Step 17-18: 連鎖クエスト（報酬カスケード） ----
    def generate_followup(
        self,
        parent: GeneratedQuest,
        player: Entity | None = None,
        seed: int | None = None,
    ) -> GeneratedQuest | None:
        """親クエストのフォローアップ（連鎖次世代）を生成 (Step 17)"""
        cfg = self.registry.chain_config()
        max_depth = int(cfg.get("max_depth", 5))
        if parent.depth + 1 > max_depth:
            return None  # Step 21: 深度上限で打ち切り
        if seed is None:
            seed = random.randint(0, 10**9)
        self._seeded_rng("chain", parent.chain_id or parent.quest_id, seed)

        # 難易度・報酬のエスカレーション (Step 17)
        diff_order = self.registry.difficulty_order()
        d_idx = diff_order.index(parent.difficulty_id) if parent.difficulty_id in diff_order else 0
        d_idx = min(len(diff_order) - 1, d_idx + int(cfg.get("difficulty_escalation", 1)))
        diff = self.registry.get_difficulty(diff_order[d_idx]) or DifficultyTier()

        r_order = list(self.registry.all_rewards().keys())
        r_idx = r_order.index(parent.reward_id) if parent.reward_id in r_order else 0
        r_idx = min(len(r_order) - 1, r_idx + int(cfg.get("reward_escalation", 1)))
        reward = self.registry.get_reward(r_order[r_idx]) or RewardTable()

        arch = self.registry.get_archetype(parent.archetype_id) or QuestArchetype()
        setting = self.registry.get_setting(parent.setting_id) or StageSetting()

        quest = self._compose(
            parent.source_type, arch, diff, reward, setting, seed, npc_id=parent.npc_id
        )
        depth = parent.depth + 1
        quest.chain_id = parent.chain_id or parent.quest_id
        quest.parent_id = parent.quest_id
        quest.depth = depth

        # Step 18: 報酬カスケード合成（階層累積乗算＋ボーナス加算）
        gm = float(cfg.get("gold_multiplier_per_depth", 1.5))
        em = float(cfg.get("exp_multiplier_per_depth", 1.4))
        quest.reward["gold"] = int(quest.reward.get("gold", 0) * (gm**depth))
        quest.reward["exp"] = int(quest.reward.get("exp", 0) * (em**depth))
        bonus = quest.reward.get("bonus", {}) or {}
        bonus["fame"] = bonus.get("fame", 0) + int(cfg.get("cascade_fame_per_depth", 2)) * depth
        bonus["relationship"] = (
            bonus.get("relationship", 0) + int(cfg.get("cascade_relationship_per_depth", 1)) * depth
        )
        bonus["meta"] = bonus.get("meta", 0) + int(cfg.get("cascade_meta_per_depth", 1)) * depth
        quest.reward["bonus"] = bonus

        # Step 22: 連鎖専用フレーバー
        if depth >= max_depth - 1:
            tag = "《終幕》"
        elif depth >= 2:
            tag = f"《第{depth}章》"
        else:
            tag = "《続編》"
        quest.title = tag + quest.title
        quest.description = tag + " " + quest.description
        return quest

    # ---- 補助 ----
    def _weighted_choice(
        self, items: list[tuple[str, Any]], weights: dict[str, int], rng: random.Random
    ) -> Any | None:
        if not items:
            return None
        w = [max(1, int(weights.get(k, 1))) for k, _ in items]
        chosen = rng.choices(items, weights=w, k=1)[0]
        return chosen[1]

    def _pick_reward_for_difficulty(self, diff: DifficultyTier, rng: random.Random) -> RewardTable:
        order = list(self.registry.all_rewards().values())
        if not order:
            return RewardTable()
        idx = int((diff.recommended_power**0.5) / 12 + rng.randint(0, 1))
        idx = max(0, min(len(order) - 1, idx))
        return order[idx]

    def _get_relationship_level(self, player: Entity, npc_id: str) -> int:
        try:
            from naRou.relationship_system import REGISTRY as REL_REG
            from naRou.relationship_system import RelationshipManager

            return RelationshipManager(REL_REG).get_relationship_level(player, npc_id)
        except Exception as e:
            logger.debug(
                "RelationshipManager unavailable, falling back to character_relationships: %s", e
            )
            rels = getattr(player, "character_relationships", {})
            return int((rels.get(npc_id, {}) or {}).get("trust", 0) // 30)
