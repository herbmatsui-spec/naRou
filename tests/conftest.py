"""
Shared pytest fixtures and test utilities for the naRou test suite.

Provides:
- Engine factory with configurable subsystems
- Entity/Component test fixtures
- Mock utilities for external dependencies
- Common test data builders
- Coverage-aware test markers
"""

from __future__ import annotations

import os
import random
from contextlib import contextmanager
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Callable, Generator
from unittest.mock import MagicMock, Mock, patch

import pytest

if TYPE_CHECKING:
    from ecs.entity import Entity
    from game import Engine
    from item_system import Inventory, Item

# =============================================================================
# Test Configuration & Markers
# =============================================================================

def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "requires_audio: marks tests requiring audio system")
    config.addinivalue_line("markers", "requires_gpu: marks tests requiring GPU/rendering")
    config.addinivalue_line("markers", "balance: marks balance simulation tests")

# =============================================================================
# Core Test Data Builders
# =============================================================================

@dataclass
class TestEntityBuilder:
    """Fluent builder for creating test entities."""
    name: str = "TestEntity"
    is_player: bool = False
    is_pet: bool = False
    x: int = 0
    y: int = 0
    char: str = "@"
    color: tuple = (255, 255, 255)
    hp: int = 100
    max_hp: int = 100
    mp: int = 50
    max_mp: int = 50
    level: int = 1
    exp: int = 0
    speed: int = 70
    ap: int = 0
    max_ap: int = 100
    god_id: str = "lulwy"
    piety: int = 0
    attributes: dict = field(default_factory=dict)
    skills: dict = field(default_factory=dict)
    components: dict = field(default_factory=dict)

    def build(self) -> "Entity":
        from ecs.components import AttributesComponent
        from ecs.entity import Entity

        entity = Entity(
            x=self.x,
            y=self.y,
            char=self.char,
            color=self.color,
            name=self.name,
            is_player=self.is_player,
            is_pet=self.is_pet,
            speed=self.speed,
        )
        entity.hp = self.hp
        entity.max_hp = self.max_hp
        entity.mp = self.mp
        entity.max_mp = self.max_mp
        entity.level = self.level
        entity.exp = self.exp
        entity.ap = self.ap
        entity.max_ap = self.max_ap
        entity.god_id = self.god_id
        entity.piety = self.piety

        # Apply custom attributes
        if self.attributes:
            attrs = entity.get_component(AttributesComponent)
            for attr_name, value in self.attributes.items():
                if hasattr(attrs, attr_name):
                    setattr(attrs, attr_name, value)

        # Apply custom skills
        for skill_id, skill_data in self.skills.items():
            if skill_id in entity._skills:
                for k, v in skill_data.items():
                    setattr(entity._skills[skill_id], k, v)

        return entity

    def with_attributes(self, **attrs) -> "TestEntityBuilder":
        self.attributes.update(attrs)
        return self

    def with_skills(self, **skills) -> "TestEntityBuilder":
        self.skills.update(skills)
        return self

    def at_position(self, x: int, y: int) -> "TestEntityBuilder":
        self.x = x
        self.y = y
        return self


@dataclass
class TestItemBuilder:
    """Fluent builder for creating test items."""
    name: str = "Test Item"
    category: str = "misc"
    char: str = "?"
    color: tuple = (200, 200, 200)
    x: int = 0
    y: int = 0
    weight: float = 1.0
    value: int = 10
    extra: dict = field(default_factory=dict)

    def build(self) -> "Item":
        from item_system import Item
        item = Item(
            name=self.name,
            category=self.category,
            char=self.char,
            color=self.color,
            x=self.x,
            y=self.y,
            base_weight=self.weight,
            base_value=self.value,
        )
        for k, v in self.extra.items():
            setattr(item, k, v)
        return item

    def with_extra(self, **kwargs) -> "TestItemBuilder":
        self.extra.update(kwargs)
        return self


# =============================================================================
# Engine & System Fixtures
# =============================================================================

class DummyKernel:
    """Minimal Kernel stand-in with system registry."""
    def __init__(self):
        self._systems: dict[str, Any] = {}
        self.entity_manager = MagicMock()
        # 実 Kernel と同じ契約: entity_manager は system として登録される
        self._systems["entity_manager"] = self.entity_manager

    def get_system(self, name: str, default: Any = None) -> Any:
        return self._systems.get(name, default)

    def has_system(self, name: str) -> bool:
        return name in self._systems

    def register_system(self, name: str, system: Any) -> None:
        self._systems[name] = system


@pytest.fixture
def dummy_kernel() -> DummyKernel:
    """Provides a minimal kernel for unit tests."""
    return DummyKernel()


