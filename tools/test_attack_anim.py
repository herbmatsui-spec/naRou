#!/usr/bin/env python3
"""
Attack animation synchronization test.
Verifies that server attack_timer -> client 0.5s attack animation -> auto idle return works correctly.
"""

from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.tile_atlas import TileAtlas
from core.entity_renderer import EntityRenderer


def test_attack_animation_sync():
    """Test attack animation synchronization between server and client."""
    print("=" * 60)
    print("Attack Animation Sync Test")
    print("=" * 60)
    
    atlas = TileAtlas()
    renderer = EntityRenderer(atlas)
    
    # Register a test entity
    eid = renderer.register_entity("PLAYER", 10, 10, direction=0, state="idle")
    anim = renderer.entity_anims[eid]
    
    all_passed = True
    
    # Test 1: Server sends attack_timer=0.5 -> Client plays attack for 0.5s -> returns to idle
    print("\nTest 1: Full attack cycle (server attack_timer -> client animation)")
    renderer.update_entity(eid, 10, 10, direction=0, state="attack", is_attacking=True, dt=1/60)
    print(f"  After attack trigger: state={anim.state}, attack_timer={anim.attack_timer:.2f}, loop={anim.loop}")
    
    # Simulate 0.51s (31 frames at 60fps)
    for i in range(31):
        renderer.update_entity(eid, 10, 10, direction=0, state="attack", is_attacking=False, dt=1/60)
    
    print(f"  After 0.51s: state={anim.state}, attack_timer={anim.attack_timer:.4f}, loop={anim.loop}")
    
    if anim.state == "idle" and anim.loop:
        print("  PASS: Attack animation completed and returned to idle")
    else:
        print("  FAIL: Attack animation did not complete properly")
        all_passed = False
    
    # Test 2: Rapid attack triggers (should not stack)
    print("\nTest 2: Rapid attack triggers (no stacking)")
    renderer.update_entity(eid, 10, 10, direction=0, state="attack", is_attacking=True, dt=1/60)
    print(f"  After attack trigger: state={anim.state}, attack_timer={anim.attack_timer:.2f}")
    
    # Immediately trigger again (simulating double-click)
    renderer.update_entity(eid, 10, 10, direction=0, state="attack", is_attacking=True, dt=1/60)
    print(f"  After immediate re-trigger: state={anim.state}, attack_timer={anim.attack_timer:.2f}")
    
    # Should reset to 0.5, not add
    if abs(anim.attack_timer - 0.5) < 0.01:
        print("  PASS: Attack timer reset to 0.5 (no stacking)")
    else:
        print("  FAIL: Attack timer stacked incorrectly")
        all_passed = False
    
    # Test 3: Attack interrupted by movement
    print("\nTest 3: Attack interrupted by movement (state change)")
    renderer.update_entity(eid, 10, 10, direction=0, state="attack", is_attacking=True, dt=1/60)
    print(f"  After attack trigger: state={anim.state}, attack_timer={anim.attack_timer:.2f}")
    
    # Server sends walk state (movement) before attack completes
    # While attack_timer > 0, state should remain "attack" regardless of new_state
    for i in range(10):  # ~0.17s
        renderer.update_entity(eid, 10, 10, direction=0, state="walk", is_attacking=False, dt=1/60)
    
    print(f"  After 0.17s walk: state={anim.state}, attack_timer={anim.attack_timer:.4f}")
    
    # Attack timer should still be counting down but state remains "attack"
    if anim.state == "attack" and anim.attack_timer > 0:
        print("  PASS: Attack state maintained while timer > 0, timer continues counting down")
    else:
        print("  FAIL: Attack state should be maintained while timer > 0")
        all_passed = False
    
    # Test 4: Death during attack
    print("\nTest 4: Death during attack")
    eid2 = renderer.register_entity("ENEMY_GOBLIN", 5, 5, state="idle")
    anim2 = renderer.entity_anims[eid2]
    
    renderer.update_entity(eid2, 5, 5, direction=0, state="attack", is_attacking=True, dt=1/60)
    print(f"  After attack trigger: state={anim2.state}")
    
    # Server sends dead state
    renderer.update_entity(eid2, 5, 5, direction=0, state="dead", is_attacking=False, dt=1/60)
    print(f"  After death: state={anim2.state}, loop={anim2.loop}")
    
    if anim2.state == "dead" and not anim2.loop:
        print("  PASS: Death state overrides attack")
    else:
        print("  FAIL: Death state should override attack")
        all_passed = False
    
    # Test 5: Facing direction during attack
    print("\nTest 5: Facing direction during attack")
    eid3 = renderer.register_entity("PLAYER", 10, 10, direction=0, state="idle")
    anim3 = renderer.entity_anims[eid3]
    
    # Attack while facing right
    renderer.update_entity(eid3, 10, 10, direction=2, state="attack", is_attacking=True, dt=1/60)
    print(f"  Attack facing right: direction={anim3.direction}")
    
    # Attack while facing up
    renderer.update_entity(eid3, 10, 10, direction=3, state="attack", is_attacking=True, dt=1/60)
    print(f"  Attack facing up: direction={anim3.direction}")
    
    if anim3.direction == 3:
        print("  PASS: Facing direction updated during attack")
    else:
        print("  FAIL: Facing direction should update during attack")
        all_passed = False
    
# Test 6: Web-side attack timer simulation
    print("\nTest 6: Web-side attack timer simulation (client-side)")
    # Simulate web client with local attack timer
    attack_timer = 0.0
    state = "idle"
    
    def web_update(dt, server_state, server_attack_timer):
        nonlocal attack_timer, state
        # Server sends attack_timer > 0 -> client starts local timer
        if server_attack_timer > 0:
            attack_timer = server_attack_timer
        # Client counts down local timer
        if attack_timer > 0:
            attack_timer -= dt
            state = "attack"
            if attack_timer <= 0:
                state = "idle"
        elif state == "idle":
            # Timer expired and we're in idle, follow server state
            state = server_state
        else:
            # Still in attack but timer expired (edge case)
            state = "idle"
        return state
    
    # Simulate server sending attack_timer
    state = web_update(1/60, "idle", 0.5)  # Server sends attack_timer=0.5
    print(f"  Frame 1: state={state}, attack_timer={attack_timer:.4f}")
    
    # Server sends "attack" while timer > 0, then "idle" after timer expires
    for i in range(31):
        # Server sends "attack" for first 30 frames, then "idle"
        server_state = "attack" if i < 30 else "idle"
        state = web_update(1/60, server_state, 0)
        if i == 30:
            print(f"  Frame 32: state={state}, attack_timer={attack_timer:.4f}")
    
    if state == "idle":
        print("  PASS: Web-side timer correctly returns to idle")
    else:
        print("  FAIL: Web-side timer did not return to idle")
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL ATTACK ANIMATION SYNC TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 60)
    
    return all_passed


def main():
    return 0 if test_attack_animation_sync() else 1


if __name__ == "__main__":
    sys.exit(main())