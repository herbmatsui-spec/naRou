"""core/progression_manager のテスト。

システムアンロックフラグコンポーネントと、アンロック状態の
判定・変更を行う関数をカバーする。
正常系・異常系・境界値を含め、パブリック API を網羅的にテストする。
"""

from __future__ import annotations

from core.progression_manager import (
    ProgressionFlagComponent,
    is_unlocked,
    unlock_system,
)


class TestProgressionFlagComponent:
    """ProgressionFlagComponent のテスト。"""

    def test_default_values_are_all_false(self):
        """デフォルトではすべてのフラグが False であること。"""
        flags = ProgressionFlagComponent()
        assert flags.skill_eater is False
        assert flags.base_defense is False
        assert flags.archaeology is False
        assert flags.crafting is False
        assert flags.arena is False

    def test_custom_values(self):
        """指定した値で初期化できること。"""
        flags = ProgressionFlagComponent(
            skill_eater=True,
            base_defense=False,
            archaeology=True,
            crafting=False,
            arena=True,
        )
        assert flags.skill_eater is True
        assert flags.base_defense is False
        assert flags.archaeology is True
        assert flags.crafting is False
        assert flags.arena is True

    def test_to_dict(self):
        """to_dict が辞書を返すこと。"""
        flags = ProgressionFlagComponent(skill_eater=True, arena=True)
        expected = {
            "skill_eater": True,
            "base_defense": False,
            "archaeology": False,
            "crafting": False,
            "arena": True,
        }
        assert flags.to_dict() == expected

    def test_from_dict(self):
        """from_dict で辞書から復元できること。"""
        data = {
            "skill_eater": True,
            "base_defense": True,
            "archaeology": False,
            "crafting": True,
            "arena": False,
        }
        flags = ProgressionFlagComponent.from_dict(data)
        assert flags.skill_eater is True
        assert flags.base_defense is True
        assert flags.archaeology is False
        assert flags.crafting is True
        assert flags.arena is False

    def test_from_dict_missing_keys_default_to_false(self):
        """辞書にキーが欠けていても False で復元されること（境界値）。"""
        flags = ProgressionFlagComponent.from_dict({})
        assert flags.skill_eater is False
        assert flags.base_defense is False
        assert flags.archaeology is False
        assert flags.crafting is False
        assert flags.arena is False

    def test_from_dict_extra_keys_ignored(self):
        """余分なキーがあっても無視されること。"""
        data = {
            "skill_eater": True,
            "unknown_system": True,
        }
        flags = ProgressionFlagComponent.from_dict(data)
        assert flags.skill_eater is True
        assert flags.base_defense is False


class TestIsUnlocked:
    """is_unlocked 関数のテスト。"""

    def test_returns_false_when_locked(self):
        """アンロックされていないシステムは False を返すこと。"""
        flags = ProgressionFlagComponent()
        assert is_unlocked(flags, "skill_eater") is False

    def test_returns_true_when_unlocked(self):
        """アンロック済みシステムは True を返すこと。"""
        flags = ProgressionFlagComponent(skill_eater=True)
        assert is_unlocked(flags, "skill_eater") is True

    def test_unknown_system_returns_false(self):
        """存在しないシステム名では False を返すこと（getattr の既定値）。"""
        flags = ProgressionFlagComponent()
        assert is_unlocked(flags, "nonexistent_system") is False


class TestUnlockSystem:
    """unlock_system 関数のテスト。"""

    def test_unlocks_existing_system(self):
        """存在するシステムをアンロックできること。"""
        flags = ProgressionFlagComponent()
        unlock_system(flags, "archaeology")
        assert flags.archaeology is True

    def test_unknown_system_noop(self):
        """存在しないシステムでは何もしないこと（hasattr でガード）。"""
        flags = ProgressionFlagComponent()
        unlock_system(flags, "nonexistent_system")
        assert flags.skill_eater is False

    def test_unlock_idempotent(self):
        """二度アンロックしても True のままであること。"""
        flags = ProgressionFlagComponent()
        unlock_system(flags, "crafting")
        unlock_system(flags, "crafting")
        assert flags.crafting is True
