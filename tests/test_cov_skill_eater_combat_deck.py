"""Coverage tests for skill_eater_combat_deck (CombatDeckSystem)."""

from __future__ import annotations

import pytest

from skill_eater_combat_deck import CombatDeckSystem


@pytest.fixture
def deck() -> CombatDeckSystem:
    return CombatDeckSystem(["fire", "ice", "bolt", "heal", "shield", "dash"])


class TestInit:
    def test_piles_initial_state(self, deck: CombatDeckSystem) -> None:
        assert sorted(deck.draw_pile) == sorted(["fire", "ice", "bolt", "heal", "shield", "dash"])
        assert deck.discard_pile == []
        assert deck.hand == []
        assert deck.hand_limit == 4
        assert deck.mana == 3
        assert deck.max_mana == 3
        assert deck.fatigue_damage == 0

    def test_shuffle_preserves_cards(self) -> None:
        d1 = CombatDeckSystem(["a", "b", "c"])
        d2 = CombatDeckSystem(["a", "b", "c"])
        assert sorted(d1.draw_pile) == ["a", "b", "c"]
        assert sorted(d2.draw_pile) == ["a", "b", "c"]


class TestStartTurn:
    def test_draw_fills_hand(self, deck: CombatDeckSystem) -> None:
        res = deck.start_turn()
        assert len(res["hand"]) == 4
        assert len(res["drawn_cards"]) == 4
        assert res["hand"] == deck.hand
        assert res["current_mana"] == 3
        assert res["draw_pile_count"] == 2
        assert res["discard_pile_count"] == 0
        assert res["fatigue_damage_taken"] == 0

    def test_mana_refills_each_turn(self, deck: CombatDeckSystem) -> None:
        deck.start_turn()
        deck.mana = 0
        res = deck.start_turn()
        assert res["current_mana"] == 3

    def test_hand_limit_blocks_overdraw(self, deck: CombatDeckSystem) -> None:
        deck.start_turn()  # hand = 4
        res = deck.start_turn()
        assert res["drawn_cards"] == []
        assert len(res["hand"]) == 4

    def test_custom_draw_count(self, deck: CombatDeckSystem) -> None:
        res = deck.start_turn(draw_count=2)
        assert len(res["drawn_cards"]) == 2
        assert res["draw_pile_count"] == 4

    def test_empty_deck_reloads_with_fatigue(self, deck: CombatDeckSystem) -> None:
        deck.start_turn()  # hand 4, pile 2
        deck.discard_pile = deck.hand[:]
        deck.hand = []
        res = deck.start_turn()  # draw 2 from pile, then reload 4-card discard
        assert res["fatigue_damage_taken"] == 5
        assert deck.fatigue_damage == 5
        assert len(res["hand"]) == 4
        assert res["draw_pile_count"] == 2  # 4 reloaded, 2 drawn

        # Second reload: fatigue accumulates 5 → 10
        deck.discard_pile = deck.hand[:]
        deck.hand = []
        deck.draw_pile = []
        res = deck.start_turn()
        assert res["fatigue_damage_taken"] == 10
        assert deck.fatigue_damage == 10

    def test_no_cards_anywhere_breaks_out(self, deck: CombatDeckSystem) -> None:
        deck.draw_pile = []
        res = deck.start_turn()
        assert res["drawn_cards"] == []
        assert res["hand"] == []
        assert res["fatigue_damage_taken"] == 0


class TestInstantSynthesize:
    def test_requires_both_in_hand(self, deck: CombatDeckSystem) -> None:
        deck.hand = ["fire"]
        res = deck.instant_synthesize("fire", "ice")
        assert res["success"] is False
        assert "must be in hand" in res["message"]

    def test_same_card_without_duplicate_rejected(self, deck: CombatDeckSystem) -> None:
        deck.hand = ["fire"]
        res = deck.instant_synthesize("fire", "fire")
        assert res["success"] is False
        assert "duplicate" in res["message"]

    def test_same_card_with_duplicate_allowed(self, deck: CombatDeckSystem) -> None:
        deck.hand = ["fire", "fire"]
        res = deck.instant_synthesize("fire", "fire")
        assert res["success"] is True
        assert deck.hand == ["Instant Fusion: [fire + fire]"]

    def test_fusion_replaces_both_cards(self, deck: CombatDeckSystem) -> None:
        deck.hand = ["fire", "ice", "bolt"]
        res = deck.instant_synthesize("fire", "ice")
        assert res["success"] is True
        assert res["fused_skill"] == "Instant Fusion: [fire + ice]"
        assert deck.hand == ["bolt", "Instant Fusion: [fire + ice]"]
        assert "Synthesized" in res["message"]


class TestDiscardForMana:
    def test_discard_not_in_hand(self, deck: CombatDeckSystem) -> None:
        res = deck.discard_for_mana("nope")
        assert res["success"] is False
        assert res["message"] == "Skill not in hand."

    def test_discard_grants_mana(self, deck: CombatDeckSystem) -> None:
        deck.hand = ["fire", "ice"]
        deck.mana = 1
        res = deck.discard_for_mana("fire")
        assert res["success"] is True
        assert res["discarded"] == "fire"
        assert res["current_mana"] == 2
        assert deck.hand == ["ice"]
        assert deck.discard_pile == ["fire"]
        assert res["message"] == "Discarded [fire] for +1 Mana."


class TestExecuteSkillAttack:
    def test_skill_not_in_hand(self, deck: CombatDeckSystem) -> None:
        res = deck.execute_skill_attack("nope")
        assert res["success"] is False

    def test_not_enough_mana(self, deck: CombatDeckSystem) -> None:
        deck.hand = ["fire"]
        deck.mana = 0
        res = deck.execute_skill_attack("fire", mana_cost=1)
        assert res["success"] is False
        assert res["message"] == "Not enough mana."
        assert deck.hand == ["fire"]

    def test_normal_attack_moves_card_to_discard(self, deck: CombatDeckSystem) -> None:
        deck.hand = ["fire", "ice"]
        res = deck.execute_skill_attack("fire", base_power=100, mana_cost=1)
        assert res["success"] is True
        assert res["skill_used"] == "fire"
        assert res["damage_dealt"] == 100
        assert res["remaining_mana"] == 2
        assert deck.hand == ["ice"]
        assert deck.discard_pile == ["fire"]
        assert res["message"] == "Executed [fire] dealing 100 damage!"

    def test_instant_fusion_multiplies_damage(self, deck: CombatDeckSystem) -> None:
        deck.hand = ["Instant Fusion: [fire + ice]"]
        res = deck.execute_skill_attack("Instant Fusion: [fire + ice]", base_power=100)
        assert res["damage_dealt"] == 250

    def test_high_mana_cost_rejected(self, deck: CombatDeckSystem) -> None:
        deck.hand = ["big"]
        deck.mana = 2
        res = deck.execute_skill_attack("big", mana_cost=3)
        assert res["success"] is False


class TestEnemyIntent:
    def test_intent_cycles_by_turn(self, deck: CombatDeckSystem) -> None:
        t1 = deck.get_enemy_intent(1)
        t2 = deck.get_enemy_intent(2)
        t3 = deck.get_enemy_intent(3)
        t4 = deck.get_enemy_intent(4)
        assert t1["action"] == "ATTACK"
        assert t2["action"] == "DEFEND"
        assert t3["action"] == "SPECIAL"
        assert t4 == t1
        assert t1["power"] == 120
        assert t3["power"] == 250

    def test_turn_zero_wraps_to_special(self, deck: CombatDeckSystem) -> None:
        assert deck.get_enemy_intent(0)["action"] == "SPECIAL"
