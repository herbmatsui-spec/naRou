"""
Pet Quest Analyzer Module (偏執的クエストシステム / 設計書 Phase 8 Step 29)
同行ペットプロファイル解析（種族/契約/融合/進化歴）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ecs.entity import Entity  # For type hinting


@dataclass
class PetProfile:
    """同行ペットのプロファイル"""

    species: str = ""  # ペットの種族（例: ウルフ, フェニックス）
    contract_type: str = ""  # 契約タイプ（例: 忠誠, 共生, 支配）
    evolution_stage: int = 0  # 進化段階（0: 幼生, 1: 成体, 2: 進化済み等）
    fusion_history: list[str] = field(
        default_factory=list
    )  # 融合履歴（過去に融合した種族のリスト）
    loyalty: int = 0  # 忠誠度 (0-100)
    affinity: dict[str, int] = field(default_factory=dict)  # 属性親和度 (火, 水, 風, 土 등)


class PetQuestAnalyzer:
    """同行ペットプロファイルを解析し、クエスト生成に使用する情報を提供"""

    def analyze_pet(self, player: Entity) -> PetProfile | None:
        """プレイヤーの同行ペットを解析してプロファイルを返す"""
        # ペットシステムから同行ペット情報を取得
        # ここでは簡易実装として、プレーヤーのコンポーネントから情報を取得する想定
        # 実際には、pet_contract_system.py や pet_evolution_system.py を参照する

        # プレイヤーがペットを所持しているか確認（仮の実装）
        if not hasattr(player, "pet") or player.pet is None:
            return None

        pet = player.pet
        # ペットオブジェクトから情報を抽出（実際の実装に合わせて調整必要）
        return PetProfile(
            species=getattr(pet, "species", "unknown"),
            contract_type=getattr(pet, "contract_type", "unknown"),
            evolution_stage=getattr(pet, "evolution_stage", 0),
            fusion_history=getattr(pet, "fusion_history", []),
            loyalty=getattr(pet, "loyalty", 0),
            affinity=getattr(pet, "affinity", {}),
        )


# グローバルインスタンス（シングルトンライクに使用）
PET_QUEST_ANALYZER = PetQuestAnalyzer()


def analyze_active_pet(player: Entity) -> PetProfile | None:
    """プレイヤーの同行ペットを分析してプロファイルを取得（ヘルパー関数）"""
    return PET_QUEST_ANALYZER.analyze_pet(player)


__all__ = [
    "PET_QUEST_ANALYZER",
    "PetProfile",
    "PetQuestAnalyzer",
    "analyze_active_pet",
]
