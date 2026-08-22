import os
import re


def add_future_annotations(file_path: str) -> bool:
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    # Skip if already has import
    if any("from __future__ import annotations" in line for line in lines):
        return False
    # Find insertion point: after shebang and any existing __future__ imports, after docstring if present
    insert_idx = 0
    # Shebang
    if lines and lines[0].startswith("#!"):
        insert_idx = 1
    # Skip module docstring if present
    if insert_idx < len(lines) and (
        lines[insert_idx].strip().startswith('"""') or lines[insert_idx].strip().startswith("'''")
    ):
        # Find closing triple quotes
        delim = lines[insert_idx].strip()[:3]
        for i in range(insert_idx + 1, len(lines)):
            if delim in lines[i]:
                insert_idx = i + 1
                break
    # Insert import
    lines.insert(insert_idx, "from __future__ import annotations\n")
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return True


def replace_blind_exception(file_path: str) -> bool:
    # Replace patterns like "except Exception as e:" with "except Exception as e:"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    original = content
    # Simple substitution preserving existing body
    content = re.sub(r"except\s+Exception\s*:", r"except Exception as e:", content)
    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


def process_file(file_path: str):
    changed = False
    changed |= add_future_annotations(file_path)
    changed |= replace_blind_exception(file_path)
    return changed


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    for dirpath, dirnames, filenames in os.walk(root):
        # skip hidden dirs and virtual envs
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "__pycache__"]
        for fn in filenames:
            if fn.endswith(".py"):
                fp = os.path.join(dirpath, fn)
                try:
                    process_file(fp)
                except Exception as e:
                    print(f"Error processing {fp}: {e}")


if __name__ == "__main__":
    main()
