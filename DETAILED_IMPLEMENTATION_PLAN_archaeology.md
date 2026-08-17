# 「考古学・発掘・解読」メタゲーム 実装計画書（詳細版：ステップ1-36）

## 概要
本計画は、`memory_fragments.yaml`（記憶の欠片）と `story_endings.yaml`（ストーリーエンディング）を
連携させ、「**断片収集 → 解読 → 真実到達 → プレイヤーの解釈によるエンディング分岐**」という
考古学ループを実装する。単なるクリア報酬ではなく、謎解きと考察を最大化し、コミュニティ議論と
二次創作を喚起する設計を目指す。既存の ECS（`SystemManager` / `BaseSystem`）および YAML データ駆動
アーキテクチャに準拠し、後方互換を維持する。

## 前提条件
- Python 3.10以上、既存 naRou プロジェクト環境、`PyYAML`
- 既存 `components.py` / `game.py` / `save_system.py` / `DataManager` の規約を踏襲
- `memory_fragments.yaml` / `story_endings.yaml` の既存キーを削除・改名しない（拡張のみ）

---

## フェーズA: 分析と設計（ステップ1-5）

**ステップ1: 既存2 YAML の構造を分析し考古学ループを定義**
- `memory_fragments.yaml` の `trigger_conditions` / `unlock_requirement` / `resolution_paths` を確認
- `story_endings.yaml` の `unlock_conditions` / `ending_scene` / `rewards` を確認
- ループを「発掘(遺跡) → 収集(断片) → 解読(グリフ) → 真理(コーデックス) → 解釈(エンディング)」と定義

**ステップ2: 拡張スキーマを設計**
- 断片に `glyph_script`（暗号文字列）・`cipher_type`（言語族）・`decoder_hint`・`truth_link` を追加
- 真理コーデックスで「必要解読断片集合 → 真理ノード → 候補エンディング群」を定義

**ステップ3: 統合ポイントを洗い出し**
- コンポーネント:`components.py` に `ArchaeologyComponent` を新設
- エンティティ:`entity.py` にプロパティ追加
- 永続化:`save_system.py` のスキーマへフィールド追加
- 登録:`game.py` の `systems_mgr.register("archaeology_manager", ...)`

**ステップ4: 成功基準とテスト戦略を策定**
- 成功基準: 1周のループ（発掘→真理到達→解釈記録）が自動テストで完遂する
- `tests/test_archaeology_metagame.py` を 36ステップ形式で作成

**ステップ5: 作業 TODO と進捗管理を決定**
- 本リポジトリの TODO リストにフェーズ A-F を登録し、順次完了印を付ける

---

## フェーズB: データ層（ステップ6-14）

**ステップ6: `memory_fragments.yaml` を拡張（後方互換）**
- 既存 `goblin_child_screams` / `ancient_hero_memory` に `glyph_script`・`cipher_type`・`decoder_hint`・`truth_link` を付与
- 新規断片 `sunken_civ_tablet` / `star_chart_shard` / `traitor_kings_will` を3件追加
- 各断片は `truth_link` で真理ノードと結びつく

**ステップ7: `data/archaeology_sites.yaml` を作成**
- 遺跡サイト定義:`id`・`name`・`min_depth`・`max_depth`・`fragment_pool`（重み付き）・`decoder_key_pool`
- 例:`goblin_ruins`（深度3-）・`hero_sanctum`（深度10-）・`abyssal_dig`（深度20-）

**ステップ8: `data/decoder_keys.yaml` を作成**
- 言語族（例:`goblin_rune`・`heroic_glyph`・`abyssal_script`）ごとに鍵を定義
- 鍵の獲得手段:`drop_from_site` / `quest_reward` / `trade` を記述

**ステップ9: `data/truth_codex.yaml` を作成**
- `truth_nodes`: 各ノードに `required_decoded_fragments`（リスト）と `candidate_endings`（story_endings の id 群）
- 例:`truth_of_coexistence` は goblin/hero 系断片を要求し `goblin_peace_bringer` 等を候補に

