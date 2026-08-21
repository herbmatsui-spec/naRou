"""
NPC Relationship Simulation - Dialogue Generation System
Step 14: Dialogue generation based on relationships
"""

from __future__ import annotations

import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .engine import RelationshipManager
from .models import RelationshipType
from .personality import CharacterArchetype, PersonalityTrait


class DialogueMood(Enum):
    """対話の雰囲気"""

    FRIENDLY = "friendly"  # 友好的
    HOSTILE = "hostile"  # 敵対的
    NEUTRAL = "neutral"  # 中立
    INTIMATE = "intimate"  # 親密
    TENSE = "tense"  # 緊張
    PLAYFUL = "playful"  # 遊び心
    RESPECTFUL = "respectful"  # 敬意
    COLD = "cold"  # 冷たい


class DialogueContext(Enum):
    """対話コンテキスト"""

    GREETING = "greeting"  # 挨拶
    FAREWELL = "farewell"  # 別れ
    QUEST = "quest"  # クエスト関連
    SMALL_TALK = "small_talk"  # 雑談
    CONFLICT = "conflict"  # 対立
    ROMANCE = "romance"  # 恋愛
    MENTORSHIP = "mentorship"  # 師弟
    TRADING = "trading"  # 取引
    CRISIS = "crisis"  # 危機


@dataclass
class DialogueTemplate:
    """対話テンプレート"""

    template_id: str
    context: DialogueContext
    mood: DialogueMood
    relationship_type: RelationshipType
    min_level: int
    max_level: int
    templates: list[str]
    required_archetype: CharacterArchetype | None = None
    conditions: dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedDialogue:
    """生成された対話"""

    speaker_id: str
    listener_id: str
    context: DialogueContext
    mood: DialogueMood
    text: str
    relationship_type: RelationshipType
    relationship_level: int
    emotional_tone: str
    timestamp: float = field(default_factory=time.time)
    follow_up_options: list[str] = field(default_factory=list)


