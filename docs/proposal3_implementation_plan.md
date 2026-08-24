# 提案3 実装計画（72ステップ）【メタシナリオ介入】プロシージャル・イベントシステム

## 設計方針（実装者への注意）

- 各ステップは**独立して動作する最小単位**とし、完了条件（テスト）を満たしてから次へ進む。
- 全ての新規ロジックは `naRou/systems/skill_eater_meta_intervention_system.py`（新規）へ集約し、既存ファイルは「追加・拡張」のみとする。
- 数値は `data/meta_intervention.yaml` へ切り出し、ハードコードしない。
- 登録は `naRou/packages/world_a/package.py` の既存パターン（Step 120付近）に倣う。
- テストは `tests/test_skill_eater_meta_intervention_*.py` に配置。

---

## Phase A：データモデル・基盤（Step 1–12）

### Step 1《SkillTier 拡張》
- 対象：`naRou/systems/skill_eater_system.py:16` `class SkillTier`
- 作業：`META_UNIQUE = "MetaUnique"` を追加。
- 完了：既存 `get_skills_by_tier` が `META_UNIQUE` を返せること（既存テストが壊れない）。

### Step 2《ReincarnationComponent 拡張》
- 対象：`naRou/ecs/components/components.py:102` `ReincarnationComponent`
- 作業：`template_exposure: int = 0` を追加（露見度）。
- 完了：`ReincarnationComponent()` が `template_exposure=0` で初期化される。

### Step 3《ReincarnationMetaState 拡張》
- 対象：`naRou/systems/skill_eater_meta_quest_system.py:276`
- 作業：`devoured_template_counts: dict[str,int]=field(default_factory=dict)` を追加。
- 完了：既存 `process_reincarnation` が壊れない（デフォルト値のため）。

### Step 4《テンプレ YAML 雛形作成》
- 対象：新規 `data/templates/expel_incompetent.yaml`
- 作業：設計案§17 のスキーマ（id/archetype/contexts/faction_weight/route_steps/exploit_windows/reward）を1件だけ書く。
- 完了：YAML がパースできる（python -c で yaml.safe_load）。

### Step 5《テンプレデータクラス定義》
- 対象：新規 `naRou/systems/skill_eater_template_model.py`
- 作業：`TemplateData`, `RouteStep`, `ExploitWindow`, `TemplateReward` の `@dataclass` と `from_dict` を実装。
- 完了：Step4 の YAML を `TemplateData.from_dict` で読める。

### Step 6《テンプレローダー》
- 対象：同上ファイル
- 作業：`load_templates(dir_path) -> dict[str, TemplateData]` を実装（glob `*.yaml`）。
- 完了：`load_templates("data/templates")` が1件返る。

### Step 7《ローダーユニットテスト》
- 対象：新規 `tests/test_skill_eater_meta_intervention_loader.py`
- 作業：一時 dir に YAML を書き、`load_templates` が `route_steps` を正しく復元することを assert。
- 完了：`pytest` が通る。

### Step 8《KarmaData に露見度軸》
- 対象：`naRou/systems/karma_system.py` `KarmaData`
- 作業：`exposure: int = 0` フィールド追加（actions に `template_deep_read` など定義）。
- 完了：既存 `update_karma` が壊れない。

### Step 9《露見度更新アクション》
- 対象：同上 `update_karma`
- 作業：`action=="template_deep_read"` で `exposure += 1` を処理。
- 完了：単体で `update_karma(player,"template_deep_read",1)` で exposure が増える。

### Step 10《entity への露見度アクセサ》
- 対象：`naRou/ecs/entity.py`（karma_law_chaos 付近）
- 作業：`template_exposure` getter/setter を `ReincarnationComponent` 経由で追加。
- 完了：entity から `entity.template_exposure` で取得・設定できる。

### Step 11《セーブ互換》
- 対象：`naRou/systems/save_system.py`
- 作業：`template_exposure`, `devoured_template_counts` を save/load に含める（存在しない場合は 0/{} で復元）。
- 完了：旧セーブを load しても KeyError が出ない。

### Step 12《基盤統合テスト》
- 対象：`tests/.../test_skill_eater_meta_intervention_loader.py` に追記
- 作業：Step2,3,8,10 の値が往復（save→load→entity）で一致することを assert。
- 完了：`pytest` 通過。

---

## Phase B：原典閲覧拡張（Step 13–22）

### Step 13《MetaAwarenessSystem スキャンI/F》
- 対象：`naRou/systems/meta_awareness_system.py`
- 作業：`trigger_template_scan(target) -> list[dict]` をスタブ（空リスト）で追加。
- 完了：呼び出しが `[]` を返す。