**ステップ10: `components.py` に `ArchaeologyComponent` を追加**
- フィールド:`excavated_sites`・`collected_fragments`・`decoded_fragments`・`owned_keys`・`reached_truths`・`interpretation_notes`・`leaned_endings`

**ステップ11: `entity.py` にプロパティを追加**
- `archaeology` プロパティで `ArchaeologyComponent` を取得（StorytellerComponent と同パターン）

**ステップ12: `save_system.py` へ永続化フィールドを追加**
- `serializable_fields` / スキーマ辞書へ `archaeology_*` を追記し、ロード時に復元

**ステップ13: YAML 読み込みを検証**
- `DataManager` 経由で4 YAML をロードし、キー存在をアサートする軽量スクリプトを実行

**ステップ14: データ整合性テストを書く**
- 全 `truth_link` が `truth_codex` に存在し、全 `candidate_endings` が `story_endings` に存在することを検証

---

## フェーズC: システムコア（ステップ15-24）

**ステップ15: `archaeology_system.py` の骨格を作成**
- `ArchaeologyRegistry`（4 YAML をロード・キャッシュ）と `ArchaeologyManager(BaseSystem)` を定義

**ステップ16: 発掘ドロップ解決を実装**
- `resolve_excavation(site_id, depth)` で `fragment_pool` から重み付き抽選し断片 id を返す

**ステップ17: 収集ロジックを実装**
- `collect_fragment(player, fragment_id, engine)`: 重複排除し `collected_fragments` へ追加、ログ通知

**ステップ18: デコーダー鍵の獲得・管理**
- `acquire_key(player, key_id)` / `has_key(player, cipher_type)` を実装

**ステップ19: 解読ロジックを実装**
- `decode_fragment(player, fragment_id, engine)`: 対応 `cipher_type` の鍵所有時のみ `glyph_script` を解読済みへ
- 未所持なら `decoder_hint` をログ表示（謎解きの余地を残す）

**ステップ20: 部分真理の蓄積**
- 解読済み断片ごとに `truth_codex` の進捗を更新（候補ノードの達成度カウント）

**ステップ21: 真理到達の解決**
- `check_truth_progress(player, engine)`: あるノードの要求断片が全解読なら `reached_truths` へ追加し通知

**ステップ22: エンディング候補の提示**
- `suggest_endings(player)`: 到達済み真理ノードから `candidate_endings` を収集し一覧化

**ステップ23: 解釈による分岐記録**
- `interpret_truth(player, truth_id, ending_id, note)`: プレイヤーの解釈（寄り先エンディング）を `leaned_endings` に記録
- `story_endings` の `unlock_conditions` を満たすよう `story_flags` をセット（他システム互換）

**ステップ24: システム単体テスト**
- 発掘→収集→解読→真理→解釈の一連を疑似エンティティで駆動し、状態遷移を検証

---

## フェーズD: 統合（ステップ25-30）

**ステップ25: `game.py` へ登録**
- `self.archaeology_manager = self.systems_mgr.register("archaeology_manager", ArchaeologyManager(reg))`

**ステップ26: 発掘アクション入力フック**
- `input_handler.py` に `[x]` を「その深度で発掘」に割り当て、`excavate(player, engine)` を呼ぶ

**ステップ27: 遺跡マーカの描画**
- `map_engine.py` / `render_system.py` に発掘可能サイトの視覚マーカ（⛏/💎）を追加

**ステップ28: 考古学ジャーナルパネル**
- `journal_ui.py` に「考古学」タブを追加: 断片・解読済・到達真理・解釈ノートを表示

**ステップ29: ログ・効果音フィードバック**
- 解読成功・真理到達時に `engine.log` と `SoundManager.play_se` で演出

**ステップ30: メタ進行・実績との連携**
- `MetaProgressionManager.add_memory_fragment` 経由で `collected_fragments` 数をメタゴールに反映

---

## フェーズE: コミュニティ・二次創作（ステップ31-33）

