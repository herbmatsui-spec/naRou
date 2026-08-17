"""
プロシージャル・クエスト生成システム (Steps 9-36)

依頼ボード / ランダムダンジョン探索 / NPC個別クエスト を
「アーキタイプ × 難易度 × 報酬 × 舞台」の組み合わせで自動生成する。
既存の Registry/Manager/Data 3層パターンに厳密準拠。
"""

from __future__ import annotations
import os
import random
import hashlib
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from entity import Entity
    from game import Engine


# ============================================================
# フェーズB: データクラス (Steps 9-14)
# ============================================================

# Step 9: QuestArchetype
@dataclass
class QuestArchetype:
    """クエストアーキタイプ（形態）"""
    id: str = ""
    name: str = ""
    objective_type: str = "kill"          # kill/collect/visit/escort/explore/rescue/delivery
    title_template: str = "{setting}のクエスト"
    desc_template: str = "{setting}で任務を遂行せよ。"
    reward_weight: float = 1.0
    base_complexity: int = 1


# Step 10: DifficultyTier
@dataclass
class DifficultyTier:
    """難易度ティア（指数スケーリング）"""
    id: str = ""
    name: str = ""
    level_range: List[int] = field(default_factory=lambda: [1, 5])
    enemy_multiplier: float = 1.0
    objective_complexity: float = 1.0
    recommended_power: int = 10


# Step 11: RewardTable
@dataclass
class RewardTable:
    """報酬テーブル"""
    id: str = ""
    name: str = ""
    gold_range: List[int] = field(default_factory=lambda: [20, 80])
    exp_range: List[int] = field(default_factory=lambda: [10, 40])
    item_pool: List[str] = field(default_factory=list)
    bonus: Dict[str, int] = field(default_factory=dict)


# Step 12: StageSetting
@dataclass
class StageSetting:
    """舞台設定"""
    id: str = ""
    name: str = ""
    flavor: str = ""
    enemy_pool: List[str] = field(default_factory=list)
    hazard: str = ""
    depth_modifier: float = 1.0
    environmental_modifier: float = 1.0


# Step 13: NPCQuestTheme
@dataclass
class NPCQuestTheme:
    """NPC個別クエストテーマ"""
    npc_type: str = ""
    quest_pool: List[str] = field(default_factory=list)
    relationship_gate: int = 1
    flavor: str = "{npc}「頼んだよ。」"


# Step 14: QuestObjectiveSpec / GeneratedQuest
@dataclass
class QuestObjectiveSpec:
    """生成されたクエストの1目的"""
    objective_id: str = ""
    description: str = ""
    target_type: str = "kill"
    target_id: str = ""
    required_count: int = 1
    current_count: int = 0
    cascade_bonus: Dict[str, int] = field(default_factory=dict)  # 連鎖累積報酬 (Step 14)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "description": self.description,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "required_count": self.required_count,
            "current_count": self.current_count,
            "cascade_bonus": self.cascade_bonus,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "QuestObjectiveSpec":
        return cls(
            objective_id=d.get("objective_id", ""),
            description=d.get("description", ""),
            target_type=d.get("target_type", "kill"),
            target_id=d.get("target_id", ""),
            required_count=d.get("required_count", 1),
            current_count=d.get("current_count", 0),
            cascade_bonus=d.get("cascade_bonus", {}),
        )