### Step 14《閲覧深度メソッド》
- 対象：同上
- 作業：`get_reading_depth() -> int` を `awareness_level` に基づき 1/2/3 を返すよう実装。
- 完了：Lv1→1, Lv4→3 など分岐する。

### Step 15《フラグ検出ロジック》
- 対象：同上 `trigger_template_scan`
- 作業：引数 `target.scenario_flags`（Step23で付与）を読み、`{"archetype","weight"}` を返す。
- 完了：フラグ 0.7 の NPC が検出される。

### Step 16《深読みのカルマ代償》
- 対象：同上
- 作業：深度3 の読みで `karma_law_chaos -= 1`（秩序逸脱）するよう `karma_manager` を呼ぶ。
- 完了：深読み後に `karma_law_chaos` が減る。

### Step 17《深読みの露見度代償》
- 対象：同上
- 作業：深度3 で `template_exposure += 1`（Step10）を呼ぶ。
- 完了：深読み後に露見度が増える。

### Step 18《スキャンスタブテスト》
- 対象：新規 `tests/test_skill_eater_meta_intervention_awareness.py`
- 作業：ダミー target（scenario_flags 付き）で検出数・深度を assert。
- 完了：`pytest` 通過。

### Step 19《exploit窓提示I/F》
- 対象：同上
- 作業：`get_exploit_windows(template: TemplateData, depth) -> list[ExploitWindow]` を追加（深度<窓.tier は除外）。
- 完了：深度2 で T1/T2 窓のみ返る。

### Step 20《演出発火》
- 対象：同上
- 作業：スキャン成功時に `presentation.add_event(emote="emote_exclamations.png", message=...)` を呼ぶ。
- 完了：スキャン後に `presentation.get_and_clear_events()` に1件ある。

### Step 21《演出テスト》
- 対象：Step18 のテストに追記
- 作業：スキャンで演出イベントが発火することを assert。
- 完了：`pytest` 通過。

### Step 22《統合：awareness×template》
- 対象：同上
- 作業：実際の `TemplateData`（Step5）を渡し、検出→窓提示が連動することを assert。
- 完了：`pytest` 通過。

---

## Phase C：プロシージャル生成器（Step 23–34）

### Step 23《生成器スケルトン》
- 対象：新規 `naRou/systems/skill_eater_meta_intervention_system.py`
- 作業：`class TemplateEventGenerator` を定義、`__init__(templates, rng)` のみ。
- 完了：インスタンス化できる。

### Step 24《シード抽選》
- 対象：同上
- 作業：`_roll_seed(context) -> (archetype, faction)` を重み付き抽選で実装。
- 完了：固定 seed で決定論的に同一結果。

### Step 25《Route 展開》
- 対象：同上
- 作業：`build_route(template) -> list[RouteStep]` をそのまま展開。
- 完了：route_steps 数 == 生成 route 数。

### Step 26《Exploit 窓抽出》
- 対象：同上
- 作業：`extract_windows(template, context) -> list[ExploitWindow]` を実装。
- 完了：窓リストが正しく抽出される。

### Step 27《難易度式》
- 対象：同上
- 作業：`compute_difficulty(windows, loop_count) -> float` を設計案§13 式で実装。
- 完了：loop 増で難易度低下（diff 減）する。

### Step 28《探索フック》
- 対象：`naRou/systems/skill_eater_exploration_system.py`
- 作業：探索移動時に `generator.maybe_spawn(context)` を呼ぶフック（確率 0.3–0.8）を追加。
- 完了：既存探索が壊れない。

### Step 29《システム登録》
- 対象：`naRou/packages/world_a/package.py:120` 付近
- 作業：`kernel.register_system("skill_eater_meta_intervention", TemplateEventGenerator(...))` を追加。
- 完了：`package` のセットアップが例外なく終わる。

### Step 30《アクティブイベント保持》
- 対象：新規システム / または `engine` 状態
- 作業：`active_template_events: list[TemplateEvent]` を保持するフィールドを追加。
- 完了：生成イベントがリストに追加される。

### Step 31《生成器決定論テスト》
- 対象：新規 `tests/test_skill_eater_meta_intervention_generator.py`
- 作業：seed 固定で同一 context から同一 id のイベントが出ることを assert。
- 完了：`pytest` 通過。

### Step 32《探索統合テスト》
- 対象：Step31 に追記
- 作業：探索システム経由で `active_template_events` に1件入ることを assert。
- 完了：`pytest` 通過。

### Step 33《engine プロパティ》
- 対象：`naRou/engine/engine.py`（他システム getter 旁）
- 作業：`template_intervention_system` プロパティを追加。
- 完了：`engine.template_intervention_system` で取得できる。

