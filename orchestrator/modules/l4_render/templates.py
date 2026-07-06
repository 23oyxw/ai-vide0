"""
Scene templates for video composition.
Each template defines: background, layout zones, model position, text position.
Backgrounds are generated via FFmpeg as simple gradient/pattern frames.
Models are simple silhouette placeholders (colored rounded rects).
"""

from __future__ import annotations

from pathlib import Path
import subprocess as sp

FFMPEG = "ffmpeg"
FONT = "C\\:/Windows/Fonts/simhei.ttf"
CANVAS = "720x1280"
FPS = 24


# ── Style → Template mapping ──
# Each style maps to 4 scene templates (hook/pain/product/CTA)
TEMPLATES = {
    "real": {
        "bg_gradient": ["0x2a2020:0x1a1010", "0x252015:0x1a100a", "0x1a2a20:0x0a1a10", "0x2a1a20:0x1a0a10"],
        "accent": ["0xff8866", "0xffaa44", "0x66dd88", "0xff6688"],
        "layout": "model_left_product_right",
        "description": "真人出镜：暖色渐变背景，左模特右产品",
    },
    "product": {
        "bg_gradient": ["0xf8f8f5:0xf0f0ea", "0xfafaf8:0xf2f2ee", "0xf5f8f5:0xeef0ee", "0xfaf5f5:0xf5eeee"],
        "accent": ["0x333333", "0x444444", "0x333333", "0x444444"],
        "layout": "product_center",
        "description": "纯产品：极简浅灰渐变，产品居中",
    },
    "3d": {
        "bg_gradient": ["0x0a0a1a:0x050510", "0x0a1a0a:0x050a05", "0x1a0a1a:0x0a050a", "0x0a1a1a:0x050a0a"],
        "accent": ["0x00ffcc", "0x00ccff", "0xff00cc", "0xccff00"],
        "layout": "product_center_rotate",
        "description": "3D 动画：暗黑科技渐变，产品居中放大",
    },
    "unbox": {
        "bg_gradient": ["0x2a2520:0x1a1510", "0x282420:0x181410", "0x252820:0x151810", "0x2a2820:0x1a1810"],
        "accent": ["0xffcc88", "0xffbb66", "0xffdd99", "0xffaa55"],
        "layout": "product_center_desk",
        "description": "开箱测评：桌面木色渐变，产品居中桌面感",
    },
    "compare": {
        "bg_gradient": ["0x1a1a2a:0x0a0a1a", "0x2a1a1a:0x1a0a0a", "0x1a2a1a:0x0a1a0a", "0x2a2a1a:0x1a1a0a"],
        "accent": ["0xffd700", "0xff8800", "0x00ff88", "0xffd700"],
        "layout": "split_left_right",
        "description": "对比测评：分屏暗色渐变，左右对比布局",
    },
}


def generate_template_frame(
    style: str,
    scene_idx: int,
    output_path: Path,
) -> Path | None:
    """Generate a single background frame image for a scene."""
    t = TEMPLATES.get(style, TEMPLATES["real"])
    gradient = t["bg_gradient"][scene_idx % len(t["bg_gradient"])]
    out = output_path / f"bg_{scene_idx}.png"
    r = sp.run([
        FFMPEG, "-y",
        "-f", "lavfi", "-i", f"gradient=c={gradient}:s={CANVAS}:d=0.1",
        "-frames:v", "1", "-q:v", "1",
        str(out),
    ], capture_output=True, text=True, timeout=10)
    if out.exists() and out.stat().st_size > 100:
        return out
    return None


def generate_model_silhouette(
    style: str,
    output_path: Path,
) -> Path | None:
    """Generate a simple model silhouette placeholder."""
    t = TEMPLATES.get(style, TEMPLATES["real"])
    accent = t["accent"][0]
    out = output_path / "model_placeholder.png"
    # Simple rounded rect silhouette at bottom-left
    r = sp.run([
        FFMPEG, "-y",
        "-f", "lavfi", "-i", f"color=c={accent}@0.3:s=240x480:d=0.1",
        "-frames:v", "1", "-q:v", "1",
        str(out),
    ], capture_output=True, text=True, timeout=10)
    if out.exists() and out.stat().st_size > 100:
        return out
    return None


def get_template_config(style: str) -> dict:
    """Get the full template configuration for a style."""
    return TEMPLATES.get(style, TEMPLATES["real"])
