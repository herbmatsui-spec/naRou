"""Stub for pydantic.alias_generators.to_camel"""

def to_camel(s: str) -> str:
    # Simple conversion: snake_case -> camelCase
    parts = s.split('_')
    if not parts:
        return s
    return parts[0] + ''.join(p.title() for p in parts[1:])
