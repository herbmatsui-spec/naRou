# SkillEaterBlackMarketNetwork - 詳細実装計画 (72ステップ)

## 概要
既存の `skill_eater_economy_system.py` を拡張し、4つの闇市場拠点、動的価格システム、密輸ルート、専売品、演出システムを実装する。

---

## フェーズ 1: データ構造・基盤クラス (Steps 1-12)

### Step 1: BlackMarketLocation データクラス定義
```python
@dataclass
class BlackMarketLocation:
    id: str
    name: str
    district: str  # "slum", "cyber", "midas_back", "mobile"
    base_demand_factor: float = 0.0
    base_supply_factor: float = 0.0
    heat_penalty: float = 0.0
    faction_rep_bonus: dict[str, float] = field(default_factory=dict)
    specialty_items: list[str] = field(default_factory=list)  # 専売品IDリスト
    is_mobile: bool = False
    current_position: tuple[int, int] | None = None  # 移動型用
    unlock_condition: str | None = None  # 解放条件
    is_unlocked: bool = False
```

### Step 2: SmuggleRoute データクラス定義
```python
@dataclass
class SmuggleRoute:
    id: str
    origin_id: str
    destination_id: str
    risk_level: int  # 1-10
    base_profit_per_turn: int
    heat_generation_per_turn: int
    contraband_types: list[str]  # 取扱い可能な違法品タイプ
    is_active: bool = True
    turns_remaining: int = 0  # 0=永続
    established_turn: int = 0
```

### Step 3: ContrabandItem データクラス定義 (専売品)
```python
@dataclass
class ContrabandItem:
    id: str
    name: str
    type: str  # "illegal_skill", "concept_crystal", "forbidden_data_chip"
    base_price: int
    rarity: str  # "common", "rare", "unique", "legendary"
    source_locations: list[str]  # 入手可能な拠点
    route_restrictions: list[str]  # 密輸ルート制限
    heat_risk: int  # 所持時の警戒度増加/ターン
    description: str = ""
```

### Step 4: MarketPriceSnapshot データクラス定義 (価格履歴)
```python
@dataclass
class MarketPriceSnapshot:
    location_id: str
    item_id: str
    turn: int
    final_price: int
    demand_factor: float
    supply_factor: float
    heat_penalty: float
    faction_bonus: float
```

### Step 5: BlackMarketNetwork クラス作成 (新規ファイル: skill_eater_black_market.py)
- シングルトンパターンで実装
- 既存の `SkillEaterEconomySystem` と連携
- Audio/Presentation システム統合

### Step 6: 4拠点の初期化データ定義
| 拠点ID | 名称 | 地区 | 専門 | 解放条件 |
|--------|------|------|------|----------|
| `underground_bazaar` | UndergroundBazaar | スラム | 違法スキル | 初期解放 |
| `neon_data_haven` | NeonDataHaven | サイバー地区 | 禁忌データチップ | レジスタンス評判 30+ |
| `midas_black_vault` | MidasBlackVault | ミダスタワー裏 | コンセプト結晶 | ミダス敵対 + 闇資金 50000+ |
| `mobile_caravan` | MobileCaravan | 移動型 | 全種ランダム | 特定クエスト完了 |

### Step 7: 初期密輸ルート定義 (6ルート)
1. `bazaar_to_haven`: Bazaar → Haven (リスク3, 利益500/ターン, 違法スキル/データチップ)
2. `haven_to_vault`: Haven → Vault (リスク5, 利益1200/ターン, データチップ/結晶)
3. `vault_to_bazaar`: Vault → Bazaar (リスク7, 利益2000/ターン, 結晶/違法スキル)
4. `caravan_cycle`: Caravan巡回 (リスク4, 利益800/ターン, 全種)
5. `bazaar_to_vault_direct`: 直行便 (リスク8, 利益3000/ターン, 結晶のみ)
6. `emergency_evac`: 緊急避難 (リスク10, 利益0, 全種・熱逃れ用)

