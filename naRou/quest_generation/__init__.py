"""Quest generation package (split from procedural_quest_generator.py)."""
from .generator import *
from .generator import ProceduralQuestGenerator
from .manager import *
from .manager import ProceduralQuestManager
from .models import *
from .registry import *
from .registry import REGISTRY, QuestGenerationRegistry

GENERATOR = ProceduralQuestGenerator(REGISTRY)
MANAGER = ProceduralQuestManager(GENERATOR)
PROCEDURAL_QUEST_GENERATOR = GENERATOR  # 後方互換エイリアス（潜在バグ修正）
