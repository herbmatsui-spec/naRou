import json

def tokens_to_css(tokens, prefix="--"):
    lines = [":root {"]
    def flatten(d, path=""):
        for k, v in d.items():
            new_path = f"{path}{k}"
            if isinstance(v, dict):
                flatten(v, f"{new_path}-")
            else:
                lines.append(f"  {prefix}{new_path}: {v};")
    flatten(tokens)
    lines.append("}")
    return "\n".join(lines)

if __name__ == "__main__":
    with open("design_tokens.json") as f:
        tokens = json.load(f)
    print(tokens_to_css(tokens))
