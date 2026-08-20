# 🗂️ Aの世界（スキル喰い / Skill Eater）ゲームデザイン 目次

このフォルダは、**Aの世界＝スキル喰い RPG** のゲームデザイン関連ドキュメントを一元化したものです。

## 📌 読み順（推奨）
1. **`DESIGN_A_SKILL_EATER.md`** — 世界観・核心メカニク・4大コアシステムの全体像（入り口）**← Aの正規設計書（world bible）**
2. **`reference_multiverse_W4.md`** — マルチバース全体設計からの「W4: skill_eater」抜粋（メタ認識・継承・難易度との関わり）
3. **`DESIGN_A_IMPLEMENTATION_PHASES.md`** / **`_PT2`** / **`_PT3`** — フェーズ別詳細実装計画
4. **`DESIGN_A_SKILLS.md`** — スキル定義・階層・Tier/Type
5. **`DESIGN_A_QUESTS.md`** — クエスト設計
6. **`DESIGN_A_NPC_DIALOGUES.md`** — NPC対話設計

## 🔗 関連（このフォルダ外・共有リソース）
- `README.md` §「Aの世界：スキル喰い 4大コアシステム」 — 概要・Webショーケース
- `NAROU_9_WORLDS_DESIGN.md` — 9世界統合設計書（W4全体・メタ認識フレームワーク・継承・難易度曲線）
- `MULTIVERSE_GAME_DESIGN.md` — マルチバース全体ゲームデザイン
- `skill_eater_*.py`（リポジトリ直下） — 設計の実体（コード）

## 📁 データ実体（設計↔実装の紐付け）
- **正規パス**: `data/worlds/skill_eater/skills.yaml` — スキル定義本体（ワールド別データは `data/worlds/<world_id>/` 配下、NAROU規約準拠）
- 設計ドキュメント内のパス表記は上記正規パスに統一済（詳細は `PLAN_01_data_path_unification.md`）

## 🧭 設計の階層と正規仕様（Canonical）

Aの世界を記述する文書が複数あるため、どれが正（canonical）かと使い分けを明記する（詳細は `PLAN_02_design_hierarchy.md`）。

| レイヤ | 文書 | 正規性・役割 | 使い分け |
|---|---|---|---|
| **A固有 詳細設計（正規）** | `DESIGN_A_SKILL_EATER.md` + `DESIGN_A_SKILLS/QUESTS/NPC/IMPLEMENTATION_PHASES` | **Aの世界の正規仕様（world bible）**。機械・物語・マッピングの詳細はこちらが主体 | A固有の仕様・数値・矛盾は本群を優先 |
| **マルチバース統合設計** | `NAROU_9_WORLDS_DESIGN.md`（W4） | 正規性は**クロスワールド領域（継承ルール・メタ認識・世界順序・難易度曲線）に限定** | 他世界との整合・引き継ぎはこちらを優先 |
| **便利抜粋（非正規）** | `reference_multiverse_W4.md` | NAROU W4 の抜粋コピー。**漂着の可能性あり** | 手軽な参照のみ。詳細は上2つへ |
| **実装（仕様の正）** | `skill_eater_*.py`（リポジトリ直下） | 最終的な挙動の正 | 文書と食い違う場合はコードを正とし、文書側を修正課題とする |

**矛盾解決ルール**: A固有メカニクスで `DESIGN_A_*` と `NAROU_9_WORLDS_DESIGN.md` W4 が衝突した場合は **DESIGN_A を優先**。クロスワールド（継承・順序・難易度）は **NAROU を優先**。数値の正規値はコードを確認のこと。