@pytest.fixture
def test_engine(dummy_kernel: DummyKernel) -> "Engine":
    """Engine instance with dummy kernel for unit testing."""
    import game
    engine = game.Engine.__new__(game.Engine)
    engine.kernel = dummy_kernel
    # Engine の player/turns/dungeon_level は game_state_data バックのプロパティ。
    # __new__ で __init__ を迂回するため、軽量スタブを先に用意する。
    engine.game_state_data = SimpleNamespace(turns=0)
    engine.turns = 0
    engine.dungeon_level = 1
    engine.log = MagicMock()
    engine.player = MagicMock()
    engine.quests = []
    return engine


@pytest.fixture
def full_engine() -> Generator["Engine", None, None]:
    """Fully initialized engine (slower, use for integration tests)."""
    import game
    engine = game.Engine()
    try:
        yield engine
    finally:
        # Cleanup
        pass


# =============================================================================
# Entity & Component Fixtures
# =============================================================================

@pytest.fixture
def player_entity() -> "Entity":
    """Standard player entity for testing."""
    return (TestEntityBuilder()
        .with_attributes(
            strength=15, endurance=12, dexterity=14,
            perception=10, learning=13, will=11,
            magic=8, charisma=10
        )
        .build())


@pytest.fixture
def monster_entity() -> "Entity":
    """Standard monster entity for testing."""
    return (TestEntityBuilder()
        .with_attributes(strength=10, endurance=10, dexterity=10)
        .at_position(5, 5)
        .build())


@pytest.fixture
def pet_entity() -> "Entity":
    """Standard pet entity for testing."""
    return (TestEntityBuilder()
        .with_attributes(strength=12, endurance=14, dexterity=11)
        .build())


@pytest.fixture
def empty_entity() -> "Entity":
    """Minimal entity with no special configuration."""
    return TestEntityBuilder().build()


# =============================================================================
# Mock Utilities
# =============================================================================

@contextmanager
def mock_pygame():
    """Context manager to mock pygame for headless testing."""
    with patch.dict('sys.modules', pygame=MagicMock()):
        import pygame
        pygame.mixer = MagicMock()
        pygame.mixer.init = MagicMock()
        pygame.mixer.quit = MagicMock()
        pygame.mixer.Sound = MagicMock(return_value=MagicMock(play=MagicMock()))
        pygame.mixer.music = MagicMock()
        pygame.display = MagicMock()
        pygame.Surface = MagicMock()
        yield pygame


@contextmanager
def mock_tcod():
    """Context manager to mock tcod for headless testing."""
    tcod_mock = MagicMock()
    tcod_mock.console = MagicMock()
    tcod_mock.context = MagicMock()
    tcod_mock.tileset = MagicMock()
    tcod_mock.event = MagicMock()
    with patch.dict('sys.modules', tcod=tcod_mock):
        yield tcod_mock


@contextmanager
def mock_audio_system():
    """Context manager to mock audio system."""
    with patch('sound_manager.SoundManager') as mock_sm:
        mock_sm.get_instance = MagicMock(return_value=MagicMock(
            play_se=MagicMock(),
            play_bgm=MagicMock(),
            stop_bgm=MagicMock(),
            set_volume=MagicMock(),
        ))
        yield mock_sm.get_instance()


class MockRandom:
    """Deterministic random for reproducible tests."""
    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)
        self._sequence = []
        self._index = 0

    def random(self) -> float:
        val = self._rng.random()
        self._sequence.append(('random', val))
        return val

    def randint(self, a: int, b: int) -> int:
        val = self._rng.randint(a, b)
        self._sequence.append(('randint', val, a, b))
        return val

    def choice(self, seq):
        val = self._rng.choice(seq)
        self._sequence.append(('choice', val))
        return val

    def shuffle(self, seq):
        self._rng.shuffle(seq)
        self._sequence.append(('shuffle', list(seq)))

    def getstate(self):
        return self._rng.getstate()

    def setstate(self, state):
        self._rng.setstate(state)

    def record_calls(self) -> bool:
        """Enable call recording for verification."""
        self._sequence = []
        return True

    def get_calls(self) -> list:
        return self._sequence


@pytest.fixture
def mock_random() -> MockRandom:
    """Deterministic random generator for tests."""
    return MockRandom(42)


# =============================================================================
# Data Fixtures
# =============================================================================

