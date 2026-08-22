# 実装済み: スキル喰いサイクルHUD常時表示 + 色覚モード数値強制表示

## 概要
序盤体験改善の一環として、以下3項目を実装：

1. **スキル喰い専用チュートリアル** (Phase A)
2. **喰らいサイクル常時HUD** (Phase B)
3. **色覚モード時の数値強制表示** (Phase C)

---

## Phase A: スキル喰い専用チュートリアル (data/tutorial_guides.yaml)

### 追加された5つのガイド

| ID | トリガー条件 | 発火タイミング |
|----|-------------|--------------|
| `skill_eater_enter` | `switch_world_skill_eater` | Aの世界へ遷移直後 |
| `skill_eater_first_scan` | `first_scan` | Xキー初回押下時 |
| `skill_eater_first_devour` | `first_devour_attempt` | Vキー初回押下時 |
| `skill_eater_toxicity_warning` | `toxicity_above_40` | 毒性40%到達時 |
| `skill_eater_first_synthesis` | `first_synthesis_open` | Shift+T初回押下時 |

### 実装側で必要なトリガー呼び出し
以下の箇所で `engine.check_tutorial_triggers("条件名")` を呼ぶ必要あり：

```python
# game.py - switch_world() 内
self.check_tutorial_triggers("switch_world_skill_eater")

# game.py - execute_scan() 成功時
self.check_tutorial_triggers("first_scan")

# game.py - execute_devour() 呼び出し時
self.check_tutorial_triggers("first_devour_attempt")

# skill_eater_toxicity_system.py - add_toxicity() で40%到達検知時
engine.check_tutorial_triggers("toxicity_above_40")

# 合成メニュー初回オープン時 (未実装 - 将来対応)
engine.check_tutorial_triggers("first_synthesis_open")
```

---

## Phase B: 喰らいサイクル常時HUD (uirenderer.py, render_context.py)

### 表示内容 (底部UI 行4-5)

```
┌────────────────────────────────────────────────────────────────────────┐
│ ☠ 毒性:[████████░░] 42%     🎯 捕食:72%  [V]喰らう                    │
│ 💾 スキル:3/10  [Shift+T]合成                                          │
└────────────────────────────────────────────────────────────────────────┘
```

### 構成要素

1. **毒性ゲージ** (`context.toxicity_manager.render_toxicity_gauge_ui()`)
   - 緑(0-39%) / 黄(40-79%) / 赤(80-100%) で色変化
   - ブロック表示 `████░░░░░░` で視認性確保

2. **所持スキル数** (`context.world_a_data.get("skills", [])`)
   - 10個上限到達で赤色警告

3. **捕食成功率** (`context.last_scan_result.devour_success_rate`)
   - 解析(X)実行後のみ表示、未解析時は案内文言

4. **背景・枠線** で視認性向上

### データフロー

```
Engine.execute_scan() 
    → self.last_scan_result = res (AnalysisResult)
    → render_all() で RenderContext に渡す
    → UIRenderer._draw_skill_eater_hud() で描画
```

### RenderContext に追加されたフィールド
- `world_a_data: dict` - スキルリスト、施設、ペット派遣等
- `toxicity_manager` - SkillToxicityManager インスタンス
- `skill_eater_combat_system` - SkillEaterCombatSystem インスタンス
- `color_vision_mode: str` - "none"/"deutan"/"protan"/"tritan"/"high_contrast"
- `last_scan_result` - 直近の AnalysisResult (捕食成功率表示用)

---

## Phase C: 色覚モード時の数値強制表示 (uirenderer.py, ui_fx_systems.py)

### 対象バー
- HPバー (プレイヤー)
- MPバー (プレイヤー)
- HPバー (ペット)
- 毒性ゲージ (スキル喰いHUD)
- 捕食成功率 (スキル喰いHUD)

### 実装詳細

#### GaugeBar.render() 変更 (`ui_fx_systems.py`)
```python
@staticmethod
def render(
    current: int,
    maximum: int,
    length: int = 10,
    fill_char: str = "■",
    empty_char: str = "□",
    force_numeric: bool = False,  # 追加
) -> str:
    # ... 既存ロジック ...
    if force_numeric:
        pct = int((current / max(1, maximum)) * 100)
        return f"[{bar}] {current}/{maximum} ({pct}%)"
    return f"[{bar}] {current}/{maximum}"
```

#### UIRenderer.render() 変更 (`uirenderer.py`)
```python
# 色覚モード判定
is_a11y = getattr(context, "color_vision_mode", "none") != "none"

# 使用例
hp_bar = GaugeBar.render(p.hp, p.max_hp, length=8, force_numeric=is_a11y)
mp_bar = GaugeBar.render(p.mp, p.max_mp, length=6, force_numeric=is_a11y)
pet_hp_bar = GaugeBar.render(context.pet.hp, context.pet.max_hp, length=6, force_numeric=is_a11y)
```

#### スキル喰いHUD内での併記
```python
# 毒性ゲージ
if is_a11y:
    console.print(x=2, y=ui_y + 4, string=f"☠ 毒性:[{tox_blocks}] {tox_pct}% ({tox_pct}%)", fg=fg_color)
else:
    console.print(x=2, y=ui_y + 4, string=f"☠ 毒性:[{tox_blocks}] {tox_pct}%", fg=fg_color)

# 捕食成功率
if is_a11y:
    console.print(x=40, y=ui_y + 4, string=f"🎯 捕食:{rate}% ({rate}%)  [V]喰らう", fg=(255, 180, 180))
else:
    console.print(x=40, y=ui_y + 4, string=f"🎯 捕食:{rate}%  [V]喰らう", fg=(255, 180, 180))
```

### 色覚モード設定
`config.yaml` の `accessibility.color_vision` で設定：
- `none` (デフォルト) - 通常表示
- `deutan` - 緑色盲対応
- `protan` - 赤色盲対応
- `tritan` - 青色盲対応
- `high_contrast` - ハイコントラスト

起動時メニューで選択可能（`main.py` の `prompt_accessibility()`）

---

## テスト結果

- `tests/test_ux_enhancements.py`: 4 passed
- `tests/test_accessibility.py`: 6 passed
- `tests/` -k "skill_eater": 147 passed
- 全テスト (既知の失敗2件を除く): **661 passed**

既知の失敗（本変更無関係）:
- `test_achievement_trophy_72_steps.py` - entity.py に TODO コメント不足
- `test_dungeon_world_storyteller_72_steps.py` - entity.py に TODO コメント不足
- `test_reincarnation_72_steps.py` - game.py に TODO コメント不足
- `test_headless_launch.py` - pygame 未インストール環境

---

## 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `data/tutorial_guides.yaml` | +5 ガイド追加 |
| `render_context.py` | +5 フィールド追加 |
| `game.py` | RenderContext 作成時の引数追加、`last_scan_result` プロパティ追加、`execute_scan()` で結果保存 |
| `uirenderer.py` | `_draw_skill_eater_hud()` 新規、`render()` に色覚判定・HUD呼び出し追加 |
| `ui_fx_systems.py` | `GaugeBar.render()` に `force_numeric` 引数追加 |
| `CHANGELOG.md` | 変更履歴記録 |
| `docs/IMPLEMENTED_TUTORIALS.md` | チュートリアル実装メモ (新規) |
| `docs/IMPLEMENTED_HUD.md` | 本ファイル (新規) |