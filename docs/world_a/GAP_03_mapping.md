# 実装実態ギャップリスト（§2 マッピング）— PLAN-03 成果物

> 出典: `docs/world_a/DESIGN_A_SKILL_EATER.md` §2（L26-65）
> 目的: §2が謳う「基底システムの本ワールド向けオーバーライド」が、実装・データ実体とどう乖離しているかを TBD 管理する。

## 調査サマリ（2026-08-20 時点）
- 基底データ `data/gods.yaml`, `factions.yaml`, `jobs.yaml`, `skill_trees.yaml`, `reincarnation.yaml`, `pet_*.yaml`（8ファイル）は**存在するが汎用・基底**であり、skill_eater 固有のオーバーライドではない。
- **skill_eater 固有データは `data/worlds/skill_eater/skills.yaml` のみ**（`data/worlds/skill_eater/` 配下はこれのみ）。
- `skill_eater_*.py` は上記基底データを**一切ロードしていない**（grep 結果空）。経済/Husk/輪廻/ROOT は Python ロジックに直接実装され、§2が想定した「基底のオーバーライド」形ではない。
- 結論: §2 は現時点では**設計意図**にとどまり、実装は「独自ロジック」として進んでいる。

## ギャップリスト

| §2項目 | 設計マッピング（意図） | 既存システム/データ | skill_eater固有データ | 実装状況 | 備考 |
|---|---|---|---|---|---|
| 2.1 概念の柱 (gods) | gods.yaml → 9柱の概念（喰った数で概念値上昇） | `data/gods.yaml`（汎用） | 未作成 | **TBD（設計のみ）** | 概念値上昇ロジック・パッシブ付与未実装 |
| 2.2 派閥 (factions) | factions.yaml → 商会/戦線/銀行/ブローカー | `data/factions.yaml`（汎用） | 未作成 | **TBD（設計のみ）** | 経済・監査レイドは `skill_eater_economy_system.py` で一部実装済だが派閥データ未 |
| 2.3 ジョブ=スキル階級 (jobs) | jobs.yaml → 6階級（奴隷〜イーター） | `data/jobs.yaml`（汎用） | 未作成 | **TBD（設計のみ）** | 階級バフ/交渉権限の実装なし |
| 2.4 喰らいツリー (skill_trees) | skill_trees.yaml → 動的ツリー | `data/skill_trees.yaml`（汎用） | 未作成 | **TBD（設計のみ）** | 動的ツリー描画(星図UI)は未実装；合成では静的/動的ノードは生成される |
| 2.5 従属スキル保有者 (pet) | pet_*.yaml → Husk従属 | `data/pet_*.yaml`（汎用, 8ファイル） | 未作成 | **TBD（設計のみ）** | Husk従属は `skill_eater_servant_system.py` で実装済だがペット基底データ未参照 |
| 2.6 輪廻転生 (reincarnation) | reincarnation.yaml → スキル継承 | `data/reincarnation.yaml`（汎用） | 未作成 | **TBD（設計のみ）** | 輪廻継承は `skill_eater_meta_quest_system.py` で一部実装済 |
| §3.1 スキル定義 (skills) | skills.yaml → スキルマスタ | — | `data/worlds/skill_eater/skills.yaml`（実体） | **実装済** | 正規パスへ統一済（PLAN-01） |

## クローズ方針（TBD解消時のアクション）
1. 各 §2 項目について「ワールド別データ `data/worlds/skill_eater/<file>.yaml` を新規作成」または「汎用 `data/*.yaml` を参照」のいずれかを決定。
2. 決定したものから順にデータファイルを追加し、本表の「実装状況」を更新。
3. 固有データを新規作成する場合は `skill_eater_*.py` 側でのロード実装も別途必要（別タスク）。
