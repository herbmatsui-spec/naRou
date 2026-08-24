# 実装計画: 報酬マネージャーと実際のアイテム・経済システムの連携 (TODO 解決)

**優先度**: 3 (中)
**対象ファイル**: `naRou/reward_manager.py` (主), `naRou/systems/item_system.py`, `naRou/systems/item_generator.py`, `naRou/systems/world_event_system.py`, `naRou/engine/engine.py`, `tests/test_reward_manager_integration.py`
**目的**: `reward_manager.py` 内の `# TODO: 実際の通貨システムと連携` / `# TODO: 実際のアイテムシステムと連携` を解消し、報酬がゲーム内で実際に機能するようにする。

---

## 現状サマリ (計画の前提)

- `naRou/reward_manager.py:36-42` の `_grant_currency()` / `_grant_item()` は「実装は省略」の TODO で何もしない。
- 実際のシステムはすでに存在する:
  - アイテム: `naRou/systems/item_system.py` の `Item` クラスと `Inventory` クラス (`add_item()` はスタック処理付き)。
  - アイテム生成: `naRou/systems/item_system.py` の `create_sample_item(name)` と `naRou/systems/item_generator.py` の `ItemGenerator`。
  - 経済: `player.gold` / `player.platinum` (EconomyComponent への委譲, `entity.py:345-346`)。
  - その他: `player.piety` (entity.py:109), `player.gain_exp(amount)` (entity.py:1303, ログ文字列の list を返す), `player.inventory` (entity.py:232 で参照あり)。
- 呼び出し側: `naRou/systems/world_event_system.py:176` の `REWARD_MANAGER.grant_event_rewards(player, edata)`。ここには `engine` が渡されていない。
- `WorldEventData.rewards` は `dict[str, Any]` (world_event_system.py:54)。実際に使われているキー例: `gold`, `platinum`, `exp`, `piety`, `fame`, `items`（辞書）, `artifact`, `special_currency`(旧), `item_drops`(辞書, ドロップ率付き), `currency_amount`。

この計画は「低性能な LLM でも 1 ステップずつ確実に実装できる」ことを重視し、各ステップを极小・自己完結に分割している。

---

## Phase 1 — 現状把握と準備 (Step 1〜7)

**Step 1.** `naRou/reward_manager.py` を全文読み、TODO のあるメソッド (`_grant_currency`, `_grant_item`, `grant_event_rewards`) と import を書き出す。完了条件: ファイルの構造を口頭で説明できる。

**Step 2.** `naRou/systems/item_system.py` の `Item.__init__` の引数一覧と、`Inventory.add_item(item)` の戻り値 `(bool, str)` を確認する。完了条件: `add_item` がスタック時に `existing.count` を増やすことを確認。

**Step 3.** `naRou/systems/item_system.py` の `create_sample_item(name, x=0, y=0)` が既知の `name`（"longsword" 等）に対して `Item` を返すことを確認する。完了条件: 不明な `name` のときは `"longsword"` を返すフォールバックがあることを確認。

**Step 4.** `naRou/managers/combat_manager.py` の `handle_kill_rewards` を読み、既存の報酬付与パターン (`engine.survival.gold += ...`, `engine.player.gain_exp(...)`) を確認する。完了条件: `gain_exp` はログ文字列の list を返すことを確認。

**Step 5.** `naRou/engine/engine.py` 付近で `engine.inventory` / `engine.survival` がどう扱われているか grep し、プレイヤー報酬は `player.gold`/`player.inventory` 経由で良いことを確認する。完了条件: `player.gold += x` が機能することを確認（委譲）。

**Step 6.** `naRou/systems/item_generator.py` の `ItemGenerator` の `generate` メソッド（ランダムアイテム生成）のシグネチャを確認する。完了条件: 後で使う場合の呼び出し方をメモ。

**Step 7.** `tests/` 配下で `test_item_*.py` または `test_inventory_*.py` を 1 つ開き、テストの書き方（import パス、`pytest` の書き方）を確認する。完了条件: 後で真似る雛形を得る。

---

## Phase 2 — 報酬スキーマの定義 (Step 8〜15)

