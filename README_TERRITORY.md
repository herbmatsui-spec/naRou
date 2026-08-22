# SkillEaterTerritoryControl - 開発者向けドキュメント

## 概要
派閥テリトリー・勢力図システム。プレイヤーとNPC派閥が区画を巡って争う戦略層を追加。

## アーキテクチャ

### 主要クラス

| クラス | ファイル | 役割 |
|--------|---------|------|
| `District` | skill_eater_territory_system.py | 区画データ (ID, 名前, 支配派閥, 安定度, 資源, 防御, 隠し要素) |
| `TerritoryState` | skill_eater_territory_system.py | シングルトン管理クラス (区画辞書, 派閥関係, ターン処理, イベント) |
| `TerritoryController` | skill_eater_territory_system.py | アクション実行・クールダウン管理・履歴記録 |
| `TerritoryActionBase` + 実装クラス | skill_eater_territory_system.py | 5アクションの基底・具象クラス |
| `DynamicEvent` | skill_eater_territory_system.py | 4種動的イベント (戦争/裏切り/第三勢力/ミダス検挙) |
| `TerritoryMapRenderer` | skill_eater_territory_ui.py | テキスト/描画用データ生成 |
| `TerritoryActionPanel` | skill_eater_territory_ui.py | UI用アクション情報生成 |
| `TerritoryEventPanel` | skill_eater_territory_ui.py | UI用イベント情報生成 |

### 既存システムとの統合

| 既存システム | 統合ポイント |
|------------|------------|
| `FactionState` (skill_eater_economy_system.py) | 新フィールド追加: `controlled_districts`, `territory_income_per_turn`, `morale`, `is_at_war`, `war_target` |
| `SkillEaterAudioSystem` | 新規音声自動対応 (ファイル存在時のみ再生) |
| `SkillEaterPresentationSystem` | `add_event()` 連携でエモート+音声+メッセージ |
| `EventBus` | `NEW_DAY` フックでターン処理連携可能 |
| `WorldMapManager` | 区画データとマップ層の同期 (将来拡張) |
| `SaveSystem` | `territory_state` プロパティでJSONシリアライズ対応 |

## データフロー

```
Turn Start (Engine)
    ↓
TerritoryState.on_turn_start()
    ├─ 収入配分 (_distribute_turn_income)
    ├─ 安定度更新 (_update_stability)
    ├─ 失陥判定 (_check_district_loss)
    ├─ ショップ解放 (_check_shop_unlocks)
    ├─ ダンジョン発見 (_check_dungeon_reveals)
    ├─ 破壊工作処理 (_process_sabotage_effects)
    ├─ 停戦カウント (_process_ceasefire_countdown)
    ├─ 士気更新 (_update_faction_morale)
    └─ イベントトリガー (check_event_triggers)
        ├─ 派閥戦争
        ├─ 裏切り
        ├─ 第三勢力
        └─ ミダス検挙
    ↓
Turn End
    ↓
TerritoryState.on_turn_end() → 統計記録
```

## アクション詳細

| アクション | 対象 | コスト | クールダウン | 基礎成功率 | 主な効果 |
|-----------|------|--------|-------------|-----------|---------|
| PATROL | 自派閥区画 | AP1, 100アルド | 1T | 95% | 安定度+5, 資源+5% |
| RAID | 敵派閥区画 | AP3, 500アルド | 3T | 50% | 区画奪取, 影響力±50, 戦争30% |
| PROPAGANDA | 中立/敵区画(隣接) | AP2, 300アルド | 2T | 40% | 派閥変更 or 忠誠心低下 |
| SABOTAGE | 敵派閥区画 | AP3, 800アルド | 4T | 30% | 資源半減/防御-1 (3T), 発覚リスク |
| NEGOTIATE | 戦争中派閥 | AP2, 2000アルド | 5T | 35% | 停戦10T, 評判+10 |

## 動的イベント

| イベント | 発生条件 | 効果 | 解決 |
|---------|---------|------|------|
| 派閥戦争 | 影響力差<20% & 隣接≥3 | 双方士気-10, 襲撃+20%, プロパガンダ無効 | 区画数比較で勝敗 |
| 裏切り | 士気<20 & 区画≥3 | 反乱派閥独立, 親派閥影響力-300 | 鎮圧/容認/利用選択 |
| 第三勢力 | 中立≥5 & 総影響力<5000 | 新派閥出現, 中立区画2-3制圧 | 全区画失陥で撤退 |
| ミダス検挙 | 警戒度≥80 & 違法区画≥2 | 熱リセット, 違法区画中立化, 違法スキル/アルド没収 | 即時解決 |

