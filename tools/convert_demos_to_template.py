"""Convert demo HTML files to use the shared Jinja2 base template and component CSS.

This script:
1. Scans the `demos/` directory for `*.html` files.
2. Extracts the original <title> if present.
3. Replaces the entire <head> section with `{% extends "templates/base.html" %}` and block tags.
4. Wraps the original <body> content inside `{% block content %}`.
5. Removes any Tailwind CDN <script> or <link> tags.
6. Saves the transformed file back in place (overwrites).

Run manually: `python tools/convert_demos_to_template.py`
"""

from __future__ import annotations

import os
import re


def convert_file(path):
    with open(path, encoding="utf-8") as f:
        html = f.read()
    # Extract title
    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
    title = title_match.group(1) if title_match else "naRou Demo"
    # Remove <head>...</head>
    html_no_head = re.sub(r"<head[\s\S]*?</head>", "", html, flags=re.IGNORECASE)
    # Remove Tailwind CDN links (both script and link tags containing 'tailwind')
    html_clean = re.sub(r"<.*?tailwind.*?>", "", html_no_head, flags=re.IGNORECASE)
    # Extract body content
    body_match = re.search(r"<body[\s\S]*?>([\s\S]*?)</body>", html, re.IGNORECASE)
    body_content = body_match.group(1).strip() if body_match else html_clean.strip()
    # Build new template content
    # Build new template content using explicit string concatenation to avoid f-string brace issues
    new_html = (
        '{% extends "templates/base.html" %}\n'
        "{% block title %}" + title + "{% endblock %}\n"
        "{% block content %}\n" + body_content + "\n"
        "{% endblock %}\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_html)
    print(f"Converted {os.path.basename(path)}")


if __name__ == "__main__":
    demo_dir = os.path.join(os.path.dirname(__file__), "..", "demos")
    for fname in os.listdir(demo_dir):
        if fname.lower().endswith(".html"):
            convert_file(os.path.join(demo_dir, fname))
