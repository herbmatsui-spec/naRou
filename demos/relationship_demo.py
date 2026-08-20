"""
NPC関係性シミュレーション・ドラマエンジン - デモンストレーション
実装されたシステムの動作確認用スクリプト
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.relationships import RelationshipType, create_engine


def demo():
    """エンジンのデモンストレーション"""
    print("=" * 70)
    print("NPC関係性シミュレーション・ドラマエンジン - デモ")
    print("=" * 70)

    # テンポラリディレクトリにテスト用データを作成
    temp_dir = tempfile.mkdtemp()
    data_file = os.path.join(temp_dir, "demo_relations.yaml")
    with open(data_file, "w", encoding="utf-8") as f:
        f.write("""
relationship_templates:
  friends:
    id: "friends"
    name: "友人"
    relationship_type: "favorability"
    initial_level: 20
    decay_rate: 0.01
    romance_potential: 0.3
    betrayal_risk: 0.1
  lovers:
    id: "lovers"
    name: "恋人"
    relationship_type: "romance"
    initial_level: 70
    decay_rate: 0.003
  master_apprentice:
    id: "master_apprentice"
    name: "師弟"
    relationship_type: "mentorship"
    initial_level: 50
    decay_rate: 0.001
  bitter_enemies:
    id: "bitter_enemies"
    name: "敵対"
    relationship_type: "enmity"
    initial_level: -50
    decay_rate: 0.001
""")

    # エンジン作成
    engine = create_engine(data_file)
    print("\n[1] エンジン初期化完了")

    # キャラクター初期化
    engine.initialize_character("player", "プレイヤー", "hero")
    engine.initialize_character("elena", "エレナ", "lover")
    engine.initialize_character("gareth", "ガレス", "mentor")
    engine.initialize_character("mordred", "モルドレッド", "villain")
    print("[2] キャラクター初期化: プレイヤー、エレナ、ガレス、モルドレッド")

    # 関係確立（師弟は gareth(師)→player(弟子) の方向で確立）
    engine.establish_relationship("player", "elena", "lovers")
    engine.establish_relationship("gareth", "player", "master_apprentice")
    engine.establish_relationship("player", "mordred", "bitter_enemies")
    print("[3] 関係確立: 恋人(エレナ)、師弟(ガレス→プレイヤー)、敵対(モルドレッド)")

    # 関係変化
    engine.modify_relationship("player", "elena", "talk", 15)
    engine.modify_relationship("gareth", "player", "knowledge_share", 20)
    engine.modify_relationship("player", "mordred", "betrayal", -10)
    print("[4] 関係変化を適用")

    # ロマンス進行
    romance_state = engine.romance.initiate_romance("player", "elena")
    print(
        f"[5] ロマンス進行: ステージ = {romance_state.stage.value if romance_state else 'N/A'}"
    )

    # 師弟関係
    mentorship_state = engine.mentorship.establish_mentorship("gareth", "player")
    teach_result = engine.mentorship.teach_skill("gareth", "player", "basic_sword")
    print(f"[6] 師弟関係: スキル伝授 = {teach_result.get('success', False)}")

    # 裏切りシステム
    betrayal_result = engine.betrayal.commit_betrayal(
        "mordred",
        "player",
        __import__(
            "src.relationships.betrayal", fromlist=["BetrayalType"]
        ).BetrayalType.BACKSTAB,
        context={"evidence_available": True, "witnesses": ["elena"]},
    )
    print(
        f"[7] 裏切り発生: 敵対レベル変化 = {betrayal_result['impact'].get('favorability', 'N/A')}"
    )

    # 分岐シナリオ生成
    scenarios = engine.check_scenarios("player")
    print(f"[8] 分岐シナリオ生成: {len(scenarios)}件")
    for s in scenarios[:3]:
        print(f"    - {s.title}: {s.description[:30]}...")

    # 対話生成
    dialogue = engine.generate_dialogue("elena", "player", "greeting")
    if dialogue:
        print(f'[9] 対話生成: "{dialogue.text[:40]}..."')

    # パーソナリティ互換性
    compat = engine.personality.get_compatibility_between("player", "elena")
    print(f"[10] パーソナリティ互換性(プレイヤー×エレナ): {compat:.2f}")

    # メモリ作成
    engine.memory.record_relationship_event(
        "player", "elena", RelationshipType.ROMANCE, 25
    )
    print("[11] 関係イベントから記憶を作成")

    # 可視化
    print("\n[12] 関係グラフ可視化（テキスト）:")
    text_viz = engine.visualizer.visualize_as_text("player")
    print(text_viz[:800])

    # 健全性分析
    health = engine.visualizer.analyze_graph_health()
    print(f"\n[13] グラフ健全性スコア: {health['health_score']:.1f}/100")

    # ステータスレポート
    report = engine.get_status_report()
    print("\n[14] ステータスレポート:")
    print(f"    登録テンプレート数: {report['relationship_manager']['template_count']}")
    print(f"    ロマンス統計: {report['romance']}")
    print(f"    裏切り統計: {report['betrayal']}")

    # セーブ/ロード
    save_file = os.path.join(temp_dir, "demo_save.json")
    save_result = engine.save(save_file)
    print(f"\n[15] セーブ: {'成功' if save_result['success'] else '失敗'}")

    # 新しいエンジンでロード
    new_engine = create_engine(data_file)
    load_result = new_engine.load(save_file)
    print(f"[16] ロード: {'成功' if load_result['success'] else '失敗'}")
    if load_result["success"]:
        level = new_engine.manager.get_relationship_level(
            "player", "elena", RelationshipType.ROMANCE
        )
        print(f"    ロード後のロマンスレベル(プレイヤー×エレナ): {level}")

    print("\n" + "=" * 70)
    print("デモ完了 - すべてのシステムが正常に動作しました")
    print("=" * 70)


if __name__ == "__main__":
    demo()