### Step 34《掃討テスト》
- 対象：Step31 に追記
- 作業：Step23–33 全通し、生成→保持→取得が通る。
- 完了：`pytest` 通過。

---

## Phase D：介入実行エンジン（Step 35–50）

### Step 35《介入エンジンスケルトン》
- 対象：新規システム内に `class InterventionEngine`
- 作業：`__init__(registry, presentation, rule_engine, meta_state)` のみ。
- 完了：インスタンス化できる。

### Step 36《介入アクション定義》
- 対象：`skill_eater_template_model.py`
- 作業：`InterventionAction` dataclass（tier, window_id, params）を追加。
- 完了：from_dict で復元できる。

### Step 37《T1 実行（表面介入）》
- 対象：介入エンジン
- 作業：`execute_t1(action) -> result`：安値買い叩き等を模擬（gold 消費→スキル取得予約）。
- 完了：T1 成功で gold が減る。

### Step 38《T2 実行（構造介入）》
- 対象：同上
- 作業：`execute_t2`：ヒロイン主導権移譲等、フラグ反転ロジックを模擬。
- 完了：対象 NPC の scenario_flag が反転する。

### Step 39《T3 実行（存在介入）》
- 対象：同上
- 作業：`execute_t3`：成功時に `rule_engine.override_rule("template_weight_<id>", 0.0, cost_type="KARMA")` を呼ぶ。
- 完了：T3 成功で `GlobalRuleEngine` の該当値が 0 になる。

### Step 40《成功判定ロール》
- 対象：同上
- 作業：`roll_success(window, difficulty) -> bool` を実装（乱数＋閾値）。
- 完了：成功率が window.base_success に近似。

### Step 41《完全性計算》
- 対象：同上
- 作業：`compute_completeness(template, executed_steps) -> float`（0–1）。
- 完了：全ステップ潰しで 1.0。

### Step 42《報酬計算式》
- 対象：同上
- 作業：`calc_karma(reward, tier, completeness)` を設計案§15 倍率で実装。
- 完了：完全性100% で ×4.0。

### Step 43《強奪スキル付与》
- 対象：同上
- 作業：成功時 `stolen_skill` を `skill_eater_bounty_system` の付与フローで player へ追加。
- 完了：player のスキルに追加される。

### Step 44《限定ユニーク付与》
- 対象：同上
- 作業：完全性≥0.7 で `META_UNIQUE` スキル（`《ざまぁの極み》`等）を registry から付与。
- 完了：`get_skills_by_tier(META_UNIQUE)` に該当スキルが入る。

### Step 45《露見度反映》
- 対象：同上
- 作業：介入実行で `player.template_exposure += f(tier)` を反映。
- 完了：T3 ほど露見度が大きく増える。

### Step 46《失敗処理》
- 対象：同上
- 作業：失敗時はテンプレを定形完遂し、player を「共犯」扱い（karma_good_evil 減）に。
- 完了：失敗で good_evil が減る。

### Step 47《テンプレ学習・耐性》
- 対象：新規システム
- 作業：`devoured_template_counts` に基づき再抽選時の base_success を 0.7/周 減衰。
- 完了：同一アーキタイプ乱獲で成功率低下。

### Step 48《善悪変動》
- 対象：介入エンジン
- 作業：T2 以上で `karma_good_evil` を変動させる。
- 完了：T2 介入で good_evil が動く。

### Step 49《演出発火（階層別）》
- 対象：介入エンジン
- 作業：各 tier で専用 `add_event`（emote/audio/message）を発火。
- 完了：tier ごとに異なる演出イベントが1件出る。

### Step 50《T1 成功パステスト》
- 対象：新規 `tests/test_skill_eater_meta_intervention_engine.py`
- 作業：T1 成功一連を通し、gold減・報酬付与・演出を assert。
- 完了：`pytest` 通過。

---

## Phase E：報酬・周回・法則書き換え連動（Step 51–60）

### Step 51《因果ポイント加算》
- 対象：介入エンジン
- 作業：成功で `meta_state.total_karma_points += karma`。
- 完了：介入後に total_karma_points が増える。

### Step 52《乱獲カウント》
- 対象：同上
- 作業：`meta_state.devoured_template_counts[archetype] += 1`。
- 完了：カウントが増える。

### Step 53《周回減衰係数》
- 対象：生成器
- 作業：難易度式に `loop_mod = 1/(1+0.1*(loop-1))` を組み込む。
- 完了：周回で難易度が緩和される。

### Step 54《T3 法則書き換え接続》
- 対象：介入エンジン
- 作業：Step39 を `GlobalRuleEngine.override_rule` 本実装に差し替え（KARMA 消費）。
- 完了：T3 成功で世界パラメータが変わる。