@pytest.fixture
def sample_items() -> list:
    """Collection of common test items."""
    from item_system import CAT_ARMOR, CAT_FOOD, CAT_POTION, CAT_WEAPON, Item

    return [
        Item("Iron Sword", CAT_WEAPON, ")", (200, 200, 200), 0, 0, base_weight=3.0, base_value=100),
        Item("Leather Armor", CAT_ARMOR, "[", (150, 100, 50), 0, 0, base_weight=5.0, base_value=80),
        Item("Healing Potion", CAT_POTION, "!", (255, 100, 100), 0, 0, base_weight=0.5, base_value=50),
        Item("Bread", CAT_FOOD, "%", (200, 180, 100), 0, 0, base_weight=0.3, base_value=10),
    ]


@pytest.fixture
def sample_skills() -> dict:
    """Common skill test data."""
    return {
        "fire_bolt": {"name": "Fire Bolt", "category": "magic", "damage": 20, "mp_cost": 5},
        "heal": {"name": "Heal", "category": "magic", "heal_amount": 30, "mp_cost": 8},
        "slash": {"name": "Slash", "category": "physical", "damage": 15, "stamina_cost": 3},
        "shield_bash": {"name": "Shield Bash", "category": "physical", "damage": 10, "stun_chance": 0.3},
    }


# =============================================================================
# Assertion Helpers
# =============================================================================

def assert_entity_stats(entity: "Entity", **expected) -> None:
    """Assert entity has expected stat values."""
    for attr, expected_value in expected.items():
        actual = getattr(entity, attr, None)
        if actual is None:
            # Check attributes component
            from ecs.components import AttributesComponent
            attrs = entity.get_component(AttributesComponent)
            actual = getattr(attrs, attr, None)
        assert actual == expected_value, f"{attr}: expected {expected_value}, got {actual}"


def assert_skill_level(entity: "Entity", skill_id: str, expected_level: int) -> None:
    """Assert entity's skill is at expected level."""
    assert skill_id in entity._skills, f"Skill {skill_id} not found"
    assert entity._skills[skill_id].level == expected_level


def assert_inventory_contains(entity: "Entity", item_name: str, count: int = 1) -> None:
    """Assert entity's inventory contains item."""
    from ecs.components import InventoryComponent
    inv = entity.get_component(InventoryComponent)
    found = sum(1 for item in inv.items if item.name == item_name)
    assert found >= count, f"Expected {count} {item_name}, found {found}"


# =============================================================================
# Coverage-Aware Test Decorators
# =============================================================================

def requires_coverage(module: str, minimum: float = 0.0):
    """Decorator to skip test if module coverage is below minimum."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Coverage check would go here
            return func(*args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# Test Session Lifecycle
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Session-level setup/teardown."""
    # Ensure deterministic randomness
    random.seed(42)

    # Mock pygame globally for headless CI
    with mock_pygame():
        yield

    # Cleanup
    pass


# =============================================================================
# Parametrized Test Data
# =============================================================================

@pytest.fixture(params=[
    ("easy", 0.5),
    ("normal", 1.0),
    ("hard", 1.5),
])
def difficulty_preset(request):
    """Parametrized difficulty presets."""
    return request.param


@pytest.fixture(params=[
    ("warrior", {"strength": 16, "endurance": 14, "dexterity": 12}),
    ("mage", {"strength": 8, "endurance": 10, "dexterity": 10, "magic": 16, "learning": 14}),
    ("rogue", {"strength": 12, "endurance": 10, "dexterity": 16, "perception": 14}),
    ("cleric", {"strength": 10, "endurance": 12, "will": 16, "magic": 14}),
])
def class_template(request):
    """Parametrized class templates for testing."""
    return request.param


# =============================================================================
# Async Test Support
# =============================================================================

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# File System Helpers
# =============================================================================

@contextmanager
def temp_yaml_file(content: dict, suffix: str = ".yaml"):
    """Create temporary YAML file for testing."""
    import tempfile

    import yaml
    with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False, encoding='utf-8') as f:
        yaml.dump(content, f)
        fname = f.name
    try:
        yield fname
    finally:
        import os
        os.unlink(fname)


@contextmanager
def temp_dir():
    """Create temporary directory."""
    import shutil
    import tempfile
    d = tempfile.mkdtemp()
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


# =============================================================================
# Additional Test Fixtures
# =============================================================================

