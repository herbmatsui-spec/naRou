# 実装計画書: PLAN_03 CombatSystem 統合 — 単一実装への段階的移行

**対象発見**: F002, F008 (high ×2)  
**優先度**: 3 (バグ修正が二ヶ所必要；AoE は旧、報酬は新と相互呼び出し — 保守性・信頼性リスク大)  
**作業見積**: 3–4時間 (Phase 0: 20分 + 実装: 90–120分 + 検証: 30分)  
**戦略**: **段階的移行** (Big Bang 書き換え回避)。新 `engine/systems/combat_system.py` を標準とし、旧 `systems.py:87` `CombatSystem` を委譲先に降格 → 最終的に削除。

---

## 0. 回帰安全網 (Phase 0 — 直列、最初に完了)

| # | テストファイル | テスト名 | 目的 | 初期状態 |
|---|---|---|---|---|
| 0.1 | `tests/test_combat_consolidation.py` (新規) | `test_combat_damage_calc_matches_reference` | 旧 `systems.CombatSystem.melee_damage()` と新 `CombatSystem.calculate_damage()` が同一入力で同一出力 | `xfail(strict=True)` |
| 0.2 | `tests/test_combat_consolidation.py` | `test_kill_rewards_trigger_once` | 敵撃破時に報酬 (XP/ゴールド/クエスト進捗/称号/ペット絆/派閥評判) が **1回だけ** 発火する | `xfail(strict=True)` |
| 0.3 | `tests/test_combat_consolidation.py` | `test_aoe_damage_distribution` | AoE ダメージが全対象に正しく分配される (旧実装委譲中も新実装で同一結果) | `xfail(strict=True)` |
| 0.4 | `tests/test_non_vacuity.py` | `assert_can_fail(test_kill_rewards_trigger_once, single_kill, double_kill_simulation)` | 二重発火を検出できる非空虚性証明 | 実装後 green |

**非空虚性証明**: `double_kill_simulation` で同一敵を二重に kill イベント発火 → 報酬が2倍にならないことを検証。

---

## 1. 移行戦略 (4段階)

| 段階 | 方針 | 対象 | 完了条件 |
|---|---|---|---|
| **Phase A** | 新実装を標準化、旧を委譲ヘルパーに降格 | `engine/systems/combat_system.py` 拡張、`systems.py` 旧メソッドを `@staticmethod` 明示 | 0.1, 0.2 PASS |
| **Phase B** | 呼び出し側を新実装に切替 | `engine/engine.py`, `engine/systems/world_system.py`, `packages/gameplay/package.py` | 全呼び出しが新 API 経由 |
| **Phase C** | 旧実装削除 + import 整理 | `systems.py:87-300` `CombatSystem` クラス削除 | ruff clean, 旧参照ゼロ |
| **Phase D** | 残存参照 (skill_eater 等) の移行 | `skill_eater/combat/engine.py` 等 | 全テスト PASS |

**本計画書は Phase A–B まで**。Phase C–D は別計画 (リスク分離)。

---

## 2. 実装ステップ (ファイル単位、アトミック)

### Step 1: `engine/systems/combat_system.py` — 新実装を完全版に拡張
- **現状**: `calculate_damage()`, `on_kill()` 等あるが、AoE は旧に委譲 (`line 218: from naRou.systems import CombatSystem as LegacyCombat`)
- **拡張**: `aoe_damage(center, radius, base_damage, falloff)` を自前実装 (旧ロジック移植)
- **インターフェース統一**: 全メソッドをインスタンスメソッドに (旧は `@staticmethod`)
- **依存**: `systems.py` の定数 (MAP_WIDTH 等) は `constants` から取るよう変更
- **回帰テスト**: 0.1, 0.3 の基盤。

### Step 2: `systems.py:87` — 旧 `CombatSystem` を明示的委譲レイヤーに
- **変更**: クラス名を `_LegacyCombatSystem` に変更 (private 明示)、全メソッドに `@staticmethod` 維持、docstring に `"DEPRECATED: use engine.systems.combat_system.CombatSystem"` 追記
- **理由**: 既存コード (`engine/systems/combat_system.py:218` 等) が壊れないよう段階的移行
- **回帰テスト**: 既存テスト全 PASS 確認。

### Step 3: `engine/engine.py:34,189` — import 整理・新実装統一
- **変更**: 
  - Line 34: `from naRou.systems import CombatSystem as LegacyCombat` → 削除 (未使用、F811 解消)
  - Line 189: `from engine.systems.combat_system import CombatSystem` のみ残す
- **回帰テスト**: F811 消滅確認 (ruff)、0.2 PASS へ。

### Step 4: 呼び出し側切替 — `engine/systems/world_system.py`, `packages/gameplay/package.py`
- **world_system.py**: `CombatSystem.apply_damage()` → `self.engine.combat_system.calculate_damage()` + `on_kill()` 連鎖
- **gameplay/package.py**: `player_act()` 内のダメージ計算を新 API に統一
- **並列化**: 2ファイル独立 → 別サブエージェント可
- **回帰テスト**: 0.2 (kill rewards once) が green になる。

---

## 3. 検証手順

```bash
# Phase 0: 赤確認
/usr/bin/python3 -m pytest tests/test_combat_consolidation.py -v --runxfail

# Phase A 後 (Step 1-2)
/usr/bin/python3 -m pytest tests/test_combat_consolidation.py::test_combat_damage_calc_matches_reference -v
/usr/bin/python3 -m pytest tests/test_combat_consolidation.py::test_aoe_damage_distribution -v

# Phase B 後 (Step 3-4)
/usr/bin/python3 -m pytest tests/test_combat_consolidation.py -v
/usr/bin/python3 -m pytest tests/test_non_vacuity.py::assert_can_fail -v

# 既存スイート回帰確認
/usr/bin/python3 -m pytest tests/test_enemy_abilities.py -v --deselect "::test_ranged_ability_accuracy_depends_on_defender"
/usr/bin/python3 -m pytest tests/test_skill_synthesis_72_steps.py -v
```

---

## 4. 完了の定義

- [ ] `test_combat_damage_calc_matches_reference` PASS (旧新同一出力)
- [ ] `test_kill_rewards_trigger_once` PASS (二重発火なし)
- [ ] `test_aoe_damage_distribution` PASS
- [ ] 非空虚性証明 PASS
- [ ] ruff: F811 `CombatSystem` 再定義消滅
- [ ] 既存 8スイート + enemy_abilities 21/21 PASS
- [ ] `systems.py` から `CombatSystem` クラス削除 **未実施** (Phase C 以降) — 現段階では `_LegacyCombatSystem` として残存許容