### Step 55《world_modifier 拡張》
- 対象：`skill_eater_meta_quest_system.py` `apply_world_modifier`
- 作業：テンプル乱獲に基づく供給単価変動を追加。
- 完了：乱獲アーキタイプの単価が低下。

### Step 56《輪廻転生での引継ぎ》
- 対象：同上 `process_reincarnation`
- 作業：`devoured_template_counts` を新プレイヤーへ半減引継ぎ。
- 完了：転生後もカウントが残る（減衰済）。

### Step 57《法則書き換え統合テスト》
- 対象：Step50 のテストに追記
- 作業：T3→override_rule→world_modifier が連動することを assert。
- 完了：`pytest` 通過。

### Step 58《転生引継ぎテスト》
- 対象：同上
- 作業：`process_reincarnation` 後に counts が引き継がれることを assert。
- 完了：`pytest` 通過。

### Step 59《報酬ティア表実装》
- 対象：介入エンジン
- 作業：設計案§15 のティア表を `data/meta_intervention.yaml` から適用。
- 完了：完全性ごとに倍率が正しい。

### Step 60《報酬ティアテスト》
- 対象：Step59
- 作業：0–100% の各ティアで karma 出力を assert。
- 完了：`pytest` 通過。

---

## Phase F：UI / UX（Step 61–68）

### Step 61《フラグ揺らぎオーバーレイ》
- 対象：`skill_eater_presentation_system.py` `build_diegetic_ui_data`
- 作業：template 持ち NPC 向けに `flag_badges: list[dict]` を追加出力。
- 完了：義眼有無でバッジ有無が切り替わる。

### Step 62《原典閲覧モードUI》
- 対象：新規システム / UI
- 作業：深度3 時の「IFルートタイムライン」表示データを構築。
- 完了：タイムライン dict が生成される。

### Step 63《完全性ゲージ》
- 対象：介入エンジン
- 作業：介入実行結果に `completeness` を含め、UI がゲージ描画できる形に。
- 完了：結果 dict に completeness が含まれる。

### Step 64《入力マッピング》
- 対象：`naRou/input_actions.py`
- 作業：`scan_template`（原典閲覧）と `intervene(window_id)` のアクションを追加。
- 完了：入力から両アクションが呼べる。

### Step 65《介入メニュー描画》
- 対象：UI（既存メニュー実装に倣う）
- 作業：検出窓を選択できるメニューデータを構築。
- 完了：窓リストがメニューに出る。

### Step 66《イベントログ文》
- 対象：新規システム
- 作業：アーキタイプ別のログメッセージテーブルを `data/meta_intervention.yaml` へ。
- 完了：各 archetype で文が取得できる。

### Step 67《Web 状態公開（任意）》
- 対象：`naRou/web_server.py`（既存 karma 出力旁）
- 作業：`active_template_events` を JSON に含める。
- 完了：Web で状態が見える。

### Step 68《UI データテスト》
- 対象：新規 `tests/test_skill_eater_meta_intervention_ui.py`
- 作業：Step61–66 のビルダーが None を返さず正形であることを assert。
- 完了：`pytest` 通過。

---

## Phase G：テスト・バランス・文書（Step 69–72）

### Step 69《統合ループテスト》
- 対象：新規 `tests/test_skill_eater_meta_intervention_integration.py`
- 作業：scan → intervene(T2) → reward → reincarnate の全ループを1テストで通す。
- 完了：`pytest` 通過。

### Step 70《バランス設定》
- 対象：`data/meta_intervention.yaml`
- 作業：発生頻度・難易度係数・報酬単価・周回減衰を全定数として記述。
- 完了：設定値がロードされる。

### Step 71《プレイスルーデモ》
- 対象：新規 `demos/meta_intervention_demo.py`
- 作業：設計案§16 の進行例をそのままスクリプト化し、出力を print。
- 完了：`python demos/meta_intervention_demo.py` が完走する。

### Step 72《文書・最終検証》
- 対象：`CHANGELOG.md` / 設計ドキュメント
- 作業：実装内容を CHANGELOG に追記。最後に `pytest tests/test_skill_eater_meta_intervention*` と `ruff`/`mypy`（pyproject 設定）を実行し全 green。
- 完了：全テスト・リント・型検査が通る。

---

## 実装順の依存関係（簡易）

```
A(1-12) → B(13-22) → C(23-34) → D(35-50) → E(51-60) → F(61-68) → G(69-72)
```
各 Phase 内も基本的に番号順だが、スタブ（13/23/35）を先に置くことで並行実装も可能。貧弱なLLMは「その Step の完了条件だけ」を満たせばよく、先行 Step の本実装が未完成でもスタブがあれば次へ進める。
