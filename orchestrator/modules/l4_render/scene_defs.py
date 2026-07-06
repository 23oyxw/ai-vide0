"""Scene/storyboard definitions for video composition.
Each style has 4 scene variants — matches standard e-commerce storyboard structure:
  1. Hook (0-3s)  → grab attention
  2. Pain (3-7s)  → show problem
  3. Product (7-12s) → showcase solution
  4. CTA (12-15s) → call to action
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SceneDef:
    """Definition for one video scene."""
    index: int
    label: str  # "钩子", "痛点", "特写", "CTA"
    duration_sec: float
    image_type: str  # "白底主图", "场景氛围图", "卖点特写图"
    bg_color: str  # FFmpeg color hex
    accent_color: str  # text accent
    text_position: str  # "bottom" | "center" | "top-right"
    product_size: str  # "400x400" | "500x500" | "300x300"
    product_position: str  # "center-top" | "center" | "full"
    overlay_style: str  # "clean" | "dark-box" | "gradient-bottom"


# ── Pre-built scene sequences per video style ──

REAL_PERSON_SCENES = [
    SceneDef(0, "钩子", 3.0, "场景氛围图", "0x2a2020", "0xff8866", "bottom", "400x400", "center-top", "dark-box"),
    SceneDef(1, "痛点", 4.0, "场景氛围图", "0x252015", "0xffaa44", "bottom", "400x400", "center-top", "dark-box"),
    SceneDef(2, "特写", 4.5, "卖点特写图", "0x1a2a20", "0x66dd88", "center", "500x500", "center", "clean"),
    SceneDef(3, "CTA", 3.5, "白底主图", "0x2a1a20", "0xff6688", "bottom", "400x400", "center-top", "gradient-bottom"),
]

PRODUCT_ONLY_SCENES = [
    SceneDef(0, "钩子", 3.0, "白底主图", "0xf8f8f5", "0x333333", "bottom", "500x500", "center", "clean"),
    SceneDef(1, "痛点", 4.0, "场景氛围图", "0xfafaf8", "0x444444", "bottom", "500x500", "center", "clean"),
    SceneDef(2, "特写", 4.5, "卖点特写图", "0xf5f8f5", "0x333333", "center", "600x600", "full", "clean"),
    SceneDef(3, "CTA", 3.5, "白底主图", "0xfaf5f5", "0x444444", "bottom", "500x500", "center", "clean"),
]

TECH_3D_SCENES = [
    SceneDef(0, "钩子", 3.0, "场景氛围图", "0x0a0a1a", "0x00ffcc", "bottom", "400x400", "center-top", "dark-box"),
    SceneDef(1, "痛点", 4.0, "卖点特写图", "0x0a1a0a", "0x00ccff", "bottom", "450x450", "center-top", "dark-box"),
    SceneDef(2, "特写", 4.5, "白底主图", "0x1a0a1a", "0xff00cc", "center", "500x500", "center", "clean"),
    SceneDef(3, "CTA", 3.5, "场景氛围图", "0x0a1a1a", "0xccff00", "bottom", "400x400", "center-top", "gradient-bottom"),
]

UNBOXING_SCENES = [
    SceneDef(0, "钩子", 3.0, "场景氛围图", "0x2a2520", "0xffcc88", "bottom", "350x350", "center-top", "gradient-bottom"),
    SceneDef(1, "痛点", 4.0, "卖点特写图", "0x282420", "0xffbb66", "bottom", "450x450", "center", "dark-box"),
    SceneDef(2, "特写", 4.5, "白底主图", "0x252820", "0xffdd99", "center", "500x500", "center", "clean"),
    SceneDef(3, "CTA", 3.5, "场景氛围图", "0x2a2820", "0xffaa55", "bottom", "400x400", "center-top", "dark-box"),
]

COMPARE_SCENES = [
    SceneDef(0, "钩子", 3.0, "白底主图", "0x1a1a2a", "0xffd700", "bottom", "350x350", "center-top", "dark-box"),
    SceneDef(1, "痛点", 4.0, "卖点特写图", "0x2a1a1a", "0xff8800", "bottom", "450x450", "center", "dark-box"),
    SceneDef(2, "特写", 4.5, "场景氛围图", "0x1a2a1a", "0x00ff88", "center", "500x500", "center", "clean"),
    SceneDef(3, "CTA", 3.5, "白底主图", "0x2a2a1a", "0xffd700", "bottom", "400x400", "center-top", "gradient-bottom"),
]

STYLE_SCENE_MAP = {
    "real": REAL_PERSON_SCENES,
    "product": PRODUCT_ONLY_SCENES,
    "3d": TECH_3D_SCENES,
    "unbox": UNBOXING_SCENES,
    "compare": COMPARE_SCENES,
}


def get_scenes(style: str) -> list[SceneDef]:
    """Get 4-scene storyboard for a given video style."""
    return STYLE_SCENE_MAP.get(style, REAL_PERSON_SCENES)
