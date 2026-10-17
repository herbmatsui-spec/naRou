"""Regression test: スラム金庫は記憶抽出前に開かない (案9バッチ1 bug4).

修正前は unlock_slum_hidden_safe が discovered_secrets に鍵が無くても
フォールバック値 "4989" を正解扱いし、HUSK_01 からの記憶抽出を
省略して金庫を開けられた。
"""

from __future__ import annotations

import pytest

from skill_eater_slum_map import SlumMapManager


@pytest.fixture
def mgr() -> SlumMapManager:
    return SlumMapManager()


class TestBug4SafeRequiresExtraction:
    def test_safe_cannot_be_opened_before_extraction(self, mgr: SlumMapManager) -> None:
        assert mgr.discovered_secrets == {}
        res = mgr.unlock_slum_hidden_safe("4989")
        assert res["success"] is False
        assert res["error"] == "CODE_NOT_DISCOVERED"
        assert "記憶" in res["message"]

    def test_safe_opens_after_extraction_with_extracted_code(
        self, mgr: SlumMapManager
    ) -> None:
        assert mgr.extract_memory_data("HUSK_01")["success"] is True
        res = mgr.unlock_slum_hidden_safe("4989")
        assert res["success"] is True
        assert res["reward_gold"] == 1200
        assert res["reward_item"] == "RARE_SCRAP_METEOR_FRAGMENT"

    def test_wrong_code_after_extraction_rejected(self, mgr: SlumMapManager) -> None:
        mgr.extract_memory_data("HUSK_01")
        res = mgr.unlock_slum_hidden_safe("0000")
        assert res["success"] is False
        assert res["error"] == "WRONG_CODE"
