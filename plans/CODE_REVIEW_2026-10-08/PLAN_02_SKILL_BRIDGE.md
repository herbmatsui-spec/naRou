# 実装計画書: PLAN_02 スキル「所有→使用」パイプライン実装 (Entity→CharacterState ブリッジ)

**対象発見**: F011, F012, F013 (critical ×3)  
**優先度**: 2 (スキルシステムの核心機能がデッドコード化；融合/覚醒/進化/継承/共鳴/特化が全て「所有」止まり)  
**作業見積**: 2–3時間 (Phase 0: 20分 + 実装: 60–90分 + 検証: 20分)  
**並列化**: ファイル所有権で 3サブエージェントに分割可能 (Bridge Core / Skill Modules / Integration)

---

## 0. 回帰安全網 (Phase 0 — 直列、最初に完了)

| # | テストファイル | テスト名 | 目的 | 初期状態 |
|---|---|---|---|---|
| 0.1 | `tests/test_skill_bridge.py` (新規) | `test_fused_skill_becomes_castable` | `skill_fusion_system.fuse()` 後、該当スキルが `CharacterState.skills` (spellbook) に入り `cast_skill` 可能になる | `xfail(strict=True)` |
| 0.2 | `tests/test_skill_bridge.py` | `test_learned_skill_appears_in_spellbook` | いずれかのスキル習得系システム (覚醒/進化/継承/共鳴/特化) 実行後、spellbook に反映される | `xfail(strict=True)` |
| 0.3 | `tests/test_skill_bridge.py` | `test_cast_skill_consumes_cooldown_on_character_state` | `CharacterState.cast_skill()` がクールダウンを正しく管理する | `xfail(strict=True)` (既存実装の動作確認兼用) |
| 0.4 | `tests/test_non_vacuity.py` | `assert_distinguishes(check_bridge, good_bridge, bad_bridge)` | ブリッジ機能の有無を検出できる非空虚性証明 | 実装後 green |

**非空虚性証明**: `bad_bridge` = ブリッジ呼び出しをコメントアウトした版 → spellbook に入らないことを検出。

---

## 1. アーキテクチャ決定 (実装前確定事項)

| 決定項目 | 採用案 | 理由 |
|---|---|---|
| **ブリッジ関数の場所** | `skill_bridge.py` (新規モジュール、ルート) | 単一責任；全 skill_* モジュールから import 可能；循環回避 |
| **ブリッジ API** | `bridge_skill_to_spellbook(entity: Entity, skill_id: str, level: int) -> bool` | 所有→呪文帳の単方向同期；戻り値で成功/失敗判定 |
| **spellbook キー** | `CharacterState.skills[skill_id] = CharacterSkillSlot(level=..., cooldown=0, ...)` | 既存 `skill_eater/combat/engine.py:816` `cast_skill()` と互換 |
| **呼び出し側** | 各 skill_* モジュールの「習得完了」地点 (fuse, awaken, evolve, inherit, resonate, specialize) | 既存フローを壊さず注入 |

---

## 2. 実装ステップ (ファイル単位、アトミック)

### Step 1: `skill_bridge.py` (新規) — ブリッジ核心実装
- **内容**:
  ```python
  def bridge_skill_to_spellbook(entity: "Entity", skill_id: str, level: int = 1) -> bool:
      from ecs.entity import Entity
      from character_state import CharacterState  # 既存 import パス確認
      if not hasattr(entity, 'character_state') or entity.character_state is None:
          return False
      cs: CharacterState = entity.character_state
      if skill_id not in cs.skills:
          cs.skills[skill_id] = CharacterSkillSlot(skill_id=skill_id, level=level, cooldown=0)
      else:
          cs.skills[skill_id].level = max(cs.skills[skill_id].level, level)
      return True
  ```
- **依存**: `CharacterState` と `CharacterSkillSlot` の定義位置確認 (`skill_eater/combat/engine.py` 付近)
- **回帰テスト**: 0.1, 0.2 の前提となる。

### Step 2: `skill_fusion_system.py:495` — 融合完了時にブリッジ呼び出し
- **場所**: `fuse()` メソッド内、`player.skills[recipe.output] = Skill(...)` の直後
- **追加**: `from skill_bridge import bridge_skill_to_spellbook; bridge_skill_to_spellbook(player, recipe.output, 1)`
- **回帰テスト**: 0.1 が green になる。

### Step 3: `skill_awakening_system.py:127` — 覚醒完了時にブリッジ呼び出し
- **場所**: `awaken()` 完了直後
- **追加**: 同パターンでブリッジ呼び出し
- **回帰テスト**: 0.2 に寄与。

### Step 4: `skill_evolution_system.py` / `skill_inheritance_system.py` / `skill_resonance_system.py` / `skill_specialization_system.py` — 各習得完了点にブリッジ注入
- **対象**: 6モジュール (各1箇所、計6箇所)
- **パターン**: 統一ヘルパー `def _grant_and_bridge(player, skill_id, level): player.skills[skill_id] = Skill(...); bridge_skill_to_spellbook(player, skill_id, level)`
- **並列化**: 6ファイル互いに独立 → 3サブエージェントに2ファイルずつ割当可能
- **回帰テスト**: 0.2 が green になる。

### Step 5: `skill_transfer_system.py` — 移転時も spellbook 同期 (任意・低優先)
- **理由**: 移転は「他キャラへ渡す」操作。渡した側は spellbook からも削除すべきだが、仕様未定のため Phase 2 に延期可。

---

## 3. 検証手順

```bash
# Phase 0: 赤確認
/usr/bin/python3 -m pytest tests/test_skill_bridge.py -v --runxfail

# 実装後 (Step 1-2 だけで 0.1 が通るはず)
/usr/bin/python3 -m pytest tests/test_skill_bridge.py::test_fused_skill_becomes_castable -v

# 全 Step 完了後
/usr/bin/python3 -m pytest tests/test_skill_bridge.py -v
/usr/bin/python3 -m pytest tests/test_non_vacuity.py::assert_distinguishes -v
```

---

## 4. 完了の定義

- [ ] `test_fused_skill_becomes_castable` PASS
- [ ] `test_learned_skill_appears_in_spellbook` PASS (6モジュール全網羅)
- [ ] `test_cast_skill_consumes_cooldown_on_character_state` PASS (既存動作確認)
- [ ] 非空虚性証明: ブリッジ無効化で検出
- [ ] 既存 8スイート (`test_skill_synthesis_72_steps.py` 等) に回帰なし
- [ ] ruff/mypy clean
- [ ] `skill_bridge.py` 単体テスト追加 (`tests/test_skill_bridge_unit.py`)