**ステップ31: 9件の提案をまとめた設計ドキュメントを作成**
（詳細は後段「コミュニティ議論・二次創作喚起 9提案」を参照）

**ステップ32: 解釈台帳（interpretation ledger）の保存・出力**
- `interpretation_notes` を YAML/Markdown でエクスポートする `export_ledger(player)` を実装

**ステップ33: 共有用サマリー出力**
- 到達真理・寄り先エンディング・解釈文を含む投稿向けテキストを生成する `export_share_summary(player)`

---

## フェーズF: 検証と仕上げ（ステップ34-36）

**ステップ34: 36ステップ検証テストを作成**
- `tests/test_archaeology_metagame.py` で各ステップの成果をアサート（YAML/コンポーネント/ループ/UI登録）

**ステップ35: pytest 実行と修正**
- `python -m pytest tests/test_archaeology_metagame.py -q` を実行し、失敗を潰す
- 既存テスト（`test_dungeon_world_storyteller_72_steps.py`）も引き続き通ることを確認

**ステップ36: 実装サマリーを作成**
- `ARCHAEOLOGY_IMPLEMENTATION_SUMMARY.md` に使い方・拡張方法・トラブルシューティングを記載

---

## コミュニティ議論・二次創作喚起 9提案（単なるクリアから「謎解き・考察」へ）

1. **公開コーデックス＆解読wiki**: 言語族（cipher_type）別の解読進捗をプレイヤー同士で照合できる共有スキーマを配布。未解読グリフは意図的に「空白」とし、議論の種にする。
2. **「真実の複数解釈」エンディング投票**: 到達した真理ノードごとに「あなたはどう解釈したか？」を投票・アンケート。多数派/少数派解釈で派閥のアイデンティティを形成。
3. **不完全断片・補足二次創作コンテスト**: 断片のテキストを不完全なまま公開し、「空白を埋める」小説・イラスト・設定補足を募る。正解のない謎こそ創作の肥沃な土壌。
4. **考古学学派（ギルド/派閥）の対立**: 解釈の違いを派閥の教義にし、学派間で「真実」を論争。ゲーム内派閥戦争と連動させ議論を報酬化。
5. **週替わり「未解読断片」公式配信**: 運営が毎週新断片を少量配信し、コミュニティ総力での解読イベントを開催。FOMO ではなく「共犯関係」で結ぶ。
6. **解釈台帳（interpretation ledger）の共有形式**: プレイヤーの解釈を JSON/Markdown で出力可能にし、SNS やファンサイトへそのまま貼れる標準フォーマットを提供。
7. **ステガノグラフィ広報・隠しヒント**: 公式画像の alt テキストや SNS 投稿に解読ヒントを忍ばせ、プレイヤー同士で「気づき」を共有する宝探しを演出。
8. **二次創作引用ライセンスの明記**: 断片テキストと真理ノードを CCライクな引用ライセンスで公開し、同人・動画・考察文における「そのまま引用」を許容・奨励。
9. **「到達した真実」比較ダッシュボード**: どのエンディングに寄ったかの統計を可視化し、「自分の結論」と「世界の結論」のズレを楽しむ。考察が次週の運営判断に反映される透明性も。

---

## 成功基準（チェックリスト）
- [ ] 既存 `memory_fragments.yaml` / `story_endings.yaml` を壊さず拡張
- [ ] 4 YAML が全てロード可能で整合性エラーなし
- [ ] 発掘→収集→解読→真理→解釈のループが自動テストで完遂
- [ ] `game.py` にシステム登録され、[x] で発掘できる
- [ ] 考古学ジャーナルで状態を確認可能
- [ ] 解釈台帳・共有サマリーが出力できる
- [ ] `python -m pytest` が全て通る

## 注意事項
- 各ステップは順序通り、かつ後方互換を保ちながら実施
- 飛ばすと依存破綻するため、失敗時は前ステップへ戻る
- 定期的な pytest と git チェックポイントを推奨
