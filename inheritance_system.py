"""
特典継承システム
"""
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import yaml
import os


@dataclass
class InheritanceData:
    """継承データクラス"""
    id: str
    name: str
    description: str
    always_keep: List[str]
    selective_keep_rules: Dict[str, Any]


class InheritanceRegistry:
    """継承レジストリ（シングルトン的）"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data: Dict[str, InheritanceData] = {}
        return cls._instance
    
    def load(self, path: str = "data/reincarnation_inheritance.yaml") -> None:
        """YAMLファイルから継承データを読み込み"""
        self._data.clear()
        always_keep = []
        selective_rules = {}
        if os.path.exists(path):
            try:
                with open(path, encoding='utf-8') as f:
                    raw = yaml.safe_load(f)
                if raw and 'inheritance' in raw:
                    inh = raw['inheritance']
                    always_keep = inh.get('always_keep', [])
                    selective_rules = inh.get('selective_keep', {})
            except Exception:
                pass

        default_data = InheritanceData(
            id="default",
            name="デフォルト継承",
            description="基本的な継承ルール",
            always_keep=always_keep,
            selective_keep_rules=selective_rules
        )
        self._data["default"] = default_data
    
    def all(self) -> Dict[str, InheritanceData]:
        """全継承データを取得"""
        return self._data.copy()
    
    def get(self, inheritance_id: str = "default") -> Optional[InheritanceData]:
        """特定の継承データを取得"""
        return self._data.get(inheritance_id or "default")


# グローバルレジストリインスタンス
REGISTRY = InheritanceRegistry()


class InheritanceManager:
    """継承管理クラス"""
    
    def __init__(self, registry: Optional[InheritanceRegistry] = None):
        self.registry = registry or REGISTRY
    
    def process_inheritance(self, player: Any, selections: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """継承処理を実行"""
        data = self.registry.get("default")
        always_kept = data.always_keep if data else []
        selective_kept = list(selections.keys()) if selections else []
        return {
            "always_kept": always_kept,
            "selective_kept": selective_kept
        }