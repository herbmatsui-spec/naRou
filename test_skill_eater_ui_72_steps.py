"""
test_skill_eater_ui_72_steps.py
W4 スキャナー・星図UI（軸A・軸B）の全72ステップ検証用テストスイート
"""
import math


from skill_eater_ui_systems import (
    DynamicFocusDoFSystem,
    HoldScannerToggleSystem,
    MagneticCursorSystem,
    RadialMenu,
    RadialMenuItem,
    ReticleARHologramSystem,
    SilhouetteColorSystem,
    SkillMetadata,
    SkillNodePoint,
    TargetEntity,
)


def test_steps_1_to_12_radial_menu():
    """【機能1】ラジアルメニュー（Steps 1-12）の検証"""
    menu = RadialMenu(center_x=960.0, center_y=540.0, radius=150.0)

    # Step 4, 5: アイテム追加
    executed = []
    menu.add_item(RadialMenuItem("skill_1", "icon1.png", "喰らい"), callback=lambda: executed.append("skill_1"))
    menu.add_item(RadialMenuItem("skill_2", "icon2.png", "解析"), callback=lambda: executed.append("skill_2"))
    menu.add_item(RadialMenuItem("skill_3", "icon3.png", "合成"), callback=lambda: executed.append("skill_3"))
    menu.add_item(RadialMenuItem("skill_4", "icon4.png", "解放"), callback=lambda: executed.append("skill_4"))

    # Step 6: 4アイテムが90度間隔で配置されているか
    assert len(menu.items) == 4
    assert math.isclose(menu.items[0].angle_rad, -math.pi / 2, rel_tol=1e-3)

    # Step 7, 8, 9, 10: スティック入力による角度判定とハイライト
    # 上方向（0, -1） -> skill_1
    idx = menu.handle_input(stick_x=0.0, stick_y=-1.0)
    assert idx == 0
    assert menu.items[0].is_highlighted is True
    assert menu.items[1].is_highlighted is False

    # 右方向（1, 0） -> skill_2
    idx = menu.handle_input(stick_x=1.0, stick_y=0.0)
    assert idx == 1
    assert menu.items[1].is_highlighted is True

    # Step 11: 決定コールバック発火
    res = menu.confirm_selection()
    assert "skill_2" in executed

    # Step 12: アニメーション補間
    menu.update_animation(open_target=True, delta_time=0.1)
    assert menu.anim_scale > 0.0
    assert menu.is_open is True


def test_steps_13_to_24_magnetic_cursor():
    """【機能2】マグネットカーソル（Steps 13-24）の検証"""
    system = MagneticCursorSystem(snap_radius=40.0)

    # Step 13, 14: ノード登録
    nodes = [
        SkillNodePoint("center", 0.0, 0.0, "Root"),
        SkillNodePoint("right_node", 100.0, 0.0, "Slash"),
        SkillNodePoint("up_node", 0.0, 100.0, "Magic"),
    ]
    system.register_nodes(nodes)
    assert system.current_node_id == "center"

    # Step 23: リスナー登録
    selected_log = []
    system.subscribe_node_selected(lambda nid: selected_log.append(nid))

    # Step 15-20: 右方向への入力で right_node に吸着ターゲット更新
    target_id = system.handle_direction_input(dir_x=1.0, dir_y=0.0)
    assert target_id == "right_node"
    assert system.target_x == 100.0
    assert "right_node" in selected_log

    # Step 21, 22: カーソル移動の補間と吸着エフェクト
    for _ in range(10):
        system.update_cursor_interpolation(delta_time=0.1)
    assert math.isclose(system.cursor_x, 100.0, abs_tol=1.0)
    assert system.snap_effect_played is True

    # Step 24: マウス近傍吸着
    nearest = system.handle_mouse_proximity_snap(mouse_x=5.0, mouse_y=95.0)
    assert nearest == "up_node"


def test_steps_25_to_36_hold_scanner_toggle():
    """【機能3】スキャナー長押し切り替え（Steps 25-36）の検証"""
    scanner = HoldScannerToggleSystem(cooldown_time=0.05)

    events = []
    scanner.register_observer(lambda state: events.append(state))

    # Step 25, 28: 押下でスキャナー開始
    assert scanner.on_button_pressed() is True
    assert scanner.is_scanning is True
    assert events[-1] is True

    # Step 36: チャタリング防止
    assert scanner.on_button_pressed() is False

    # Step 32-35: 更新でHUD可視化・フェードイン
    scanner.update(delta_time=0.1)
    assert scanner.hud_visible is True
    assert scanner.hud_alpha > 0.0
    assert scanner.camera_filter_active is True

    # Step 26, 29: 離上でスキャナー終了
    assert scanner.on_button_released() is True
    assert scanner.is_scanning is False

    for _ in range(5):
        scanner.update(delta_time=0.1)
    assert scanner.hud_alpha < 0.2