**Step 8.** `reward_manager.py` の先頭に、報酬キー定数を追加する。
```python
KEY_GOLD = "gold"
KEY_PLATINUM = "platinum"
KEY_EXP = "exp"
KEY_PIETY = "piety"
KEY_FAME = "fame"
KEY_ITEMS = "items"
KEY_ITEM_DROPS = "item_drops"
KEY_ARTIFACT = "artifact"
KEY_SPECIAL_CURRENCY = "special_currency"
KEY_CURRENCY_AMOUNT = "currency_amount"
```
完了条件: ファイルが構文エラーなく import できる。

**Step 9.** `RewardManager` クラスの docstring に「対応する報酬辞書のスキーマ」を記述する（gold/platinum/exp/piety/fame/items/item_drops/artifact/special_currency を列挙）。

**Step 10.** 通貨ID から実際の属性へのマッピング辞書を追加する。
```python
_CURRENCY_MAP = {
    "gold": KEY_GOLD,
    "g": KEY_GOLD,
    "platinum": KEY_PLATINUM,
    "p": KEY_PLATINUM,
}
```
完了条件: 辞書が定義されている。

**Step 11.** `reward_manager.py` の `from naRou.systems.item_system import Item, Inventory, create_sample_item` を追加 import する（ファイル冒頭の import 群に追記）。完了条件: import エラーがない。

**Step 12.** `_normalize_rewards(rewards)` ヘルパを追加。`rewards` が `None` なら `{}` を返し、dict 以外なら `{}` を返す。完了条件: `None` 入力で `{}` を返すことを確認（後でテスト）。

**Step 13.** `_get_amount(rewards, key, default=0)` ヘルパを追加。`rewards.get(key, default)` を `int(...)` に変換して返す（変換失敗時は default）。完了条件: 文字列 `"100"` も `100` になる。

**Step 14.** `_resolve_item_id(raw_id)` ヘルパを追加。そのまま `str` 化して返す（後段の `create_sample_item` で使う）。完了条件: 単に `return str(raw_id)`。

**Step 15.** Phase 2 の定数・ヘルパをまとめて 1 回 import テストする（例: `python -c "import naRou.reward_manager"`）。完了条件: エラーなし。

---

## Phase 3 — 通貨・経験値・信心の連携 (Step 16〜30)

**Step 16.** `_grant_gold(self, player, amount)` を追加。`amount = int(amount); player.gold = getattr(player, "gold", 0) + amount`。完了条件: メソッドが定義されている。

**Step 17.** `_grant_platinum(self, player, amount)` を追加。`player.platinum = getattr(player, "platinum", 0) + amount`。完了条件: 同上。

**Step 18.** `_grant_exp(self, player, amount, engine=None)` を追加。`logs = player.gain_exp(int(amount))` とし、engine があれば `engine.log` で各ログを出力。戻り値は `logs`（list）。完了条件: `gain_exp` の戻りをそのまま返す。

**Step 19.** `_grant_piety(self, player, amount)` を追加。`player.piety = getattr(player, "piety", 0) + int(amount)`。完了条件: 定義済み。

**Step 20.** `_grant_fame(self, player, amount)` を追加。Entity に `fame` 属性はないため、`player.faction_reputation` に `"world"` キーで加算する（`player.faction_reputation.setdefault("world", 0)`）。完了条件: 属性が無い場合でもクラッシュしない（`hasattr` でガード）。

**Step 21.** `_log(self, engine, message, color=None)` ヘルパを追加。`if engine is not None and hasattr(engine, "log"): engine.log(message, color or (255,255,255))`。完了条件: engine=None で何もしない。

**Step 22.** `_grant_currency(self, player, currency_id, amount, engine=None)` を実装。`mapped = self._CURRENCY_MAP.get(str(currency_id).lower(), KEY_GOLD)` とし、mapped に応じて gold/platinum を加算。完了条件: `special_currency="platinum"` で platinum が増える。

**Step 23.** Step 22 の `_grant_currency` 内で、未知の通貨ID のときは `self._log(engine, f"未対応の通貨: {currency_id}", (255,100,100))` として gold にフォールバックする。完了条件: 未知ID でも例外を出さない。

