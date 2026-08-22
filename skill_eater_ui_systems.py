"""
skill_eater_ui_systems.py
W4（スキル喰い）UI/UX システムモジュール
計画書（implementation_plan.md）の軸A・軸Bに関する全72ステップの実装
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable

# ==============================================================================
# 【機能1】ラジアルメニュー（リングメニュー）システム (Steps 1-12)
# ==============================================================================

@dataclass
class RadialMenuItem:
    """Step 4: メニューアイテムのデータ構造（ID, アイコン画像パス, 表示ラベル名）"""
    item_id: str
    icon_path: str
    label: str
    angle_rad: float = 0.0
    is_highlighted: bool = False


class RadialMenu:
    """ラジアルメニュー（リングメニュー）UIコンポーネント (Steps 1-12)"""

    def __init__(self, center_x: float = 0.0, center_y: float = 0.0, radius: float = 100.0):
        # Step 1: UIレイヤー用のキャンバス/ベースフレーム初期化設定
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius

        # Step 2: ラジアルメニュー親ノード管理
        self.items: list[RadialMenuItem] = []
        self.selected_index: int | None = None
        self.is_open: bool = False
        self.anim_scale: float = 0.0  # Step 12用
        self.anim_alpha: float = 0.0  # Step 12用
        self._on_select_callbacks: dict[str, Callable[[], Any]] = {}

    @staticmethod
    def calculate_position_on_circle(center_x: float, center_y: float, radius: float, angle_rad: float) -> tuple[float, float]:
        """Step 3: 円形レイアウト構成用の数学関数（三角関数を用いた座標計算）"""
        x = center_x + radius * math.cos(angle_rad)
        y = center_y + radius * math.sin(angle_rad)
        return (x, y)

    def add_item(self, item: RadialMenuItem, callback: Callable[[], Any] | None = None) -> None:
        """Step 5: 定義データに基づいてアイテムノードを動的に追加"""
        self.items.append(item)
        if callback:
            self._on_select_callbacks[item.item_id] = callback
        self.recalculate_layout()

    def recalculate_layout(self) -> None:
        """Step 6: 各アイテムノードを円周上に等間隔で配置するレイアウト関数"""
        count = len(self.items)
        if count == 0:
            return
        angle_step = (2 * math.pi) / count
        for i, item in enumerate(self.items):
            # 上方向（-pi/2）を起点に時計回りに配置
            item.angle_rad = -math.pi / 2 + i * angle_step

    def handle_input(self, stick_x: float, stick_y: float, deadzone: float = 0.2) -> int | None:
        """
        Step 7: プレイヤー入力（スティックXY / マウス相対座標）の取得
        Step 8: 入力座標から角度（atan2）を計算
        Step 9: 現在選択されているアイテムの判定
        Step 10: 選択中アイテムのハイライト更新
        """
        magnitude = math.hypot(stick_x, stick_y)
        if magnitude < deadzone or len(self.items) == 0:
            self._clear_highlights()
            self.selected_index = None
            return None

        # Step 8: 角度計算 (-pi ~ pi)
        input_angle = math.atan2(stick_y, stick_x)

        # Step 9: 最も角度の近いアイテムを判定
        best_index = 0
        min_diff = float("inf")
        for i, item in enumerate(self.items):
            # 角度差を -pi ~ pi に正規化
            diff = abs((input_angle - item.angle_rad + math.pi) % (2 * math.pi) - math.pi)
            if diff < min_diff:
                min_diff = diff
                best_index = i

        # Step 10: 選択アイテムを視覚的に強調
        self._clear_highlights()
        self.selected_index = best_index
        self.items[best_index].is_highlighted = True
        return self.selected_index

    def _clear_highlights(self) -> None:
        for item in self.items:
            item.is_highlighted = False

    def confirm_selection(self) -> Any:
        """Step 11: 決定ボタン押下時に選択中アイテムのコールバックを発火"""
        if self.selected_index is not None and 0 <= self.selected_index < len(self.items):
            selected_item = self.items[self.selected_index]
            cb = self._on_select_callbacks.get(selected_item.item_id)
            if cb:
                return cb()
            return selected_item.item_id
        return None

    def update_animation(self, open_target: bool, delta_time: float, speed: float = 10.0) -> None:
        """Step 12: 開閉時のスケール・フェードアニメーション補間"""
        self.is_open = open_target
        target_scale = 1.0 if open_target else 0.0
        target_alpha = 1.0 if open_target else 0.0
        self.anim_scale += (target_scale - self.anim_scale) * min(1.0, speed * delta_time)
        self.anim_alpha += (target_alpha - self.anim_alpha) * min(1.0, speed * delta_time)


# ==============================================================================
# 【機能2】星図UIのマグネットカーソルシステム (Steps 13-24)
# ==============================================================================

@dataclass
class SkillNodePoint:
    node_id: str
    x: float
    y: float
    skill_name: str = ""


class MagneticCursorSystem:
    """星図UIにおけるマグネット（スナップ）カーソルシステム (Steps 13-24)"""

    def __init__(self, snap_radius: float = 50.0):
        # Step 13: 全スキルノードの座標リスト管理
        self.nodes: list[SkillNodePoint] = []
        # Step 14: 現在のカーソル位置 (X, Y)
        self.cursor_x: float = 0.0
        self.cursor_y: float = 0.0
        self.target_x: float = 0.0
        self.target_y: float = 0.0
        self.current_node_id: str | None = None
        self.snap_radius = snap_radius
        self.snap_effect_played: bool = False  # Step 22用
        self._listeners: list[Callable[[str], None]] = []

    def register_nodes(self, nodes: list[SkillNodePoint]) -> None:
        self.nodes = list(nodes)
        if nodes and self.current_node_id is None:
            self.cursor_x = nodes[0].x
            self.cursor_y = nodes[0].y
            self.target_x = self.cursor_x
            self.target_y = self.cursor_y
            self.current_node_id = nodes[0].node_id

    def subscribe_node_selected(self, callback: Callable[[str], None]) -> None:
        """Step 23: 選択中ノード情報のブロードキャストリスナー登録"""
        self._listeners.append(callback)

    def handle_direction_input(self, dir_x: float, dir_y: float) -> str | None:
        """
        Step 15: 方向入力イベント
        Step 16: 入力ベクトルの正規化
        Step 17: ノード間方向ベクトルの計算
        Step 18: 内積（ドット積）による方向候補抽出
        Step 19: 角度と距離の重み付けスコア計算
        Step 20: ターゲットノード座標更新
        """
        length = math.hypot(dir_x, dir_y)
        if length < 0.1 or not self.nodes:
            return None

        # Step 16: 正規化
        norm_dir_x = dir_x / length
        norm_dir_y = dir_y / length

        current_node = next((n for n in self.nodes if n.node_id == self.current_node_id), None)
        origin_x = current_node.x if current_node else self.cursor_x
        origin_y = current_node.y if current_node else self.cursor_y

        best_score = -float("inf")
        best_node = None

        for node in self.nodes:
            if current_node and node.node_id == current_node.node_id:
                continue

            # Step 17: 方向ベクトル計算
            dx = node.x - origin_x
            dy = node.y - origin_y
            dist = math.hypot(dx, dy)
            if dist < 1e-4:
                continue

            node_dir_x = dx / dist
            node_dir_y = dy / dist

            # Step 18: 内積 (dot product)
            dot = norm_dir_x * node_dir_x + norm_dir_y * node_dir_y
            if dot <= 0.2:  # 前方およそ78度以内
                continue

            # Step 19: 角度一致度と距離のスコア計算（角度重視＋距離が近いほど高スコア）
            score = (dot * 2.0) - (dist * 0.005)
            if score > best_score:
                best_score = score
                best_node = node

        # Step 20: ターゲット座標の更新
        if best_node:
            self.current_node_id = best_node.node_id
            self.target_x = best_node.x
            self.target_y = best_node.y
            self.snap_effect_played = False
            self._broadcast_selected(best_node.node_id)
            return best_node.node_id

        return None

    def update_cursor_interpolation(self, delta_time: float, lerp_speed: float = 15.0) -> None:
        """
        Step 21: Lerpによる滑らかな補間アニメーション
        Step 22: 吸着エフェクトのトリガー
        """
        self.cursor_x += (self.target_x - self.cursor_x) * min(1.0, lerp_speed * delta_time)
        self.cursor_y += (self.target_y - self.cursor_y) * min(1.0, lerp_speed * delta_time)

        # 到達判定
        if math.hypot(self.target_x - self.cursor_x, self.target_y - self.cursor_y) < 1.0:
            if not self.snap_effect_played:
                self.snap_effect_played = True  # Step 22: 吸着エフェクト発生フラグ

    def handle_mouse_proximity_snap(self, mouse_x: float, mouse_y: float) -> str | None:
        """Step 24: マウス操作時の近傍ノード自動吸着判定"""
        nearest_node = None
        min_dist = self.snap_radius

        for node in self.nodes:
            dist = math.hypot(node.x - mouse_x, node.y - mouse_y)
            if dist < min_dist:
                min_dist = dist
                nearest_node = node

        if nearest_node:
            self.current_node_id = nearest_node.node_id
            self.target_x = nearest_node.x
            self.target_y = nearest_node.y
            self._broadcast_selected(nearest_node.node_id)
            return nearest_node.node_id
        else:
            self.target_x = mouse_x
            self.target_y = mouse_y
            return None

    def _broadcast_selected(self, node_id: str) -> None:
        """Step 23: UIシステムへの通知"""
        for cb in self._listeners:
            cb(node_id)


# ==============================================================================
# 【機能3】長押しスキャナー切り替えシステム (Steps 25-36)
# ==============================================================================

class HoldScannerToggleSystem:
    """スキャナー長押し切り替え＆HUD制御 (Steps 25-36)"""

    def __init__(self, cooldown_time: float = 0.1):
        # Step 27: is_scanning フラグ
        self.is_scanning: bool = False
        self.hud_visible: bool = False
        self.hud_alpha: float = 0.0
        self.camera_filter_active: bool = False
        self.cooldown_timer: float = 0.0
        self.cooldown_duration = cooldown_time
        self._observers: list[Callable[[bool], None]] = []

    def register_observer(self, callback: Callable[[bool], None]) -> None:
        """Step 30: イベントパブリッシャーの購読"""
        self._observers.append(callback)

    def on_button_pressed(self) -> bool:
        """Step 25, 28: 押下イベントで is_scanning = True"""
        if self.cooldown_timer > 0:
            return False  # Step 36: チャタリング防止
        self.is_scanning = True
        self.cooldown_timer = self.cooldown_duration
        self._notify_state_change()
        return True

    def on_button_released(self) -> bool:
        """Step 26, 29: 離上イベントで is_scanning = False"""
        self.is_scanning = False
        self._notify_state_change()
        return True

    def _notify_state_change(self) -> None:
        """Step 30, 31: 変更をリスナーへ通知"""
        for obs in self._observers:
            obs(self.is_scanning)

    def update(self, delta_time: float, transition_speed: float = 5.0) -> None:
        """
        Step 32, 33: HUD可視性更新
        Step 34: フェードイン/アウト アニメーション
        Step 35: カメラポストプロセスフィルター切り替え
        Step 36: クールダウンタイマー更新
        """
        if self.cooldown_timer > 0:
            self.cooldown_timer = max(0.0, self.cooldown_timer - delta_time)

        target_alpha = 1.0 if self.is_scanning else 0.0
        self.hud_alpha += (target_alpha - self.hud_alpha) * min(1.0, transition_speed * delta_time)
        self.hud_visible = self.hud_alpha > 0.01
        self.camera_filter_active = self.is_scanning


# ==============================================================================
# 【機能4】照準（レティクル）周辺のARホログラムUI (Steps 37-48)
# ==============================================================================

@dataclass
class TargetEntity:
    entity_id: str
    world_x: float
    world_y: float
    world_z: float
    hp: int
    max_hp: int
    skill_name: str
    is_occluded: bool = False


@dataclass
class ARPanelWidget:
    """Step 41: ARパネルプレハブ・ウィジェット"""
    screen_x: float = 0.0
    screen_y: float = 0.0
    scale: float = 1.0
    alpha: float = 1.0
    visible: bool = False
    title_text: str = ""
    skill_text: str = ""
    scanline_progress: float = 0.0  # Step 48用


class ReticleARHologramSystem:
    """照準周辺ARホログラムUIシステム (Steps 37-48)"""

    def __init__(self, screen_width: float = 1920.0, screen_height: float = 1080.0):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.panel = ARPanelWidget()
        self.current_target_id: str | None = None

    def get_reticle_screen_pos(self) -> tuple[float, float]:
        """Step 37: レティクルのスクリーン中央座標"""
        return (self.screen_width / 2.0, self.screen_height / 2.0)

    @staticmethod
    def world_to_screen(world_x: float, world_y: float, world_z: float, cam_x: float, cam_y: float, fov_scale: float = 1000.0) -> tuple[float, float, float]:
        """Step 39: 3Dワールド座標からスクリーン2D座標への簡易射影変換"""
        rel_x = world_x - cam_x
        rel_y = world_y - cam_y
        dist = max(0.1, world_z)
        screen_x = 960.0 + (rel_x / dist) * fov_scale
        screen_y = 540.0 + (rel_y / dist) * fov_scale
        return (screen_x, screen_y, dist)

    def update_target_ar_panel(self, target: TargetEntity | None, cam_x: float, cam_y: float, delta_time: float) -> ARPanelWidget:
        """
        Steps 38, 40, 42, 43, 44, 45, 46, 47, 48:
        ARパネルの位置更新、クランプ、距離に応じたスケール/透明度、遮蔽判定、アニメーション
        """
        if target is None:
            self.panel.visible = False
            self.current_target_id = None
            return self.panel

        # Step 47: 遮蔽判定
        if target.is_occluded:
            self.panel.visible = False
            return self.panel

        # Step 39: 座標変換
        sx, sy, dist = self.world_to_screen(target.world_x, target.world_y, target.world_z, cam_x, cam_y)

        # Step 40, 43: オフセット配置 (右上にホログラム表示)
        offset_x = 60.0
        offset_y = -40.0
        raw_x = sx + offset_x
        raw_y = sy + offset_y

        # Step 44: 画面外クランプ
        clamped_x = max(100.0, min(self.screen_width - 250.0, raw_x))
        clamped_y = max(80.0, min(self.screen_height - 150.0, raw_y))

        # Step 45: 距離に応じたスケール調整
        scale = max(0.6, min(1.2, 10.0 / dist))

        # Step 46: 距離に応じた透明度
        alpha = max(0.2, min(1.0, 1.0 - (dist - 5.0) / 25.0))

        # Step 42: データバインド
        self.panel.title_text = f"TARGET: HP {target.hp}/{target.max_hp}"
        self.panel.skill_text = f"EXTRACTABLE: {target.skill_name}"

        # Step 48: スキャンラインアニメーション
        if self.current_target_id != target.entity_id:
            self.current_target_id = target.entity_id
            self.panel.scanline_progress = 0.0
        else:
            self.panel.scanline_progress = min(1.0, self.panel.scanline_progress + delta_time * 3.0)

        self.panel.screen_x = clamped_x
        self.panel.screen_y = clamped_y
        self.panel.scale = scale
        self.panel.alpha = alpha
        self.panel.visible = True
        return self.panel


# ==============================================================================
# 【機能5】カラーコードとシルエットによる視覚伝達 (Steps 49-60)
# ==============================================================================

# Step 50: レア度別カラーコード (R, G, B)
RARITY_COLORS = {
    "COMMON": (0.8, 0.8, 0.8),
    "UNCOMMON": (0.2, 0.9, 0.3),
    "RARE": (0.2, 0.5, 1.0),
    "EPIC": (0.8, 0.2, 0.9),
    "LEGENDARY": (1.0, 0.7, 0.1),
}

# Step 51: 属性別カラーコード
ELEMENT_COLORS = {
    "FIRE": (1.0, 0.2, 0.1),
    "ELECTRIC": (1.0, 0.9, 0.2),
    "POISON": (0.2, 0.9, 0.2),
    "VOID": (0.5, 0.1, 0.8),
    "PHYSICAL": (0.7, 0.7, 0.7),
}

@dataclass
class SkillMetadata:
    """Step 49: スキルメタデータ定義"""
    skill_id: str
    rarity: str
    element: str
    danger_level: int = 1


@dataclass
class OutlineMaterialParams:
    """Step 53: アウトライン（シルエット）シェーダーパラメータ"""
    color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    intensity: float = 1.0
    pulse_rate: float = 1.0
    is_flashing: bool = False
    is_active: bool = False


class SilhouetteColorSystem:
    """カラーコード＆シルエットシェーダー連携システム (Steps 49-60)"""

    def __init__(self):
        self.default_params = OutlineMaterialParams(is_active=False)

    @staticmethod
    def extract_dominant_skill(skills: list[SkillMetadata]) -> SkillMetadata | None:
        """Step 54: 最も重要度・レア度が高い代表スキルを選出"""
        if not skills:
            return None
        rarity_weights = {"COMMON": 1, "UNCOMMON": 2, "RARE": 3, "EPIC": 4, "LEGENDARY": 5}
        return max(skills, key=lambda s: (rarity_weights.get(s.rarity, 0), s.danger_level))

    def compute_outline_params(
        self,
        skills: list[SkillMetadata],
        danger_rating: int,
        is_stunned: bool = False,
        elapsed_time: float = 0.0
    ) -> OutlineMaterialParams:
        """
        Steps 55, 56, 57, 58, 59:
        カラー決定、発光強度、パルス明滅、状態異常点滅
        """
        dominant = self.extract_dominant_skill(skills)
        if not dominant:
            return OutlineMaterialParams(is_active=False)

        # Step 55, 56: カラー取得
        color = ELEMENT_COLORS.get(dominant.element, RARITY_COLORS.get(dominant.rarity, (1.0, 1.0, 1.0)))

        # Step 57: 危険度に応じた発光強度
        base_intensity = 1.0 + (danger_rating * 0.3)

        # Step 58: パルス明滅効果
        pulse = 0.8 + 0.2 * math.sin(elapsed_time * 4.0)
        final_intensity = base_intensity * pulse

        # Step 59: スタン等の点滅フラグ
        flashing = is_stunned and (int(elapsed_time * 10) % 2 == 0)

        return OutlineMaterialParams(
            color=color,
            intensity=final_intensity,
            pulse_rate=4.0,
            is_flashing=flashing,
            is_active=True
        )

    def reset_material(self) -> OutlineMaterialParams:
        """Step 60: クリーンアップ・リセット"""
        return OutlineMaterialParams(is_active=False)


# ==============================================================================
# 【機能6】動的フォーカス（被写界深度 / DoF）システム (Steps 61-72)
# ==============================================================================

@dataclass
class PostProcessProfile:
    """Step 62: DoFポストプロセス設定"""
    dof_enabled: bool = False
    focus_distance: float = 10.0
    aperture: float = 2.8
    focal_length: float = 50.0
    background_dim_alpha: float = 0.0  # Step 71用フォールバック


class DynamicFocusDoFSystem:
    """動的被写界深度（DoF）制御システム (Steps 61-72)"""

    def __init__(self, is_low_quality_mode: bool = False):
        # Step 61, 71: 初期化＆低スペックフォールバック設定
        self.profile = PostProcessProfile()
        self.is_low_quality_mode = is_low_quality_mode
        self.target_focus_dist: float = 10.0
        self.target_aperture: float = 2.8

    def set_focus_mode(self, is_focused: bool, target_distance: float = 5.0) -> None:
        """
        Step 63, 64, 65, 66, 67, 68:
        フォーカス有効化、ターゲット距離計算、絞り/焦点距離設定
        """
        if not is_focused:
            self.reset_to_default()
            return

        self.target_focus_dist = max(0.5, target_distance)
        self.target_aperture = 1.4 if not self.is_low_quality_mode else 2.8

        if self.is_low_quality_mode:
            # Step 71: 低スペック時はDoF無効＋暗転（Dimmer）フォールバック
            self.profile.dof_enabled = False
            self.profile.background_dim_alpha = 0.6
        else:
            # Step 64, 68: DoF有効化
            self.profile.dof_enabled = True
            self.profile.focal_length = 85.0
            self.profile.background_dim_alpha = 0.0

    def update_transition(self, delta_time: float, lerp_speed: float = 8.0) -> PostProcessProfile:
        """
        Step 69, 70: 滑らかなLerp補間トランジション＆フォーカス追従
        """
        self.profile.focus_distance += (self.target_focus_dist - self.profile.focus_distance) * min(1.0, lerp_speed * delta_time)
        self.profile.aperture += (self.target_aperture - self.profile.aperture) * min(1.0, lerp_speed * delta_time)
        return self.profile

    def reset_to_default(self) -> PostProcessProfile:
        """Step 72: 通常ゲームプレイへのリセット・クリーンアップ"""
        self.profile.dof_enabled = False
        self.profile.focus_distance = 50.0
        self.profile.aperture = 8.0
        self.profile.focal_length = 35.0
        self.profile.background_dim_alpha = 0.0
        self.target_focus_dist = 50.0
        self.target_aperture = 8.0
        return self.profile