### Step 8: 専売品初期データ定義 (12アイテム)
| ID | 名称 | タイプ | 価格 | 入手拠点 | 制限ルート |
|----|------|--------|------|----------|------------|
| `ill_skill_01` | 《影縫い》 | illegal_skill | 15000 | Bazaar | bazaar_to_haven |
| `ill_skill_02` | 《記憶泥棒》 | illegal_skill | 22000 | Bazaar | bazaar_to_vault_direct |
| `ill_skill_03` | 《魂喰らい》 | illegal_skill | 50000 | Vault | vault_to_bazaar |
| `crystal_01` | 《暴食の概念結晶》 | concept_crystal | 80000 | Vault | haven_to_vault |
| `crystal_02` | 《虚無の概念結晶》 | concept_crystal | 120000 | Vault | vault_to_bazaar |
| `chip_01` | 《MIDAS人体実験記録》 | forbidden_data_chip | 30000 | Haven | bazaar_to_haven |
| `chip_02` | 《スキル銀行暗号鍵》 | forbidden_data_chip | 45000 | Haven | haven_to_vault |
| `chip_03` | 《覚醒プロトコル原本》 | forbidden_data_chip | 100000 | Caravan | caravan_cycle |
| `ill_skill_04` | 《死者の囁き》 | illegal_skill | 35000 | Caravan | caravan_cycle |
| `crystal_03` | 《終焉の概念結晶》 | concept_crystal | 200000 | Caravan | emergency_evac |
| `chip_04` | 《世界の裏設定ログ》 | forbidden_data_chip | 75000 | Caravan | caravan_cycle |
| `ill_skill_05` | 《因果律切断》 | illegal_skill | 150000 | Vault | vault_to_bazaar |

### Step 9: 動的価格計算メソッド実装
```python
def calculate_dynamic_price(
    self, 
    location: BlackMarketLocation, 
    item: ContrabandItem,
    player_faction_reps: dict[str, int]
) -> tuple[int, dict]:
    """
    価格 = base_price * (1 + demand_factor - supply_factor + heat_penalty + faction_rep_bonus)
    戻り値: (最終価格, 計算内訳dict)
    """
```

### Step 10: 需要・供給ファクター更新ロジック
- 売却時: supply_factor += 0.05, demand_factor -= 0.02
- 購入時: demand_factor += 0.05, supply_factor -= 0.02
- ターン経過: 自然回復 (demand/supply 0.01ずつ中立へ)
- 最大±0.5でクランプ

### Step 11: 派閥評判ボーナス計算
- broker派閥: +評判×0.002 (最大+0.2)
- resistance派閥: +評判×0.001 (最大+0.1, データチップのみ)
- midas派閥: -評判×0.003 (敵対時ペナルティ, 最大-0.3)
- bank派閥: 中立

### Step 12: 警戒度ペナルティ計算
- heat_penalty = min(0.5, current_heat × 0.005)
- heat_level 100で価格1.5倍

---

## フェーズ 2: 拠点管理・解放システム (Steps 13-20)

### Step 13: 拠点解放判定メソッド
```python
def check_location_unlock(self, location_id: str, player: CharacterState) -> bool
```

### Step 14: 移動型拠点 (MobileCaravan) 位置更新ロジック
- 5ターンごとにランダム移動 (4地区間)
- 現在位置に応じて専売品ローテーション
- 位置表示用座標管理

### Step 15: 拠点ステータス取得メソッド
```python
def get_location_status(self, location_id: str) -> dict
# 返却: 解放状態, 現在価格補正, 専売品リスト, 熱ペナルティ等
```

### Step 16: 拠点間移動コマンド実装
- 移動コスト (アルド/ターン)
- 移動中の遭遇イベント (ランダム)
- 高熱時は移動制限

### Step 17: 拠点固有イベント生成
- Bazaar: "露天商の噂話" (価格ヒント)
- Haven: "ハッカー集会" (データチップ割引)
- Vault: "裏金融セミナー" (結晶レアドロップ情報)
- Caravan: "行商人の特別セール" (全品10%オフ)

### Step 18: 拠点レベル/アップグレードシステム
- 取引額累計でレベルアップ
- レベルごとに: 価格補正改善, 専売品追加, 熱ペナルティ軽減

### Step 19: 拠点UI表示用データ整形
```python
def format_location_for_ui(self, location_id: str) -> dict
# UI表示用に整形: 名前, アイコン, 価格傾向, 在庫, 解放進捗
```

### Step 20: 拠点データ永続化対応
- to_dict()/from_dict() 実装
- セーブ/ロード対応

---

## フェーズ 3: 密輸ルートシステム (Steps 21-30)

### Step 21: 密輸ルート確立メソッド
```python
def establish_smuggle_route(
    self, 
    origin_id: str, 
    destination_id: str, 
    risk_level: int,
    initial_investment: int
) -> tuple[bool, str]
```
- 投資額に応じて成功率変動
- リスクレベルで発覚確率決定

### Step 22: ルート自動搬入処理 (ターン処理)
```python
def process_smuggle_routes_turn_end(self) -> list[dict]
```
- アクティブルート毎に:
  - 利益加算 (alodo_currency)
  - 熱上昇 (heat_level)
  - 発覚判定 (リスク×ターン数で累積)
  - 発覚時: ルート閉鎖, 熱大幅上昇, 投資損失

