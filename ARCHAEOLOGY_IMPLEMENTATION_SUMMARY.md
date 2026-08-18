# 考古学・発掘・解読メタゲーム — 実装サマリー (Step 36)

## 概要
`memory_fragments.yaml`（記憶の欠片）と `story_endings.yaml`（エンディング）を `truth_codex.yaml` で
連携し、「**発掘 → 収集 → 解読 → 真理到達 → プレイヤーの解釈によるエンディング分岐**」のループを実装した。
エンディングは「正解」ではなく、プレイヤーの解釈（`interpret_truth`）に委ねられる。

## 使い方
1. ダンジョン深部で `[x]` を押すと、その深度の遺跡を発掘する（断片とデコーダー鍵をドロップ）。
   - 深度3〜: ゴブリンの廃都 / 深度10〜: 英雄の聖域 / 深度20〜: 深淵の発掘坑
2. 対応する言語族の鍵を手に入れると、自動（または次回発掘時）に断片が**解読**される。
3. ある真理ノードの要求断片がすべて解読されると**真理に到達**する。
4. `[j]` ジャーナル（考古学タブ）で進捗を確認。到達真理に「どのエンディングの視点で読むか」を解釈として記録できる。
5. `interpret_truth()` で記録した解釈が `story_flags["ending_<id>_unlocked_by_archaeology"]` を立て、
   `story_endings.yaml` の解放条件と接続される。

## ファイル構成
| ファイル | 内容 |
| :--- | :--- |
| `data/memory_fragments.yaml` | 拡張: `glyph_script`/`cipher_type`/`decoder_hint`/`truth_link` + 新規3断片（後方互換） |
| `data/archaeology_sites.yaml` | 遺跡サイト（深度・ドロッププール） |
| `data/decoder_keys.yaml` | 言語族の解読鍵 |
| `data/truth_codex.yaml` | 真理ノード（要求断片→候補エンディング） |
| `components.py` | `ArchaeologyComponent` 追加 |
| `entity.py` | `player.archaeology` プロパティ委譲 + コンポーネント初期化 |
| `save_system.py` | 後方互換フィールド登録（pickle で全体保存） |
| `archaeology_system.py` | `ArchaeologyRegistry` + `ArchaeologyManager`（ループ本体・出力） |
| `game.py` | `archaeology_manager` 登録 + `Engine.excavate()` |
| `input_handler.py` | `[x]` 発掘アクション |
| `journal_ui.py` | ジャーナル「考古学」セクション |
| `tests/test_archaeology_metagame.py` | 36ステップ検証テスト |
| `ARCHAEOLOGY_COMMUNITY_PROPOSALS.md` | コミュニティ・二次創作 9提案 |

## 拡張方法
- 新断片: `memory_fragments.yaml` に `cipher_type` と `truth_link` を付けて追加。
- 新遺跡: `archaeology_sites.yaml` に `min_depth`/`max_depth`/`fragment_pool`/`decoder_key_pool` を追加。
- 新真理: `truth_codex.yaml` に `required_decoded_fragments` と `candidate_endings`（`story_endings` の id）を追加。
- 言語族: `decoder_keys.yaml` に `cipher_type` と獲得手段を追加。

## コミュニティ・二次創作（詳細は別添）
9提案（`ARCHAEOLOGY_COMMUNITY_PROPOSALS.md`）を策定。解釈台帳は
`ArchaeologyManager.export_ledger()`（JSON）／`export_share_summary()`（Markdown）で出力可能。

## テスト
```
python -m pytest tests/test_archaeology_metagame.py -q
```
全36ステップが通過。既存 `test_meta_progression` / `test_dungeon_world_storyteller_72_steps` /
`test_reincarnation_72_steps` も引き続き通過（後方互換を維持）。

## 注意事項
- 既存 `memory_fragments.yaml` / `story_endings.yaml` のキーは削除・改名せず拡張のみ。
- `player.archaeology.collected_fragments` は `ReincarnationComponent.collected_fragments` と名前が被るため、
  プレイヤー直下のプロパティは付けず、コンポーネント経由でアクセスする。
