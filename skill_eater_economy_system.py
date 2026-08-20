"""
skill_eater_economy_system.py
Aの世界（スキル喰い） Phase 5: 派閥影響力＆経済システム＆拠点買収
提案5: 経済・闇市場・買収・建築のEmote & Audio演出 (Steps 33〜40)
"""

from dataclasses import dataclass

from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_presentation_system import SkillEaterPresentationSystem
from skill_eater_system import CharacterState, SkillEaterRegistry


@dataclass
class FactionState:
    id: str
    name: str
    reputation: int = 0  # -100 to 100
    influence_points: int = 1000
    is_hostile: bool = False


@dataclass
class BaseFacility:
    id: str
    name: str
    level: int = 1
    max_level: int = 5
    upgrade_cost_aldo: int = 1000
    required_secret_skill: str | None = None
    effect_description: str = ""


class SkillEaterEconomySystem:
    def __init__(
        self,
        registry: SkillEaterRegistry | None = None,
        audio: SkillEaterAudioSystem | None = None,
        presentation: SkillEaterPresentationSystem | None = None,
    ):
        self.registry = registry or SkillEaterRegistry.get_instance()
        self.audio = audio or SkillEaterAudioSystem.get_instance()
        self.presentation = presentation or SkillEaterPresentationSystem.get_instance()
        if audio and not presentation:
            self.presentation.audio_system = audio
        self.aldo_currency: int = 0
        self.heat_level: int = 0
        self.factions: dict[str, FactionState] = {
            "midas": FactionState(
                id="midas",
                name="ミダス・ホールディングス",
                reputation=-50,
                is_hostile=True,
            ),
            "resistance": FactionState(
                id="resistance", name="スキル開放戦線", reputation=30, is_hostile=False
            ),
            "bank": FactionState(
                id="bank", name="世界スキル銀行", reputation=0, is_hostile=False
            ),
            "broker": FactionState(
                id="broker", name="闇市場ブローカー", reputation=10, is_hostile=False
            ),
        }
        self.base_facilities: dict[str, BaseFacility] = {
            "rehab_lab": BaseFacility(
                id="rehab_lab",
                name="従属者再教育ラボ",
                level=1,
                upgrade_cost_aldo=2000,
                required_secret_skill="rar_utility_005",
                effect_description="従属者の最大スキル移植枠数を拡張する",
            ),
            "synthesis_furnace": BaseFacility(
                id="synthesis_furnace",
                name="魔導合成炉",
                level=1,
                upgrade_cost_aldo=5000,
                effect_description="プロシージャル合成時の上位Tierボーナス確率UP",
            ),
            "hq_vault": BaseFacility(
                id="hq_vault",
                name="レジスタンス金庫室",
                level=1,
                upgrade_cost_aldo=3000,
                effect_description="ターン経過ごとの定期アルド収入を増加",
            ),
        }

    def get_player_skill_net_worth(self, player: CharacterState) -> int:
        total = 0
        for s_id in player.get_skill_ids():
            s_def = self.registry.get_skill(s_id)
            if s_def and s_def.market_value > 0:
                total += s_def.market_value
        return total

    def evaluate_social_tier(self, player: CharacterState) -> str:
        net_worth = self.get_player_skill_net_worth(player)
        if net_worth == 0:
            return "奴隷（ノースキル）"
        elif net_worth < 10000:
            return "庶民（コモン級）"
        elif net_worth < 100000:
            return "中流階級（シルバー）"
        elif net_worth < 500000:
            return "新興富裕層（ゴールド）"
        else:
            return "支配階級（プラチナ／スキルイーター）"

    def sell_skill_to_black_market(
        self, player: CharacterState, skill_id: str
    ) -> tuple[bool, int, str]:
        """Step 33, 34: 闇市場売却時のEmote & Audio演出 (emote_cash + handleCoins / doorClose_1)"""
        if not player.has_skill(skill_id):
            return False, 0, "指定スキルを所持していません。"

        skill_def = self.registry.get_skill(skill_id)
        if not skill_def or skill_def.market_value <= 0:
            return False, 0, "このスキルは取引不可能な資産です。"

        value = skill_def.market_value
        player.remove_skill(skill_id)
        self.aldo_currency += value

        self.factions["broker"].reputation = min(
            100, self.factions["broker"].reputation + 2
        )

        # Step 33: アルド獲得エモート
        self.presentation.add_event(
            emote_file="emote_cash.png",
            audio_file="handleCoins.ogg",
            message=f"{value} アルドを獲得！",
        )

        if skill_def.is_illegal:
            self.heat_level += 10
            # Step 34: 密売扉音
            self.presentation.add_event(
                emote_file="emote_cash.png",
                audio_file="doorClose_1.ogg",
                message=f"闇取引完了（警戒度: {self.heat_level}）",
            )
            return (
                True,
                value,
                f"《{skill_def.name}》（違法合成品）を闇市場に密売し、{value} アルドを獲得！（警戒度: {self.heat_level}）",
            )

        return (
            True,
            value,
            f"《{skill_def.name}》を闇市場に売却し、{value} アルドを獲得しました！",
        )

    def sell_skill_to_normal_market(
        self, player: CharacterState, skill_id: str
    ) -> tuple[bool, int, str]:
        """Step 33, 35: 正規市場売却時のEmote & Audio演出 (emote_cash / emote_cross)"""
        if not player.has_skill(skill_id):
            return False, 0, "指定スキルを所持していません。"

        skill_def = self.registry.get_skill(skill_id)
        if not skill_def or skill_def.market_value <= 0:
            return False, 0, "このスキルは取引不可能な資産です。"

        if skill_def.is_illegal:
            # Step 35: 査定拒絶エモート
            self.presentation.add_event(
                emote_file="emote_cross.png",
                audio_file="metalClick.ogg",
                message="公認市場での取引拒絶（違法品）",
            )
            return (
                False,
                0,
                f"査定拒絶：『{skill_def.name}』は認可外の違法合成スキルです。公認市場では取り扱えません。",
            )

        value = skill_def.market_value
        player.remove_skill(skill_id)
        self.aldo_currency += value

        # Step 33: 正規取引
        self.presentation.add_event(
            emote_file="emote_cash.png",
            audio_file="handleCoins2.ogg",
            message=f"公認売却：{value} アルド獲得",
        )

        return (
            True,
            value,
            f"《{skill_def.name}》を正規市場に売却し、{value} アルドを獲得しました。",
        )

    def check_inspector_raid(self) -> tuple[bool, CharacterState | None, str]:
        """Step 38: 監査官急襲アラート (emote_alert + metalLatch 連続)"""
        if self.heat_level >= 100:
            self.heat_level = 0
            self.presentation.add_event(
                emote_file="emote_alert.png",
                audio_file="metalLatch.ogg",
                message="【緊急警報！】ミダス特別監査局長がアジトを急襲！",
            )
            inspector = CharacterState(
                id="inspector_special",
                name="ミダス特別監査局長",
                hp=300,
                max_hp=300,
                mp=100,
                max_mp=100,
                atk=45,
                defense=35,
                intelligence=30,
                speed=25,
            )
            inspector.add_skill("rar_combat_012")
            inspector.add_skill("rar_utility_005")
            msg = "【緊急警報！】闇市場への違法スキル密売が発覚！ ミダス特別監査局長がアジトを急襲してきました！"
            return True, inspector, msg
        return False, None, f"警戒度: {self.heat_level}/100"

    def takeover_branch(self, branch_name: str, seized_aldo: int) -> str:
        """Step 37: 支店買収テイクオーバー (emote_exclamations + doorOpen_2 + handleCoins)"""
        self.aldo_currency += seized_aldo
        self.factions["midas"].influence_points = max(
            0, self.factions["midas"].influence_points - 300
        )
        self.factions["resistance"].influence_points += 300
        self.factions["resistance"].reputation = min(
            100, self.factions["resistance"].reputation + 20
        )

        self.presentation.add_event(
            emote_file="emote_exclamations.png",
            audio_file="doorOpen_2.ogg",
            message=f"{branch_name} を制圧！ {seized_aldo} アルドを押収！",
        )
        self.audio.play_sound("handleCoins.ogg")

        return f"【支店買収完了】{branch_name} を制圧！ {seized_aldo} アルドを押収し、戦線の勢力が拡大しました！"

    def upgrade_facility(
        self, player: CharacterState, facility_id: str
    ) -> tuple[bool, str]:
        """Step 36: 施設強化建築 (emote_stars + chop + metalPot1)"""
        facility = self.base_facilities.get(facility_id)
        if not facility:
            return False, "存在しない施設です。"

        if facility.level >= facility.max_level:
            return False, "既に最大レベルに達しています。"

        if self.aldo_currency < facility.upgrade_cost_aldo:
            self.presentation.add_event(
                emote_file="emote_cross.png",
                audio_file="metalClick.ogg",
                message="資金不足",
            )
            return (
                False,
                f"アルドが不足しています。（必要: {facility.upgrade_cost_aldo} アルド, 所持: {self.aldo_currency} アルド）",
            )

        if facility.required_secret_skill and not player.has_skill(
            facility.required_secret_skill
        ):
            sec_def = self.registry.get_skill(facility.required_secret_skill)
            sec_name = sec_def.name if sec_def else facility.required_secret_skill
            self.presentation.add_event(
                emote_file="emote_cross.png",
                audio_file="metalClick.ogg",
                message="必要スキル不足",
            )
            return False, f"強化には企業秘密スキル《{sec_name}》の所持が必要です。"

        self.aldo_currency -= facility.upgrade_cost_aldo
        facility.level += 1
        facility.upgrade_cost_aldo = int(facility.upgrade_cost_aldo * 1.5)

        self.presentation.add_event(
            emote_file="emote_stars.png",
            audio_file="chop.ogg",
            message=f"【施設強化】{facility.name} が Lv.{facility.level} に昇格！",
        )
        self.audio.play_sound("metalPot1.ogg")

        return (
            True,
            f"【施設強化完了】{facility.name} が Lv.{facility.level} に昇格しました！",
        )