@dataclass
class GeneratedQuest:
    """自動生成されたクエスト（組み合わせの実体）"""
    quest_id: str = ""
    title: str = ""
    description: str = ""
    source_type: str = "board"            # board / dungeon / npc
    archetype_id: str = ""
    difficulty_id: str = ""
    reward_id: str = ""
    setting_id: str = ""
    npc_id: Optional[str] = None
    seed: int = 0
    recommended_level: int = 1
    objectives: List[QuestObjectiveSpec] = field(default_factory=list)
    reward: Dict[str, Any] = field(default_factory=dict)
    expires: int = 0
    chain_id: str = ""          # 連鎖識別子 (Step 13)
    parent_id: str = ""         # 親クエストID (Step 13)
    depth: int = 0              # 連鎖深度 (Step 13)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quest_id": self.quest_id,
            "title": self.title,
            "description": self.description,
            "source_type": self.source_type,
            "archetype_id": self.archetype_id,
            "difficulty_id": self.difficulty_id,
            "reward_id": self.reward_id,
            "setting_id": self.setting_id,
            "npc_id": self.npc_id,
            "seed": self.seed,
            "recommended_level": self.recommended_level,
            "objectives": [o.to_dict() for o in self.objectives],
            "reward": self.reward,
            "expires": self.expires,
            "chain_id": self.chain_id,
            "parent_id": self.parent_id,
            "depth": self.depth,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GeneratedQuest":
        return cls(
            quest_id=d.get("quest_id", ""),
            title=d.get("title", ""),
            description=d.get("description", ""),
            source_type=d.get("source_type", "board"),
            archetype_id=d.get("archetype_id", ""),
            difficulty_id=d.get("difficulty_id", ""),
            reward_id=d.get("reward_id", ""),
            setting_id=d.get("setting_id", ""),
            npc_id=d.get("npc_id"),
            seed=d.get("seed", 0),
            recommended_level=d.get("recommended_level", 1),
            objectives=[QuestObjectiveSpec.from_dict(o) for o in d.get("objectives", [])],
            reward=d.get("reward", {}),
            expires=d.get("expires", 0),
            chain_id=d.get("chain_id", ""),
            parent_id=d.get("parent_id", ""),
            depth=d.get("depth", 0),
        )

    def is_completed(self) -> bool:
        return all(o.current_count >= o.required_count for o in self.objectives)


# ============================================================
# フェーズC: レジストリ (Steps 15-18)
# ============================================================

