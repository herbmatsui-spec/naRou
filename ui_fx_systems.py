"""
Elona Roguelike - UI & Visual FX Systems (Phases 2 - 8)
- FloatingText (Popup Damage & Healing)
- ParticleSystem (Spells, Explosions, Sparks)
- LookMode (Inspect entities & tiles)
- ContextMenu (Spacebar smart interact)
- MiniMap (Dungeon radar overlay)
- PaperDollRenderer (Visual equipment layout)
- DynamicLighting (Smooth FOV distance shading)
"""

from __future__ import annotations

import logging
logger = logging.getLogger(__name__)
import math
import random
from dataclasses import dataclass
from typing import Any

import tcod

from constants import COLOR_PET_PINK, MAP_WIDTH, VIEW_HEIGHT
from feature_flags import is_enabled
from job_system import JobRegistry
from skill_tree_system import SkillTreeRegistry


@dataclass
class FloatingText:
    """ポップアップダメージ・回復表示 (Phase 6)"""

    text: str
    x: float
    y: float
    color: tuple[int, int, int]
    life: int = 4  # 残り表示ターン/フレーム
    vy: float = -0.3  # 上向きの浮遊速度

    def update(self) -> bool:
        self.y += self.vy
        self.life -= 1
        return self.life > 0


@dataclass
class Particle:
    """魔法の軌跡や爆発などのパーティクル (Phase 7)"""

    char: str
    x: float
    y: float
    color: tuple[int, int, int]
    life: int = 3
    vx: float = 0.0
    vy: float = 0.0
    # 衝撃波などのための拡張属性
    is_shockwave: bool = False
    # Tiny Rogue tile-based rendering
    tile_id: str | None = None

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        return self.life > 0


class LookCursor:
    """ルックモード（ターゲット調査）管理 (Phase 2)"""

    def __init__(self, x: int = 0, y: int = 0):
        self.x = x
        self.y = y

    def move(self, dx: int, dy: int, map_w: int = MAP_WIDTH, map_h: int = VIEW_HEIGHT):
        self.x = max(0, min(map_w - 1, self.x + dx))
        self.y = max(0, min(map_h - 1, self.y + dy))


class ContextAction:
    """コンテキストメニュー項目 (Phase 4)"""

    def __init__(
        self, label: str, action_key: str, handler_name: str, payload: Any = None
    ):
        self.label = label
        self.action_key = action_key
        self.handler_name = handler_name
        self.payload = payload


class ContextMenu:
    """スマートインタラクション用メニュー (Phase 4)"""

    def __init__(self):
        self.actions: list[ContextAction] = []
        self.selected_index: int = 0

    def set_actions(self, actions: list[ContextAction]):
        self.actions = actions
        self.selected_index = 0

    def is_empty(self) -> bool:
        return len(self.actions) == 0


class MiniMapRenderer:
    """ダンジョン全体を見渡すミニマップ (Phase 3)"""

    WIDTH = 18
    HEIGHT = 9

    @classmethod
    def render(
        cls,
        console: tcod.console.Console,
        start_x: int,
        start_y: int,
        game_map,
        player,
        pet,
        entities,
    ):
        # 枠線描画
        console.draw_frame(
            x=start_x,
            y=start_y,
            width=cls.WIDTH + 2,
            height=cls.HEIGHT + 2,
            title="🗺️MAP",
            fg=(80, 120, 180),
            bg=(10, 14, 22),
        )

        scale_x = game_map.width / cls.WIDTH
        scale_y = game_map.height / cls.HEIGHT

        for my in range(cls.HEIGHT):
            for mx in range(cls.WIDTH):
                orig_x = int(mx * scale_x)
                orig_y = int(my * scale_y)

                if 0 <= orig_x < game_map.width and 0 <= orig_y < game_map.height:
                    if game_map.explored[orig_x][orig_y]:
                        if game_map.is_walkable(orig_x, orig_y):
                            console.print(
                                start_x + 1 + mx, start_y + 1 + my, "·", fg=(70, 75, 90)
                            )
                        else:
                            console.print(
                                start_x + 1 + mx, start_y + 1 + my, "#", fg=(40, 45, 55)
                            )
                    else:
                        console.print(
                            start_x + 1 + mx, start_y + 1 + my, " ", bg=(8, 10, 15)
                        )

        # 敵モンスター (赤)
        for e in entities:
            if e not in (player, pet) and getattr(e, "hp", 0) > 0:
                if game_map.visible[e.x][e.y]:
                    emx = int(e.x / scale_x)
                    emy = int(e.y / scale_y)
                    if 0 <= emx < cls.WIDTH and 0 <= emy < cls.HEIGHT:
                        console.print(
                            start_x + 1 + emx, start_y + 1 + emy, "x", fg=(255, 80, 80)
                        )

        # ペット (ピンク)
        if pet and pet.hp > 0:
            pmx = int(pet.x / scale_x)
            pmy = int(pet.y / scale_y)
            if 0 <= pmx < cls.WIDTH and 0 <= pmy < cls.HEIGHT:
                console.print(
                    start_x + 1 + pmx, start_y + 1 + pmy, "p", fg=COLOR_PET_PINK
                )

        # プレイヤー (緑)
        pl_mx = int(player.x / scale_x)
        pl_my = int(player.y / scale_y)
        if 0 <= pl_mx < cls.WIDTH and 0 <= pl_my < cls.HEIGHT:
            console.print(
                start_x + 1 + pl_mx, start_y + 1 + pl_my, "@", fg=(100, 255, 120)
            )


@dataclass
class LightSource:
    """状況適応型ダイナミック・ライティング用光源 (Proposal 2)"""

    x: int
    y: int
    radius: float = 7.0
    color: tuple[int, int, int] = (255, 240, 200)  # 暖色系松明光
    intensity: float = 1.0
    flicker: bool = False
    source_type: str = "torch"  # torch, magic, moonlight, altar, crystal


