# 戦闘解決モデル仕様書 (Phase 2 Step 33)

## 概要
現在の「当たって壁を潰す」のみの戦闘を、**AP（アクションポイント）制**に置き換える。
位置・向き・射程・APコストによって戦術的深度を生む。

---

## 1. APシステム基本設計

### 1.1 AP基礎値
- **全Entity（プレイヤー・敵・ペット）共通**: `ap = 2` (初期値・最大値)
- APは**ターン開始時に最大値(2)まで回復**する（自然回復ではない）

### 1.2 アクション別APコスト
```python
AP_COST = {
    "attack": 1,      # 近接攻撃・射程攻撃
    "move": 1,        # 1マス移動
    "wait": 0,        # 待機（パス）— 世界を1tick進めるのみ
    "spell": 1,       # 呪文詠唱
    "item": 1,        # アイテム使用
    "skill": 1,       # スキル発動
}
```

### 1.3 AP消費のルール
- AP ≥ コストのときのみ実行可能
- 実行時に即座にAPを減算
- AP不足時は「行動不能」メッセージを出し、入力を待ち直す
- **敵AIも同一APルールに従う**（敵1体 = AP 1-2）

### 1.4 ターン進行モデル
```
プレイヤー入力 → AP消費 → 行動解決 → (AP残あれば継続 / なければ敵フェーズへ)
敵フェーズ: 各敵がAP消費しながら行動 → 全敵AP尽きたらプレイヤーターンに戻る
```
- `WaitAction` (キー `.` / `5` / `wait`) は **AP 0で世界を1tick進める**唯一の経路

---

## 2. 既存バグの置き換え方針

### 2.1 `player.x + 3` ハードコード座標 (engine/engine.py:1738)
- **現状**: `tx, ty = self.player.x + 3, self.player.y` で右3マス固定
- **置き換え**: `systems.aimed_tile(origin, direction, distance) -> Point` を新設
  - `direction`: 8方向ベクトル (dx, dy)
  - `distance`: 射程距離
  - 視線判定込みで「撃てる最寄り敵」を返す

### 2.2 `xp_next = 100` 固定 (ecs/entity.py:94)
- **現状**: レベルアップ必要経験値が全レベルで100固定
- **置き換え**: `data/balance_standards.yaml` の `exp_curve: {base: 120, growth: 1.35}` に基づく動的計算
  - `exp_next = floor(base * growth ** (level - 1))`
  - Phase 1 Step 21で実装済み

---

## 3. 移行期間中の二重実装方針 (`legacy_bump` フラグ)

既存テスト・セーブ互換のため、**新旧並存期間を設ける**:

```python
# config.yaml に追加
game:
  legacy_bump: true  # true: 旧ロジック併用、false: 新AP制のみ
```

| `legacy_bump` | 動作 |
|---------------|------|
| `true` (デフォルト) | 旧 `GameplayLoop.player_act` と新 `resolve_action()` 両方動く。AP不足時は旧ロジックへフォールバック |
| `false` | 完全に新AP制のみ。AP不足は「行動不能」で入力待ち |

**移行完了条件**: 全戦闘テストが `legacy_bump: false` で緑 → フラグ削除

---

## 4. A（engine.py所有）への要求事項

以下は **A担当ファイル** への変更要求。Bは `docs/compose/spec/combat-resolution.md` に列挙し、Aブランチで実装してもらう。

| 要求ID | 内容 | 対象ファイル | Step |
|--------|------|-------------|------|
| A-1 | `Entity.ap` プロパティ追加 (getter/setter、初期値2) | `ecs/entity.py` | 34.2 |
| A-2 | `engine.turns` 毎フレーム加算停止 → ターン制に一本化 (自然回復バグ修正) | `engine/engine.py:2114` | 18.2 |
| A-3 | `x + 3` ハードコード削除、`aimed_tile()` 使用へ置換 | `engine/engine.py:1738` | 42 |
| A-4 | `WaitAction` を `advance_world()` ではなく `pass_turn()` 呼び出しに変更 | `engine/engine.py` (input系) | 42.1 |

---

## 5. 非空虚性の証明 (各Step共通)

新規テスト追加時、**必ず「1つだけ意図的に壊す → 赤になる」を実行し、出力をコミットメッセージに残す**。

例:
```bash
# test_ap_defaults_to_two を壊す
sed -i 's/ap == 2/ap == 999/' tests/test_ap_system.py
pytest tests/test_ap_system.py::test_ap_defaults_to_two -v
# → FAILED (赤確認)
git checkout tests/test_ap_system.py
```

---

## 6. Definition of Done (Step 33)

- [x] `docs/compose/spec/combat-resolution.md` 存在
- [x] Aへの要求 (A-1〜A-4) が明記されている
- [x] `docs/compose/spec/shipping-chain.md` 索引に登録