"""Replace Tailwind utility classes with token-based aliases (Step 5).

Reads `class_mapping.json` and rewrites `class="..."` attributes in all
`demos/*.html` files, swapping known Tailwind utility names for the
design-token alias classes defined in `assets/css/demo.css`.

Run: python tools/replace_classes.py
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main() -> int:
    with open(os.path.join(ROOT, "class_mapping.json"), encoding="utf-8") as f:
        mapping = json.load(f)

    demo_dir = os.path.join(ROOT, "demos")
    changed_files = 0
    total_replaced = 0

    for fn in os.listdir(demo_dir):
        if not fn.endswith(".html"):
            continue
        path = os.path.join(demo_dir, fn)
        with open(path, encoding="utf-8") as f:
            html = f.read()

        def repl(m):
            classes = m.group(1).split()
            new_classes = [mapping.get(c, c) for c in classes]
            return f'class="{" ".join(new_classes)}"'

        new_html, n = re.subn(r'class="([^"]+)"', repl, html)
        if n:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_html)
            changed_files += 1
            total_replaced += n
            print(f"Updated {fn} ({n} class attrs)")

    print(
        f"Done. {changed_files} files changed, {total_replaced} class attributes rewritten."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
