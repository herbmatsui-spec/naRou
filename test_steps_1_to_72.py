"""Comprehensive Verification Tests for Steps 1 through 72.

Verifies:
- Steps 1-24: Dynamic Audio (footsteps, UI, 3D spatial sound)
- Steps 25-48: Emotes, Interaction prompts, Floating combat feedback
- Steps 49-72: Dynamic lighting, Squash/stretch, Screen shake, Particles & Footprints
"""

from audio.dynamic_audio import (
    ENVIRONMENT_SOUND_PATHS,
    FOOTSTEP_SOUND_PATHS,
    UI_SOUND_PATHS,
    load_footstep_cache,
    play_footstep_sound,
    play_positional_sound,
    play_ui_sound,
)
from emote_feedback_system import (
    EMOTE_PATHS,
    CombatFeedbackManager,
    EmoteComponent,
    InteractableObject,
)
from visual_fx_system import (
    CameraShakeManager,
    EnvironmentFXManager,
    LightingManager,
    LightSource,
    SpriteDeformation,
)


def test_steps_1_to_8_footstep_audio():
    # Step 1 & 2
    assert len(FOOTSTEP_SOUND_PATHS) == 10
    cache = load_footstep_cache()
    assert len(cache) == 10

    # Steps 3-7
    res = play_footstep_sound(volume=0.5)
    assert 0 <= res["index"] < 10
    assert 0.94 <= res["pitch"] <= 1.06
    assert res["volume"] == 0.5


def test_steps_9_to_16_ui_audio():
    assert "bookOpen" in UI_SOUND_PATHS
    assert "cloth1" in UI_SOUND_PATHS
    assert "handleCoins" in UI_SOUND_PATHS
    res = play_ui_sound("bookOpen", volume=0.8)
    assert res["key"] == "bookOpen"
    assert res["volume"] == 0.8


def test_steps_17_to_24_spatial_audio():
    assert "doorOpen" in ENVIRONMENT_SOUND_PATHS
    # Nearby sound
    near = play_positional_sound(
        "doorOpen", source_x=2.0, source_y=0.0, listener_x=0.0, listener_y=0.0, max_distance=10.0
    )
    assert near["volume"] > 0.7
    assert near["pan"] > 0.0  # to the right

    # Far away sound
    far = play_positional_sound(
        "creak", source_x=50.0, source_y=50.0, listener_x=0.0, listener_y=0.0, max_distance=10.0
    )
    assert far["volume"] == 0.0


def test_steps_25_to_32_emotes():
    assert "exclamation" in EMOTE_PATHS
    comp = EmoteComponent()
    comp.set_emote("exclamation", duration=30)
    assert comp.current_emote == "exclamation"
    info = comp.get_render_info(100.0, 100.0)
    assert info is not None
    assert info["emote"] == "exclamation"

    for _ in range(30):
        comp.update()
    assert comp.current_emote is None


def test_steps_33_to_40_interaction_prompts():
    obj = InteractableObject(object_id="chest_1", x=10.0, y=10.0, interaction_radius=3.0)
    # Player far
    assert not obj.check_player_distance(player_x=20.0, player_y=20.0)
    assert obj.get_prompt_render_info(ticks=10) is None

    # Player near
    assert obj.check_player_distance(player_x=11.0, player_y=10.0)
    info = obj.get_prompt_render_info(ticks=15)
    assert info is not None
    assert "render_y" in info


def test_steps_41_to_48_combat_feedback():
    mgr = CombatFeedbackManager()
    normal_fb = mgr.add_hit_feedback(x=50.0, y=50.0, damage=25, is_crit=False)
    crit_fb = mgr.add_hit_feedback(x=50.0, y=50.0, damage=100, is_crit=True)

    assert not normal_fb.is_crit
    assert normal_fb.text == "25"
    assert crit_fb.is_crit
    assert "CRIT" in crit_fb.text
    assert crit_fb.icon == "star"

    assert len(mgr.feedbacks) == 2
    for _ in range(70):
        mgr.update()
    assert len(mgr.feedbacks) == 0


def test_steps_49_to_56_lighting():
    lighting = LightingManager(ambient_darkness=180)
    torch = LightSource(x=100.0, y=100.0, base_radius=50.0, flicker=True)
    lighting.add_light(torch)

    frame = lighting.generate_frame_lighting(player_x=50.0, player_y=50.0, ticks=10)
    assert frame["ambient_alpha"] == 180
    assert len(frame["light_cutouts"]) == 2  # Player light + 1 torch


def test_steps_57_to_64_squash_stretch_and_shake():
    cam = CameraShakeManager()
    cam.trigger_shake(duration=5, magnitude=4.0)
    ox, oy = cam.update()
    assert cam.shake_duration == 4

    sprite = SpriteDeformation()
    sprite.on_windup()
    assert sprite.scale_y > 1.0  # stretch
    sprite.on_impact()
    assert sprite.scale_x > 1.0  # squash
    sprite.update(recovery_rate=0.5)


def test_steps_65_to_72_particles_and_footprints():
    env = EnvironmentFXManager()
    env.on_character_step(x=10.0, y=10.0, terrain_type="snow")
    assert len(env.footprints) == 1

    env.spawn_ambient_dust(640, 480)
    env.update(640, 480)


if __name__ == "__main__":
    test_steps_1_to_8_footstep_audio()
    test_steps_9_to_16_ui_audio()
    test_steps_17_to_24_spatial_audio()
    test_steps_25_to_32_emotes()
    test_steps_33_to_40_interaction_prompts()
    test_steps_41_to_48_combat_feedback()
    test_steps_49_to_56_lighting()
    test_steps_57_to_64_squash_stretch_and_shake()
    test_steps_65_to_72_particles_and_footprints()
    print("ALL 72 STEPS VERIFICATION TESTS PASSED SUCCESSFULLY!")
