# SkillEaterSecretAccess - 隠しエリア・秘密通路・鍵システム 実装完了

## 概要
World A（スキル喰い）における秘密検知・隠し扉・鍵アイテム・アクセス条件・報酬・音響演出を実装しました。

## 実装済み機能（全72ステップ完了）

### 1. データ基盤 (Steps 1-12)
- **定数追加**: 隠しタイル、鍵タイプ、アクセス条件、報酬タイプ、音響/エモート
- **YAMLデータ**: `secret_areas.yaml`（8つの秘密エリア）、`key_items.yaml`（15種類の鍵）
- **データクラス**: `SecretArea`, `KeyItem`, `SecretConnection`
- **レジストリ**: `SecretAreaRegistry` シングルトン
- **プレイヤー状態拡張**: 発見/解放済みシークレット、所持キー、ロア、検知失敗カウント

### 2. 検知システム (Steps 13-24)
- **知覚判定**: `perception_check()` - 知覚+解析Lv+スキルボーナス+連続失敗ペナルティ
- **自動検知**: `advance_world()` でターン毎に周囲3マス以内をチェック
- **手動検索**: `;` キーで `ActionSearch` 実行、スキルボーナス付き
- **検知種別分岐**: hidden_door/false_wall/secret_floor/vent それぞれタイル変更
- **イベント・音響・エモート**: 検知成功時に `secret_detected` イベント + `perception_success` SFX + `emote_eye.png`

### 3. 鍵・解除システム (Steps 25-36)
- **キーインベントリ**: `add_key/remove_key/has_key/get_key_count`
- **キー入手**: ダンジョン生成時（深度連動）、モンスター撃破ドロップ（5-30%）
- **解除処理**: `try_unlock_secret()` - 発見→条件→鍵→解除→報酬のフロー
- **アクセス条件**: 派閥評判/スキル保有/クエストフラグ/時間帯/犠牲(HP/スキル/アイテム)
- **鍵種別**: キーカード(Lv1-5)/生体認証(指紋/網膜/DNA)/暗号解除(Lv1-3)/物理鍵
- **解除成功時**: タイル恒久床化、`secret_unlocked` イベント + `secret_wall_slide`/`keycard_beep`/`ancient_mechanism` SFX + `emote_key.png`

### 4. 特殊移動・報酬 (Steps 37-48)
- **床下通路**: 下層へワープ移動、`ancient_mechanism` SFX
- **換気ダクト**: クロール移動（スタミナ消費）、`vent_crawl` SFXループ
- **隠し扉アニメ**: 開放時に4フレーム開放アニメーション
- **偽の壁**: 発見後通行可能、微小抵抗
- **報酬**: 禁忌スキル/コンセプト結晶/ロア/ショートカット/隠し商人
- **イベント発行**: `secret_passage_used` / `secret_unlocked`

### 5. マップ生成統合 (Steps 49-60)
- **配置フック**: `generate_dungeon()` 終了時に `_place_secret_areas()` 呼び出し
- **配置ロジック**: YAML指定位置優先、代替位置自動探索、階段除外
- **テーマ密度**: `gimmicks` パラメータで秘密密度制御（テーマ別設定済み）
- **重複回避**: 使用済み座標セット管理
- **ミニマップ統合**: `get_secret_minimap_data()` で発見済み🔓/未解除🔒表示
- **ヒント機能**: `get_secret_hint_at()` で調査時に条件表示

### 6. システム統合 (Steps 61-72)
- **セーブ/ロード**: `save_secret_registry_state()` / `load_secret_registry_state()`
- **難易度スケール**: Easy(-5)/Normal(0)/Hard(+5)/Lunatic(+10)
- **転生引き継ぎ**: 記憶の欠片で全引き継ぎ、通常は20%ランダム引き継ぎ
- **実績/称号**: first_discovery/secret_hunter/master_unlocker/key_collector/keycard_master
- **テスト**: 39ユニットテスト全パス（検知14、マップ生成10、統合15）

## ファイル構成

```
constants.py              # 定数定義
data/
  secret_areas.yaml       # 秘密エリア定義（8エリア）
  key_items.yaml          # 鍵アイテム定義（15種類）
  audio_config.yaml       # SE追加
  dungeon_themes.yaml     # gimmicks密度設定
secret_area_system.py     # コア実装（約700行）
map_engine.py             # GameMap統合（隠しタイル、アニメ、ミニマップ）
packages/gameplay/package.py  # 自動検知、キー入手、ドロップ
input_actions.py          # ActionSearch 実装
input_handler.py          # ; キー登録
world_map_manager.py      # 層間秘密移動統合
tests/
  test_secret_access.py           # 29テスト
  test_secret_map_generation.py   # 10テスト
```

## 使用方法

### プレイヤー操作
- `;` キー: 手動秘密検索（スキルボーナス付き）
- 移動時: 自動検知（周囲3マス、ターン毎）
- 隠し扉前で決定: 解除プロンプト表示 → 条件満たせば解除
- 秘密通路上で決定/方向キー: 床下ワープ/ダクトクロール

### モッダー向け拡張
1. `data/secret_areas.yaml` に新エリア追加
2. `data/key_items.yaml` に新鍵追加
3. `data/dungeon_themes.yaml` の `gimmicks` で密度調整
4. `SecretConnection` で層間接続定義

## バランス調整済み項目
- 検知難易度: 基礎15-35、知覚20+解析3で成功率約60-80%
- キードロップ: 深度1ごとに+0.5%、ボス30%
- 消費型キー: 生体/暗号は1回使用、キーカード/物理は永続
- 転生引き継ぎ: 記憶の欠片で全復元、通常20%

## テスト実行
```bash
python -m pytest tests/test_secret_access.py tests/test_secret_map_generation.py -v
# 39 passed
```

---

**実装完了日**: 2026-08-22  
**ステータス**: 全72ステップ実装完了・全テストパス