def test_steps_37_to_48_reticle_ar_hologram():
    """【機能4】照準ARホログラムUI（Steps 37-48）の検証"""
    ar_system = ReticleARHologramSystem(screen_width=1920.0, screen_height=1080.0)

    # Step 37: 照準位置取得
    rx, ry = ar_system.get_reticle_screen_pos()
    assert rx == 960.0 and ry == 540.0

    target = TargetEntity(
        entity_id="enemy_1",
        world_x=2.0,
        world_y=1.0,
        world_z=10.0,
        hp=75,
        max_hp=100,
        skill_name="Thunder Slash",
        is_occluded=False,
    )

    # Step 38-48: ARパネル更新
    panel = ar_system.update_target_ar_panel(target, cam_x=0.0, cam_y=0.0, delta_time=0.1)
    assert panel.visible is True
    assert "HP 75/100" in panel.title_text
    assert "Thunder Slash" in panel.skill_text
    assert panel.scale > 0.0
    assert panel.alpha > 0.0

    # Step 47: 遮蔽時は非表示
    target.is_occluded = True
    panel_occluded = ar_system.update_target_ar_panel(target, cam_x=0.0, cam_y=0.0, delta_time=0.1)
    assert panel_occluded.visible is False


def test_steps_49_to_60_silhouette_color_system():
    """【機能5】カラーコードとシルエット（Steps 49-60）の検証"""
    silhouette = SilhouetteColorSystem()

    skills = [
        SkillMetadata("sk_1", rarity="COMMON", element="PHYSICAL", danger_level=1),
        SkillMetadata("sk_2", rarity="EPIC", element="ELECTRIC", danger_level=4),
    ]

    # Step 54: 代表スキル選出（EPICのElectricが選ばれる）
    dominant = silhouette.extract_dominant_skill(skills)
    assert dominant is not None
    assert dominant.skill_id == "sk_2"

    # Step 55-59: パラメータ計算
    params = silhouette.compute_outline_params(
        skills=skills,
        danger_rating=3,
        is_stunned=True,
        elapsed_time=1.0,
    )
    assert params.is_active is True
    # ELECTRICの色 (1.0, 0.9, 0.2)
    assert params.color == (1.0, 0.9, 0.2)
    assert params.intensity > 1.0

    # Step 60: リセット
    reset_params = silhouette.reset_material()
    assert reset_params.is_active is False


def test_steps_61_to_72_dynamic_focus_dof():
    """【機能6】動的被写界深度（DoF）（Steps 61-72）の検証"""
    dof_system = DynamicFocusDoFSystem(is_low_quality_mode=False)

    # Step 63-68: フォーカス設定
    dof_system.set_focus_mode(is_focused=True, target_distance=4.0)
    assert dof_system.profile.dof_enabled is True

    # Step 69, 70: トランジション補間
    for _ in range(5):
        profile = dof_system.update_transition(delta_time=0.1)
    assert profile.focus_distance < 10.0  # 4.0に向けて近づく

    # Step 71: 低品質モード時のフォールバック検証
    low_dof = DynamicFocusDoFSystem(is_low_quality_mode=True)
    low_dof.set_focus_mode(is_focused=True, target_distance=4.0)
    assert low_dof.profile.dof_enabled is False
    assert low_dof.profile.background_dim_alpha == 0.6

    # Step 72: リセット
    reset_prof = dof_system.reset_to_default()
    assert reset_prof.dof_enabled is False
    assert reset_prof.focus_distance == 50.0


if __name__ == "__main__":
    test_steps_1_to_12_radial_menu()
    test_steps_13_to_24_magnetic_cursor()
    test_steps_25_to_36_hold_scanner_toggle()
    test_steps_37_to_48_reticle_ar_hologram()
    test_steps_49_to_60_silhouette_color_system()
    test_steps_61_to_72_dynamic_focus_dof()
    print("ALL 72 UI/UX STEPS VERIFIED AND PASSED!")
