"""Coverage tests for skill_eater_slum_map (SlumMapManager / HuskNPC)."""

from __future__ import annotations

import pytest

from skill_eater_slum_map import HuskNPC, SlumMapManager


@pytest.fixture
def mgr() -> SlumMapManager:
    return SlumMapManager()


class TestHuskNPC:
    def test_defaults(self) -> None:
        npc = HuskNPC(
            npc_id="X1",
            name="n",
            pos=(0, 0),
            memory_key="K",
            memory_text="t",
            unlocked_secret_type="LORE",
            secret_value="v",
        )
        assert npc.is_extracted is False
        assert npc.pos == (0, 0)


class TestPopulate:
    def test_two_husks_created(self, mgr: SlumMapManager) -> None:
        assert len(mgr.husks) == 2
        ids = [h.npc_id for h in mgr.husks]
        assert ids == ["HUSK_01", "HUSK_02"]

    def test_repopulate_resets_extraction(self, mgr: SlumMapManager) -> None:
        mgr.extract_memory_data("HUSK_01")
        mgr.populate_slum_husks()
        assert all(not h.is_extracted for h in mgr.husks)
        assert len(mgr.husks) == 2


class TestAnalyzeHusk:
    def test_analyze_known_husk(self, mgr: SlumMapManager) -> None:
        res = mgr.analyze_husk("HUSK_01")
        assert res["success"] is True
        assert res["detectable_memory"] is True
        assert res["target_name"] == "元査定係の老人"
        assert "記憶抽出可能" in res["prompt"]

    def test_analyze_already_extracted(self, mgr: SlumMapManager) -> None:
        mgr.extract_memory_data("HUSK_01")
        res = mgr.analyze_husk("HUSK_01")
        assert res["success"] is False
        assert res["error"] == "ALREADY_EXTRACTED"

    def test_analyze_unknown_husk(self, mgr: SlumMapManager) -> None:
        res = mgr.analyze_husk("NOPE")
        assert res == {"success": False, "error": "NPC_NOT_FOUND"}


class TestExtractMemoryData:
    def test_extract_safe_code_husk(self, mgr: SlumMapManager) -> None:
        res = mgr.extract_memory_data("HUSK_01")
        assert res["success"] is True
        assert res["memory_key"] == "SAFE_PASSWORD_MIDAS_SLUM"
        assert res["secret_type"] == "SAFE_CODE"
        assert res["secret_value"] == "4989"
        assert mgr.discovered_secrets["SAFE_PASSWORD_MIDAS_SLUM"] == "4989"
        assert mgr.journal_log[-1]["key"] == "SAFE_PASSWORD_MIDAS_SLUM"
        # SAFE_CODE はルート解放をしない
        assert mgr.unlocked_routes == []

    def test_extract_secret_route_husk_unlocks_route(self, mgr: SlumMapManager) -> None:
        res = mgr.extract_memory_data("HUSK_02")
        assert res["secret_type"] == "SECRET_ROUTE"
        assert "TUNNEL_SEWER_MARKET" in mgr.unlocked_routes
        assert mgr.check_route_access("TUNNEL_SEWER_MARKET") is True

    def test_extract_twice_fails(self, mgr: SlumMapManager) -> None:
        first = mgr.extract_memory_data("HUSK_01")
        assert first["success"] is True
        second = mgr.extract_memory_data("HUSK_01")
        assert second == {"success": False, "error": "ALREADY_EXTRACTED"}

    def test_extract_unknown_husk(self, mgr: SlumMapManager) -> None:
        res = mgr.extract_memory_data("NOPE")
        assert res == {"success": False, "error": "NPC_NOT_FOUND"}


class TestHiddenSafe:
    def test_correct_code_opens_safe(self, mgr: SlumMapManager) -> None:
        res = mgr.unlock_slum_hidden_safe("4989")
        assert res["success"] is True
        assert res["reward_gold"] == 1200
        assert res["reward_item"] == "RARE_SCRAP_METEOR_FRAGMENT"

    def test_wrong_code_rejected(self, mgr: SlumMapManager) -> None:
        res = mgr.unlock_slum_hidden_safe("0000")
        assert res["success"] is False
        assert res["error"] == "WRONG_CODE"

    def test_default_code_fallback_before_extraction(self, mgr: SlumMapManager) -> None:
        # discovered_secrets が空でも 4989 がフォールバックとして使われる
        assert mgr.discovered_secrets == {}
        res = mgr.unlock_slum_hidden_safe("4989")
        assert res["success"] is True


class TestRouteAccessAndFX:
    def test_route_not_unlocked_by_default(self, mgr: SlumMapManager) -> None:
        assert mgr.check_route_access("TUNNEL_SEWER_MARKET") is False

    def test_presentation_fx_config(self, mgr: SlumMapManager) -> None:
        fx = mgr.get_extraction_presentation_fx()
        assert fx["sound"] == "se_memory_glitch_extract.ogg"
        assert fx["duration_ms"] == 1200
        assert fx["screen_effect"] == "CRT_WARP_DISTORTION"
        assert "particles" in fx
