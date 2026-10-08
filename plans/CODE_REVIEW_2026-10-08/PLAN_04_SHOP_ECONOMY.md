# 実装計画書: PLAN_04 最小機能ショップ実装 + 金消費パス追加

**対象発見**: F014, F044 (high ×2)  
**優先度**: 4 (金策のみで消費なし → インフレ必至；商用品質の経済ループ必須)  
**作業見積**: 2–3時間 (Phase 0: 15分 + 実装: 60–90分 + 検証: 20分)  
**スコープ**: **最小実装** — 買う/売る/在庫/価格 のみ。評判ゲート・品質・レア度は Phase 2。

---

## 0. 回帰安全網 (Phase 0 — 直列、最初に完了)

| # | テストファイル | テスト名 | 目的 | 初期状態 |
|---|---|---|---|---|
| 0.1 | `tests/test_shop_economy.py` (新規) | `test_shop_buy_item_reduces_gold` | 店でアイテム購入 → `player.gold` 減少、インベントリに追加 | `xfail(strict=True)` |
| 0.2 | `tests/test_shop_economy.py` | `test_shop_sell_item_increases_gold` | 店にアイテム売却 → `player.gold` 増加、インベントリから削除 | `xfail(strict=True)` |
| 0.3 | `tests/test_shop_economy.py` | `test_gold_inflation_bounded_over_100_quests` | 100クエスト完走シミュレーションでゴールが上限付き (売却上限 or 消費 > 獲得) | `xfail(strict=True)` |
| 0.4 | `tests/test_non_vacuity.py` | `assert_distinguishes(check_gold_flow, working_shop, broken_shop_no_sell)` | 売却機能の有無でゴールドフローが変わることを非空虚性証明 | 実装後 green |

**非空虚性証明**: `broken_shop_no_sell` = `sell_item()` を no-op にした版 → 100クエストでゴールドが単調増加し上限超えを検出。

---

## 1. 実装ステップ (ファイル単位、アトミック)

### Step 1: `data/shop_inventory.yaml` (新規) — 店在庫・価格定義
- **内容**: YAML スキーマ定義
  ```yaml
  shops:
    - id: "town_general"
      name: "総合店"
      buy_markup: 1.5    # 買値 = base_price * 1.5
      sell_markdown: 0.4 # 売値 = base_price * 0.4
      inventory:
        - item_id: "healing_potion"
          base_price: 50
          stock: 10
          restock_rate: 0.1  # per day
        - item_id: "mana_potion"
          base_price: 80
          stock: 5
          restock_rate: 0.1
  ```
- **配置**: `data/shop_inventory.yaml` (既存 `data/` パターン踏襲)
- **回帰テスト**: 0.1, 0.2 のデータソース。

### Step 2: `shop_system.py` (新規) — 店ロジック核心
- **クラス**: `ShopSystem`
- **メソッド**:
  - `load_shops()` — YAML 読込 + バリデーション
  - `get_shop(shop_id)` — 在庫・価格取得
  - `buy_item(player, shop_id, item_id, quantity=1)` → `(success, message, gold_delta)`
  - `sell_item(player, shop_id, item_id, quantity=1)` → 同上
  - `restock_all()` — 日次補充 (将来 `time_system` から呼出)
- **設計**: `Entity` 直接操作せず `player.gold` / `player.inventory` (既存) 経由
- **回帰テスト**: 0.1, 0.2 が green になる。

### Step 3: `player_actions.py:249` — `_perform_shop()` スタブを実装に置換
- **現状**: メッセージ返すだけのスタブ
- **実装**: 
  ```python
  def _perform_shop(engine, action):
      from shop_system import ShopSystem
      shop = ShopSystem()
      if action.sub_action == "buy":
          return shop.buy_item(engine.player, action.shop_id, action.item_id, action.quantity)
      elif action.sub_action == "sell":
          return shop.sell_item(engine.player, action.shop_id, action.item_id, action.quantity)
      return shop.get_shop(action.shop_id)
  ```
- **Action 定義**: `input_actions.py` に `ShopAction(shop_id, sub_action, item_id, quantity)` 追加 (或いは既存拡張)
- **回帰テスト**: 0.1, 0.2 統合テストとして機能。

### Step 4: `reputation_gate_system.py:262` — `_unlock_shop()` スタブ解除 (最小)
- **変更**: `return True` → `return shop_id in UNLOCKED_SHOPS` (セットで管理)
- **理由**: 将来の評判連携のフックだけ残し、現状は全開放

### Step 5: `procedural_quest_generator.py` — クエスト報酬に「店解放券」追加 (任意)
- **理由**: 進行感演出；必須ではないため Phase 2 に延期可

---

## 2. 検証手順

```bash
# Phase 0: 赤確認
/usr/bin/python3 -m pytest tests/test_shop_economy.py -v --runxfail

# Step 1-2 後
/usr/bin/python3 -m pytest tests/test_shop_economy.py::test_shop_buy_item_reduces_gold -v
/usr/bin/python3 -m pytest tests/test_shop_economy.py::test_shop_sell_item_increases_gold -v

# 全 Step 後
/usr/bin/python3 -m pytest tests/test_shop_economy.py -v
/usr/bin/python3 -m pytest tests/test_non_vacuity.py::assert_distinguishes -v

# インフレ境界テスト (時間かかるため手動/夜間)
# /usr/bin/python3 -m pytest tests/test_shop_economy.py::test_gold_inflation_bounded_over_100_quests -v
```

---

## 3. 完了の定義

- [ ] `test_shop_buy_item_reduces_gold` PASS
- [ ] `test_shop_sell_item_increases_gold` PASS
- [ ] `test_gold_inflation_bounded_over_100_quests` PASS (または境界値証明)
- [ ] 非空虚性証明 PASS
- [ ] `skill_transfer_system.py` 以外の金消費パスが存在すること確認
- [ ] 既存テスト (`test_procedural_quest_generation_36_steps.py` 等) に回帰なし
- [ ] ruff/mypy clean