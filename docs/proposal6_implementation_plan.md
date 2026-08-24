# 提案6 実装計画：タワーディフェンス型スラム防衛戦（バベル強制監査部隊）

## 方針

既存の `naRou/skill_eater/skill_eater_base_defense.py`（`BaseDefenseManager`：Heat/Warning/Breach/Aftermath、Midas施設・敵・バランスシム済）を**壊さず**拡張する。
新設する `AuditDefenseManager(BaseDefenseManager)` に、設計書の「脅威度・第1〜第5監査・捕食錬成・Husk壁・EMP・部隊長強奪」を実装する。
各ステップは**1ファイル・1関数・1テスト**を目安に最小化し、低性能LLMでも順に実装・検証できるようにする。

用語マップ：
- 脅威度 = `threat_level`（既存 `heat_level` は Midas用として残存）
- 監査部隊 = `AuditUnit` / `AuditCaptain`（Midas敵とは別系統）
- 錬成 = `distill()`（捕食スキル → タレット設計図）
- 強奪 = `seize_captain()`（部隊長専用スキル奪取）

---

## Phase 0 基盤・データモデル（1〜9）

**1. 列挙型の追加**
- ファイル：`naRou/skill_eater/skill_eater_audit_defense.py`（新規作成）
- 作業：`AuditTier(str,Enum)` {T1..T5}、 `AuditUnitType` {CLEANER, PEACEKEEPER, PURIFIER, CARDINAL, INQUISITOR}、 `TrapType` {EMP, POISON_CLOUD, DECOY} を定義。
- 完了条件：import エラーなし、`AuditTier.T4.value == "T4"`。

**2. データクラス定義（その1）**
- 作業：`AuditUnit`、`AuditCaptain`（`special_skill_id`, `hp`, `atk`, `is_captain=True`）、`DistillBlueprint`（`skill_id`, `element`, `role`, `turret_stats`）、`HuskBarricade`、`EmpMine`、`SeizedSkill` を `@dataclass` で定義（フィールドのみ、ロジックなし）。
- 完了条件：各 dataclass をインスタンス化できる。

**3. 監査ティア設定定数**
- 作業：`AUDIT_TIER_CONFIG: dict[int, dict]` をファイル冒頭に定義。各ティアに `unit_count`, `captain_hp`, `steal_base_rate`, `core_timer`, `incoming_skill` を埋める（設計書15.6表をベース）。
- 完了条件：`AUDIT_TIER_CONFIG[5]["steal_base_rate"]` が設計値と一致。

**4. モジュール骨格＋サブクラス**
- 作業：`class AuditDefenseManager(BaseDefenseManager):` を宣言し、`__init__` で `super().__init__()` を呼び、`threat_level=0`, `audit_state=None` を追加。
- 完了条件：`AuditDefenseManager()` が既存施設を初期化できる（親の挙動を壊さない）。

**5. 脅威度計算関数**
- 作業：`compute_threat(registry) -> int` を追加。捕食スキル数×1、ランク重み（common1/rare3/epic6/legend12）、強奪済専用スキル×10、スラム勢力Lv×2、反逆行為フラグ×5 を加算し100でクランプ。
- 完了条件：既知の fixture registry で期待値と一致。

**6. 脅威度計算のユニットテスト**
- ファイル：`tests/test_audit_defense_threat.py`（新規）
- 作業：`compute_threat` にスキル3つ（rare×2, epic×1）の fixture を渡し、期待値を assert。
- 完了条件：`pytest tests/test_audit_defense_threat.py` 成功。

**7. 監査ユニット定義YAML**
- ファイル：`data/worlds/skill_eater/audit_units.yaml`（新規）
- 作業：各ティアの `units`（hp/atk/def/speed/weakness_element）と `captain`（hp/special_skill_id）を記述。`special_skill_id` 例：`execute_death_immunity`（第4）。
- 完了条件：YAML が parse できる。

**8. YAMLローダー**
- 作業：`load_audit_units(path) -> dict` を追加（既存パターンに倣い `yaml.safe_load`）。
- 完了条件：ロード結果に `T4.captain.special_skill_id == "execute_death_immunity"`。