### Step 23: 発覚リスク計算
- 基礎発覚率 = risk_level × 0.02 / ターン
- 同一ルート継続で +0.01/ターン累積
- 派閥評判で軽減 (broker +20で -30%)

### Step 24: ルート強制終了・撤退メソッド
```python
def abandon_smuggle_route(self, route_id: str) -> tuple[int, str]
```
- 投資回収率計算 (経過ターン/想定ターン)
- 撤退時の熱上昇 (最小限)

### Step 25: ルートアップグレード (投資追加)
- 追加投資でリスク低減/利益増加
- 最大リスク1まで低減可能

### Step 26: ルート一覧取得・フィルタリング
```python
def get_active_routes(self) -> list[dict]
def get_available_routes(self, origin_id: str) -> list[dict]
```

### Step 27: 専売品別ルート制限チェック
- アイテムごとに許可ルート指定
- 違反搬入時: 発覚率2倍, 利益半減

### Step 28: 緊急避難ルート (emergency_evac) 特殊処理
- 熱80以上で自動解放
- 利益0だが熱を-30/ターン減少
- 3ターンで完了, ルート消滅

### Step 29: 密輸ルート収支レポート生成
```python
def generate_smuggle_report(self) -> str
# ターン収支, 累積利益, リスク状況, 推奨アクション
```

### Step 30: ルートデータ永続化対応

---

## フェーズ 4: 取引システム・動的価格統合 (Steps 31-40)

### Step 31: 闇市場購入メソッド
```python
def buy_from_black_market(
    self, 
    player: CharacterState, 
    location_id: str, 
    item_id: str,
    quantity: int = 1
) -> tuple[bool, int, str, dict]
```
- 価格計算 (動的価格適用)
- 在庫確認 (専売品は無限だが購入制限あり)
- アルド支払い, アイテム付与
- Emote/Audio演出: hologram_ui_open.ogg + emote_graph_up.png

### Step 32: 闇市場売却メソッド (既存 sell_skill_to_black_market 拡張)
- 専売品も売却可能 (買取価格 = 動的価格 × 0.6)
- 違法スキル売却時の熱上昇調整
- Emote/Audio演出: credits_transfer.ogg + emote_cash.png

### Step 33: 在庫システム実装
- 拠点ごとの在庫数管理 (初期在庫 + 密輸補充 - 売上)
- 密輸ルートからの自動補充
- 売り切れ時の入荷待ち通知

### Step 34: 大量取引割引/プレミアム
- 5個以上: 5%割引
- 10個以上: 10%割引
- 違法品まとめ売り: 熱ペナルティ軽減

### Step 35: 価格履歴記録・グラフデータ生成
- 過去20ターン分の価格推移保存
- UIグラフ描画用データ出力
- emote_graph_up.png 使用

### Step 36: 取引履歴ログ
- 全取引記録 (時刻, 拠点, アイテム, 価格, 数量)
- 後で分析/アチーブメント用

### Step 37: 闇市場専用通貨/換金レート (オプション)
- "シャドークレジット" 導入検討
- アルド⇔クレジット変換 (手数料あり)

### Step 38: 取引時の派閥評判変動
- broker: +1~3/取引
- resistance: データチップ購入で+2
- midas: 結晶購入で-5 (敵対時)

### Step 39: 違法品所持ペナルティ (ターン終了時)
- 所持違法品数 × heat_risk を heat_level に加算
- 概念結晶は熱リスク2倍
- セーフハウスで軽減可能

### Step 40: 取引キャンセル/返品システム (制限付き)
- 1ターン以内なら80%返金
- 違法品は返品不可

---

## フェーズ 5: 演出システム統合 (Steps 41-52)

### Step 41: 新規Audioファイル確認・追加
必要ファイル (assets/audio/):
- hologram_ui_open.ogg (ホログラムUI開く音)
- credits_transfer.ogg (クレジット送金音)
- encrypted_comms.ogg (暗号通信音)
- ※ 既存: handleCoins.ogg, doorClose_1.ogg, metalClick.ogg 等使用

### Step 42: 新規Emoteファイル確認・追加
必要ファイル (assets/emote/pixel/style1/):
- emote_graph_up.png (価格上昇/グラフ)
- emote_lock.png (ロック/暗号/制限)
- ※ 既存: emote_cash.png, emote_alert.png, emote_cross.png, emote_exclamations.png 等使用

