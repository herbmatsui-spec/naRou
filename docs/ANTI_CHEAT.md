# Anti-Cheat & Security — naRou: Masterpiece Edition (Proposal #1-C)

This document describes the tamper-resistant infrastructure protecting save files,
runtime integrity, and license compliance.

## 1. Save File HMAC Signing (Step 61)

**File:** `save_system.py`

- **Algorithm:** HMAC-SHA256 over the gzip-compressed pickle payload.
- **Key Management:** `SAVE_HMAC_KEY` environment variable (base64-encoded 32-byte key).
  Falls back to a deterministic dev key derived from project hash.
- **Format:** `[32 bytes SHA256] [32 bytes HMAC] [compressed payload]`
- **Verification:** HMAC verified first; then SHA256 checksum.
- **Tamper Response:** `SaveDataCorruptedError` raised; auto-recovers from latest
  backup generation (max 3 kept).

**Dev Notes:**
- Do not commit `SAVE_HMAC_KEY` to source control.
- Rotate keys by building with new env var; old saves become unloadable
  (intentional — prevents old tampered saves from loading).

## 2. Improved Tamper Detection (Step 62)

**File:** `save_system.py` / `integrity_checker.py`

- Legacy format (no HMAC) is rejected unless SHA256 passes (for migration).
- JSON saves also use SHA256 checksum; HMAC not yet applied to JSON format.
- On tamper detection: exception raised, backup rotation tried automatically.

## 3. Runtime Integrity Checker (Steps 63-65)

**File:** `integrity_checker.py`

| Feature | Method | Description |
|---------|--------|-------------|
| Anti-debug | `is_debugger_attached()` | Windows: `IsDebuggerPresent`; Linux: `/proc/self/status TracerPid`; macOS: `ptrace(PT_DENY_ATTACH)`; Generic: `sys.gettrace()` |
| Memory baseline | `snapshot_critical_values()` | Records gold, level, hp, mp, hunger, thirst, etc. |
| Memory check | `check_memory_integrity()` | Flags unexpected changes; allows small natural deltas |
| Anomaly detection | `detect_anomaly()` | Flags 3× expected damage, 100% crit over 50 attacks |
| Violation log | `_log_violation()` | Writes to `integrity_violations.log` + logger |

**Integration:** Call `get_integrity_checker(engine).periodic_check(engine)` every ~30s
from the main game loop.

## 4. Config Encryption (Step 66)

**File:** `config_manager.py`

- **Algorithm:** Fernet (AES-128-GCM) via `cryptography` library.
- **Key:** `CONFIG_ENCRYPTION_KEY` env (base64-encoded 32-byte key).
  Dev fallback: ephemeral key (does not persist).
- **API:**
  - `set_sensitive(key, value)` — stores encrypted under `config["secure"]`
  - `get_sensitive(key)` — returns decrypted string
- **Use Cases:** API keys, license tokens, server URLs.

## 5. License Checker (Steps 67-68)

**File:** `license_checker.py`

Two verification paths:

1. **Steam DRM** — Checks `SteamAppId` / `STEAM_USER` env; in production
   would call Steamworks `ISteamUser::GetAuthSessionTicket`.
2. **Custom Token** — HMAC-SHA256 signed token `payload.sig` where
   payload is base64url JSON `{app_id, issued, exp}` and sig is
   HMAC-SHA256(`LICENSE_SECRET`, payload).

**Caching:** Successful check cached for 7 days in `license_cache.json`
to allow offline play.

## 6. Anomaly Detection & Violation Logging (Steps 69-70)

**File:** `integrity_checker.py`

- **Combat anomalies:** Damage > 3× expected max; 100% crit rate over 50 attacks.
- **Log file:** `integrity_violations.log` (append-only, timestamped).
- **Response:** Cloud save disabled locally; local play still allowed;
  violation count tracked for server-side review.

## 7. Deployment Checklist

| Item | Required Env Var | Where Set |
|------|------------------|-----------|
| Save HMAC key | `SAVE_HMAC_KEY` | Build pipeline secret |
| Config encryption key | `CONFIG_ENCRYPTION_KEY` | Build pipeline secret |
| Steam App ID | `STEAM_APP_ID` | Steamworks dashboard |
| License secret (custom) | `LICENSE_SECRET` | Secure vault |
| License token (custom) | `LICENSE_TOKEN` | Per-user distribution |

## 8. Incident Response

1. **Save tamper detected** → Auto-restore from backup; increment violation count.
2. **Debugger attached** → Log violation; do not crash (avoids revealing detection).
3. **Memory anomaly** → Log violation; optional: disable cloud features.
4. **License invalid** → Offline play allowed for 7 days (cached); then require re-check.

## 9. Future Hardening

- Apply HMAC to JSON save format.
- Add kernel-level anti-debug (Windows: `NtGlobalFlag`, `BeingDebugged` PEB).
- Encrypt save payload with per-session key (AES-GCM).
- Server-side replay verification for leaderboards.
- Code signing + reproducible builds (already in CD pipeline).