**Step 24.** 旧キー `special_currency` の処理を `grant_event_rewards` から `_grant_currency` に委譲する形に置き換え準備（まだ呼ばない）。完了条件: `_grant_currency` が既存ロジックと等価であることをコメントで示す。

**Step 25.** `grant_event_rewards` に `engine=None` 引数を追加（後で実体化）。このステップではシグネチャだけ変更し、呼び出し側は未修正。完了条件: 既存呼び出しがまだ壊れない（キーワード引数なので）。

**Step 26.** `_grant_gold/platinum/exp/piety` を `grant_event_rewards` 内の小さなディスパッチ（まだ gold/platinum/exp/piety キーを読むだけ）に仮配置。完了条件: 構文OK。

**Step 27.** Step 26 のコードを `try/except Exception` で囲み、失敗しても他の報酬処理を続行するようにする。完了条件: 1 つ失敗しても例外が外に漏れない。

**Step 28.** `player` が `inventory` や `gold` 属性を持たない（NPC 想定）場合のガードを各 `_grant_*` に入れる（`getattr` 使用済みなら確認）。完了条件: ダミーオブジェクトでクラッシュしない。

**Step 29.** Phase 3 の各 `_grant_*` に対するミニテストを `tests/test_reward_manager_integration.py` に書く準備（まだ空ファイルで可）。完了条件: ファイルが存在する。

**Step 30.** Phase 3 の単体チェック: `python -c "from naRou.reward_manager import RewardManager; m=RewardManager(); m._grant_gold(...)"` は後日なので、ここでは import のみ確認。完了条件: import 成功。

---

## Phase 4 — アイテム連携の実装 (Step 31〜48)

**Step 31.** `_create_item(self, item_id, quantity=1)` を追加。`item = create_sample_item(str(item_id))` を呼び、`item.count = int(quantity)` を設定して返す。完了条件: `Item` インスタンスを返す。

**Step 32.** Step 31 を `try/except` で囲み、`create_sample_item` が失敗した場合は最小の `Item(str(item_id), CAT_TOOL, "?", (200,200,200), count=int(quantity))` を返すフォールバックを追加（CAT_TOOL は item_system から import）。完了条件: 未知ID でも `Item` を返す。

**Step 33.** `_grant_item(self, player, item_id, quantity=1, engine=None)` を追加。`inv = getattr(player, "inventory", None)` を取得。完了条件: メソッド定義。

**Step 34.** Step 33 内で `if inv is None: self._log(engine, "インベントリがないためアイテムを付与できません", (255,100,100)); return` を追加。完了条件: ガードあり。

**Step 35.** Step 33 内で `item = self._create_item(item_id, quantity); ok, msg = inv.add_item(item); self._log(engine, msg)` を追加。完了条件: アイテムが inventory に入る。

**Step 36.** `_grant_items(self, player, items_dict, engine=None)` を追加。`items_dict` を `{"item_id": quantity}` とみなし、各キーで `_grant_item` を呼ぶ。完了条件: dict ループで付与。

**Step 37.** `grant_event_rewards` の `item_drops` 分岐を「既存の drop_chance ロジックを `_grant_item` に置き換える」よう書き換え。`for item_id, drop_chance in ...: if random.random() < float(drop_chance): self._grant_item(player, item_id, 1, engine)`。完了条件: ドロップ率つきで付与される。

**Step 38.** `rewards` の `items` キー（確定ドロップ）を `_grant_items` に渡す分岐を追加（drop_chance なし）。完了条件: 確定付与される。

**Step 39.** `artifact` キーを処理: `artifact_id = rewards.get("artifact")` があり `_grant_item(player, artifact_id, 1, engine)` を呼ぶ。完了条件: 1 個付与。

**Step 40.** `_grant_item` で `quantity > 1` のとき `item.count` が正しく反映されることを、`create_sample_item` の戻りに対して明示的に上書きする（Step 31 で済んでいれば確認のみ）。完了条件: スタック数が正しい。

