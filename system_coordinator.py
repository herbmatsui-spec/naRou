"""
Elona Roguelike - System Coordinator
Step 9: SystemCoordinator 抽出
システム間の依存性解決と初期化順序の管理を担当するクラス
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field

# 依存性グラフのエッジを表すクラス
@dataclass
class DependencyEdge:
    """システム間の依存関係を表す"""
    dependent: str  # 依存しているシステム名
    dependency: str  # 依存されているシステム名

class SystemCoordinator:
    """
    システム間の依存性を管理し、適切な初期化・更新順序を決定するクラス
    SystemManagerのラッパーとして機能し、依存性解決を追加する
    """
    
    def __init__(self, engine: Any):
        """
        システムコーディネーターを初期化
        
        Args:
            engine: ゲームエンジンインスタンス（システムに渡すため）
        """
        self.engine = engine
        # 内部でSystemManagerを使用
        from systems_manager import SystemManager
        self._system_manager = SystemManager()
        
        # 依存性グラフを管理
        self._dependencies: List[DependencyEdge] = []
        # 登録順序を管理（依存性解決前の順序）
        self._registration_order: List[str] = []
        # 初期化完了したシステムのセット
        self._initialized_systems: Set[str] = set()
        
    def register_system(self, name: str, system: Any, 
                       dependencies: Optional[List[str]] = None) -> Any:
        """
        システムを登録し、オプションで依存性を指定
        
        Args:
            name: システム名
            system: システムオブジェクト
            dependencies: このシステムが依存するシステム名のリスト
            
        Returns:
            登録されたシステムオブジェクト
        """
        # SystemManagerに登録
        registered_system = self._system_manager.register(name, system)
        
        # 登録順序を記録
        self._registration_order.append(name)
        
        # 依存性を記録
        if dependencies:
            for dep in dependencies:
                self._dependencies.append(DependencyEdge(dependent=name, dependency=dep))
                
        return registered_system
    
    def _resolve_dependencies(self) -> List[str]:
        """
        依存性グラフに基づいて初期化順序を決定する
        トポロジカルソートを使用して巡回依存性をチェック
        
        Returns:
            初期化すべきシステム名のリスト（依存性を考慮した順序）
        """
        # 隣接リストと入次数を計算
        adj_list: Dict[str, List[str]] = {}
        in_degree: Dict[str, int] = {}
        
        # すべての登録済みシステムを初期化
        for system_name in self._registration_order:
            adj_list[system_name] = []
            in_degree[system_name] = 0
        
        # 依存性エッジに基づいてグラフを構築
        for edge in self._dependencies:
            if edge.dependency not in adj_list:
                # 依存先が登録されていない場合は無視（エラーではなく警告レベル）
                continue
            if edge.dependent not in adj_list:
                # 依存元が登録されていない場合は無視
                continue
                
            adj_list[edge.dependency].append(edge.dependent)
            in_degree[edge.dependent] = in_degree.get(edge.dependent, 0) + 1
        
        # トポロジカルソート（カーンのアルゴリズム）
        # 入次数が0のノードから開始
        queue: List[str] = [node for node in self._registration_order 
                           if in_degree[node] == 0]
        result: List[str] = []
        
        while queue:
            # 入次数が0のノードを取り出す
            node = queue.pop(0)
            result.append(node)
            
            # このノードに依存しているノードの入次数を減らす
            for neighbor in adj_list[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # 巡回依存性がある場合、結果の長さが登録済みシステム数と一致しない
        if len(result) != len(self._registration_order):
            # 巡回依存性がある場合は、登録順序でフォールバック
            # 実際のアプリケーションではここで警告を出すべき
            return self._registration_order
            
        return result
    
    def initialize_all(self, engine: Any) -> None:
        """
        すべてのシステムを依存性を考慮して初期化する
        
        Args:
            engine: ゲームエンジンインスタンス
        """
        # 依存性を解決して初期化順序を決定
        init_order = self._resolve_dependencies()
        
        # システムを順番に初期化
        for system_name in init_order:
            if system_name in self._initialized_systems:
                continue  # すでに初期化済み
                
            system = self._system_manager.get(system_name)
            if system is None:
                continue
                
            # システムのinitializeメソッドを呼び出す
            if hasattr(system, "initialize") and callable(system.initialize):
                try:
                    system.initialize(engine)
                except TypeError:
                    # エンジンパラメータを取らないinitializeメソッドの場合
                    system.initialize()
            
            self._initialized_systems.add(system_name)
    
    def update_all(self, engine: Any, delta_time: float = 1.0) -> None:
        """
        すべてのシステムを更新する
        （依存性は更新時には考慮せず、登録順序で更新）
        
        Args:
            engine: ゲームエンジンインスタンス
            delta_time: 前フレームからの経過時間
        """
        # 登録順序で更新（依存性は初期化時のみ考慮）
        for system_name in self._registration_order:
            system = self._system_manager.get(system_name)
            if system is None:
                continue
                
            # システムのupdateメソッドを呼び出す
            if hasattr(system, "update") and callable(system.update):
                try:
                    system.update(engine, delta_time)
                except TypeError:
                    try:
                        # エンジンパラメータを取らないupdateメソッドの場合
                        system.update(engine)
                    except TypeError:
                        # どちらのパラメータも取らないupdateメソッドの場合
                        system.update()
    
    def get_system(self, name: str) -> Any:
        """
        指定された名前のシステムを取得する
        
        Args:
            name: システム名
            
        Returns:
            システムオブジェクト、見つからない場合はNone
        """
        return self._system_manager.get(name)
    
    def has_system(self, name: str) -> bool:
        """
        指定された名前のシステムが登録されているかチェックする
        
        Args:
            name: システム名
            
        Returns:
            システムが登録されている場合True
        """
        return self._system_manager.has(name)