### Step 43: 黒市場専用PresentationEvent定数定義
```python
BLACK_MARKET_EVENTS = {
    "ui_open": ("emote_graph_up.png", "hologram_ui_open.ogg"),
    "buy_success": ("emote_cash.png", "credits_transfer.ogg"),
    "sell_success": ("emote_cash.png", "handleCoins.ogg"),
    "route_establish": ("emote_exclamations.png", "encrypted_comms.ogg"),
    "route_profit": ("emote_stars.png", "credits_transfer.ogg"),
    "route_detected": ("emote_alert.png", "metalLatch.ogg"),
    "route_abandon": ("emote_cross.png", "doorClose_1.ogg"),
    "price_surge": ("emote_graph_up.png", "hologram_ui_open.ogg"),
    "contraband_get": ("emote_heart.png", "encrypted_comms.ogg"),
    "heat_warning": ("emote_alert.png", "metalClick.ogg"),
}
```

### Step 44: 拠点UI開閉演出
```python
def play_location_enter(self, location_id: str)
def play_location_exit(self, location_id: str)
```

### Step 45: 購入成功演出 (アイテムタイプ別)
- 違法スキル: emote_cash + credits_transfer + "違法スキル《XXX》を入手！"
- 概念結晶: emote_heart + encrypted_comms + "概念結晶《XXX》が輝く…"
- データチップ: emote_graph_up + hologram_ui_open + "禁忌データ《XXX》を解読"

### Step 46: 売却成功演出
- 通常: emote_cash + handleCoins
- 違法品: emote_cash + doorClose_1 + 熱警告

### Step 47: 密輸ルート確立演出
- emote_exclamations + encrypted_comms + "密輸ルート確立: XXX → YYY (リスク: Z)"

### Step 48: 密輸利益自動収入演出 (ターン終了時)
- emote_stars + credits_transfer + "密輸ルート『XXX』から YYY アルドの利益！"

### Step 49: 密輸発覚演出
- emote_alert + metalLatch (連続3回) + "【発覚！】密輸ルート『XXX』がミダスに察知された！"

### Step 50: 価格変動演出 (大幅変動時)
- 前ターン比 ±20%以上: emote_graph_up + hologram_ui_open
- "需給変動: 《XXX》が YY% 変動 (現在: ZZZ アルド)"

### Step 51: 高熱警告演出
- heat_level 70以上: emote_alert + metalClick (定期的)
- "警戒度危険水域: XXX/100"

### Step 52: 移動型拠点遭遇演出
- Caravan発見: emote_idea + bookOpen + "移動闇市場『MobileCaravan』を発見！現在地: XXX地区"

---

## フェーズ 6: 統合・既存システム連携 (Steps 53-60)

### Step 53: SkillEaterEconomySystem への統合メソッド追加
```python
# 既存クラスにメソッド追加 (継承 or 委譲)
def open_black_market(self, location_id: str) -> dict
def buy_contraband(self, player: CharacterState, location_id: str, item_id: str) -> tuple[bool, str]
def sell_contraband(self, player: CharacterState, location_id: str, item_id: str) -> tuple[bool, str]
def establish_route(self, origin: str, dest: str, risk: int, investment: int) -> tuple[bool, str]
def get_market_prices(self, location_id: str) -> dict
```

### Step 54: ターン終了処理への統合
- 既存 `process_turn_end` または新規メソッドで:
  - 密輸ルート自動処理
  - 需要供給自然回復
  - 違法品所持熱上昇
  - 移動拠点位置更新
  - 拠点イベント発生判定

### Step 55: 派閥システム連携強化
- 既存 FactionState 拡張 (black_market_affinity 追加)
- 派閥クエストで拠点解放/ルート優遇

### Step 56: 監査官急襲 (既存 check_inspector_raid) 連携
- 密輸発覚時の熱上昇で急襲トリガー
- ルート発覚 = 即座に heat_level += 30

### Step 57: セーフハウス休憩時の熱減衰連携
- 既存 SafehouseLocation.rest_at_safehouse() で密輸熱も減衰
- 密輸ルート維持コスト免除

### Step 58: スキルアーカイブシステム連携
- 違法スキルはアーカイブ不可 (または熱ペナルティ付きで可)
- 概念結晶はアーカイブ時特殊効果

### Step 59: 戦闘ドロップへの専売品追加
- 特定敵から概念結晶/データチップドロップ
- 闇市場で高値売却可能

### Step 60: セーブ/ロード完全対応
- BlackMarketNetwork 状態完全保存
- 既存セーブ形式との互換性維持

---

## フェーズ 7: テスト・検証・調整 (Steps 61-72)

