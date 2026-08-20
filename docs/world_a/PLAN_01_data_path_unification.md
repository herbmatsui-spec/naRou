# 実装計画書：提案1 — Aの世界 データパス表記の統一

- **計画ID**: PLAN-01
- **対象提案**: 9改善提案の「1. 設計と実装のデータパス表記の統一」
- **作成日**: 2026-08-20
- **スコープ**: 設計ドキュメント側のパス表記修正（実装コードの改修は含まない／関連課題は末尾に継送）

---

## 1. 背景と問題

Aの世界（スキル喰い）のスキルデータは、実装・規約・設計ドキュメントの間でパス表記が食い違っている。

| 参照元 | 記載パス | 状態 |
|---|---|---|
| `docs/world_a/DESIGN_A_SKILL_EATER.md:70` | `data/skill_eater.yaml`（新規作成と表記） | ❌ 実体なし・規約違反 |
| `docs/world_a/DESIGN_A_SKILL_EATER.md:73`（YAML例コメント） | `# data/skill_eater.yaml` | ❌ 同上 |
| `NAROU_9_WORLDS_DESIGN.md:249` | `data/worlds/skill_eater/devour_system.yaml` | ⚠️ 規約準拠だが未存在（設計参照のみ） |
| **実体ファイル** | `data/worlds/skill_eater/skills.yaml`（先頭キー `skills:`） | ✅ 存在・運用中 |

結果として、設計を読んだ開発者が `data/skill_eater.yaml` を探しても存在せず、実体の `data/worlds/skill_eater/skills.yaml` とのズレが生じる。

---

## 2. 目標（Canonical Path の確定）

プロジェクト規約 `data/worlds/<world_id>/<file>.yaml`（NAROU設計準拠）を採用し、Aの世界の正規スキルデータパスを以下に固定する。

```
CANONICAL = data/worlds/skill_eater/skills.yaml
```

- ワールド別データは `data/worlds/<id>/` に配置（W1等の既存規約と統一）。
- スキル定義本体は `skills.yaml`（既存ファイルを正とする）。
- 今後追加される機構別ファイル（捕食/合成/経済等）も同ディレクトリ配下へ。

---

## 3. 現状調査結果（裏付け）

- `grep` 結果: 設計側でフラットパス `data/skill_eater.yaml` を参照しているのは `DESIGN_A_SKILL_EATER.md` の 2 箇所のみ（L70, L73）。
- 実体ファイル `data/worlds/skill_eater/skills.yaml` は存在し、`skills:` リスト形式で `SkillEaterRegistry.from_dict(data["skills"])` と互換。
- `skill_eater_system.py:94` の `load_from_yaml()` は汎用ローダでパス非依存。ゲーム側実行ローディングは現状テストのみ（`data_manager.py:136` に「スタンドアロン skills.yaml は未定義」の注釈あり）。

---

## 4. 実装手順

### Step 1 — 設計ドキュメントのパス修正（`DESIGN_A_SKILL_EATER.md`）
- **L70**: `### 3.1. スキルイーターシステム定義 (`data/skill_eater.yaml` 新規作成)` → `### 3.1. スキルイーターシステム定義 (`data/worlds/skill_eater/skills.yaml`)`
- **L73**: コードブロック内コメント `# data/skill_eater.yaml` → `# data/worlds/skill_eater/skills.yaml`
- 合わせて L70 付近に一文を追加：「本作のワールド別データは `data/worlds/<world_id>/` 配下に置く（NAROU_9_WORLDS_DESIGN.md 規約準拠）。スキル定義本体は既存の `skills.yaml` を正とする」

### Step 2 — 検証
- 設計ドキュメント内に `data/skill_eater.yaml`（フラット）の残存がゼロであることを `grep` で確認。
- 正規パス `data/worlds/skill_eater/skills.yaml` が一貫して参照されていることを確認。

### Step 3 — `docs/world_a/INDEX.md` へ反映（任意・軽微）
- 既存の「関連リソース」に「データ実体: `data/worlds/skill_eater/`」の記載を追記し、設計↔実体の紐付けを明記。

---

## 5. 受け入れ基準（Acceptance）

1. `docs/world_a/DESIGN_A_SKILL_EATER.md` 内に `data/skill_eater.yaml` の記載が一切ない。
2. 同ドキュメントは `data/worlds/skill_eater/skills.yaml` をスキルデータの正規パスとして参照している。
3. 修正は設計ドキュメントの表記のみ。実装コードへの影響なし（ローダはパス非依存）。

---

## 6. 影響範囲・リスク

- **影響**: 設計ドキュメント（Markdown）のみ。Python コード・YAML データ・テストの変更なし。
- **リスク**: 極低。既存の実体ファイル名を変えるわけではない（参照先を実体に合わせる方向）。
- **注意**: 本計画は「表記の統一」が目的。設計YAML例の **スキーマ**（`skill_eater_mechanics:` 型）と実体（`skills:` リスト型）の不一致は別課題（提案3・今後）とし、本計画では触れない。

---

## 7. 関連・フォローアップ（本計画外・継送）

以下は「真正の統一」のために別途対応を推奨（提案1のスコープ外）。
- **テストのハードコードパス**: `tests/*.py`（8ファイル）が `e:/narou2/data/worlds/skill_eater/skills.yaml` を絶対指定。リポジトリ相対 `data/worlds/skill_eater/skills.yaml` への置換を推奨（別計画 PLAN-01b）。
- **未存在参照**: `NAROU_9_WORLDS_DESIGN.md:249` の `devour_system.yaml` は設計上言及されるが未作成。作成するか「計画中/TBD」と明記するか要決定（9世界統合計画と連動）。
- **実行時ローディング**: ゲーム本番で `skills.yaml` を `data/worlds/skill_eater/skills.yaml` から正規ロードする記述の整備（実装フェーズと連動）。