## 設定ファイル

| ファイル | 内容 |
|---------|------|
| `data/territory_districts.yaml` | 初期区画定義 (13区画, 隣接関係, 派閥関係) |
| `data/territory_balance.yaml` | 全数値パラメータ (難易度別スケーリング込み) |

## セーブ/ロード

```python
# JSON保存時
data["territory"] = engine.territory_state.to_dict()

# JSON読込時
engine.territory_state = TerritoryState.from_dict(data["territory"])
```

pickle形式 (savegame.bin) は自動対応 (Engine に territory_state プロパティあり)

## デバッグコマンド

```python
# テリトリー状態取得
territory = TerritoryState.get_instance()

# 区画一覧
for d in territory.districts.values():
    print(f"{d.id}: {d.name} - {d.controlling_faction} (稳定度:{d.stability})")

# 派閥サマリー
from skill_eater_territory_ui import create_territory_ui
ui = create_territory_ui(territory)
summary = ui["map_renderer"].get_faction_summary()

# アクション実行
controller = TerritoryController(territory)
result = controller.execute_action("player", TerritoryActionType.PATROL, "industrial_zone")

# イベント強制発火
event = territory.trigger_event("faction_war")

# ターン処理手動実行
territory.on_turn_start(turn_number)
territory.update_events()
territory.on_turn_end()
```

## 既知の制限・今後の拡張案

### 制限
1. 区画座標システム未実装 (マップ描画はテキストベースのみ)
2. 空間音響 (`play_positional_sound`) 未連携
3. AI派閥の戦略的判断は簡易評価関数のみ
4. マルチプレイ/ネットワーク対応なし

### 拡張案
1. **区画マップ可視化**: `WorldMapManager` と連携し、ミニマップに派閥色オーバーレイ
2. **外交システム拡張**: 同盟/不可侵/貿易協定などの条約タイプ追加
3. **区画固有イベント**: 区画ごとのユニークイベント・クエスト
4. **派閥固有アクション**: 派閥ごとにユニークなテリトリーアクション
5. **シーズン/気候効果**: 季節による資源変動・移動コスト変化
6. **リプレイ/観戦モード**: ターン履歴からのリプレイ再生

## ファイル構成

```
naRou/
├── skill_eater_territory_system.py   # コアロジック (データ構造, ターン処理, アクション, イベント)
├── skill_eater_territory_ui.py       # UI連携 (描画データ, パネル情報)
├── data/
│   ├── territory_districts.yaml      # 初期区画データ
│   └── territory_balance.yaml        # バランスパラメータ
└── assets/
    ├── audio/                        # 音声ファイル (既存+新規配置)
    └── emote/pixel/style1/           # エモート画像 (既存+emote_speech.svg, emote_flag.svg)
```

## テスト手順

1. **基本動作確認**
   ```python
   territory = TerritoryState.get_instance()
   territory.load_from_yaml("data/territory_districts.yaml")
   print(territory.render_text_map())
   ```

2. **アクションテスト**
   ```python
   controller = TerritoryController(territory)
   # パトロール
   r = controller.execute_action("midas", TerritoryActionType.PATROL, "industrial_zone")
   # 襲撃
   r = controller.execute_action("resistance", TerritoryActionType.RAID, "industrial_zone")
   ```

3. **ターン処理テスト**
   ```python
   territory.on_turn_start(1)
   territory.update_events()
   stats = territory.on_turn_end()
   ```

4. **セーブ/ロードテスト**
   ```python
   from save_system import SaveSystem
   SaveSystem.save_json(engine)
   loaded_engine, _ = SaveSystem.load_json()
   ```

## 変更履歴
- v1.0.0: 初版実装 (Steps 1-72 完了)
  - Phase 1: データ構造 (Steps 1-12)
  - Phase 2: アクションシステム (Steps 13-28)
  - Phase 3: ターン処理 (Steps 29-38)
  - Phase 4: 動的イベント (Steps 39-54)
  - Phase 5: 音響・演出 (Steps 55-62)
  - Phase 6: UI・統合 (Steps 63-72)