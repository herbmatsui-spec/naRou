# Telemetry & Analytics — naRou: Masterpiece Edition (Proposal #1-B)

## Overview

`telemetry_manager.py` implements a **privacy-first, opt-in** analytics layer for
commercial operations. It powers data-driven balance decisions (proposal #8:
Seasonal Live Ops) without compromising player trust.

## Design principles

1. **Opt-in only** — `ConfigManager.telemetry_enabled` defaults to `False`. No
   data is collected until the player explicitly consents in the settings UI.
2. **Anonymous** — only a random UUID (`get_anonymous_id`) ties events together.
   No device IDs, IPs, or PII are stored.
3. **Offline-safe** — events are queued locally (`telemetry_cache/queue.json`)
   and flushed in batches; works without network access.
4. **GDPR-ready** — `delete_my_data()` erases the local identity and queue; a
   server-side deletion API can be layered on top.

## Capabilities

| Feature | Method |
|---------|--------|
| Anonymous ID | `get_anonymous_id()` |
| Session tracking | `start_session()` / `end_session()` |
| Event tracking | `track(event, props)` |
| Funnel events | `FUNNEL_EVENTS` (tutorial → boss → reincarnation …) |
| Crash reporting | `init_sentry()` / `send_crash()` / `install_exception_hook()` |
| Performance metrics | `track_performance(metrics)` |
| Balance telemetry | `track_balance(result)` |
| Batch flush | `flush()` |
| Dashboard export | `export_summary(path)` |
| A/B variants | `get_variant(experiment, variants)` |

## Privacy & compliance

See `privacy_policy.html` for the player-facing policy. The summary:

- Collected: anonymous ID, progression events, aggregate perf metrics, crash
  stack traces (no PII).
- Never collected: name, email, IP, save-file plaintext.
- Deletion: in-game toggle + `delete_my_data()` + support request.

## Wiring

```python
from config_manager import get_config_manager
from telemetry_manager import get_telemetry_manager

cfg = get_config_manager()
if cfg.get_telemetry_enabled():
    tm = get_telemetry_manager()
    tm.start_session()
    tm.track("boss_defeated", {"name": "goblin_king"})
```
