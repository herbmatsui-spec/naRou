"""Generate color-blind safe design token variants (Step 14 of Proposal 5).

For each color-vision deficiency type (protan, deutan, tritan) defined under
accessibility.colorBlind in design_tokens.json, produce a modified token file
where the affected semantic colors are replaced with simulation-friendly values.

Run: python tools/generate_colorblind_palettes.py
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

TYPES = ["protan", "deutan", "tritan"]


def main() -> int:
    with open(os.path.join(ROOT, "design_tokens.json"), encoding="utf-8") as f:
        tokens = json.load(f)

    cb = tokens.get("accessibility", {}).get("colorBlind", {})
    if not cb:
        print("No accessibility.colorBlind section found in design_tokens.json")
        return 1

    for ctype in TYPES:
        if ctype not in cb:
            print(f"Skip missing type: {ctype}")
            continue
        overrides = cb[ctype]
        variant = copy.deepcopy(tokens)
        sem = variant["color"]["semantic"]
        for key, value in overrides.items():
            if key in sem:
                sem[key] = value
        out_name = f"design_tokens.{ctype}.json"
        out_path = os.path.join(ROOT, out_name)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(variant, f, indent=2, ensure_ascii=False)
        print(f"Wrote {out_name} ({len(overrides)} colors overridden)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
