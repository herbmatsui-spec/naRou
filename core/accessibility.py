"""accessibility.py - アクセシビリティ支援（色覚多様性・フォント等）。

Step 26-29 で構築。design_tokens.<variant>.json を読み込み、有効なトークンを返す。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, cast

# 対応する色覚バリアント -> トークンファイル名
_TOKEN_FILES = {
    "none": "design_tokens.json",
    "deutan": "design_tokens.deutan.json",
    "protan": "design_tokens.protan.json",
    "tritan": "design_tokens.tritan.json",
    "high_contrast": "design_tokens.high_contrast.json",
}

_VALID_VARIANTS = set(_TOKEN_FILES.keys())


def _resolve_variant(requested: str | None) -> str:
    """Step 28: 環境変数 COLOR_VISION を優先し、不正値は none に戻す。"""
    variant = requested
    env = os.environ.get("COLOR_VISION")
    if env:
        variant = env
    if variant not in _VALID_VARIANTS:
        variant = "none"
    return variant


# Step 26: バリアントに対応する design_tokens を読み込む
def load_design_tokens(variant: str = "none") -> dict[str, Any]:
    """design_tokens.<variant>.json を読み込んで dict を返す。"""
    variant = _resolve_variant(variant)
    filename = _TOKEN_FILES.get(variant, "design_tokens.json")
    path = Path(filename)
    if not path.exists():
        path = Path("design_tokens.json")
    with open(path, encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


# Step 27: 現在有効なトークンを config から決定して返す
def get_active_tokens() -> dict[str, Any]:
    """config の accessibility.color_vision を見てトークンを返す。"""
    from config import get_config

    variant = get_config("accessibility.color_vision") or "none"
    return load_design_tokens(variant)


# Step 29: プラットフォーム非依存のスタブ検出（後で拡張用）
def detect_os_a11y() -> str:
    """OS のアクセシビリティ設定を判定するスタブ。常に 'none' を返す。"""
    return "none"