class DynamicLighting:
    """状況適応型ダイナミック・ライティング & 複数光源・影・シルエット管理 (Proposal 2)"""

    @staticmethod
    def calculate_distance_intensity(
        x: int, y: int, px: int, py: int, max_radius: float = 8.0
    ) -> float:
        dist = math.hypot(x - px, y - py)
        if dist > max_radius:
            return 0.0
        # 2次曲線による自然な減衰
        intensity = 1.0 - (dist / max_radius) ** 1.6
        return max(0.15, min(1.0, intensity))

    @staticmethod
    def blend_color(
        base_color: tuple[int, int, int], factor: float
    ) -> tuple[int, int, int]:
        return (
            int(base_color[0] * factor),
            int(base_color[1] * factor),
            int(base_color[2] * factor),
        )

    @classmethod
    def calculate_tile_lighting(
        cls,
        x: int,
        y: int,
        base_color: tuple[int, int, int],
        light_sources: list[LightSource],
        ambient_color: tuple[int, int, int] | None = None,
    ) -> tuple[tuple[int, int, int], float]:
        if ambient_color is None:
            # バイオームに基づいたデフォルト環境光の決定
            # 本来は context.current_biome 等から取得するが、ここでは座標ベースの擬似バイオームで実装
            # 0: 深い森 (緑がかった暗闇), 1: 洞窟 (青白い暗闇), 2: 溶岩地帯 (赤みがかった暗闇)
            biome_type = (x // 50 + y // 50) % 3
            biome_ambients = {
                0: (15, 30, 20),  # Forest
                1: (20, 25, 40),  # Cave
                2: (40, 20, 15),  # Lava
            }
            ambient_color = biome_ambients.get(biome_type, (20, 25, 35))
        """複数光源からの光線合成と影・照度計算 (RGB加算合成 + クランプ)"""
        total_r = ambient_color[0]
        total_g = ambient_color[1]
        total_b = ambient_color[2]
        total_intensity = 0.15

        for light in light_sources:
            dist = math.hypot(x - light.x, y - light.y)
            if dist <= light.radius:
                # 距離減衰カーブ
                falloff = 1.0 - (dist / light.radius) ** 1.5
                factor = max(0.0, min(1.0, falloff * light.intensity))
                total_intensity = max(total_intensity, factor)

                # 光源色の加算ブレンド
                total_r += int(light.color[0] * factor * (base_color[0] / 255.0))
                total_g += int(light.color[1] * factor * (base_color[1] / 255.0))
                total_b += int(light.color[2] * factor * (base_color[2] / 255.0))

        lit_r = min(255, max(0, total_r))
        lit_g = min(255, max(0, total_g))
        lit_b = min(255, max(0, total_b))
        return (lit_r, lit_g, lit_b), min(1.0, total_intensity)

    @classmethod
    def get_tile_lighting_properties(cls, tile_id: str) -> dict[str, Any]:
        """
        Get tile-specific lighting properties for advanced rendering.

        Returns dict with keys:
        - 'emissive': bool - whether tile emits light
        - 'emissive_color': Tuple[int, int, int] - color of emitted light
        - 'emissive_radius': float - radius of emitted light
        - 'reflective': bool - whether tile reflects light strongly
        - 'translucent': bool - whether tile lets light through
        - 'material': str - material type for material-based lighting
        """
        props = {
            "emissive": False,
            "emissive_color": (255, 255, 255),
            "emissive_radius": 0.0,
            "reflective": False,
            "translucent": False,
            "material": "default",
        }

        # Tiny Rogue tile properties
        if tile_id.startswith("TR_"):
            # Light sources
            if tile_id in ("TR_DECOR_01",):  # Torch
                props.update(
                    {
                        "emissive": True,
                        "emissive_color": (255, 180, 50),
                        "emissive_radius": 5.0,
                        "material": "fire",
                    }
                )
            elif tile_id in ("TR_DECOR_03",):  # Altar
                props.update(
                    {
                        "emissive": True,
                        "emissive_color": (255, 225, 100),
                        "emissive_radius": 4.0,
                        "material": "holy",
                    }
                )
            elif tile_id in ("TR_DECOR_04",):  # Fountain
                props.update(
                    {
                        "emissive": True,
                        "emissive_color": (100, 200, 255),
                        "emissive_radius": 3.0,
                        "material": "water",
                    }
                )
            # Reflective surfaces
            elif (
                tile_id.startswith(("TR_ITEM_04", "TR_ITEM_05", "TR_ITEM_07", "TR_ITEM_08"))
            ):  # Weapons
                props.update(
                    {
                        "reflective": True,
                        "material": "metal",
                    }
                )
            elif tile_id.startswith("TR_UI_07"):  # Coin
                props.update(
                    {
                        "reflective": True,
                        "material": "gold",
                    }
                )
            # Translucent
            elif tile_id.startswith("TR_EFFECT_03"):  # Ice
                props.update(
                    {
                        "translucent": True,
                        "material": "ice",
                    }
                )
            elif tile_id.startswith("TR_EFFECT_06"):  # Heal
                props.update(
                    {
                        "translucent": True,
                        "material": "holy",
                    }
                )
            elif tile_id.startswith("TR_DECOR_04"):  # Fountain/water
                props.update(
                    {
                        "translucent": True,
                        "material": "water",
                    }
                )
            # Material types for floor/wall
            elif tile_id.startswith(("TR_FLOOR", "TR_WALL")):
                props.update({"material": "stone"})
            elif tile_id.startswith(("TR_MONSTER", "TR_PLAYER")):
                props.update({"material": "flesh"})

        return props

    @classmethod
    def get_light_sources_for_engine(cls, context) -> list[LightSource]:
        """現在のゲーム状態から動的光源リストを抽出"""
        sources: list[LightSource] = []
        if not getattr(context, "player", None):
            return sources

        # 1. プレイヤーの松明 / 光 (手持ち光源)
        p = context.player
        sources.append(
            LightSource(
                x=p.x,
                y=p.y,
                radius=8.0,
                color=(255, 235, 190),
                intensity=1.0,
                source_type="player",
            )
        )

        # 2. ペットの淡い守護光
        if getattr(context, "pet", None) and context.pet.hp > 0:
            sources.append(
                LightSource(
                    x=context.pet.x,
                    y=context.pet.y,
                    radius=4.5,
                    color=(255, 200, 230),
                    intensity=0.75,
                    source_type="pet",
                )
            )

        # 3. 祭壇の神聖な黄金光
        if getattr(context, "altar_pos", None):
            ax, ay = context.altar_pos
            sources.append(
                LightSource(
                    x=ax,
                    y=ay,
                    radius=6.0,
                    color=(255, 225, 100),
                    intensity=1.2,
                    source_type="altar",
                )
            )

        # 4. 下り階段 / ポータルの神秘的な青光
        if getattr(context, "game_map", None) and getattr(
            context.game_map, "stairs_down_pos", None
        ):
            sx, sy = context.game_map.stairs_down_pos
            sources.append(
                LightSource(
                    x=sx,
                    y=sy,
                    radius=5.0,
                    color=(120, 220, 255),
                    intensity=0.9,
                    source_type="portal",
                )
            )

        # 5. 鉱石脈・採取ノードの微光
        if getattr(context, "resource_nodes", None):
            for node in context.resource_nodes:
                if not getattr(node, "depleted", False):
                    sources.append(
                        LightSource(
                            x=node.x,
                            y=node.y,
                            radius=3.0,
                            color=(100, 255, 180),
                            intensity=0.6,
                            source_type="resource",
                        )
                    )

        # 6. 光る魔法パーティクル
        if getattr(context, "particles", None):
            for pt in context.particles[:5]:
                sources.append(
                    LightSource(
                        x=int(pt.x),
                        y=int(pt.y),
                        radius=2.5,
                        color=pt.color,
                        intensity=0.8,
                        source_type="magic",
                    )
                )

        return sources


class GaugeBar:
    """ビジュアルステータスバー生成 (HP/MP/満腹度など)"""

    @staticmethod
    def render(
        current: int,
        maximum: int,
        length: int = 10,
        fill_char: str = "■",
        empty_char: str = "□",
    ) -> str:
        if maximum <= 0:
            return empty_char * length
        ratio = max(0.0, min(1.0, current / maximum))
        filled_count = int(ratio * length)
        return (fill_char * filled_count) + (empty_char * (length - filled_count))


@dataclass
class TutorialGuide:
    """動的チュートリアルガイドデータ (Step 1.1)"""

    id: str
    trigger_condition: str
    title: str
    message: str
    action_required: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "trigger_condition": self.trigger_condition,
            "title": self.title,
            "message": self.message,
            "action_required": self.action_required,
        }


