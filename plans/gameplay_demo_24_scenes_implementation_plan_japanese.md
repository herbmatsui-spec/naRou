# ゲームプレイ・デモ（24シーン）再構築 実装計画書

- 作成日: 2026-08-18
- 対象: `naRou: Masterpiece Edition`
- 目的: 旧「Elona」テーマの24シーン＆ギャラリーを削除し、現在の実装（`naRou: Masterpiece Edition`）の実システム・機能・特長に合わせて作り直す。

## 1. 現状認識（なぜ作り直すか）

- `demos/scene_01_*.html` 〜 `demos/scene_24_*.html`（計24ファイル）と `demos/gallery_24_scenes.html` は、旧来の「Elona ライクな一般的なRPG」を想定したハードコードされたシーンであり、現在の `naRou` 実装のシステム名と一致しない。
- 生成元 `generate_24_scenes.py` も同様の旧コンテンツを保持し、出力先が `e:/notedesk/elona/demos/`（Windows絶対パス）で本環境では機能しない。
- 実装済みシステムは `data/*.yaml` と各 `*_system.py` に定義されており、実名（日本語）が存在する。デモはこれを正しく反映すべき。

## 2. ゴール

1. 旧24シーンファイルおよび旧ギャラリーを削除する。
2. 実システムに基づく新しい24シーンを設計・定義する（表参照）。
3. `generate_24_scenes.py` を書き直し、同じデータから「24個の個別HTML」＋「ギャラリーHTML」を相対パス `demos/` に生成する。
4. スタイルは既存の自己完結型テンプレート（外部JSに非依存・`file://` で開ける）を維持する。

## 3. 新24シーンのマッピング（実システム → シーン）

| # | ファイル | タイトル | 反映する実機能（抜粋） |
|---|---|---|---|
| 1 | scene_01_base_home.html | 拠点・我が家 | 洞窟拠点、シエル、SHA256検証セーブ |
| 2 | scene_02_adventurers_guild.html | 冒険者ギルド | 冒険者ギルド(vernis)、ランク novice→leader、日替わりクエスト |
| 3 | scene_03_job_system.html | ジョブシステム | 見習い→戦士/魔法使い→剣聖/大賢者、専用スキル(シールドバッシュ/居合術/メテオ) |
| 4 | scene_04_skill_tree.html | スキルツリー | 剣術/魔法/体術の3ツリー・9ノード・スキルポイント |
| 5 | scene_05_skill_fusion.html | スキル合成 | 火炎爆砕合成/聖光撃合成、魔導剣・聖騎士・影殺セット |
| 6 | scene_06_skill_evolution_awakening.html | スキル進化・覚醒 | 剣術の進化の道、竜殺しの覚醒、神聖魔導の覚醒 |
| 7 | scene_07_skill_meta.html | 専門化・継承・共鳴・転移 | 火炎魔導専門化、血統スキル継承、炎の騎士セット、急所看破の転移 |
| 8 | scene_08_pet_contract.html | ペット契約 | 標準契約/魂の絆契約、絆しきい値200/500/800 |
| 9 | scene_09_pet_evolution.html | ペット進化 | 子犬→猟犬/警備犬/魔導猟犬、子猫→黒豹 |
| 10 | scene_10_pet_fusion.html | ペット融合 | ドラゴンハウンド、ユニコーンペガサス |
| 11 | scene_11_procedural_dungeon.html | 自動生成ダンジョン | 8舞台(街/森/洞窟/遺跡/火山/雪原/沼/深淵)、3次元(material/ethereal/void)・垂直世界 |
| 12 | scene_12_combat_system.html | 戦闘システム | 命中率/クリティカル、6元素、状態異常(毒/麻痺/混乱/盲目/出血) |
| 13 | scene_13_monsters_ai.html | モンスター＆AI | ぷち/ゴブリン/オーク/ミノタウロス/リッチ/レッドドラゴン、6種AI |
| 14 | scene_14_gods_faith.html | 神々と信仰 | ジュア/ルルウィ/マニ/イツパロトル/クミロミ、エーテル病 |
| 15 | scene_15_faction_war.html | 派閥戦争 | ガルド王国/ルミエスト教会/シャドウハンド、勢力値 |
| 16 | scene_16_guilds_detail.html | 魔術士・盗賊ギルド | 魔術士ギルド(lumiest)/盗賊ギルド(derphy)、ギルドスキル |
| 17 | scene_17_reincarnation.html | 輪廻転生 | 輪廻転生(最低Lv50)、カルマ、記憶の欠片、能力ボーナス |
| 18 | scene_18_ng_plus.html | ニューゲーム+ | NG+スケーリング(敵強化/ドロップ増)、カルマ変動 |
| 19 | scene_19_meta_progression.html | メタ進行 | メタ目標(深淵の踏破者等)、運命の特異点(サイクル修正) |
| 20 | scene_20_storyteller.html | ストーリーテラー | 自動生成ストーリー「ゴブリンの侵略」、選択肢・エンディング |
| 21 | scene_21_procedural_quests.html | 自動生成クエスト | 8アーキ型/6難易度/5報酬表/連鎖クエスト |
| 22 | scene_22_save_migration.html | セーブ＆マイグレーション | SaveSystem v2.0.0、SHA256+gzip、世代バックアップ、MigrationManager |
| 23 | scene_23_balance_simulator.html | バランス検証 | tests/balance_simulator.py、100試行、勝率・レポート出力 |
| 24 | scene_24_ecs_architecture.html | ECSアーキテクチャ・フィナーレ | SystemManager/BaseSystem/SystemCoordinator、登録30システム、デュアルUI |

## 4. 実装アプローチ

- 単一の `generate_24_scenes.py` に `SCENES`（filename, title, desc, icon, grid(5×10), log）を定義。
- 同一データから以下を生成：
  - `demos/scene_XX_*.html` × 24（自己完結HTML、旧テンプレート互換スタイル）
  - `demos/gallery_24_scenes.html`（SCENESから `scenes` JS配列を埋め込み、オートツアー機能維持）
- 出力パスを相対 `demos/` に修正（旧 `e:/notedesk/elona/demos/` を除去）。
- 各シーンの `log` には実際のシステム名・用語（日本語）を使用。

## 5. 削除対象

- `demos/scene_01_adventurer_start.html` 〜 `demos/scene_24_grand_ending.html`（24ファイル）
- `demos/gallery_24_scenes.html`

## 6. 検証

- スクリプト実行後、`demos/` に24ファイル＋ギャラリーが生成されることを確認。
- ギャラリーのオートツアー（シーン切替・24ボタン）が動作することを目視確認（HTML構造チェック）。
- 各 scene ファイルが `file://` で開ける自己完結構造であることを確認。
- README の「ゲームプレイ・デモ」セクションのリンクが新ファイル名と一致するよう更新。
