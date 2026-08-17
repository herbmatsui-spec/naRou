"""
NPC Relationship Simulation - Dynamic Relationship Change System
Step 5: Dynamic relationship change system
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Any, Callable
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

from .models import (
    RelationshipType, InteractionType, RelationshipModifier
)
from .engine import RelationshipManager


@dataclass
class DelayedEffect:
    """遅延効果（時間経過後に適用される関係変更）"""
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    amount: int
    delay_time: float  # 遅延時間（秒）
    start_time: float
    interaction_type: InteractionType
    context: Dict[str, Any] = field(default_factory=dict)
    is_applied: bool = False
    
    def is_ready(self, current_time: float) -> bool:
        """遅延時間が経過したかチェック"""
        return current_time >= (self.start_time + self.delay_time) and not self.is_applied
    
    def apply(self) -> RelationshipModifier:
        """効果を適用し、修正子を返す"""
        self.is_applied = True
        return RelationshipModifier(
            interaction_type=self.interaction_type,
            amount=self.amount,
            timestamp=time.time(),
            context=self.context.copy()
        )


@dataclass
class CumulativeEffect:
    """累積効果（複数の類似インタラクションの合計効果）"""
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    interaction_type: InteractionType
    threshold: int  # この値に達すると効果が発動
    current_count: int = 0
    effect_amount: int = 0  # 発動時の効果量
    last_reset: float = field(default_factory=time.time)
    reset_interval: float = 3600.0  # 1時間でリセット（デフォルト）
    
    def add_interaction(self) -> bool:
        """インタラクションを追加し、しきい値に達したらTrueを返す"""
        self.current_count += 1
        
        # 時間経過によるリセットチェック
        if time.time() - self.last_reset > self.reset_interval:
            self.current_count = 1  # リセットして現在のインタラクションをカウント
            self.last_reset = time.time()
        
        return self.current_count >= self.threshold
    
    def get_effect(self) -> Optional[RelationshipModifier]:
        """累積効果を取得し、カウンターをリセット"""
        if self.current_count >= self.threshold:
            self.current_count = 0
            self.last_reset = time.time()
            return RelationshipModifier(
                interaction_type=self.interaction_type,
                amount=self.effect_amount,
                timestamp=time.time()
            )
        return None
    
    def reset(self) -> None:
        """カウンターをリセット"""
        self.current_count = 0
        self.last_reset = time.time()


class DynamicRelationshipSystem:
    """
    動的関係変更システム
    遅延効果、累積効果、コンテキスト依存の変更など、
    高度な関係ダイナミクスを管理
    """
    
    def __init__(self, relationship_manager: RelationshipManager):
        self.rm = relationship_manager
        self.graph = relationship_manager.graph
        
        # 遅延効果のキュー
        self._delayed_effects: List[DelayedEffect] = []
        
        # 累積効果のトラッキング
        self._cumulative_effects: Dict[
            Tuple[str, str, RelationshipType, InteractionType], 
            CumulativeEffect
        ] = {}
        
        # コンテキストボーナス/ペナルティルール
        self._context_modifiers: List[Callable[[Dict[str, Any]], float]] = []
        
        # 反応遅延（あるインタラクション後の反応の遅れ）
        self._reaction_delays: Dict[InteractionType, float] = {
            InteractionType.BETRAYAL: 5.0,   # 裏切り後の反応は遅れる
            InteractionType.CONFESSION: 10.0, # 告白後の関係変化は時間をかけて現れる
            InteractionType.RESCUE: 2.0,     # 救出後の感情はすぐに現れるが持続
            InteractionType.ARGUMENT: 0.5,   # 喧嘩は即座に影響
        }
        
        # トレンド分析用のヒストリーバッファ
        self._relationship_history: Dict[
            Tuple[str, str, RelationshipType], 
            deque
        ] = defaultdict(lambda: deque(maxlen=100))  # 過去100エントリーを保持
    
    def apply_interaction_with_dynamics(self, source_id: str, target_id: str,
                                      interaction_type: InteractionType,
                                      base_amount: int,
                                      context: Optional[Dict[str, Any]] = None) -> Dict[RelationshipType, int]:
        """動的システムを考慮してインタラクションを適用"""
        context = context or {}
        changes: Dict[RelationshipType, int] = {}
        
        # 1. 即時効果を計算
        immediate_changes = self._calculate_immediate_effect(
            source_id, target_id, interaction_type, base_amount, context
        )
        
        # 2. 遅延効果をスケジュール
        self._schedule_delayed_effects(
            source_id, target_id, interaction_type, base_amount, context
        )
        
        # 3. 累積効果を更新
        cumulative_changes = self._update_cumulative_effects(
            source_id, target_id, interaction_type, context
        )
        
        # 4. すべての変更を適用
        all_changes = self._merge_changes(immediate_changes, cumulative_changes)
        
        # 5. 実際に関係を変更
        for rel_type, amount in all_changes.items():
            # 多層グラフのため、すべての関係タイプに変更を適用
            edge = self.graph.get_edge(source_id, target_id, rel_type)
            if edge:
                # 文脈による最終調整
                final_amount = self._apply_context_modifiers(amount, context, rel_type)
                
                if final_amount != 0:
                    edge.add_modifier(RelationshipModifier(
                        interaction_type=interaction_type,
                        amount=final_amount,
                        context=context.copy(),
                        timestamp=time.time()
                    ))
                    changes[rel_type] = edge.level
                    
                    # ヒストリーバッファに記録
                    self._record_history(source_id, target_id, rel_type, edge.level)
        
        # 6. 遅延効果のキューを処理
        self._process_delayed_effects()
        
        return changes
    
    def _calculate_immediate_effect(self, source_id: str, target_id: str,
                                  interaction_type: InteractionType,
                                  base_amount: int,
                                  context: Dict[str, Any]) -> Dict[RelationshipType, int]:
        """即時効果を計算"""
        changes: Dict[RelationshipType, int] = {}
        
        # 基本的な変更量
        changes[RelationshipType.FAVORABILITY] = base_amount
        
        # インタラクションタイプによる追加効果
        if interaction_type == InteractionType.GIFT:
            changes[RelationshipType.FRIENDSHIP] = base_amount // 2
        elif interaction_type == InteractionType.RESCUE:
            changes[RelationshipType.TRUST] = base_amount * 2  # TRUSTは仮のタイプ、実際はFAVORABILITYに含む
            changes[RelationshipType.FRIENDSHIP] = base_amount
        elif interaction_type == InteractionType.BETRAYAL:
            changes[RelationshipType.BETRAYAL] = base_amount
            changes[RelationshipType.ENMITY] = base_amount // 2
        elif interaction_type == InteractionType.CONFESSION:
            changes[RelationshipType.ROMANCE] = base_amount
        elif interaction_type == InteractionType.KNOWLEDGE_SHARE:
            changes[RelationshipType.MENTORSHIP] = base_amount
        
        return changes
    
    def _schedule_delayed_effects(self, source_id: str, target_id: str,
                                interaction_type: InteractionType,
                                base_amount: int,
                                context: Dict[str, Any]) -> None:
        """遅延効果をスケジュール"""
        delay = self._reaction_delays.get(interaction_type, 0.0)
        if delay <= 0:
            return
        
        # 特定のインタラクションタイプに遅延効果を設定
        delayed_amount = int(base_amount * 0.3)  # 基本量の30%を遅延効果とする
        if delayed_amount == 0:
            return
        
        delayed_effect = DelayedEffect(
            source_id=source_id,
            target_id=target_id,
            relationship_type=RelationshipType.FAVORABILITY,  # 簡略化のためFAVORABILITYに
            amount=delayed_amount,
            delay_time=delay,
            start_time=time.time(),
            interaction_type=interaction_type,
            context=context.copy()
        )
        
        self._delayed_effects.append(delayed_effect)
        # 時間順でソート（効率的な処理のため）
        self._delayed_effects.sort(key=lambda x: x.start_time + x.delay_time)
    
    def _update_cumulative_effects(self, source_id: str, target_id: str,
                                 interaction_type: InteractionType,
                                 context: Dict[str, Any]) -> Dict[RelationshipType, int]:
        """累積効果を更新し、発動した効果を返す"""
        changes: Dict[RelationshipType, int] = {}
        
        key = (source_id, target_id, RelationshipType.FAVORABILITY, interaction_type)
        if key not in self._cumulative_effects:
            # デフォルトの累積効果設定
            self._cumulative_effects[key] = CumulativeEffect(
                source_id=source_id,
                target_id=target_id,
                relationship_type=RelationshipType.FAVORABILITY,
                interaction_type=interaction_type,
                threshold=3,  # 3回で効果発動
                effect_amount=5  # 発動時の効果量
            )
        
        cum_effect = self._cumulative_effects[key]
        if cum_effect.add_interaction():
            effect_mod = cum_effect.get_effect()
            if effect_mod:
                changes[RelationshipType.FAVORABILITY] = effect_mod.amount
        
        return changes
    
    def _merge_changes(self, *change_dicts: Dict[RelationshipType, int]) -> Dict[RelationshipType, int]:
        """複数の変更辞書をマージ"""
        merged: Dict[RelationshipType, int] = defaultdict(int)
        for change_dict in change_dicts:
            for rel_type, amount in change_dict.items():
                merged[rel_type] += amount
        return dict(merged)
    
    def _apply_context_modifiers(self, base_amount: int, 
                               context: Dict[str, Any],
                               relationship_type: RelationshipType) -> int:
        """コンテキストによる修正子を適用"""
        modifier = 1.0
        
        # 登録されたすべてのコンテキスト修正子を適用
        for context_func in self._context_modifiers:
            try:
                context_multiplier = context_func(context)
                modifier *= context_multiplier
            except Exception:
                # 修正子が失敗しても継続
                continue
        
        return int(base_amount * modifier)
    
    def _record_history(self, source_id: str, target_id: str,
                       relationship_type: RelationshipType, level: int) -> None:
        """関係レベルの変化をヒストリーバッファに記録"""
        key = (source_id, target_id, relationship_type)
        self._relationship_history[key].append({
            'timestamp': time.time(),
            'level': level
        })
    
    def _process_delayed_effects(self) -> None:
        """遅延効果のキューを処理"""
        current_time = time.time()
        ready_effects = []
        remaining_effects = []
        
        for effect in self._delayed_effects:
            if effect.is_ready(current_time):
                ready_effects.append(effect)
            else:
                remaining_effects.append(effect)
        
        self._delayed_effects = remaining_effects
        
        # 準備ができた効果を適用
        for effect in ready_effects:
            modifier = effect.apply()
            # 実際に関係を変更
            edge = self.graph.get_edge(
                effect.source_id, effect.target_id, effect.relationship_type
            )
            if edge:
                edge.add_modifier(modifier)
                # ここでリスナーへの通知なども行う（簡略化のため省略）
    
    def add_context_modifier(self, modifier_func: Callable[[Dict[str, Any]], float]) -> None:
        """コンテキスト修正子を追加"""
        self._context_modifiers.append(modifier_func)
    
    def get_relationship_trend(self, source_id: str, target_id: str,
                             relationship_type: RelationshipType,
                             window_size: int = 10) -> str:
        """関係のトレンドを分析（改善中、悪化中、安定中）"""
        key = (source_id, target_id, relationship_type)
        history = self._relationship_history.get(key)
        
        if not history or len(history) < 2:
            return "insufficient_data"
        
        # 最近のwindow_sizeエントリーを取得
        recent = list(history)[-window_size:] if len(history) >= window_size else list(history)
        if len(recent) < 2:
            return "insufficient_data"
        
        # 線形回帰の簡易版でトレンドを計算
        levels = [entry['level'] for entry in recent]
        n = len(levels)
        
        # 傾きを計算（簡易版）
        sum_x = sum(range(n))
        sum_y = sum(levels)
        sum_xy = sum(i * levels[i] for i in range(n))
        sum_x2 = sum(i * i for i in range(n))
        
        if n * sum_x2 - sum_x * sum_x == 0:
            slope = 0
        else:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        if slope > 0.5:
            return "improving"
        elif slope < -0.5:
            return "declining"
        else:
            return "stable"
    
    def get_predicted_level(self, source_id: str, target_id: str,
                          relationship_type: RelationshipType,
                          hours_ahead: float = 24.0) -> int:
        """指定時間後の予測関係レベルを取得"""
        edge = self.graph.get_edge(source_id, target_id, relationship_type)
        if not edge:
            return 0
        
        current_level = edge.level
        
        # 現在のトレンドを取得
        trend = self.get_relationship_trend(source_id, target_id, relationship_type)
        
        # 減衰を考慮
        decay_per_hour = edge.decay_rate * 24  # 日単位の減衰率を時間単位に変換
        decay_effect = -current_level * decay_per_hour * hours_ahead / 24
        
        # トレンドによる予測変化
        trend_effect = 0
        if trend == "improving":
            trend_effect = 2 * hours_ahead  # 時間あたり2ポイントの改善
        elif trend == "declining":
            trend_effect = -2 * hours_ahead  # 時間あたり2ポイントの悪化
        
        predicted = current_level + decay_effect + trend_effect
        return max(-100, min(100, int(predicted)))
    
    def cleanup_old_data(self, max_age_hours: float = 168.0) -> None:  # 1週間デフォルト
        """古いデータをクリーンアップ"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        # 遅延効果のクリーンアップ
        self._delayed_effects = [
            effect for effect in self._delayed_effects
            if current_time - effect.start_time < max_age_seconds
        ]
        
        # 累積効果のクリーンアップ（古いものはリセット）
        for key, cum_effect in self._cumulative_effects.items():
            if current_time - cum_effect.last_reset > max_age_seconds:
                cum_effect.reset()
        
        # ヒストリーバッファはdequeのmaxlenによって自動的に管理される