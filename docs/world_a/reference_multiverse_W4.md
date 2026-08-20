# 📎 参照：マルチバース全体設計からの W4（スキル喰い）抜粋

> 出典: `NAROU_9_WORLDS_DESIGN.md`
> このファイルは Aの世界の設計を一元化するための**抜粋コピー**です。正・最新は元ファイルを参照してください。

## W4: `skill_eater` — スキル喰い・解析チート

- **舞台**: スキル資本主義アルディナ商業連合
- **主人公ポジション**: 《解析》のみ所持のクビになった元商会社員 → スキルイーター覚醒
- **核心ギミック**:
  - 敵のスキルを「喰らって」自分のものにする
  - 《解析》でスキルツリー全構造可視化 → 弱点特定 → `devour()` で強制取得
  - 喰ったスキル同士を `synthesis()` で合成 → 概念スキル生成

### 主要データ構造（抜粋）
```yaml
devour_mechanics:
  analysis:
    reveal: ["skill_tree_full", "weakness", "synergy", "evolution_path"]
    cost_mp: 10
  devour:
    base_success: 0.6
    modifiers:
      analysis_level: "+0.05 per level"
      target_willing: "+0.3"
      target_unconscious: "+0.2"
      skill_rarity_penalty: "legendary:-0.3, unique:-0.5, concept:-0.7"
    on_success: ["acquire_skill(level=1)", "target.lose_skill() + memory_damage()"]
    on_fail: ["skill_backlash(random_debuff)", "alert_nearby_enemies()"]
  synthesis:
    cost_mp: 100
    recipes:
      - ["fire_magic", "analysis"] → "flame_structure_analysis"
      - ["sword_mastery", "devour"] → "blade_eater"
      - ["healing", "poison"] → "corrupt_healing"
      - ["*concept*", "*concept*"] → "meta_concept"
```

### 継承アイテム例（他世界への持ち出し）
- `devoured_skill_archive[]` → 次世界で初期スキルとして選択可（上限5個）
- `concept_pillar_fragment[9]` → 9柱の概念欠片。全回収で《世界編集》解放

## メタ認識フレームワーク（W4との関わり）
- **《原典閲覧》**: W4ではスキルツリー可視化・弱点特定に直結
- **《世界線引き継ぎ》**: W4 → `*` への変換ルールあり（喰ったスキルの30%を次世界初期スキルとして付与）

## 難易度（9世界中）
- W4: ★★★☆☆ — 喰い失敗リスクあり、合成試行錯誤必要
- W9（最終）到達のための核心ピースの一つ
