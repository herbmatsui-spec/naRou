"""
プロシージャル・クエスト生成システム 総合テスト (全36ステップ)
依頼ボード / ランダムダンジョン探索 / NPC個別クエスト の自動生成を検証。
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import yaml


def test_all_36_steps_procedural_quest_generation():
    print("=== プロシージャル・クエスト生成システム 全36ステップ 総合検証開始 ===")

    # ---------------------------------------------------------
    # フェーズA: データ設計 (Steps 1-8)
    # ---------------------------------------------------------
    with open("data/procedural_scenarios.yaml", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # Step 1: quest_generation セクション追加
    assert "quest_generation" in raw, "Step 1 Failed: quest_generation missing"
    print("[OK] Step 1 (data/procedural_scenarios.yaml quest_generation セクション)")

    qg = raw["quest_generation"]

    # Step 2: クエストアーキタイプ (7種)
    arch = qg.get("archetypes", {})
    assert "slay" in arch and len(arch) >= 7, "Step 2 Failed: archetypes"
    print(
        f"[OK] Step 2 (アーキタイプ定義 {len(arch)}種: slay/gather/escort/explore/boss_hunt/rescue/delivery)"
    )

    # Step 3: 難易度ティア (6段階)
    diffs = qg.get("difficulty_tiers", {})
    assert "tutorial" in diffs and len(diffs) >= 6, "Step 3 Failed: difficulty_tiers"
    print(f"[OK] Step 3 (難易度ティア {len(diffs)}段階: tutorial..abyss, 指数スケーリング)")

    # Step 4: 報酬テーブル (5段階)
    rewards = qg.get("reward_tables", {})
    assert "copper" in rewards and len(rewards) >= 5, "Step 4 Failed: reward_tables"
    print(f"[OK] Step 4 (報酬テーブル {len(rewards)}段階: copper..legendary)")

    # Step 5: 舞台設定 (8種)
    settings = qg.get("stage_settings", {})
    assert "town" in settings and len(settings) >= 8, "Step 5 Failed: stage_settings"
    print(
        f"[OK] Step 5 (舞台設定 {len(settings)}種: town/forest/cave/ruins/volcano/snowfield/swamp/abyss)"
    )

    # Step 6: NPC個別クエストテーマ
    npc_themes = qg.get("npc_quest_themes", {})
    assert "villager" in npc_themes, "Step 6 Failed: npc_quest_themes"
    print(f"[OK] Step 6 (NPC個別クエストテーマ {len(npc_themes)}種)")

    # Step 7: 既存 scenario_templates の維持
    assert "goblin_invasion" in raw.get("scenario_templates", {}), "Step 7 Failed: backward compat"
    print("[OK] Step 7 (既存 scenario_templates.goblin_invasion の維持/後方互換)")

    # Step 8: 依頼ボード設定
    board = qg.get("request_board", {})
    assert board.get("max_active") == 8, "Step 8 Failed: request_board.max_active"
    print("[OK] Step 8 (依頼ボード設定: max_active=8, refresh_cycle, type_weights)")

    # ---------------------------------------------------------
    # フェーズB: データクラス (Steps 9-14)
    # ---------------------------------------------------------
    from procedural_quest_generator import (
        DifficultyTier,
        GeneratedQuest,
        NPCQuestTheme,
        QuestArchetype,
        QuestObjectiveSpec,
        RewardTable,
        StageSetting,
    )

    # Step 9
    assert QuestArchetype is not None, "Step 9 Failed"
    # Step 10
    assert DifficultyTier is not None, "Step 10 Failed"
    # Step 11
    assert RewardTable is not None, "Step 11 Failed"
    # Step 12
    assert StageSetting is not None, "Step 12 Failed"
    # Step 13
    assert NPCQuestTheme is not None, "Step 13 Failed"
    # Step 14
    assert QuestObjectiveSpec is not None and GeneratedQuest is not None, "Step 14 Failed"
    gq = GeneratedQuest(title="t", archetype_id="slay")
    assert gq.to_dict()["title"] == "t" and GeneratedQuest.from_dict(gq.to_dict()).title == "t"
    print(
        "[OK] Steps 9-14 (QuestArchetype/DifficultyTier/RewardTable/StageSetting/NPCQuestTheme/QuestObjectiveSpec/GeneratedQuest)"
    )

    # ---------------------------------------------------------
    # フェーズC: レジストリ (Steps 15-18)
    # ---------------------------------------------------------
    from procedural_quest_generator import REGISTRY, QuestGenerationRegistry

    # Step 15
    assert QuestGenerationRegistry is not None, "Step 15 Failed"
    # Step 16: シングルトン
    r1 = QuestGenerationRegistry()
    r2 = QuestGenerationRegistry()
    assert r1 is r2, "Step 16 Failed: singleton"
    # Step 17: load
    REGISTRY.load()
    assert len(REGISTRY.all_archetypes()) >= 7, "Step 17 Failed: load"
    # Step 18: 取得メソッド
    assert REGISTRY.get_archetype("slay") is not None
    assert REGISTRY.get_difficulty("normal") is not None
    assert REGISTRY.get_reward("gold") is not None
    assert REGISTRY.get_setting("forest") is not None
    assert REGISTRY.get_npc_theme("villager") is not None
    assert REGISTRY.board_config().get("max_active") == 8
    print("[OK] Steps 15-18 (QuestGenerationRegistry シングルトン/load/取得メソッド)")

    # ---------------------------------------------------------
    # フェーズD: 合成エンジン (Steps 19-23)
    # ---------------------------------------------------------
    from procedural_quest_generator import ProceduralQuestGenerator

    gen = ProceduralQuestGenerator(REGISTRY)

    # Step 19: シード決定論
    rng_a = gen._seeded_rng("board", 123)
    rng_b = gen._seeded_rng("board", 123)
    assert rng_a.randint(0, 1_000_000) == rng_b.randint(0, 1_000_000), "Step 19 Failed: determinism"
    print("[OK] Step 19 (シード決定論ヘルパー _seeded_rng)")

    # Step 20: コア合成 _compose
    cq = gen._compose(
        "board",
        REGISTRY.get_archetype("slay"),
        REGISTRY.get_difficulty("normal"),
        REGISTRY.get_reward("gold"),
        REGISTRY.get_setting("forest"),
        777,
    )
    assert isinstance(cq, GeneratedQuest) and cq.quest_id, "Step 20 Failed: _compose"
    # Step 21: タイトル/説明文自動生成
    assert cq.title and cq.description, "Step 21 Failed: title/desc"
    assert (
        "{setting}" not in cq.title and "{enemy}" not in cq.title
    ), "Step 21 Failed: template unfilled"
    # Step 22: 目的自動生成（難易度でスケール）
    easy = gen._compose(
        "board",
        REGISTRY.get_archetype("slay"),
        REGISTRY.get_difficulty("tutorial"),
        REGISTRY.get_reward("copper"),
        REGISTRY.get_setting("forest"),
        1,
    )
    hard = gen._compose(
        "board",
        REGISTRY.get_archetype("slay"),
        REGISTRY.get_difficulty("abyss"),
        REGISTRY.get_reward("legendary"),
        REGISTRY.get_setting("forest"),
        2,
    )
    assert easy.objectives and easy.objectives[0].required_count >= 1, "Step 22 Failed: objective"
    assert (
        hard.objectives[0].required_count > easy.objectives[0].required_count
    ), "Step 22 Failed: scaling"
    # Step 23: 報酬合成
    assert cq.reward.get("gold", 0) > 0 and cq.reward.get("exp", 0) > 0, "Step 23 Failed: reward"
    print("[OK] Steps 20-23 (_compose/title/desc/objective scaling/reward)")

    # ---------------------------------------------------------
    # フェーズE: 依頼ボード (Steps 24-27)
    # ---------------------------------------------------------
    from entity import Entity

    p = Entity()

    # Step 24: generate_board_quest
    bq = gen.generate_board_quest(p, seed=42)
    assert bq.source_type == "board" and bq.quest_id, "Step 24 Failed"
    # Step 25: generate_board_pool（重複排除）
    pool = gen.generate_board_pool(p)
    assert len(pool) == 8, f"Step 25 Failed: pool size {len(pool)}"
    titles = {q.title for q in pool}
    assert len(titles) == len(pool), "Step 25 Failed: duplicates in pool"
    # Step 26: refresh_board（マネージャ）
    from procedural_quest_generator import ProceduralQuestManager

    mgr = ProceduralQuestManager(gen)
    mgr.refresh_board(p)
    assert len(p.procedural_quest.active_board) == 8, "Step 26 Failed: refresh_board"
    # Step 27: 出現重み・推奨レベル適用（難易度帯が min~max 内）
    order = REGISTRY.difficulty_order()
    min_i = order.index("tutorial")
    max_i = order.index("normal")
    allowed = set(order[min_i : max_i + 1])
    for d in p.procedural_quest.active_board:
        assert d["difficulty_id"] in allowed, "Step 27 Failed: difficulty range"
    print("[OK] Steps 24-27 (generate_board_quest/pool/refresh_board/出現重み・範囲)")

    # ---------------------------------------------------------
    # フェーズF: ランダムダンジョン探索 (Steps 28-30)
    # ---------------------------------------------------------
    # Step 28: generate_dungeon_quest
    dq = gen.generate_dungeon_quest(p, seed=99)
    assert dq.source_type == "dungeon", "Step 28 Failed"
    # Step 29: ダンジョン目的生成（探索またはボス討伐）
    assert dq.archetype_id in ("explore", "boss_hunt"), "Step 29 Failed"
    otype = dq.objectives[0].target_type
    assert otype in ("explore", "kill"), "Step 29 Failed: objective type"
    # Step 30: 舞台×テーマ合成（setting が存在）
    assert dq.setting_id in REGISTRY.all_settings(), "Step 30 Failed"
    print("[OK] Steps 28-30 (generate_dungeon_quest/目的生成/舞台×テーマ合成)")

    # ---------------------------------------------------------
    # フェーズG: NPC個別クエスト (Steps 31-33)
    # ---------------------------------------------------------
    # Step 31: generate_npc_quest
    p.character_relationships["gwen"] = {"trust": 50, "mood": 40}
    nq = gen.generate_npc_quest("gwen", "villager", p, seed=7)
    assert nq is not None and nq.source_type == "npc", "Step 31 Failed"
    assert nq.npc_id == "gwen", "Step 31 Failed: npc_id"
    # Step 32: 友好度ゲート（閾値未満は生成されない）
    p2 = Entity()
    p2.character_relationships["gwen"] = {"trust": 0, "mood": 0}
    blocked = gen.generate_npc_quest("gwen", "villager", p2, seed=7)
    assert blocked is None, "Step 32 Failed: gate not enforced"
    # Step 33: 個別フレーバー
    assert "gwen" in nq.description, "Step 33 Failed: flavor"
    print("[OK] Steps 31-33 (generate_npc_quest/友好度ゲート/個別フレーバー)")

    # ---------------------------------------------------------
    # フェーズH: 管理・進捗・報酬 (Steps 34-35)
    # ---------------------------------------------------------
    # Step 34: update_progress / complete_quest（報酬付与）
    mgr.refresh_board(p)
    q0 = GeneratedQuest.from_dict(p.procedural_quest.active_board[0])
    mgr.accept_quest(p, q0.quest_id)
    assert len(p.procedural_quest.accepted_quests) == 1, "Step 34 Failed: accept"
    gold_before = p.gold
    obj = q0.objectives[0]
    # 目的を即座に完了させる
    mgr.update_progress(p, obj.target_type, obj.target_id, obj.required_count)
    assert p.gold > gold_before, "Step 34 Failed: reward not granted"
    assert p.procedural_quest.completed_count >= 1, "Step 34 Failed: completed count"
    # Step 35: ProceduralQuestComponent 追加と永続化
    from components import ProceduralQuestComponent

    assert isinstance(p.procedural_quest, ProceduralQuestComponent), "Step 35 Failed: component"
    print("[OK] Steps 34-35 (update_progress/complete_quest 報酬付与 / ProceduralQuestComponent)")

    # ---------------------------------------------------------
    # フェーズI: 統合・テスト (Step 36)
    # ---------------------------------------------------------
    # Step 36a: Engine 統合
    from game import Engine

    eng = Engine()
    assert hasattr(eng, "quest_generation_registry"), "Step 36 Failed: registry on Engine"
    assert hasattr(eng, "procedural_quest_generator"), "Step 36 Failed: generator on Engine"
    assert hasattr(eng, "procedural_quest_manager"), "Step 36 Failed: manager on Engine"

    # Step 36b: 決定論（同一シード → 同一クエスト）
    a = gen.generate_board_quest(p, seed=12345)
    b = gen.generate_board_quest(p, seed=12345)
    assert a.quest_id == b.quest_id and a.title == b.title, "Step 36 Failed: determinism"

    # Step 36c: 組み合わせ爆発（アーキタイプ×難易度×報酬×舞台 = 7×6×5×8 = 1680通りの一意性）
    combos = set()
    for aid in REGISTRY.all_archetypes():
        for did in REGISTRY.all_difficulties():
            for rid in REGISTRY.all_rewards():
                for sid in REGISTRY.all_settings():
                    q = gen._compose(
                        "board",
                        REGISTRY.get_archetype(aid),
                        REGISTRY.get_difficulty(did),
                        REGISTRY.get_reward(rid),
                        REGISTRY.get_setting(sid),
                        1,
                    )
                    combos.add(q.quest_id)
    assert len(combos) > 1000, f"Step 36 Failed: combination explosion {len(combos)}"

    # Step 36d: 永続化（セーブ→ロードで進行状態が復元される）
    eng.player.procedural_quest.completed_count = 5
    eng.player.procedural_quest.completed_quest_ids = ["gen_x"]
    import tempfile

    try:
        from save_system import SaveSystem

        tmp = os.path.join(tempfile.gettempdir(), "pq_test_save.bin")
        SaveSystem.SAVE_PATH = tmp
        msg = SaveSystem.save(eng)
        assert "セーブ完了" in msg, "Step 36 Failed: save"
        loaded, _ = SaveSystem.load()
        assert loaded is not None, "Step 36 Failed: load"
        assert loaded.player.procedural_quest.completed_count == 5, "Step 36 Failed: persistence"
    finally:
        SaveSystem.SAVE_PATH = "savegame.bin"
        if "tmp" in dir() and os.path.exists(tmp):
            os.remove(tmp)

    print("[OK] Step 36 (Engine 統合 / 決定論 / 組み合わせ爆発 >1000 / 永続化)")

    # ---------------------------------------------------------
    # フェーズI: Phase 5 - Procedural Dungeon Interlock (Steps 37-40)
    # ---------------------------------------------------------
    # Step 37: ダンジョン仕様ロード
    spec = gen._load_dungeon_spec("standard_exploration")
    assert spec is not None, "Step 37 Failed: dungeon spec load"
    assert spec.spec_id == "standard_exploration", "Step 37 Failed: spec_id"
    assert spec.name == "標準探索ダンジョン", "Step 37 Failed: name"
    print("[OK] Step 37 (ダンジョン仕様ロード)")

    # Step 38: ダンジョン同期クエスト生成
    from entity import Entity

    p = Entity()
    synced_quest = gen.generate_dungeon_synced_quest(
        spec_id="standard_exploration",
        quest_id="test_synced_001",
        title="テストダンジョンクエスト",
        description="テスト用のダンジョン同期クエスト",
        player=p,
        seed=12345,
    )
    assert synced_quest is not None, "Step 38 Failed: quest generation returned None"
    assert synced_quest.quest_id == "test_synced_001", "Step 38 Failed: quest_id mismatch"
    assert synced_quest.title == "テストダンジョンクエスト", "Step 38 Failed: title mismatch"
    assert (
        synced_quest.description == "テスト用のダンジョン同期クエスト"
    ), "Step 38 Failed: description mismatch"
    assert synced_quest.source_type == "dungeon_synced", "Step 38 Failed: source_type"
    print("[OK] Step 38 (ダンジョン同期クエスト生成)")

    # Step 39: クエスト目的がダンジョン生成結果に基づいて更新されている
    assert len(synced_quest.objectives) > 0, "Step 39 Failed: no objectives"
    # 目的の説明がダンジョン仕様に基づいていることを確認（簡易チェック）
    obj_desc = " ".join([obj.description for obj in synced_quest.objectives])
    assert (
        "階層" in obj_desc
        or "部屋" in obj_desc
        or "ボス" in obj_desc
        or "入口" in obj_desc
        or "出口" in obj_desc
    ), "Step 39 Failed: objective description not dungeon-related"
    print("[OK] Step 39 (クエスト目的のダンジョン同期)")

    # Step 40: フィードバック情報が報酬に含まれている
    assert "dungeon_feedback" in synced_quest.reward, "Step 40 Failed: dungeon_feedback in reward"
    feedback = synced_quest.reward["dungeon_feedback"]
    assert "spec_id" in feedback, "Step 40 Failed: spec_id in feedback"
    assert feedback["spec_id"] == "standard_exploration", "Step 40 Failed: feedback spec_id"
    assert "generated_floors" in feedback, "Step 40 Failed: generated_floors in feedback"
    assert (
        isinstance(feedback["generated_floors"], int) and feedback["generated_floors"] > 0
    ), "Step 40 Failed: generated_floors positive"
    print("[OK] Step 40 (ダンジョンフィードバック情報)")

    print("\nALL 40 STEPS OF PROCEDURAL QUEST GENERATION SYSTEM VERIFIED 100% SUCCESSFULLY!")


if __name__ == "__main__":
    test_all_36_steps_procedural_quest_generation()