**9. ローダーのユニットテスト**
- 作業：テストで `load_audit_units` を呼び、T1ユニット数＞0 を assert。
- 完了条件：テスト成功。

---

## Phase 1 脅威度・予兆・スケジュール（10〜18）

**10. トリガー型追加**
- 作業：親の `RaidTriggerType` に `AUDIT_THREAT = "AuditThreat"` を追加。
- 完了条件：親モジュールの import でエラーなし。

**11. 脅威度UI状態フィールド**
- 作業：`get_defense_ui_state()` をオーバーライドし、`threat_level` と `audit_tier` を追加して返す。
- 完了条件：呼び出し結果に `threat_level` キーが含まれる。

**12. 脅威度加算フック**
- 作業：`add_threat(amount)` を追加（親 `increase_heat` と同型だが `threat_level` を操作）。捕食成功・専用スキル強奪から呼ぶ予定のため、ここでは呼び出し口だけ。
- 完了条件：`add_threat(10)` で `threat_level` が +10 クランプされる。

**13. 予兆期間（time_system連動）**
- 作業：`start_audit_premonition(tier)` を追加。`time_system`（既存）の「プレイヤーが日付を進めたときのみ経過」セマンティクスに合わせ、`premonition_days` カウントダウンを持つ。`WARNING` フェーズ開始を予約。
- 完了条件：予兆開始で `current_phase == WARNING` 予約フラグが立つ。

**14. ティア決定関数**
- 作業：`threat_to_tier(threat) -> int`：閾値（例 20/40/60/80/95）で T1..T5 を返す。
- 完了条件：`threat_to_tier(95) == 5`、`threat_to_tier(0) == 1`（最低T1で発火想定）。

**15. ティア境界のユニットテスト**
- 作業：境界値（19/20/39/40/...）で期待ティアを assert。
- 完了条件：テスト成功。

**16. 来襲ブリーフィング生成**
- 作業：`generate_briefing(tier) -> dict`：YAMLから編成・兵科・部隊長専用スキルを抜き出し、`{composition, captain_skill, recommended_counter_element}` を返す。
- 完了条件：T3ブリーフィングに `captain_skill` が含まれる。

**17. ブリーフィングの決定論テスト**
- 作業：seed 固定で2回呼び同一 dict を assert（乱数非依存）。
- 完了条件：テスト成功。

**18. process_turn への統合**
- 作業：親 `process_turn()` の NORMAL分岐に、`check_audit_trigger()`（脅威度閾値）を追加し、発火時に `start_audit_premonition()` を呼ぶ。
- 完了条件：脅威度閾値超えで予兆が開始する。

---

## Phase 2 捕食スキル→タレット錬成（19〜27）

**19. 錬成設計図データクラス拡充**
- 作業：`DistillBlueprint` に `turret_stats`（damage/range/cooldown/element/status）を既定値付きで追加。
- 完了条件：要素付きでインスタンス化できる。

**20. スキル分類関数**
- 作業：`classify_skill(skill) -> (element, role)`：スキル名/タグから fire/ice/thunder/poison/physical と attack/defense/utility を判定。
- 完了条件：`classify_skill(Inferno Breath) == ("fire","attack")`。

**21. 分類のユニットテスト**
- 作業：サンプル5スキル（炎/氷/雷/毒/物理）で期待タプルを assert。
- 完了条件：テスト成功。

**22. 錬成コストモデル**
- 作業：`DISTILL_COST = {"junk": 200, "skill_lock": True}` と `distill_cost(skill) -> dict` を追加。
- 完了条件：`distill_cost` が junk 量を返す。

**23. 錬成実行**
- 作業：`distill_skill(skill_id) -> DistillBlueprint`：資源チェック→スキルを一時ロック→設計図を `blueprints` へ登録。
- 完了条件：錬成後 `blueprints` に追加され、スキルがロック状態になる。

