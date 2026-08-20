"""
Elona Roguelike - Entity Manager
Step 10: エンティティ管理の委譲
エンティティ、アイテム、リソースノードの生成・取得・削除ロジックを管理するクラス
"""

from __future__ import annotations

from entity import Entity
from item_system import Item
from resource_node import ResourceNode


class EntityManager:
    """
    エンティティ、アイテム、リソースノードの管理を担当するクラス
    エンティティの生成・取得・削除ロジックをカプセル化する
    """

    def __init__(self):
        """エンティティマネージャーを初期化"""
        self.entities: list[Entity] = []
        self.items_on_ground: list[Item] = []
        self.resource_nodes: list[ResourceNode] = []
        # Deferred removal set – entities scheduled for deletion after current loop
        self._pending_removal: set[Entity] = set()

    def add_entity(self, entity: Entity) -> None:
        """
        エンティティを追加する

        Args:
            entity: 追加するエンティティ
        """
        self.entities.append(entity)

    def remove_entity(self, entity: Entity) -> bool:
        """
        エンティティを削除する

        Args:
            entity: 削除するエンティティ

        Returns:
            削除に成功した場合True、見つからなかった場合False
        """
        try:
            self.entities.remove(entity)
            return True
        except ValueError:
            return False

    def schedule_removal(self, entity: Entity) -> None:
        """Mark an entity for deferred removal after the current update loop."""
        self._pending_removal.add(entity)

    def process_pending_removals(self) -> None:
        """Remove all entities that were scheduled via `schedule_removal`."""
        for e in list(self._pending_removal):
            self.remove_entity(e)
        self._pending_removal.clear()

    def get_entities(self) -> list[Entity]:
        """
        すべてのエンティティのリストを取得する

        Returns:
            エンティティのリストのコピー
        """
        return self.entities.copy()

    def get_living_entities(self) -> list[Entity]:
        """
        生存しているエンティティのリストを取得する

        Returns:
            生存しているエンティティのリストのコピー
        """
        return [e for e in self.entities if e.hp > 0]

    def get_entity_at(self, x: int, y: int) -> Entity | None:
        """
        指定された位置にあるエンティティを取得する

        Args:
            x: X座標
            y: Y座標

        Returns:
            位置にあるエンティティ（生存しているもののみ）、見つからない場合はNone
        """
        for entity in self.entities:
            if entity.x == x and entity.y == y and entity.hp > 0:
                return entity
        return None

    def get_entities_in_range(
        self, center_x: int, center_y: int, radius: int
    ) -> list[Entity]:
        """
        指定された範囲内のエンティティを取得する

        Args:
            center_x: 中心X座標
            center_y: 中心Y座標
            radius: 半径（チェビシェフ距離）

        Returns:
            範囲内のエンティティのリスト
        """
        result = []
        for entity in self.entities:
            if entity.hp <= 0:
                continue
            distance = max(abs(entity.x - center_x), abs(entity.y - center_y))
            if distance <= radius:
                result.append(entity)
        return result

    def add_item(self, item: Item) -> None:
        """
        アイテムを地面上に追加する

        Args:
            item: 追加するアイテム
        """
        self.items_on_ground.append(item)

    def remove_item(self, item: Item) -> bool:
        """
        地面上のアイテムを削除する

        Args:
            item: 削除するアイテム

        Returns:
            削除に成功した場合True、見つからなかった場合False
        """
        try:
            self.items_on_ground.remove(item)
            return True
        except ValueError:
            return False

    def get_items_at(self, x: int, y: int) -> list[Item]:
        """
        指定された位置にあるアイテムのリストを取得する

        Args:
            x: X座標
            y: Y座標

        Returns:
            位置にあるアイテムのリスト
        """
        return [item for item in self.items_on_ground if item.x == x and item.y == y]

    def get_all_items(self) -> list[Item]:
        """
        すべての地面上のアイテムのリストを取得する

        Returns:
            アイテムのリストのコピー
        """
        return self.items_on_ground.copy()

    def add_resource_node(self, node: ResourceNode) -> None:
        """
        リソースノードを追加する

        Args:
            node: 追加するリソースノード
        """
        self.resource_nodes.append(node)

    def remove_resource_node(self, node: ResourceNode) -> bool:
        """
        リソースノードを削除する

        Args:
            node: 削除するリソースノード

        Returns:
            削除に成功した場合True、見つからなかった場合False
        """
        try:
            self.resource_nodes.remove(node)
            return True
        except ValueError:
            return False

    def get_resource_nodes_at(self, x: int, y: int) -> list[ResourceNode]:
        """
        指定された位置にあるリソースノードのリストを取得する

        Args:
            x: X座標
            y: Y座標

        Returns:
            位置にあるリソースノードのリスト
        """
        return [node for node in self.resource_nodes if node.x == x and node.y == y]

    def get_all_resource_nodes(self) -> list[ResourceNode]:
        """
        すべてのリソースノードのリストを取得する

        Returns:
            リソースノードのリストのコピー
        """
        return self.resource_nodes.copy()

    def get_blocked_positions(self) -> set[tuple[int, int]]:
        """
        全生存エンティティの座標セットを取得する（衝突判定用）

        Returns:
            (x, y)タプルのセット
        """
        return {(entity.x, entity.y) for entity in self.entities if entity.hp > 0}

    def is_position_blocked(self, x: int, y: int) -> bool:
        """
        指定された位置がエンティティによってブロックされているかチェックする

        Args:
            x: X座標
            y: Y座標

        Returns:
            ブロックされている場合True
        """
        return any(
            entity.x == x and entity.y == y and entity.hp > 0
            for entity in self.entities
        )

    def clear(self) -> None:
        """すべてのエンティティ、アイテム、リソースノードをクリアする"""
        self.entities.clear()
        self.items_on_ground.clear()
        self.resource_nodes.clear()