**Step 41.** `Inventory.add_item` のスタック動作を活用していることを確認（重複アイテムは count 加算）。完了条件: 既存アイテムと同名なら新規生成しない。

**Step 42.** アイテム付与成功時に `self._log(engine, f"{item_id} を入手した。", (120,255,120))` を出す。完了条件: ログが出る。

**Step 43.** インベントリ満杯時のメッセージ（`add_item` が `False` を返す）をそのまま `engine.log` に流す。完了条件: 満杯時もクラッシュしない。

**Step 44.** プレイヤーが `inventory` 非保持のときはログのみで終了（Step 34 で済み、確認）。完了条件: NPC で安全。

**Step 45.** `_grant_item` のテスト: ダミー `player`（`.inventory` に `add_item` を持つ偽オブジェクト）を用意し、`inventory.items` に 1 件増えることを確認。完了条件: テストが通る。

**Step 46.** `_grant_items` のテスト: `{"bread": 2, "potion_heal": 1}` を渡し、合計 2 件（またはスタックで件数変動）になることを確認。完了条件: 通る。

**Step 47.** `item_drops` のテスト: `drop_chance=1.0` なら必ず付与、`0.0` なら付与されないことを確認。完了条件: 通る。

**Step 48.** インベントリなしプレイヤーで `_grant_item` を呼び、例外が出ないことをテスト。完了条件: 通る。

---

## Phase 5 — grant_event_rewards の統合 (Step 49〜57)

**Step 49.** `grant_event_rewards(self, player, event_data, engine=None)` のシグネチャを確定（Step 25 で仮追加済み）。完了条件: シグネチャ確定。

**Step 50.** `world_event_system.py:176` の呼び出しを `REWARD_MANAGER.grant_event_rewards(player, edata, engine)` に変更（`trigger_event` は `engine` 引数を持つ）。完了条件: 引数追加。

**Step 51.** `grant_event_rewards` 冒頭で `rewards = self._normalize_rewards(getattr(event_data, "rewards", {}))` を取得。完了条件: 辞書化。

**Step 52.** gold/platinum/exp/piety/fame の各キーを `_get_amount` で読み、値が 0 より大きければ対応 `_grant_*` を呼ぶ。完了条件: 各キーが反映。

**Step 53.** 旧 `special_currency` キーがあれば `_grant_currency(player, rewards[KEY_SPECIAL_CURRENCY], self._get_amount(rewards, KEY_CURRENCY_AMOUNT, 100), engine)` を呼ぶ（後方互換維持）。完了条件: 旧仕様も動く。

**Step 54.** `items` / `item_drops` / `artifact` を Phase 4 のメソッドへ委譲。完了条件: アイテム付与される。

**Step 55.** 各 `_grant_*` 呼び出しを `try/except Exception as e: self._log(engine, f"報酬付与失敗: {e}", (255,100,100))` で囲む。完了条件: 1 つ失敗してもイベント全体が止まらない。

**Step 56.** `grant_event_rewards` が付与したログ文字列の list を返すようにし（任意・拡張性）、既存呼び出し側は戻り値を無視しても良いようにする。完了条件: 戻り値は list。

**Step 57.** `grant_event_rewards` と各 `_grant_*` の docstring を書き直し、「実際のアイテム/経済システムと連携済み」と明記。完了条件: docstring 更新。

---

## Phase 6 — 他の報酬経路との整合確認 (Step 58〜66)

**Step 58.** `grep -rn "reward" naRou/procedural_quest_generator.py` し、報酬付与が `player.inventory.add_item` 等で行われている箇所（例: 1284 行付近）を確認。完了条件: 重複実装でないことを確認。

**Step 59.** `combat_manager.py` の corpse ドロップ (`Item(...)` + `entity_manager.add_item`) と RewardManager のアイテム付与が競合しないことを確認（別経路なので問題なし）。完了条件: メモだけ。

**Step 60.** `narrative_executor.py` の `grant_ending_rewards` がアイテムを付与しているか確認。付与しているなら `RewardManager` の `_grant_item` を使うようリファクタ検討（非破壊なら後回し）。完了条件: 影響範囲をメモ。

