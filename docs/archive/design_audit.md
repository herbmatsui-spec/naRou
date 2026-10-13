# Design Audit (Step 1 of Proposal 5)

Audit of styling used across `demos/*.html` after they were migrated to the
shared `templates/base.html`. The original Tailwind CDN was removed; the
utility class names below are now re-implemented in `assets/css/demo.css`
using design-token variables (no Tailwind dependency).

## Custom (demo-specific) classes
| Class | Purpose |
|-------|---------|
| `.stage-box` | Outer scene container |
| `.grid-map` | Tile grid layout (CSS grid) |
| `.tile` | Base tile cell |
| `.tile-wall` / `.tile-floor` | Tile variants (background) |
| `.anim-pulse` | Pulsing animation for interactive tiles |
| `.controls` / `.control-group` / `.slider` | Demo control widgets |
| `.stat-row` / `.info` / `.gallery-container` | Misc layout helpers |

## Most common Tailwind-style utility classes (count)
```
1200 tile          623 tile-wall       302 tile-floor     275 anim-pulse
 81 text-xs         80 flex             79 items-center    52 justify-between
 30 font-bold       28 text-slate-400   27 gap-3           27 text-sky-300
 26 border-b        26 text-3xl        26 bg-sky-500/20   26 px-3
 26 py-1            26 rounded-full    26 border          26 border-slate-800
 26 text-sm         26 text-yellow-300 26 font-medium     26 text-slate-500
 25 stage-box       25 border-slate-700 25 pb-3           25 text-xl
 25 text-sky-400    25 font-semibold   25 bg-slate-900    25 rounded-lg
 25 p-3             24 grid-map
```

## Color tokens used (mapped to design_tokens)
- `slate-*`  → neutral grays (`--color-text-secondary`, `--color-border-*`)
- `sky-*`    → accent / info (`--color-semantic-info`)
- `yellow-*` → gold (`--color-semantic-gold`)
- `amber-*` / `orange-*` → warning (`--color-semantic-warning`)

## Conclusion
All 78 distinct classes are covered by `assets/css/demo.css` (custom classes)
plus the utility subset. No Tailwind CDN or build step is required.
