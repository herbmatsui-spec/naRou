# Implementation Plan – Fix Failing Tests (Step 1 ~ 12)

---

## Overview
The current test suite reports **397 / 429** passing tests. All syntax, lint, and type‑checking errors have been resolved. The remaining **32 failures** stem from logical inconsistencies across several subsystems (graphics, procedural quest generation, narrative DAG, scheduler, meta‑progression, web server, particle simulation, etc.).

The plan below breaks the remediation work into **12 concrete steps**, each with a clear scope, target modules, and expected test coverage improvements.

---

## Step 1 – Failure Inventory & Asset Validation (0.5 day)
- **Goal**: Produce a detailed list of failing tests with stack traces and verify that all test assets (YAML, PNG, JSON, etc.) exist and match expected formats.
- **Actions**:
  1. Run `pytest -vv` on the failing tests and redirect output to `tools_output/failure_report.txt`.
  2. Add a helper script `scripts/validate_test_assets.py` that checks the presence and basic validity (e.g., image dimensions, YAML syntax) of every asset referenced by the test suite.
- **Deliverable**: `tools_output/failure_report.txt` and the validation script.

---

## Step 2 – Graphics & Renderer Compatibility (2 days)
- **Modules**: `core/tiny_rogue_tiles.py`, `core/tile_atlas.py`, `core/lighting.py`, `core/renderer_base.py`, `core/tcod_renderer.py`.
- **Tasks**:
  - Align atlas image size expectations (`test_tiny_rogue_graphics`).
  - Ensure `TerminalLightingSystem` produces a `GBuffer` with identical shape/dtype to the TCOD renderer (`test_renderer_parity`).
  - Add `from .gbuffer import GBuffer` in `core/lighting.py`.
- **Verification**: Both graphics tests must pass.

---

## Step 3 – Procedural Quest Hooks (1 day)
- **Modules**: `procedural_quest_generator.py`, `procedural_quest_manager.py`.
- **Changes**:
  - Proper logging and fallback handling for all `except` blocks.
  - Refine `present_followup` duplicate‑chain detection.
  - Return a fully populated `QuestHookResult` (`success`, `message`, `reward`).
- **Test**: `test_procedural_quest_gameplay_hook.py`.

---

## Step 4 – Narrative DAG Evaluation (1 day)
- **Modules**: `quest_narrative_dag.py`, `narrative_executor.py`.
- **Fixes**:
  - Correct indentation of the `except` block (already done) and ensure it returns `False` without side effects.
  - Preserve context when evaluating conditions.
- **Test**: `test_phase4_narrative_dag.py`.

---

## Step 5 – Storyteller Generation (1 day)
- **Modules**: `dungeon_quest_feedback.py`, `procedural_dungeon_generator.py`.
- **Updates**:
  - Provide a proper fallback when the spec is missing.
  - Initialise `Storyteller` fields (`world_state`, `active_dag`).
- **Test**: `test_dungeon_world_storyteller_72_steps.py`.

---

## Step 6 – Headless & Text‑Mode Launch (0.5 day)
- **Modules**: `engine.py`, `cli.py`.
- **Fixes**:
  - Guard against missing terminal capabilities.
  - Ensure the text‑mode entry point does not raise exceptions.
- **Test**: `test_headless_launch.py`.

---

## Step 7 – Immersion (World News & Echoes) (0.5 day)
- **Modules**: `immersion_system.py`, `world_news.py`.
- **Tasks**:
  - Verify that `WorldNews` objects are correctly instantiated even when optional data is absent.
  - Add defensive checks around external API calls.
- **Test**: `test_immersion.py`.

---

## Step 8 – Meta‑Progression & Achievement (2 days)
- **Modules**: `meta_progression.py`, `achievement.py`.
- **Actions**:
  - Clamp all computed values to avoid overflow.
  - Propagate meta‑progression changes to the achievement system (unlock trophies).