**Step 61.** `systems/skill_eater_meta_intervention_system.py:328` の `apply_rewards` が何をするか確認。完了条件: RewardManager と役割が重複しないかメモ。

**Step 62.** 同じイベントで `grant_event_rewards` が複数回呼ばれないよう、`trigger_event` 側で `player.active_world_events` への追加タイミングを確認（world_event_system.py:164-165 で既にガードあり）。完了条件: 二重付与なし。

**Step 63.** `community_goal_manager.py` の `get_goal_reward` が返す reward を RewardManager が処理する必要があるか確認。必要なら `grant_event_rewards` の入力を `event_data` だけでなく dict でも受け付けるよう `_normalize_rewards` を拡張。完了条件: dict 入力も動く。

**Step 64.** コード内の残りの `# TODO: 実際の` 系コメントを grep し、reward_manager 以外に影響するものがないか確認。完了条件: リストアップ。

**Step 65.** `reward_manager.py` の 2 つの TODO コメント（38, 42 行）を削除し、代わりに「連携済み」の短いコメントに置換。完了条件: TODO コメント消滅。

**Step 66.** Phase 1〜5 の変更で `reward_manager.py` と `world_event_system.py` が構文エラーなく import できることを `python -c "import naRou.reward_manager, naRou.systems.world_event_system"` で確認。完了条件: エラーなし。

---

## Phase 7 — テストと動作確認 (Step 67〜72)

**Step 67.** `tests/test_reward_manager_integration.py` を作成し、`import pytest` と `from naRou.reward_manager import RewardManager` を書く。完了条件: 空テストでも collect される。

**Step 68.** テスト `test_grant_gold_and_platinum`: ダミー player に `gold=0, platinum=0` をセット、`rm.grant_event_rewards(p, SimpleNamespace(rewards={"gold":100,"platinum":2}))` 後 `p.gold==100 and p.platinum==2`。完了条件: 通る。

**Step 69.** テスト `test_grant_exp`: `gain_exp` をモック/簡易実装し、`p.exp` が増えるか、または `gain_exp` が呼ばれたことを確認。完了条件: 通る。

**Step 70.** テスト `test_grant_item_and_stack`: ダミー inventory（`add_item` を本物の `Inventory` で代用）に `rewards={"items":{"bread":3}}` を渡し、該当アイテムの `count>=3` になることを確認。完了条件: 通る。

**Step 71.** `pytest tests/test_reward_manager_integration.py -q` を実行。完了条件: 全テスト緑。

**Step 72.** `pytest` 全体（または該当する既存テスト群: `test_item_*`, `test_inventory_*`, `test_phase2_social_simulation` 等）を実行し、回帰がないことを確認。その後 `CHANGELOG.md` に「RewardManager が実際のアイテム/経済システムと連携 (TODO 解消)」を追記。完了条件: 回帰なし・CHANGELOG 更新。

---

## 受け入れ基準 (Definition of Done)

1. `reward_manager.py` の `# TODO: 実際の通貨システムと連携` および `# TODO: 実際のアイテムシステムと連携` が削除され、実装されている。
2. `grant_event_rewards` が `gold`/`platinum`/`exp`/`piety`/`fame`/`items`/`item_drops`/`artifact`/`special_currency` の全キーを実際に反映する。
3. アイテムは `player.inventory` に `Item` として正しく追加（スタック込み）される。
4. `world_event_system.py` から `engine` 付きで呼ばれるようになり、付与時にログが出る。
5. `tests/test_reward_manager_integration.py` が追加され、既存テストが回帰していない。

## 注意点 (低性能 LLM 向け)

- 各ステップは「前のステップが終わっていれば 1 ファイルだけ触れば済む」ように分割済み。
- import エラーが出たら「Phase 2 の import 追加 (Step 11)」と「定数名のタイポ」を最初に疑う。
- `player` には常に `getattr(..., 0)` でアクセスし、NPC 等への誤適用でクラッシュしないよう配慮する。
- 1 ステップ終えるごとに `python -c "import naRou.reward_manager"` で構文チェックすると安全。