**24. 錬成のユニットテスト**
- 作業：資源十分な fixture で `distill_skill` を呼び、設計図追加＋スキル `locked==True` を assert。
- 完了条件：テスト成功。

**25. 解体・復元**
- 作業：`undistill(blueprint_id)`：設計図削除＋スキルロック解除＋資源70%還元。
- 完了条件：解体でロックが戻る。

**26. 設計図レジストリ管理**
- 作業：`list_blueprints()` / `get_blueprint(id)` を追加。
- 完了条件：登録済み設計図一覧が取得できる。

**27. 設計図のユニットテスト**
- 作業：add→get→undistill の一連を assert。
- 完了条件：テスト成功。

---

## Phase 3 属性防衛タレット（28〜36）

**28. 施設へ要素付与**
- 作業：親 `DefenseFacility` に `element: str = "none"`, `blueprint_id: str | None = None` を追加（既存施設は無影響）。
- 完了条件：既存施設の from_dict/to_dict が壊れない（後方互換）。

**29. 属性タレット雛形**
- 作業：`AUDIT_TURRET_TEMPLATES`（fire/ice/thunder/poison）を定義し、`DEFAULT_AUDIT_FACILITIES` に追加。
- 完了条件：`get_facility_status()` に新タレットが含まれる。

**30. 錬成タレット建設**
- 作業：`build_distilled_turret(blueprint_id)`：設計図から `element/status` を読み、`DefenseFacility` を生成・建設。
- 完了条件：建設後タレットが `element` を持つ。

**31. 状態異常適用**
- 作業：`_facility_attack_enemies` を拡張し、属性に応じ `burn/freeze/poison` を敵に付与（既存ステータスシステム `skill_eater_toxicity_system` / 状態異常APIを再利用）。
- 完了条件：炎タレット命中で敵に `burn` が付く。

**32. 属性適用のユニットテスト**
- 作業：fireタレット1発で敵 `status` に burn を assert。
- 完了条件：テスト成功。

**33. スキルLv連動スケーリング**
- 作業：タレット `damage/range` に源スキルLvを乗算（`1.15 ** (skill_lv-1)`）。
- 完了条件：Lv3スキル由来タレットはLv1の約1.5倍ダメージ。

**34. スケーリングのユニットテスト**
- 作業：Lv1 vs Lv3 で damage 比を assert。
- 完了条件：テスト成功。

**35. クールダウン・射程の設計図反映**
- 作業：build 時に `blueprint.turret_stats` の cooldown/range を施設へコピー。
- 完了条件：`facility.range == blueprint.range`。

**36. 統合テスト（建設→1tick）**
- 作業：錬成→建設→`process_breach_phase()` 1回で敵HPが減ることを assert。
- 完了条件：テスト成功。

---

## Phase 4 Husk壁・EMP地雷（37〜45）

**37. Husk壁データクラス**
- 作業：`HuskBarricade(id, hp, max_hp, cell)` を定義。
- 完了条件：インスタンス化できる。

**38. Husk→壁変換**
- 作業：`place_husk_barricade(husk)`：`skill_eater_husk_system.create_husk` 由来の Husk から `HuskBarricade` を生成し `husk_barricades` へ追加。
- 完了条件：変換後リストに追加される。

**39. Husk壁生成のユニットテスト**
- 作業：ダミーHuskで `place_husk_barricade` を呼び、hp＞0 を assert。
- 完了条件：テスト成功。

**40. 壁の進行遮断・被弾**
- 作業：`_enemy_attack_facilities` に壁をターゲット候補として追加。壁HP0で「残骸」化（再取得可能フラグ）。
- 完了条件：壁がダメージを受け、0で `is_debris` になる。

**41. EMP地雷データクラス＋設置**
- 作業：`EmpMine(id, cell, trigger_radius, stun_turns)` と `plant_emp_mine(cell)`。
- 完了条件：設置で `emp_mines` に追加。

**42. EMPスタン効果**
- 作業：敵が半径内に入ったら `stun_turns` を付与（ドローン/装甲に特効：既存ステータス `stun` 再利用）。
- 完了条件：起動で敵に stun が付く。