### Step 61: 単体テスト - 価格計算
```python
def test_dynamic_price_calculation():
    # 基礎価格10000, demand=0.2, supply=0.1, heat=0.05, faction=0.1
    # 期待: 10000 * 1.25 = 12500
```

### Step 62: 単体テスト - 密輸ルート収支
```python
def test_smuggle_route_profit():
    # リスク3, 投資10000, 5ターン運用
    # 期待利益: 500*5 - 熱コスト - 発覚リスク期待値
```

### Step 63: 単体テスト - 拠点解放条件
```python
def test_location_unlock_conditions():
    # 各拠点の解放条件検証
```

### Step 64: 単体テスト - 移動拠点ローテーション
```python
def test_mobile_caravan_movement():
    # 5ターンごとに移動, 専売品ローテーション確認
```

### Step 65: 統合テスト - 全拠点巡回取引
```python
def test_full_market_cycle():
    # Bazaar→Haven→Vault→Caravan で全専売品購入→売却
    # 利益確認, 熱管理確認
```

### Step 66: 統合テスト - 密輸ルート複数並行運用
```python
def test_parallel_smuggle_routes():
    # 3ルート同時運用, 発覚リスク分散確認
```

### Step 67: 統合テスト - 高熱時の緊急避難
```python
def test_emergency_evacuation():
    # heat=85で緊急避難ルート発動, 熱減衰確認
```

### Step 68: 演出テスト - 全イベント発火確認
```python
def test_all_presentation_events():
    # 各演出が正しいEmote/Audioで発火するか
```

### Step 69: バランス調整 - 価格パラメータチューニング
- 基礎価格, 需要供給変動幅, 派閥ボーナス係数
- プレイテストで経済破綻しない範囲に調整

### Step 70: バランス調整 - 密輸リスク/リターン
- リスクレベル別期待値計算
- 高リスク高リターンが成立するか確認

### Step 71: エッジケーステスト
- アルド不足時, 在庫切れ, 解放前アクセス, 同時多発発覚等

### Step 72: 総合動作確認・ドキュメント更新
- エンドツーエンドプレイテスト
- README/実装メモ更新
- 既存テストスイート全通過確認 (pytest)

---

## 実装順序の推奨

### 必須パス (最小実装): Steps 1-12, 21-24, 31-32, 41-46, 53-54, 60
→ これで基本的な闇市場売買+密輸ルートが動作

### 推奨パス: 必須 + Steps 13-20, 25-30, 33-40, 47-52, 55-59, 61-72
→ 完全な機能セット

### 開発時の注意点
1. **既存コード破壊禁止**: 既存メソッドシグネチャ変更不可、追加のみ
2. **シングルトン維持**: `_instance` パターン継続
3. **Audio/Emote欠損耐性**: ファイルなしでもエラーにしない (ログのみ)
4. **型ヒント完全**: 全メソッドに型アノテーション
5. **ドキュメント文字列**: 全publicメソッドにdocstring

---

## ファイル構成 (最終形)

```
naRou/
├── skill_eater_black_market.py      # 新規: メインシステム (約500行)
├── skill_eater_economy_system.py    # 既存: 統合メソッド追加 (約100行追加)
├── skill_eater_system.py            # 既存: 変更なし
├── skill_eater_audio_system.py      # 既存: 変更なし
├── skill_eater_presentation_system.py # 既存: 変更なし
├── assets/audio/
│   ├── hologram_ui_open.ogg         # 追加必要
│   ├── credits_transfer.ogg         # 追加必要
│   └── encrypted_comms.ogg          # 追加必要
└── assets/emote/pixel/style1/
    ├── emote_graph_up.png           # 追加必要
    └── emote_lock.png               # 追加必要
```

---

## 依存関係まとめ

| 新規クラス | 依存元 | 用途 |
|-----------|--------|------|
| BlackMarketNetwork | SkillEaterEconomySystem | 闇市場全般管理 |
| BlackMarketLocation | BlackMarketNetwork | 拠点データ |
| SmuggleRoute | BlackMarketNetwork | 密輸ルートデータ |
| ContrabandItem | BlackMarketNetwork | 専売品データ |
| MarketPriceSnapshot | BlackMarketNetwork | 価格履歴 |

---

## 完了基準

- [ ] 4拠点すべてアクセス可能
- [ ] 動的価格が需給/熱/派閥で変動
- [ ] 密輸ルート確立・自動収益・発覚リスク動作
- [ ] 12種専売品が適切な拠点/ルートで取引可能
- [ ] 指定Audio/Emoteが対応イベントで再生
- [ ] 既存テスト全通過 + 新規テスト追加
- [ ] セーブ/ロード正常動作