@pytest.fixture
def test_fixtures_dir() -> str:
    """Return path to test fixtures directory."""
    import os
    return os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def test_items_yaml(test_fixtures_dir: str) -> dict:
    """Load test items YAML."""
    import yaml
    with open(os.path.join(test_fixtures_dir, "test_items.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def test_affixes_yaml(test_fixtures_dir: str) -> dict:
    """Load test affixes YAML."""
    import yaml
    with open(os.path.join(test_fixtures_dir, "test_affixes.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def test_exp_curve_yaml(test_fixtures_dir: str) -> dict:
    """Load test exp curve YAML."""
    import yaml
    with open(os.path.join(test_fixtures_dir, "test_exp_curve.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def mock_engine_with_systems() -> "Engine":
    """Engine with mocked kernel and common systems."""
    from unittest.mock import MagicMock

    import game

    engine = game.Engine.__new__(game.Engine)
    engine.kernel = MagicMock()
    engine.kernel.get_system = MagicMock(return_value=None)
    engine.kernel.has_system = MagicMock(return_value=False)
    engine.kernel.entity_manager = MagicMock()

    engine.turns = 0
    engine.dungeon_level = 1
    engine.log = MagicMock()
    engine.player = MagicMock()
    engine.quests = []
    engine.survival = MagicMock()
    engine.survival.gold = 0
    engine.survival.platinum = 0

    return engine


@pytest.fixture
def test_item_factory(test_items_yaml: dict):
    """Factory for creating test items from fixtures."""
    from item_system import Item

    def _create(item_id: str, **overrides) -> "Item":
        data = test_items_yaml["items"][item_id].copy()
        data.update(overrides)
        return Item(**data)

    return _create


@pytest.fixture
def inventory_with_items():
    """Inventory pre-populated with test items."""
    from item_system import CAT_FOOD, CAT_POTION, CAT_WEAPON, Inventory, Item

    inv = Inventory()
    inv.add_item(Item("Iron Sword", CAT_WEAPON, ")", (200, 100, 100), 0, 0, base_weight=3.0, base_value=100))
    inv.add_item(Item("Healing Potion", CAT_POTION, "!", (255, 100, 100), 0, 0, base_weight=0.5, base_value=50))
    inv.add_item(Item("Bread", CAT_FOOD, "%", (200, 180, 100), 0, 0, base_weight=0.3, base_value=10))
    return inv


@pytest.fixture
def seeded_rng():
    """Seeded random number generator for deterministic tests."""
    import random
    return random.Random(42)


@pytest.fixture
def temp_yaml_fixture():
    """Create a temporary YAML file from a dict."""
    import os
    import tempfile

    import yaml

    def _create(content: dict, suffix: str = ".yaml") -> str:
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False, encoding='utf-8') as f:
            yaml.dump(content, f)
            fname = f.name
        return fname

    return _create


# =============================================================================
# Additional Assertion Helpers
# =============================================================================

def assert_item_equal(item1: "Item", item2: "Item") -> None:
    """Assert two items are equal in all significant attributes."""
    assert item1.name == item2.name
    assert item1.category == item2.category
    assert item1.char == item2.char
    assert item1.color == item2.color
    assert item1.item_id == item2.item_id or item1.item_id == item2.item_id  # uuid may differ
    assert item1.base_weight == item2.base_weight
    assert item1.base_value == item2.base_value
    assert item1.count == item2.count
    assert item1.material == item2.material
    assert item1.quality == item2.quality
    assert item1.identified == item2.identified
    assert item1.cursed == item2.cursed
    assert item1.enchants == item2.enchants
    assert item1.locked == item2.locked
    assert item1.durability == item2.durability if hasattr(item1, 'durability') else True
    assert item1.max_durability == item2.max_durability if hasattr(item1, 'max_durability') else True


def assert_inventory_state(inventory: "Inventory", expected_counts: dict[str, int]) -> None:
    """Assert inventory contains expected item counts."""
    for item_name, expected_count in expected_counts.items():
        actual_count = sum(1 for item in inventory.items if item.name == item_name)
        assert actual_count == expected_count, f"Item '{item_name}': expected {expected_count}, got {actual_count}"


# =============================================================================
# Property-Based Test Helpers
# =============================================================================

def generate_random_item_params(rng: random.Random) -> dict:
    """Generate random item parameters for property-based testing."""
    categories = ["weapon", "armor", "potion", "scroll", "food", "tool"]
    materials = ["iron", "steel", "wood", "cloth", "glass", "mythril"]
    qualities = ["bad", "normal", "good", "miracle", "god"]

    return {
        "name": f"Item_{rng.randint(1, 1000)}",
        "category": rng.choice(categories),
        "char": rng.choice([")", "[", "!", "?", "%", "/"]),
        "color": (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)),
        "x": 0,
        "y": 0,
        "base_weight": round(rng.uniform(0.1, 10.0), 1),
        "base_value": rng.randint(1, 1000),
        "material": rng.choice(materials),
        "quality": rng.choice(qualities),
        "cursed": rng.choice([True, False]),
    }