**43. EMPのユニットテスト**
- 作業：mine設置→敵進入→stun付与を assert。
- 完了条件：テスト成功。

**44. 罠の永続化構造**
- 作業：`traps: dict` に husk_barricades / emp_mines を格納し、`to_dict/from_dict` で扱える形にする（実装はPhase9で完結）。
- 完了条件：メモリ上で traps が管理されている。

**45. 罠管理のユニットテスト**
- 作業：壁＋地雷を置き、`len(traps)` を assert。
- 完了条件：テスト成功。

---

## Phase 5 監査ユニット・部隊長AI（46〜54）

**46. ティア別ユニット生成**
- 作業：`_generate_audit_units(tier)`：YAMLから該当ティアの `units` を `AUDIT_TIER_CONFIG` の `unit_count` で生成。
- 完了条件：T2で `unit_count` 分の `AuditUnit` が得られる。

**47. ウェーブ生成のユニットテスト**
- 作業：T1/T3/T5 で生成数がティアで増えることを assert。
- 完了条件：テスト成功。

**48. 弱点属性の適用**
- 作業：敵に `weakness_element` を持たせ、タレット側で倍率（×1.5）を適用。
- 完了条件：弱点属性タレットでダメージが上がる。

**49. 部隊長データ**
- 作業：`_spawn_captain(tier)`：YAMLの `captain` から `AuditCaptain` を生成し、リストへ追加。
- 完了条件：captain が `is_captain==True` で存在。

**50. 部隊長バフ（士気）**
- 作業：captain生存中、残兵の atk/def に `+15%` を付与するフラグ計算。
- 完了条件：captain生存時の敵 atk が上昇。

**51. 部隊長撃破→撤退**
- 作業：captain `is_dead` 時に `squad_retreat=True` をセットし、残兵を即排除扱い。
- 完了条件：captain死亡で `squad_retreat` が True。

**52. 撤退のユニットテスト**
- 作業：captainを殺し、`process_breach_phase` で残兵0・勝利遷移を assert。
- 完了条件：テスト成功。

**53. 強奪前提デバフ**
- 作業：`can_seize(captain)`：HP≤30% かつ (stun|freeze|poison) いずれか1つ以上で True。
- 完了条件：条件を満たさないと False。

**54. 前提のユニットテスト**
- 作業：HP50%で False、HP20%+freeze で True を assert。
- 完了条件：テスト成功。

---

## Phase 6 部隊長専用スキル強奪（55〜60）

**55. 強奪判定**
- 作業：`seize_captain(captain) -> dict`：`can_seize` 確認後、`success_rate = 40 + skill_lv*4 - tier*5`（第5は −20 ペナルティ）で抽選。
- 完了条件：rate がクランプ（0〜95）される。

**56. 成功/失敗処理**
- 作業：成功→`grant_special_skill(captain.special_skill_id)`（registryへ）+ `squad_retreat=True`。失敗→`captain` 反撃ダメージ + `add_toxicity(15)`。
- 完了条件：成功でスキル付与、失敗で毒性＋反撃。

**57. 成功パスのユニットテスト**
- 作業：確定成功（rate=100モック）でスキル獲得＋撤退を assert。
- 完了条件：テスト成功。

**58. 失敗パスのユニットテスト**
- 作業：確定失敗で `toxicity` 増加を assert。
- 完了条件：テスト成功。

**59. 《執行権限：即死無効化》実装**
- 作業：`skill_eater_system` のプレイヤー死亡判定に、`execute_death_immunity` 所持時は即死を無効化する分岐を1つ追加。
- 完了条件：フラグありで即死ダメージが0になる。

**60. 即死無効のユニットテスト**
- 作業：スキル所持状態で致死ダメージを与え、生存を assert。
- 完了条件：テスト成功。

---

## Phase 7 タレット間シナジー（61〜63）

**61. 氷→雷拡散**
- 作業：`_facility_attack_enemies` で、freeze状態の敵へ雷タレット命中時に隣接2体へ雷ダメージを追加。
- 完了条件：freeze敵への雷で隣接にもダメージ。