class DialogueGenerationSystem:
    """
    関係ベースの対話生成システム
    関係状態に応じたダイアログテンプレートの選択とプロシージャル生成
    """

    def __init__(
        self,
        relationship_manager: RelationshipManager,
        personality_system: PersonalitySystem | None = None,
    ):
        self.rm = relationship_manager
        self.graph = relationship_manager.graph
        self.personality_system = personality_system

        # 対話テンプレート
        self.templates: list[DialogueTemplate] = self._load_dialogue_templates()

        # コンテキスト別の話題
        self.topics_by_context: dict[DialogueContext, list[str]] = self._load_topics()

        # キャラクター特有の対話パターン
        self.character_speech_patterns: dict[str, dict[str, Any]] = {}

        # 対話履歴
        self.dialogue_history: dict[tuple[str, str], list[GeneratedDialogue]] = (
            defaultdict(list)
        )

        # 設定
        self._config = {
            "max_history_per_pair": 50,
            "relationship_influence": 0.7,
            "personality_influence": 0.3,
            "random_variation": 0.2,
        }

    def _load_dialogue_templates(self) -> list[DialogueTemplate]:
        """対話テンプレートのロード"""
        templates = [
            # 挨拶 - 友好的
            DialogueTemplate(
                template_id="greet_friendly",
                context=DialogueContext.GREETING,
                mood=DialogueMood.FRIENDLY,
                relationship_type=RelationshipType.FAVORABILITY,
                min_level=20,
                max_level=100,
                templates=[
                    "やあ、{player_name}！久しぶりだね。元気にしてた？",
                    "おっ、{player_name}じゃないか。今日はどうしたの？",
                    "お帰りなさい、{player_name}。いつも頼りにしてるよ。",
                    "ごきげんよう、{player_name}。今日も素敵だね。",
                ],
            ),
            # 挨拶 - 敵対的
            DialogueTemplate(
                template_id="greet_hostile",
                context=DialogueContext.GREETING,
                mood=DialogueMood.HOSTILE,
                relationship_type=RelationshipType.FAVORABILITY,
                min_level=-100,
                max_level=-20,
                templates=[
                    "…お前か。ここには用はないだろう。",
                    "嫌な予感がすると思ったら、お前だったのか。",
                    "何しに来た？用がないなら消えな。",
                    "ふん、またお前か。勘弁してくれ。",
                ],
            ),
            # 挨拶 - 中立
            DialogueTemplate(
                template_id="greet_neutral",
                context=DialogueContext.GREETING,
                mood=DialogueMood.NEUTRAL,
                relationship_type=RelationshipType.FAVORABILITY,
                min_level=-19,
                max_level=19,
                templates=[
                    "こんにちは、{player_name}。",
                    "やあ、何か用かい？",
                    "お疲れ様です、{player_name}。",
                    "今日はいい天気ですね。",
                ],
            ),
            # 恋愛 - 親密
            DialogueTemplate(
                template_id="romance_intimate",
                context=DialogueContext.ROMANCE,
                mood=DialogueMood.INTIMATE,
                relationship_type=RelationshipType.ROMANCE,
                min_level=50,
                max_level=100,
                templates=[
                    "あなたがそばにいるだけで、心が安らぐの。",
                    "昨日のことは…本当に幸せだった。ありがとう。",
                    "将来のこと、考えてもいいかな？",
                    "あなたの笑顔が、私の一番の宝物だわ。",
                ],
            ),
            # 師弟 - 敬意
            DialogueTemplate(
                template_id="mentor_respect",
                context=DialogueContext.MENTORSHIP,
                mood=DialogueMood.RESPECTFUL,
                relationship_type=RelationshipType.MENTORSHIP,
                min_level=40,
                max_level=100,
                templates=[
                    "師匠、今日も教えを乞います。",
                    "あなたの言葉は、いつも私の支えです。",
                    "師匠のようになりたいと、本気で思っています。",
                    "この技、師匠ならどうされますか？",
                ],
            ),
            # 対立 - 緊張
            DialogueTemplate(
                template_id="conflict_tense",
                context=DialogueContext.CONFLICT,
                mood=DialogueMood.TENSE,
                relationship_type=RelationshipType.ENMITY,
                min_level=20,
                max_level=100,
                templates=[
                    "君とは、話が合わないな。",
                    "これ以上深入りするのはやめよう。",
                    "今日はここまでにしておこう。",
                    "また、意見が対立してしまったか。",
                ],
            ),
        ]
        return templates

    def _load_topics(self) -> dict[DialogueContext, list[str]]:
        """コンテキスト別の話題をロード"""
        return {
            DialogueContext.SMALL_TALK: [
                "最近の天気について",
                "この街の噂話",
                "美味しい店の話",
                "趣味の話",
                "最近読んだ本",
                "旅の思い出",
            ],
            DialogueContext.QUEST: [
                "近くで起きている事件",
                "困っている村人",
                "盗まれた品物",
                "魔物の出没",
                "古い遺跡の探索",
                "ギルドの依頼",
            ],
            DialogueContext.ROMANCE: [
                "二人の将来",
                "好きな場所",
                "大切な思い出",
                "デートの約束",
                "素直な気持ち",
                "不安なこと",
            ],
            DialogueContext.MENTORSHIP: [
                "技術の研鑽",
                "過去の経験",
                "試練の意味",
                "奥義の秘訣",
                "師弟の絆",
                "継承すべき志",
            ],
            DialogueContext.TRADING: [
                "商品の価値",
                "相場の動向",
                "希少な素材",
                "取引の条件",
                "長期的な協力",
                "互恵の関係",
            ],
            DialogueContext.CRISIS: [
                "迫りくる危機",
                "守るべきもの",
                "戦う理由",
                "仲間の安否",
                "過去の失敗",
                "希望の光",
            ],
        }

    def generate_dialogue(
        self,
        speaker_id: str,
        listener_id: str,
        context: DialogueContext,
        relationship_type: RelationshipType | None = None,
    ) -> GeneratedDialogue | None:
        """対話を生成"""
        # 話し手と聞き手の情報を取得
        speaker_node = self.graph.get_node(speaker_id)
        listener_node = self.graph.get_node(listener_id)

        if not speaker_node or not listener_node:
            return None

        # 関係タイプが指定されていない場合は、コンテキストに適したものを選択
        if relationship_type is None:
            relationship_type = self._select_relationship_type(context)

        # 関係レベルを取得
        relationship_level = self.rm.get_relationship_level(
            speaker_id, listener_id, relationship_type
        )

        # 適切なテンプレートを選択
        template = self._select_template(
            context, relationship_type, relationship_level, speaker_id
        )
        if not template:
            return None

        # パーソナリティに基づく修正
        if self.personality_system:
            speaker_profile = self.personality_system.get_profile(speaker_id)
            if speaker_profile:
                speaker_profile.get_trait(
                    PersonalityTrait.EXTRAVERSION
                )

        # テキストを生成（テンプレートの変数を置換）
        template_text = random.choice(template.templates)
        text = self._fill_template(template_text, speaker_node, listener_node)

        # 話題を追加（小話などの場合）
        topic = None
        if context in self.topics_by_context:
            topic = random.choice(self.topics_by_context[context])
            text += f"（話題：{topic}）"

        # 感情的トーンを決定
        emotional_tone = self._determine_emotional_tone(
            template.mood, relationship_level
        )

        # フォローアップオプションを生成
        follow_ups = self._generate_follow_up_options(context, template.mood)

        dialogue = GeneratedDialogue(
            speaker_id=speaker_id,
            listener_id=listener_id,
            context=context,
            mood=template.mood,
            text=text,
            relationship_type=relationship_type,
            relationship_level=relationship_level,
            emotional_tone=emotional_tone,
            follow_up_options=follow_ups,
        )

        # 履歴に記録
        self._record_dialogue(dialogue)

        return dialogue

    def _select_relationship_type(self, context: DialogueContext) -> RelationshipType:
        """コンテキストに適した関係タイプを選択"""
        mapping = {
            DialogueContext.GREETING: RelationshipType.FAVORABILITY,
            DialogueContext.FAREWELL: RelationshipType.FAVORABILITY,
            DialogueContext.QUEST: RelationshipType.FAVORABILITY,
            DialogueContext.SMALL_TALK: RelationshipType.FRIENDSHIP,
            DialogueContext.CONFLICT: RelationshipType.ENMITY,
            DialogueContext.ROMANCE: RelationshipType.ROMANCE,
            DialogueContext.MENTORSHIP: RelationshipType.MENTORSHIP,
            DialogueContext.TRADING: RelationshipType.BUSINESS,
            DialogueContext.CRISIS: RelationshipType.FAVORABILITY,
        }
        return mapping.get(context, RelationshipType.FAVORABILITY)

    def _select_template(
        self,
        context: DialogueContext,
        relationship_type: RelationshipType,
        relationship_level: int,
        speaker_id: str = "",
    ) -> DialogueTemplate | None:
        """条件に合うテンプレートを選択"""
        candidates = []

        for template in self.templates:
            if template.context != context:
                continue
            if template.relationship_type != relationship_type:
                continue
            if not (template.min_level <= relationship_level <= template.max_level):
                continue

            # アーキタイプ条件
            if template.required_archetype:
                speaker_profile = (
                    self.personality_system.get_profile(speaker_id)
                    if self.personality_system
                    else None
                )
                if (
                    not speaker_profile
                    or speaker_profile.archetype != template.required_archetype
                ):
                    continue

            candidates.append(template)

        if not candidates:
            # フォールバック：レベルのみでマッチするものを探す
            for template in self.templates:
                if (
                    template.context == context
                    and template.min_level <= relationship_level <= template.max_level
                ):
                    candidates.append(template)

        if not candidates:
            return None

        return random.choice(candidates)

    def _fill_template(
        self, template: str, speaker_node: Any, listener_node: Any
    ) -> str:
        """テンプレートの変数を置換"""
        return template.replace("{speaker_name}", speaker_node.name).replace(
            "{player_name}", listener_node.name
        )

    def _determine_emotional_tone(
        self, mood: DialogueMood, relationship_level: int
    ) -> str:
        """感情的トーンを決定"""
        if mood == DialogueMood.FRIENDLY:
            return "温かい" if relationship_level > 50 else "穏やか"
        elif mood == DialogueMood.HOSTILE:
            return "鋭い" if relationship_level < -50 else "冷ややか"
        elif mood == DialogueMood.INTIMATE:
            return "甘い" if relationship_level > 80 else "優しい"
        elif mood == DialogueMood.TENSE:
            return "張り詰めた"
        elif mood == DialogueMood.PLAYFUL:
            return "軽快な"
        elif mood == DialogueMood.RESPECTFUL:
            return "敬虔な"
        elif mood == DialogueMood.COLD:
            return "無機質な"
        else:
            return "中立的"

    def _generate_follow_up_options(
        self, context: DialogueContext, mood: DialogueMood
    ) -> list[str]:
        """フォローアップオプションを生成"""
        if context == DialogueContext.ROMANCE:
            return ["優しく応える", "照れて誤魔化す", "真剣に答える", "軽く流す"]
        elif context == DialogueContext.MENTORSHIP:
            return ["熱心に学ぶ", "質問する", "感謝を伝える", "自分の考えを述べる"]
        elif context == DialogueContext.CONFLICT:
            return ["距離を置く", "話し合いを続ける", "譲歩する", "反論する"]
        elif context == DialogueContext.QUEST:
            return ["引き受ける", "断る", "詳細を聞く", "報酬を交渉する"]
        elif context == DialogueContext.TRADING:
            return ["値切る", "買う", "売る", "保留する"]
        else:
            return ["相槌を打つ", "質問する", "話を広げる", "話題を変える"]

    def generate_procedural_dialogue(
        self,
        speaker_id: str,
        listener_id: str,
        context: DialogueContext,
        relationship_type: RelationshipType | None = None,
    ) -> GeneratedDialogue | None:
        """プロシージャル対話を生成（テンプレートなしの動的生成）"""
        speaker_node = self.graph.get_node(speaker_id)
        listener_node = self.graph.get_node(listener_id)

        if not speaker_node or not listener_node:
            return None

        if relationship_type is None:
            relationship_type = self._select_relationship_type(context)

        relationship_level = self.rm.get_relationship_level(
            speaker_id, listener_id, relationship_type
        )

        # パーソナリティに基づく対話スタイル
        style_prefix = ""
        style_suffix = ""
        if self.personality_system:
            profile = self.personality_system.get_profile(speaker_id)
            if profile:
                if profile.get_trait(PersonalityTrait.EXTRAVERSION) > 0.7:
                    style_prefix = "（元気よく）"
                elif profile.get_trait(PersonalityTrait.NEUROTICISM) > 0.7:
                    style_prefix = "（少し不安げに）"
                elif profile.get_trait(PersonalityTrait.CONSCIENTIOUSNESS) > 0.7:
                    style_suffix = "（真剣な表情で）"

        # コンテキストと関係に基づくベーステキスト
        base_text = self._generate_base_text(
            context, relationship_type, relationship_level, speaker_node, listener_node
        )

        text = f"{style_prefix}{base_text}{style_suffix}"

        mood = self._determine_mood_from_level(relationship_type, relationship_level)
        emotional_tone = self._determine_emotional_tone(mood, relationship_level)

        dialogue = GeneratedDialogue(
            speaker_id=speaker_id,
            listener_id=listener_id,
            context=context,
            mood=mood,
            text=text,
            relationship_type=relationship_type,
            relationship_level=relationship_level,
            emotional_tone=emotional_tone,
            follow_up_options=self._generate_follow_up_options(context, mood),
        )

        self._record_dialogue(dialogue)

        return dialogue

    def _generate_base_text(
        self,
        context: DialogueContext,
        relationship_type: RelationshipType,
        level: int,
        speaker_node: Any,
        listener_node: Any,
    ) -> str:
        """ベーステキストを生成"""
        listener_name = listener_node.name

        if context == DialogueContext.GREETING:
            if level > 40:
                return f"{listener_name}さん、お会いできて嬉しいです。"
            elif level < -40:
                return f"…{listener_name}。何用ですか。"
            else:
                return f"こんにちは、{listener_name}。"
        elif context == DialogueContext.SMALL_TALK:
            topics = self.topics_by_context.get(DialogueContext.SMALL_TALK, [])
            topic = random.choice(topics) if topics else "色々なこと"
            return f"最近の{topic}について、どう思いますか？"
        elif context == DialogueContext.QUEST:
            return f"{listener_name}、頼みたいことがあるのですが…。"
        elif context == DialogueContext.ROMANCE:
            if level > 60:
                return f"{listener_name}、あなたと過ごす時間は私の宝物です。"
            elif level > 20:
                return f"{listener_name}のこと、もっと知りたいな。"
            else:
                return f"{listener_name}…少し緊張しますね。"
        elif context == DialogueContext.MENTORSHIP:
            if level > 60:
                return "師匠、次はどのような試練が待っていますか？"
            else:
                return "教えを乞います、よろしくお願いします。"
        else:
            return f"{listener_name}、少しお話ししませんか？"

    def _determine_mood_from_level(
        self, relationship_type: RelationshipType, level: int
    ) -> DialogueMood:
        """レベルから雰囲気を決定"""
        if relationship_type == RelationshipType.ROMANCE:
            if level > 50:
                return DialogueMood.INTIMATE
            elif level < -20:
                return DialogueMood.COLD
            else:
                return DialogueMood.FRIENDLY

        if relationship_type == RelationshipType.ENMITY:
            if level > 20:
                return DialogueMood.TENSE
            else:
                return DialogueMood.HOSTILE

        if relationship_type == RelationshipType.MENTORSHIP:
            if level > 40:
                return DialogueMood.RESPECTFUL
            else:
                return DialogueMood.NEUTRAL

        # 好感度ベース
        if level > 40:
            return DialogueMood.FRIENDLY
        elif level < -40:
            return DialogueMood.HOSTILE
        else:
            return DialogueMood.NEUTRAL

    def _record_dialogue(self, dialogue: GeneratedDialogue) -> None:
        """対話履歴を記録"""
        key = (dialogue.speaker_id, dialogue.listener_id)
        self.dialogue_history[key].append(dialogue)

        # 最大履歴数を超えた場合は古いものを削除
        if len(self.dialogue_history[key]) > self._config["max_history_per_pair"]:
            self.dialogue_history[key] = self.dialogue_history[key][
                -self._config["max_history_per_pair"] :
            ]

    def get_dialogue_history(
        self, speaker_id: str, listener_id: str, limit: int = 10
    ) -> list[GeneratedDialogue]:
        """対話履歴を取得"""
        key = (speaker_id, listener_id)
        history = self.dialogue_history.get(key, [])
        return history[-limit:] if limit else history

    def generate_relationship_reflection(self, character_id: str, other_id: str) -> str:
        """関係についての内省的な対話を生成"""
        character_node = self.graph.get_node(character_id)
        other_node = self.graph.get_node(other_id)

        if not character_node or not other_node:
            return ""

        # すべての関係タイプを確認
        reflections = []
        for rel_type in RelationshipType:
            level = self.rm.get_relationship_level(character_id, other_id, rel_type)
            if abs(level) < 15:
                continue

            reflection = self._create_reflection_text(rel_type, level, other_node.name)
            if reflection:
                reflections.append(reflection)

        if not reflections:
            return f"{other_node.name}のことは、まだよく分からないな。"

        return random.choice(reflections)

    def _create_reflection_text(
        self, rel_type: RelationshipType, level: int, other_name: str
    ) -> str:
        """内省テキストを作成"""
        rel_names = {
            RelationshipType.FAVORABILITY: "好感",
            RelationshipType.ROMANCE: "恋愛",
            RelationshipType.MENTORSHIP: "師弟",
            RelationshipType.ENMITY: "敵対",
            RelationshipType.FRIENDSHIP: "友情",
            RelationshipType.FAMILY: "家族",
            RelationshipType.RIVALRY: "競争",
            RelationshipType.BETRAYAL: "信頼",
            RelationshipType.BUSINESS: "取引",
            RelationshipType.FACTION: "派閥",
        }

        rel_name = rel_names.get(rel_type, "関係")

        if level > 70:
            return f"{other_name}とは、本当に深い{rel_name}関係だ。大切にしたい。"
        elif level > 40:
            return f"{other_name}のことは信頼している。良き{rel_name}だ。"
        elif level > 15:
            return f"{other_name}とはまずまずの{rel_name}関係だと思う。"
        elif level < -70:
            return f"{other_name}とは、もう許せないほどの{rel_name}の裂け目がある。"
        elif level < -40:
            return f"{other_name}とは、{rel_name}において対立している。"
        elif level < -15:
            return f"{other_name}とは、あまり{rel_name}が良くない。"
        else:
            return ""

    def set_character_speech_pattern(
        self, character_id: str, patterns: dict[str, Any]
    ) -> None:
        """キャラクター特有の話し方パターンを設定"""
        self.character_speech_patterns[character_id] = patterns

    def serialize(self) -> dict[str, Any]:
        """対話データをシリアライズ"""
        return {
            "dialogue_history": {
                f"{s}_{l}": [
                    {
                        "speaker_id": d.speaker_id,
                        "listener_id": d.listener_id,
                        "context": d.context.value,
                        "mood": d.mood.value,
                        "text": d.text,
                        "relationship_type": d.relationship_type.value,
                        "relationship_level": d.relationship_level,
                        "emotional_tone": d.emotional_tone,
                        "timestamp": d.timestamp,
                        "follow_up_options": d.follow_up_options,
                    }
                    for d in dialogues
                ]
                for (s, l), dialogues in self.dialogue_history.items()
            },
            "speech_patterns": self.character_speech_patterns,
        }

    def deserialize(self, data: dict[str, Any]) -> None:
        """対話データをデシリアライズ"""
        self.dialogue_history.clear()

        for key, dialogues_data in data.get("dialogue_history", {}).items():
            s, l = key.split("_", 1)
            dialogues = []
            for d_data in dialogues_data:
                dialogue = GeneratedDialogue(
                    speaker_id=d_data["speaker_id"],
                    listener_id=d_data["listener_id"],
                    context=DialogueContext(d_data["context"]),
                    mood=DialogueMood(d_data["mood"]),
                    text=d_data["text"],
                    relationship_type=RelationshipType(d_data["relationship_type"]),
                    relationship_level=d_data["relationship_level"],
                    emotional_tone=d_data["emotional_tone"],
                    timestamp=d_data.get("timestamp", time.time()),
                    follow_up_options=d_data.get("follow_up_options", []),
                )
                dialogues.append(dialogue)
            self.dialogue_history[(s, l)] = dialogues

        self.character_speech_patterns = data.get("speech_patterns", {})