- **Tests**: `test_meta_progression.py`, `test_achievement_trophy_72_steps.py`.

---

## Step 9 – Reincarnation & Save‑Load Integrity (2 days)
- **Modules**: `reincarnation.py`, `save_load.py`.
- **Changes**:
  - Ensure full serialization of `MetaProgression`, `Achievement`, and `SkillTree`.
  - Update checksum generation and backup rotation logic.
- **Tests**: `test_reincarnation_72_steps.py`, `test_stability.py` (all four sub‑tests).

---

## Step 10 – Pet Contract & Skill Fusion (1.5 days)
- **Modules**: `pet_contract.py`, `skill_fusion.py`.
- **Fixes**:
  - Correct fusion result merging into the target `Pet`.
  - Add duplicate‑skill detection in `SkillFusion.perform`.
- **Tests**: `test_pet_contract_evolution_fusion_72_steps.py`, `tests/unit/test_skill_fusion.py`.

---

## Step 11 – Scheduler & State Machine Hooks (2 days)
- **Modules**: `scheduler.py`, `engine.py`, `state_machine.py`.
- **Goals**:
  - Guarantee that `Scheduler.create_context` injects `engine.time` and `engine.world_state`.
  - Verify correct order of `on_exit`/`on_enter` hooks during `Engine.change_state`.
- **Tests**: `test_phase3_scheduler.py`, `test_state_machine.py`.

---

## Step 12 – Web Server & Canvas Serialization (1.5 days)
- **Modules**: `web_server.py`, `web_canvas.py`.
- **Tasks**:
  - Replace the hard‑coded `RuntimeError` on start‑up with graceful shutdown handling.
  - Serialize `Canvas` data via base64‑encoded NumPy arrays, ensuring JSON compatibility.
- **Tests**: `test_web_smoke.py`, `test_web_server_canvas_state_serialization`, `test_web_server_*`.

---

## Step 13 – Particle Simulation Stability (0.5 day)
- **Module**: `core/particles.py`.
- **Fix**: Initialise `self.perm` as `np.arange(256, dtype=np.uint32)` and mask indices with `& 0xFF` to avoid overflow warnings.
- **Test**: `test_particle_determinism.py`.

---

## Consolidated Timeline
| Day | Focus |
|-----|-------|
| 1   | Failure inventory, asset validation script |
| 2‑3 | Graphics & renderer compatibility |
| 4‑5 | Procedural quest hooks & Narrative DAG |
| 6‑7 | Storyteller, headless launch, immersion |
| 8‑9 | Meta‑progression & achievement |
|10‑11| Reincarnation & save‑load integrity |
|12‑13| Pet contract & skill fusion |
|14‑15| Scheduler & state‑machine hooks |
|16‑17| Web server & canvas serialization |
|18   | Particle simulation fix |
|19   | Full regression run (`pytest -q`) – **expect 429/429** |
|20   | Code cleanup, final Ruff/Mypy run, documentation update |

---

## Common Development Guidelines
1. **Minimal invasive changes** – keep API surface stable; modify only the surrounding logic of the failing path.
2. **Typing** – add or refine `typing` annotations for every modified function; ensure `mypy` passes with `--ignore-missing-imports`.
3. **Logging** – enable `core/logging.debug_enabled` during test runs to capture internal state for any future failures.
4. **Test‑driven workflow** – after each step, run the specific failing test(s) first, then the full suite to confirm no regressions.
5. **Documentation** – update `docs/architecture.md` and `CHANGELOG.md` with each major change.

---

## Deliverables
- `IMPLEMENTATION_PLAN.md` (this file) – stored at the repository root.
- Updated source files across the modules listed above.
- Helper scripts: `scripts/validate_test_assets.py`.
- Automated test‑run scripts: `run_failing.sh`, `run_full.sh`.
- Updated documentation (`docs/architecture.md`).

---

*Prepared for immediate execution. All steps are independent and can be run in parallel where possible, maximizing throughput while keeping the codebase stable.*