**62. 毒→炎爆発**
- 作業：poison状態の敵へ炎ダメージで小範囲AoEを1回発生。
- 完了条件：poison敵への炎で周囲AoE。

**63. 壁裏DPSボーナス**
- 作業：Husk壁に隣接するタレットの `efficiency` に +0.25 を加算（最大1.0）。
- 完了条件：壁隣接タレットの実効DPSが上がる。

---

## Phase 8 UI・チュートリアル・特殊監査（64〜69）

**64. 防衛戦UI状態**
- 作業：`skill_eater_ui_systems.py`（または `skill_eater_territory_ui.py`）に `render_audit_defense(state)` の骨格を追加：上部(脅威度/予兆/ウェーブ)、中央(グリッド)、下部(行動パレット)。
- 完了条件：state dict を受け取り文字列出力（描画スタブ）を返す。

**65. 要塞化モードUI**
- 作業：予兆期間中用の `render_fortify_mode(state)` スタブ（配置/解体の選択リスト）。
- 完了条件：スタブが呼び出せる。

**66. 初回監査チュートリアル**
- 作業：`tutorial_controller.py` 連動で、T1監査時に「炎タレット1＋Husk壁」の錬成を案内するステップを追加。
- 完了条件：T1予兆時に案内メッセージが出る。

**67. 特殊監査フック**
- 作業：`SPECIAL_AUDIT_TYPES = {NIGHT, HEAVY, REVERSE_EAT, MERC_MIX}` と `roll_special_audit()`（乱数）を追加。各種は既存フラグで後段が分岐。
- 完了条件：`roll_special_audit` が enum を返す。

**68. アイコン描画**
- 作業：新施設/壁/地雷用のアイコン定数をUIに追加（既存 `EMOTE_*` にならう）。
- 完了条件：定数が参照できる。

**69. アクセシビリティ設定**
- 作業：`defense_options = {"speed":1.0, "auto_layout":False, "colorblind_icons":True}` を `get_defense_ui_state` に含める。
- 完了条件：状態に `defense_options` が含まれる。

---

## Phase 9 バランス・保存・総合テスト（70〜72）

**70. バランス定数＋監査シミュ**
- 作業：設計書15.6表を `AUDIT_BALANCE` 定数へ反映。`balance_test()` をオーバーライドし、監査ティアごとの勝率を出力（親の100シミ類似）。
- 完了条件：`balance_test(simulations=20)` が `win_rate` を返す。

**71. 保存/復元拡張**
- 作業：親 `to_dict/from_dict` をオーバーライドし、`threat_level`, `blueprints`, `husk_barricades`, `emp_mines`, `seized_skills` を含める。既存キーは維持。
- 完了条件：round-trip（`to_dict→from_dict`）で状態が一致。

**72. 総合ウォークスルーテスト**
- ファイル：`tests/test_audit_defense_walkthrough.py`（新規）
- 作業：T3監査を「予兆→炎/氷錬成→Husk壁配置→EMP設置→breach→部隊長弱体化→強奪」の順でシミュレートし、専用スキル獲得＋勝利を assert。
- 完了条件：`pytest tests/test_audit_defense_walkthrough.py` 成功。

---

## 実装順序の注意

- Phase 0→1→2→3 は「脅威度が上がり、捕食スキルでタレットを建設できる」最小実用ライン。ここまでで動くプロトタイプが得られる。
- Phase 4→5→6 で「Husk壁・EMP・部隊長強奪」の設計書コア体験が完成。
- Phase 7→8→9 は polish（シナジー・UI・バランス）。
- 各ステップは「既存 `BaseDefenseManager` の動作を壊さない」ことを前提とし、失敗時は直前ステップへ差し戻し可能にする。
- 全ステップにユニットテスト（6/9/15/17/21/24/27/32/34/39/43/45/47/52/54/57/58/60/72等）を置き、低性能LLMでも「テスト緑」を進捗の客観基準にできる。
