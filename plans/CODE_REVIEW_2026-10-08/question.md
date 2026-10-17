# コードレビュー 質問分解 (baseline)

## 質問
naRou コードベース(main @ 71018e5、2026-10-08 実測)の重要なコード品質問題(バグ、デッドコード、設計問題、テスト負債、衛生)は何か。また、改善提案の上位は何か。

## サブ質問
- SQ1: 静的解析 — ruff/mypy は main チェックアウトで何を報告するか
- SQ2: テスト実態 — 主張された8スイート全PASSは実際に通るか。スイートの真の状態(完走率、失敗、xfail)は
- SQ3: 継承主張検証 — build/lib/naRou はソースツリーと同期しているか(主張された「唯一の残実装項目」)
- SQ4: engine/core 深掘り — engine/engine.py、core/、入力レイヤーのバグ・設計問題
- SQ5: スキル系レビュー — 3層「スキル」ハザード(MEMORY.md:42)、skill_* ルートモジュールの品質
- SQ6: save/web/entry レビュー — save_system.py、web_server.py、run.py、main_text.py の永続化・サーバー問題
- SQ7: テスト品質レビュー — 72ステップスイートの空虚性(意味あるアサートをしているか)、テスト負債構造
- SQ8: データ整合性 — data/ スキーマ、Pydantic モデル、YAML
- SQ9: 衛生 — 未追跡アーティファクト(.tmp_bb4、en.yaml.backup、tests/relationships)、デッドコード、リポジトリ形状

## 理想的な答えの形状
file:line 証拠 + 重要度 + 確度付きの優先づけられた発見リスト、検証済み継承主張、ランキングされた改善案9つ、上位6つの詳細実装計画(回帰テスト名入り、ファイル単位のアトミックサブステップ)。

## キーワードクラスタ
- 静的: ruff / mypy / unused / F401 / F841 / type-ignore
- テスト: pytest / xfail / fail / skip / Engine() 重量化 / suite runnable
- デザイン: GAME_OVER / death loop / no fail state / difficulty easy / damage 0.5
- スキル: Entity.skills / CharacterState.skills / SkillEaterRegistry / 三層
- 永続化: karma_law_chaos / legacy_skills / save / load
- web: bind 8080 / web_server / Address already in use
- データ: Pydantic / enum / schema / yaml
- 衛生: .tmp_bb4 / en.yaml.backup / tests/relationships / dead code
