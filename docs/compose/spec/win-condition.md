# 勝利条件仕様書

## 概要
プレイヤーがダンジョン深度 20 階に到達し、ボス「ヴォイド・ボス」を撃破することで勝利となる。

## 勝利条件の詳細

### 条件
1. `dungeon_level >= 20` であること
2. ヴォイド・ボス（`void_boss`）を撃破していること

### 遷移
勝利条件を満たした時点で `GameStateMachine.transition("victory")` を呼び出し、ゲーム状態を `victory` に遷移させる。

### 実装場所
- `Engine.check_win_condition()` メソッドで判定を行う
- `advance_world()` または階段降下時 (`descend_stairs()`) で呼び出す

## データ定義

`data/world_state.yaml` に以下を定義:

```yaml
win:
  kind: "depth_boss"
  depth: 20
  boss_id: "void_boss"
```

## 関連システム
- `GameStateMachine`: 状態遷移管理（`playing` → `victory` → `title`）
- `RunHistoryStore`: 勝利記録の保存
- `RunSummary`: 勝利時のラン集計

## 非機能要件
- 勝利判定は毎ターンではなく、階層到達時またはボス撃破時にのみ行う
- 勝利後は入力を遮断し、ラン終了処理へ移行する