class TutorialManager:
    """チュートリアルガイド読み込みおよび進行管理 (Step 1.1, 1.2)"""

    def __init__(self, file_path: str = "data/tutorial_guides.yaml"):
        self.file_path = file_path
        self.guides: dict[str, TutorialGuide] = {}
        self.load()

    def load(self) -> None:
        import os

        import yaml

        self.guides = {}
        if not os.path.exists(self.file_path):
            return
        try:
            with open(self.file_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for gid, gdata in data.get("tutorial_guides", {}).items():
                self.guides[gid] = TutorialGuide(
                    id=gdata.get("id", gid),
                    trigger_condition=gdata.get("trigger_condition", ""),
                    title=gdata.get("title", ""),
                    message=gdata.get("message", ""),
                    action_required=gdata.get("action_required", ""),
                )
        except Exception as e:
            logger.exception("Unhandled exception")
            print(f"[TutorialManager] Failed to load {self.file_path}: {e}")

    def check_triggers(
        self, trigger_condition: str, completed_set: set
    ) -> TutorialGuide | None:
        """発動条件に一致し、未完了のチュートリアルを検索"""
        for guide in self.guides.values():
            if (
                guide.trigger_condition == trigger_condition
                and guide.id not in completed_set
            ):
                return guide
        return None

    def update(self, delta_time: float = 1.0) -> None:
        """チュートリアルマネージャーの更新処理"""


@dataclass
class FloatingNotification:
    """画面中央・上部用フローティング通知 (Step 2.2)"""

    title: str
    message: str
    category: str = "general"  # trophy, achievement, quest, tutorial, critical
    duration: int = 30  # フレーム数 / ターン数
    color: tuple[int, int, int] = (255, 215, 0)


class NotificationManager:
    """重要イベントのポップアップ通知キュー管理 (Step 2.2)"""

    def __init__(self):
        self.active_notifications: list[FloatingNotification] = []

    def notify(
        self,
        title: str,
        message: str,
        category: str = "general",
        color: tuple[int, int, int] = (255, 215, 0),
        duration: int = 30,
    ) -> None:
        self.active_notifications.append(
            FloatingNotification(
                title=title,
                message=message,
                category=category,
                duration=duration,
                color=color,
            )
        )

    def update(self, delta_time: float = 1.0) -> None:
        remaining = []
        for n in self.active_notifications:
            n.duration -= 1
            if n.duration > 0:
                remaining.append(n)
        self.active_notifications = remaining

    def get_latest(self) -> FloatingNotification | None:
        return self.active_notifications[0] if self.active_notifications else None


class ScreenShake:
    """画面振動・エフェクト管理 (Step 2.3)"""

    def __init__(self):
        self.intensity: float = 0.0
        self.duration: int = 0
        self.direction: tuple[float, float] = (0.0, 0.0)  # 衝撃の方向ベクトル (dx, dy)

    def trigger(
        self,
        intensity: float = 1.0,
        duration: int = 4,
        direction: tuple[float, float] = (0.0, 0.0),
    ) -> None:
        self.intensity = intensity
        self.duration = duration
        self.direction = direction

    def update(self) -> bool:
        if self.duration > 0:
            self.duration -= 1
            return True
        self.intensity = 0.0
        return False

    @property
    def is_active(self) -> bool:
        return self.duration > 0


class HelpSystem:
    """初心者向けチュートリアル & ヘルプガイド"""

    TutorialManager = TutorialManager

    SECTIONS = [
        {
            "title": "1. 基本目的 & 初心者の心得",
            "lines": [
                "★ 目標: 食料を確保しながらダンジョンを探索し、強力な装備を手に入れよう！",
                "★ 生存のコツ: HPが減ったら無理せず [Space] で待機し、自然回復や階段・薬で回復。",
                "★ 餓死に注意: 飢餓状態になるとHPが急速に減ります。[i] から食料を食べよう。",
                "★ ペット『シエル』: 頼もしい仲間です。ピンチの時は援護してくれます。装備もできます。",
                "★ 最初の一歩: 右下の階段 [>] からダンジョンに降りてみよう。",
                "★ お金の稼ぎ方: モンスターを倒すとお金が落ちています。売却すれば資金に！",
            ],
        },
        {
            "title": "2. キー操作一覧",
            "lines": [
                "【移動/攻撃】 矢印キー または テンキー(1-9) / hjkl yubn (斜め移動も可能)",
                "【便利操作】   [Space] : スマート行動 (アイテム拾い/食事/会話/ドア開けなど)",
                "【調べる】     [l] : 周囲の敵・地形・アイテムを詳しく調査 (トラップも発見)",
                "【荷物管理】   [i] : インベントリ (アイテム使用/装備/捨てる/売却)",
                "【能力確認】   [c] : キャラクターシート (ステータス/スキル/耐性/レベル確認)",
                "【魔法詠唱】  [f] : 魔法を詠唱する前に [c] で魔法書を確認しよう",
                "【神への祈り】  [p] : 信仰している神に祈るとHP/MP回復や恩恵が得られる",
                "【階段昇降】   [>] : 下り階段 (深層へ),  [<] : 上り階段 (浅層へ)",
                "【セーブ】     [s] : セーブ,  [r] : ロード,  [Esc] : メニュー/終了",
                "【ヘルプ】     [?] / [h] : このヘルプ画面を表示",
                "【ルックモード】 [Shift] + 方向キー : カーソルで遠くのマスを調査",
            ],
        },
        {
            "title": "3. 画面と記号の読み方 (凡例)",
            "lines": [
                "  @  : あなた (緑=良好, 黄色=警告, 赤=危険)",
                "  p  : ペット (妹分シエル、ピンク色)",
                "  #  : 壁 (通行不可)  /  . : 安全な床",
                "  >  : 下り階段 (深層へ, 赤色)  /  < : 上り階段 (青色)",
                "  _  : 神の祭壇 (信仰を捧げたり祈る場所、黄色)",
                "  %  : 薬草  /  ? : キノコ  /  $ : 鉱石鉱脈",
                "  !  : ポーション  /  / : 武器  /  [ : 防具",
                "  x  : 敵モンスター (色で危険度を判断)",
                "  ⚔/✷/➛/✚ : 敵の『次回行動』予測 (頭上に表示) = 突撃/詠唱/逃走/回復",
                "  🐌 : かたつむり少女『グウェン』 (友好的NPC)",
                "  🍖 : 肉類 (食料として利用可能)",
                "  💰 : 金貨や宝箱 (お得意の収入源)",
            ],
        },
        {
            "title": "4. システムの解説",
            "lines": [
                "● ターン制: あなたが一歩動くと、周囲の敵や世界も一歩動きます。戦略的に行動しましょう。",
                "● 信仰: ジュアやルルウィなどの神を信仰して祈ると強力な恩恵が得られます。裏切ると罰があります。",
                "● エーテル病: 長く冒険すると変異が発生。進行しすぎると能力低下。[c] で確認しよう。",
                "● カルマ: 悪事を働くと下がり、街の護衛に追われるようになります。善行で上げましょう。",
                "● 空腹と満腹: 空腹になるとHP回復が止まり、さらに減少します。食料は[i]から食べよう。",
                "● 経験値とレベル: 敵を倒すと経験値が入り、一定量でレベルアップ。能力値が上がります。",
                "● ペットシステム: ペットは装備させたり、コマンドを出したりできます。忠誠度が重要。",
                "● 願いの杖: 特殊アイテムでテキスト入力によりさまざまな願いを叶えられます。",
            ],
        },
    ]


class SkillTreeUI:
    """スキルツリー表示ヘルパー (Step 28) - エネルギー回路ビジュアライザー統合"""

    @staticmethod
    def format_tree_summary(
        tree_id: str, tree_name: str, tiers_count: int, learned_count: int
    ) -> str:
        return f"【{tree_name}】 習得済: {learned_count}/{tiers_count} ティア"

    @staticmethod
    def format_tier_line(
        tier_name: str, cost: int, learned: bool, can_learn: bool, frame_count: int = 0
    ) -> str:
        # Proposal 9: エネルギー回路演出 (Rich Data Visualizer)
        # 習得済のスキルには、時間経過で流れる「エネルギーの脈動」を表現
        if learned:
            pulse = "⚡" if (frame_count // 10) % 2 == 0 else "✨"
            status = f"{pulse} 習得済"
        else:
            status = "〇習得可" if can_learn else "×未開放"

        return f"{status} {tier_name:<12} (必要SP: {cost})"

    @classmethod
    def render_circuit_overlay(
        cls,
        console: tcod.console.Console,
        x: int,
        y: int,
        width: int,
        height: int,
        frame_count: int,
    ):
        """スキルツリーの背景に流れるエネルギー回路を描画"""
        # 擬似的な回路パターン
        for i in range(0, width, 4):
            # サイン波で流れる光の粒子
            offset = (frame_count * 2) % 4
            if i + offset < width:
                console.print(x + i + offset, y + (height // 2), "━", fg=(0, 150, 255))
                if (i + offset) % 8 == 0:
                    console.print(
                        x + i + offset, y + (height // 2), "◆", fg=(100, 200, 255)
                    )


class JobUI:
    """ジョブUI表示ヘルパー (Step 53)"""

    @staticmethod
    def format_job_summary(job_name: str, level: int, exp: int) -> str:
        return f"現在の職業: 【{job_name}】 (Job Lv.{level}  EXP: {exp})"


def play_pet_fusion_fx(
    engine: Any, pet1_name: str, pet2_name: str, result_name: str
) -> None:
    """ペット融合エフェクト・パーティクル・ログ演出 (Steps 71, 72)"""
    if not hasattr(engine, "player"):
        return
    px, py = engine.player.x, engine.player.y
    # 神秘的な光のパーティクル
    for _ in range(25):
        engine.particles.append(
            Particle(
                x=px,
                y=py,
                dx=random.uniform(-1.8, 1.8),
                dy=random.uniform(-1.8, 1.8),
                color=random.choice(
                    [(255, 200, 100), (200, 100, 255), (100, 255, 220), (255, 255, 255)]
                ),
                lifetime=15,
                char=random.choice(["*", "✨", "+", "⭐"]),
            )
        )
    engine.floating_texts.append(
        FloatingText(
            x=px,
            y=py - 1,
            text=f"🧬 融合成功！【{result_name}】誕生！",
            color=(255, 215, 0),
            lifetime=30,
        )
    )
    from sound_manager import SoundManager

    SoundManager.play_se("level_up")
    engine.log(
        f"★錬金遺伝子融合の奇跡！【{pet1_name}】と【{pet2_name}】が融合し、【{result_name}】が誕生した！",
        (255, 215, 0),
    )


class PetUI:
    """ペット情報・絆表示ヘルパー"""

    @staticmethod
    def format_bond_summary(
        pet_name: str, contract_name: str, bond: int, max_bond: int
    ) -> str:
        return f"【{pet_name}】 契約: {contract_name}  絆度: {bond}/{max_bond}"


class WeatherAtmosphereLayer:
    """動的レイヤー・環境エフェクト (Proposal 1) - 霧・光粒子・陽炎・浮遊塵"""

    @staticmethod
    def apply_atmosphere(
        console: tcod.console.Console,
        cam_x: int,
        cam_y: int,
        view_w: int,
        view_h: int,
        weather: str = "fog",
        tick: int = 0,
        player_speed: int = 70,
        sanity_ratio: float = 1.0,
    ) -> None:
        """ダンジョン・天候・精神状態に応じた空気感のレイヤー描画"""
        speed_factor = max(0.5, player_speed / 70.0)
        t = tick * 0.05 * speed_factor

        # 精神状態低下(SAN値減)に応じた色味と揺らぎの変化
        is_insane = sanity_ratio < 0.5
        insane_tint = (50, 0, 70) if is_insane else (25, 30, 45)

        for vy in range(view_h):
            for vx in range(view_w):
                mx = cam_x + vx
                my = cam_y + vy

                # 多重サイン波による滑らかな霧・陽炎の濃度マップ
                noise_val = math.sin(mx * 0.15 + t) * math.cos(
                    my * 0.2 - t * 0.8
                ) + math.sin((mx + my) * 0.1 + t * 0.5)
                # 0.0 ~ 1.0 に正規化
                intensity = (noise_val + 2.0) / 4.0

                # --- 視差効果を伴うアンビエント粒子 (Proposal 1) ---
                # 速度の異なる3つのレイヤーで奥行きを表現
                for layer in range(1, 4):
                    # レイヤーごとに異なる速度と周期
                    layer_t = t * (0.5 ** (layer - 1))
                    layer_noise = math.sin(mx * (0.1 * layer) + layer_t) * math.cos(
                        my * (0.1 * layer) - layer_t
                    )
                    layer_intensity = (layer_noise + 1.0) / 2.0

                    if layer_intensity > 0.92:  # 非常に稀に発生する粒子
                        # レイヤーが高いほど小さく、暗い色にする（遠近感）
                        p_col = (
                            int(200 * (1.0 / layer)),
                            int(220 * (1.0 / layer)),
                            int(255 * (1.0 / layer)),
                        )
                        char = "·" if layer == 1 else " "
                        # 背景色にブレンドして描画
                        cur_fg = console.fg[vx, vy]
                        console.fg[vx, vy] = p_col
                        console.print(vx, vy, char, fg=p_col)

                if weather == "fog" and intensity > 0.65:
                    alpha = (intensity - 0.65) * 0.4
                    cur_bg = console.bg[vx, vy]
                    # アルファ合成
                    nbg_r = min(
                        255,
                        int(cur_bg[0] * (1.0 - alpha) + (insane_tint[0] + 150) * alpha),
                    )
                    nbg_g = min(
                        255,
                        int(cur_bg[1] * (1.0 - alpha) + (insane_tint[1] + 160) * alpha),
                    )
                    nbg_b = min(
                        255,
                        int(cur_bg[2] * (1.0 - alpha) + (insane_tint[2] + 180) * alpha),
                    )
                    console.bg[vx, vy] = (nbg_r, nbg_g, nbg_b)
                elif weather == "heatwave" and intensity > 0.7:
                    # 揺れる陽炎
                    cur_fg = console.fg[vx, vy]
                    console.fg[vx, vy] = (
                        min(255, cur_fg[0] + 30),
                        cur_fg[1],
                        max(0, cur_fg[2] - 20),
                    )
                elif weather == "rain":
                    # 雨粒子 (TR_EFFECT_02 fire tile repurposed as rain drops)
                    rain_intensity = (math.sin(vx * 0.3 + tick * 0.8) + 1) * 0.5
                    if rain_intensity > 0.7:
                        console.print(vx, vy, "│", fg=(100, 150, 255))
                elif weather == "snow":
                    # 雪粒子 (TR_EFFECT_03 ice tile)
                    snow_intensity = (math.sin(vx * 0.2 + tick * 0.3) + 1) * 0.5
                    if snow_intensity > 0.75:
                        console.print(vx, vy, "❆", fg=(200, 230, 255))

    @staticmethod
    def spawn_weather_particles(
        fx_manager: Any,
        weather: str,
        cam_x: int,
        cam_y: int,
        view_w: int,
        view_h: int,
        tick: int,
    ) -> None:
        """Spawn weather particles using Tiny Rogue TR_EFFECT_* tiles."""
        if not is_enabled("ENABLE_TINY_ROGUE_GFX"):
            return

        if weather == "rain":
            # Spawn rain drops using TR_EFFECT_02 (fire) as rain
            for _ in range(3):
                fx_manager.spawn_tile_effect(
                    cam_x + random.randint(0, view_w),
                    cam_y + random.randint(0, view_h),
                    "fire",  # repurposed as rain
                    count=1,
                    vx=random.uniform(-0.1, 0.1),
                    vy=random.uniform(0.5, 1.0),
                    life=random.randint(5, 10),
                    color=(100, 150, 255),
                )
        elif weather == "snow":
            # Spawn snow using TR_EFFECT_03 (ice)
            for _ in range(2):
                fx_manager.spawn_tile_effect(
                    cam_x + random.randint(0, view_w),
                    cam_y + random.randint(0, view_h),
                    "ice",
                    count=1,
                    vx=random.uniform(-0.2, 0.2),
                    vy=random.uniform(0.1, 0.3),
                    life=random.randint(10, 20),
                    color=(200, 230, 255),
                )
        elif weather == "ash":
            # Volcanic ash using TR_EFFECT_10 (smoke)
            for _ in range(2):
                fx_manager.spawn_tile_effect(
                    cam_x + random.randint(0, view_w),
                    cam_y + random.randint(0, view_h),
                    "smoke",
                    count=1,
                    vx=random.uniform(-0.3, 0.3),
                    vy=random.uniform(0.0, 0.2),
                    life=random.randint(15, 30),
                    color=(100, 100, 100),
                )


class ScreenFilterManager:
    """状態連動型ビジュアル・デグラデーション (Proposal 3) & 次元干渉グリッチ (Proposal 7)"""

    @staticmethod
    def apply_post_processing(
        console: tcod.console.Console,
        hp: int,
        max_hp: int,
        is_poisoned: bool = False,
        is_starving: bool = False,
        glitch_duration: int = 0,
        frame_count: int = 0,
        dimension_break_frames: int = 0,
    ) -> None:
        """画面全体のポストプロセッシング処理"""
        w, h = console.width, console.height

        # --- 次元突破演出 (Proposal 7: Dimension-break Growth) ---
        if dimension_break_frames > 0:
            # 画面中央から外側へ広がる衝撃波と色彩反転
            f = dimension_break_frames
            center_x, center_y = w // 2, h // 2

            # 放射状のグリッチ・パーティクル
            for _ in range(5):
                import random

                angle = random.uniform(0, 2 * math.pi)
                dist = (20 - f) * 5  # 外側へ拡大
                gx = int(center_x + math.cos(angle) * dist)
                gy = int(center_y + math.sin(angle) * dist)
                if 0 <= gx < w and 0 <= gy < h:
                    console.print(gx, gy, "✧", fg=(255, 255, 255))

            # 画面全体の色彩反転・明滅 (フレーム数に応じて強度を変化)
            if f % 2 == 0:
                for y in range(h):
                    for x in range(w):
                        cur_bg = console.bg[x, y]
                        console.bg[x, y] = (
                            255 - cur_bg[0],
                            255 - cur_bg[1],
                            255 - cur_bg[2],
                        )

        # 1. 出血・低HPの画面端ビネット（赤色ノイズ・血飛沫）
        hp_ratio = max(0.0, min(1.0, hp / max(1, max_hp)))

        # --- ダイナミック・オーラ演出 (Proposal 4) ---
        # バフ状態などの「黄金のオーラ」をシミュレート
        # 本来はengineからバフ状態を取得すべきだが、ここではデモとしてHPが高い時に微弱な黄金粒子を出す
        if hp_ratio > 0.8:
            aura_intensity = (hp_ratio - 0.8) * 2.0  # 0.0 ~ 0.4
            for _ in range(2):  # 1フレームに数個の粒子を散布
                import random

                rx = random.randint(0, w - 1)
                ry = random.randint(0, h - 1)
                # 黄金色の輝きを背景に加算
                cur_bg = console.bg[rx, ry]
                console.bg[rx, ry] = (
                    min(255, int(cur_bg[0] + 100 * aura_intensity)),
                    min(255, int(cur_bg[1] + 80 * aura_intensity)),
                    int(cur_bg[2] * (1.0 - aura_intensity)),
                )

        if hp_ratio < 0.35:
            danger_intensity = (0.35 - hp_ratio) / 0.35  # 0.0 ~ 1.0
            pulse = (math.sin(frame_count * 0.2) + 1.0) * 0.5
            vignette_alpha = danger_intensity * (0.35 + 0.25 * pulse)

            for y in range(h):
                for x in range(w):
                    # 画面中心からの距離によるビネット効果
                    dx = (x - w / 2) / (w / 2)
                    dy = (y - h / 2) / (h / 2)
                    dist_sq = dx * dx + dy * dy
                    if dist_sq > 0.5:
                        edge_factor = min(1.0, (dist_sq - 0.5) / 0.5) * vignette_alpha
                        cur_bg = console.bg[x, y]
                        console.bg[x, y] = (
                            min(255, int(cur_bg[0] + 160 * edge_factor)),
                            int(cur_bg[1] * (1.0 - edge_factor)),
                            int(cur_bg[2] * (1.0 - edge_factor)),
                        )

        # 2. 毒状態の緑色ノイズ
        if is_poisoned:
            p_shift = int(frame_count % 3)
            for y in range(0, h, 2):
                scan_y = (y + p_shift) % h
                for x in range(0, w, 3):
                    cur_fg = console.fg[x, scan_y]
                    console.fg[x, scan_y] = (
                        int(cur_fg[0] * 0.6),
                        min(255, cur_fg[1] + 60),
                        int(cur_fg[2] * 0.6),
                    )

        # 3. 飢餓状態の彩度低下 (デサチュレーション)
        if is_starving:
            for y in range(h):
                for x in range(w):
                    cur_fg = console.fg[x, y]
                    gray = int(
                        0.299 * cur_fg[0] + 0.587 * cur_fg[1] + 0.114 * cur_fg[2]
                    )
                    # 彩度を50%落とす
                    console.fg[x, y] = (
                        int(cur_fg[0] * 0.4 + gray * 0.6),
                        int(cur_fg[1] * 0.4 + gray * 0.6),
                        int(cur_fg[2] * 0.4 + gray * 0.6),
                    )

        # 4. 次元干渉グリッチ (Proposal 7)
        if glitch_duration > 0:
            import random

            glitch_rows = random.sample(range(h), min(h, 4))
            for gy in glitch_rows:
                offset = random.randint(-4, 4)
                for gx in range(w):
                    target_x = max(0, min(w - 1, gx + offset))
                    console.ch[gx, gy] = console.ch[target_x, gy]
                    # サイケデリックな色変調
                    console.fg[gx, gy] = (
                        random.choice([255, 50]),
                        random.choice([0, 255]),
                        255,
                    )


class ItemInspectorUI:
    """超詳細なアイテム・インスペクター (Proposal 4) - 材質・刻印・アート表示"""

    ITEM_ART = {
        "weapon": [
            "  /| ________________",
            "O|===|* >============>",
            "  \\| ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾",
        ],
        "shield": [" /======\\ ", "|  🛡️★  |", " \\======/ "],
        "potion": ["   [==]   ", "  /~~~~\\  ", " |  🧪  | ", "  \\____/  "],
        "food": ["  .----.  ", " ( 🍖🥩 ) ", "  `----'  "],
        "default": [" +------+ ", " | ★📦★ | ", " +------+ "],
    }

    @classmethod
    def render_inspection(
        cls,
        console: tcod.console.Console,
        item: Any,
        appraisal_level: int = 1,
        x: int = 10,
        y: int = 12,
    ) -> None:
        """鑑定レベルと素材に応じた超詳細クローズアップの描画"""
        bw, bh = 60, 14
        console.draw_rect(x=x, y=y, width=bw, height=bh, ch=0, bg=(14, 18, 28))
        console.draw_frame(
            x=x,
            y=y,
            width=bw,
            height=bh,
            title=f" 🔬 精密インスペクター: {item.display_name} ",
            fg=(255, 215, 0),
        )

        # アスキーアート拡大図の描画
        art_lines = cls.ITEM_ART.get(
            getattr(item, "category", ""), cls.ITEM_ART["default"]
        )
        for idx, line in enumerate(art_lines):
            console.print(
                x=x + 3,
                y=y + 3 + idx,
                string=line,
                fg=getattr(item, "color", (200, 200, 255)),
            )

        # 材質・質感・光沢の表示
        mat_name = getattr(item, "material", "iron")
        mat_dict = {
            "rubynus": "深紅のルビナス (艷やかな光沢・吸血の波動)",
            "mithril": "純銀のミスリル (極限の軽さと神聖な輝き)",
            "emerald": "翠玉エメラルド (魔力を帯びた透明感)",
            "steel": "高純度鋼鉄 (重厚な鍛造の焼き入れ跡)",
            "iron": "汎用鉄材 (無骨な質感と細かな研磨傷)",
        }
        mat_desc = mat_dict.get(mat_name, f"{mat_name} (一般的な材質)")
        console.print(x=x + 22, y=y + 2, string=f"材質: {mat_desc}", fg=(255, 230, 160))

        # 鑑定レベルに応じた微細構造・刻印の可視化
        if appraisal_level >= 1:
            console.print(
                x=x + 22,
                y=y + 4,
                string=f"重量: {getattr(item, 'weight', 1.0)}s   価値: {getattr(item, 'value', 0)}G",
                fg=(200, 240, 255),
            )
        if appraisal_level >= 3:
            console.print(
                x=x + 22,
                y=y + 6,
                string="刻印: 『エルス領主の鍛冶職人による微細な銘』",
                fg=(160, 220, 180),
            )
            console.print(
                x=x + 22,
                y=y + 7,
                string="微細摩耗: 刃こぼれなし (耐久度 100%)",
                fg=(180, 200, 220),
            )
        if appraisal_level >= 5:
            console.print(
                x=x + 22,
                y=y + 9,
                string="神気共鳴: ★★★★★ (神の祝福が宿っている)",
                fg=(255, 215, 80),
            )
        else:
            console.print(
                x=x + 22,
                y=y + 9,
                string="隠された刻印: (鑑定スキル Lv.3 以上で可視化)",
                fg=(100, 100, 120),
            )


class EmotionalUI:
    """感情同期型UIアニメーション (Proposal 5) - UIの鼓動・振動・歓喜オーラ"""

    @classmethod
    def draw_emotional_frame(
        cls,
        console: tcod.console.Console,
        x: int,
        y: int,
        width: int,
        height: int,
        title: str,
        base_fg: tuple[int, int, int],
        bg: tuple[int, int, int] = (15, 18, 28),
        hp_ratio: float = 1.0,
        is_celebrating: bool = False,
        frame_count: int = 0,
    ) -> tuple[int, int]:
        """緊張感(ピンチ時の震え)や歓喜(虹色オーラ)を反映した動的ウィンドウ枠描画"""
        draw_x, draw_y = x, y
        fg_col = base_fg

        # 1. 緊張感・恐怖: ピンチ時のUI微小振動
        if hp_ratio < 0.25:
            intensity = int((0.25 - hp_ratio) * 10) + 1
            offset_x = (frame_count % 3 - 1) if intensity > 1 else 0
            offset_y = ((frame_count // 2) % 3 - 1) if intensity > 1 else 0
            draw_x = max(0, min(console.width - width, x + offset_x))
            draw_y = max(0, min(console.height - height, y + offset_y))
            # 危険な赤色の鼓動
            pulse = (math.sin(frame_count * 0.3) + 1.0) * 0.5
            fg_col = (255, int(80 * pulse), int(80 * pulse))

        # 2. 歓喜・祝福: 虹色グラデーション
        elif is_celebrating:
            hue = (frame_count * 15) % 360
            # 簡易HSV -> RGB変換
            hi = int(hue / 60) % 6
            f = hue / 60 - int(hue / 60)
            q = int(255 * (1 - f))
            t = int(255 * f)
            if hi == 0:
                fg_col = (255, t, 0)
            elif hi == 1:
                fg_col = (q, 255, 0)
            elif hi == 2:
                fg_col = (0, 255, t)
            elif hi == 3:
                fg_col = (0, q, 255)
            elif hi == 4:
                fg_col = (t, 0, 255)
            else:
                fg_col = (255, 0, q)

        console.draw_rect(x=draw_x, y=draw_y, width=width, height=height, ch=0, bg=bg)
        console.draw_frame(
            x=draw_x, y=draw_y, width=width, height=height, title=title, fg=fg_col
        )
        return draw_x, draw_y


class CinematicLogVisualizer:
    """究極のログ・ビジュアライザー (Proposal 9) - ログの文字単位アニメーション・衝撃波・発光演出"""

    @classmethod
    def render_cinematic_logs(
        cls,
        console: tcod.console.Console,
        msg_log: Any,
        start_x: int,
        start_y: int,
        count: int = 4,
        frame_count: int = 0,
    ) -> None:
        """ログの振動・重要度発光・文字別パルスを伴う映画的描画"""
        recent = msg_log.get_recent(count) if hasattr(msg_log, "get_recent") else []
        for i, lmsg in enumerate(recent):
            tag = (
                "[!]"
                if lmsg.level == "WARNING"
                else ("★" if lmsg.level == "SUCCESS" else " ")
            )
            text = f"{tag} {lmsg.text}"[:74]
            base_col = lmsg.color

            # 最新ログ (i == len(recent)-1) に対する衝撃波・発光エフェクト
            is_latest = i == len(recent) - 1
            y_pos = start_y + i

            if is_latest and lmsg.level in ("WARNING", "DANGER", "CRITICAL"):
                # 衝撃波の左右揺らぎ
                shake_x = (frame_count % 3 - 1) if (frame_count % 4 < 2) else 0
                pulse_r = min(255, base_col[0] + 50)
                pulse_g = max(0, base_col[1] - 30)
                pulse_b = max(0, base_col[2] - 30)
                console.print(
                    x=start_x + shake_x,
                    y=y_pos,
                    string=text,
                    fg=(pulse_r, pulse_g, pulse_b),
                )
            elif is_latest and lmsg.level == "SUCCESS":
                # 祝福の黄金フラッシュ
                gold_pulse = int(50 * math.sin(frame_count * 0.4))
                console.print(
                    x=start_x,
                    y=y_pos,
                    string=text,
                    fg=(min(255, 220 + gold_pulse), min(255, 200 + gold_pulse), 50),
                )
            else:
                console.print(x=start_x, y=y_pos, string=text, fg=base_col)


def format_skill_tree_display(registry: SkillTreeRegistry) -> str:
    """スキルツリーデータを簡単なテキスト形式で返す"""
    lines = []
    lines.append("=== スキルツリー ===")
    for tree in registry.all().values():
        lines.append(f"{tree.icon} {tree.name}")
        for tier in tree.tiers:
            learned_marker = (
                "[ ]"  # placeholder; actual learned status would need player data
            )
            lines.append(f"  {learned_marker} {tier.name} (コスト: {tier.cost})")
            for effect in tier.effects:
                if effect.type == "damage_bonus":
                    lines.append(f"    ダメージ+{effect.value} ({effect.target})")
                elif effect.type == "crit_chance":
                    lines.append(f"    会心率+{int(effect.value)}% ({effect.target})")
                elif effect.type == "unlock_skill":
                    lines.append(f"    スキル解放: {effect.value}")
                else:
                    lines.append(f"    {effect.type}: {effect.value} ({effect.target})")
        lines.append("")
    return "\n".join(lines)


def format_job_display(registry: JobRegistry, player) -> str:
    """ジョブデータを簡単なテキスト形式で返す"""
    lines = []
    lines.append("=== 職業システム ===")
    lines.append(
        f"現在の職業: {player.job} (Job Lv.{player.job_level}  EXP: {player.job_exp})"
    )
    lines.append("")

    # 現在の職業のステータス補正
    current_job = registry.get(player.job)
    if current_job and current_job.stat_modifiers:
        lines.append("現在の職業補正:")
        for attr, val in current_job.stat_modifiers.items():
            sign = "+" if val >= 0 else ""
            lines.append(f"  {attr}: {sign}{val}")
        lines.append("")

    # 習得済みジョブ
    if hasattr(player, "mastered_jobs") and player.mastered_jobs:
        lines.append("マスター済み職業:")
        for job_id in player.mastered_jobs:
            job = registry.get(job_id)
            if job:
                lines.append(f"  ✓ {job.name} (tier {job.tier})")
        lines.append("")

    # 利用可能なジョブ
    for job_id, job in registry.all().items():
        if job_id == "novice":
            continue
        if job_id in getattr(player, "mastered_jobs", []) or job_id == player.job:
            continue
        # Check unlock conditions (simplified)
        lines.append("転職可能な職業:")
        break

    # Show all jobs with status
    lines.append("職業一覧:")
    for job_id, job in registry.all().items():
        if job_id == "novice":
            continue
        status = ""
        if job_id == player.job:
            status = " (現在)"
        elif job_id in getattr(player, "mastered_jobs", []):
            status = " (マスター済み)"
        icon = getattr(job, "icon", "📋")
        lines.append(f"  {icon} {job.name} (tier {job.tier}){status}")
        if job.stat_modifiers:
            for attr, val in job.stat_modifiers.items():
                sign = "+" if val >= 0 else ""
                lines.append(f"    {attr}: {sign}{val}")
        lines.append("")

    return "\n".join(lines)


# --- LocalizationManager integration (i18n, Step 3.x) ---
from localization_manager import localize  # noqa: E402,F401
