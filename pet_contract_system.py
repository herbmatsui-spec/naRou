"""
ペット契約システム
契約データの管理・絆度更新・効果取得・進化可否判定
Steps 19-26
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TYPE_CHECKING
import yaml
from pathlib import Path

if TYPE_CHECKING:
    from entity import PetAI


@dataclass
class PetContractData:
    """ペット契約データ (Step 20)"""
    id: str
    name: str
    icon: str = "🤝"
    max_bond: int = 1000
    bond_gain: Dict[str, int] = field(default_factory=dict)
    bond_decay: Dict[str, int] = field(default_factory=dict)
    bond_effects: List[Dict[str, Any]] = field(default_factory=list)


class PetContractRegistry:
    """ペット契約レジストリ (シングルトン) (Steps 21, 22)"""
    _instance: Optional['PetContractRegistry'] = None
    _contracts: Dict[str, PetContractData] = {}
    _loaded: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._contracts = {}
            cls._loaded = False
        return cls._instance

    def load(self, path: str = "data/pet_contracts.yaml") -> None:
        """YAMLからペット契約定義をロード (Step 22)"""
        if self._loaded:
            return
        p = Path(path)
        if not p.exists():
            self._loaded = True
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            contracts_data = data.get('pet_contracts', {})
            for cid, c in contracts_data.items():
                contract = PetContractData(
                    id=cid,
                    name=c.get('name', cid),
                    icon=c.get('icon', '🤝'),
                    max_bond=c.get('max_bond', 1000),
                    bond_gain=c.get('bond_gain') or {},
                    bond_decay=c.get('bond_decay') or {},
                    bond_effects=c.get('bond_effects') or []
                )
                self._contracts[cid] = contract
            self._loaded = True
        except Exception:
            self._loaded = True

    def get(self, contract_id: str) -> Optional[PetContractData]:
        """特定契約データを取得 (Step 21)"""
        return self._contracts.get(contract_id)

    def all(self) -> Dict[str, PetContractData]:
        """すべての契約データ辞書を返す (Step 21)"""
        return self._contracts


REGISTRY = PetContractRegistry()


class PetContractManager:
    """ペット契約管理マネージャー (Steps 23-26)"""

    def __init__(self, registry: Optional[PetContractRegistry] = None):
        self.registry = registry or REGISTRY

    def update_bond(self, pet: 'PetAI', amount: int) -> int:
        """絆度更新 (0-max_bondでクランプ) (Step 24)"""
        contract = self.registry.get(getattr(pet, 'contract_id', 'default'))
        max_bond = contract.max_bond if contract else 1000
        cur_bond = getattr(pet, 'bond', 0)
        new_bond = max(0, min(max_bond, cur_bond + amount))
        pet.bond = new_bond
        return new_bond

    def get_bond_effects(self, pet: 'PetAI') -> List[Dict[str, Any]]:
        """現在の絆度で適用される効果リスト (Step 25)"""
        contract = self.registry.get(getattr(pet, 'contract_id', 'default'))
        if not contract or not contract.bond_effects:
            return []
        cur_bond = getattr(pet, 'bond', 0)
        active_effects = []
        for group in contract.bond_effects:
            threshold = group.get('threshold', 0)
            if cur_bond >= threshold:
                active_effects.append(group)
        return active_effects

    def can_evolve(self, pet: 'PetAI', evolution_data: Dict[str, Any]) -> bool:
        """進化可能かチェック (Step 26)"""
        req_bond = evolution_data.get('requirements', {}).get('bond')
        if req_bond is None:
            req_bond = evolution_data.get('bond', 0)
        cur_bond = getattr(pet, 'bond', 0)
        return cur_bond >= req_bond
