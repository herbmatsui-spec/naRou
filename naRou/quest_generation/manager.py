"""Procedural quest manager (Steps 34-35)."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .generator import ProceduralQuestGenerator
from .models import GeneratedQuest, _get_enemy_name_map
from .registry import REGISTRY, QuestGenerationRegistry

if TYPE_CHECKING:
    from game import Engine
    from naRou.ecs.entity import Entity

logger = logging.getLogger(__name__)


def _norm_target(s: Any) -> str:
    """照合用正規化：小文字・空白排除"""
    return str(s).lower().replace(" ", "_").replace("　", "")


def _target_matches(quest_target: str, event_norm: str) -> bool:
    """生成クエストの目標(target_id)と実際のイベント対象を曖昧照合 (Step 34)"""
    if not quest_target or not event_norm:
        return False
    q = _norm_target(quest_target)
    if q == event_norm:
        return True
    if q in event_norm or event_norm in q:
        return True
    for key, variants in _get_enemy_name_map().items():
        norms = [v.lower().replace(" ", "_") for v in variants]
        q_in = q in norms
        e_in = event_norm in norms or key == event_norm
        if q_in and e_in:
            return True
    return False


class ProceduralQuestManager:
    """生成クエストの受諾・進捗・達成・報酬付与管理 (Steps 34-35)"""

    def __init__(self, generator: ProceduralQuestGenerator | None = None):
        self.generator = generator or ProceduralQuestGenerator(REGISTRY)

    def _comp(self, player: Entity):
        return player.procedural_quest

    # Step 26, 27: ボード管理
    def ensure_board(self, player: Entity, engine: Engine | None = None) -> list[GeneratedQuest]:
        comp = self._comp(player)
        if not comp.active_board:
            self.refresh_board(player, engine)
        return [GeneratedQuest.from_dict(d) for d in comp.active_board]

    def refresh_board(self, player: Entity, engine: Engine | None = None) -> list[GeneratedQuest]:
        """依頼ボードを再生成 (Step 26, 27)"""
        comp = self._comp(player)
        comp.board_seed = (comp.board_seed + 1) % (10**9)
        quests = self.generator.generate_board_pool(player)
        comp.active_board = [q.to_dict() for q in quests]
        if engine:
            engine.log(f"依頼ボードが更新された（{len(quests)}件）", (200, 220, 255))
        return quests

    def get_available_board(self, player: Entity) -> list[GeneratedQuest]:
        return self.ensure_board(player)

    def get_npc_quests(self, player: Entity, npc_id: str, npc_type: str) -> list[GeneratedQuest]:
        """NPCが提示可能な個別クエスト一覧 (Step 31)"""
        q = self.generator.generate_npc_quest(npc_id, npc_type, player)
        return [q] if q else []

    def accept_quest(self, player: Entity, quest_id: str) -> bool:
        comp = self._comp(player)
        for bd in comp.active_board:
            if bd.get("quest_id") == quest_id:
                comp.accepted_quests.append(bd)
                comp.active_board = [b for b in comp.active_board if b.get("quest_id") != quest_id]
                return True
        return False

    # Step 34: 進捗更新
    def update_progress(
        self,
        player: Entity,
        event_type: str,
        target_id: str,
        amount: int = 1,
        engine: Engine | None = None,
    ) -> list[str]:
        """イベントに基づき受諾済クエストの目的を進捗 (Step 34)"""
        comp = self._comp(player)
        logs: list[str] = []
        n_target = _norm_target(target_id)
        for qd in comp.accepted_quests:
            quest = GeneratedQuest.from_dict(qd)
            changed = False
            for obj in quest.objectives:
                if (obj.target_type == event_type and obj.current_count < obj.required_count) and (
                    obj.target_id == target_id or _target_matches(obj.target_id, n_target)
                ):
                    obj.current_count = min(obj.required_count, obj.current_count + amount)
                    changed = True
            if changed:
                qd.clear()
                qd.update(quest.to_dict())
                if quest.is_completed():
                    ok, msg, _ = self.complete_quest(player, quest.quest_id, engine)
                    if ok:
                        logs.append(msg)
        return logs

    # Step 34: 達成と報酬付与
    def complete_quest(
        self, player: Entity, quest_id: str, engine: Engine | None = None
    ) -> tuple[bool, str, dict[str, Any]]:
        comp = self._comp(player)
        target = None
        for qd in comp.accepted_quests:
            if qd.get("quest_id") == quest_id:
                target = qd
                break
        if target is None:
            return False, "クエストが受諾されていません。", {}

        quest = GeneratedQuest.from_dict(target)
        reward = quest.reward
        gold = int(reward.get("gold", 0))
        exp = int(reward.get("exp", 0))
        items = reward.get("items", []) or []
        bonus = reward.get("bonus", {}) or {}
        # Step 24: 目的ごとの累積報酬(cascade_bonus)を合算
        for obj in quest.objectives:
            for k, v in (obj.cascade_bonus or {}).items():
                bonus[k] = bonus.get(k, 0) + v

        player.gold = getattr(player, "gold", 0) + gold
        try:
            player.job_exp = getattr(player, "job_exp", 0) + exp
        except Exception as e:
            logger.warning("Failed to add job_exp to player: %s", e)
        try:
            if hasattr(player, "inventory") and items:
                for it in items:
                    player.inventory.add_item(it, 1)
        except Exception as e:
            logger.warning("Failed to add quest reward items to player inventory: %s", e)
        fame = int(bonus.get("fame", 0))
        rel_bonus = int(bonus.get("relationship", 0))
        meta = int(bonus.get("meta", 0))
        if fame:
            try:
                player.guild_contribution = getattr(player, "guild_contribution", 0) + fame
            except Exception as e:
                logger.warning("Failed to update guild_contribution: %s", e)
        if rel_bonus and quest.npc_id:
            try:
                from naRou.relationship_system import REGISTRY as REL_REG
                from naRou.relationship_system import RelationshipManager

                RelationshipManager(REL_REG).update_relationship(
                    player,
                    quest.npc_id,
                    action="quest",
                    delta_trust=rel_bonus * 5,
                    delta_mood=rel_bonus * 3,
                )
            except Exception as e:
                logger.debug("Falling back to direct character_relationships update: %s", e)
                rels = getattr(player, "character_relationships", {})
                cur = rels.get(quest.npc_id, {"trust": 0, "mood": 0})
                cur["trust"] = cur.get("trust", 0) + rel_bonus * 5
                rels[quest.npc_id] = cur
                player.character_relationships = rels
        if meta:
            try:
                player.meta_progression = getattr(player, "meta_progression", {})
                player.meta_progression["points"] = player.meta_progression.get("points", 0) + meta
            except Exception as e:
                logger.warning("Failed to update meta_progression points: %s", e)

        comp.accepted_quests = [q for q in comp.accepted_quests if q.get("quest_id") != quest_id]
        comp.completed_quest_ids.append(quest_id)
        comp.completed_count += 1
        msg = f"生成クエスト【{quest.title}】達成！ 金貨+{gold}G, 経験+{exp} 獲得！"
        if engine:
            engine.log(msg, (255, 215, 0))
        # Step 20, 21, 23: 連鎖フォローアップの自動提示
        self.present_followup(player, quest, engine)
        return True, msg, reward

    # Step 19: 連鎖フォローアップの提示
    def present_followup(
        self, player: Entity, parent_quest: GeneratedQuest, engine: Engine | None = None
    ) -> GeneratedQuest | None:
        """完了時に次の連鎖クエストを生成しボードへ提示 (Step 19)"""
        followup = self.generator.generate_followup(parent_quest, player)
        if followup is None:
            return None
        comp = self._comp(player)
        cid = followup.chain_id
        # 同一 chain_id の重複生成を防止 (付録7)
        if followup.quest_id in comp.active_chains.get(cid, []):
            return None
        comp.active_chains.setdefault(cid, []).append(followup.quest_id)
        comp.active_board.append(followup.to_dict())
        if engine:
            engine.log(f"連鎖クエスト【{followup.title}】が発生！", (255, 180, 255))
        return followup
