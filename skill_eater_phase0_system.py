"""Phase 0 System for Skill Eater World (Aの世界).

Handles the Phase 0 (Landing/Recognition) flow, implementing the 72-step design.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Any, Dict, Optional

from meta_awareness_system import MetaAwarenessSystem


class Phase0State(Enum):
    """States within Phase 0."""

    INIT = auto()
    VR_TRAINING = auto()
    APTITUDE_TEST = auto()
    FIRING = auto()
    HACKING = auto()
    ESCAPE = auto()
    BOSS = auto()
    COMPLETED = auto()


def load_past_world_inheritance(save_data: Optional[Dict[str, Any]] = None) -> list[str]:
    """Extracts inherited skills/artifacts from past cleared worlds."""
    if not save_data:
        return ["ISEKAI_PHARMACY_RECIPE_V1", "DUNGEON_HEART_SEED"]
    meta = save_data.get("meta_progress", {})
    return meta.get("inherited_skills", ["ISEKAI_PHARMACY_RECIPE_V1"])


class AptitudeScannerUI:
    """Scanner UI component for aptitude test with scanning animation and glitch support."""

    def __init__(self) -> None:
        self.is_scanning: bool = False
        self.glitch_active: bool = False
        self.detected_text: str = ""

    def start_scan(self) -> Dict[str, Any]:
        self.is_scanning = True
        return {"action": "SCAN_START", "progress": 0, "status": "SCANNING_BODY_WAVE"}

    def trigger_glitch(self, glitch_text: str) -> Dict[str, Any]:
        self.glitch_active = True
        self.detected_text = glitch_text
        return {"action": "GLITCH_DETECTED", "text": glitch_text, "color": "CYAN_MAGENTA_SHIFT"}

    def render_glitch_easter_egg(self, inherited_keys: list[str]) -> list[Dict[str, Any]]:
        """Generates visual glitch frames displaying corrupted past world memories."""
        glitch_frames = []
        for key in inherited_keys:
            glitch_frames.append(
                {
                    "type": "CORRUPTED_SIGNAL",
                    "raw_code": f"UNKNOWN_ARTIFACT_HEX_0x{hash(key) & 0xFFFF:04X}",
                    "glitched_label": f"ERR: {key[:8]}...[OUT_OF_BOUNDS]",
                    "duration_ms": 250,
                }
            )
        return glitch_frames


class FutureWarningUI:
    """UI panel presenting worst-case flash forward with dark red warning overlay."""

    def __init__(self) -> None:
        self.visible: bool = False
        self.theme: str = "DARK_RED_GLITCH"

    def render(self, timeline: Dict[str, Any]) -> Dict[str, Any]:
        self.visible = True
        return {
            "ui_name": "FUTURE_WARNING_PANEL",
            "theme": self.theme,
            "title": "⚠️ 《原典閲覧》警告：因果予測（破滅ルート）",
            "events": timeline.get("forecast_events", []),
            "prompt": "【推奨選択】解雇通知を受諾し、社外へ脱出せよ。",
        }


class SkillScannerUI:
    """Skill Eater dedicated holographic scanner UI showing code, weaknesses, and targets."""

    def __init__(self) -> None:
        self.active_targets: list[Dict[str, Any]] = []
        self.hud_style: str = "CYBERPUNK_SCANNER"

    def render(self) -> Dict[str, Any]:
        return {
            "ui_name": "SKILL_SCANNER_HUD",
            "style": self.hud_style,
            "target_matrix_visible": True,
            "targets": self.active_targets,
        }

    def generate_glitch_transition(self, duration_ms: int = 2000) -> list[Dict[str, Any]]:
        """Generates frame sequence for transitioning from classic UI to Scanner UI."""
        return [
            {"step": 1, "noise_intensity": 0.3, "color_split": "RGB", "duration_ms": 500},
            {"step": 2, "noise_intensity": 0.8, "matrix_code_overlay": True, "duration_ms": 1000},
            {"step": 3, "noise_intensity": 0.1, "hud_reveal": True, "duration_ms": 500},
        ]

    def get_objective_overlay(self) -> Dict[str, str]:
        """Returns cyberpunk themed mission objectives."""
        return {
            "target": "TARGET: Midas Trading Co. Headquarters",
            "primary_objective": "MISSION: Escape to Slum Underground",
            "warning": "SECURITY STATUS: High Alert",
        }


class FakeStatusUI:
    """Mock/Classic RPG style fake status UI for VR orientation."""

    def __init__(self, hp: int = 100, mp: int = 20, job: str = "見習い社員") -> None:
        self.hp = hp
        self.mp = mp
        self.job = job

    def render(self) -> Dict[str, Any]:
        return {
            "ui_type": "CLASSIC_RPG",
            "hp": self.hp,
            "mp": self.mp,
            "job": self.job,
            "style": "pixel_frame_retro",
        }


class HologramEnemy:
    """Hologram enemy for VR training simulation."""

    def __init__(self, name: str = "ホログラム・ゴブリン", hp: int = 30, atk: int = 5) -> None:
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.atk = atk
        self.is_hologram = True


class UIMode(Enum):
    CLASSIC_RPG = auto()
    SKILL_SCANNER = auto()


class OfficeTerminal:
    """Interactable office terminal object with hacking interfaces."""

    def __init__(self) -> None:
        self.terminal_id: str = "MIDAS_HR_TERMINAL_04"
        self.is_hacked: bool = False
        self.security_level: int = 1

    def interact(self) -> Dict[str, Any]:
        return {
            "terminal_id": self.terminal_id,
            "status": "AWAITING_INPUT",
            "prompt": "【社内端末アクセス】機密データの横領を実行しますか？",
        }


class HackingMinigameUI:
    """Simple rhythm/timing based security bypass hacking puzzle UI."""

    def __init__(self) -> None:
        self.target_code: str = "7734"
        self.user_input: str = ""

    def render(self) -> Dict[str, Any]:
        return {
            "ui_name": "HACKING_TERMINAL_PUZZLE",
            "instruction": "セキュリティ暗号を突破せよ：指定コードと同期",
            "target_pattern": self.target_code,
            "style": "GREEN_MONOCHROME_CRT",
        }


HACKING_REWARD_TABLE: Dict[str, Dict[str, Any]] = {
    "LEVEL_1_EASY": {
        "reward_id": "STOLEN_CREDITS_SMALL",
        "name": "裏帳簿の端数資金 (500G)",
        "gold": 500,
    },
    "LEVEL_2_MEDIUM": {
        "reward_id": "SLUM_SECTOR_MAP",
        "name": "スラム街地下構造マップ",
        "item": "MAP_SLUM_UNDERGROUND",
    },
    "LEVEL_3_HARD": {
        "reward_id": "SKILL_DISCARD_KEY",
        "name": "コモンスキル《鍵開け・初級》",
        "skill": "LOCKPICK_LV1",
    },
}


class EscapeMap:
    """Stealth escape map model representing office corridors leading to the exit."""

    def __init__(self) -> None:
        self.grid_width: int = 10
        self.grid_height: int = 5
        self.player_pos: tuple[int, int] = (0, 2)
        self.exit_pos: tuple[int, int] = (9, 2)
        self.husks: list[Dict[str, Any]] = [
            {
                "pos": (1, 1),
                "label": "スキルを抜かれ虚ろな目で座り込む元社員",
                "status": "DRAINED_HUSK",
            },
            {
                "pos": (7, 3),
                "label": "『オレの…鑑定スキルを返せ…』と呻く男",
                "status": "DRAINED_HUSK",
            },
        ]
        self.guards: list[Dict[str, Any]] = [
            {"id": "G1", "pos": (3, 2), "patrol": [(3, 1), (3, 2), (3, 3)], "vision_range": 1},
            {"id": "G2", "pos": (6, 2), "patrol": [(6, 3), (6, 2), (6, 1)], "vision_range": 1},
        ]
        self.cameras: list[Dict[str, Any]] = [
            {"id": "CAM1", "pos": (5, 0), "coverage": [(5, 0), (5, 1), (5, 2)], "active": True}
        ]

    def reveal_stealth_overlays(self, analysis_active: bool = True) -> Dict[str, Any]:
        """Provides highlighted danger zones (red cones) and safe routes via Analysis skill."""
        if not analysis_active:
            return {"danger_zones": [], "safe_path_hint": None}
        danger_cells = set()
        for g in self.guards:
            danger_cells.add(g["pos"])
        for c in self.cameras:
            if c["active"]:
                danger_cells.update(c["coverage"])
        return {
            "danger_zones": list(danger_cells),
            "safe_path_hint": [
                (0, 2),
                (1, 2),
                (2, 2),
                (2, 0),
                (3, 0),
                (4, 0),
                (7, 0),
                (7, 2),
                (8, 2),
                (9, 2),
            ],
        }

    def step_player(
        self, next_pos: tuple[int, int], analysis_active: bool = True
    ) -> Dict[str, Any]:
        """Moves player and checks if detected by security."""
        self.player_pos = next_pos
        overlays = self.reveal_stealth_overlays(analysis_active)
        is_detected = next_pos in overlays["danger_zones"]
        is_escaped = next_pos == self.exit_pos
        return {
            "player_pos": self.player_pos,
            "detected": is_detected,
            "escaped": is_escaped,
        }

    def handle_detection_penalty(self) -> Dict[str, Any]:
        """Resets player to checkpoint and inflicts HP penalty on detection."""
        self.player_pos = (0, 2)
        return {
            "action": "RESET_CHECKPOINT",
            "hp_penalty": 15,
            "message": "警備員に見つかり追放された！ダメージを受け、スタート地点へ引き戻された。",
        }

    def get_skill_market_ticker(self) -> list[str]:
        """Provides simulated environmental LED stock ticker lines for skill market prices."""
        return [
            "【スキル市場速報】《剛力Lv5》▲12.4% 高騰 | 《上級火魔法》▼3.1% 反落",
            "【ミダス商会公示】低適性者のスキル強制買い取り価格改定（一律50G）",
            "【資本速報】世界スキル銀行：新規マスタースキル債券を発行",
        ]


class MiddleManagerBoss:
    """Tutorial boss: Midas Trading Co. Middle Manager with overpowered Rare Skill."""

    def __init__(self) -> None:
        self.name: str = "ミダス商会 査定課長ゴルドー"
        self.hp: int = 5000
        self.max_hp: int = 5000
        self.atk: int = 250
        self.skill_name: str = "レアスキル《黄金重力圧（ゴールド・プレス）》"
        self.charge_turns_required: int = 2
        self.current_charge: int = 0
        self.weakness_revealed: bool = False


class Phase0Manager:
    """Manages the lifecycle and state transitions of Phase 0."""

    def __init__(self) -> None:
        self.is_initialized: bool = True
        self.current_state: Phase0State = Phase0State.INIT
        self.ui_mode: UIMode = UIMode.CLASSIC_RPG
        self.fake_ui = FakeStatusUI()
        self.scanner_ui = AptitudeScannerUI()
        self.warning_ui = FutureWarningUI()
        self.scanner_hud = SkillScannerUI()
        self.escape_map = EscapeMap()
        self.terminal = OfficeTerminal()
        self.hacking_ui = HackingMinigameUI()
        self.vr_enemy: Optional[HologramEnemy] = None
        self.boss_enemy: Optional[MiddleManagerBoss] = None
        self.inefficient_action_count: int = 0
        self.meta_score: int = 0
        self.future_avoided: bool = False
        self.countdown_seconds: int = 30
        self.is_timer_running: bool = False
        self.player_inventory: list[str] = []

    def award_meta_choice(self, reason: str, points: int = 100) -> Dict[str, Any]:
        """Awards meta-awareness hidden score points for choosing optimal meta routes."""
        self.meta_score += points
        return {
            "action": "AWARD_META_SCORE",
            "points": points,
            "total_score": self.meta_score,
            "reason": reason,
        }

    def start_vr_training(self) -> None:
        self.current_state = Phase0State.VR_TRAINING
        self.vr_enemy = HologramEnemy()
        self.inefficient_action_count = 0

    def record_vr_action(self, action_type: str) -> bool:
        """Records a VR action. Returns True if considered inefficient/deliberate failure."""
        is_inefficient = action_type in ("MISS_ATTACK", "WASTE_MP", "IDLE_STARE", "HIT_SELF")
        if is_inefficient:
            self.inefficient_action_count += 1
        return is_inefficient

    def check_vr_termination(self, threshold: int = 3) -> Dict[str, Any]:
        """Checks if VR training should force-terminate due to inefficiency rating."""
        if self.inefficient_action_count >= threshold:
            return {
                "terminated": True,
                "reason": "適性スコア極低（Eランク以下）：新人研修即時打ち切り",
                "evaluation": "INCOMPETENT",
            }
        return {"terminated": False, "reason": "", "evaluation": "PENDING"}

    def complete_vr_training(self) -> Dict[str, Any]:
        """Transitions from VR Training to Aptitude Test phase."""
        eval_result = self.check_vr_termination()
        self.current_state = Phase0State.APTITUDE_TEST
        return {
            "success": True,
            "next_state": self.current_state.name,
            "evaluation": eval_result.get("evaluation", "INCOMPETENT"),
            "message": "VR研修終了。続いて能力適性検査室へ移動します。",
        }

    def evaluate_aptitude_choice(self, chosen_option_id: str) -> Dict[str, Any]:
        """Validates choice in aptitude test. Only Analysis choice allows progression."""
        if chosen_option_id != "opt_analysis":
            return {
                "accepted": False,
                "error": "ERR_SYSTEM_OVERLOAD: 指定スキルの波形偽装に失敗。生体拒絶反応発生。",
                "meta_hint": "メタ知識の警告: 本来の力を表に出すと即座に隔離・解剖されます。《解析》のみを申告してください。",
            }
        return {
            "accepted": True,
            "skill_declared": "ANALYSIS",
            "evaluation": "WORTHLESS_SLAVE_CLASS",
        }

    def get_evaluator_dialogue(self, evaluation: str) -> str:
        """Retrieves harsh dialogue from company evaluator NPC based on test result."""
        if evaluation == "WORTHLESS_SLAVE_CLASS":
            return "『適性結果：《解析》のみ。戦闘適性ゼロ、生産適性ゼロ。……貴様、何のために我が社へ応募したのだ？即刻解雇（クビ）だ！』"
        return "『審査完了。次の部署へ配置する。』"

    def execute_firing_transition(self) -> Dict[str, Any]:
        """Transitions state from APTITUDE_TEST to FIRING."""
        self.current_state = Phase0State.FIRING
        self.award_meta_choice(
            "Successfully concealed power and triggered dismissal event", points=150
        )
        dialogue = self.get_evaluator_dialogue("WORTHLESS_SLAVE_CLASS")
        return {
            "success": True,
            "current_state": self.current_state.name,
            "dialogue": dialogue,
            "status": "DISMISSED",
        }

    def trigger_readers_privilege_prediction(self) -> Dict[str, Any]:
        """Triggers the Reader's Privilege auto-prediction upon dismissal."""
        meta_sys = MetaAwarenessSystem.get_instance()
        prediction = meta_sys.trigger_flash_forward("MIDAS_DISMISSAL")
        ui_render = self.warning_ui.render(prediction.get("timeline", {}))
        return {
            "prediction": prediction,
            "ui_render": ui_render,
            "status": "PREDICTION_DISPLAYED",
        }

    def sign_dismissal_paper(self, accept: bool = True) -> Dict[str, Any]:
        """Player interaction to sign the dismissal paper, avoiding future doom."""
        if not accept:
            return {
                "success": False,
                "message": "解雇拒否を選択：ミダス商会で強制労働となり破滅未来が確定します。",
                "game_over": True,
            }
        self.future_avoided = True
        self.warning_ui.visible = False
        self.award_meta_choice("Optimal meta action: accepted dismissal", points=200)
        return {
            "success": True,
            "future_flag": "AVOIDED",
            "message": "解雇通知に署名完了。破滅ルートを完全回避しました。",
            "audio_event": "se_fate_avoided_chime.ogg",
            "screen_shake": "STOP_CALM",
            "game_over": False,
        }

    def trigger_ui_hack_transition(self) -> Dict[str, Any]:
        """Switches UI mode from CLASSIC_RPG to SKILL_SCANNER with glitch animation."""
        self.ui_mode = UIMode.SKILL_SCANNER
        glitch_sequence = self.scanner_hud.generate_glitch_transition()
        return {
            "status": "UI_HACKED",
            "new_mode": self.ui_mode.name,
            "glitch_sequence": glitch_sequence,
        }

    def get_audio_crossfade_config(self) -> Dict[str, Any]:
        """Provides audio crossfade parameters from peaceful RPG theme to dark synth."""
        return {
            "action": "CROSSFADE_BGM",
            "fade_out_track": "bgm_peaceful_office.ogg",
            "fade_in_track": "bgm_cyber_synth_slum.ogg",
            "duration_ms": 2500,
        }

    def get_world_template_recognition_message(self) -> str:
        """System prompt message announcing successful recognition of World A template."""
        return (
            "【世界法則の解析完了】対象テンプレート：スキル資本主義／攻略指針：下剋上・スキル強奪"
        )

    def export_save_state(self) -> Dict[str, Any]:
        """Exports Phase 0 progression and UI hack state for persistence."""
        return {
            "current_state": self.current_state.name,
            "ui_mode": self.ui_mode.name,
            "meta_score": self.meta_score,
            "future_avoided": self.future_avoided,
            "phase0_cleared": self.current_state == Phase0State.COMPLETED,
        }

    def start_embezzlement_timer(self, duration: int = 30) -> Dict[str, Any]:
        """Starts countdown timer before security forces player out of the office."""
        self.current_state = Phase0State.HACKING
        self.countdown_seconds = duration
        self.is_timer_running = True
        return {"action": "TIMER_STARTED", "remaining_seconds": self.countdown_seconds}

    def submit_hacking_attempt(
        self, entered_code: str, difficulty: str = "LEVEL_1_EASY"
    ) -> Dict[str, Any]:
        """Processes hacking attempt and awards stolen assets on success."""
        reward_info = HACKING_REWARD_TABLE.get(difficulty, HACKING_REWARD_TABLE["LEVEL_1_EASY"])
        if entered_code == "7734":
            self.award_meta_choice(f"Embezzlement success: {reward_info['name']}", points=150)
            return {
                "success": True,
                "reward": reward_info,
                "message": f"ハッキング成功！【{reward_info['name']}】を横領しました。",
            }
        return {
            "success": False,
            "reward": None,
            "message": "アクセス拒否：警備システムに通報されました！",
        }

    def trigger_security_alert(self) -> Dict[str, Any]:
        """Triggers office security alarm when hacking fails or timer expires."""
        self.is_timer_running = False
        return {
            "alert_level": "RED_ALERT",
            "siren_audio": "se_alarm_siren_loop.ogg",
            "message": "警報発令：不法端末アクセスを検知。警備ドローンが出動します！",
        }

    def add_stolen_item_to_inventory(self, item_id: str) -> Dict[str, Any]:
        """Adds stolen item to inventory and generates HUD toast notification."""
        self.player_inventory.append(item_id)
        return {
            "action": "ITEM_ACQUIRED",
            "item_id": item_id,
            "inventory": self.player_inventory,
            "toast": f"獲得: {item_id}",
        }

    def complete_hacking_and_escape(self) -> Dict[str, Any]:
        """Transitions state from HACKING to ESCAPE as exit doors unlock."""
        self.is_timer_running = False
        self.current_state = Phase0State.ESCAPE
        return {
            "success": True,
            "next_state": self.current_state.name,
            "message": "オフィスの非常扉が開いた。警備をかいくぐり脱出せよ！",
        }

    def check_escape_clear(self, player_pos: tuple[int, int]) -> Dict[str, Any]:
        """Checks if player reached the exit door, completing stealth escape."""
        if player_pos == self.escape_map.exit_pos:
            self.current_state = Phase0State.BOSS
            self.award_meta_choice("Stealth puzzle escape clear", points=200)
            return {
                "escaped": True,
                "next_state": self.current_state.name,
                "message": "非常口の突破に成功！しかし、裏路地に待ち伏せの気配が……",
            }
        return {
            "escaped": False,
            "next_state": self.current_state.name,
            "message": "脱出経路を捜索中",
        }

    def trigger_boss_encounter(self) -> Dict[str, Any]:
        """Triggers encounter cutscene with Middle Manager at the back alley."""
        self.current_state = Phase0State.BOSS
        self.boss_enemy = MiddleManagerBoss()
        return {
            "action": "ENCOUNTER_START",
            "boss_name": self.boss_enemy.name,
            "dialogue": "『フハハ！クビのゴミ虫風情が、我が社から逃げ切れると思ったか！？ここで貴様の端数魔力も回収してやる！』",
            "bgm": "bgm_boss_middle_manager.ogg",
        }

    def process_boss_turn(self, player_hp: int) -> Dict[str, Any]:
        """Calculates boss action. If charging completes, unleashes lethal attack."""
        if not self.boss_enemy:
            return {"action": "NONE"}
        self.boss_enemy.current_charge += 1
        if self.boss_enemy.current_charge < self.boss_enemy.charge_turns_required:
            return {
                "action": "CHARGING",
                "message": f"『{self.boss_enemy.name}』は《黄金重力圧》の魔力を充填中……！",
                "damage": 0,
            }
        return {
            "action": "LETHAL_ATTACK",
            "message": f"『{self.boss_enemy.name}』の《黄金重力圧》が直撃！致命傷！",
            "damage": self.boss_enemy.atk,
        }

    def analyze_boss_weakness(self) -> Dict[str, Any]:
        """Uses Analysis to reveal boss charge delay and environmental escape trick."""
        if not self.boss_enemy:
            return {"success": False}
        self.boss_enemy.weakness_revealed = True
        self.award_meta_choice("Analyzed middle manager weakness", points=100)
        return {
            "success": True,
            "revealed_data": {
                "skill_type": "HEAVY_CHARGE_TYPE",
                "weakness": "充填時間中（残り1ターン）に路地の障害物を倒せば視界を遮り100%逃走可能",
            },
            "special_action_unlocked": "TRIGGER_ALLEY_OBSTACLE_ESCAPE",
        }

    def execute_environmental_escape(self) -> Dict[str, Any]:
        """Executes environmental escape trick during boss charging window."""
        if not self.boss_enemy or not self.boss_enemy.weakness_revealed:
            return {"success": False, "message": "脱出経路が分析されていません！"}
        self.award_meta_choice("Clever environmental escape from boss", points=250)
        return {
            "success": True,
            "action": "ESCAPE_TO_SLUM",
            "message": "路地のコンテナを崩してゴルドーの視界を遮断！スラム街の深部へと飛び込んだ！",
        }

    def get_boss_parting_dialogue(self) -> str:
        """Boss's enraged parting dialogue seeding hatred and revenge motivation for Phase 1."""
        return "『おのれ小賢しいネズミが……ッ！スラムに逃げ込んだとて無駄だ！貴様のスキルを根こそぎ奪い、豚箱にぶち込んでやるからなァッ！！』"

    def handle_boss_defeat_retry(self) -> Dict[str, Any]:
        """Handles death from boss by restoring player at post-dismissal checkpoint."""
        self.current_state = Phase0State.ESCAPE
        if self.boss_enemy:
            self.boss_enemy.current_charge = 0
        return {
            "action": "RETRY_FROM_CHECKPOINT",
            "checkpoint": "MIDAS_OFFICE_EXIT",
            "message": "《黄金重力圧》に圧倒された……！メタ記憶を巻き戻し、非常口前へリトライします。",
        }

    def transition_to_slum_alley(self) -> Dict[str, Any]:
        """Transitions map and environment to Phase 1 starting location (Slum Alley)."""
        self.current_state = Phase0State.COMPLETED
        return {
            "action": "MAP_LOAD",
            "room_id": "slum_alley",
            "room_name": "スラムの裏路地",
            "environment_description": "薄暗く湿った路地。遠くでサイレンが鳴り響く。",
        }

    def get_phase0_title_card(self) -> Dict[str, str]:
        """Provides title card display parameters upon arriving at the Slum."""
        return {
            "title": "Aの世界：『スキル喰いの異世界倒産』",
            "subtitle": "〜最弱《解析》だけでスキル資本主義をハックする〜",
            "act_name": "第１幕：逃亡と覚醒",
        }

    def calculate_phase0_bonus_exp(self) -> Dict[str, Any]:
        """Calculates bonus starting EXP and funds based on Phase 0 meta choices."""
        base_exp = 100
        bonus_exp = self.meta_score * 2
        total_exp = base_exp + bonus_exp
        return {
            "base_exp": base_exp,
            "bonus_exp": bonus_exp,
            "total_exp": total_exp,
            "meta_score": self.meta_score,
            "message": f"フェーズ0完了ボーナス：+{total_exp} EXP 獲得！",
        }

    def update_world_state_phase(
        self, world_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Updates main WorldState from Phase 0 (Recognition) to Phase 1 (Foundation)."""
        state = world_state or {}
        state["world_id"] = "skill_eater"
        state["template_id"] = "skill_capitalism"
        state["phase"] = "Phase 1: 基盤構築 (Lv1-20)"
        state["phase_index"] = 1
        return state

    def get_slum_ambient_audio_config(self) -> Dict[str, Any]:
        """Provides slum ambient environmental audio settings."""
        return {
            "action": "START_AMBIENT_LOOP",
            "ambient_tracks": [
                "amb_slum_rain.ogg",
                "amb_distant_siren.ogg",
                "amb_slum_chatter.ogg",
            ],
            "volume": 0.7,
        }

    def unlock_free_exploration(self) -> Dict[str, Any]:
        """Lifts all tutorial rails and locks, enabling free open exploration."""
        return {
            "tutorial_locked": False,
            "controls_enabled": ["MOVE", "DEVOUR", "SYNTHESIS", "INVENTORY", "MENU"],
            "message": "チュートリアル制限解除：スラム街の自由探索が可能になりました。",
        }

    def get_initial_phase1_journal_quest(self) -> Dict[str, Any]:
        """Registers the initial Phase 1 main quest into the player journal."""
        return {
            "quest_id": "QUEST_SE_01_REBEL_CONTACT",
            "title": "メインクエスト：スキル開放戦線との接触",
            "objective": "スラムの地下闇市場へ向かい、レジスタンスの連絡員を探せ。",
            "reward_exp": 300,
        }

    def complete_phase0_workflow(
        self, save_dict: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Finalizes Phase 0, updates save dictionary, and prepares Phase 1 state."""
        self.current_state = Phase0State.COMPLETED
        if save_dict is not None:
            save_dict["phase0_completed"] = True
            save_dict["phase0_meta_score"] = self.meta_score
            save_dict["current_phase"] = 1
            save = save_dict
        else:
            save = {
                "phase0_completed": True,
                "phase0_meta_score": self.meta_score,
                "current_phase": 1,
            }
        return {
            "success": True,
            "status": "PHASE0_PERMANENTLY_COMPLETED",
            "save_data": save,
        }