# Step 15, 16: QuestGenerationRegistry (シングルトン)
class QuestGenerationRegistry:
    """クエスト生成設定レジストリ (Step 15, 16)"""
    _instance: Optional['QuestGenerationRegistry'] = None

    def __new__(cls) -> 'QuestGenerationRegistry':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._archetypes: Dict[str, QuestArchetype] = {}
            cls._difficulties: Dict[str, DifficultyTier] = {}
            cls._rewards: Dict[str, RewardTable] = {}
            cls._settings: Dict[str, StageSetting] = {}
            cls._npc_themes: Dict[str, NPCQuestTheme] = {}
            cls._board_config: Dict[str, Any] = {}
            cls._display_names: Dict[str, Dict[str, str]] = {}
            cls._chain_config: Dict[str, Any] = {}
            cls._loaded = False
        return cls._instance

    # Step 17: load()
    def load(self, file_path: str = "data/procedural_scenarios.yaml") -> None:
        """YAML(procedural_scenarios.yaml) から quest_generation を読み込む (Step 17)"""
        self._archetypes = {}
        self._difficulties = {}
        self._rewards = {}
        self._settings = {}
        self._npc_themes = {}
        self._board_config = {}
        self._display_names = {}
        self._chain_config = {}

        if not os.path.exists(file_path):
            self._load_fallback()
            self._loaded = True
            return

        try:
            import yaml
            with open(file_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            qg = raw.get("quest_generation", {})
            self._build(qg)
        except Exception:
            self._load_fallback()
        self._loaded = True

    def _build(self, qg: Dict[str, Any]) -> None:
        for aid, a in (qg.get("archetypes") or {}).items():
            self._archetypes[aid] = QuestArchetype(
                id=aid, name=a.get("name", aid), objective_type=a.get("objective_type", "kill"),
                title_template=a.get("title_template", "{setting}のクエスト"),
                desc_template=a.get("desc_template", "{setting}で任務を遂行せよ。"),
                reward_weight=float(a.get("reward_weight", 1.0)),
                base_complexity=int(a.get("base_complexity", 1)),
            )
        for did, d in (qg.get("difficulty_tiers") or {}).items():
            self._difficulties[did] = DifficultyTier(
                id=did, name=d.get("name", did),
                level_range=d.get("level_range", [1, 5]),
                enemy_multiplier=float(d.get("enemy_multiplier", 1.0)),
                objective_complexity=float(d.get("objective_complexity", 1.0)),
                recommended_power=int(d.get("recommended_power", 10)),
            )
        for rid, r in (qg.get("reward_tables") or {}).items():
            self._rewards[rid] = RewardTable(
                id=rid, name=r.get("name", rid),
                gold_range=r.get("gold_range", [20, 80]),
                exp_range=r.get("exp_range", [10, 40]),
                item_pool=r.get("item_pool", []),
                bonus=r.get("bonus", {}),
            )
        for sid, s in (qg.get("stage_settings") or {}).items():
            self._settings[sid] = StageSetting(
                id=sid, name=s.get("name", sid), flavor=s.get("flavor", ""),
                enemy_pool=s.get("enemy_pool", []), hazard=s.get("hazard", ""),
                depth_modifier=float(s.get("depth_modifier", 1.0)),
                environmental_modifier=float(s.get("environmental_modifier", 1.0)),
            )
        for nid, n in (qg.get("npc_quest_themes") or {}).items():
            self._npc_themes[nid] = NPCQuestTheme(
                npc_type=n.get("npc_type", nid),
                quest_pool=n.get("quest_pool", []),
                relationship_gate=int(n.get("relationship_gate", 1)),
                flavor=n.get("flavor", "{npc}「頼んだよ。」"),
            )
        self._board_config = qg.get("request_board", {}) or {}
        self._display_names = qg.get("display_names", {}) or {}
        self._chain_config = qg.get("chain_config", {}) or {}

    def _load_fallback(self) -> None:
        self._archetypes = {
            "slay": QuestArchetype("slay", "討伐", "kill", "{setting}の討伐", "", 1.0, 1),
        }
        self._difficulties = {
            "normal": DifficultyTier("normal", "中", [15, 35], 2.6, 1.6, 120),
        }
        self._rewards = {
            "gold": RewardTable("gold", "金", [250, 800], [120, 400], ["gem"], {"fame": 8}),
        }
        self._settings = {
            "forest": StageSetting("forest", "森", "深い森", ["wolf", "goblin"], "毒", 1.0, 1.0),
        }
        self._npc_themes = {
            "villager": NPCQuestTheme("villager", ["rescue"], 1, "{npc}「お願い…」"),
        }
        self._board_config = {"max_active": 8, "type_weights": {"slay": 3}}
        self._display_names = {}
        self._chain_config = {}

    # Step 18: 取得メソッド群
    def get_display_name(self, category: str, id: str) -> str:
        """英語IDを日本語表示名へ変換（未定義なら元のIDを返す・フォールバック）(Step 10)"""
        return self._display_names.get(category, {}).get(id, id)
    def get_archetype(self, aid: str) -> Optional[QuestArchetype]:
        return self._archetypes.get(aid)

    def get_difficulty(self, did: str) -> Optional[DifficultyTier]:
        return self._difficulties.get(did)

    def get_reward(self, rid: str) -> Optional[RewardTable]:
        return self._rewards.get(rid)

    def get_setting(self, sid: str) -> Optional[StageSetting]:
        return self._settings.get(sid)

    def get_npc_theme(self, npc_type: str) -> Optional[NPCQuestTheme]:
        return self._npc_themes.get(npc_type)

    def board_config(self) -> Dict[str, Any]:
        return self._board_config

    def chain_config(self) -> Dict[str, Any]:
        """連鎖クエスト設定 (Step 16)"""
        return self._chain_config

    def display_names(self) -> Dict[str, Dict[str, str]]:
        return self._display_names

    def all_archetypes(self) -> Dict[str, QuestArchetype]:
        return dict(self._archetypes)

    def all_difficulties(self) -> Dict[str, DifficultyTier]:
        return dict(self._difficulties)

    def all_rewards(self) -> Dict[str, RewardTable]:
        return dict(self._rewards)

    def all_settings(self) -> Dict[str, StageSetting]:
        return dict(self._settings)

    def all_npc_themes(self) -> Dict[str, NPCQuestTheme]:
        return dict(self._npc_themes)

    def difficulty_order(self) -> List[str]:
        """ティアを難易度順（低→高）に並べたIDリスト"""
        tiers = list(self._difficulties.values())
        tiers.sort(key=lambda t: t.recommended_power)
        return [t.id for t in tiers]


REGISTRY = QuestGenerationRegistry()


# ============================================================
# フェーズD〜G: 生成エンジン (Steps 19-33)
# ============================================================

class ProceduralQuestGenerator:
    """プロシージャルクエスト生成器 (Steps 19-33)"""

    def __init__(self, registry: Optional[QuestGenerationRegistry] = None):
        self.registry = registry or REGISTRY

    # Step 19: シード決定論ヘルパー
    def _seeded_rng(self, *keys: Any) -> random.Random:
        """(seed, *keys) から決定論的乱数を生成 (Step 19)"""
        base = "|".join(str(k) for k in keys)
        digest = hashlib.sha256(base.encode("utf-8")).hexdigest()
        return random.Random(int(digest[:16], 16))

    # Step 20: コア合成
    def _compose(self, source_type: str, archetype: QuestArchetype,
                 difficulty: DifficultyTier, reward: RewardTable,
                 setting: StageSetting, seed: int,
                 npc_id: Optional[str] = None) -> GeneratedQuest:
        """アーキタイプ × 難易度 × 報酬 × 舞台 を合成 (Step 20)"""
        rng = self._seeded_rng(source_type, archetype.id, difficulty.id,
                               reward.id, setting.id, npc_id or "", seed)

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
        objective = self._build_objective(archetype, enemy, item, boss, required_count,
                                         enemy_disp, item_disp, boss_disp)

        # Step 23: 報酬合成
        final_reward = self._compose_reward(difficulty, reward, rng)

        title = archetype.title_template.format(
            setting=setting_disp, archetype=archetype.name,
            enemy=enemy_disp, item=item_disp, boss=boss_disp,
            required_count=required_count)
        desc = archetype.desc_template.format(
            setting=setting_disp, archetype=archetype.name,
            enemy=enemy_disp, item=item_disp, boss=boss_disp,
            required_count=required_count, hazard=setting.hazard,
            flavor=setting.flavor)

        recommended_level = int((difficulty.level_range[0] + difficulty.level_range[1]) / 2)

        return GeneratedQuest(
            quest_id=f"gen_{source_type}_{seed & 0xffffffff:x}_{archetype.id}_{difficulty.id}_{reward.id}_{setting.id}",
            title=title, description=desc, source_type=source_type,
            archetype_id=archetype.id, difficulty_id=difficulty.id,
            reward_id=reward.id, setting_id=setting.id, npc_id=npc_id,
            seed=seed, recommended_level=recommended_level,
            objectives=[objective], reward=final_reward, expires=0)

    def _compute_required_count(self, archetype: QuestArchetype,
                                difficulty: DifficultyTier,
                                setting: StageSetting,
                                rng: random.Random) -> int:
        base = 4 * archetype.base_complexity
        val = base * difficulty.enemy_multiplier * difficulty.objective_complexity
        if archetype.objective_type == "explore":
            val *= setting.depth_modifier
        val *= setting.environmental_modifier
        count = max(1, int(round(val * rng.uniform(0.9, 1.1))))
        return count

    def _build_objective(self, archetype: QuestArchetype, enemy: str,
                          item: str, boss: str, required_count: int,
                          enemy_disp: str = "", item_disp: str = "",
                          boss_disp: str = "") -> QuestObjectiveSpec:
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
            objective_id=f"{archetype.id}_obj", description=desc,
            target_type=otype, target_id=target_id,
            required_count=required_count)

    def _compose_reward(self, difficulty: DifficultyTier,
                        reward: RewardTable,
                        rng: random.Random) -> Dict[str, Any]:
        gold = int(rng.randint(reward.gold_range[0], reward.gold_range[1])
                   * difficulty.enemy_multiplier)
        exp = int(rng.randint(reward.exp_range[0], reward.exp_range[1])
                  * difficulty.objective_complexity)
        items = []
        if reward.item_pool and rng.random() < 0.85:
            items.append(rng.choice(reward.item_pool))
        bonus = dict(reward.bonus)
        return {"gold": gold, "exp": exp, "items": items, "bonus": bonus}

    # ---- 共通: 難易度帯の選択 ----
    def _pick_difficulty_for_level(self, player_level: int,
                                   min_id: Optional[str] = None,
                                   max_id: Optional[str] = None,
                                   rng: Optional[random.Random] = None) -> DifficultyTier:
        order = self.registry.difficulty_order()
        if min_id:
            while order and order[0] != min_id:
                order.pop(0)
        if max_id and max_id in order:
            idx = order.index(max_id)
            order = order[:idx + 1]
        cand: List[DifficultyTier] = []
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
    def generate_board_quest(self, player: Optional["Entity"] = None,
                             seed: Optional[int] = None,
                             archetype_id: Optional[str] = None,
                             difficulty_id: Optional[str] = None) -> GeneratedQuest:
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
                player_level, cfg.get("min_difficulty"), cfg.get("max_difficulty"), rng)
        if diff is None:
            diff = DifficultyTier()

        reward = self._pick_reward_for_difficulty(diff, rng)
        setting = rng.choice(list(self.registry.all_settings().values())) if self.registry.all_settings() else StageSetting()
        return self._compose("board", arch, diff, reward, setting, seed)

    def generate_board_pool(self, player: Optional["Entity"] = None,
                            count: Optional[int] = None) -> List[GeneratedQuest]:
        """依頼ボード用クエスト複数生成＋重複排除 (Step 25)"""
        cfg = self.registry.board_config()
        max_active = count or int(cfg.get("max_active", 8))
        quests: List[GeneratedQuest] = []
        seen_keys = set()
        attempts = 0
        while len(quests) < max_active and attempts < max_active * 20:
            attempts += 1
            q = self.generate_board_quest(player)
            # 報酬ティアのみ異なる同一見た目クエストを排除し、掲示板を視覚的に多様に保つ
            key = (q.archetype_id, q.difficulty_id, q.setting_id, q.title)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            quests.append(q)
        return quests

    # ---- Step 28-30: ランダムダンジョン探索 ----
    def generate_dungeon_quest(self, player: Optional["Entity"] = None,
                               seed: Optional[int] = None,
                               theme_id: Optional[str] = None) -> GeneratedQuest:
        """ランダムダンジョン探索クエストを生成 (Step 28)"""
        if seed is None:
            seed = random.randint(0, 10**9)
        rng = self._seeded_rng("dungeon", seed)

        theme = None
        try:
            from procedural_dungeon_generator import REGISTRY as DT_REG
            if theme_id:
                theme = DT_REG.get(theme_id)
            elif player is not None:
                from procedural_dungeon_generator import ProceduralDungeonGenerator
                gen = ProceduralDungeonGenerator(DT_REG)
                theme = gen.select_theme_by_story(player)
        except Exception:
            theme = None

        setting = None
        if theme is not None:
            setting = self.registry.get_setting(theme.theme_id) or self.registry.get_setting("cave")
        if setting is None:
            setting = rng.choice(list(self.registry.all_settings().values())) if self.registry.all_settings() else StageSetting()

        # ダンジョン目的: 探索 または ボス討伐 (Step 29)
        arch = self.registry.get_archetype("explore") or self.registry.get_archetype("boss_hunt") or QuestArchetype()
        if rng.random() < 0.4:
            arch = self.registry.get_archetype("boss_hunt") or arch

        player_level = int(getattr(player, "level", 1)) if player else 1
        diff = self._pick_difficulty_for_level(player_level, None, None, rng)
        reward = self._pick_reward_for_difficulty(diff, rng)
        # Step 30: 舞台×テーマ合成
        return self._compose("dungeon", arch, diff, reward, setting, seed)

    # ---- Step 31-33: NPC個別クエスト ----
    def generate_npc_quest(self, npc_id: str, npc_type: str,
                           player: Optional["Entity"] = None,
                           seed: Optional[int] = None) -> Optional[GeneratedQuest]:
        """NPC個別クエストを生成 (Step 31)"""
        theme = self.registry.get_npc_theme(npc_type)
        if theme is None:
            return None

        # Step 32: 友好度ゲート
        if player is not None and theme.relationship_gate > 0:
            rel_level = self._get_relationship_level(player, npc_id)
            if rel_level < theme.relationship_gate:
                return None

        if seed is None:
            seed = random.randint(0, 10**9)
        rng = self._seeded_rng("npc", npc_id, seed)

        pool = [self.registry.get_archetype(a) for a in theme.quest_pool]
        pool = [a for a in pool if a is not None]
        arch = rng.choice(pool) if pool else (self.registry.get_archetype("delivery") or QuestArchetype())

        player_level = int(getattr(player, "level", 1)) if player else 1
        diff = self._pick_difficulty_for_level(player_level, None, None, rng)
        reward = self._pick_reward_for_difficulty(diff, rng)

        # Step 33: 個別フレーバー付与
        setting = rng.choice(list(self.registry.all_settings().values())) if self.registry.all_settings() else StageSetting()
        quest = self._compose("npc", arch, diff, reward, setting, seed, npc_id=npc_id)
        quest.description = theme.flavor.format(npc=npc_id) + " " + quest.description
        return quest

    # ---- Step 17-18: 連鎖クエスト（報酬カスケード） ----
    def generate_followup(self, parent: GeneratedQuest,
                          player: Optional["Entity"] = None,
                          seed: Optional[int] = None) -> Optional[GeneratedQuest]:
        """親クエストのフォローアップ（連鎖次世代）を生成 (Step 17)"""
        cfg = self.registry.chain_config()
        max_depth = int(cfg.get("max_depth", 5))
        if parent.depth + 1 > max_depth:
            return None  # Step 21: 深度上限で打ち切り
        if seed is None:
            seed = random.randint(0, 10**9)
        rng = self._seeded_rng("chain", parent.chain_id or parent.quest_id, seed)

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

        quest = self._compose(parent.source_type, arch, diff, reward, setting, seed, npc_id=parent.npc_id)
        depth = parent.depth + 1
        quest.chain_id = parent.chain_id or parent.quest_id
        quest.parent_id = parent.quest_id
        quest.depth = depth

        # Step 18: 報酬カスケード合成（階層累積乗算＋ボーナス加算）
        gm = float(cfg.get("gold_multiplier_per_depth", 1.5))
        em = float(cfg.get("exp_multiplier_per_depth", 1.4))
        quest.reward["gold"] = int(quest.reward.get("gold", 0) * (gm ** depth))
        quest.reward["exp"] = int(quest.reward.get("exp", 0) * (em ** depth))
        bonus = quest.reward.get("bonus", {}) or {}
        bonus["fame"] = bonus.get("fame", 0) + int(cfg.get("cascade_fame_per_depth", 2)) * depth
        bonus["relationship"] = bonus.get("relationship", 0) + int(cfg.get("cascade_relationship_per_depth", 1)) * depth
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
    def _weighted_choice(self, items: List[Tuple[str, Any]],
                         weights: Dict[str, int], rng: random.Random) -> Optional[Any]:
        if not items:
            return None
        w = [max(1, int(weights.get(k, 1))) for k, _ in items]
        chosen = rng.choices(items, weights=w, k=1)[0]
        return chosen[1]

    def _pick_reward_for_difficulty(self, diff: DifficultyTier,
                                    rng: random.Random) -> RewardTable:
        order = list(self.registry.all_rewards().values())
        if not order:
            return RewardTable()
        idx = int((diff.recommended_power ** 0.5) / 12 + rng.randint(0, 1))
        idx = max(0, min(len(order) - 1, idx))
        return order[idx]

    def _get_relationship_level(self, player: "Entity", npc_id: str) -> int:
        try:
            from relationship_system import RelationshipManager, REGISTRY as REL_REG
            return RelationshipManager(REL_REG).get_relationship_level(player, npc_id)
        except Exception:
            rels = getattr(player, "character_relationships", {})
            return int((rels.get(npc_id, {}) or {}).get("trust", 0) // 30)


# ============================================================
# フェーズH: 管理・進捗・報酬 (Steps 34-35)
# ============================================================

# 敵名のローマ字↔カタカナ/日本語ゆれを吸収する軽量マップ（ゲーム内実体名との照合用）
_ENEMY_NAME_MAP = {
    "goblin": ["ゴブリン", "goblin", "ゴブリ"],
    "slime": ["スライム", "ぷち", "slime"],
    "wolf": ["オオカミ", "ウルフ", "wolf"],
    "frost_wolf": ["フロストウルフ", "ice wolf", "frost_wolf"],
    "bat": ["コウモリ", "bat"],
    "cave_bear": ["ケイブベア", "cave_bear", "熊"],
    "bear": ["ベア", "bear", "熊"],
    "skeleton": ["スケルトン", "skeleton"],
    "ghost": ["ゴースト", "ghost"],
    "golem": ["ゴーレム", "golem"],
    "fire_lizard": ["ファイアリザード", "fire_lizard"],
    "magma_elemental": ["マグマエレメンタル", "magma_elemental"],
    "ifrit": ["イフリート", "ifrit"],
    "yeti": ["イエティ", "yeti"],
    "ice_sprite": ["アイススプライト", "ice_sprite"],
    "crocodile": ["クロコダイル", "ワニ", "crocodile"],
    "venom_toad": ["ベノムトード", "venom_toad"],
    "abyssal_horror": ["アビサルホラー", "abyssal_horror"],
    "void_lord": ["ヴォイドロード", "void_lord"],
    "nightmare": ["ナイトメア", "nightmare"],
    "bandit": ["バンディット", "bandit", "盗賊"],
    "stray_dog": ["野良犬", "stray_dog"],
    "pickpocket": ["スリ", "pickpocket"],
    "dog": ["犬", "dog"],
}


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
    for key, variants in _ENEMY_NAME_MAP.items():
        norms = [v.lower().replace(" ", "_") for v in variants]
        q_in = q in norms
        e_in = event_norm in norms or key == event_norm
        if q_in and e_in:
            return True
    return False


class ProceduralQuestManager:
    """生成クエストの受諍・進捗・達成・報酬付与管理 (Steps 34-35)"""

    def __init__(self, generator: Optional[ProceduralQuestGenerator] = None):
        self.generator = generator or ProceduralQuestGenerator(REGISTRY)

    def _comp(self, player: "Entity"):
        return player.procedural_quest

    # Step 26, 27: ボード管理
    def ensure_board(self, player: "Entity", engine: Optional["Engine"] = None) -> List[GeneratedQuest]:
        comp = self._comp(player)
        if not comp.active_board:
            self.refresh_board(player, engine)
        return [GeneratedQuest.from_dict(d) for d in comp.active_board]

    def refresh_board(self, player: "Entity", engine: Optional["Engine"] = None) -> List[GeneratedQuest]:
        """依頼ボードを再生成 (Step 26, 27)"""
        comp = self._comp(player)
        comp.board_seed = (comp.board_seed + 1) % (10**9)
        quests = self.generator.generate_board_pool(player)
        comp.active_board = [q.to_dict() for q in quests]
        if engine:
            engine.log(f"依頼ボードが更新された（{len(quests)}件）", (200, 220, 255))
        return quests

    def get_available_board(self, player: "Entity") -> List[GeneratedQuest]:
        return self.ensure_board(player)

    def get_npc_quests(self, player: "Entity", npc_id: str,
                       npc_type: str) -> List[GeneratedQuest]:
        """NPCが提示可能な個別クエスト一覧 (Step 31)"""
        q = self.generator.generate_npc_quest(npc_id, npc_type, player)
        return [q] if q else []

    def accept_quest(self, player: "Entity", quest_id: str) -> bool:
        comp = self._comp(player)
        for bd in comp.active_board:
            if bd.get("quest_id") == quest_id:
                comp.accepted_quests.append(bd)
                comp.active_board = [b for b in comp.active_board if b.get("quest_id") != quest_id]
                return True
        return False

    # Step 34: 進捗更新
    def update_progress(self, player: "Entity", event_type: str,
                        target_id: str, amount: int = 1,
                        engine: Optional["Engine"] = None) -> List[str]:
        """イベントに基づき受諾済クエストの目的を進捗 (Step 34)"""
        comp = self._comp(player)
        logs: List[str] = []
        n_target = _norm_target(target_id)
        for qd in comp.accepted_quests:
            quest = GeneratedQuest.from_dict(qd)
            changed = False
            for obj in quest.objectives:
                if obj.target_type == event_type and obj.current_count < obj.required_count:
                    if obj.target_id == target_id or _target_matches(obj.target_id, n_target):
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
    def complete_quest(self, player: "Entity", quest_id: str,
                       engine: Optional["Engine"] = None) -> Tuple[bool, str, Dict[str, Any]]:
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
        except Exception:
            pass
        try:
            if hasattr(player, "inventory") and items:
                for it in items:
                    player.inventory.add_item(it, 1)
        except Exception:
            pass
        fame = int(bonus.get("fame", 0))
        rel_bonus = int(bonus.get("relationship", 0))
        meta = int(bonus.get("meta", 0))
        if fame:
            try:
                player.guild_contribution = getattr(player, "guild_contribution", 0) + fame
            except Exception:
                pass
        if rel_bonus and quest.npc_id:
            try:
                from relationship_system import RelationshipManager, REGISTRY as REL_REG
                RelationshipManager(REL_REG).update_relationship(
                    player, quest.npc_id, action="quest", delta_trust=rel_bonus * 5, delta_mood=rel_bonus * 3)
            except Exception:
                rels = getattr(player, "character_relationships", {})
                cur = rels.get(quest.npc_id, {"trust": 0, "mood": 0})
                cur["trust"] = cur.get("trust", 0) + rel_bonus * 5
                rels[quest.npc_id] = cur
                player.character_relationships = rels
        if meta:
            try:
                player.meta_progression = getattr(player, "meta_progression", {})
                player.meta_progression["points"] = player.meta_progression.get("points", 0) + meta
            except Exception:
                pass

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
    def present_followup(self, player: "Entity", parent_quest: GeneratedQuest,
                         engine: Optional["Engine"] = None) -> Optional[GeneratedQuest]:
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
